from __future__ import annotations

"""LLM providers adapters.

提供与 LLMAnimePostProcessor 兼容的 LLMCallable 适配器。
此处实现 Z.ai/ZhipuAI 提供器，基于 z-ai-sdk-python（zai 包）。

参考（Context7 文档摘要）:
- from zai import ZaiClient, ZhipuAiClient
- client.chat.completions.create(model="glm-4", messages=[{"role":"user","content":"..."}])
- 响应文本：response.choices[0].message.content 或流式 delta.content
"""

import asyncio
import logging
from typing import Any

from superchan.anime.llm_stylizer import LLMCallable
from superchan.utils.config import LLMConfig

logger = logging.getLogger(__name__)


def build_zai_llm(cfg: LLMConfig) -> LLMCallable:
    """构建一个基于 Z.ai/ZhipuAI SDK 的一次性 LLM 调用器。

    需求：
    - pip install z-ai-sdk-python 以提供 `zai` 包（或用户自备）
    - cfg.api_key 必须可用
    - cfg.model 指定模型（如 glm-4 / charglm-3 / glm-4v 等）

    说明：SDK 为同步接口，此处通过 asyncio.to_thread 以异步方式封装。
    """
    try:
        # 延迟导入，避免未安装时报错影响其他路径
        from zai import ZaiClient, ZhipuAiClient  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise ImportError("未安装 z-ai-sdk-python，请先安装依赖：pip install z-ai-sdk-python") from exc

    api_key = (cfg.api_key or "").strip()
    if not api_key:
        raise ValueError("缺少 Z.ai API Key，请在 config/user.toml 的 [llm].api_key 设置或通过环境变量提供")

    provider = (cfg.provider or "").lower()
    # 国内：ZhipuAiClient；海外：ZaiClient。若未指定 provider，则默认使用 ZaiClient。
    if provider in {"zhipu", "zhipuai", "cn"}:
        _client = ZhipuAiClient(api_key=api_key)
    else:
        _client = ZaiClient(api_key=api_key)

    def _sync_infer(prompt: str, model: str) -> str:
        # 简单消息体：直接把 prompt 作为用户消息
        resp = _client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
    
        # 非流式：choices[0].message.content
        return str(resp.choices[0].message.content) # type: ignore


    async def _call(prompt: str, *, model: str | None = None, **kwargs: Any) -> str:
        chosen_model = (model or cfg.model or "").strip()
        if not chosen_model:
            raise ValueError("缺少 Z.ai 模型名，请在 [llm].model 指定")
        # 在后台线程中调用同步 SDK
        return await asyncio.to_thread(_sync_infer, prompt, chosen_model)

    return _call
