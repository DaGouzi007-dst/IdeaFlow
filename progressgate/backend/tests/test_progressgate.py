from contextlib import contextmanager
from io import BytesIO
import json
from urllib.error import HTTPError, URLError
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import demo
from app.db import get_session
from app.main import app
from app.models import Decision
from app.references import LiveReferences, get_reference_data


PROJECT = "11111111-1111-4111-8111-111111111111"
IDEA = "44444444-4444-4444-8444-444444444441"
OTHER_PROJECT = "22222222-2222-4222-8222-222222222222"
CONVERSATION = "33333333-3333-4333-8333-333333333333"
MESSAGE = "55555555-5555-4555-8555-555555555555"


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


@pytest.fixture
def live_routes(client, monkeypatch):
    idea = {"idea_id": IDEA, "project_id": PROJECT, "title": "服务中的想法", "summary": "服务中的摘要", "stage": "现在做"}
    routes = {
        "http://projects.test/api/projects": [{"project_id": PROJECT, "name": "服务项目"}],
        f"http://projects.test/api/projects/{PROJECT}": {"project_id": PROJECT, "name": "服务项目"},
        f"http://projects.test/api/projects/{OTHER_PROJECT}": {"project_id": OTHER_PROJECT, "name": "另一个项目"},
        "http://ideas.test/api/ideas": [idea, {**idea, "idea_id": str(uuid4()), "project_id": OTHER_PROJECT},
                                          {**idea, "idea_id": str(uuid4()), "project_id": "demo-project"}],
        f"http://ideas.test/api/ideas/{IDEA}": idea,
        f"http://ideas.test/api/ideas/{IDEA}/sources": [{"message_id": MESSAGE, "quote": "服务中的原文", "source_ref": json.dumps({
            "projectId": PROJECT, "sessionId": CONVERSATION, "messageId": MESSAGE,
        })}],
        f"http://projects.test/api/conversations/{CONVERSATION}": {
            "project_id": PROJECT, "conversation_id": CONVERSATION, "title": "服务中的会话",
            "messages": [{"message_id": MESSAGE, "seq": 1, "role": "user", "content": "服务中的原文"}],
        },
    }

    def fake_open(url, timeout):
        assert timeout == 5
        value = routes.get(url)
        if url not in routes:
            raise HTTPError(url, 404, "missing", {}, None)
        if isinstance(value, Exception):
            raise value
        return BytesIO(value if isinstance(value, bytes) else json.dumps(value).encode())

    monkeypatch.setattr("app.references.urlopen", fake_open)
    app.dependency_overrides[get_reference_data] = lambda: LiveReferences("http://projects.test", "http://ideas.test")
    try:
        yield routes
    finally:
        app.dependency_overrides.pop(get_reference_data, None)


def test_live_project_filter_and_idea_mapping(client, live_routes):
    assert client.get("/api/health").json()["reference_data"] == "live"
    assert client.get("/api/projects").json() == [{"project_id": PROJECT, "name": "服务项目"}]
    ideas = client.get(f"/api/projects/{PROJECT}/ideas").json()
    assert len(ideas) == 1 and ideas[0]["content"] == "服务中的摘要"
    assert ideas[0]["idea_id"] == IDEA and ideas[0]["project_id"] == PROJECT


def test_live_idea_requires_explicit_adoption_and_resolves_original_message(client, live_routes):
    task_url = f"/api/projects/{PROJECT}/tasks"
    assert client.post(task_url, json={"title": "关联实际想法", "idea_id": IDEA}).status_code == 422
    assert client.put(f"/api/ideas/{IDEA}/decision", json={"status": "adopted"}).status_code == 200
    assert client.post(task_url, json={"title": "关联实际想法", "idea_id": IDEA}).status_code == 201
    sources = client.get(f"/api/ideas/{IDEA}/sources").json()
    assert sources[0]["status"] == "available"
    assert sources[0]["context"][0]["message_id"] == MESSAGE
    assert sources[0]["context"][0]["content"] == "服务中的原文"


@pytest.mark.parametrize("case, expected", [
    ("no_ref", "unresolved"), ("partial_ref", "unresolved"), ("bad_json", "invalid"), ("foreign_ref", "invalid"),
    ("foreign_conversation", "invalid"), ("deleted_conversation", "missing"), ("deleted_message", "missing"),
])
def test_live_sources_do_not_fabricate_or_leak_context(client, live_routes, case, expected):
    source = live_routes[f"http://ideas.test/api/ideas/{IDEA}/sources"][0]
    conversation_url = f"http://projects.test/api/conversations/{CONVERSATION}"
    if case == "no_ref":
        source["source_ref"] = None
    elif case == "partial_ref":
        source["source_ref"] = json.dumps({"projectId": PROJECT, "messageId": MESSAGE})
    elif case == "bad_json":
        source["source_ref"] = "{invalid"
    elif case == "foreign_ref":
        source["source_ref"] = json.dumps({"projectId": OTHER_PROJECT, "sessionId": CONVERSATION, "messageId": MESSAGE})
    elif case == "foreign_conversation":
        live_routes[conversation_url]["project_id"] = OTHER_PROJECT
    elif case == "deleted_conversation":
        del live_routes[conversation_url]
    else:
        live_routes[conversation_url]["messages"] = []
    response = client.get(f"/api/ideas/{IDEA}/sources")
    assert response.status_code == 200
    source = response.json()[0]
    assert source["status"] == expected and source["context"] == []
    assert source["quote"] == "服务中的原文"


