from __future__ import annotations

"""Email utilities.

提供通用的工具函数：文本提取、HTML 粗略去标签、字符串裁剪、提示词构建等。
这些工具被 summariser 与 fetcher 复用。
"""

from html import unescape
import re
from collections.abc import Iterable

from .models import EmailMessage


_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(html: str) -> str:
    """粗略去除 HTML 标签，保留纯文本。

    注意：这是一个轻量实现，满足终端摘要场景；如需更准确的提取，
    可在未来引入专用的 HTML 解析库（例如 beautifulsoup4）。
    """

    text = _TAG_RE.sub(" ", html)
    text = unescape(text)
    # 归一化空白
    text = re.sub(r"\s+", " ", text).strip()
    return text


def ensure_plain_text(msg: EmailMessage) -> str:
    """返回适合摘要的纯文本正文。优先 body_text，其次从 body_html 提取。"""

    if msg.body_text and msg.body_text.strip():
        return msg.body_text.strip()
    if msg.body_html:
        return strip_html(msg.body_html)
    return ""


def clamp(text: str, max_len: int) -> str:
    """将文本裁剪到指定长度，超出部分以省略号结尾。"""

    t = text.strip()
    if len(t) <= max_len:
        return t
    return t[: max(0, max_len - 3)].rstrip() + "..."


def join_nonempty(parts: Iterable[str], sep: str = "; ") -> str:
    """连接非空字符串。"""

    return sep.join(p for p in parts if p and p.strip())


def build_summary_prompt(msg: EmailMessage, *, max_body_chars: int = 2000) -> str:
    """构建用于 LLM 摘要的提示词。"""

    body = clamp(ensure_plain_text(msg), max_body_chars)
    recipients = join_nonempty(msg.recipients)
    cc = join_nonempty(msg.cc)
    return (
        "请对以下邮件进行结构化分析和总结，请严格按照以下JSON格式输出，不要输出其他内容:\n"
        "```json\n"
        '  "标题": "邮件的主要标题",\n'
        '  "内容": "邮件内容的简要总结，不超过3句话",\n'
        '  "优先级": "高/中/低 中的一个",\n'
        '  "类别": "工作/个人/通知/垃圾/其他 中的一个",\n'
        '  "关键词": ["关键词1", "关键词2", "关键词3"],\n'
        '  "情感": "积极/中性/消极 中的一个",\n'
        '  "行动项": ["需要采取的具体行动1", "需要采取的具体行动2"]\n'
        "}\n\n"
        "```\n"
        "请分析以下邮件内容并按上述格式返回JSON:\n\n"
        f"主题: {msg.subject}\n"
        f"发件人: {msg.sender}\n"
        f"收件人: {recipients}\n"
        f"抄送: {cc}\n"
        f"时间: {msg.timestamp}\n\n"
        f"正文:\n{body}\n"
    )


__all__ = [
    "strip_html",
    "ensure_plain_text",
    "clamp",
    "join_nonempty",
    "build_summary_prompt",
]
