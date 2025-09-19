# 终端 UI 集成与运行说明

## 概述
终端 UI 提供了一个基于终端的交互界面，用于发送请求到执行层并显示输出。UI 与核心执行层保持低耦合，通信通过可插拔的 IO 路由器 [`src/ui/io_router.py`](src/ui/io_router.py:1) 完成。IoRouter 负责通过 transport 将请求发送到后端并将响应封装为 OutputPayload 分发给已注册回调（send_request / 回调接收机制）。

主要职责：
- 接受用户输入（自然语言或程序化面板）并构建统一的 request dict。
- 将 request 通过 IoRouter 发送到后端（或注入的 transport）。
- 接收 IoRouter 分发的 OutputPayload 并渲染到界面。

## 依赖与安装
建议环境与主要依赖：
- Python 3.9+
- 终端 UI 运行依赖：textual

建议安装命令（示例）：
```python
pip install "textual"
```
说明：项目依赖管理由使用者自行处理，以上仅为最小运行所需的建议命令。

## 快速开始（步骤化）
前提假设：在项目根目录运行，且已安装 textual。

1. 使用示例运行入口（任选其一）：
   - 运行模块方式（假设在项目根）：
```python
python -m src.ui.run_terminal_ui
```
   - 或直接运行脚本（假设 Python 可找到 src 包）：
```python
python src/ui/run_terminal_ui.py
```
   以上示例基于示例入口文件 [`src/ui/run_terminal_ui.py`](src/ui/run_terminal_ui.py:1)。

2. 运行效果说明：
- 启动后会打开终端 UI（基于 textual）。常见键绑定：
  - 按键 n：唤起自然语言输入（提交为 {"text": "<内容>"}）
  - 按键 p：唤起程序化面板输入（单行 key=value,... 格式）
  - 按键 q：退出 UI
- 在程序化面板模式下，面板默认值可通过配置文件 [`config/panels/example_panel.yaml`](config/panels/example_panel.yaml:1) 提供的 default_values 预览。

## API 与扩展点
下面说明核心数据结构与可扩展点，便于在不同界面或平台间复用。

### OutputPayload
OutputPayload 定义见 [`src/ui/io_router.py`](src/ui/io_router.py:1)，结构主要字段：
- text: str（必填）——用于显示的文本内容
- timestamp: Optional[datetime]（可选）——响应时间，序列化为 ISO 字符串
- metadata: Dict[str, Any]（可选）——额外上下文

使用示例：回调中将 payload 转为字典进行网络/日志处理：
```python
def my_callback(output):
    data = output.to_dict()
    print(data["text"])
```

### IoRouter 与 transport 注入点
- IoRouter 在构造时接受一个异步 transport：async def transport(request: dict) -> dict。
- 默认 transport 为仓库内的模拟实现（短延迟返回示例响应），可在构造时替换以接入真实网络或执行器。

简短注入示例（2-3 行）：
```python
async def my_transport(req: dict) -> dict:
    return {"text": "ok", "timestamp": None}
router = IoRouter(transport=my_transport)
```

注册/注销回调：
- register_callback(callback) -> callback_id: str，用于接收 OutputPayload（同步或异步函数均可）。
- unregister_callback(callback_id) 在 UI 退出或不再需要时调用以避免泄露。

示例：注册额外回调（1 行）：
```python
cb_id = router.register_callback(lambda o: print(o.text))
```

### BaseUI 约定
BaseUI 定义见 [`src/ui/base_ui.py`](src/ui/base_ui.py:1)。子类必须遵守的约定：
- 构造时接收 router: IoRouter，BaseUI 会自动用 register_callback 注册内部异步回调并维护内部 asyncio.Queue。
- 必须实现：
  - async send_request(request: dict) -> None：对 request 做类型/字段校验后调用 router.send_request(request)。
  - async receive_output(output: OutputPayload) -> None：接收并处理/入队以供渲染。
- shutdown()：在 UI 退出时调用以 unregister callback（BaseUI 在 __init__ 时已注册）。

设计理由：保持 UI 层无网络/执行细节，将传输逻辑通过 transport 注入到 IoRouter 中，从而实现低耦合、多界面复用。

