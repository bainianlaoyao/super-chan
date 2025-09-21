import asyncio
import datetime as dt

from superchan.ui.io_payload import InputPayload, OutputPayload
from superchan.anime import LLMAnimePostProcessor, make_anime_transport


async def _fake_transport(req: InputPayload) -> OutputPayload:
    # 模拟底层引擎返回一个朴素文本
    return OutputPayload(output=f"echo: {req.input}", type="text", timestamp=dt.datetime.now(dt.timezone.utc))


def test_middleware_wraps_transport():
    stylizer = LLMAnimePostProcessor(llm=None)
    wrapped = make_anime_transport(_fake_transport, stylizer)

    req = InputPayload(type="nl", input="你好")
    out = asyncio.run(wrapped(req))
    assert out.type == "text"
    assert isinstance(out.output, str)
    assert out.output.startswith("【苏帕酱】")