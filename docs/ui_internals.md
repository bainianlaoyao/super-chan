# UI 内部与通用约定（UI Internals）

本文档基于源码实现准确记录 UI 层与 IO 路由的内部契约与扩展点。主要参考实现：[`superchan/ui/io_router.py`](superchan/ui/io_router.py:1)、[`superchan/ui/base_ui.py`](superchan/ui/base_ui.py:1)、[`superchan/ui/terminal/terminal_ui.py`](superchan/ui/terminal/terminal_ui.py:1)。

目次：OutputPayload、InputPayload、IoRouter、transport 注入点、BaseUI、panel 配置、并发与生命周期、终端 UI 关系。

---

## OutputPayload（输出载荷）

源码定义参考：[`superchan/ui/io_router.py`](superchan/ui/io_router.py:1)。

字段（准确列出源码类型与语义）：
- text: str（必填）——用于渲染的主要文本。
- timestamp: datetime.datetime | None（可选）——源码使用 timezone-aware UTC 或 None；序列化为 ISO 字符串。to_dict() 返回 ISO 字符串或 None；from_dict() 接受 ISO 字符串并尝试用 datetime.fromisoformat 解析，解析失败时记录异常并置为 None（依据源码实现）。
- metadata: dict[str, Any]（可选，默认空 dict）——任意扩展字段；to_dict() 返回 metadata 的浅拷贝。

行为细节：
- to_dict() 返回 {"text": self.text, "timestamp": ISO 或 None, "metadata": dict(self.metadata)}。
- from_dict(data) 会从 data.get("text") 读取 text；若缺失则以 str(data) 作为后备 text。timestamp 使用 datetime.fromisoformat 解析，失败时记录异常并置为 None；metadata 使用 dict(data.get("metadata") or {})。

回调使用示例（使用源码签名）：
```python
from superchan.ui.io_router import OutputPayload, IoRouter, InputPayload

async def my_async_cb(output: OutputPayload) -> None:
    print(output.text)

def my_sync_cb(output: OutputPayload) -> None:
    print(output.to_dict())

router = IoRouter()
cb_id_async = router.register_callback(my_async_cb)  # 返回 str
cb_id_sync = router.register_callback(my_sync_cb)    # 返回 str
```

---

## InputPayload（输入载荷）

源码定义参考：[`superchan/ui/io_router.py`](superchan/ui/io_router.py:1)。

字段与语义（源码精确）：
- type: Literal["precedure", "nl"] —— 注意源码使用 'precedure'（拼写即为字面值），必须严格使用该字面值或兼容层处理。
- input: str | dict[str, Any] —— 当 type == "nl" 时应为 str；当 type == "precedure" 时应为 dict。构造时 __post_init__ 会校验，类型不符时抛出 TypeError。
- timestamp: datetime.datetime | None —— 可选，序列化为 ISO 或 None。
- metadata: dict[str, Any] —— 可选，默认空 dict。

行为细节：
- to_dict() 返回字段并将 timestamp 序列化为 ISO 字符串或 None。
- from_dict(data) 提供向后兼容：若缺少 'type'，默认 type='nl'，并尝试使用 'text' 或 'backing' 作为 input；对非期望类型会做容错转换（例如将非字符串转换为 str，或将原始 data 转为 dict 作为 precedure 的 input），解析 timestamp 失败时记录异常并置 None（依据源码实现）。

示例构造与发送（源码签名：IoRouter.send_request 接受 InputPayload）：
```python
from superchan.ui.io_router import InputPayload, IoRouter
import datetime

router = IoRouter()
req = InputPayload(type="nl", input="Hello", timestamp=datetime.datetime.now(datetime.timezone.utc))
await router.send_request(req)
```

---

## IoRouter（精确契约）

源码定义参考：[`superchan/ui/io_router.py`](superchan/ui/io_router.py:1)。

构造函数：
- __init__(self, transport: TransportCallable | None = None) -> None  
  - transport 类型别名 TransportCallable = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]（即 async callable 接受 dict 并返回 dict）。若未提供，使用 _default_transport。

主要方法与签名（源码精确）：
- async def send_request(self, request: InputPayload) -> None  
  - 要求传入 InputPayload 实例；函数体中调用 request.to_dict()，然后 await self._transport(req)，再将返回值转换为 dict 并通过 OutputPayload.from_dict 生成 OutputPayload，最后 await self._dispatch_output(payload)。  
  - 注意：源码中未对 transport 异常做捕获，transport 抛出的异常将传播到调用者（依据源码实现）。