### TerminalTextualUI 行为要点
终端实现位于 [`src/ui/terminal_ui.py`](src/ui/terminal_ui.py:1)（类 TerminalTextualUI / TerminalApp）。
关键行为：
- panel_config：构造 TerminalTextualUI 时可传入 panel_config（通常从 YAML 配置解析得到），用于程序化面板的默认值与示例提示。
- 后台队列机制：IoRouter 通过回调将 OutputPayload 推送到 BaseUI 的 asyncio.Queue，TerminalApp 在后台任务中轮询该队列并写入 TextLog 用于渲染。
- 键绑定行为：按 n 显示自然语言输入框（提交构造 {"text": "..."}），按 p 显示程序化面板输入（单行 key=value,...），提交后调用 ui.send_request(req)。
- 启动方法：调用 ui.run_blocking() 会阻塞当前线程并启动 textual 应用（见示例 [`src/ui/run_terminal_ui.py`](src/ui/run_terminal_ui.py:1)）。

## 面板配置说明
示例配置文件：[`config/panels/example_panel.yaml`](config/panels/example_panel.yaml:1)。

主要字段：
- id: 面板唯一标识
- title: 显示标题（中文）
- description: 面板说明
- fields: 列表，定义每个请求字段的 name / type / label / placeholder / required / options（当 type == select）
- default_values: 用于预填充的示例值，UI 可用于占位提示或快速构建请求

简短示例片段说明 UI 如何解析为请求：
- 配置字段：action, target, count, verbose
- 用户在程序化面板输入 "action=query, target=user/123, count=2, verbose=true" 时，TerminalApp 的解析会构建为：
```python
req = {"action": "query", "target": "user/123", "count": "2", "verbose": "true"}
await ui.send_request(req)
```
注意：终端解析为字符串值，若调用方需要特定类型（int/bool），请在 transport 或后端执行器对字段进行类型转换与校验。

## 常见操作示例
- 注入自定义 transport 并启动 UI（3 行以内）：
```python
router = IoRouter(transport=custom_transport)
ui = TerminalTextualUI(router, panel_config={"action":"demo"})
ui.run_blocking()
```
- 在代码中注册额外回调（1 行）：
```python
cb_id = router.register_callback(lambda o: print(o.to_dict()))
```

## 扩展建议与注意事项
- 多界面并行设计要点：
  - 保持低耦合：所有界面（web/桌面/终端）应使用统一的 request dict 与统一的 OutputPayload，避免在 UI 层实现执行器逻辑。
  - transport 插件化：将各种传输方式作为可注入的 transport，以便不同界面共享 IoRouter。
- 禁止在 UI 层实现网络传输逻辑：网络/执行应通过 IoRouter 的 transport 注入实现，UI 仅负责构建请求与渲染输出。
- 错误与类型处理建议：UI 层可做最小输入校验，但类型转换与安全校验应在后端或 transport 层完成；遵循仓库 [`CODE_STYLE.md`](CODE_STYLE.md:1) 的异常与日志处理约定。

## 文件与目录引用
- [`src/ui/io_router.py`](src/ui/io_router.py:1)：IO 路由中心，定义 OutputPayload 与 IoRouter（transport 注入、回调注册分发）。
- [`src/ui/base_ui.py`](src/ui/base_ui.py:1)：抽象基类 BaseUI，负责回调注册、内部队列与 shutdown 约定。
- [`src/ui/terminal_ui.py`](src/ui/terminal_ui.py:1)：终端实现 TerminalTextualUI 与 TerminalApp（textual 逻辑、键绑定、队列轮询）。
- [`src/ui/run_terminal_ui.py`](src/ui/run_terminal_ui.py:1)：示例运行入口，展示如何注入 custom_transport 并启动 UI。
- [`config/panels/example_panel.yaml`](config/panels/example_panel.yaml:1)：面板配置示例（fields / default_values）。

## 参考与遵循
本文档编写遵循仓库设计文档 [`design.md`](design.md:1) 与代码风格规范 [`CODE_STYLE.md`](CODE_STYLE.md:1) 中的接口与注释约定，保持简洁、说明“为什么”以及如何使用。