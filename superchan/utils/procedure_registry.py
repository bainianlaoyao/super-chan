from __future__ import annotations

"""全局 Procedure 注册表。

职责：
- 提供 register_procedure 与 get_registered_procedures 接口
- 在模块加载时，集中导入各处定义的 procedure，并完成注册

注意：避免循环依赖，不要从 core.executors 导入类型；这里自行定义签名别名。
"""

from collections.abc import Awaitable, Callable
from typing import Any

ProcedureFunc = Callable[[dict[str, Any], dict[str, Any] | None], Awaitable[Any]]

_REGISTRY: dict[str, ProcedureFunc] = {}


def register_procedure(name: str, func: ProcedureFunc) -> None:
    if not name:
        raise ValueError("procedure 名称不能为空")
    _REGISTRY[name] = func


def get_registered_procedures() -> dict[str, ProcedureFunc]:
    # 返回浅拷贝，避免外部直接修改内部表
    return dict(_REGISTRY)


# ---- 在此处集中导入并注册所有 procedure -----------------------------------
# 约定：每个模块导出公共别名 proc_xxx 供注册使用

try:
    from superchan.core.procedures.echo import proc_echo  # type: ignore
    register_procedure("echo", proc_echo)  # type: ignore[arg-type]
except Exception:
    # echo 为可选示例，缺失时忽略
    pass

try:
    from superchan.super_program.email.precedure.summerise_past_email import (
        proc_summerise_past_email,
    )  # type: ignore
    register_procedure("summerise_past_email", proc_summerise_past_email)  # type: ignore[arg-type]
except Exception:
    # 邮件汇总过程依赖 Outlook/LLM，环境不满足时允许跳过注册
    pass


__all__ = [
    "register_procedure",
    "get_registered_procedures",
]
