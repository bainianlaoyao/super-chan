"""superchan.ui.io_router

模块说明：
该模块实现一个轻量的 IO 路由中心，作为 UI 层与后端 transport/执行器之间的桥梁。
核心功能：
- 将由 UI 产生的 `InputPayload` 通过可配置的异步 `transport` 发送到后端；
- 将 transport 的响应封装为 `OutputPayload` 并分发给所有已注册的回调（支持同步和异步回调）；
- 提供注册/注销回调的线程安全操作以及对并发回调的收集与异常记录。

设计要点与 API：
- Transport：类型为 Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]
    - transport 接受序列化后的请求 dict（例如由 `InputPayload.to_dict()` 生成），返回一个 dict 形式的响应。
- 回调：支持两类回调签名
    - 异步回调：async def cb(OutputPayload) -> None
    - 同步回调：def cb(OutputPayload) -> None
    IoRouter 会自动将同步回调提交到线程池以避免阻塞事件循环。

主要类：
- IoRouter
    - send_request(request: InputPayload) -> None: 发送请求并分发返回的 OutputPayload。
    - register_callback(callback) -> str: 注册回调，返回 callback_id（hex uuid）。
    - unregister_callback(callback_id: str) -> None: 注销回调。

并发与错误处理：
- 发起请求后，IoRouter 会将 transport 的返回值转换为 `OutputPayload`，并为每个回调创建任务或将同步调用提交到线程池。
- 回调执行过程中的异常会被记录（使用模块级 logger），并不会影响其他回调的执行。
- 内部使用 asyncio.Lock 保护回调注册表以保证并发安全。

示例：
>>> router = IoRouter()
>>> cid = router.register_callback(lambda out: print(out.text))
>>> await router.send_request(InputPayload(type="nl", input="hello"))

注意事项：
- IoRouter 假定传入的 request 已为 `InputPayload` 实例；send_request 使用 request.to_dict() 进行序列化。
- 默认 transport 为一个轻量模拟实现（见 `_default_transport`），在生产环境应替换为真实的异步 transport。

导出符号：IoRouter, TransportCallable, AsyncCallback, SyncCallback, CallbackType
"""

from __future__ import annotations

import asyncio
import datetime
import inspect
import logging
import uuid

from collections.abc import Callable, Coroutine
from typing import cast, Any

from superchan.ui.io_payload import OutputPayload, InputPayload

logger = logging.getLogger(__name__)

 
# 明确 transport 与回调类型
# Transport 为 async callable 返回 coroutine that yields dict[str, Any]
TransportCallable = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]
AsyncCallback = Callable[[OutputPayload], Coroutine[Any, Any, None]]
SyncCallback = Callable[[OutputPayload], None]
CallbackType = AsyncCallback | SyncCallback


class IoRouter:
    """
    IO 路由器。负责将来自 UI 的请求通过 transport 发送到 core（可插拔 transport），
    并将 transport 返回的输出封装为 OutputPayload 并分发给所有注册的回调。
    """

    def __init__(self, transport: TransportCallable | None = None) -> None:
        self._transport: TransportCallable = transport or self._default_transport
        self._callbacks: dict[str, CallbackType] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    @staticmethod
    async def _default_transport(request: dict[str, Any]) -> dict[str, Any]:
        await asyncio.sleep(0.05)
        return {"text": "模拟响应: " + str(request), "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}

    async def send_request(self, request: InputPayload) -> None:
        """
        Send request through transport and dispatch resulting OutputPayload.

        仅接受 InputPayload 实例。调用方必须构造 InputPayload（例如包含 'type' 与 'input' 字段）。
        示例序列化（request.to_dict()）会包含 "type" 与 "input" 字段，以及可选的 "timestamp" 与 "metadata"。

        运行时会在传入非 InputPayload 时记录错误并抛出 TypeError。
        """

        req: dict[str, Any] = request.to_dict()
        response_any: Any = await self._transport(req)
        # 明确将 transport 返回值构造为 dict 以供 OutputPayload.from_dict 使用，避免盲目 cast
        response_dict: dict[str, Any] = dict(response_any)
        payload: OutputPayload = OutputPayload.from_dict(response_dict)

        await self._dispatch_output(payload)

    async def _dispatch_output(self, output: OutputPayload) -> None:
        # 复制回调表以减少持锁时间
        async with self._lock:
            callbacks: list[CallbackType] = list(self._callbacks.values())

        if not callbacks:
            return

        loop = asyncio.get_running_loop()
        tasks: list[asyncio.Task[Any] | asyncio.Future[Any]] = []
        for cb in callbacks:
            # 优先判断是否为协程函数（避免同步调用阻塞事件循环）
            if inspect.iscoroutinefunction(cb):
                try:
                    async_cb = cast(AsyncCallback, cb)
                    coro = async_cb(output)
                    tasks.append(loop.create_task(coro))
                except Exception:
                    logger.exception("为协程回调创建任务失败")
            else:
                try:
                    sync_cb = cast(SyncCallback, cb)
                    tasks.append(loop.run_in_executor(None, sync_cb, output))
                except Exception:
                    logger.exception("将同步回调提交到线程池失败")

        if not tasks:
            return

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for res in results:
            # 使用 duck-typing 检测异常对象（避免运行时 isinstance 检查）
            if getattr(res, "__traceback__", None) is not None:
                logger.exception("回调执行过程中发生异常：%s", res)

    async def _transport_send(self, request: dict[str, Any]) -> dict[str, Any]:
        return await self._transport(request)

    async def _get_registered_count(self) -> int:
        async with self._lock:
            return len(self._callbacks)

    def register_callback(self, callback: CallbackType) -> str:
        if not callable(callback):
            raise TypeError("callback 必须为可调用对象")

        callback_id = uuid.uuid4().hex

        async def _register() -> None:
            async with self._lock:
                self._callbacks[callback_id] = callback

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_register())
        except RuntimeError:
            asyncio.run(_register())

        return callback_id

    def unregister_callback(self, callback_id: str) -> None:
 
        async def _unregister() -> None:
            async with self._lock:
                self._callbacks.pop(callback_id, None)
 
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_unregister())
        except RuntimeError:
            asyncio.run(_unregister())