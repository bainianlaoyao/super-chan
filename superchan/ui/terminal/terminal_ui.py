"""src/ui/terminal_ui.py

基于 textual 的最小终端 UI 实现（TerminalTextualUI）。

变更说明（兼容最新 textual）：
- 用 Static 替代已弃用的 TextLog，维护行缓冲并使用 Static.update 渲染；
- 将 Button 点击处理改为 on_button_pressed 事件处理；
- 调整 bind 调用参数和 Input 构造以匹配新版 API；放宽事件对象访问以兼容不同版本。
"""
from __future__ import annotations

import asyncio
from typing import Any, cast

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Static

from superchan.ui.base_ui import BaseUI
from superchan.ui.io_router import IoRouter, OutputPayload, InputPayload


class TerminalTextualUI(BaseUI):
    """
    基于 textual 的终端 UI。

    参数：
    - router: IoRouter（必填）
    - panel_config: 可选 dict，用于程序化请求面板默认值（当前只做存储与展示）
    - name: 可选 UI 名称
    """

    def __init__(self, router: IoRouter, panel_config: dict[str, Any] | None = None, name: str | None = None) -> None:
        super().__init__(router=router, name=name)
        self.panel_config: dict[str, Any] = panel_config or {}
        self._app: TerminalApp | None = None

    async def send_request(self, payload: InputPayload) -> None:
        """
        将外部构造的 dict 包装为类型安全的 InputPayload，然后传给 IoRouter.send_request。

        原因：IoRouter.send_request 现在严格接受 InputPayload，直接传 dict 会触发静态类型错误。
        """

        await self.router.send_request(payload)

    async def receive_output(self, output: OutputPayload) -> None:
        await self.queue.put(output)

    def run_blocking(self) -> None:
        self._app = TerminalApp(self)
        self._app.run()

    def start(self) -> None:
        self.run_blocking()


