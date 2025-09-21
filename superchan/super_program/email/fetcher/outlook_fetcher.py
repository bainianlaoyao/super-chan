from __future__ import annotations

"""Outlook fetcher using local Outlook COM (pywin32).

仅在 Windows 且安装了 Microsoft Outlook 时可用。依赖 pywin32（win32com）。
提供基本能力：按文件夹抓取邮件、可选未读过滤、标记已读、移动邮件。
"""

from dataclasses import dataclass
from collections.abc import Iterable
from typing import Any

from superchan.super_program.email.models import EmailAttachment, EmailMessage
from .base_fetcher import BaseEmailFetcher


try:  # 延迟导入，便于在非 Windows 环境下被安全 import
    import win32com.client  # type: ignore
except Exception:  # pragma: no cover - 环境不满足时仍然允许模块被导入
    win32com = None  # type: ignore


@dataclass(slots=True)
class OutlookFetcher(BaseEmailFetcher):
    profile_name: str | None = None
    _app: Any | None = None
    _ns: Any | None = None

    def __post_init__(self) -> None:
        if win32com is None:  # noqa: SIM108 - 明确错误信息
            raise ImportError(
                "OutlookFetcher 需要 pywin32；请先安装：pip install pywin32，并确保 Windows 上已安装 Outlook"
            )
        self._app = win32com.client.Dispatch("Outlook.Application")  # type: ignore[attr-defined]
        self._ns = self._app.GetNamespace("MAPI")
        # 若需要特定 profile，可在此处理；默认使用系统默认配置文件

    def _folder_id(self, name: str) -> int:
        mapping: dict[str, int] = {
            "Inbox": 6,
            "Sent Items": 5,
            "Drafts": 16,
            "Deleted Items": 3,
            "Junk": 23,
        }
        return mapping.get(name, 6)

    def fetch(self, *, folder: str = "Inbox", unread_only: bool = False, limit: int | None = None) -> list[EmailMessage]:
        ns = self._require_ns()
        fld = ns.GetDefaultFolder(self._folder_id(folder))
        items = fld.Items
        if unread_only:
            items = items.Restrict("[UnRead] = True")
        items.Sort("[ReceivedTime]", True)

        emails: list[EmailMessage] = []
        count = 0
        for it in items:
            if limit is not None and count >= limit:
                break
            # 43: olMail
            if getattr(it, "Class", None) != 43:
                continue
            emails.append(self._to_email(it))
            count += 1
        return emails

    def mark_as_read(self, ids: Iterable[str]) -> None:
        ns = self._require_ns()
        for mid in ids:
            item = ns.GetItemFromID(mid)
            item.UnRead = False
            item.Save()

    def move(self, ids: Iterable[str], *, dest_folder: str) -> None:
        ns = self._require_ns()
        target = ns.GetDefaultFolder(self._folder_id(dest_folder))
        for mid in ids:
            item = ns.GetItemFromID(mid)
            item.Move(target)

    # -- helpers -----------------------------------------------------------------
    def _to_email(self, it: Any) -> EmailMessage:  # Outlook COM item, 动态对象
        body_text = str(getattr(it, "Body", "") or "")
        body_html = getattr(it, "HTMLBody", None)

        recipients: list[str] = []
        rcp = getattr(it, "Recipients", None)
        if rcp is not None:
            for r in rcp:
                addr = str(getattr(r, "Address", "") or "")
                if addr:
                    recipients.append(addr)

        atts: list[EmailAttachment] = []
        att_col = getattr(it, "Attachments", None)
        if att_col is not None:
            for a in att_col:
                atts.append(
                    EmailAttachment(
                        filename=str(getattr(a, "FileName", "") or ""),
                        size=int(getattr(a, "Size", 0) or 0),
                        content=None,
                    )
                )

        flags: set[str] = set()
        if getattr(it, "UnRead", False):
            flags.add("unread")
        else:
            flags.add("read")
        if getattr(it, "FlagStatus", 0) == 1:
            flags.add("flagged")

        return EmailMessage(
            message_id=str(getattr(it, "EntryID", "") or ""),
            subject=str(getattr(it, "Subject", "") or ""),
            sender=str(getattr(it, "SenderEmailAddress", "") or ""),
            recipients=recipients,
            body_text=body_text,
            body_html=str(body_html) if body_html is not None else None,
            attachments=atts,
            timestamp=getattr(it, "ReceivedTime", None),
            flags=flags,
            raw_hint=None,
        )

    def _require_ns(self) -> Any:
        ns = self._ns
        if ns is None:
            raise RuntimeError("Outlook Namespace 尚未初始化")
        return ns


__all__ = ["OutlookFetcher"]
