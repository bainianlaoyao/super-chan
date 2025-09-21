from __future__ import annotations

"""Base interfaces for email fetchers.

抽象定义：不同来源（IMAP/API/Outlook）抓取邮件需要遵循的最小契约。
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Protocol

from superchan.super_program.email.models import EmailMessage


class SupportsFetch(Protocol):
    def fetch(self, *, folder: str = "Inbox", unread_only: bool = False, limit: int | None = None) -> list[EmailMessage]: ...


class BaseEmailFetcher(ABC):
    """抓取器抽象基类。"""

    @abstractmethod
    def fetch(self, *, folder: str = "Inbox", unread_only: bool = False, limit: int | None = None) -> list[EmailMessage]:
        """抓取邮件，返回标准化 EmailMessage 列表。"""

    def mark_as_read(self, ids: Iterable[str]) -> None:  # 可选能力
        raise NotImplementedError

    def move(self, ids: Iterable[str], *, dest_folder: str) -> None:  # 可选能力
        raise NotImplementedError


__all__ = ["BaseEmailFetcher", "SupportsFetch"]