class TerminalApp(App[Any]):
    """
    textual 应用内部实现（简化）。

    结构：
    - Static (输出区域，替代 TextLog)
    - Input (hidden by default)
    - Button 行：显示当前快捷键提示（可交互）
    """

    CSS_PATH = None  # 不依赖外部样式文件

    def __init__(self, ui: TerminalTextualUI, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # 明确成员类型
        self.ui: TerminalTextualUI = ui
        self.display_queue: asyncio.Queue[OutputPayload] = ui.queue
        self.log_widget: Any = None
        self.input_widget: Any = None
        self.mode: str | None = None  # "natural" | "programmatic" | None
        self._output_lines: list[str] = []
        self._poll_task: asyncio.Task[Any] | None = None

        # 绑定键：新版 textual bind 只接受 key 与 action 两个位置参数
        self.bind("n", "natural_input")
        self.bind("p", "program_panel")
        self.bind("q", "quit")

    def compose(self) -> ComposeResult:
        # 不在构造时传 visible 参数，以保持与新版 API 兼容
        yield Vertical(
            Static("按 n 唤起自然语言输入；按 p 唤起程序化面板；按 q 退出", id="help"),
            Static("", id="output"),
            Horizontal(Button("自然输入 (n)", id="btn_n"), Button("程序化面板 (p)", id="btn_p"), id="controls"),
            Input(placeholder="输入并回车提交", id="input"),
        )

    async def on_mount(self) -> None:
        # 获取引用并进行类型转换（cast）以避免类型检查错误
        self.log_widget = cast(Static | None, self.query_one("#output"))
        self.input_widget = cast(Input | None, self.query_one("#input"))
        # 初始隐藏输入框（通过属性，不在构造时指定）
        if self.input_widget is not None:
            try:
                self.input_widget.visible = False
            except Exception:
                # 兼容更老/新版本：若无 visible 属性，尝试通过 styles 控制显示
                try:
                    self.input_widget.styles.display = "none"  # type: ignore[attr-defined]
                except Exception:
                    pass
        # 启动后台任务轮询 display_queue
        self._poll_task = asyncio.create_task(self._poll_display_queue())

    async def on_unmount(self) -> None:
        # 停止后台任务
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        # 调用上层 shutdown（若有异常让上层处理）
        self.ui.shutdown()

    async def _poll_display_queue(self) -> None:
        """
        在后台轮询 BaseUI 的队列并将 OutputPayload 渲染到输出区域。
        """
        while True:
            payload: OutputPayload = await self.display_queue.get()
            text = payload.text if payload and getattr(payload, "text", None) is not None else str(payload)
            self._output_lines.append(text)
            if len(self._output_lines) > 200:
                self._output_lines = self._output_lines[-200:]
            if self.log_widget:
                # 使用 Static.update 渲染全部行
                self.log_widget.update("\n".join(self._output_lines))

    # Action: 自然输入
    def action_natural_input(self) -> None:
        self.mode = "natural"
        if self.input_widget:
            self.input_widget.value = ""
            try:
                self.input_widget.visible = True
            except Exception:
                try:
                    self.input_widget.styles.display = None  # type: ignore[attr-defined]
                except Exception:
                    pass
            self.input_widget.placeholder = "输入自然语言并回车提交（提交为 {'text': '<内容>'}）"
            self.set_focus(self.input_widget)

    # Action: 程序化面板（简化为 single-line key=value,... 格式）
    def action_program_panel(self) -> None:
        self.mode = "programmatic"
        if self.input_widget:
            self.input_widget.value = ""
            default_example = "k=v, a=b"
            if self.ui and getattr(self.ui, "panel_config", None):
                try:
                    default_example = ", ".join(f"{k}={v}" for k, v in self.ui.panel_config.items())
                except Exception:
                    default_example = "k=v, a=b"
            try:
                self.input_widget.visible = True
            except Exception:
                try:
                    self.input_widget.styles.display = None  # type: ignore[attr-defined]
                except Exception:
                    pass
            self.input_widget.placeholder = f"程序化面板: {default_example}（格式 key=value,...）"
            self.set_focus(self.input_widget)

    async def on_input_submitted(self, event: Any) -> None:
        """
        处理 Input 回车提交事件。兼容不同版本的事件对象。
        """
        raw_value = getattr(event, "value", None)
        if raw_value is None:
            inp = getattr(event, "input", None)
            raw_value = getattr(inp, "value", "") if inp is not None else ""
        raw = str(raw_value).strip()

        # 隐藏输入框并清理模式
        if self.input_widget:
            try:
                self.input_widget.visible = False
            except Exception:
                try:
                    self.input_widget.styles.display = "none"  # type: ignore[attr-defined]
                except Exception:
                    pass
        mode = self.mode
        self.mode = None

        if not raw:
            return

        if mode == "natural":
            req = {"text": raw}
        elif mode == "programmatic":
            req: dict[str, Any] = {}
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
                    req[k.strip()] = v.strip()
                else:
                    req.setdefault("text", "")
                    req["text"] += (part + " ")
            if "text" in req:
                req["text"] = req["text"].strip()
        else:
            req = {"text": raw}

        # 按原行为异步发送请求：先用类型安全的 InputPayload 包装
        asyncio.create_task(self.ui.send_request(InputPayload.from_dict(req)))

    async def action_quit(self) -> None:
        # async 确保签名与 App 基类兼容
        self.exit()

    async def on_button_pressed(self, event: Any) -> None:
        """
        处理按钮按下事件，兼容不同版本的事件属性。
        使用属性比较（duck-typing）代替 isinstance 检查：优先使用 event.button.id，
        若不存在则尝试把 event.sender 作为字符串候选直接比较常量。
        """
        # 优先尝试 event.button，再尝试 event.sender
        btn = getattr(event, "button", None)
        if btn is None:
            btn = getattr(event, "sender", None)
        btn_id = getattr(btn, "id", None) if btn is not None else None

        # 若没有从 button.id 获取到值，尝试把 event.sender 作为字符串候选直接比较
        if not btn_id and hasattr(event, "sender"):
            sender_val = getattr(event, "sender")
            try:
                # 使用直接比较判断是否为预期的按钮 id（对非字符串对象通常返回 False）
                if sender_val == "btn_n" or sender_val == "btn_p":
                    btn_id = sender_val
            except Exception:
                # 保护性捕获：若 sender_val 无法与字符串比较，忽略并继续
                pass

        # 最终判断并触发对应动作（使用直接比较，避免 isinstance）
        try:
            if btn_id == "btn_n":
                self.action_natural_input()
            elif btn_id == "btn_p":
                self.action_program_panel()
        except Exception:
            # 理论上比较不会抛异常；若抛出则记录并忽略，保持行为向后兼容
            pass