"""Persist OuroConfig as a small TOML file.

The store reads with stdlib ``tomllib`` and writes a hand-rolled TOML emitter
to avoid a hard dependency on a TOML writer. The store is the only place that
knows the on-disk layout of config; callers use ``OuroConfig`` only.
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from ouro_agent.config.model import (
    DEFAULT_CONFIG,
    FORBIDDEN_FIELDS,
    OuroConfig,
    ConfigError,
)
from ouro_agent.i18n import DEFAULT_LANGUAGE, label

_CONFIG_FILENAME = "config.toml"


def config_path(override: Path | None = None) -> Path:
    if override is not None:
        return override
    env_dir = os.environ.get("OURO_AGENT_HOME")
    if env_dir:
        return Path(env_dir) / _CONFIG_FILENAME
    return Path.home() / ".ouro_agent" / _CONFIG_FILENAME


def load_config(path: Path | None = None) -> OuroConfig:
    target = config_path(path)
    if not target.exists():
        return DEFAULT_CONFIG
    with target.open("rb") as fp:
        raw = tomllib.load(fp)
    cfg_table = raw.get("ouro_agent", {})
    if not isinstance(cfg_table, dict):
        raise ConfigError(f"{target}: [ouro_agent] table must be a mapping")
    config = DEFAULT_CONFIG
    for key, value in cfg_table.items():
        if key in FORBIDDEN_FIELDS:
            raise ConfigError(
                f"{target}: refusing to load forbidden field '{key}'. "
                "API keys must come from environment variables."
            )
        try:
            config = config.with_field(key, value)
        except ConfigError as err:
            raise ConfigError(f"{target}: {err}") from err
    return config


def save_config(config: OuroConfig, path: Path | None = None) -> Path:
    target = config_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_render_toml(config), encoding="utf-8")
    return target


def set_field(name: str, value: Any, path: Path | None = None) -> OuroConfig:
    config = load_config(path).with_field(name, value)
    save_config(config, path)
    return config


def redacted_view(
    config: OuroConfig, language: str = DEFAULT_LANGUAGE
) -> dict[str, str]:
    """Return a display dict that never includes anything resembling a secret."""
    return {
        "provider": config.provider,
        "model": config.model,
        "api_key_env": config.api_key_env or label("config_api_key_env_unset", language),
        "api_key_value": label("config_api_key_value_note", language),
        "base_url": config.base_url or "-",
        "api_version": config.api_version or "-",
        "timeout_seconds": str(config.timeout_seconds),
        "max_retries": str(config.max_retries),
        "trace_level": config.trace_level,
        "unicode_mode": "true" if config.unicode_mode else "false",
        "language": config.language,
    }


def _render_toml(config: OuroConfig) -> str:
    lines = [
        "# Ouro Agent local configuration.",
        "# This file MUST NOT contain plaintext API keys.",
        "# Use api_key_env to point at an environment variable name instead.",
        "",
        "[ouro_agent]",
    ]
    for key, value in config.to_dict().items():
        lines.append(f"{key} = {_format_toml_value(value)}")
    lines.append("")
    return "\n".join(lines)


def _format_toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'
