import json
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, select

from . import demo
from .db import create_tables, get_session
from .models import Decision, DecisionEvent, DecisionInput, Task, TaskEvent, TaskInput, TaskUpdate, utc_now


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    yield


app = FastAPI(title="IdeaFlow ProgressGate", version="0.1.0", lifespan=lifespan)
SessionDep = Annotated[Session, Depends(get_session)]


def get_task_or_404(session: Session, task_id: str) -> Task:
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.get("/api/health")
def health():
    return {"status": "ok", "reference_data": "demo"}


@app.get("/api/projects")
def list_demo_projects():
    return demo.projects()


@app.get("/api/projects/{project_id}/ideas")
def list_demo_ideas(project_id: UUID):
    return demo.ideas_for_project(str(project_id))


@app.get("/api/demo/ideas/{idea_id}/sources")
def list_demo_idea_sources(idea_id: UUID):
    return demo.idea_sources(str(idea_id))


@app.get("/api/ideas/{idea_id}/decision")
def get_decision(idea_id: UUID, session: SessionDep):
    idea = demo.require_idea(str(idea_id))
    decision = session.exec(select(Decision).where(Decision.idea_id == idea["idea_id"])).first()
    return decision


@app.put("/api/ideas/{idea_id}/decision")
def put_decision(idea_id: UUID, data: DecisionInput, session: SessionDep):
    idea = demo.require_idea(str(idea_id))
    decision = session.exec(select(Decision).where(Decision.idea_id == idea["idea_id"])).first()
    reason = data.reason or None
    if decision is None:
        decision = Decision(project_id=idea["project_id"], idea_id=idea["idea_id"], status=data.status, reason=reason)
        changes = {"status": {"from": None, "to": data.status}, "reason": {"from": None, "to": reason}}
        event_type = "created"
    else:
        changes = {key: {"from": getattr(decision, key), "to": value}
                   for key, value in {"status": data.status, "reason": reason}.items()
                   if getattr(decision, key) != value}
        event_type = "updated"
    if not changes:
        return decision
    decision.status = data.status
    decision.reason = reason
    decision.updated_at = utc_now()
    session.add(decision)
    session.add(DecisionEvent(decision_id=decision.decision_id, idea_id=decision.idea_id,
                              event_type=event_type, changes_json=json.dumps(changes, ensure_ascii=False)))
    session.commit()
    session.refresh(decision)
    return decision


@app.get("/api/ideas/{idea_id}/decision/events")
def decision_events(idea_id: UUID, session: SessionDep):
    idea = demo.require_idea(str(idea_id))
    events = session.exec(select(DecisionEvent).where(DecisionEvent.idea_id == idea["idea_id"])
                          .order_by(DecisionEvent.created_at.asc(), DecisionEvent.event_id.asc())).all()
    return [{"event_id": event.event_id, "decision_id": event.decision_id, "idea_id": event.idea_id,
             "event_type": event.event_type, "changes": event.changes(), "created_at": event.created_at}
            for event in events]


@app.get("/api/projects/{project_id}/tasks")
def list_tasks(project_id: UUID, session: SessionDep):
    project = demo.require_project(str(project_id))
    return session.exec(
        select(Task).where(Task.project_id == project["project_id"]).order_by(Task.created_at.desc())
    ).all()


@app.post("/api/projects/{project_id}/tasks", status_code=201)
def create_task(project_id: UUID, data: TaskInput, session: SessionDep):
    project = demo.require_project(str(project_id))
    idea_id = str(data.idea_id) if data.idea_id is not None else None
    if idea_id is not None:
        idea = demo.require_idea(idea_id)
        if idea["project_id"] != project["project_id"]:
            raise HTTPException(status_code=422, detail="想法不属于当前项目")
        decision = session.exec(select(Decision).where(Decision.idea_id == idea_id)).first()
        if decision is None or decision.status != "adopted":
            raise HTTPException(status_code=422, detail="请先将该想法的决策设为采纳")
    task = Task(
        project_id=project["project_id"],
        idea_id=idea_id,
        title=data.title,
        description=data.description or None,
        assignee=data.assignee or None,
        due_date=data.due_date.isoformat() if data.due_date else None,
        completion_condition=data.completion_condition or None,
    )
    session.add(task)
    session.add(TaskEvent(task_id=task.task_id, event_type="created", changes_json="{}"))
    session.commit()
    session.refresh(task)
    return task


@app.get("/api/tasks/{task_id}")
def get_task(task_id: UUID, session: SessionDep):
    return get_task_or_404(session, str(task_id))


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: UUID, data: TaskUpdate, session: SessionDep):
    task = get_task_or_404(session, str(task_id))
    updates = data.model_dump(mode="json", exclude_unset=True)
    if updates.get("title", task.title) is None or updates.get("status", task.status) is None:
        raise HTTPException(status_code=422, detail="任务标题和状态不能为空")
    updates = {key: (None if value == "" else value) for key, value in updates.items()}
    next_status = updates.get("status", task.status)
    block_reason = updates.get("block_reason", task.block_reason)
    result = updates.get("result", task.result)
    if next_status == "blocked" and not block_reason:
        raise HTTPException(status_code=422, detail="标记为受阻时，请填写阻塞原因")
    if next_status == "done" and not result:
        raise HTTPException(status_code=422, detail="标记为完成时，请填写执行结果")

    changes = {}
    for key, value in updates.items():
        previous = getattr(task, key)
        if previous != value:
            changes[key] = {"from": previous, "to": value}
            setattr(task, key, value)
    if changes:
        task.updated_at = utc_now()
        session.add(task)
        session.add(TaskEvent(
            task_id=task.task_id,
            event_type="updated",
            changes_json=json.dumps(changes, ensure_ascii=False),
        ))
        session.commit()
        session.refresh(task)
    return task


@app.get("/api/tasks/{task_id}/events")
def task_events(task_id: UUID, session: SessionDep):
    task = get_task_or_404(session, str(task_id))
    events = session.exec(
        select(TaskEvent).where(TaskEvent.task_id == task.task_id).order_by(TaskEvent.created_at.asc())
    ).all()
    return [
        {"event_id": event.event_id, "task_id": event.task_id, "event_type": event.event_type,
         "changes": event.changes(), "created_at": event.created_at}
        for event in events
    ]
