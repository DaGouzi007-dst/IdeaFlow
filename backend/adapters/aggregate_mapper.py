# backend/adapters/__init__.py  （空文件）
# backend/adapters/aggregate_mapper.py
"""第一部分聚合样例（projects/conversations/messages）→ MessageDTO 映射。"""
import hashlib
from contracts import MessageDTO


class AggregateMapper:
    """把第一部分导出的三表平铺 JSON 转成第二部分的扁平消息列表。

    字段映射：
      conversation_id  → session_id
      title            → session_title
      source           → tool
      （数组顺序）      → seq
      （自生成）        → id = f"{conversation_id}-m{seq}"
      （自算）          → content_hash = sha1(content)
    """

    def to_dtos(self, data: dict) -> list[MessageDTO]:
        projects = {p["project_id"]: p for p in data.get("projects", [])}
        convs = {c["conversation_id"]: c for c in data.get("conversations", [])}

        by_conv: dict[str, list[dict]] = {}
        for m in data.get("messages", []):
            by_conv.setdefault(m["conversation_id"], []).append(m)

        out: list[MessageDTO] = []
        for conv_id, msgs in by_conv.items():
            conv = convs.get(conv_id, {})
            project_id = conv.get("project_id", "")
            if project_id not in projects:
                project_id = project_id or "unknown"
            for seq, raw in enumerate(msgs, start=1):
                content = raw["content"]
                out.append(MessageDTO(
                    id=f"{conv_id}-m{seq}",
                    session_id=conv_id,
                    session_title=conv.get("title", ""),
                    project_id=project_id,
                    seq=seq,
                    role=raw["role"],
                    content=content,
                    created_at=raw.get("created_at") or "",
                    tool=conv.get("source", ""),
                    content_hash=hashlib.sha1(content.encode("utf-8")).hexdigest(),
                ))
        return out