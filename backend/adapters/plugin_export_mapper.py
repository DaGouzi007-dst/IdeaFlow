"""AI-Chat-Toolkit 导出 JSON → MessageDTO（仅用于第二部分联调测试）。

正式链路应走第一模块导入（由它生成 UUID）；此适配器直接灌第二部分，
用于在没有第一模块时快速验证检索/高亮/溯源。
"""
import hashlib
from contracts import MessageDTO

ROLES = {"user", "assistant", "system"}



def _conversation_key(d: dict) -> str:
    tail = (d.get("url") or "").rstrip("/").split("/")[-1]
    return tail or hashlib.sha1(d["title"].encode("utf-8")).hexdigest()[:12]


def to_dtos(d: dict, project_id: str = "imported") -> list[MessageDTO]:
    conv_id = _conversation_key(d)
    out: list[MessageDTO] = []
    for seq, m in enumerate(d["messages"], start=1):
        content = m["content"]
        role = m["role"] if m["role"] in ROLES else "system"
        out.append(MessageDTO(
            id=f"{conv_id}-m{seq}",                 # 测试用合成 id；正式由第一模块生成 UUID
            session_id=conv_id,
            session_title=d["title"],
            project_id=project_id,
            seq=seq,
            role=role,
            content=content,
            created_at="", 
            tool=d.get("platform", "unknown"),      # ← platform → tool，筛选可用
            content_hash=hashlib.sha1(content.encode("utf-8")).hexdigest(),
        ))
    return out