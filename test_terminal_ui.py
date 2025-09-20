#!/usr/bin/env python3
"""测试 terminal_ui 的简单脚本"""

import asyncio
import sys
from superchan.ui.terminal.terminal_ui import TerminalUI
from superchan.ui.io_router import IoRouter

async def test():
    """测试函数"""
    try:
        print("创建 IoRouter...")
        router = IoRouter()

        print("创建 TerminalUI...")
        ui = TerminalUI(router)

        print("Terminal UI 创建成功！")
        print("注意：这是一个 TUI 应用程序，需要在终端中运行。")
        print("要正常运行，请使用：")
        print("uv run python superchan/ui/terminal/terminal_ui.py")

        return True
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # sys.exit(0 if success else 1)
