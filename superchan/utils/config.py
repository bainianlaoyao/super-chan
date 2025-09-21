from __future__ import annotations

"""User configuration loader for Super-Chan.

支持从环境变量 SUPERCHAN_CONFIG 指定的路径或默认的 config/user.toml 读取配置。
支持以 ${ENV:VAR_NAME} 形式引用环境变量并进行展开。
"""

import os
from dataclasses import dataclass, field
from typing import Any, cast

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover - 3.10 fallback (当前项目为 3.13，无需触发)
    tomllib = None  # type: ignore


@dataclass
class LLMConfig:
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


@dataclass
class AnimeStyleConfig:
    system_prompt: str | None = None


@dataclass
class UserConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    anime_style: AnimeStyleConfig = field(default_factory=AnimeStyleConfig)


def _expand_env(value: Any) -> Any:
    """展开 ${ENV:VAR} 模式的值；非字符串原样返回。"""
    if not isinstance(value, str):
        return value
    if value.startswith("${ENV:") and value.endswith("}"):
        var = value[6:-1]
        return os.environ.get(var, "")
    return value


def _expand_mapping(obj: Any) -> Any:
    if isinstance(obj, dict):
        d = cast(dict[Any, Any], obj)
        out: dict[str, Any] = {}
        for k in list(d.keys()):
            ks = str(k)
            out[ks] = _expand_mapping(d[k])
        return out
    if isinstance(obj, list):
        seq = cast(list[Any], obj)
        lst: list[Any] = []
        for v in seq:
            lst.append(_expand_mapping(v))
        return lst
    return _expand_env(obj)


def _to_llm_config(section: dict[str, Any] | None) -> LLMConfig:
    sec = section or {}
    sec = _expand_mapping(sec)
    return LLMConfig(
        provider=str(sec.get("provider") or "") or None,
        model=str(sec.get("model") or "") or None,
        base_url=str(sec.get("base_url") or "") or None,
        api_key=str(sec.get("api_key") or "") or None,
    )


def _to_anime_style_config(section: dict[str, Any] | None, legacy_anime: dict[str, Any] | None = None) -> AnimeStyleConfig:
    # 合并新旧结构，优先使用新结构 anime_style
    merged: dict[str, Any] = {}
    if legacy_anime:
        merged.update(legacy_anime)
    if section:
        merged.update(section)
    sec = _expand_mapping(merged)
    return AnimeStyleConfig(
        system_prompt=str(sec.get("system_prompt") or "") or None,
    )


def load_user_config(root_dir: str) -> UserConfig:
    """加载用户配置。

    优先读取环境变量 SUPERCHAN_CONFIG 指定的 TOML 文件，
    否则读取 `config/user.toml`。
    """
    cfg_path = os.environ.get("SUPERCHAN_CONFIG")
    if not cfg_path:
        cfg_path = os.path.join(root_dir, "config", "user.toml")

    data: dict[str, Any] = {}
    if tomllib is None:
        # 理论上不会走到这里（py>=3.13），加上防御逻辑
        raise RuntimeError("Python 环境缺少 tomllib，无法解析 TOML 配置")

    try:
        with open(cfg_path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        # 若文件不存在，返回默认空配置
        data = {}

    llm = _to_llm_config(data.get("llm"))
    anime_style = _to_anime_style_config(data.get("anime_style"), data.get("anime"))
    return UserConfig(llm=llm, anime_style=anime_style)
