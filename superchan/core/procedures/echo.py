from __future__ import annotations

import asyncio
import time
from typing import Any

from superchan.ui.io_payload import OutputPayload


async def _proc_echo(params: dict[str, Any], metadata: dict[str, Any] | None) -> OutputPayload:
    start = time.perf_counter()
    text = str(params.get("text", ""))
    delay = 0.0
    try:
        delay = float(params.get("time_delay", 0.0) or 0.0)
    except Exception:
        delay = 0.0
    if delay > 0:
        await asyncio.sleep(min(delay, 5.0))
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


proc_echo = _proc_echo

__all__ = ["proc_echo", "_proc_echo"]
