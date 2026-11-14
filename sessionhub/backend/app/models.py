"""请求体模型（pydantic v2）。

注意：不做 str_strip_whitespace——消息内容必须原样保存，保证检索与
溯源拿到的原文和导入时逐字一致；"是否为空"的判断在 validation.py 中
用 strip() 语义完成，同样不改动存储内容。
"""

from pydantic import BaseModel


class ProjectInput(BaseModel):
    """POST /api/projects 请求体。"""

    name: str


class MessageInput(BaseModel):
    """导入请求体中 messages 数组的元素。"""

    role: str
    content: str
    created_at: str | None = None


class ImportInput(BaseModel):
    """POST /api/projects/{project_id}/conversations/import 请求体。

    未知字段按《会话导入与管理-格式说明》第 4 节直接忽略，
    因此不设置 extra="forbid"。
    """

    title: str
    source: str
    source_conversation_id: str | None = None
    messages: list[MessageInput]
