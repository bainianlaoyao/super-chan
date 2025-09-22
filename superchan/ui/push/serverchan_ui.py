from __future__ import annotations

"""ServerChan push UI (sctapi.ftqq.com) — 仅结构与初始化配置。

注意：本文件仅提供结构与初始化校验，不包含具体网络实现。
"""
import requests
import re
from typing import Any
import asyncio
import logging


from superchan.ui.io_router import OutputPayload, IoRouter
from superchan.ui.push.base_push_ui import BasePushUI


class ServerChanUI(BasePushUI):
    """ServerChan 推送 UI。

    初始化所需：api_key（即 sendkey）。
    """

    def __init__(self, router: IoRouter, api_key : str, name: str | None = None) -> None:
        if not api_key:
            # 严格要求配置按 CODE_STYLE：依赖不满足应直接退出/抛错
            raise RuntimeError("缺少 ServerChan api_key，请在配置 push.serverchan.api_key 设置")

        super().__init__(router, name or "serverchan")

        # 保存必要配置（仅存储，不进行实际发送）
        self.api_key: str = api_key

        self.logger = logging.getLogger(__name__)

    async def receive_output(self, output: OutputPayload) -> None:  # pragma: no cover - network side-effect
        """接收 OutputPayload 并推送至 ServerChan（始终发送）。"""
        try:
            # 通用渠道过滤：若声明了 channels 且不包含当前 UI 名称，则跳过
            if not self.allow_by_channels(output):
                return
            title, content = self._build_message(output)
            # 使用线程池避免在事件循环中执行阻塞的 urllib 调用
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._post_message, title, content)
        except Exception as exc:  # 记录但不吞异常细节
            self.logger.exception("ServerChan 推送失败: %s", exc)

    # ---------- internals ----------

    def _build_message(self, output: OutputPayload) -> tuple[str, str]:
        if output.type =='text':
            text = str(output.output)
        elif output.type == 'dict' and isinstance(output.output, dict):
            text = output.output.get('text', '未获取到文本')
        else:
            text = "解析失败: " + str(output.output)
        md = output.metadata or {}
        # 标题优先级：push_serverchan.title > push.title > command_name/source > 默认
        title = (
            md.get("source", 'superchan')+ " 来信: "
        )

        # 内容优先级：push_serverchan.content > push.content > output 内容格式化
        content = text

        return title, content

    def _post_message(self, title: str, content: str) -> None:
        options = {"tags": "苏帕酱"}  # 可选参数

        self.sc_send(self.api_key, title, content, options)

    @staticmethod
    def sc_send(sendkey: str, title: str, desp: str = '', options: dict[str, Any] | None = None) -> dict[str, Any]:
        if options is None:
            options = {}
        if sendkey.startswith('sctp'):
            match = re.match(r'^sctp(\d+)t', sendkey)
            if match:
                url = f'https://{match.group(1)}.push.ft07.com/send/{sendkey}.send'
            else:
                raise ValueError("Invalid sendkey format for 'sctp'.")
        else:
            url = f'https://sctapi.ftqq.com/{sendkey}.send'
        params = {
            'title': title,
            'desp': desp,
            **options
        }
        headers = {
            'Content-Type': 'application/json;charset=utf-8'
        }
        response = requests.post(url, json=params, headers=headers)
        result = response.json()
        return result
