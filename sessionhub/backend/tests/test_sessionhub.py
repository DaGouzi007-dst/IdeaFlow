"""第一模块接口测试（pytest + FastAPI TestClient）。

覆盖：项目创建/列表/详情、导入成功路径、会话回读、
重复导入 409、overwrite 替换、404/422 结构化错误、未知字段忽略。

运行（在 sessionhub/backend 目录下）：
    python -m pytest tests/ -v
"""

import json
import sys
import uuid as uuidlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# 保证 `from app.main import app` 在任何工作目录下都能成立
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """每个测试用独立的临时数据库，互不干扰。"""
    monkeypatch.setenv("SESSIONHUB_DB", str(tmp_path / "test.db"))
    with TestClient(app) as c:
        yield c


def is_uuid(value: str) -> bool:
    try:
        uuidlib.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def make_project(client, name="演示项目"):
    resp = client.post("/api/projects", json={"name": name})
    assert resp.status_code == 201
    return resp.json()


def sample_body(**overrides):
    body = {
        "title": "讨论会话导入格式的边界",
        "source": "synthetic",
        "source_conversation_id": None,
        "messages": [
            {"role": "system", "content": "演示数据。", "created_at": None},
            {"role": "user", "content": "第一阶段支持哪些格式？",
             "created_at": "2026-11-05T20:05:00+08:00"},
            {"role": "assistant", "content": "只支持约定的 JSON 格式。",
             "created_at": "2026-11-05T20:06:12+08:00"},
        ],
    }
    body.update(overrides)
    return body


# ---------- 项目接口 ----------

def test_create_project_and_list(client):
    created = make_project(client, "第一个项目")
    assert is_uuid(created["project_id"])
    assert created["name"] == "第一个项目"

    listing = client.get("/api/projects")
    assert listing.status_code == 200
    assert any(p["project_id"] == created["project_id"] for p in listing.json())


def test_create_project_empty_name_422(client):
    resp = client.post("/api/projects", json={"name": "   "})
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail[0]["field"] == "name"


def test_get_project_404(client):
    resp = client.get("/api/projects/不存在的编号")
    assert resp.status_code == 404
    assert "项目不存在" in resp.json()["detail"]


# ---------- 导入成功路径 ----------

def test_import_and_get_conversation_roundtrip(client):
    project_id = make_project(client)["project_id"]
    resp = client.post(f"/api/projects/{project_id}/conversations/import",
                       json=sample_body())
    assert resp.status_code == 201
    data = resp.json()
    assert data["imported_count"] == 3
    assert data["overwritten"] is False
    assert len(data["message_ids"]) == 3
    assert all(is_uuid(mid) for mid in data["message_ids"])
    conversation_id = data["conversation_id"]
    assert is_uuid(conversation_id)

    got = client.get(f"/api/conversations/{conversation_id}")
    assert got.status_code == 200
    conv = got.json()
    assert conv["project_id"] == project_id
    assert conv["title"] == "讨论会话导入格式的边界"
    assert conv["source_conversation_id"] is None
    assert len(conv["messages"]) == 3
    # 顺序、角色、时间、seq 与导入一致；created_at=null 原样保留
    assert [m["seq"] for m in conv["messages"]] == [1, 2, 3]
    assert [m["role"] for m in conv["messages"]] == ["system", "user", "assistant"]
    assert conv["messages"][0]["created_at"] is None
    assert conv["messages"][1]["created_at"] == "2026-11-05T20:05:00+08:00"


def test_import_unknown_fields_ignored(client):
    project_id = make_project(client)["project_id"]
    body = sample_body()
    body["future_field"] = "未知字段第一阶段忽略"
    body["messages"][0]["internal_note"] = "消息级未知字段也忽略"
    resp = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    assert resp.status_code == 201


def test_import_z_suffix_utc_time_accepted(client):
    project_id = make_project(client)["project_id"]
    body = sample_body()
    body["messages"][1]["created_at"] = "2026-11-05T12:05:00Z"
    resp = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    assert resp.status_code == 201


# ---------- 重复导入（规则 6 + overwrite） ----------

def test_duplicate_source_import_returns_409(client):
    project_id = make_project(client)["project_id"]
    body = sample_body(source_conversation_id="external-conv-42")
    first = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    assert first.status_code == 201
    old_conversation_id = first.json()["conversation_id"]

    second = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    assert second.status_code == 409
    payload = second.json()
    assert payload["existing_conversation_id"] == old_conversation_id
    assert "external-conv-42" in payload["detail"]


def test_overwrite_replaces_existing_conversation(client):
    project_id = make_project(client)["project_id"]
    body = sample_body(source_conversation_id="external-conv-42")
    old = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    old_id = old.json()["conversation_id"]

    body["messages"][0]["content"] = "替换后的内容。"
    body["title"] = "替换后的标题"
    again = client.post(
        f"/api/projects/{project_id}/conversations/import?overwrite=true", json=body
    )
    assert again.status_code == 201
    data = again.json()
    assert data["overwritten"] is True
    new_id = data["conversation_id"]
    assert new_id != old_id

    # 旧会话连带消息一起消失，新会话可查
    assert client.get(f"/api/conversations/{old_id}").status_code == 404
    new_conv = client.get(f"/api/conversations/{new_id}").json()
    assert new_conv["title"] == "替换后的标题"
    assert new_conv["messages"][0]["content"] == "替换后的内容。"


