"""Configuration data model.

Rules:
* `provider` is mandatory; mock is the safe default.
* `api_key_env` only stores the name of an environment variable, never a key.
* No field accepts a plaintext API key.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ouro_agent.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES

SUPPORTED_PROVIDERS: tuple[str, ...] = (
    "mock",
    "openai",
    "anthropic",
    "openai-compatible",
)

DEFAULT_API_KEY_ENV: dict[str, str] = {
    "mock": "",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai-compatible": "OURO_API_KEY",
}

MUTABLE_FIELDS: frozenset[str] = frozenset(
    {
        "provider",
        "model",
        "api_key_env",
        "base_url",
        "api_version",
        "timeout_seconds",
        "max_retries",
        "trace_level",
        "unicode_mode",
        "language",
    }
)

FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {
        "api_key",
        "openai_api_key",
        "anthropic_api_key",
        "secret",
        "secret_key",
        "token",
    }
)


class ConfigError(ValueError):
    """Raised when a config field violates the rules."""


@dataclass(frozen=True)
class OuroConfig:
    provider: str = "mock"
    model: str = "mock-smart"
    api_key_env: str = ""
    base_url: str = ""
    api_version: str = ""
    timeout_seconds: int = 30
    max_retries: int = 2
    trace_level: str = "L0"
    unicode_mode: bool = False
    language: str = DEFAULT_LANGUAGE

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key_env": self.api_key_env,
            "base_url": self.base_url,
            "api_version": self.api_version,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "trace_level": self.trace_level,
            "unicode_mode": self.unicode_mode,
            "language": self.language,
        }

    def with_field(self, name: str, value: Any) -> "OuroConfig":
        if name in FORBIDDEN_FIELDS:
            raise ConfigError(
                f"refusing to store '{name}'. API keys are read from environment "
                "variables; only set 'api_key_env' to the variable name."
            )
        if name not in MUTABLE_FIELDS:
            raise ConfigError(f"unknown config field: {name}")

        coerced = _coerce(name, value)
        if name == "provider" and coerced not in SUPPORTED_PROVIDERS:
            raise ConfigError(
                f"provider must be one of {', '.join(SUPPORTED_PROVIDERS)}; "
                f"got {coerced!r}"
            )
        if name == "api_key_env" and isinstance(coerced, str):
            if coerced.startswith("sk-") or coerced.startswith("sk_"):
                raise ConfigError(
                    "api_key_env stores a variable NAME (e.g. 'OPENAI_API_KEY'), "
                    "not the key itself."
                )
        if name == "trace_level" and coerced not in {"L0", "L1", "L2"}:
            raise ConfigError("trace_level must be one of L0, L1, L2")
        if name == "language" and coerced not in SUPPORTED_LANGUAGES:
            raise ConfigError(
                f"language must be one of {', '.join(SUPPORTED_LANGUAGES)}; got {coerced!r}"
            )
        return replace(self, **{name: coerced})


DEFAULT_CONFIG = OuroConfig()


def _coerce(name: str, value: Any) -> Any:
    if name in {"timeout_seconds", "max_retries"}:
        try:
            return int(value)
        except (TypeError, ValueError) as err:
            raise ConfigError(f"{name} must be an integer") from err
    if name == "unicode_mode":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        return bool(value)
    return str(value).strip()
