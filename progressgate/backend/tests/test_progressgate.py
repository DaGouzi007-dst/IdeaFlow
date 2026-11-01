from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import demo
from app.db import get_session
from app.main import app


PROJECT = "11111111-1111-4111-8111-111111111111"
IDEA = "44444444-4444-4444-8444-444444444441"


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def test_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr("app.main.create_tables", lambda: None)
    app.dependency_overrides[get_session] = test_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()


def test_decision_to_task_and_blocked_recovery(client):
    decision = client.put(
        f"/api/ideas/{IDEA}/decision", json={"status": "adopted", "reason": "先验证基本流程"}
    )
    assert decision.status_code == 200
    created = client.post(
        f"/api/projects/{PROJECT}/tasks",
        json={"title": "实现任务页面", "idea_id": IDEA, "completion_condition": "能记录进度", "due_date": "2026-11-01"},
    )
    assert created.status_code == 201
    task = created.json()
    assert task["idea_id"] == IDEA and task["status"] == "todo" and task["due_date"] == "2026-11-01"
    assert UUID(task["task_id"]).version == 4

    url = f"/api/tasks/{task['task_id']}"
    assert client.patch(url, json={"status": "blocked"}).status_code == 422
    blocked = client.patch(url, json={
        "status": "blocked", "block_reason": "接口尚未确认", "error_excerpt": "HTTP 422", "attempted_steps": "检查样例数据",
        "next_step": "与想法模块对齐",
    })
    assert blocked.status_code == 200
    resumed = client.patch(url, json={"status": "in_progress", "resolution": "字段已对齐"})
    assert resumed.status_code == 200
    assert client.patch(url, json={"status": "done"}).status_code == 422
    assert client.patch(url, json={"status": "done", "result": "页面及接口已完成"}).status_code == 200

    saved = client.get(url).json()
    assert saved["status"] == "done" and saved["idea_id"] == IDEA
    assert saved["block_reason"] == "接口尚未确认" and saved["resolution"] == "字段已对齐"
    assert saved["error_excerpt"] == "HTTP 422" and saved["attempted_steps"] == "检查样例数据"
    events = client.get(f"{url}/events").json()
    assert len(events) == 4
    assert [event["changes"].get("status", {}).get("to") for event in events[1:]] == [
        "blocked", "in_progress", "done"
    ]
    cleared = client.patch(url, json={"due_date": None})
    assert cleared.status_code == 200 and cleared.json()["due_date"] is None


def test_manual_tasks_and_decision_are_independent(client):
    response = client.post(f"/api/projects/{PROJECT}/tasks", json={"title": "手动任务"})
    assert response.status_code == 201 and response.json()["idea_id"] is None
    first = client.put(f"/api/ideas/{IDEA}/decision", json={"status": "pending"}).json()
    second = client.put(
        f"/api/ideas/{IDEA}/decision", json={"status": "rejected", "reason": "暂不采用"}
    ).json()
    assert first["decision_id"] == second["decision_id"]
    assert client.post(
        f"/api/projects/{PROJECT}/tasks", json={"title": "关联任务", "idea_id": IDEA}
    ).status_code == 422
    assert len(client.get(f"/api/projects/{PROJECT}/tasks").json()) == 1


def test_demo_source_context_and_manual_idea(client):
    sources = client.get(f"/api/demo/ideas/{IDEA}/sources")
    assert sources.status_code == 200
    source = sources.json()[0]
    assert source["conversation_title"] == "讨论任务跟踪"
    assert len(source["context"]) == 2
    assert any(message["message_id"] == source["message_id"] for message in source["context"])
    manual = "44444444-4444-4444-8444-444444444442"
    assert client.get(f"/api/demo/ideas/{manual}/sources").json() == []


def test_rejects_unknown_and_cross_project_references(client, monkeypatch):
    fixture = demo.demo_data()
    other_project, other_idea = str(uuid4()), str(uuid4())
    fixture["projects"].append({"project_id": other_project, "name": "另一个项目"})
    fixture["ideas"].append({
        "project_id": other_project, "idea_id": other_idea, "title": "其他项目的想法",
        "content": "示例", "source_message_id": None,
    })
    monkeypatch.setattr(demo, "demo_data", lambda: fixture)
    assert client.post(f"/api/projects/{uuid4()}/tasks", json={"title": "任务"}).status_code == 404
    assert client.post(f"/api/projects/{PROJECT}/tasks", json={
        "title": "任务", "idea_id": other_idea,
    }).status_code == 422
    assert client.get(f"/api/tasks/{uuid4()}").status_code == 404
    assert client.post(f"/api/projects/{PROJECT}/tasks", json={"title": "   "}).status_code == 422
    assert client.post(f"/api/projects/{PROJECT}/tasks", json={"title": "任务", "due_date": "not-a-date"}).status_code == 422


def test_records_survive_database_reopen(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'progressgate.db'}"

    @contextmanager
    def reopened_client():
        engine = create_engine(database_url, connect_args={"check_same_thread": False})

        def persisted_session():
            with Session(engine) as session:
                yield session

        with monkeypatch.context() as changes:
            changes.setattr(
                "app.main.create_tables", lambda: SQLModel.metadata.create_all(engine)
            )
            app.dependency_overrides[get_session] = persisted_session
            try:
                with TestClient(app) as test_client:
                    yield test_client
            finally:
                app.dependency_overrides.clear()
                engine.dispose()

    with reopened_client() as client:
        decision = client.put(
            f"/api/ideas/{IDEA}/decision",
            json={"status": "adopted", "reason": "保留来源，方便回顾"},
        )
        assert decision.status_code == 200
        created = client.post(
            f"/api/projects/{PROJECT}/tasks",
            json={"title": "验证记录持久化", "idea_id": IDEA},
        )
        assert created.status_code == 201
        task_id = created.json()["task_id"]
        updated = client.patch(
            f"/api/tasks/{task_id}",
            json={"status": "blocked", "block_reason": "等待联调"},
        )
        assert updated.status_code == 200

    # A new engine and HTTP client must read the same file without reseeding records.
    with reopened_client() as client:
        decision = client.get(f"/api/ideas/{IDEA}/decision").json()
        assert decision["status"] == "adopted"
        assert decision["reason"] == "保留来源，方便回顾"
        tasks = client.get(f"/api/projects/{PROJECT}/tasks").json()
        assert [task["task_id"] for task in tasks] == [task_id]
        task = client.get(f"/api/tasks/{task_id}").json()
        assert task["status"] == "blocked" and task["block_reason"] == "等待联调"
        assert task["idea_id"] == IDEA
        events = client.get(f"/api/tasks/{task_id}/events").json()
        assert len(events) == 2
        assert events[1]["changes"]["status"] == {"from": "todo", "to": "blocked"}
