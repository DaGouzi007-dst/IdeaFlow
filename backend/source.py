"""LocalSource：MessageSourcePort 实现，读本地 SQLite。"""
import hashlib
import json
import sqlite3
from contracts import MessageDTO


class LocalSource:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    _COLS = "id, session_id, seq, role, content, created_at, content_hash"

    def _to_dto(self, row) -> MessageDTO:
        mid, sid, seq, role, content, created, c_hash = row
        meta = self.conn.execute(
            "SELECT title, project_id, tool FROM sessions WHERE id=?", (sid,)
        ).fetchone() or ("", "", "")
        return MessageDTO(
            id=mid, session_id=sid, session_title=meta[0], project_id=meta[1],
            seq=seq, role=role, content=content, created_at=created,
            tool=meta[2], content_hash=c_hash,
        )

    def get_message(self, message_id: str) -> MessageDTO | None:
        row = self.conn.execute(
            f"SELECT {self._COLS} FROM messages WHERE id=?", (message_id,)
        ).fetchone()
        return self._to_dto(row) if row else None

        # source.py 的 get_window 里加兜底
    def get_window(self, session_id: str, seq: int | None,
                before: int = 2, after: int = 2) -> list[MessageDTO]:
        if seq is None:
            # 没有 seq 时退化为取会话首尾各 N 条，不做邻域
            rows = self.conn.execute(
                f"SELECT {self._COLS} FROM messages WHERE session_id=? "
                "ORDER BY seq LIMIT ?", (session_id, before + after + 1),
            ).fetchall()
        else:
            rows = self.conn.execute(
                f"SELECT {self._COLS} FROM messages "
                "WHERE session_id=? AND seq BETWEEN ? AND ? ORDER BY seq",
                (session_id, seq - before, seq + after),
            ).fetchall()
        return [self._to_dto(r) for r in rows]


    def get_session_meta(self, session_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT title, project_id, tool FROM sessions WHERE id=?", (session_id,)
        ).fetchone()
        return {"title": row[0], "projectId": row[1], "tool": row[2]} if row else None

    def list_all_messages(self) -> list[MessageDTO]:
        rows = self.conn.execute(
            f"SELECT {self._COLS} FROM messages ORDER BY session_id, seq"
        ).fetchall()
        return [self._to_dto(r) for r in rows]


def load_from_json(conn: sqlite3.Connection, path: str) -> list[MessageDTO]:
    """从 fixture JSON 转 MessageDTO 列表，供 Indexer.rebuild 使用。"""
    out: list[MessageDTO] = []
    with open(path, encoding="utf-8") as f:
        for s in json.load(f):
            for i, m in enumerate(s["messages"], start=1):
                content = m["content"].strip("\n")
                out.append(MessageDTO(
                    id=f"{s['sessionId']}-m{i}",
                    session_id=s["sessionId"],
                    session_title=s["sessionTitle"],
                    project_id=s["projectId"],
                    seq=i, role=m["role"], content=content,
                    created_at=m.get("createdAt", s.get("createdAt", "")),
                    tool=s["tool"],
                    content_hash=hashlib.sha1(content.encode("utf-8")).hexdigest(),
                ))
    return out