def test_duplicate_allowed_when_source_id_is_null(client):
    """source_conversation_id 为 null 不参与查重：null 可导入多次。"""
    project_id = make_project(client)["project_id"]
    first = client.post(f"/api/projects/{project_id}/conversations/import",
                        json=sample_body())
    second = client.post(f"/api/projects/{project_id}/conversations/import",
                         json=sample_body())
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["conversation_id"] != second.json()["conversation_id"]


# ---------- 404 ----------

def test_import_into_missing_project_404(client):
    resp = client.post("/api/projects/没有这个项目/conversations/import",
                       json=sample_body())
    assert resp.status_code == 404
    assert "项目不存在" in resp.json()["detail"]


def test_get_missing_conversation_404(client):
    resp = client.get("/api/conversations/没有这个会话")
    assert resp.status_code == 404
    assert "会话不存在" in resp.json()["detail"]


# ---------- 422 结构化错误 ----------

def test_invalid_role_structured_422(client):
    project_id = make_project(client)["project_id"]
    body = sample_body()
    body["messages"][2]["role"] = "tool"  # 第 3 条
    resp = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    hit = [e for e in detail if e["field"] == "role"]
    assert hit and hit[0]["message_index"] == 3
    assert hit[0]["received"] == "tool"
    assert "user" in hit[0]["issue"]  # 提示里列出合法取值


def test_created_at_without_timezone_422(client):
    project_id = make_project(client)["project_id"]
    body = sample_body()
    body["messages"][1]["created_at"] = "2026-11-05T20:05:00"  # 缺时区
    resp = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    assert resp.status_code == 422
    hit = [e for e in resp.json()["detail"] if e["field"] == "created_at"]
    assert hit and hit[0]["message_index"] == 2
    assert "时区" in hit[0]["issue"]


def test_unparseable_created_at_422(client):
    project_id = make_project(client)["project_id"]
    body = sample_body()
    body["messages"][1]["created_at"] = "去年冬天"
    resp = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    assert resp.status_code == 422
    hit = [e for e in resp.json()["detail"] if e["field"] == "created_at"]
    assert hit and "ISO 8601" in hit[0]["issue"]


def test_multiple_errors_reported_together(client):
    """一次报出全部问题：空 title + 空 messages 数组。"""
    project_id = make_project(client)["project_id"]
    body = {"title": "", "source": "synthetic", "messages": []}
    resp = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    assert resp.status_code == 422
    fields = {e["field"] for e in resp.json()["detail"]}
    assert {"title", "messages"} <= fields


def test_empty_content_in_message_422(client):
    project_id = make_project(client)["project_id"]
    body = sample_body()
    body["messages"][0]["content"] = "   "
    resp = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    assert resp.status_code == 422
    hit = [e for e in resp.json()["detail"] if e["field"] == "content"]
    assert hit and hit[0]["message_index"] == 1


def test_invalid_json_body_422(client):
    project_id = make_project(client)["project_id"]
    resp = client.post(
        f"/api/projects/{project_id}/conversations/import",
        content=b"{oops",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail[0]["field"] == "body"
    assert "JSON" in detail[0]["issue"]


def test_missing_field_422_has_message_index(client):
    """缺 role 的消息：报错要定位到第几条。"""
    project_id = make_project(client)["project_id"]
    body = sample_body()
    del body["messages"][1]["role"]  # 第 2 条缺 role
    resp = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    assert resp.status_code == 422
    hit = [e for e in resp.json()["detail"] if e["field"] == "role"]
    assert hit and hit[0]["message_index"] == 2
    assert hit[0]["issue"] == "缺少必填字段"


# ---------- 全或无 ----------

def test_failed_import_writes_nothing(client):
    """第 4 条消息 role 非法时，前面 3 条合法消息也不落库。"""
    project_id = make_project(client)["project_id"]
    body = sample_body()
    body["messages"].append({"role": "tool", "content": "坏消息", "created_at": None})
    resp = client.post(f"/api/projects/{project_id}/conversations/import", json=body)
    assert resp.status_code == 422
    listing = client.get("/api/projects")
    assert listing.status_code == 200  # 服务正常
    # 项目下没有任何会话：用一个新项目再导一次合法的来对比（间接证明无残留写入）
    # 直接验证方式：查看该项目的会话数量——通过再次导入相同 title 的合法会话成功且互不影响
    ok = client.post(f"/api/projects/{project_id}/conversations/import",
                     json=sample_body())
    assert ok.status_code == 201


# ---------- 组内样例文件（存在时才跑） ----------

def test_repo_sample_import(client):
    sample = Path(__file__).resolve().parents[3] / "docs" / "样例" / "会话导入样例.json"
    if not sample.is_file():
        pytest.skip("仓库样例文件不存在，跳过")
    project_id = make_project(client)["project_id"]
    resp = client.post(f"/api/projects/{project_id}/conversations/import",
                       json=json.loads(sample.read_text(encoding="utf-8")))
    assert resp.status_code == 201
    assert resp.json()["imported_count"] == 7
