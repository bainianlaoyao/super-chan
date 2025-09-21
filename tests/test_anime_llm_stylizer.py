import asyncio
from typing import Any

from superchan.ui.io_payload import OutputPayload
from superchan.anime import LLMAnimePostProcessor


async def _dummy_llm(prompt: str, *, model: str | None = None, **kwargs: Any) -> str:
    # 返回一个简单的包裹文本，模拟 LLM 输出
    return "【LLM】" + (prompt[-20:] if len(prompt) > 20 else prompt)


def test_fallback_mode():
    pp = LLMAnimePostProcessor(llm=None)
    src = OutputPayload(output="你好，世界", type="text")
    out = asyncio.run(pp.process(src))
    assert out.type == "text"
    assert isinstance(out.output, str)
    assert out.output.startswith("【苏帕酱】")


def test_llm_mode():
    pp = LLMAnimePostProcessor(llm=_dummy_llm, model="fake-model")
    src = OutputPayload(output={"text": "今天天气不错"}, type="dict")
    out = asyncio.run(pp.process(src))
    assert out.type == "text"
    assert isinstance(out.output, str)
    assert out.metadata.get("anime", {}).get("mode") == "llm"
