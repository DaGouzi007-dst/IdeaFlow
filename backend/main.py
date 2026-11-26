import json
import math
import os
import urllib.parse
import urllib.request
from collections import Counter
from uuid import UUID

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlmodel import Session, SQLModel, select

import models
from models import Idea, IdeaRelation, IdeaSource

SQLModel.metadata.create_all(models.engine)

STAGES = ("现在做", "以后再说", "已放弃")
TYPES = ("重复", "互补", "冲突")
STATUSES = ("待确认", "已确认", "已拒绝")

app = FastAPI(title="IdeaFlow 想法卡片")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5171",
        "http://localhost:5171",
        "http://127.0.0.1:5172",
        "http://localhost:5172",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 新建 json
class IdeaIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = ""
    premise: str = ""
    stage: str = "现在做"
    tags: list[str] = []
    project_id: str | None = None  # 为空表示不绑定项目

# 修改 json
class IdeaPatch(BaseModel):
    title: str | None = None
    summary: str | None = None
    premise: str | None = None
    stage: str | None = None
    tags: list[str] | None = None
    favorite: bool | None = None
    project_id: str | None = None

# 加出处json
class SourceRef(BaseModel):
    """与第二部分接口一致的坐标结构。"""

    projectId: str
    sessionId: str
    messageId: str
    charStart: int | None = None
    charEnd: int | None = None
    snippet: str | None = None


class SourceIn(BaseModel):
    message_id: str = Field(min_length=1)
    source_ref: str | None = None
    quote: str | None = None
    ref: SourceRef | None = None  # 可选，兼容不传坐标的调用


# 从搜索结果建卡，卡片与出处一次写入
class FromSourceIn(BaseModel):
    ref: SourceRef
    quote: str = ""
    project_id: str | None = None  # 缺省取坐标中的 projectId
    title: str | None = None  # 缺省取原文前 40 字
    summary: str | None = None
    tags: list[str] = []
    premise: str = ""
    stage: str = "现在做"

# 建立关系
class RelationIn(BaseModel):
    from_idea_id: str
    to_idea_id: str
    relation_type: str
    note: str | None = None

# 改状态
class RelationPatch(BaseModel):
    status: str

# 三个数据库工具函数
def out(session: Session, idea: Idea) -> dict:
    """转换为接口返回结构，出处单独查询。"""
    rows = session.exec(select(IdeaSource).where(IdeaSource.idea_id == idea.idea_id)).all()
    return {
        "idea_id": idea.idea_id,
        "project_id": idea.project_id,
        "title": idea.title,
        "summary": idea.summary,
        "tags": (idea.tags or "").split(",") if idea.tags else [],
        "premise": idea.premise,
        "stage": idea.stage,
        "favorite": idea.favorite,
        "sources": [row.message_id for row in rows],
        "created_at": idea.created_at,
        "updated_at": idea.updated_at,
    }


def relation_out(session: Session, rel: IdeaRelation) -> dict:
    """补上双方的标题。"""
    a = session.get(Idea, rel.from_idea_id)
    b = session.get(Idea, rel.to_idea_id)
    return {
        "relation_id": rel.relation_id,
        "from_idea_id": rel.from_idea_id,
        "from_title": a.title if a else "（已删除）",
        "to_idea_id": rel.to_idea_id,
        "to_title": b.title if b else "（已删除）",
        "relation_type": rel.relation_type,
        "status": rel.status,
        "note": rel.note,
        "updated_at": rel.updated_at,
    }


def find(session: Session, idea_id: str) -> Idea:
    idea = session.get(Idea, idea_id)
    if idea is None:
        raise HTTPException(404, "找不到这条想法")
    return idea


# ---------- 相似推荐 ----------
# 中文不分词，按字符二元组统计；IDF 降低常见字组的权重


def grams(text: str) -> list[str]:
    s = "".join(c for c in text if c.isalnum())
    return [s[i : i + 2] for i in range(len(s) - 1)]


