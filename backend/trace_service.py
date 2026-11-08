"""溯源服务：所有对外溯源调用都走这里。"""
from contracts import SourceRef, ResolvedSource, ContextWindow, BatchResolveRequest

# 第 1 部分就绪后，只改这一常量
DEEP_LINK_TEMPLATE = "/viewer/projects/{pid}/sessions/{sid}?msg={mid}"


# trace_service.py 修改 resolve + 新增 resolve_batch

class TraceService:
    def __init__(self, source):
        self.source = source

    def resolve(self, ref: SourceRef) -> ResolvedSource | None:
        msg = self.source.get_message(ref.message_id)
        if not msg:
            return None
        # 没有偏移 → 整条消息
        if ref.char_start is None or ref.char_end is None:
            return ResolvedSource(
                ref=ref, session_title=msg.session_title,
                message=msg, excerpt=msg.content,
                available=True, precision="message_only",      # ←
            )
        excerpt = msg.content[ref.char_start:ref.char_end]
        ok = ref.snippet is None or excerpt == ref.snippet
        return ResolvedSource(
            ref=ref, session_title=msg.session_title,
            message=msg, excerpt=excerpt,
            available=ok, precision="exact" if ok else "message_only",  # ←
        )

    def resolve_batch(self, req: BatchResolveRequest) -> list[dict]:   # ← 新增
        """批量解析，可选带上下文。给第三部分列表页用，避免 N+1。"""
        out = []
        for ref in req.refs:
            r = self.resolve(ref)
            if r is None:
                out.append({"messageId": ref.message_id, "status": "missing"})
                continue
            item = {"messageId": ref.message_id, "status": "ok" if r.available else "drifted",
                    "resolved": r.model_dump(by_alias=True)}
            if req.include_context:
                ctx = self.get_context(ref, before=1, after=1)
                if ctx:
                    item["context"] = ctx.model_dump(by_alias=True)
            out.append(item)
        return out

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