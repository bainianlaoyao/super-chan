"""superchan.ui.push

推送 UI 模块包。

本包内的 UI 仅承担“输出接收（receive_output）”职责，不产生输入；
它们继承自 BaseUI，但 send_request 是无操作（no-op）。

当前内置：
- BasePushUI: 推送 UI 抽象基类
- ServerChanUI: ServerChan 渠道的推送 UI（需要 api_key 初始化）
"""

from .base_push_ui import BasePushUI
from .serverchan_ui import ServerChanUI

__all__ = [
    "BasePushUI",
    "ServerChanUI",
]