def vectorize(docs: list[str]) -> list[dict]:
    counts = [Counter(grams(d)) for d in docs]
    df = Counter()
    for c in counts:
        df.update(c.keys())
    n = len(docs)
    vecs = []
    for c in counts:
        total = sum(c.values()) or 1
        vec = {w: (k / total) * (math.log((1 + n) / (1 + df[w])) + 1) for w, k in c.items()}
        norm = math.sqrt(sum(x * x for x in vec.values())) or 1
        vecs.append({w: x / norm for w, x in vec.items()})  # 归一化后点积就是余弦
    return vecs


def idea_text(idea: Idea) -> str:
    """标题重复一次以加权，说明、标签、前提一并参与。"""
    tags = " ".join((idea.tags or "").split(","))
    return f"{idea.title} {idea.title} {idea.summary or ''} {tags} {idea.premise or ''}"


def source_out(row: IdeaSource) -> dict:
    """返回拆分后的 ref，同时保留原始 source_ref。"""
    ref = None
    if row.source_ref and row.source_ref.startswith("{"):
        try:
            ref = json.loads(row.source_ref)
        except ValueError:
            ref = None
    return {
        "message_id": row.message_id,
        "source_ref": row.source_ref,
        "ref": ref,
        "quote": row.quote,
        "created_at": row.created_at,
    }


def is_uuid(value: str) -> bool:
    """判断字符串是否为 UUID。"""
    try:
        UUID(str(value))
        return True
    except ValueError:
        return False


def same_span(row: "IdeaSource", char_start: int | None, quote: str) -> bool:
    """判断是否为同一段出处：有坐标比对起始位置，否则比对原文。"""
    if char_start is None:
        return (row.quote or "").strip() == quote
    if not row.source_ref or not row.source_ref.startswith("{"):
        return False
    try:
        return json.loads(row.source_ref).get("charStart") == char_start
    except ValueError:
        return False


# 接口
@app.get("/api/ideas")
def list_ideas(q: str | None = None):
    with Session(models.engine) as session:
        stmt = select(Idea)
        if q:
            kw = "%" + q + "%"
            stmt = stmt.where(
                or_(Idea.title.like(kw), Idea.summary.like(kw), Idea.tags.like(kw), Idea.premise.like(kw))
            )
        stmt = stmt.order_by(Idea.favorite.desc(), Idea.updated_at.desc())
        return [out(session, idea) for idea in session.exec(stmt).all()]


@app.get("/api/ideas/{idea_id}")
def get_idea(idea_id: str):
    with Session(models.engine) as session:
        return out(session, find(session, idea_id))

# 相似推荐
@app.get("/api/ideas/{idea_id}/similar")
def similar_ideas(idea_id: str, limit: int = 3):
    """返回措辞相近的卡片，仅作提示。"""
    if not 1 <= limit <= 10:
        raise HTTPException(422, "limit 取 1 到 10")
    with Session(models.engine) as session:
        idea = find(session, idea_id)
        others = [row for row in session.exec(select(Idea)).all() if row.idea_id != idea_id]
        if not others:
            return []
        vecs = vectorize([idea_text(idea)] + [idea_text(row) for row in others])
        pairs = [(sum(x * vecs[i + 1].get(w, 0) for w, x in vecs[0].items()), row) for i, row in enumerate(others)]
        pairs.sort(key=lambda p: p[0], reverse=True)
        weak = not (idea.summary or "").strip()  # 未填说明时结果不稳定，标记给前端
        return [
            {"idea_id": row.idea_id, "title": row.title, "score": round(score, 3), "weak": weak}
            for score, row in pairs
            if score >= 0.25
        ][:limit]


@app.post("/api/ideas", status_code=201)
def create_idea(payload: IdeaIn):
    if payload.stage not in STAGES:
        raise HTTPException(422, "阶段只能是：现在做 / 以后再说 / 已放弃")
    idea = Idea(
        # 纯知识性想法不绑项目，空串表示未归属
        project_id=(payload.project_id or "").strip(),
        title=payload.title.strip(),
        summary=payload.summary,
        premise=payload.premise,
        stage=payload.stage,
        tags=",".join(payload.tags),
    )
    with Session(models.engine) as session:
        session.add(idea)
        session.commit()
        session.refresh(idea)
        return out(session, idea)


