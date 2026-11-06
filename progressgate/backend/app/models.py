import json
from datetime import date, datetime, timezone
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field as InputField, StringConstraints
from sqlalchemy import Column, Text, UniqueConstraint
from sqlmodel import Field, SQLModel
from typing_extensions import Annotated


TaskStatus = Literal["todo", "in_progress", "blocked", "done"]
DecisionStatus = Literal["pending", "adopted", "rejected"]
ShortTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


def new_id() -> str:
    return str(uuid4())


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Decision(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("idea_id", name="uq_decision_idea"),)

    decision_id: str = Field(default_factory=new_id, primary_key=True)
    project_id: str = Field(index=True)
    idea_id: str = Field(index=True)
    status: str
    reason: str | None = None
    updated_at: str = Field(default_factory=utc_now)


class DecisionEvent(SQLModel, table=True):
    event_id: str = Field(default_factory=new_id, primary_key=True)
    decision_id: str = Field(foreign_key="decision.decision_id", index=True)
    idea_id: str = Field(index=True)
    event_type: str
    changes_json: str = Field(sa_column=Column(Text, nullable=False))
    created_at: str = Field(default_factory=utc_now)

    def changes(self) -> dict:
        return json.loads(self.changes_json)


class Task(SQLModel, table=True):
    task_id: str = Field(default_factory=new_id, primary_key=True)
    project_id: str = Field(index=True)
    idea_id: str | None = Field(default=None, index=True)
    title: str
    description: str | None = None
    assignee: str | None = None
    due_date: str | None = None
    completion_condition: str | None = None
    status: str = "todo"
    block_reason: str | None = None
    error_excerpt: str | None = None
    attempted_steps: str | None = None
    next_step: str | None = None
    resolution: str | None = None
    result: str | None = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class TaskEvent(SQLModel, table=True):
    event_id: str = Field(default_factory=new_id, primary_key=True)
    task_id: str = Field(foreign_key="task.task_id", index=True)
    event_type: str
    changes_json: str = Field(sa_column=Column(Text, nullable=False))
    created_at: str = Field(default_factory=utc_now)

    def changes(self) -> dict:
        return json.loads(self.changes_json)


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DecisionInput(InputModel):
    status: DecisionStatus
    reason: str | None = InputField(default=None, max_length=5000)


class TaskInput(InputModel):
    title: ShortTitle
    idea_id: UUID | None = None
    description: str | None = InputField(default=None, max_length=5000)
    assignee: str | None = InputField(default=None, max_length=100)
    due_date: date | None = None
    completion_condition: str | None = InputField(default=None, max_length=5000)


class TaskUpdate(InputModel):
    title: ShortTitle | None = None
    description: str | None = InputField(default=None, max_length=5000)
    assignee: str | None = InputField(default=None, max_length=100)
    due_date: date | None = None
    completion_condition: str | None = InputField(default=None, max_length=5000)
    status: TaskStatus | None = None
    block_reason: str | None = InputField(default=None, max_length=5000)
    error_excerpt: str | None = InputField(default=None, max_length=5000)
    attempted_steps: str | None = InputField(default=None, max_length=5000)
    next_step: str | None = InputField(default=None, max_length=5000)
    resolution: str | None = InputField(default=None, max_length=5000)
    result: str | None = InputField(default=None, max_length=5000)
