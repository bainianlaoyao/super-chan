"""superchan.core

Core 层：调度与执行。

导出：
- CoreEngine: 承载执行器并负责调度。
- make_inprocess_transport: 将 CoreEngine 暴露为 IoRouter 可用的异步 transport。
"""

from .engine import CoreEngine
from .transport import make_inprocess_transport
from .executors import ProgrammaticExecutor, build_default_programmatic_executor

__all__ = [
    "CoreEngine",
    "make_inprocess_transport",
    "ProgrammaticExecutor",
    "build_default_programmatic_executor",
]
