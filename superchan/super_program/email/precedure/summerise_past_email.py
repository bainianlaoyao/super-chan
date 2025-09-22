from __future__ import annotations

"""Procedure: summerise_past_email

抓取过去一段时间内的邮件，逐封调用 LLM 进行原子总结，
并按优先级生成带有文首导读的 Markdown 汇总文档。

输入（params）：
- past_days: int >= 0（默认 0）
- past_hours: int >= 0（默认 24；当两者皆为 0 时按 24 小时处理）
- fetcher: str，默认 "outlook"
- folder: str，默认 "Inbox"
- unread_only: bool，默认 False
- limit: int，默认 100；<=0 视为不限制

输出（OutputPayload.type == "dict"）：
{
  markdown: str,
  total_emails: int,
  summarised: int,
  time_used: float,
  warnings: list[str],
}
"""

import asyncio
import time
import datetime as _dt
from typing import Any
from pathlib import Path

from superchan.ui.io_payload import OutputPayload
from superchan.utils.config import load_user_config, LLMConfig
from superchan.super_program.email.fetcher.outlook_fetcher import OutlookFetcher
from superchan.super_program.email.summariser.llm_summariser import LLMSummariser
from superchan.super_program.email.models import EmailMessage, Summary


def _calc_since(past_days: int, past_hours: int) -> _dt.datetime:
	if past_days <= 0 and past_hours <= 0:
		past_hours = 24
	now = _dt.datetime.now(_dt.timezone.utc)
	delta = _dt.timedelta(days=max(0, past_days), hours=max(0.0, float(past_hours)))
	return now - delta


def _priority_order(p: str) -> int:
	mapping = {"high": 0, "medium": 1, "low": 2}
	return mapping.get(p.lower(), 1)


def _render_markdown(lead: str, summaries: list[Summary]) -> str:
	lines: list[str] = []
	lines.append("# 邮件汇总")
	if lead.strip():
		lines.append("")
		lines.append("> 导读：")
		for ln in lead.strip().splitlines():
			lines.append(f"> {ln}")

	# 按优先级分组渲染
	by_priority: dict[str, list[Summary]] = {"high": [], "medium": [], "low": []}
	for s in summaries:
		by_priority.setdefault(s.priority.lower(), []).append(s)

	for prio in ("high", "medium", "low"):
		bucket = by_priority.get(prio, [])
		if not bucket:
			continue
		lines.append("")
		title_map = {"high": "高优先级", "medium": "中等优先级", "low": "低优先级"}
		lines.append(f"## {title_map.get(prio, prio)} ({len(bucket)})")
		for s in bucket:
			lines.append("")
			t = s.title.strip() or "(无标题)"
			lines.append(f"### {t}")
			if s.category:
				lines.append(f"- 类别: `{s.category}`")
			if s.keywords:
				kw = ", ".join(s.keywords)
				lines.append(f"- 关键词: {kw}")
			if s.action_items:
				lines.append("- 行动项:")
				for ai in s.action_items:
					lines.append(f"  - {ai}")
			if s.content:
				lines.append("")
				lines.append(s.content)

	return "\n".join(lines).strip() + "\n"


