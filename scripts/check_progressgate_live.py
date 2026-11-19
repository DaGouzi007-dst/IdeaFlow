"""用合成数据检查第一、三、四模块的 HTTP 联调；会在指定测试服务中创建记录。"""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request(base, path, method="GET", body=None, expected=200):
    payload = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = Request(base.rstrip("/") + path, data=payload, method=method, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=10) as response:
            status, raw = response.status, response.read()
    except HTTPError as exc:
        status, raw = exc.code, exc.read()
    result = json.loads(raw)
    if status != expected:
        raise RuntimeError(f"{method} {path}: 预期 {expected}，实际 {status}，{result}")
    return result


def verify(projects, ideas, progressgate):
    if request(progressgate, "/api/health")["reference_data"] != "live":
        raise RuntimeError("第四模块须以 live 模式运行；未创建测试数据")
    project = request(projects, "/api/projects", "POST", {"name": "第四周合成联调项目"}, 201)
    pid = project["project_id"]
    content = "请把方案决定和任务状态分开记录。"
    imported = request(projects, f"/api/projects/{pid}/conversations/import", "POST", {
        "title": "第四周合成联调会话", "source": "synthetic", "source_conversation_id": None,
        "messages": [{"role": "user", "content": content, "created_at": None},
                     {"role": "assistant", "content": "采纳后再创建任务，并保留进展记录。", "created_at": None}],
    }, 201)
    mid = imported["message_ids"][0]
    cid = imported["conversation_id"]
    idea = request(ideas, "/api/ideas", "POST", {"project_id": pid, "title": "把方案落成任务", "summary": content}, 201)
    iid = idea["idea_id"]
    request(ideas, f"/api/ideas/{iid}/sources", "POST", {
        "message_id": mid, "quote": content,
        "source_ref": json.dumps({"projectId": pid, "sessionId": cid, "messageId": mid}),
    }, 201)
    project_ideas = request(progressgate, f"/api/projects/{pid}/ideas")
    assert any(row["idea_id"] == iid and row["content"] == content for row in project_ideas)
    task_path = f"/api/projects/{pid}/tasks"
    body = {"title": "第四周联调验证任务", "idea_id": iid, "assignee": "演示负责人"}
    request(progressgate, task_path, "POST", body, 422)
    request(progressgate, f"/api/ideas/{iid}/decision", "PUT", {"status": "adopted", "reason": "合成联调验证"})
    task = request(progressgate, task_path, "POST", body, 201)
    tid = task["task_id"]
    path = f"/api/tasks/{tid}"
    request(progressgate, path, "PATCH", {"status": "blocked"}, 422)
    request(progressgate, path, "PATCH", {"status": "blocked", "block_reason": "验证阻塞记录"})
    request(progressgate, path, "PATCH", {"status": "in_progress", "resolution": "合成问题已处理"})
    request(progressgate, path, "PATCH", {"status": "done"}, 422)
    request(progressgate, path, "PATCH", {"status": "done", "result": "第一、三、四模块验证完成"})
    saved = request(progressgate, path)
    assert saved["project_id"] == pid and saved["idea_id"] == iid and saved["status"] == "done"
    assert len(request(progressgate, path + "/events")) == 4
    sources = request(progressgate, f"/api/ideas/{iid}/sources")
    assert sources[0]["status"] == "available" and sources[0]["message_id"] == mid
    assert any(row["message_id"] == mid and row["content"] == content for row in sources[0]["context"])
    return {"passed": True, "scope": "第一、三、四模块 HTTP 联调，未覆盖第二模块检索", "project_id": pid,
            "conversation_id": cid, "message_id": mid, "idea_id": iid, "task_id": tid}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects-url", default="http://127.0.0.1:8001")
    parser.add_argument("--ideas-url", default="http://127.0.0.1:8003")
    parser.add_argument("--progressgate-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    try:
        result = verify(args.projects_url, args.ideas_url, args.progressgate_url)
    except (AssertionError, RuntimeError, URLError, ValueError, KeyError, OSError) as exc:
        print(f"联调验证失败：{exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
