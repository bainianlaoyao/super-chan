from __future__ import annotations

"""
CoreEngine: 统一接收 InputPayload，调度到相应的执行器，并产出 OutputPayload。

当前实现：
- 支持 "precedure"（程序化）与 "nl"（自然语言）两种输入类型。
- 程序化执行委托给 ProgrammaticExecutor。
- NL 输入提供一个最小回显实现（可替换）。
"""

import datetime
from typing import Any
from .executors import ProgrammaticExecutor

from superchan.ui.io_payload import InputPayload, OutputPayload


class CoreEngine:
    """核心引擎，负责调度与执行。"""

    def __init__(self, programmatic_executor: ProgrammaticExecutor | None = None) -> None:
        self._programmatic: ProgrammaticExecutor | None = programmatic_executor

    @property
    def programmatic(self) -> ProgrammaticExecutor | None:
        return self._programmatic

    def set_programmatic(self, executor: ProgrammaticExecutor) -> None:
        self._programmatic = executor

    async def handle_input(self, payload: InputPayload) -> OutputPayload:
        """根据 InputPayload.type 路由到具体执行器并返回 OutputPayload。"""
        now = datetime.datetime.now(datetime.timezone.utc)

        if payload.type == "precedure" and isinstance(payload.input, dict):
            if self._programmatic is None:
                return OutputPayload(
                    output={
                        "text": f"对于 {payload.input.get('name',"")}, 程序化执行器未配置",
                        "error": "missing_programmatic_executor",
                    },
                    type="dict",
                    timestamp=now,
                    metadata={"source": "core"},
                )

            # 约定：procedure 名称在 metadata["procedure"]，由 UI 层注入
            proc_name = str((payload.metadata or {}).get("procedure") or "")
            if not proc_name:
                return OutputPayload(
                    output={
                        "text": "缺少 procedure 名称",
                        "error": "missing_procedure_name",
                    },
                    type="dict",
                    timestamp=now,
                    metadata={"source": "core"},
                )

            try:
                result: OutputPayload = await self._programmatic.execute(
                    proc_name, _ensure_dict(payload.input), payload.metadata
                )
            except Exception as exc:  # noqa: BLE001 - 统一捕获返回结构化错误
                return OutputPayload(
                    output={
                        "text": f"procedure 执行异常: {exc}",
                        "error": "procedure_exception",
                    },
                    type="dict",
                    timestamp=now,
                    metadata={"source": "core"},
                )

            return result

        # NL 输入：最小回显（可在后续替换为对话 agent 等）
        return OutputPayload(
            output=f"你说：{payload.input}",
            type="text",
            timestamp=now,
            metadata={"source": "core"},
        )


def _ensure_dict(value: Any) -> dict[str, Any]:
    from typing import cast
    if isinstance(value, dict):
        return cast(dict[str, Any], value)
    return {"value": value}
