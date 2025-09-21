# IoRouter 消息路由

IoRouter 是 UI 层与后端之间的消息路由中间件，负责请求发送、响应分发和回调管理。

## 核心功能

### 请求发送

```python
async def send_request(self, request: InputPayload) -> None:
    # 将 InputPayload 序列化为字典
    req_dict = request.to_dict()
    # 发送到 transport
    response_dict = await self._transport(req_dict)
    # 构造 OutputPayload
    output = OutputPayload.from_dict(response_dict)
    # 分发到所有回调
    await self._dispatch_output(output)
```

### 回调管理

支持同步和异步回调的注册和注销：

```python
# 注册回调
callback_id = router.register_callback(my_callback)

# 注销回调
router.unregister_callback(callback_id)
```

## Transport 接口

### 类型定义

```python
TransportCallable = Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]
```

Transport 是一个异步函数，接受请求字典，返回响应字典。

### 默认实现

如果未提供 transport，使用默认的模拟实现：

```python
async def _default_transport(self, request: dict[str, Any]) -> dict[str, Any]:
    # 模拟后端响应
    return {
        "text": f"收到请求: {request}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": {}
    }
```

## 并发与错误处理

### 并发安全

- 使用 `asyncio.Lock` 保护回调表
- 支持多个并发请求
- 回调分发使用任务池

### 错误处理策略

- Transport 异常会传播到调用者
- 回调执行异常被记录但不影响其他回调
- 使用 `asyncio.gather(..., return_exceptions=True)` 收集异常

## 回调分发机制

### 异步回调

```python
async def _dispatch_output(self, output: OutputPayload) -> None:
    callbacks = list(self._callbacks.values())
    tasks = []

    for callback in callbacks:
        if inspect.iscoroutinefunction(callback):
            # 异步回调：创建任务
            task = asyncio.create_task(callback(output))
            tasks.append(task)
        else:
            # 同步回调：使用线程池
            task = asyncio.get_event_loop().run_in_executor(None, callback, output)
            tasks.append(task)

    # 等待所有任务完成
    await asyncio.gather(*tasks, return_exceptions=True)
```

### 回调类型

```python
CallbackType = Union[
    Callable[[OutputPayload], Coroutine[Any, Any, None]],  # 异步回调
    Callable[[OutputPayload], None]                        # 同步回调
]
```

## 实现注意事项

### 事件循环处理

- 自动检测当前事件循环
- 支持在无事件循环环境下的同步操作
- 回调注册是异步调度的

### 性能优化

- 回调列表复制避免并发修改
- 支持回调的惰性清理
- 异常隔离不影响正常流程

## 参考源码

- [`superchan/ui/io_router.py`](superchan/ui/io_router.py:1)