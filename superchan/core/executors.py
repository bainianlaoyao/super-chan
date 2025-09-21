from __future__ import annotations

"""执行器实现集合。

ProgrammaticExecutor: 基于注册表的程序化执行器，运行结构化 procedure。
"""

import asyncio
import time
from typing import Any
from collections.abc import Awaitable, Callable

from superchan.ui.io_payload import OutputPayload


ProcedureFunc = Callable[[dict[str, Any], dict[str, Any] | None], Awaitable[OutputPayload]]


class ProgrammaticExecutor:
    """程序化执行器：注册并执行 procedure。

    - 使用 register(name, func) 注册异步过程函数。
    - execute(name, params, metadata) 执行并返回 OutputPayload。
    """

    def __init__(self) -> None:
        self._registry: dict[str, ProcedureFunc] = {}

    def register(self, name: str, func: ProcedureFunc) -> None:
        if not name:
            raise ValueError("procedure 名称不能为空")
        if not asyncio.iscoroutinefunction(func):
            raise TypeError("procedure 必须是 async 函数")
        self._registry[name] = func

    def unregister(self, name: str) -> None:
        self._registry.pop(name, None)

    async def execute(self, name: str, params: dict[str, Any], metadata: dict[str, Any] | None = None) -> OutputPayload:
        func = self._registry.get(name)
        if func is None:
            return OutputPayload(
                output={
                    "text": f"未找到 procedure: {name}",
                    "error": "procedure_not_found",
                },
                type="dict",
            )
        result: OutputPayload = await func(params, metadata)

        # 补充耗时信息到 metadata 并返回
        result.metadata = {**(result.metadata or {}), "command_name": name}
        return result


# ---------------------------
# 内置最小示例：echo
# ---------------------------

async def _proc_echo(params: dict[str, Any], metadata: dict[str, Any] | None) -> OutputPayload:
    start = time.perf_counter()
    # 支持 input_schema 中的 text 与 time_delay，可选
    text = str(params.get("text", ""))
    delay = 0.0
    try:
        delay = float(params.get("time_delay", 0.0) or 0.0)
    except Exception:
        delay = 0.0
    if delay > 0:
        await asyncio.sleep(min(delay, 5.0))  # 防御性上限
    # 返回 OutputPayload（type=dict），UI 会优先显示 output['text']
    used = time.perf_counter() - start
    return OutputPayload(
        output={
            "text": text,
            "echo": True,
            "time_used": used,
        },
        
        type="dict",
        metadata=metadata or {},
    )


def build_default_programmatic_executor() -> ProgrammaticExecutor:
    exe = ProgrammaticExecutor()
    exe.register("echo", _proc_echo)
    return exe