- def register_callback(self, callback: CallbackType) -> str  
  - CallbackType = AsyncCallback | SyncCallback，其中 AsyncCallback = Callable[[OutputPayload], Coroutine[Any, Any, None]]，SyncCallback = Callable[[OutputPayload], None]。  
  - 行为：验证 callback 可调用，生成 callback_id: str（uuid.uuid4().hex），然后在事件循环中通过 create_task 异步执行内部 _register() 将 callback 写入 self._callbacks（若不存在运行中事件循环，则使用 asyncio.run(_register())）。返回 callback_id（同步返回，注册操作是调度到事件循环中执行的，非阻塞等待注册完成）。

- def unregister_callback(self, callback_id: str) -> None  
  - 行为：调度异步 _unregister()（在事件循环中 create_task 或 asyncio.run）以从 self._callbacks 弹出该 id；函数同步返回（注销为调度式，非阻塞）。

行为与并发模型：
- 内部使用 self._lock: asyncio.Lock 保护对 self._callbacks 的访问；register/unregister 使用异步函数在锁内修改字典。
- 输出分发由 async def _dispatch_output(self, output: OutputPayload) 执行：复制回调列表后对每个回调：
  - 若 inspect.iscoroutinefunction(cb) 为 True，则将协程作为 task 提交到当前事件循环：loop.create_task(coro)。
  - 否则将同步回调提交到线程池：loop.run_in_executor(None, sync_cb, output).
- 所有任务通过 asyncio.gather(..., return_exceptions=True) 等待完成，并对结果中出现的异常（gather 返回的异常对象）使用 logger.exception 记录，但不会向外抛出（依据源码：回调异常被记录，send_request 的调用者不会收到回调内异常）。

任务调度与错误传播注意：
- register_callback / unregister_callback 是“调度注册/注销”而非同步完成；调用后立即返回 callback_id 或 None，但在极端无事件循环环境下会使用 asyncio.run 执行注册/注销同步到当前线程。文档应提醒调用方注册后可能需要短暂等待回调确实生效（依据源码实现）。
- send_request 直接 await transport；transport 的异常会直接传播到 send_request 的调用者，IoRouter 仅在回调分发阶段捕获并记录回调内错误。

transport 注入点（源码精确签名与约定）：
- 类型别名：TransportCallable = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]
- 推荐实现签名（与源码一致）：
```python
async def transport(request: dict[str, Any]) -> dict[str, Any]:
    # 返回一个可由 OutputPayload.from_dict 解析的 dict
    return {"text": "ok", "timestamp": "2025-01-01T00:00:00+00:00", "metadata": {}}
```
- 返回值约定：应返回 dict[str, Any]，其中至少可提取用于 OutputPayload 的字段（text、timestamp、metadata）；IoRouter 会用 dict(response_any) 将 transport 返回值构造为 dict。
- 错误处理建议：transport 内部应捕获并转换错误为标准化 dict 或直接抛出以由上层决定；注意：send_request 未对 transport 异常做捕获，调用方应准备处理 transport 抛出的异常（依据源码实现）。

---

## BaseUI（精确约定）

源码定义参考：[`superchan/ui/base_ui.py`](superchan/ui/base_ui.py:1)。

构造参数与成员（源码精确）：
- __init__(self, router: IoRouter, name: str | None = None) -> None  
  - router: IoRouter（必填）。name 为可选字符串，默认使用类名。
- 成员：
  - self.router: IoRouter
  - self.name: str
  - self._queue: asyncio.Queue[OutputPayload] —— 源码使用 asyncio.Queue[OutputPayload] 作为内部传递队列。
  - self._callback_id: str —— register_callback 返回值。

生命周期与回调包装（源码精确）：
- __init__ 在构造时调用 self.router.register_callback(self._async_callback) 并存储返回的 callback_id。register 是以调度方式执行（参见 IoRouter.register_callback 的行为说明）。
- self._async_callback(self, output: OutputPayload) -> None 为协程函数（源码定义 async），其默认行为为 await self.receive_output(output)。
- 子类必须实现：
  - async def send_request(self, payload: InputPayload) -> None
  - async def receive_output(self, output: OutputPayload) -> None
