"""Anthropic Messages API provider adapter.

Posts to ``<base_url>/v1/messages`` with Anthropic's Messages payload shape.
We send **both** ``x-api-key`` (Anthropic's official header) and
``Authorization: Bearer ...`` so the same adapter works against the official
Anthropic API and against Anthropic-compatible bridges (e.g. dashscope's
``/apps/anthropic`` endpoint), where the bridge typically expects a Bearer
token under ``ANTHROPIC_AUTH_TOKEN``.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ouro_agent.providers.base import (
    EchoUsage,
    ModelTurnResult,
    Provider,
    ProviderError,
)
from ouro_agent.providers.http import http_post_json, safe_get

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ouro_agent.llm.prompt import PromptContext


DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com"
DEFAULT_API_KEY_ENV = "ANTHROPIC_API_KEY"
DEFAULT_API_VERSION = "2023-06-01"
DEFAULT_MAX_TOKENS = 512


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(
        self,
        *,
        model: str,
        api_key_env: str = DEFAULT_API_KEY_ENV,
        base_url: str = DEFAULT_ANTHROPIC_BASE_URL,
        api_version: str = DEFAULT_API_VERSION,
        timeout_seconds: float = 30.0,
        max_retries: int = 1,
    ):
        if not model:
            raise ProviderError("Anthropic provider requires a non-empty model name")
        self._model = model
        self._api_key_env = api_key_env or DEFAULT_API_KEY_ENV
        self._base_url = (base_url or DEFAULT_ANTHROPIC_BASE_URL).rstrip("/")
        self._api_version = api_version or DEFAULT_API_VERSION
        self._timeout = float(timeout_seconds)
        self._max_retries = int(max_retries)

    @property
    def model(self) -> str:
        return self._model

    def _read_key(self) -> str:
        key = os.environ.get(self._api_key_env, "").strip()
        if not key:
            raise ProviderError(
                f"environment variable '{self._api_key_env}' is not set; "
                "the engine refuses to call a real provider without a key."
            )
        return key

    def request_turn(self, prompt: "PromptContext") -> ModelTurnResult:
        key = self._read_key()
        url = f"{self._base_url}/v1/messages"
        body: dict = {
            "model": self._model,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": 0.4,
            **prompt.to_anthropic_payload(),
        }
        headers = {
            "x-api-key": key,
            "Authorization": f"Bearer {key}",
            "anthropic-version": self._api_version,
        }
        response = http_post_json(
            url,
            headers=headers,
            payload=body,
            timeout=self._timeout,
            max_retries=self._max_retries,
        )

        text = _extract_text(response.body)
        usage = response.body.get("usage", {}) or {}
        in_tokens = int(usage.get("input_tokens", 0) or 0)
        out_tokens = int(usage.get("output_tokens", 0) or 0)
        echo = EchoUsage(
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            total_tokens=in_tokens + out_tokens,
            cached_tokens=int(usage.get("cache_read_input_tokens", 0) or 0),
            latency_ms=response.latency_ms,
        )
        return ModelTurnResult(
            provider=self.name,
            model=self._model,
            raw_text=text,
            usage=echo,
        )


def _extract_text(body: dict) -> str:
    """Pull the first text block out of an Anthropic Messages response."""
    content = body.get("content")
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return str(block.get("text", ""))
    if isinstance(content, str):
        return content
    return safe_get(body, "completion", default="") or ""