@app.post("/api/ideas/from-source", status_code=201)
def create_from_source(payload: FromSourceIn):
    """从搜索结果建卡，卡片与出处在同一事务内写入。"""
    ref = payload.ref
    quote = (payload.quote or "").strip()
    if not quote:
        raise HTTPException(422, "必须带原文片段")
    if payload.stage not in STAGES:
        raise HTTPException(422, "阶段只能是：现在做 / 以后再说 / 已放弃")
    if not is_uuid(ref.projectId):
        raise HTTPException(422, "projectId 不是 UUID：" + ref.projectId)
    if not is_uuid(ref.sessionId):
        raise HTTPException(422, "sessionId 不是 UUID：" + ref.sessionId)
    if ref.charStart is not None and ref.charEnd is not None and ref.charEnd < ref.charStart:
        raise HTTPException(422, "charEnd 不能小于 charStart")
    project_id = (payload.project_id or ref.projectId).strip()
    if project_id != ref.projectId:
        raise HTTPException(422, "项目归属不一致：project_id 和坐标里的 projectId 不一样")
    title = (payload.title or "").strip() or quote[:40]
    with Session(models.engine) as session:
        # 同一消息的同一段话只存一次，重复时返回已有卡片编号
        for row in session.exec(select(IdeaSource).where(IdeaSource.message_id == ref.messageId)).all():
            if same_span(row, ref.charStart, quote):
                raise HTTPException(409, {"message": "这条出处已经存过", "existing_idea_id": row.idea_id})
        idea = Idea(
            project_id=project_id,
            title=title[:200],
            summary=payload.summary if payload.summary is not None else quote,
            premise=payload.premise,
            stage=payload.stage,
            tags=",".join(payload.tags),
        )
        session.add(idea)
        session.flush()
        session.add(
            IdeaSource(
                idea_id=idea.idea_id,
                message_id=ref.messageId,
                source_ref=ref.model_dump_json(),
                quote=quote,
            )
        )
        session.commit()
        session.refresh(idea)
        return out(session, idea)


@app.patch("/api/ideas/{idea_id}")
def update_idea(idea_id: str, payload: IdeaPatch):
    changes = payload.model_dump(exclude_unset=True)
    if "stage" in changes and changes["stage"] not in STAGES:
        raise HTTPException(422, "阶段只能是：现在做 / 以后再说 / 已放弃")
    if "tags" in changes:
        changes["tags"] = ",".join(changes["tags"])
    if "project_id" in changes:
        changes["project_id"] = (changes["project_id"] or "").strip()
    with Session(models.engine) as session:
        idea = find(session, idea_id)
        for key, value in changes.items():
            setattr(idea, key, value)
        idea.updated_at = models.now()
        session.commit()
        session.refresh(idea)
        return out(session, idea)


@app.delete("/api/ideas/{idea_id}", status_code=204)
def delete_idea(idea_id: str):
    with Session(models.engine) as session:
        find(session, idea_id)
        for row in session.exec(select(IdeaSource).where(IdeaSource.idea_id == idea_id)).all():
            session.delete(row)
        rels = session.exec(
            select(IdeaRelation).where(
                or_(IdeaRelation.from_idea_id == idea_id, IdeaRelation.to_idea_id == idea_id)
            )
        ).all()
        for rel in rels:
            session.delete(rel)
        session.delete(session.get(Idea, idea_id))
        session.commit()
    return Response(status_code=204)


# ---------- 出处 ----------


@app.get("/api/ideas/{idea_id}/sources")
def list_sources(idea_id: str):
    with Session(models.engine) as session:
        find(session, idea_id)
        rows = session.exec(
            select(IdeaSource).where(IdeaSource.idea_id == idea_id).order_by(IdeaSource.created_at)
        ).all()
        return [source_out(r) for r in rows]


@app.post("/api/ideas/{idea_id}/sources", status_code=201)
def add_source(idea_id: str, payload: SourceIn):
    if payload.ref and not (payload.quote and payload.quote.strip()):
        raise HTTPException(422, "有坐标的出处必须带原文片段")
    if payload.ref and payload.ref.messageId != payload.message_id:
        raise HTTPException(422, "坐标里的 messageId 和 message_id 对不上")
    with Session(models.engine) as session:
        find(session, idea_id)
        if session.get(IdeaSource, (idea_id, payload.message_id)):
            raise HTTPException(409, "这条出处已经存过")
        row = IdeaSource(
            idea_id=idea_id,
            message_id=payload.message_id,
            source_ref=payload.ref.model_dump_json() if payload.ref else payload.source_ref,
            quote=payload.quote,
        )
        session.add(row)
        session.commit()
        return source_out(row)