- shutdown(self) -> None：调用 self.router.unregister_callback(self._callback_id)。源码在异常时会 re-raise。

实现建议（依据源码行为）：
- 推荐以异步回调注册（BaseUI 已用 async _async_callback），以便 IoRouter 在其事件循环中 create_task 执行；如果需要同步回调，需实现线程安全的转发到主 loop。
- 子类常见做法：在 receive_output 中把 output 放入 self._queue（例如 self._queue.put_nowait(output)），并在 UI 的主循环中消费该队列并渲染。

示例（构建请求与发送，示例使用源码签名）：
```python
from superchan.ui.base_ui import BaseUI
from superchan.ui.io_router import InputPayload

class MyUI(BaseUI):
    async def send_request(self, payload: InputPayload) -> None:
        # 这里可以做最小校验，然后直接调用 router.send_request
        await self.router.send_request(payload)

    async def receive_output(self, output):
        # 将输出放入队列以供主渲染循环消费
        self._queue.put_nowait(output)
```

---

## 面板配置（panels）格式（与源码示例对应）

示例配置参考：[`superchan/config/panels/example_panel.yaml`](superchan/config/panels/example_panel.yaml:1)。

源码并未强制统一的 schema，但仓库示例使用的约定如下（按示例精确列出）：
- id: str（必填）
- title: str（可选）
- description: str（可选）
- fields: list[dict]（必填），每个字段包含示例子字段：
  - name: str（必填）：用于构建请求的 key
  - type: "string" | "integer" | "boolean" | "select"（示例中使用这些字面值）
  - label: str（可选）
  - placeholder: str（可选）
  - required: bool（可选）
  - options: list（当 type == "select" 时存在）
- default_values: dict（可选）

语义与类型转换责任（依据源码与示例）：
- 仓库示例中的 UI 通常以字符串化的输入构建请求（终端输入常为字符串）；示例实现中请假定后端/transport 负责把字符串转换为具体类型（例如 "2" -> int）。
- 如果 UI 在客户端做类型转换，则必须捕获转换异常并向用户反馈；否则应交由 transport/后端处理（依据源码注释）。

程序化解析示例（将面板字段构造成 InputPayload）：
```python
from superchan.ui.io_router import InputPayload

# 假设从面板 UI 收到字符串化字段
values = {"action": "query", "target": "user/123", "count": "2", "verbose": "true"}
# 将程序化请求作为 precedure 类型的 dict 负载发送
payload = InputPayload(type="precedure", input=values)
await router.send_request(payload)
```

---

## 并发、队列与后台任务（源码行为）

- IoRouter 使用 asyncio.Lock 保护回调表的并发访问，分发使用当前事件循环的任务与线程池（见 _dispatch_output 的实现）。
- BaseUI 使用 asyncio.Queue[OutputPayload] 作为回调到 UI 主循环间的缓冲，建议主循环以非阻塞方式轮询（例如 await queue.get() 或用 asyncio.create_task 消费）。
- 回调分发对回调异常的处理策略为记录（logger.exception）但不抛出；transport 异常在 send_request 时会向上抛出（依据源码实现）。

---

## 与 Terminal UI 文档的关系

- 下面列出属于终端呈现实现细节、建议在 [`docs/terminal_ui.md`](docs/terminal_ui.md:1) 中仅以 API 概览或简短引用出现的函数/参数/行为：  
  - IoRouter.register_callback / unregister_callback 的使用说明（在 ui_internals 中详述注册行为与并发语义，终端文档只需展示如何调用与示例）。  
  - BaseUI._async_callback、BaseUI.queue 的消费策略（ui_internals 中说明队列契约，终端文档仅列出消费示例）。  
  - 面板渲染与用户输入解析的细节（例如格式化、交互提示、分页），这些属于终端实现，docs/terminal_ui.md 中保留简短说明并链接到本页以获取协议细节。  
  - 任何终端特有的渲染优化、着色或交互控制（例如分屏、流式更新策略），仅在终端文档中记录实现提示，不在本页重复具体实现细节。

---

参考源码文件：[`superchan/ui/io_router.py`](superchan/ui/io_router.py:1)、[`superchan/ui/base_ui.py`](superchan/ui/base_ui.py:1)、（终端实现参考但仓库未找到文件时亦保留引用）[`superchan/ui/terminal/terminal_ui.py`](superchan/ui/terminal/terminal_ui.py:1)。

文档结束。