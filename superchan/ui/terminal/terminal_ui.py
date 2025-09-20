"""superchan.ui.terminal.terminal_ui

Terminal UI 实现模块。

该模块基于 Textual 框架提供完整的终端用户界面，包含：
- TerminalUI: 继承 BaseUI 并集成 Textual App，负责应用级管理
- DisplayPane: 历史消息显示区域，支持滚动和消息分类
- InputPane: 多行输入区域，支持 Ctrl+Enter 发送和 Enter 换行
- 完整的键盘绑定和消息路由功能

设计特点：
- 遵循文档约定的键位绑定（Ctrl+Enter 发送，Enter 换行，Ctrl+D/Ctrl+C 退出）
- 支持用户/系统消息的差异化显示
- 集成 IoRouter 进行消息路由和处理
- 提供优雅的错误处理和资源清理
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import TextArea, RichLog, Header, Footer, Static
from textual.events import Key

from superchan.ui.base_ui import BaseUI
from superchan.ui.io_router import IoRouter, OutputPayload, InputPayload

logger = logging.getLogger(__name__)


class SuperChanAsciiPanel(Static):
    """
    Super Chan ASCII Art 动画面板。
    
    显示 Super Chan 的 ASCII art 形象，支持：
    - 动态 ASCII art 动画
    - 状态变化（思考、说话、待机等）
    - 非阻塞的自由面板显示
    """
    
    # Super Chan ASCII Art 帧
    ASCII_FRAMES = [
        # 用户选择：兔子宝宝表情（版本 2）
        """
(\\_/)
(o.o)
 /   \\  """,
        """
(\\_/)
(-_-)
 /   \\  """,
        """
(\\_/)
(?.?)
 /   \\  """,
        """
