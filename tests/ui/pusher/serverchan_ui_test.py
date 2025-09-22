import os
import time
from typing import Any

import pytest

from superchan.ui.io_router import IoRouter
from superchan.ui.io_payload import OutputPayload
from superchan.ui.push.serverchan_ui import ServerChanUI
from superchan.utils.config import load_user_config



async def test_serverchan_real_push_roundtrip(tmp_path: Any) -> None:
    # 加载真实用户配置
    cfg = load_user_config(os.getcwd())
    sendkey = (cfg.push.serverchan.api_key or '').strip()
    if not sendkey:
        pytest.skip("No ServerChan api_key configured; set push.serverchan.api_key in config/user.toml or SUPERCHAN_CONFIG")

    # 构建 IoRouter 与 ServerChanUI
    router = IoRouter()
    ui = ServerChanUI(router, {"api_key": sendkey}, name="serverchan")

    # 构建一个会被该 UI 放行的 OutputPayload（包含 channels）
    md = {
        "source": "tests",
        "push": {"channels": ["serverchan"]},
    }
    out = OutputPayload(output={"text": "来自测试的问候 at " + time.strftime('%H:%M:%S')}, type="dict", metadata=md)

    # 直接调用 UI 的回调逻辑进行推送（避免依赖 transport）
    await ui.receive_output(out)

    # 若未抛异常则视为成功（ServerChan 可能异步，但 HTTP 返回非 200 / 非 code=0 时会抛错）
    assert True
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_serverchan_real_push_roundtrip(''))    