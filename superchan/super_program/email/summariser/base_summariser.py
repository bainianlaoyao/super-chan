from __future__ import annotations

"""Base interfaces for email summarisers."""

from abc import ABC, abstractmethod
from superchan.super_program.email.models import EmailMessage, Summary


class BaseSummariser(ABC):
    @abstractmethod
    async def summarise(self, message: EmailMessage) -> Summary: ...


__all__ = ["BaseSummariser"]
