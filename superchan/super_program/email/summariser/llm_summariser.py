from __future__ import annotations

"""LLM-driven email summariser (package version)."""

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol, cast

from superchan.utils.config import LLMConfig
from superchan.utils.llm_providers import build_zai_llm

from superchan.super_program.email.models import EmailMessage, Summary
from superchan.super_program.email.utils import build_summary_prompt
from .base_summariser import BaseSummariser


class LLMCallable(Protocol):
    async def __call__(self, prompt: str, *, model: str | None = None, **kwargs: Any) -> str: ...


@dataclass(slots=True)
class LLMSummariser(BaseSummariser):
    llm_cfg: LLMConfig
    llm: LLMCallable | None = None

    def __post_init__(self) -> None:
        if self.llm is None:
            self.llm = build_zai_llm(self.llm_cfg)

    async def summarise(self, message: EmailMessage) -> Summary:
        prompt = build_summary_prompt(message)
        assert self.llm is not None
        raw = await self.llm(prompt, model=self.llm_cfg.model)
        return self._parse_summary(raw, message.message_id)

    def _parse_summary(self, content: str, email_id: str) -> Summary:
        try:
            data = json.loads(content)
            return Summary(
                email_id=email_id,
                title=str(data.get("标题") or data.get("title") or ""),
                content=str(data.get("内容") or data.get("content") or ""),
                priority=self._normalize_priority(str(data.get("优先级") or data.get("priority") or "")),
                category=str(data.get("类别") or data.get("category") or "其他"),
                keywords=self._to_list_of_str(data.get("关键词") or data.get("keywords")),
                sentiment=self._normalize_sentiment(str(data.get("情感") or data.get("sentiment") or "")),
                action_items=self._to_list_of_str(data.get("行动项") or data.get("actions") or data.get("action_items")),
            )
        except Exception:
            return Summary(
                email_id=email_id,
                title="",
                content=content.strip(),
                priority="medium",
                category="其他",
            )

    @staticmethod
    def _to_list_of_str(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [p.strip() for p in re.split(r"[,;]\s*", value) if p.strip()]
        if isinstance(value, list):
            any_list = cast(list[Any], value)
            out: list[str] = []
            for elem in any_list:
                s = str(elem).strip()
                if s:
                    out.append(s)
            return out
        return []

    @staticmethod
    def _normalize_priority(p: str) -> str:
        ps = p.strip().lower()
        mapping = {"高": "high", "中": "medium", "低": "low", "high": "high", "medium": "medium", "low": "low"}
        return mapping.get(ps, "medium")

    @staticmethod
    def _normalize_sentiment(s: str) -> float:
        ss = s.strip().lower()
        mapping = {"积极": 0.8, "中性": 0.5, "消极": 0.2, "positive": 0.8, "neutral": 0.5, "negative": 0.2}
        return mapping.get(ss, 0.5)


__all__ = ["LLMSummariser"]
