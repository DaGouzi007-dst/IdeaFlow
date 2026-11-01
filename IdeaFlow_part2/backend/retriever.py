"""关键词检索器：jieba 切词 → FTS5 MATCH（AND 语义）→ bm25 排序。"""
import re
import sqlite3
import jieba
from contracts import SearchQuery


def build_match(q: str) -> str:
    words = [w for w in jieba.lcut(q) if re.search(r"\w", w)]
    if not words:
        return ""
    return " AND ".join(f'"{w.replace(chr(34), chr(34) * 2)}"' for w in words)


class KeywordRetriever:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def search(self, q: SearchQuery, limit: int) -> list[tuple[str, float]]:
        expr = build_match(q.q)
        if not expr:
            return []
        sql = (
            "SELECT d.message_id, bm25(search_fts) AS s "
            "FROM search_fts JOIN search_doc d ON d.rowid = search_fts.rowid "
            "WHERE search_fts MATCH ?"
        )
        params: list = [expr]
        if q.project_id:
            sql += " AND d.project_id = ?"; params.append(q.project_id)
        if q.session_ids:
            sql += f" AND d.session_id IN ({','.join('?' * len(q.session_ids))})"
            params += q.session_ids
        if q.tools:
            sql += f" AND d.tool IN ({','.join('?' * len(q.tools))})"
            params += q.tools
        if q.roles:
            sql += f" AND d.role IN ({','.join('?' * len(q.roles))})"
            params += q.roles
        sql += " ORDER BY s LIMIT ?"; params.append(limit)
        # bm25 越小越相关，取负让 score 越大越相关
        return [(mid, -s) for mid, s in self.conn.execute(sql, params)]