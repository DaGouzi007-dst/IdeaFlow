# -*- coding: utf-8 -*-
"""
[想法卡片]

接口：
    GET    /api/ideas            列表
    POST   /api/ideas            新建
    PATCH  /api/ideas/{idea_id}  修改
    DELETE /api/ideas/{idea_id}  删除


"""

import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlmodel import Field as DBField
from sqlmodel import Session, SQLModel, create_engine, select

DB_URL = "sqlite:///./ideaflow.db"
STAGES = ("现在做", "以后再说", "已放弃")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})


# 表
class Idea(SQLModel, table=True):
    idea_id: str = DBField(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = DBField(max_length=200)
    summary: str = DBField(default="")
    tags: str = DBField(default="")          # 逗号分隔
    premise: str = DBField(default="")       # 适用条件：这条建议在什么前提下成立
    stage: str = DBField(default="现在做")   # 现在做 / 以后再说 / 已放弃
    favorite: bool = DBField(default=False)
    sources: str = DBField(default="")       # 来源消息编号，逗号分隔
    updated_at: str = DBField(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


# 请求体
class IdeaIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = ""
    tags: list[str] = []
    premise: str = ""
    stage: str = "现在做"
    sources: list[str] = []


class IdeaPatch(BaseModel):
    """PATCH：字段都没填就等于不改。"""

    title: str | None = None
    summary: str | None = None
    tags: list[str] | None = None
    premise: str | None = None
    stage: str | None = None
    favorite: bool | None = None
    sources: list[str] | None = None


# 小工具
def split(text: str) -> list[str]:
    return [piece.strip() for piece in (text or "").split(",") if piece.strip()]


def join(items: list[str] | None) -> str:
    return ",".join(dict.fromkeys(str(item).strip() for item in (items or []) if str(item).strip()))


def to_out(idea: Idea) -> dict:
    return {
        "idea_id": idea.idea_id,
        "title": idea.title,
        "summary": idea.summary,
        "tags": split(idea.tags),
        "premise": idea.premise,
        "stage": idea.stage,
        "favorite": idea.favorite,
        "sources": split(idea.sources),
        "updated_at": idea.updated_at,
    }


def find(session: Session, idea_id: str) -> Idea:
    idea = session.get(Idea, idea_id)
    if idea is None:
        raise HTTPException(status_code=404, detail="找不到这条想法")
    return idea


# 初始化
app = FastAPI(title="IdeaFlow · 想法提取与整理（最小版）")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def prepare() -> None:
    """建表"""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        if session.exec(select(Idea)).first() is not None:
            return
        session.add_all(
            [
                Idea(
                    title="本地数据就用 SQLite 存",
                    summary="前后端都跑在自己机器上，没必要单独装数据库服务。",
                    tags="数据库,部署",
                    premise="数据量几 MB、只有一个人用",
                    stage="现在做",
                    sources="m-0107",
                ),
                Idea(
                    title="本地用 SQLite，别装 Postgres",
                    summary="一个人开发，起个数据库服务反而是负担。",
                    tags="数据库",
                    premise="本地开发阶段",
                    stage="现在做",
                    sources="m-0112",
                    favorite=True,
                ),
                Idea(
                    title="来源要做成单独一张表",
                    summary="一条想法可能来自好几段对话，一个来源也可能被好几条想法用到。",
                    tags="数据模型",
                    premise="需要点回原文的时候",
                    stage="以后再说",
                    sources="m-0131,m-0136",
                ),
                Idea(
                    title="先别做 AI 自动提取",
                    summary="靠模型判断哪句有用，误判了很难解释，第一版让人自己动手。",
                    tags="AI,范围",
                    premise="课程项目只有一个学期",
                    stage="现在做",
                    sources="m-0148",
                ),
                Idea(
                    title="前端用 Vue 全家桶",
                    summary="Vue 3 + Vite，别上 TypeScript 和 Pinia，四个人不好分工。",
                    tags="前端",
                    premise="组里没人写过 TypeScript",
                    stage="现在做",
                    sources="m-0155",
                ),
            ]
        )
        session.commit()


# 接口
@app.get("/api/ideas")
def list_ideas(q: str | None = None) -> list[dict]:
    with Session(engine) as session:
        statement = select(Idea)
        if q:
            keyword = "%" + q.replace("%", "").replace("_", "") + "%"
            statement = statement.where(
                or_(
                    Idea.title.like(keyword),
                    Idea.summary.like(keyword),
                    Idea.tags.like(keyword),
                    Idea.premise.like(keyword),
                )
            )
        statement = statement.order_by(Idea.favorite.desc(), Idea.updated_at.desc())
        return [to_out(idea) for idea in session.exec(statement).all()]


@app.post("/api/ideas", status_code=201)
def create_idea(payload: IdeaIn) -> dict:
    if payload.stage not in STAGES:
        raise HTTPException(status_code=422, detail="阶段只能是：现在做 / 以后再说 / 已放弃")
    idea = Idea(
        title=payload.title.strip(),
        summary=payload.summary.strip(),
        tags=join(payload.tags),
        premise=payload.premise.strip(),
        stage=payload.stage,
        sources=join(payload.sources),
    )
    with Session(engine) as session:
        session.add(idea)
        session.commit()
        session.refresh(idea)
        return to_out(idea)


@app.patch("/api/ideas/{idea_id}")
def update_idea(idea_id: str, payload: IdeaPatch) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    if "stage" in changes and changes["stage"] not in STAGES:
        raise HTTPException(status_code=422, detail="阶段只能是：现在做 / 以后再说 / 已放弃")
    for field in ("tags", "sources"):
        if field in changes:
            changes[field] = join(changes[field])
    with Session(engine) as session:
        idea = find(session, idea_id)
        for field, value in changes.items():
            setattr(idea, field, value)
        idea.updated_at = datetime.now().isoformat(timespec="seconds")
        session.add(idea)
        session.commit()
        session.refresh(idea)
        return to_out(idea)


@app.delete("/api/ideas/{idea_id}", status_code=204)
def delete_idea(idea_id: str) -> Response:
    with Session(engine) as session:
        session.delete(find(session, idea_id))
        session.commit()
    return Response(status_code=204)
