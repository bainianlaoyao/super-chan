"""Email program group package.

公开主要子包：fetcher、summariser，以及数据模型与工具。
"""

from .models import EmailAttachment, EmailMessage, Summary

__all__ = [
    "EmailAttachment",
    "EmailMessage",
    "Summary",
]
