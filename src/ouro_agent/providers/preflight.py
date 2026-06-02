"""Offline readiness checks for configured providers."""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from ouro_agent.config.model import DEFAULT_API_KEY_ENV, OuroConfig, SUPPORTED_PROVIDERS

_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
}
_PLACEHOLDER_MODELS = {"", "mock-smart", "your-model-name"}


@dataclass(frozen=True)
class ProviderPreflight:
    provider: str
    model: str
    api_key_env: str
    env_present: bool
    base_url: str
    api_version: str
    timeout_seconds: int
    max_retries: int
    issues: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.issues


def provider_preflight(
    config: OuroConfig,
    *,
    env: Mapping[str, str] | None = None,
) -> ProviderPreflight:
    """Check provider readiness without making a network request.

    This check reads only environment variable presence, never values.
    """
    env_map = os.environ if env is None else env
    provider = config.provider
    model = config.model.strip()
    api_key_env = config.api_key_env or DEFAULT_API_KEY_ENV.get(provider, "")
    base_url = _effective_base_url(config)
    issues: list[str] = []

    if provider not in SUPPORTED_PROVIDERS:
        issues.append(f"unsupported provider: {provider}")

    if provider == "mock":
        return ProviderPreflight(
            provider=provider,
            model=model or "mock-smart",
            api_key_env="",
            env_present=False,
            base_url="",
            api_version="",
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            issues=tuple(issues),
        )

    if model in _PLACEHOLDER_MODELS:
        issues.append("set a real model name before using a real provider")

    if not api_key_env:
        issues.append("set api_key_env to an environment variable name")
    elif not bool(env_map.get(api_key_env, "").strip()):
        issues.append(f"environment variable {api_key_env} is not set")

    if provider == "openai-compatible" and not base_url:
        issues.append("openai-compatible requires base_url")

    return ProviderPreflight(
        provider=provider,
        model=model,
        api_key_env=api_key_env,
        env_present=bool(api_key_env and env_map.get(api_key_env, "").strip()),
        base_url=base_url,
        api_version=config.api_version,
        timeout_seconds=config.timeout_seconds,
        max_retries=config.max_retries,
        issues=tuple(issues),
    )


def _effective_base_url(config: OuroConfig) -> str:
    if config.provider == "openai-compatible":
        return config.base_url.strip()
    return config.base_url.strip() or _DEFAULT_BASE_URLS.get(config.provider, "")
