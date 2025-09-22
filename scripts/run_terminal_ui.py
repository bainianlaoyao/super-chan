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
    from superchan.ui.push.serverchan_ui import ServerChanUI
    from superchan.core import CoreEngine, make_inprocess_transport
    from superchan.anime import LLMAnimePostProcessor, make_anime_transport
    from superchan.core.executors import build_default_programmatic_executor
    from superchan.utils.config import load_user_config
    from superchan.utils.llm_providers import build_zai_llm
    logger.info("模块导入成功")
except ImportError as e:
    logger.error(f"导入失败: {e}")
    logger.error("请确保在正确的 Python 环境中运行，并且所有依赖都已安装。")
    sys.exit(1)


def main() -> None:
    """主函数，启动终端 UI"""
    try:
        logger.info("正在初始化 Core 引擎与 IoRouter...")
        engine = CoreEngine(build_default_programmatic_executor())
        # 读取用户配置
        config = load_user_config(project_root)
        transport = make_inprocess_transport(engine)
        # 将 anime 风格化后处理接入 transport（默认使用本地回退风格器）
        system_prompt = config.anime_style.system_prompt or None
        # 根据 provider 尝试启用 Z.ai 提供器；若配置不完整则回退到本地风格化
        llm_callable = None
        try:
            if (config.llm.provider or "").lower() in {"zai", "zhipu", "zhipuai"} and (config.llm.api_key or ""):
                llm_callable = build_zai_llm(config.llm)
        except Exception as e:
            logger.warning(f"Z.ai 提供器初始化失败，使用本地回退风格器：{e}")

        if system_prompt is not None:
            stylizer = LLMAnimePostProcessor(llm=llm_callable, model=config.llm.model, system_prompt=system_prompt)
        else:
            stylizer = LLMAnimePostProcessor(llm=llm_callable, model=config.llm.model)
        transport = make_anime_transport(transport, stylizer)
        router = IoRouter(transport=transport)

        # 默认注册 ServerChan pusher（如配置了 api_key）
        sendkey = (config.push.serverchan.api_key or "").strip()
        if sendkey:

            ServerChanUI(router, sendkey, name="serverchan")
            logger.info("ServerChan pusher 已注册")



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