async def _proc_summerise_past_email(params: dict[str, Any], metadata: dict[str, Any] | None) -> OutputPayload:
	start = time.perf_counter()
	warnings: list[str] = []

	# 1) 解析参数
	past_days = 0
	past_hours = 24
	try:
		past_days = max(0, int(params.get("past_days", 0) or 0))
	except Exception:
		warnings.append("参数 past_days 非法，已回退为 0")
		past_days = 0
	try:
		past_hours = max(0, int(params.get("past_hours", 24) or 24))
	except Exception:
		warnings.append("参数 past_hours 非法，已回退为 24")
		past_hours = 24

	fetcher_name = str(params.get("fetcher", "outlook") or "outlook").lower()
	folder = str(params.get("folder", "Inbox") or "Inbox")
	unread_only = bool(params.get("unread_only", False))
	limit_raw = params.get("limit", 100)
	try:
		limit = int(limit_raw)
	except Exception:
		warnings.append("参数 limit 非法，已回退为 100")
		limit = 100
	if limit <= 0:
		limit = None  # 不限制

	since = _calc_since(past_days, past_hours)

	# 2) 构造依赖（配置 -> fetcher + summariser）
	# 读取用户配置（用于 LLM 和 OutlookFetcher 选项）
	# 尽量定位到仓库根目录（.../super_chan），以便读取 config/user.toml
	try:
		# 文件位于 superchan/super_program/email/precedure/summerise_past_email.py
		# parents[4] -> 仓库根目录（包含 config/）
		repo_root = str(Path(__file__).resolve().parents[4])
	except Exception:
		repo_root = "."
	cfg = load_user_config(root_dir=repo_root)

	# 构造 summariser（使用 email.summariser 或全局 LLM）
	if cfg.email.summariser.use_global_llm:
		llm_cfg: LLMConfig = cfg.llm
	else:
		llm_cfg = LLMConfig(
			provider=cfg.email.summariser.provider,
			model=cfg.email.summariser.model,
			base_url=cfg.email.summariser.base_url,
			api_key=cfg.email.summariser.api_key,
		)
	try:
		summariser = LLMSummariser(llm_cfg)
	except Exception as exc:
		used = time.perf_counter() - start
		return OutputPayload(
			output={
				"text": "# 邮件汇总\n\n> 无法初始化 LLM 摘要器，请检查 LLM 依赖与配置（z-ai-sdk-python、API Key、模型名）。\n",
				"total_emails": 0,
				"summarised": 0,
				"time_used": used,
				"warnings": warnings + [f"初始化摘要器失败: {exc}"]
			},
			type="dict",
			metadata=metadata or {},
		)

	# 构造 fetcher（目前仅 outlook）
	if fetcher_name not in {"outlook", "default"}:
		warnings.append(f"暂不支持的 fetcher: {fetcher_name}，已回退为 outlook")
	try:
		profile = cfg.email.fetcher_outlook.profile_name
		fetcher = OutlookFetcher(profile_name=profile)
	except Exception as exc:
		used = time.perf_counter() - start
		return OutputPayload(
			output={
				"text": "# 邮件汇总\n\n> 无法初始化 Outlook 抓取器，请检查依赖（Windows/Outlook/pywin32）。\n",
				"total_emails": 0,
				"summarised": 0,
				"time_used": used,
				"warnings": warnings + [f"初始化抓取器失败: {exc}"]
			},
			type="dict",
			metadata=metadata or {},
		)

	# 3) 抓取邮件并按时间过滤
	emails: list[EmailMessage] = []
	try:
		fetched = fetcher.fetch(folder=folder or cfg.email.fetcher_outlook.default_folder,
								unread_only=bool(unread_only or cfg.email.fetcher_outlook.unread_only),
								limit=limit)
		# 仅保留 since 之后的邮件
		for m in fetched:
			ts = m.timestamp
			# Outlook 的 ReceivedTime 可能为 naive，本地时间；做最小化处理：若无 tzinfo，视为本地时间并转换到 UTC
			if ts is None:
				continue
			if ts.tzinfo is None:
				# 假设为本地时间
				local = ts.astimezone()  # 将 naive 视为本地（Python 会将 naive 当作本地时间）
				ts_utc = local.astimezone(_dt.timezone.utc)
			else:
				ts_utc = ts.astimezone(_dt.timezone.utc)
			if ts_utc >= since:
				emails.append(m)
	except Exception as exc:
		used = time.perf_counter() - start
		return OutputPayload(
			output={
				"text": "# 邮件汇总\n\n> 抓取邮件失败。\n",
				"total_emails": 0,
				"summarised": 0,
				"time_used": used,
				"warnings": warnings + [f"抓取失败: {exc}"]
			},
			type="dict",
			metadata=metadata or {},
		)

	total = len(emails)
	if total == 0:
		used = time.perf_counter() - start
		return OutputPayload(
			output={
				"text": "# 邮件汇总\n\n> 指定时间范围内未找到邮件。\n",
				"total_emails": 0,
				"summarised": 0,
				"time_used": used,
				"warnings": warnings,
			},
			type="dict",
			metadata=metadata or {},
		)

	# 4) 逐封原子总结（并行限制）
	sem = asyncio.Semaphore(1)

	async def _one(msg: EmailMessage) -> Summary | None:
		try:
			async with sem:
				return await summariser.summarise(msg)
		except Exception as exc:
			warnings.append(f"摘要失败: {msg.message_id}: {exc}")
			return None

	tasks = [asyncio.create_task(_one(m)) for m in emails]
	results = await asyncio.gather(*tasks)
	summaries: list[Summary] = [s for s in results if s is not None]

	# 5) 先渲染 Markdown（不含导读），再基于该 Markdown 发起单独的 LLM 请求生成导读，并插入到最前部
	# 5.1) 汇总 Markdown：按优先级排序渲染（lead 为空）
	summaries.sort(key=lambda s: (_priority_order(s.priority), s.generated_at))
	base_markdown = _render_markdown("", summaries)

	# 5.2) 基于已渲染的 Markdown 调用 LLM 生成导读
	try:
		# 为避免提示过长，适度裁剪（保留前 6000 字符）
		md_for_prompt = base_markdown
		if len(md_for_prompt) > 6000:
			md_for_prompt = md_for_prompt[:6000] + "\n..."

		lead_prompt = (
			"下面是一份按优先级分组的邮件汇总 Markdown。"
			"请基于其内容生成一个简短导读（中文，30-80 字），"
			"概括关键信息与优先处理建议。请只返回导读文本，不要包含其他解释。\n\n"
			"```markdown\n" + md_for_prompt + "\n```"
		)
		# 使用 summariser 的 LLM 配置发起独立请求
		lead_text = await summariser.llm(lead_prompt, model=summariser.llm_cfg.model)  # type: ignore[arg-type]
		lead_text = str(lead_text).strip()
	except Exception as exc:
		warnings.append(f"导读生成失败: {exc}")
		lead_text = ""

	# 5.3) 将导读插入到最终 Markdown 顶部（紧随一级标题后）
	if lead_text:
		lead_block = "> 导读：\n" + "\n".join("> " + ln for ln in lead_text.splitlines()) + "\n\n"
		lines = base_markdown.splitlines(keepends=True)
		if lines and lines[0].lstrip().startswith("# "):
			# 在首行标题后插入导读
			markdown = "".join([lines[0], "\n", lead_block, *lines[1:]])
		else:
			# 找不到标题时，直接前置
			markdown = lead_block + base_markdown
	else:
		markdown = base_markdown

	used = time.perf_counter() - start
	return OutputPayload(
		output={
			"text": markdown,
			"total_emails": total,
			"summarised": len(summaries),
			"time_used": used,
			"warnings": warnings,
		},
		type="dict",
		metadata=metadata or {},
	)


# 公共别名，便于外部在不破坏私有约定的情况下进行注册
proc_summerise_past_email = _proc_summerise_past_email

__all__ = ["proc_summerise_past_email", "_proc_summerise_past_email"]

