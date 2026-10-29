"""临时项目/想法来源；团队模块完成后由正式数据接口替换。"""

import json
from pathlib import Path

from fastapi import HTTPException


FIXTURE = Path(__file__).resolve().parents[3] / "docs/样例/跨模块样例数据.json"


def demo_data() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def projects() -> list[dict]:
    return demo_data()["projects"]


def require_project(project_id: str) -> dict:
    project = next((p for p in projects() if p["project_id"] == project_id), None)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在（当前仅支持模拟项目）")
    return project


def ideas_for_project(project_id: str) -> list[dict]:
    require_project(project_id)
    return [idea for idea in demo_data()["ideas"] if idea["project_id"] == project_id]


def require_idea(idea_id: str) -> dict:
    idea = next((i for i in demo_data()["ideas"] if i["idea_id"] == idea_id), None)
    if idea is None:
        raise HTTPException(status_code=404, detail="想法不存在（当前仅支持模拟想法）")
    return idea


def idea_sources(idea_id: str) -> list[dict]:
    idea = require_idea(idea_id)
    data = demo_data()
    source_ids = idea.get("source_message_ids")
    if source_ids is None:
        source_ids = [idea["source_message_id"]] if idea.get("source_message_id") else []
    messages = {message["message_id"]: message for message in data["messages"]}
    conversations = {conversation["conversation_id"]: conversation for conversation in data["conversations"]}
    result = []
    for source_id in source_ids:
        message = messages.get(source_id)
        if message is None:
            continue
        conversation = conversations.get(message["conversation_id"])
        if conversation is None or conversation["project_id"] != idea["project_id"]:
            continue
        context = [m for m in data["messages"] if m["conversation_id"] == message["conversation_id"]]
        result.append({
            "message_id": source_id,
            "conversation_id": conversation["conversation_id"],
            "conversation_title": conversation["title"],
            "context": context,
        })
    return result
