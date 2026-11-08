"""契约层：唯一同步点。只增不改，变更走三方评审。"""
from typing import Protocol
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Base(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, from_attributes=True
    )


class MessageDTO(Base):
    id: str
    session_id: str
    session_title: str
    project_id: str
    seq: int
    role: str
    content: str
    created_at: str
    tool: str
    content_hash: str | None = None


class SourceRef(Base):
    project_id: str
    session_id: str
    message_id: str
    char_start: int | None = None      # 码点偏移
    char_end: int | None = None
    snippet: str | None = None


class SearchQuery(Base):
    q: str
    project_id: str | None = None
    session_ids: list[str] | None = None
    tools: list[str] | None = None
    roles: list[str] | None = None
    page: int = 1
    page_size: int = 20
    mode: str = "keyword"


class SearchHit(Base):
    ref: SourceRef
    session_title: str
    tool: str
    role: str
    created_at: str
    snippet: str
    highlights: list[tuple[int, int]]
    score: float
    matched_by: str = "keyword"


class SearchResult(Base):
    hits: list[SearchHit]
    total: int
    page: int
    took_ms: int


# contracts.py 修改 ResolvedSource，新增 BatchResolveRequest

class ResolvedSource(Base):
    ref: SourceRef
    session_title: str
    message: MessageDTO
    excerpt: str
    available: bool
    precision: str = "exact"      # ← 新增：exact / message_only
    # exact = 有 charStart/End 且校验通过；message_only = 只定位到整条消息


class BatchResolveRequest(Base):
    refs: list[SourceRef]
    include_context: bool = False   # ← 新增：为 True 时附带前后各 1 条


class ContextWindow(Base):
    center: MessageDTO
    before: list[MessageDTO]
    after: list[MessageDTO]
    session_id: str


# ---------- 端口 ----------
class MessageSourcePort(Protocol):
    def get_message(self, message_id: str) -> MessageDTO | None: ...
    def get_window(self, session_id: str, seq: int, before: int, after: int) -> list[MessageDTO]: ...
    def get_session_meta(self, session_id: str) -> dict | None: ...
    def list_all_messages(self) -> list[MessageDTO]: ...


class Retriever(Protocol):
    def search(self, q: SearchQuery, limit: int) -> list[tuple[str, float]]: ...