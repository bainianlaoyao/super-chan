"""LLM-based anime post-processor

提供一个用于对引擎输出文本进行“二次元风格化”的后处理器。

核心约定：
- 输入：superchan.ui.io_payload.OutputPayload（可能是 text 或 dict）
- 输出：新的 OutputPayload（type='text'），其 output 为风格化后的文本

可通过依赖注入传入一个异步 LLM 调用器；未提供时使用本地回退风格器（无外部依赖）。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Protocol
import datetime as _dt

from superchan.ui.io_payload import OutputPayload


class LLMCallable(Protocol):
    async def __call__(self, prompt: str, *, model: str | None = None, **kwargs: Any) -> str: ...


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _extract_text(payload: OutputPayload) -> str:
    """从 OutputPayload 中尽力提取文本。

    策略：
    - 若为 type=='text'：直接转为 str 返回
    - 若为 type=='dict'：
        - 优先使用 output.get('text') 或 output.get('message')
        - 否则将 dict 的简单字符串字段拼接成一段文本
        - 仍失败则使用 str(payload.output)
    """
    if payload.type == "text":
        return str(payload.output)
    out = payload.output
    if isinstance(out, dict):
        # 优先一些常见键
        for key in ("text", "message", "content"):
            val = out.get(key)
            if isinstance(val, str) and val.strip():
                return val
        # 尝试合成
        parts: list[str] = []
        for _, v in out.items():
            if isinstance(v, str) and v.strip():
                parts.append(v)
        if parts:
            return "\n".join(parts)
    return str(payload.output)


def _fallback_stylize(text: str) -> str:
    """在没有 LLM 的情况下进行简单的二次元风格化润色（无外部依赖）。"""
    base = text.strip() or "（空内容）"
    # 轻度装饰，保持可读
    # prefix = "【苏帕酱】"
    flair = " ✨"
    # 简单规则：句末加感叹和可爱符号，不重复叠加
    end = "!" if not base.endswith(("!", "！")) else ""
    return f"{base}{end}{flair}"


def _compose_prompt(system_prompt: str, text: str) -> str:
    return (
        f"{system_prompt}\n\n"
        "下面是需要你进行二次元风格化润色的文本：\n"
        f"---\n{text}\n---\n"
        "请仅输出润色后的文本，不要解释。"
    )


DEFAULT_SYSTEM_PROMPT = (
    "你是一个擅长二次元风格表达的助手。"
    "请在保持原意和可读性的前提下进行轻度风格化（可加入适量可爱语气词、表情、拟声词），"
    "避免过度冗长与角色扮演，适合终端 UI 展示。"
)


class LLMAnimePostProcessor:
    """基于 LLM 的二次元风格化后处理器。

    参数：
    - llm: 可选，异步调用器，签名为 await llm(prompt: str, *, model: str|None, **kw) -> str
    - model: 可选，传给 llm 的模型名
    - system_prompt: 可选，控制整体风格的系统提示词
    - return_dict_on_failure: 当 LLM 失败时，是否返回原 payload（True）或使用本地回退（False，默认）
    """

    def __init__(
        self,
        llm: LLMCallable | None = None,
        *,
        model: str | None = None,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        return_dict_on_failure: bool = False,
    ) -> None:
        self._llm = llm
        self._model = model
        self._system_prompt = system_prompt
        self._return_dict_on_failure = return_dict_on_failure

    async def process(self, payload: OutputPayload) -> OutputPayload:
        """对输出进行风格化，并返回新的 OutputPayload（type='text'）。"""
        text = _extract_text(payload)
        meta = dict(payload.metadata or {})

        used: str
        stylized: str
        
        if self._llm is not None:
            prompt = _compose_prompt(self._system_prompt, text)
            try:
                stylized = await self._llm(prompt, model=self._model)
                stylized = (stylized or "").strip() or _fallback_stylize(text)
                used = "llm"
            except Exception as exc:  # 兜底，防止影响主流程
                meta.setdefault("anime", {})
                meta["anime"]["llm_error"] = str(exc)
                if self._return_dict_on_failure:
                    # 返回原 payload，仅合并 metadata
                    return replace(payload, metadata=meta)
                stylized = _fallback_stylize(text)
                used = "fallback-error"
        else:
            stylized = _fallback_stylize(text)
            used = "fallback"

        # 合并 metadata 并标记来源
        meta.setdefault("anime", {})
        meta["anime"].update({
            "post_processor": "LLMAnimePostProcessor",
            "mode": used,
            "model": self._model,
        })
        meta['source'] = '苏帕酱'

        return OutputPayload(
            output=stylized,
            type="text",
            timestamp=payload.timestamp or _utcnow(),
            metadata=meta,
        )
