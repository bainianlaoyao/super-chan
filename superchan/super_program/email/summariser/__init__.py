"""Email summariser package.

导出摘要器基类与 LLM 摘要器实现。
"""

from .base_summariser import BaseSummariser
from .llm_summariser import LLMSummariser

__all__ = ["BaseSummariser", "LLMSummariser"]
