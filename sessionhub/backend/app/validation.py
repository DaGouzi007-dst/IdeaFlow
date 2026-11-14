"""导入格式校验：《会话导入与管理-格式说明》第 4 节规则的实现。

pydantic 负责"字段类型与必填"层面的检查（规则 2 的类型部分），
本模块负责语义层面的检查，并把全部问题以结构化明细返回，
供接口统一组装成 422 响应：

    {"detail": [{"message_index": 3, "field": "role", "issue": "...", "received": "..."}]}

message_index 为 1 起始的消息序号（与文档"第几条消息"的说法一致）；
非消息级问题不带 message_index。received 仅供人工排错，截断到 120 字符。
"""

from datetime import datetime

ROLES = ("user", "assistant", "system")


def make_error(field: str, issue: str, received=None, message_index: int | None = None) -> dict:
    detail: dict = {}
    if message_index is not None:
        detail["message_index"] = message_index
    detail["field"] = field
    detail["issue"] = issue
    if received is not None:
        detail["received"] = str(received)[:120]
    return detail


def is_valid_tz_iso8601(value: str) -> tuple[bool, str]:
    """校验是否为带时区的 ISO 8601 时间。返回 (是否合法, 失败原因)。"""
    text = value
    # 兼容以 Z 结尾的 UTC 写法（Python 3.10 及以下的 fromisoformat 不认 Z）
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return False, "created_at 不是合法的 ISO 8601 时间"
    if parsed.tzinfo is None:
        return False, "created_at 缺少时区信息（需带时区，如 2026-11-05T20:05:00+08:00）"
    return True, ""


def validate_import(body) -> list[dict]:
    """对已通过类型检查的导入请求体做语义校验，返回结构化错误明细。"""
    errors: list[dict] = []

    if not body.title.strip():
        errors.append(make_error("title", "title 必须是非空字符串"))
    if not body.source.strip():
        errors.append(make_error("source", "source 必须是非空字符串"))
    if body.source_conversation_id is not None and not body.source_conversation_id.strip():
        errors.append(make_error(
            "source_conversation_id",
            "source_conversation_id 必须是非空字符串或 null",
        ))
    if not body.messages:
        errors.append(make_error("messages", "messages 必须是非空数组（至少 1 条消息）"))

    for index, msg in enumerate(body.messages, start=1):
        if msg.role not in ROLES:
            errors.append(make_error(
                "role",
                "role 取值无效（允许：user、assistant、system）",
                received=msg.role,
                message_index=index,
            ))
        if not msg.content.strip():
            errors.append(make_error(
                "content",
                "content 必须是非空字符串",
                message_index=index,
            ))
        if msg.created_at is not None:
            ok, reason = is_valid_tz_iso8601(msg.created_at)
            if not ok:
                errors.append(make_error(
                    "created_at",
                    reason,
                    received=msg.created_at,
                    message_index=index,
                ))

    return errors
