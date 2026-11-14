"""SQLite 存储层：建表、连接、路径配置。

数据库文件默认位于 backend/sessionhub.db，运行产生的数据库不提交进 Git
（仓库 .gitignore 已包含 *.db）。可用环境变量 SESSIONHUB_DB 覆盖路径，
测试即通过该变量把数据库指到临时目录。
"""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# sessionhub/backend/sessionhub.db（app/ 的上一级目录下）
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "sessionhub.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    conversation_id        TEXT PRIMARY KEY,
    project_id             TEXT NOT NULL REFERENCES projects(project_id),
    title                  TEXT NOT NULL,
    source                 TEXT NOT NULL,
    source_conversation_id TEXT,
    created_at             TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_conversations_project_source
    ON conversations (project_id, source_conversation_id);

CREATE TABLE IF NOT EXISTS messages (
    message_id      TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    seq             INTEGER NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    created_at      TEXT
);

CREATE INDEX IF NOT EXISTS ix_messages_conversation
    ON messages (conversation_id, seq);
"""


def database_path() -> Path:
    env = os.environ.get("SESSIONHUB_DB")
    return Path(env) if env else DEFAULT_DB_PATH


def utc_now() -> str:
    """带时区的 ISO 8601 当前时间（UTC）。"""
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    """打开一个已建表、已开启外键的 SQLite 连接。每次请求新建，用完即关。

    check_same_thread=False：FastAPI 的同步依赖与异步路由可能运行在
    不同线程，而本模块每个请求各自新建连接、请求内串行使用，跨线程
    复用是安全的（与组长 progressgate/backend/app/db.py 的做法一致）。
    """
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
