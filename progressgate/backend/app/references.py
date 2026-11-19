"""Read-only access to projects, ideas and message sources, with explicit demo/live modes."""

import json
import os
from functools import lru_cache
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import urlopen
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from . import demo


class ProjectRef(BaseModel):
    project_id: UUID
    name: str


class IdeaRef(BaseModel):
    idea_id: UUID
    project_id: UUID
    title: str
    summary: str | None = None


class ReferenceData(Protocol):
    mode: str

    def projects(self) -> list[dict]: ...
    def require_project(self, project_id: str) -> dict: ...
    def ideas_for_project(self, project_id: str) -> list[dict]: ...
    def require_idea(self, idea_id: str) -> dict: ...
    def idea_sources(self, idea_id: str) -> list[dict]: ...


class DemoReferences:
    mode = "demo"

    projects = staticmethod(demo.projects)
    require_project = staticmethod(demo.require_project)
    ideas_for_project = staticmethod(demo.ideas_for_project)
    require_idea = staticmethod(demo.require_idea)
    idea_sources = staticmethod(demo.idea_sources)


class LiveReferences:
    mode = "live"

    def __init__(self, projects_url: str, ideas_url: str):
        self.urls = {"项目": projects_url.rstrip("/"), "想法": ideas_url.rstrip("/")}
        for url in self.urls.values():
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.query or parsed.fragment:
                raise ValueError("联调服务地址必须是 http(s) 基础地址，不能含查询参数或片段")

    def _get(self, service: str, path: str, *, missing_ok: bool = False):
        try:
            with urlopen(self.urls[service] + path, timeout=5) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code == 404 and missing_ok:
                return None
            raise HTTPException(502, f"{service}服务返回异常，请检查接口和服务状态") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise HTTPException(503, f"{service}服务暂不可用，请检查联调服务是否启动") from exc
        except (ValueError, UnicodeError) as exc:
            raise HTTPException(502, f"{service}服务返回格式不正确") from exc

    @staticmethod
    def _project(raw) -> dict:
        try:
            return ProjectRef.model_validate(raw).model_dump(mode="json")
        except ValidationError as exc:
            raise HTTPException(502, "项目服务返回格式不正确") from exc

    @staticmethod
    def _idea(raw) -> dict:
        try:
            idea = IdeaRef.model_validate(raw).model_dump(mode="json")
        except ValidationError as exc:
            raise HTTPException(502, "想法服务返回格式不正确，请核对项目和想法编号") from exc
        idea["content"] = idea.pop("summary") or ""
        return idea

    def projects(self) -> list[dict]:
        rows = self._get("项目", "/api/projects")
        if not isinstance(rows, list):
            raise HTTPException(502, "项目列表格式不正确")
        return [self._project(row) for row in rows]

    def require_project(self, project_id: str) -> dict:
        row = self._get("项目", f"/api/projects/{quote(project_id, safe='')}", missing_ok=True)
        if row is None:
            raise HTTPException(404, "项目不存在")
        project = self._project(row)
        if project["project_id"] != project_id:
            raise HTTPException(502, "项目服务返回的编号与请求不一致")
        return project

    def ideas_for_project(self, project_id: str) -> list[dict]:
        self.require_project(project_id)
        rows = self._get("想法", "/api/ideas")
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise HTTPException(502, "想法列表格式不正确")
        # Part 3 currently has no project filter; never mix ideas across projects.
        return [self._idea(row) for row in rows if row.get("project_id") == project_id]

    def require_idea(self, idea_id: str) -> dict:
        row = self._get("想法", f"/api/ideas/{quote(idea_id, safe='')}", missing_ok=True)
        if row is None:
            raise HTTPException(404, "想法不存在")
        idea = self._idea(row)
        if idea["idea_id"] != idea_id:
            raise HTTPException(502, "想法服务返回的编号与请求不一致")
        self.require_project(idea["project_id"])
        return idea

    def idea_sources(self, idea_id: str) -> list[dict]:
        idea = self.require_idea(idea_id)
        rows = self._get("想法", f"/api/ideas/{quote(idea_id, safe='')}/sources")
        if not isinstance(rows, list):
            raise HTTPException(502, "想法出处列表格式不正确")
        return [self._source(idea, row) for row in rows]

    def _source(self, idea: dict, row) -> dict:
        if not isinstance(row, dict) or not isinstance(row.get("message_id"), str):
            raise HTTPException(502, "想法出处格式不正确")
        result = {"message_id": row["message_id"], "conversation_id": None,
                  "conversation_title": None, "context": [], "quote": row.get("quote"), "status": "unresolved"}
        raw_ref = row.get("source_ref")
        if not raw_ref:
            return result
        try:
            ref = json.loads(raw_ref) if isinstance(raw_ref, str) else raw_ref
            if not isinstance(ref, dict):
                raise ValueError("invalid source ref")
            project_id = ref.get("projectId", ref.get("project_id"))
            message_id = ref.get("messageId", ref.get("message_id"))
            conversation_id = ref.get("sessionId", ref.get("session_id"))
            if (project_id is not None and project_id != idea["project_id"]) or (message_id is not None and message_id != row["message_id"]):
                raise ValueError("inconsistent reference")
            if not project_id or not message_id or not conversation_id:
                return result
            conversation_id = str(UUID(conversation_id))
        except (ValueError, TypeError, AttributeError):
            result["status"] = "invalid"
            return result
        result["conversation_id"] = conversation_id
        conversation = self._get("项目", f"/api/conversations/{conversation_id}", missing_ok=True)
        if conversation is None:
            result["status"] = "missing"
            return result
        if not isinstance(conversation, dict) or not isinstance(conversation.get("messages"), list):
            raise HTTPException(502, "会话服务返回格式不正确")
        if conversation.get("project_id") != idea["project_id"] or conversation.get("conversation_id") != conversation_id:
            result["status"] = "invalid"
            return result
        messages = conversation["messages"]
        if any(not isinstance(m, dict) or not all(k in m for k in ("message_id", "role", "content")) for m in messages):
            raise HTTPException(502, "会话消息格式不正确")
        if not any(m["message_id"] == row["message_id"] for m in messages):
            result["status"] = "missing"
            return result
        result.update(status="available", conversation_title=conversation.get("title", "来源会话"), context=messages)
        return result


@lru_cache(maxsize=1)
def get_reference_data() -> ReferenceData:
    mode = os.environ.get("PROGRESSGATE_REFERENCE_MODE", "demo")
    if mode == "demo":
        return DemoReferences()
    if mode == "live":
        return LiveReferences(os.environ.get("PROGRESSGATE_PROJECTS_URL", "http://127.0.0.1:8001"),
                              os.environ.get("PROGRESSGATE_IDEAS_URL", "http://127.0.0.1:8003"))
    raise ValueError("PROGRESSGATE_REFERENCE_MODE 只能为 demo 或 live")
