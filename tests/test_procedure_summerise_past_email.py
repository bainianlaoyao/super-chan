from __future__ import annotations

"""Integration test (manual-friendly) for summerise_past_email procedure.

该测试旨在运行真实环境下的过程：
- 需要 Windows + Outlook + pywin32
- 需要正确配置的 LLM（z-ai-sdk-python + API Key + 模型名）

注意：
- 该测试不会进行强断言，更多用于人工调试与输出检查。
- 当环境不满足时将跳过。
"""

import os
import platform
import asyncio
from typing import cast
import pytest  # type: ignore[import-not-found]

from superchan.core.executors import build_default_programmatic_executor


def _env_ready() -> tuple[bool, list[str]]:
    warnings: list[str] = []
    if platform.system().lower() != "windows":
        warnings.append("非 Windows 平台，Outlook 抓取不可用")
        return False, warnings
    try:
        import win32com.client  # type: ignore  # noqa: F401
    except Exception:
        warnings.append("缺少 pywin32 (win32com)")
        return False, warnings

    # LLM 配置检查（可选，只给出提示，不因此跳过）
    # 如果使用全局 [llm]，至少应提供 API Key & model；此处不强判
    return True, warnings


def test_run_summerise_past_email_smoke() -> None:
    ready, warns = _env_ready()
    if not ready:
        # 在缺少 pytest 类型提示的环境下，跳过类型检查
        pytest.skip("环境不满足: " + "; ".join(warns))  # type: ignore[attr-defined]

    exe = build_default_programmatic_executor()

    params = {
        "past_days": 0,
        "past_hours": 24,
        "fetcher": "outlook",
        "folder": os.environ.get("TEST_EMAIL_FOLDER", "Inbox"),
        "unread_only": False,
        "limit": int(os.environ.get("TEST_EMAIL_LIMIT", "20")),
    }

    result = asyncio.run(exe.execute("summerise_past_email", params, metadata={"source": "pytest"}))

    # 仅做轻量断言，确保结构存在
    assert result.type == "dict"
    assert isinstance(result.output, dict)
    out = result.output  # type: ignore[assignment]
    assert "markdown" in out
    assert "total_emails" in out
    assert "summarised" in out
    assert "time_used" in out
    assert "warnings" in out

    # 打印关键信息，便于人工检查
    print("\n--- summerise_past_email output summary ---")
    print(f"total: {out['total_emails']}, summarised: {out['summarised']}, time_used: {out['time_used']:.2f}s")
    w = cast(list[str], out.get("warnings") or [])
    if w:
        print("warnings:")
        for msg in w:
            print(" -", msg)
    print("\ntext preview (first 400 chars):\n")
    md = out.get("text", "")
    if isinstance(md, str):
        print(md[:400])
    else:
        print(str(md)[:400])

if __name__ == "__main__":
    test_run_summerise_past_email_smoke()