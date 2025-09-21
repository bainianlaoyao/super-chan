from __future__ import annotations

"""Email domain models for Super Program.

定义与邮件处理相关的核心数据结构：附件、邮件与摘要。
这些模型用于 fetcher/summariser 等组件之间的稳定契约。

约定与风格：
- 使用 dataclass，并提供清晰的类型注解与字段注释。
- 时间均使用带时区的 datetime（UTC 或本地带 tzinfo），避免混淆。
"""

from dataclasses import dataclass, field
from typing import Any, cast
from collections.abc import Sequence
import datetime as _dt


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


@dataclass(slots=True)
class EmailAttachment:
    """附件元数据。

    注意：content 字段仅在需要时由具体 fetcher 决定是否填充（可能为 bytes 或临时文件路径）。
    为避免内存占用，建议默认不内联大附件内容。
    """

    filename: str
    size: int | None = None
    content: bytes | str | None = None  # 原始字节或临时文件路径
    content_type: str | None = None


@dataclass(slots=True)
class EmailMessage:
    """标准化邮件对象。"""

    message_id: str
    subject: str
    sender: str
    recipients: list[str] = field(default_factory=lambda: cast(list[str], []))
    cc: list[str] = field(default_factory=lambda: cast(list[str], []))
    body_text: str = ""
    body_html: str | None = None
    attachments: list[EmailAttachment] = field(default_factory=lambda: cast(list[EmailAttachment], []))
    timestamp: _dt.datetime | None = None
    flags: set[str] = field(default_factory=lambda: cast(set[str], set()))  # {"read","unread","flagged",...}
    raw_hint: Any | None = None  # 可选：携带少量源对象引用/标识，便于后续操作


@dataclass(slots=True)
class Summary:
    """邮件摘要的结构化表示，而非纯字符串。

    设计动机：结构化字段便于检索、排序、统计分析与自动化处理，
    优于不可操作的纯文本摘要。
    """

    email_id: str  # 关联 EmailMessage.message_id
    title: str
    content: str
    priority: str  # high | medium | low
    category: str  # e.g. "urgent", "meeting", "newsletter", ...
    keywords: list[str] = field(default_factory=lambda: cast(list[str], []))
    sentiment: float = 0.5  # [-1.0, 1.0]
    action_items: list[str] = field(default_factory=lambda: cast(list[str], []))
    generated_at: _dt.datetime = field(default_factory=_utcnow)


__all__: Sequence[str] = ("EmailAttachment", "EmailMessage", "Summary")
