#!/usr/bin/env python3
"""启动终端 UI 的脚本

此脚本用于启动 superchan 的终端用户界面。
它会初始化 IoRouter 和 TerminalUI，然后运行应用程序。

使用方法：
    python scripts/run_terminal_ui.py
    或
    uv run python scripts/run_terminal_ui.py
"""

import sys
import logging
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# 添加项目根目录到 Python 路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    logger.info(f"已添加项目根目录到 Python 路径: {project_root}")

try:
    from superchan.ui.terminal.terminal_ui import run_terminal_ui
    from superchan.ui.io_router import IoRouter
    logger.info("模块导入成功")
except ImportError as e:
    logger.error(f"导入失败: {e}")
    logger.error("请确保在正确的 Python 环境中运行，并且所有依赖都已安装。")
    sys.exit(1)


def main() -> None:
    """主函数，启动终端 UI"""
    try:
        logger.info("正在初始化 IoRouter...")
        router = IoRouter()

        logger.info("Terminal UI 初始化完成，正在启动...")
        # 使用同步运行方式，因为 run_terminal_ui 内部已处理异步
        run_terminal_ui(router)

    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在退出...")
    except Exception as e:
        logger.exception(f"启动终端 UI 时发生错误: {e}")
        raise


if __name__ == "__main__":
    logger.info("启动 superchan 终端 UI...")
    try:
        main()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        sys.exit(1)
    else:
        logger.info("程序正常退出")
        sys.exit(0)