def test_live_upstream_errors_do_not_fall_back_to_demo(client, live_routes):
    live_routes["http://projects.test/api/projects"] = URLError("offline")
    response = client.get("/api/projects")
    assert response.status_code == 503 and "暂不可用" in response.json()["detail"]
    live_routes["http://projects.test/api/projects"] = b"not json"
    assert client.get("/api/projects").status_code == 502
    assert client.get(f"/api/projects/{uuid4()}/ideas").status_code == 404
    live_routes[f"http://ideas.test/api/ideas/{IDEA}"]["idea_id"] = str(uuid4())
    assert client.get(f"/api/ideas/{IDEA}/decision").status_code == 502
    assert client.get(f"/api/projects/{PROJECT}/tasks").json() == []


def test_moved_idea_needs_adoption_in_its_new_project(client, live_routes):
    decision_url = f"/api/ideas/{IDEA}/decision"
    client.put(decision_url, json={"status": "adopted"})
    old_task = client.post(f"/api/projects/{PROJECT}/tasks", json={"title": "原项目任务", "idea_id": IDEA}).json()
    live_routes[f"http://ideas.test/api/ideas/{IDEA}"]["project_id"] = OTHER_PROJECT
    assert client.get(decision_url).json() is None
    new_task_url = f"/api/projects/{OTHER_PROJECT}/tasks"
    assert client.post(new_task_url, json={"title": "新项目任务", "idea_id": IDEA}).status_code == 422
    assert client.put(decision_url, json={"status": "adopted"}).status_code == 200
    assert client.post(new_task_url, json={"title": "新项目任务", "idea_id": IDEA}).status_code == 201
    assert client.get(f"/api/tasks/{old_task['task_id']}").json()["project_id"] == PROJECT
    events = client.get(f"{decision_url}/events").json()
    assert events[-1]["changes"]["project_id"] == {"from": PROJECT, "to": OTHER_PROJECT}


def test_invalid_reference_mode_is_rejected(monkeypatch):
    get_reference_data.cache_clear()
    try:
        monkeypatch.setenv("PROGRESSGATE_REFERENCE_MODE", "typo")
        with pytest.raises(ValueError, match="demo 或 live"):
            get_reference_data()
    finally:
        get_reference_data.cache_clear()


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


def test_decision_history_and_unchanged_save(client):
    url = f"/api/ideas/{IDEA}/decision"
    assert client.get(f"{url}/events").json() == []
    assert client.get(f"/api/ideas/{uuid4()}/decision/events").status_code == 404
    first = client.put(url, json={"status": "adopted", "reason": "先做原型"}).json()
    assert client.put(url, json={"status": "adopted", "reason": "先做原型"}).json()["updated_at"] == first["updated_at"]
    client.put(url, json={"status": "rejected", "reason": "条件变化"})
    client.put(url, json={"status": "rejected", "reason": ""})
    events = client.get(f"{url}/events").json()
    assert [event["event_type"] for event in events] == ["created", "updated", "updated"]
    assert events[0]["changes"]["status"] == {"from": None, "to": "adopted"}
    assert events[1]["changes"] == {"status": {"from": "adopted", "to": "rejected"},
                                     "reason": {"from": "先做原型", "to": "条件变化"}}
    assert events[2]["changes"] == {"reason": {"from": "条件变化", "to": None}}


def test_existing_decision_starts_history_on_next_change(tmp_path, monkeypatch):
    # Simulate a pre-upgrade database without the new event table.
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}", connect_args={"check_same_thread": False})
    old_tables = [table for table in SQLModel.metadata.sorted_tables if table.name != "decisionevent"]
    SQLModel.metadata.create_all(engine, tables=old_tables)
    with Session(engine) as session:
        session.add(Decision(project_id=PROJECT, idea_id=IDEA, status="pending", reason="原有理由"))
        session.commit()

    def old_database_session():
        with Session(engine) as session:
            yield session

    monkeypatch.setattr("app.main.create_tables", lambda: SQLModel.metadata.create_all(engine))
    app.dependency_overrides[get_session] = old_database_session
    try:
        with TestClient(app) as client:
            url = f"/api/ideas/{IDEA}/decision"
            assert client.get(url).json()["reason"] == "原有理由"
            assert client.get(f"{url}/events").json() == []
            assert client.put(url, json={"status": "adopted", "reason": "新理由"}).status_code == 200
            events = client.get(f"{url}/events").json()
            assert len(events) == 1 and events[0]["event_type"] == "updated"
            assert events[0]["changes"]["reason"] == {"from": "原有理由", "to": "新理由"}
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


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
        assert client.get(f"/api/ideas/{IDEA}/decision/events").json()[0]["changes"]["reason"]["to"] == "保留来源，方便回顾"
        tasks = client.get(f"/api/projects/{PROJECT}/tasks").json()
        assert [task["task_id"] for task in tasks] == [task_id]
        task = client.get(f"/api/tasks/{task_id}").json()
        assert task["status"] == "blocked" and task["block_reason"] == "等待联调"
        assert task["idea_id"] == IDEA
        events = client.get(f"/api/tasks/{task_id}/events").json()
        assert len(events) == 2
        assert events[1]["changes"]["status"] == {"from": "todo", "to": "blocked"}