@app.get("/api/source-link")
def source_link(projectId: str, sessionId: str, messageId: str,
                charStart: int | None = None, charEnd: int | None = None):
    """跳转地址由第二部分生成，格式以对方接口为准。"""
    base = os.environ.get("PART2_BASE", "http://127.0.0.1:8002")
    params = {"projectId": projectId, "sessionId": sessionId, "messageId": messageId}
    if charStart is not None and charEnd is not None:
        params["charStart"] = charStart
        params["charEnd"] = charEnd
    url = base.rstrip("/") + "/api/trace/link?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            link = json.loads(resp.read().decode("utf-8"))["link"]
    except Exception:
        raise HTTPException(503, "第二部分服务不可用：请确认 PART2_BASE 与 8002 端口")
    return {"link": link if link.startswith("http") else base.rstrip("/") + link}


@app.delete("/api/ideas/{idea_id}/sources/{message_id}", status_code=204)
def remove_source(idea_id: str, message_id: str):
    with Session(models.engine) as session:
        row = session.get(IdeaSource, (idea_id, message_id))
        if row is None:
            raise HTTPException(404, "找不到这条出处")
        session.delete(row)
        session.commit()
    return Response(status_code=204)


# ---------- 关系 ----------


@app.get("/api/relations")
def list_all_relations(status: str | None = None):
    """不传 status 时返回全部。"""
    if status and status not in STATUSES:
        raise HTTPException(422, "状态只能是：待确认 / 已确认 / 已拒绝")
    with Session(models.engine) as session:
        stmt = select(IdeaRelation)
        if status:
            stmt = stmt.where(IdeaRelation.status == status)
        rows = session.exec(stmt.order_by(IdeaRelation.updated_at.desc())).all()
        return [relation_out(session, rel) for rel in rows]


@app.get("/api/ideas/{idea_id}/relations")
def list_relations(idea_id: str):
    with Session(models.engine) as session:
        find(session, idea_id)
        rows = session.exec(
            select(IdeaRelation).where(
                or_(IdeaRelation.from_idea_id == idea_id, IdeaRelation.to_idea_id == idea_id)
            )
        ).all()
        return [relation_out(session, rel) for rel in rows]


@app.post("/api/relations", status_code=201)
def create_relation(payload: RelationIn):
    if payload.relation_type not in TYPES:
        raise HTTPException(422, "关系类型只能是：重复 / 互补 / 冲突")
    if payload.from_idea_id == payload.to_idea_id:
        raise HTTPException(422, "不能和自己标关系")
    small, big = sorted([payload.from_idea_id, payload.to_idea_id])  # 统一按编号排序，避免重复记录
    with Session(models.engine) as session:
        find(session, small)
        find(session, big)
        exists = session.exec(
            select(IdeaRelation).where(
                IdeaRelation.from_idea_id == small,
                IdeaRelation.to_idea_id == big,
                IdeaRelation.relation_type == payload.relation_type,
            )
        ).first()
        if exists:
            raise HTTPException(409, "已经标过这条关系")
        rel = IdeaRelation(
            from_idea_id=small,
            to_idea_id=big,
            relation_type=payload.relation_type,
            note=payload.note,
        )
        session.add(rel)
        session.commit()
        session.refresh(rel)
        return relation_out(session, rel)


@app.patch("/api/relations/{relation_id}")
def update_relation(relation_id: str, payload: RelationPatch):
    if payload.status not in STATUSES:
        raise HTTPException(422, "状态只能是：待确认 / 已确认 / 已拒绝")
    with Session(models.engine) as session:
        rel = session.get(IdeaRelation, relation_id)
        if rel is None:
            raise HTTPException(404, "找不到这条关系")
        rel.status = payload.status
        rel.updated_at = models.now()
        session.commit()
        session.refresh(rel)
        return relation_out(session, rel)


if __name__ == "__main__":
    # 端口由环境变量 PORT 指定，默认 8000
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
