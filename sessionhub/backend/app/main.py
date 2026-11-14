"""IdeaFlow 第一模块（会话导入与管理）—— FastAPI 接口实现（第二阶段）。

对齐《开工方案与接口约定（讨论稿）》第五节中会话管理模块的三个接口，
并按组长第三周接口对接清单补充项目列表/详情查询：

    POST /api/projects                                     创建项目
    GET  /api/projects                                     项目列表（对接清单"待确认项目列表"项）
    GET  /api/projects/{project_id}                        项目详情（对接清单"项目不存在时的错误行为"项）
    POST /api/projects/{project_id}/conversations/import   导入本组 JSON 格式会话
    GET  /api/conversations/{conversation_id}              查看会话和消息

错误返回（格式说明第 5 节的"细化"版，detail 为字符串或结构化数组）：
    404  {"detail": "项目不存在：{id}"}
    409  {"detail": "...", "existing_conversation_id": "..."}
    422  {"detail": [{"message_index": 3, "field": "role", "issue": "...", "received": "..."}]}

导入写入采用"全或无"事务：校验全部通过后一次提交，任何失败不落库。

运行（在 sessionhub/backend 目录下）：
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8001
启动后访问 http://127.0.0.1:8001/docs 查看接口说明。
"""

import json
import sqlite3
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .db import connect, utc_now
from .models import ImportInput, ProjectInput
from .validation import make_error, validate_import

app = FastAPI(
    title="IdeaFlow 会话导入与管理 API",
    description="第一模块：项目、会话、消息的创建与查看，以及本组约定 JSON 格式的导入。",
    version="0.2.0",
)

# 组内前端（Vite 默认 5173 端口）跨域调用需要；本地开发阶段先放开
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# pydantic 报错类型 → 中文说明；未命中时退回原始 msg
ISSUE_TEXT = {
    "missing": "缺少必填字段",
    "string_type": "必须是字符串",
    "int_type": "必须是整数",
    "list_type": "必须是数组",
    "model_type": "必须是 JSON 对象",
    "model_attributes_type": "必须是 JSON 对象",
    "json_invalid": "请求体不是合法 JSON",
}


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def loc_to_detail(err: dict) -> dict:
    """把 pydantic 校验错误转成本模块统一的结构化明细。

    pydantic 的 loc 形如 ("body", "messages", 1, "role")，其中整数是
    数组下标（0 起始）。转换规则：第一个整数作为 message_index（加 1
    变成文档口径的"第几条"），紧跟在整数前的数组容器名（如 messages）
    不进入 field，其余名称段以点号拼接为 field。
    """
    loc = [p for p in err.get("loc", ()) if p != "body"]
    message_index = None
    container_name = None
    parts: list[str] = []
    for i, part in enumerate(loc):
        if isinstance(part, int):
            if message_index is None:
                message_index = part + 1
        elif i + 1 < len(loc) and isinstance(loc[i + 1], int):
            container_name = str(part)  # 数组容器名（如 messages），暂存备用
        else:
            parts.append(str(part))
    field = ".".join(parts) if parts else (container_name or "body")
    issue = ISSUE_TEXT.get(err.get("type"), str(err.get("msg", "字段不合法")))
    return make_error(field, issue, received=err.get("input"), message_index=message_index)


@app.exception_handler(RequestValidationError)
async def structured_validation_handler(request: Request, exc: RequestValidationError):
    """所有请求体类型/必填错误统一转成结构化明细（422）。"""
    return JSONResponse(
        status_code=422,
        content={"detail": [loc_to_detail(e) for e in exc.errors()]},
    )


@app.post("/api/projects", status_code=201)
def create_project(body: ProjectInput, db=Depends(get_db)):
    """创建项目。项目是导入的前提（校验规则第 1 条）。"""
    if not body.name.strip():
        return JSONResponse(
            status_code=422,
            content={"detail": [{"field": "name", "issue": "name 必须是非空字符串"}]},
        )
    project_id = str(uuid4())
    db.execute(
        "INSERT INTO projects (project_id, name, created_at) VALUES (?, ?, ?)",
        (project_id, body.name, utc_now()),
    )
    db.commit()
    return {"project_id": project_id, "name": body.name}


@app.get("/api/projects")
def list_projects(db=Depends(get_db)):
    """项目列表。组长对接清单'待确认项目列表及查询接口'项。"""
    rows = db.execute(
        "SELECT project_id, name FROM projects ORDER BY created_at, project_id"
    ).fetchall()
    return [{"project_id": row["project_id"], "name": row["name"]} for row in rows]


