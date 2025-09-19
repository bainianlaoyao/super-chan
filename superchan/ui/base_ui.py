"""src/ui/base_ui.py

定义所有 UI 共享的抽象基类 BaseUI。

该模块提供：
- BaseUI 抽象类：负责与 IoRouter 注册/注销回调并提供一个内部 asyncio.Queue 用于线程安全地在回调与 UI 主循环间传递 OutputPayload。
- 回调包装说明：IoRouter 可能以“异步任务”或“线程池同步调用”的方式调用回调，BaseUI 推荐以异步回调注册（内部会直接调用子类的 async receive_output），并在 docstring 中说明同步回调的实现选项。

设计要点（中文说明）：
- 构造参数包含 router: IoRouter 与可选 name: str。
- __init__ 会自动 register_callback，并在 shutdown() 中注销。
- 子类必须实现 async send_request(request: dict[str, Any]) -> None 与 async receive_output(output: OutputPayload) -> None。
- 不在此处实现复杂回退或吞噬异常；保持接口清晰。
"""

from __future__ import annotations

import abc
import asyncio
# from typing import Any

from superchan.ui.io_router import IoRouter, OutputPayload, InputPayload


class BaseUI(abc.ABC):
    """
    抽象 UI 基类（所有 UI 应继承该类）。

    行为：
    - 在构造时用 router.register_callback 注册一个异步回调（内部为 coroutine function），
      IoRouter 会在其事件循环中通过 create_task 调用该回调。
    - 回调职责为将来自 IoRouter 的 OutputPayload 传递给子类实现的 receive_output 方法。
    - 提供内部 asyncio.Queue 以方便子类在回调与 UI 事件循环间安全传递数据。
    - 提供 shutdown() 方法用于注销已注册的回调（必须在 UI 退出时调用）。

    回调包装说明（简要）：
    - 推荐注册异步回调（此处实现为 async _callback），因为 IoRouter 会检测协程函数并在其事件循环中创建 task 执行。
    - 若需要提供同步回调（供 IoRouter 在其线程池执行），可以实现一个同步 wrapper：
        # 说明性伪代码：在同步线程中，将协程安全地提交到运行中的事件循环（不展示具体 isinstance 示例）
        # 例如：通过线程安全的提交接口将 self.receive_output(...) 交由主 loop 执行
      但这种方式依赖于存在一个运行中的事件循环，使用时请确保主循环已就绪。
    """

    def __init__(self, router: IoRouter, name: str | None = None) -> None:
        """
        初始化 BaseUI 并向 IoRouter 注册回调。

        参数：
        - router: IoRouter 负责请求发送与回调分发（必填）
        - name: 可选的 UI 名称（用于日志或区分多个 UI）
        """
        self.router: IoRouter = router
        self.name: str = name or self.__class__.__name__

        # 内部队列用于在回调上下文与 UI 主循环间传递 OutputPayload
        self._queue: asyncio.Queue[OutputPayload] = asyncio.Queue()

        # 注册回调；使用异步回调包装，IoRouter 会把 coroutine 函数以 task 形式执行
        self._callback_id: str = self.router.register_callback(self._async_callback)

    async def _async_callback(self, output: OutputPayload) -> None:
        """
        IoRouter 将调用此异步回调（或将其作为 task 执行）。
        默认行为是将 payload 传给子类实现的 receive_output。

        子类可覆盖 receive_output 来把 output 放入队列或直接渲染。
        """
        await self.receive_output(output)

    def shutdown(self) -> None:
        """
        注销之前注册到 IoRouter 的回调。应在 UI 退出时调用以避免悬挂回调。
        """
        try:
            self.router.unregister_callback(self._callback_id)
        except Exception:
            # 仅捕获并记录少量上下文性错误（调用方可在更高层处理）
            # 不吞掉错误细节——在实际运行时应由调用者根据需要记录或展示
            raise

    @property
    def queue(self) -> asyncio.Queue[OutputPayload]:
        """公开内部队列以供子类 UI 使用（线程安全的 asyncio.Queue）。"""
        return self._queue

    @abc.abstractmethod
    async def send_request(self, payload : InputPayload) -> None:
        """
        将用户构建的请求发送到后端（通过 IoRouter）。

        子类必须实现：应构建或验证 request，然后调用 router.send_request(request)。

        参数：
        - request: dict[str, Any] 表示的请求，格式由上层协议决定。
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def receive_output(self, output: OutputPayload) -> None:
        """
        IoRouter 分发到 UI 的输出接收接口（异步）。

        子类实现应该把输出放到内部渲染队列或直接渲染到界面。
        - 注意：该方法会在事件循环中以 task 形式运行；应尽量快速完成或将耗时操作交由后台任务。
        """
        raise NotImplementedError