(\\_/)
(^_^)
 /   \\  """
    ]
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.current_frame = 0
        self.animation_task: asyncio.Task[None] | None = None
        self.state = "normal"  # normal, thinking, speaking
    
    def on_mount(self) -> None:
        """面板挂载时启动动画"""
        self.update_display()
        self.start_animation()
    
    def update_display(self) -> None:
        """更新显示内容"""
        if self.state == "thinking":
            frame = self.ASCII_FRAMES[2]
        elif self.state == "speaking":
            frame = self.ASCII_FRAMES[3]
        else:
            frame = self.ASCII_FRAMES[self.current_frame % 2]  # 在帧 0 和 1 之间切换
        
        self.update(frame)
    
    def start_animation(self) -> None:
        """启动动画循环"""
        if self.animation_task is None or self.animation_task.done():
            self.animation_task = asyncio.create_task(self._animate_ascii())
    
    async def _animate_ascii(self) -> None:
        """ASCII art 动画循环"""
        try:
            while True:
                await asyncio.sleep(2.0)  # 每2秒切换一次
                if self.state == "normal":
                    self.current_frame = (self.current_frame + 1) % 2
                    self.update_display()
        except asyncio.CancelledError:
            pass
    
    def set_state(self, state: str) -> None:
        """设置状态：normal, thinking, speaking"""
        self.state = state
        self.update_display()
    
    def stop_ascii_animation(self) -> None:
        """停止动画"""
        if self.animation_task and not self.animation_task.done():
            self.animation_task.cancel()


class DisplayPane(Container):
    """
    历史消息显示区域的容器。
    
    包含：
    - 左侧的消息日志区域
    - 右上角的 ASCII art 面板
    """
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.message_log: MessageLog | None = None
        self.ascii_panel: SuperChanAsciiPanel | None = None
    
    def compose(self) -> ComposeResult:
        """构建显示面板的内部布局"""
        with Horizontal():
            # 左侧：消息日志（占 75% 宽度）
            self.message_log = MessageLog(id="message-log")
            yield self.message_log
            
            # 右侧：ASCII art 面板（占 25% 宽度）
            self.ascii_panel = SuperChanAsciiPanel(id="ascii-panel")
            yield self.ascii_panel
    
    def add_message(self, sender: str, text: str, timestamp: datetime.datetime | None = None) -> None:
        """添加消息到日志"""
        if self.message_log:
            self.message_log.add_message(sender, text, timestamp)
    
    def set_ascii_state(self, state: str) -> None:
        """设置 ASCII art 状态"""
        if self.ascii_panel:
            self.ascii_panel.set_state(state)


class MessageLog(RichLog):
    """
    消息日志组件。
    
    负责显示所有历史消息和系统输出，支持：
    - 按时间顺序显示消息（最新在下）
    - 用户消息右对齐，系统消息左对齐
    - 自动滚动到最新消息
    - 支持用户手动滚动回看历史
    """
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(wrap=True, markup=True, **kwargs)
        self.auto_scroll = True
    
    def add_message(self, sender: str, text: str, timestamp: datetime.datetime | None = None) -> None:
        """
        添加一条消息到显示区域。
        
        参数：
        - sender: 发送者（"user" 或 "system"）
        - text: 消息内容
        - timestamp: 时间戳，None 时使用当前时间
        """
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        
        # 格式化时间戳
        time_str = timestamp.strftime("%H:%M:%S") if timestamp else "??:??:??"
        
        # 根据发送者区分样式
        if sender == "user":
            # 用户消息右对齐，蓝色
            from rich.text import Text
            from rich.align import Align
            
            user_text = Text(f"[{time_str}] 你: {text}", style="blue")
            aligned_text = Align.right(user_text)
            self.write(aligned_text)
        else:
            # 系统消息左对齐，默认颜色
            self.write(f"[{time_str}] 系统: {text}")
        
        # 自动滚动到底部
        if self.auto_scroll:
            self.scroll_end()


class InputPane(TextArea):
    """
    多行输入区域。
    
    支持：
    - 多行文本输入
    - Ctrl+Enter 发送消息
    - Enter 普通换行
    - 自动调整高度
    """
    
    def __init__(self, terminal_ui: TerminalUI, **kwargs: Any) -> None:
        super().__init__(
            placeholder="输入你的消息... (Ctrl+Enter 发送)",
            show_line_numbers=False,
            **kwargs
        )
        self.terminal_ui = terminal_ui
    
    async def _on_key(self, event: Key) -> None:
        """处理键盘事件 - 使用内部 _on_key 方法"""
        # Ctrl+Enter 发送消息
        if event.key in ["ctrl+enter", 'pagedown', 'shift+enter']:
            text = self.text.strip()
            if text:
                # 直接异步调用发送消息
                await self._send_message(text)
            event.stop()  # 阻止事件传播
        else:
            # 其他按键交由父类处理
            await super()._on_key(event)
    
    async def _send_message(self, text: str) -> None:
        """异步发送消息"""
        try:
            await self.terminal_ui.send_message(text)
            self.clear()
        except Exception as e:
            logger.exception("发送消息时出错: %s", e)


class TerminalUIBase(BaseUI):
    """
    Terminal UI 的 BaseUI 具体实现。
    用于处理与 IoRouter 的集成。
    """
    
    def __init__(self, router: IoRouter, terminal_app: TerminalUI, name: str | None = None) -> None:
        super().__init__(router, name)
        self.terminal_app = terminal_app
    
    async def send_request(self, payload: InputPayload) -> None:
        """发送请求到 IoRouter"""
        await self.router.send_request(payload)
    
    async def receive_output(self, output: OutputPayload) -> None:
        """接收来自 IoRouter 的输出，转发给 terminal app"""
        # 将输出放入队列，由消息处理任务异步处理
        await self.queue.put(output)


class TerminalUI(App[None]):
    """
    Terminal UI 主应用类。
    
    使用组合模式集成 BaseUI 功能，提供完整的终端界面：
    - 上方显示历史消息
    - 下方多行输入框
    - 完整的键盘绑定支持
    """
    
    # CSS 样式文件
    CSS_PATH = "terminal_ui.tcss"
    
    # 应用级键盘绑定
    BINDINGS = [
        Binding("ctrl+d", "quit", "退出"),
        Binding("ctrl+c", "quit", "退出"),
    ]
    
    def __init__(self, router: IoRouter, name: str | None = None, **kwargs: Any) -> None:
        # 初始化 Textual App
        super().__init__(**kwargs)
        
        # 创建 BaseUI 实例用于处理 IoRouter 集成
        self.base_ui: TerminalUIBase | None = None
        self.router = router
        self._ui_name = name or "TerminalUI"
        
        # UI 组件引用
        self.display_pane: DisplayPane | None = None
        self.input_pane: InputPane | None = None
        
        # 消息处理任务
        self._message_task: asyncio.Task[None] | None = None
    
    @property
    def queue(self) -> asyncio.Queue[OutputPayload]:
        """获取消息队列"""
        if self.base_ui is None:
            raise RuntimeError("BaseUI 尚未初始化")
        return self.base_ui.queue
    
    def compose(self) -> ComposeResult:
        """构建 UI 布局"""
        yield Header(show_clock=True)
        
        # 主要垂直布局
        with Vertical():
            # 上方：显示区域（包含消息和 ASCII art）- 75% 高度
            self.display_pane = DisplayPane(id="display")
            yield self.display_pane
            
            # 下方：输入区域 - 25% 高度
            self.input_pane = InputPane(self, id="input")
            yield self.input_pane
        
        yield Footer()
    
    def on_mount(self) -> None:
        """应用启动时的初始化"""
        logger.info("Terminal UI 启动")
        
        # 初始化 BaseUI（必须在 on_mount 中进行，确保事件循环已运行）
        self.base_ui = TerminalUIBase(self.router, self, self._ui_name)
        
        # 显示欢迎消息
        if self.display_pane:
            self.display_pane.add_message(
                "system", 
                "欢迎使用 SuperChan Terminal UI! 输入消息并按 Ctrl+Enter 发送。"
            )
        
        # 聚焦到输入框
        if self.input_pane:
            self.input_pane.focus()
        
        # 启动消息处理任务
        self._start_message_processing()
    
    def shutdown(self) -> None:
        """清理资源"""
        if self.base_ui:
            self.base_ui.shutdown()
    
    def _start_message_processing(self) -> None:
        """启动消息处理后台任务"""
        self._message_task = asyncio.create_task(self._handle_output_messages())
    
    async def _handle_output_messages(self) -> None:
        """处理来自 IoRouter 的消息"""
        try:
            while True:
                # 从队列获取输出消息
                output = await self.queue.get()
                
                # 设置 ASCII art 为说话状态
                if self.display_pane:
                    self.display_pane.set_ascii_state("speaking")
                
                # 显示消息
                if self.display_pane:
                    self.display_pane.add_message(
                        "system",
                        output.text,
                        output.timestamp
                    )
                
                # 延迟一段时间后重置 ASCII art 状态
                await asyncio.sleep(1.0)
                if self.display_pane:
                    self.display_pane.set_ascii_state("normal")
                
        except asyncio.CancelledError:
            logger.info("消息处理任务被取消")
        except Exception as e:
            logger.exception("消息处理任务异常: %s", e)
    
    async def send_message(self, text: str) -> None:
        """
        发送用户消息。
        
        参数：
        - text: 用户输入的文本
        """
        try:
            # 在显示区域显示用户消息
            if self.display_pane:
                self.display_pane.add_message("user", text)
            
            # 设置 ASCII art 为思考状态
            if self.display_pane:
                self.display_pane.set_ascii_state("thinking")
            
            # 构造 InputPayload 并发送
            payload = InputPayload(
                type="nl",
                input=text,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            
            await self.send_request(payload)
            
        except Exception as e:
            logger.exception("发送消息失败: %s", e)
            if self.display_pane:
                self.display_pane.add_message("system", f"发送失败: {e}")
            # 重置 ASCII art 状态
            if self.display_pane:
                self.display_pane.set_ascii_state("normal")
    
    # 消息处理方法
    async def send_request(self, payload: InputPayload) -> None:
        """发送请求到 IoRouter"""
        if self.base_ui is None:
            raise RuntimeError("BaseUI 尚未初始化")
        await self.base_ui.send_request(payload)
    
    async def receive_output(self, output: OutputPayload) -> None:
        """接收来自 IoRouter 的输出"""
        # 将输出放入队列，由消息处理任务异步处理
        await self.queue.put(output)
    
    # Textual App 动作实现
    async def action_quit(self) -> None:
        """退出应用程序"""
        try:
            logger.info("正在退出 Terminal UI...")
            
            # 停止 ASCII art 动画（通过 DisplayPane）
            if self.display_pane and self.display_pane.ascii_panel:
                self.display_pane.ascii_panel.stop_ascii_animation()
            
            # 取消消息处理任务
            if self._message_task and not self._message_task.done():
                self._message_task.cancel()
                try:
                    await self._message_task
                except asyncio.CancelledError:
                    pass
            
            # 清理 BaseUI 资源
            self.shutdown()
            
            # 退出应用
            self.exit()
            
        except Exception as e:
            logger.exception("退出应用程序失败: %s", e)
            # 强制退出
            self.exit()


def run_terminal_ui(router: IoRouter | None = None) -> None:
    """
    启动 Terminal UI 的便利函数。
    
    参数：
    - router: IoRouter 实例，None 时创建默认实例
    """
    if router is None:
        router = IoRouter()
    
    app = TerminalUI(router, "TerminalUI")
    app.run()


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行应用
    run_terminal_ui()