from __future__ import annotations

"""Transport 适配器。

提供 make_inprocess_transport，将 CoreEngine 暴露为 IoRouter 所需的 TransportCallable：
Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
"""

from typing import Any
from collections.abc import Callable, Coroutine

from superchan.ui.io_payload import InputPayload, OutputPayload
from .engine import CoreEngine


def make_inprocess_transport(engine: CoreEngine) -> Callable[[InputPayload], Coroutine[Any, Any, OutputPayload]]:
    async def _transport(request: InputPayload) -> OutputPayload:
        out: OutputPayload = await engine.handle_input(request)
        return out

    return _transport
