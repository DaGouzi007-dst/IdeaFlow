from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlmodel import Session, SQLModel, select

import models
from models import Idea, IdeaSource

SQLModel.metadata.create_all(models.engine)

STAGES = ("现在做", "以后再说", "已放弃")

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
        "updated_at": idea.updated_at,
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
        for row in session.exec(select(IdeaSource).where(IdeaSource.idea_id == idea_id)).all():
            session.delete(row)
        session.delete(find(session, idea_id))
        session.commit()
    return Response(status_code=204)


# 还没写：出处接口（GET/POST /api/ideas/{id}/sources）、关系接口（GET /api/ideas/{id}/relations、POST /api/relations、PATCH /api/relations/{id}）
