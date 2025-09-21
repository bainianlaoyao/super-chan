# BaseUI 抽象基类

## 概述

BaseUI 是 UI 层的抽象基类，提供统一的回调机制和生命周期管理。所有具体的 UI 实现都需要继承此类。

## 核心功能

### 回调注册管理

BaseUI 在初始化时自动注册异步回调到 IoRouter：

```python
class BaseUI:
    def __init__(self, router: IoRouter, name: str | None = None) -> None:
        self.router = router
        self.name = name or self.__class__.__name__
        self._queue: asyncio.Queue[OutputPayload] = asyncio.Queue()
        self._callback_id = self.router.register_callback(self._async_callback)
```

### 生命周期控制

- **初始化**：注册回调并存储回调ID
- **关闭**：注销回调并清理资源

```python
def shutdown(self) -> None:
    self.router.unregister_callback(self._callback_id)
```

### 异步回调处理

BaseUI 提供默认的异步回调实现，将输出放入内部队列：

```python
async def _async_callback(self, output: OutputPayload) -> None:
    await self.receive_output(output)
```

## 子类实现要求

所有继承 BaseUI 的子类必须实现以下抽象方法：

### send_request

发送请求到后端：

```python
async def send_request(self, payload: InputPayload) -> None:
    # 实现请求发送逻辑
    await self.router.send_request(payload)
```

### receive_output

处理后端响应：

```python
async def receive_output(self, output: OutputPayload) -> None:
    # 实现响应处理逻辑，通常是将输出放入队列
    await self._queue.put(output)
```

## 实现建议

### 队列消费模式

推荐在 UI 主循环中消费队列：

```python
# 在 UI 主循环中
async def main_loop(self):
    while True:
        output = await self._queue.get()
        # 处理输出并更新UI
        self.update_display(output)
```

### 错误处理

建议在子类中添加适当的错误处理：

```python
async def send_request(self, payload: InputPayload) -> None:
    try:
        await self.router.send_request(payload)
    except Exception as e:
        logger.exception("发送请求失败: %s", e)
        # 显示错误信息给用户
```

## 参考源码

- [`superchan/ui/base_ui.py`](superchan/ui/base_ui.py:1)