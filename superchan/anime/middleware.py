"""Anime post-processing transport middleware.

提供一个包装函数，将现有 transport 的输出交由 LLMAnimePostProcessor 进行风格化处理，
再把结果返回给 IoRouter 分发。
"""

from __future__ import annotations

from superchan.ui.io_router import TransportCallable
from superchan.ui.io_payload import InputPayload, OutputPayload
from .llm_stylizer import LLMAnimePostProcessor


def make_anime_transport(
    underlying: TransportCallable,
    postprocessor: LLMAnimePostProcessor,
) -> TransportCallable:
    """将 anime 风格化后处理接入到给定的 transport。

    使用方式：
    >>> stylizer = LLMAnimePostProcessor(llm=None)
    >>> router = IoRouter(transport=make_anime_transport(my_transport, stylizer))
    
    参数：
    - underlying: 原有 transport（负责与引擎交互）
    - postprocessor: 风格化处理器
    返回：新的 transport，可直接传给 IoRouter
    """

    async def _wrapped(request: InputPayload) -> OutputPayload:
        raw_out = await underlying(request)
        styled = await postprocessor.process(raw_out)
        return styled

    return _wrapped
