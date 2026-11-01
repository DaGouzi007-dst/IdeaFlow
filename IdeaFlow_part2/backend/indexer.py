"""索引器：本地业务表 + FTS5。索引表可整体重建，删除不影响业务数据。"""
import sqlite3
import jieba
from contracts import MessageDTO

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
  id TEXT PRIMARY KEY, title TEXT, project_id TEXT, tool TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS messages(
  id TEXT PRIMARY KEY, session_id TEXT, seq INT, role TEXT,
  content TEXT, created_at TEXT, content_hash TEXT);
CREATE TABLE IF NOT EXISTS search_doc(
  message_id TEXT PRIMARY KEY, session_id TEXT, session_title TEXT,
  project_id TEXT, seq INT, role TEXT, tool TEXT, created_at TEXT,
  content TEXT, tokens TEXT, content_hash TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5(tokens);
CREATE INDEX IF NOT EXISTS idx_doc_proj ON search_doc(project_id);
CREATE INDEX IF NOT EXISTS idx_doc_sess ON search_doc(session_id);
"""


def tokenize(text: str) -> str:
    return " ".join(w for w in jieba.lcut(text) if w.strip())


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


class Indexer:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def rebuild(self, messages: list[MessageDTO]) -> int:
        self.conn.execute("DELETE FROM search_doc")
        self.conn.execute("DELETE FROM search_fts")
        # 业务表：幂等 upsert
        self.conn.executemany(
            "INSERT OR REPLACE INTO sessions VALUES(?,?,?,?,?)",
            list({(m.session_id, m.session_title, m.project_id, m.tool, m.created_at)
                  for m in messages}),
        )
        self.conn.executemany(
            "INSERT OR REPLACE INTO messages VALUES(?,?,?,?,?,?,?)",
            [(m.id, m.session_id, m.seq, m.role, m.content, m.created_at, m.content_hash)
             for m in messages],
        )
        # 索引表：逐条插入，保证 rowid 与 FTS rowid 对齐
        for m in messages:
            self.conn.execute(
                "INSERT INTO search_doc VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (m.id, m.session_id, m.session_title, m.project_id, m.seq,
                 m.role, m.tool, m.created_at, m.content,
                 tokenize(m.content), m.content_hash),
            )
            rowid = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            self.conn.execute(
                "INSERT INTO search_fts(rowid, tokens) VALUES(?,?)",
                (rowid, tokenize(m.content)),
            )
        self.conn.commit()
        return len(messages)