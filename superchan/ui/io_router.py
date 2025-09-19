"""src/ui/io_router.py

本模块为所有 UI 共享的 IO 路由中心（低耦合）。提供：
- 可序列化的 OutputPayload dataclass（text, timestamp, metadata）
- 可插拔的异步 transport（网络发送占位器）
- IoRouter：请求发送、注册/注销回调、并发分发输出到所有回调

实现原则（简洁、明确、类型注解）：
- transport 为可注入的 async callable: async def transport(request: dict) -> dict
- 回调签名可接受异步函数或同步函数：Callable[[OutputPayload], Coroutine[Any, Any, None] 或同步函数]
"""

from __future__ import annotations

import asyncio
import dataclasses
import datetime
import inspect
import logging
import uuid
from dataclasses import dataclass
from collections.abc import Callable, Coroutine
from typing import Literal, cast, Any

logger = logging.getLogger(__name__)


@dataclass
class OutputPayload:
    """
    可序列化的输出载荷，UI 回调接收该对象。

    字段：
    - text: 必填，输出文本
    - timestamp: 可选，datetime 或 None（使用 timezone-aware UTC）
    - metadata: 可选，额外信息字典
    """
    text: str
    timestamp: datetime.datetime | None = None
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)  # type: ignore[assignment]

    def to_dict(self) -> dict[str, Any]:
        """
        将 OutputPayload 转成字典以便网络传输/序列化。
        datetime 使用 ISO 格式字符串表示；若 timestamp 为 None 则返回 None。
        """
        return {
            "text": self.text,
            "timestamp": self.timestamp.isoformat() if self.timestamp is not None else None,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "OutputPayload":
        """
        从字典恢复 OutputPayload。接受来自 transport 的响应 dict。
        - 当 data 中缺少 text 时，会以 str(data) 作为 text 的后备表示。
        - timestamp 尝试用 ISO 字符串解析；解析失败时记录异常并置为 None（不再做 isinstance 检查）。
        """
        text = data.get("text")
        if text is None:
            # 将任意响应以字符串形式封装为 text，保证字段满足最小要求
            text = str(data)
        raw_ts = data.get("timestamp")
        timestamp: datetime.datetime | None
        if raw_ts is None:
            timestamp = None
        else:
            try:
                # 以 duck-typing 尝试解析 ISO 字符串
                timestamp = datetime.datetime.fromisoformat(raw_ts)  # type: ignore[arg-type]
            except Exception as exc:
                # 解析失败时记录异常并置为 None
                logger.exception("无法解析 timestamp，置为 None：%s", exc)
                timestamp = None
        metadata = dict(data.get("metadata") or {})
        return OutputPayload(text=text, timestamp=timestamp, metadata=metadata)
  
@dataclass
class InputPayload:
    """
    输入载荷，供 IoRouter.send_request 使用。

    新语义：
    - type: "precedure" 或 "nl"
    - input: 当 type == "nl" 时为字符串；当 type == "precedure" 时为 dict
    - timestamp: 可选，datetime 或 None（ISO 格式序列化）
    - metadata: 可选，额外信息字典

    注意：构造时会验证 type 与 input 的一致性，校验失败将抛出 TypeError。
    """
    type: Literal["precedure", "nl"]
    input: str | dict[str, Any]
    timestamp: datetime.datetime | None = None
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)  # type: ignore[assignment]

    def __post_init__(self) -> None:    
        if self.type == "nl" and not isinstance(self.input, str):
            raise TypeError("For InputPayload.type == 'nl', input must be a str")
        if self.type == "precedure" and not isinstance(self.input, dict):
            raise TypeError("For InputPayload.type == 'precedure', input must be a dict")

    def to_dict(self) -> dict[str, Any]:
        """
        将 InputPayload 序列化为 dict。
        返回结构：
        {
          "type": "nl"|"precedure",
          "input": "..." or { ... },
          "timestamp": ISO string or None,
          "metadata": { ... }
        }
        """
        return {
            "type": self.type,
            "input": self.input,
            "timestamp": self.timestamp.isoformat() if self.timestamp is not None else None,
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "InputPayload":
        """
        从字典恢复 InputPayload，具备向后兼容性：
        - 若缺少 'type'，视为旧格式，默认 type='nl' 并尝试使用 'text' 或 'backing' 字段作为 input（字符串）。
        - timestamp 使用 fromisoformat 解析；解析失败时记录异常并置为 None。
        - 对 input 进行容错修正：当 type=='nl' 且 input 非字符串时，使用 str(input)；当 type=='precedure' 且 input 非 dict 时，使用原始 data（或空 dict）作为 dict 表示。
        """
        # 解析 type，兼容老格式（缺失 type 时默认 nl）
        type_val = data.get("type")
        if type_val is None:
            type_val = "nl"
        # 提取原始 input 字段
        raw_input = data.get("input")
        # 兼容老格式：尝试使用 text 或 backing
        if type_val == "nl" and raw_input is None:
            raw_input = data.get("text") or data.get("backing")
        # timestamp 解析
        raw_ts = data.get("timestamp")
        timestamp: datetime.datetime | None
        if raw_ts is None:
            timestamp = None
        else:
            try:
                timestamp = datetime.datetime.fromisoformat(raw_ts)  # type: ignore[arg-type]
            except Exception as exc:
                logger.exception("无法解析输入 timestamp，置为 None：%s", exc)
                timestamp = None
        metadata = dict(data.get("metadata") or {})

        # 根据 type 进行类型修正/容错
        if type_val == "nl":
            if raw_input is None:
                input_val = ""
            elif isinstance(raw_input, str):
                input_val = raw_input
            else:
                # 尝试将非字符串转换为字符串，保证兼容性
                input_val = str(raw_input)
        else:  # precedure
            if isinstance(raw_input, dict):
                # 将 raw_input 明确构造为 dict[str, Any]（避免 dict[Unknown, Unknown] 警告）。
                # raw_input 来源于外部动态数据，类型检查器无法推断其键/值类型；为最小化 Pylance 报告，
                # 显式注解并在必要处使用单个 type: ignore[arg-type] 注释以说明原因。
                input_dict: dict[str, Any] = dict(raw_input)  # type: ignore[arg-type]
                input_val = input_dict
            else:
                # 使用整个原始 data 作为预置的 dict 表示，或回退为 {}
                try:
                    input_dict: dict[str, Any] = dict(data)
                    input_dict.pop("type", None)
                    input_val = input_dict
                except Exception as exc:
                    logger.exception("无法将原始数据转换为 dict 作为 precedure input：%s", exc)
                    input_val = {}

        return InputPayload(type=type_val, input=input_val, timestamp=timestamp, metadata=metadata)
  
 
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