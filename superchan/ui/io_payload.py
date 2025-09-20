
"""superchan.ui.io_payload

模块说明：
该模块定义了在 UI 与后台/执行器之间传输的载荷数据结构（payloads）。
目标是提供简单、可序列化且向后兼容的输入/输出载荷表示。

主要内容：
- OutputPayload: UI 层接收/显示的输出对象，包含文本、时间戳和可选元数据。
- InputPayload: 由 UI/上层构造并发送到执行业务或 transport 的输入对象，支持两种语义：
    - "nl": 自然语言文本输入（字符串）
    - "precedure": 过程型输入（字典表示的结构化数据）

设计要点：
- 序列化：提供 to_dict/from_dict 方法，将 datetime 使用 ISO-8601 字符串表示，便于 JSON 序列化/传输。
- 容错与向后兼容：from_dict 实现中尽量兼容旧格式（例如缺少 "type" 字段或使用 "text"/"backing" 字段），并在解析失败时进行安全回退，以保证调用方不会因单个字段格式问题崩溃。
- 类型安全：在构造时对 InputPayload 做最小的运行时检查（通过 __post_init__），确保 type 与 input 的一致性；deserialize 时尽量对输入进行修正以兼容外部数据。

使用示例：
>>> p = InputPayload(type="nl", input="Hello")
>>> d = p.to_dict()
>>> p2 = InputPayload.from_dict(d)

注意事项：
- 时间戳采用 timezone-unaware 或 timezone-aware 的 ISO 字符串皆可解析，解析失败会被记录并回退为 None。
- from_dict 在解析时会记录异常（假设模块中存在 logger 变量）但不会抛出以保持鲁棒性；调用端如需严格校验应在接收后自行验证字段。

导出符号：OutputPayload, InputPayload
"""


from __future__ import annotations

import dataclasses
import datetime

from dataclasses import dataclass

from typing import Literal, Any
import logging

# 模块级 logger，用于记录 from_dict 解析时的异常信息。
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
  

