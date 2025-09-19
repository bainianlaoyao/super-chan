"""src/ui/run_terminal_ui.py

本模块为运行入口示例，演示如何组合 IoRouter 与 TerminalTextualUI 并注入自定义 transport。

示例仅用于演示目的：通过 asyncio 延迟模拟网络调用，且可直接在终端运行（假定 textual 已安装）。
"""
from __future__ import annotations

import asyncio
import datetime
from typing import Any

from superchan.ui.io_router import IoRouter
from superchan.ui.terminal.terminal_ui import TerminalTextualUI


async def custom_transport(request: dict[str, Any]) -> dict[str, Any]:
    """
    可选自定义 transport 示例：用 asyncio.sleep 模拟异步网络调用并返回 dict 响应。
    """
    # 模拟网络延迟
    await asyncio.sleep(0.1)
    return {
        "text": "自定义传输响应: " + str(request),
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def main() -> None:
    """
    示例运行入口（关键步骤为 3 行）：
    - 创建 IoRouter 并注入 custom_transport（可选）
    - 创建 TerminalTextualUI 并传入 panel_config
    - 启动 UI（阻塞）
    """
    # 创建 IoRouter 并注入自定义 transport（演示行）
    router: IoRouter = IoRouter(transport=custom_transport)

    # 创建终端 UI，并展示如何通过 panel_config 传入程序化面板默认值
    ui: TerminalTextualUI = TerminalTextualUI(router, panel_config={"action": "demo", "priority": "low"})

    # 启动终端 UI（阻塞调用，直到退出）
    ui.run_blocking()


if __name__ == "__main__":
    main()