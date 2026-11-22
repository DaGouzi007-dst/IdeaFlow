"""第一模块（会话导入与管理）→ MessageDTO 适配器。

两种取数方式：
1. load_from_part1_db(path)：直读 sessionhub.db（第一模块当前未提供"按项目列会话"接口，先用这个）
2. conversations_to_dtos(convs)：接收 GET /api/conversations/{id} 形状的会话字典
"""
import hashlib
import sqlite3
from contracts import MessageDTO


def conversations_to_dtos(convs: list[dict]) -> list[MessageDTO]:
    out: list[MessageDTO] = []
    for conv in convs:
        for m in conv["messages"]:
            content = m["content"]
            out.append(MessageDTO(
                id=m["message_id"],                     # 真实 UUID，不再自造
                session_id=conv["conversation_id"],
                session_title=conv["title"],
                project_id=conv["project_id"],
                seq=m["seq"],
                role=m["role"],
                content=content,
                created_at=m.get("created_at") or "",   # 第一模块允许 null
                tool=conv["source"],                    # 语义为"导入渠道"，见 P2-10
                content_hash=hashlib.sha1(content.encode("utf-8")).hexdigest(),
            ))
    return out


def load_from_part1_db(db_path: str, project_id: str | None = None) -> list[MessageDTO]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    sql = ("SELECT c.conversation_id, c.project_id, c.title, c.source, "
           "m.message_id, m.seq, m.role, m.content, m.created_at "
           "FROM conversations c JOIN messages m ON m.conversation_id = c.conversation_id")
    params: tuple = ()
    if project_id:
        sql += " WHERE c.project_id = ?"
        params = (project_id,)
    sql += " ORDER BY c.conversation_id, m.seq"
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    convs: dict[str, dict] = {}
    for r in rows:
        conv = convs.setdefault(r["conversation_id"], {
            "conversation_id": r["conversation_id"],
            "project_id": r["project_id"],
            "title": r["title"],
            "source": r["source"],
            "messages": [],
        })
        conv["messages"].append({
            "message_id": r["message_id"], "seq": r["seq"],
            "role": r["role"], "content": r["content"],
            "created_at": r["created_at"],
        })
    return conversations_to_dtos(list(convs.values()))