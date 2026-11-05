import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel, create_engine

engine = create_engine("sqlite:///ideaflow.db", connect_args={"check_same_thread": False})


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


class Idea(SQLModel, table=True):
    idea_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    project_id: str
    title: str  # 不超过 200 字，接口里校验
    summary: str | None = None
    tags: str | None = None  # 逗号分隔
    premise: str | None = None
    stage: str = "现在做"
    favorite: bool = False
    created_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)


class IdeaSource(SQLModel, table=True):
    __tablename__ = "idea_source"

    idea_id: str = Field(foreign_key="idea.idea_id", primary_key=True)
    message_id: str = Field(primary_key=True)
    source_ref: str | None = None
    quote: str | None = None
    created_at: str = Field(default_factory=now)


class IdeaRelation(SQLModel, table=True):
    __tablename__ = "idea_relation"

    relation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    from_idea_id: str = Field(foreign_key="idea.idea_id")
    to_idea_id: str = Field(foreign_key="idea.idea_id")
    relation_type: str  # 重复 / 互补 / 冲突
    confidence: float | None = None
    status: str = "待确认"
    note: str | None = None
    created_at: str = Field(default_factory=now)
    updated_at: str = Field(default_factory=now)
