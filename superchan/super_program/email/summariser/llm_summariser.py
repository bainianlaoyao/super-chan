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
        # 更稳健地解析：
        # 1) 直接解析
        # 2) 解析代码块内 JSON（移除 ```json ... ``` 包裹）
        # 3) 若缺少花括号，尝试自动补上
        # 4) 从整段文本里按大括号成对匹配提取首个平衡 JSON 对象
        for candidate in self._candidate_json_strings(content):
            try:
                data = json.loads(candidate)
                if isinstance(data, dict):
                    data_dict = cast(dict[str, Any], data)
                    return Summary(
                        email_id=email_id,
                        title=str(data_dict.get("标题") or data_dict.get("title") or ""),
                        content=str(data_dict.get("内容") or data_dict.get("content") or ""),
                        priority=self._normalize_priority(str(data_dict.get("优先级") or data_dict.get("priority") or "")),
                        category=str(data_dict.get("类别") or data_dict.get("category") or "其他"),
                        keywords=self._to_list_of_str(data_dict.get("关键词") or data_dict.get("keywords")),
                        sentiment=self._normalize_sentiment(str(data_dict.get("情感") or data_dict.get("sentiment") or "")),
                        action_items=self._to_list_of_str(
                            data_dict.get("行动项") or data_dict.get("actions") or data_dict.get("action_items")
                        ),
                    )
            except Exception:
                continue

        # 全部失败时，回退为原始内容
        return Summary(
            email_id=email_id,
            title="该邮件的llm输出解析失败",
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

    # --------------------------- helpers for robust JSON parsing --------------------------- #
    @staticmethod
    def _candidate_json_strings(text: str) -> list[str]:
        """生成一系列可能包含 JSON 对象的候选字符串。

        顺序：
        - 原始全文
        - 第一个 ```json ... ``` 代码块的内容（若存在）
        - 若代码块内容缺少花括号，则自动加上 { ... }
        - 从全文中按大括号成对匹配提取的第一个平衡对象
        """

        candidates: list[str] = []

        def add(s: str) -> None:
            s = s.strip()
            if s and s not in candidates:
                candidates.append(s)

        # 原文
        add(text)

        # 代码块（优先 ```json，其次任意 ```）
        fence_re = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.IGNORECASE | re.DOTALL)
        m = fence_re.search(text)
        if m:
            inner = m.group(1)
            add(inner)
            if not inner.lstrip().startswith("{"):
                # LLM 偶尔会漏掉开头的花括号，尝试补上
                add("{" + inner + "}")

        # 按花括号成对匹配提取
        for obj in LLMSummariser._iter_balanced_json_objects(text):
            add(obj)

        return candidates

    @staticmethod
    def _iter_balanced_json_objects(text: str):
        """从文本中迭代提取平衡的 JSON 对象子串。

        通过逐字符扫描，跟踪引号与转义，确保仅在字符串外部统计花括号深度。
        """
        depth = 0
        start = -1
        in_str = False
        escape = False

        for i, ch in enumerate(text):
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue

            if ch == '"':
                in_str = True
                continue

            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                if depth > 0:
                    depth -= 1
                    if depth == 0 and start != -1:
                        yield text[start : i + 1]
                        start = -1


__all__ = ["LLMSummariser"]
