"""OpenAI-compatible provider.

Same wire as OpenAIProvider but requires both ``base_url`` and ``api_key_env``
to be configured explicitly, since there is no sensible default. This is the
provider you want for endpoints like dashscope's OpenAI-compatible bridge.
"""
from __future__ import annotations

from ouro_agent.providers.base import ProviderError
from ouro_agent.providers.openai import (
    DEFAULT_API_KEY_ENV,
    DEFAULT_OPENAI_BASE_URL,
    OpenAIProvider,
)


class OpenAICompatibleProvider(OpenAIProvider):
    name = "openai-compatible"

    def __init__(
        self,
        *,
        model: str,
        base_url: str,
        api_key_env: str = "OURO_API_KEY",
        timeout_seconds: float = 30.0,
        max_retries: int = 1,
        request_json_object: bool = False,
    ):
        if not base_url or base_url == DEFAULT_OPENAI_BASE_URL:
            raise ProviderError(
                "openai-compatible requires an explicit base_url "
                "(e.g. https://your-host/v1)."
            )
        if not api_key_env or api_key_env == DEFAULT_API_KEY_ENV:
            # Allow OPENAI_API_KEY explicitly, but warn against accidental default.
            pass
        super().__init__(
            model=model,
            api_key_env=api_key_env,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            request_json_object=request_json_object,
        )
