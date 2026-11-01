"""溯源服务：所有对外溯源调用都走这里。"""
from contracts import SourceRef, ResolvedSource, ContextWindow

# 第 1 部分就绪后，只改这一常量
DEEP_LINK_TEMPLATE = "/viewer/projects/{pid}/sessions/{sid}?msg={mid}"


class TraceService:
    def __init__(self, source):
        self.source = source

    def resolve(self, ref: SourceRef) -> ResolvedSource | None:
        msg = self.source.get_message(ref.message_id)
        if not msg:
            return None
        excerpt = msg.content
        available = True
        if ref.char_start is not None and ref.char_end is not None:
            excerpt = msg.content[ref.char_start:ref.char_end]
            if ref.snippet is not None and excerpt != ref.snippet:
                available = False
        return ResolvedSource(
            ref=ref, session_title=msg.session_title,
            message=msg, excerpt=excerpt, available=available,
        )

    def get_context(self, ref: SourceRef, before: int = 2, after: int = 2) -> ContextWindow | None:
        msg = self.source.get_message(ref.message_id)
        if not msg:
            return None
        window = self.source.get_window(msg.session_id, msg.seq, before, after)
        return ContextWindow(
            center=msg,
            before=[m for m in window if m.seq < msg.seq],
            after=[m for m in window if m.seq > msg.seq],
            session_id=msg.session_id,
        )

    def validate_many(self, refs: list[SourceRef]) -> dict[str, str]:
        result: dict[str, str] = {}
        for ref in refs:
            msg = self.source.get_message(ref.message_id)
            if not msg:
                result[ref.message_id] = "missing"
            elif (ref.char_start is not None and ref.char_end is not None
                  and ref.snippet is not None
                  and msg.content[ref.char_start:ref.char_end] != ref.snippet):
                result[ref.message_id] = "drifted"
            else:
                result[ref.message_id] = "ok"
        return result

    def deep_link(self, ref: SourceRef) -> str:
        link = DEEP_LINK_TEMPLATE.format(
            pid=ref.project_id, sid=ref.session_id, mid=ref.message_id,
        )
        if ref.char_start is not None and ref.char_end is not None:
            link += f"&hl={ref.char_start}-{ref.char_end}"
        return link