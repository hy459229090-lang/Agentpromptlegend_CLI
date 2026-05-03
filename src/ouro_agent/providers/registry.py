"""Build a Provider from configuration and add a runtime safety net.

`build_provider` returns the configured provider unchanged. The CLI wraps
that result in `FallbackOnErrorProvider` so a network or auth failure during
combat degrades to the mock provider for the rest of the battle, with a
visible note in the log and trace.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ouro_agent.config.model import OuroConfig, SUPPORTED_PROVIDERS
from ouro_agent.i18n import DEFAULT_LANGUAGE
from ouro_agent.providers.anthropic import AnthropicProvider
from ouro_agent.providers.base import Provider, ProviderError, ModelTurnResult
from ouro_agent.providers.mock import MockProvider
from ouro_agent.providers.openai import OpenAIProvider
from ouro_agent.providers.openai_compatible import OpenAICompatibleProvider

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ouro_agent.llm.prompt import PromptContext


def build_provider(
    config: OuroConfig,
    *,
    seed: int = 0,
    force_mock: bool = False,
    language: str = DEFAULT_LANGUAGE,
) -> Provider:
    if force_mock or config.provider == "mock":
        return MockProvider(
            model=config.model or "mock-smart", seed=seed, language=language
        )

    if config.provider not in SUPPORTED_PROVIDERS:
        raise ProviderError(f"unsupported provider '{config.provider}'")

    if config.provider == "openai":
        return OpenAIProvider(
            model=config.model,
            api_key_env=config.api_key_env or "OPENAI_API_KEY",
            base_url=config.base_url or "https://api.openai.com/v1",
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )

    if config.provider == "anthropic":
        return AnthropicProvider(
            model=config.model,
            api_key_env=config.api_key_env or "ANTHROPIC_API_KEY",
            base_url=config.base_url or "https://api.anthropic.com",
            api_version=config.api_version or "2023-06-01",
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )

    if config.provider == "openai-compatible":
        if not config.base_url:
            raise ProviderError(
                "openai-compatible requires a base_url. "
                "Set it with: ouro config set base_url <url>"
            )
        return OpenAICompatibleProvider(
            model=config.model,
            base_url=config.base_url,
            api_key_env=config.api_key_env or "OURO_API_KEY",
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
        )

    raise ProviderError(f"provider '{config.provider}' has no adapter")


class FallbackOnErrorProvider(Provider):
    """Wrap any provider so that runtime failures fall back to mock for the rest of the battle.

    The first error is recorded so the CLI can show "switched to mock" once.
    """

    def __init__(self, primary: Provider, fallback: Provider):
        self.primary = primary
        self.fallback = fallback
        self.name = primary.name
        self.error: str | None = None
        self._tripped = False

    @property
    def model(self) -> str:
        return getattr(self.primary, "model", "?")

    def request_turn(self, prompt: "PromptContext") -> ModelTurnResult:
        if self._tripped:
            return self.fallback.request_turn(prompt)
        try:
            return self.primary.request_turn(prompt)
        except ProviderError as err:
            self.error = str(err)
            self._tripped = True
            return self.fallback.request_turn(prompt)
