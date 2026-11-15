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
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class IdeaIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = ""
    premise: str = ""
    stage: str = "现在做"
    tags: list[str] = []
    project_id: str = "demo-project"


class IdeaPatch(BaseModel):
    title: str | None = None
    summary: str | None = None
    premise: str | None = None
    stage: str | None = None
    tags: list[str] | None = None
    favorite: bool | None = None


class SourceIn(BaseModel):
    message_id: str = Field(min_length=1)
    source_ref: str | None = None
    quote: str | None = None


class RelationIn(BaseModel):
    from_idea_id: str
    to_idea_id: str
    relation_type: str
    note: str | None = None


class RelationPatch(BaseModel):
    status: str


def out(session: Session, idea: Idea) -> dict:
    """把一行 idea 转成前端要的样子，出处单独查。"""
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
    """关系对前端来说要知道对方是谁。"""
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


@app.post("/api/ideas", status_code=201)
def create_idea(payload: IdeaIn):
    if payload.stage not in STAGES:
        raise HTTPException(422, "阶段只能是：现在做 / 以后再说 / 已放弃")
    idea = Idea(
        project_id=payload.project_id,
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


@app.patch("/api/ideas/{idea_id}")
def update_idea(idea_id: str, payload: IdeaPatch):
    changes = payload.model_dump(exclude_unset=True)
    if "stage" in changes and changes["stage"] not in STAGES:
        raise HTTPException(422, "阶段只能是：现在做 / 以后再说 / 已放弃")
    if "tags" in changes:
        changes["tags"] = ",".join(changes["tags"])
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
        return [
            {"message_id": r.message_id, "source_ref": r.source_ref, "quote": r.quote, "created_at": r.created_at}
            for r in rows
        ]


@app.post("/api/ideas/{idea_id}/sources", status_code=201)
def add_source(idea_id: str, payload: SourceIn):
    with Session(models.engine) as session:
        find(session, idea_id)
        if session.get(IdeaSource, (idea_id, payload.message_id)):
            raise HTTPException(409, "这条出处已经存过")
        row = IdeaSource(
            idea_id=idea_id,
            message_id=payload.message_id,
            source_ref=payload.source_ref,
            quote=payload.quote,
        )
        session.add(row)
        session.commit()
        return {"message_id": row.message_id, "source_ref": row.source_ref, "quote": row.quote, "created_at": row.created_at}


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
    small, big = sorted([payload.from_idea_id, payload.to_idea_id])  # 按编号小到大存，避免存两条
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
