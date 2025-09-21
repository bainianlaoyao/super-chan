"""Email fetcher package.

包含基础抓取器抽象与具体实现（如 OutlookFetcher）。
"""

from .base_fetcher import BaseEmailFetcher
from .outlook_fetcher import OutlookFetcher

__all__ = ["BaseEmailFetcher", "OutlookFetcher"]
