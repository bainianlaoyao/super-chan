from __future__ import annotations

"""Base class for push-only UIs.

该抽象类代表“只接收输出的 UI”。
- 继承 BaseUI，保持与 IoRouter 的回调/队列机制一致；
- send_request 是 no-op（推送 UI 不产生输入）；
- 子类实现 receive_output 来执行推送逻辑。
"""

from abc import ABC, abstractmethod
from typing import Any, cast

from superchan.ui.base_ui import BaseUI
from superchan.ui.io_router import InputPayload, OutputPayload, IoRouter


class BasePushUI(BaseUI, ABC):
    """推送 UI 抽象基类：只接收输出，不发送输入。

    构造签名：
    - router: IoRouter
    - config: dict[str, Any]  渠道初始化配置（例如 api_key 等）
    - name: str | None
    """

    def __init__(self, router: IoRouter,  name: str | None = None) -> None:
        super().__init__(router, name)

    async def send_request(self, payload: InputPayload) -> None:  # pragma: no cover - not used for push UI
        """推送 UI 不发送请求，留空实现。"""
        return None

    @abstractmethod
    async def receive_output(self, output: OutputPayload) -> None:
        """子类需要实现：接收并处理输出（执行推送）。"""
        raise NotImplementedError

    # --- common helpers for push UIs ---
    def allow_by_channels(self, output: OutputPayload) -> bool:
        """
        通用过滤：基于 OutputPayload.metadata.push.channels 与 self.name 决定是否允许继续。

        规则：
        - 若 metadata.push.channels 存在且为非空列表，则当且仅当包含 self.name 时允许；
        - 若未提供 channels 或为空，则默认拒绝。

        """
        md_any: Any = output.metadata or {}
        if isinstance(md_any, dict):
            md: dict[str, Any] = cast(dict[str, Any], md_any)
        else:
            md = {}

        push_any: Any = md.get("push")
        if isinstance(push_any, dict):
            push: dict[str, Any] = cast(dict[str, Any], push_any)
        else:
            push = {}

        channels_list_any: Any = push.get("channels")
        if isinstance(channels_list_any, list):
            channels_raw: list[Any] = cast(list[Any], channels_list_any)
        else:
            channels_raw = []
        # 仅保留字符串项
        channels: list[str] = [x for x in channels_raw if isinstance(x, str)]

        # 无显式 channels 时，默认拒绝（严格模式）
        if not channels:
            return False
        return self.name in channels
