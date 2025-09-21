from __future__ import annotations

"""执行器实现集合。

ProgrammaticExecutor: 基于注册表的程序化执行器，运行结构化 procedure。
"""

import asyncio
from typing import Any
from collections.abc import Awaitable, Callable

from superchan.ui.io_payload import OutputPayload
from superchan.utils.procedure_registry import get_registered_procedures


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


def build_default_programmatic_executor() -> ProgrammaticExecutor:
    exe = ProgrammaticExecutor()
    # 从全局注册表批量注册
    for name, func in get_registered_procedures().items():
        exe.register(name, func)  # type: ignore[arg-type]
    return exe