@app.get("/api/projects/{project_id}")
def get_project(project_id: str, db=Depends(get_db)):
    """项目详情；项目不存在时按约定返回 404。"""
    row = db.execute(
        "SELECT project_id, name FROM projects WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"项目不存在：{project_id}")
    return {"project_id": row["project_id"], "name": row["name"]}


@app.post("/api/projects/{project_id}/conversations/import", status_code=201)
async def import_conversation(
    project_id: str,
    request: Request,
    overwrite: bool = False,
    db: sqlite3.Connection = Depends(get_db),
):
    """导入本组约定 JSON 格式的会话（校验规则 1-6 全在这里按序执行）。

    同一项目下 source_conversation_id 重复时返回 409 并附已有会话编号；
    ?overwrite=true 时原子替换旧会话（删除旧的会话和消息，写入新的）。
    """
    # 规则 1：项目必须存在（文档约定先查项目再解析请求体）
    project = db.execute(
        "SELECT project_id FROM projects WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    if project is None:
        raise HTTPException(status_code=404, detail=f"项目不存在：{project_id}")

    # 规则 2：请求体是合法 JSON
    try:
        raw = json.loads(await request.body())
    except json.JSONDecodeError as exc:
        return JSONResponse(
            status_code=422,
            content={"detail": [{
                "field": "body",
                "issue": f"请求体不是合法 JSON：第 {exc.lineno} 行第 {exc.colno} 列解析失败",
            }]},
        )

    # 规则 2（续）：字段类型正确（pydantic）；规则 3-5：语义校验
    try:
        body = ImportInput.model_validate(raw)
    except ValidationError as exc:
        return JSONResponse(
            status_code=422,
            content={"detail": [loc_to_detail(e) for e in exc.errors()]},
        )
    errors = validate_import(body)
    if errors:
        return JSONResponse(status_code=422, content={"detail": errors})

    # 规则 6：同一项目下同 source_conversation_id 视为重复导入
    existing = None
    if body.source_conversation_id is not None:
        existing = db.execute(
            "SELECT conversation_id FROM conversations "
            "WHERE project_id = ? AND source_conversation_id = ?",
            (project_id, body.source_conversation_id),
        ).fetchone()

    conversation_id = str(uuid4())
    message_ids = [str(uuid4()) for _ in body.messages]
    overwritten = False

    try:  # 全或无：以下所有写库要么全部成功提交，要么全部回滚
        if existing is not None:
            if not overwrite:
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": (
                            f"同来源会话已存在（source_conversation_id="
                            f"{body.source_conversation_id}），如需替换请加 ?overwrite=true"
                        ),
                        "existing_conversation_id": existing["conversation_id"],
                    },
                )
            db.execute(
                "DELETE FROM conversations WHERE conversation_id = ?",
                (existing["conversation_id"],),  # 级联删除其消息
            )
            overwritten = True

        db.execute(
            "INSERT INTO conversations "
            "(conversation_id, project_id, title, source, source_conversation_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (conversation_id, project_id, body.title, body.source,
             body.source_conversation_id, utc_now()),
        )
        for seq, (message_id, msg) in enumerate(zip(message_ids, body.messages), start=1):
            db.execute(
                "INSERT INTO messages "
                "(message_id, conversation_id, seq, role, content, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (message_id, conversation_id, seq, msg.role, msg.content, msg.created_at),
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "project_id": project_id,
        "conversation_id": conversation_id,
        "message_ids": message_ids,
        "imported_count": len(message_ids),
        "overwritten": overwritten,
    }


@app.get("/api/conversations/{conversation_id}")
def get_conversation(conversation_id: str, db=Depends(get_db)):
    """查看会话和消息。messages 按导入顺序排列，seq 从 1 起始。

    seq 是给检索/溯源模块的对齐信息（第二模块契约里有 seq 字段），
    message_id 始终是导入时生成的 UUID，全链路沿用同一编号。
    """
    conv = db.execute(
        "SELECT conversation_id, project_id, title, source, source_conversation_id "
        "FROM conversations WHERE conversation_id = ?",
        (conversation_id,),
    ).fetchone()
    if conv is None:
        raise HTTPException(status_code=404, detail=f"会话不存在：{conversation_id}")

    messages = db.execute(
        "SELECT message_id, seq, role, content, created_at "
        "FROM messages WHERE conversation_id = ? ORDER BY seq",
        (conversation_id,),
    ).fetchall()
    return {
        "conversation_id": conv["conversation_id"],
        "project_id": conv["project_id"],
        "title": conv["title"],
        "source": conv["source"],
        "source_conversation_id": conv["source_conversation_id"],
        "messages": [
            {
                "message_id": m["message_id"],
                "seq": m["seq"],
                "role": m["role"],
                "content": m["content"],
                "created_at": m["created_at"],
            }
            for m in messages
        ],
    }
