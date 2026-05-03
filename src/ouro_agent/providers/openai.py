"""OpenAI Chat Completions provider adapter.

Uses the Chat Completions wire (``POST <base_url>/chat/completions``). Works
unchanged against any "OpenAI-compatible" endpoint by setting ``base_url`` and
``api_key_env``; ``OpenAICompatibleProvider`` is a thin subclass that just
forces those two to be set explicitly.

API key is **never** read from the config file. It must be present in the
environment variable named by ``api_key_env``.
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


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_API_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_MAX_TOKENS = 512


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(
        self,
        *,
        model: str,
        api_key_env: str = DEFAULT_API_KEY_ENV,
        base_url: str = DEFAULT_OPENAI_BASE_URL,
        timeout_seconds: float = 30.0,
        max_retries: int = 1,
        request_json_object: bool = True,
    ):
        if not model:
            raise ProviderError("OpenAI provider requires a non-empty model name")
        self._model = model
        self._api_key_env = api_key_env or DEFAULT_API_KEY_ENV
        self._base_url = (base_url or DEFAULT_OPENAI_BASE_URL).rstrip("/")
        self._timeout = float(timeout_seconds)
        self._max_retries = int(max_retries)
        self._request_json_object = bool(request_json_object)

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
        url = f"{self._base_url}/chat/completions"
        body: dict = {
            "model": self._model,
            "messages": prompt.to_chat_messages(),
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": 0.4,
        }
        if self._request_json_object:
            body["response_format"] = {"type": "json_object"}

        try:
            response = http_post_json(
                url,
                headers={"Authorization": f"Bearer {key}"},
                payload=body,
                timeout=self._timeout,
                max_retries=self._max_retries,
            )
        except ProviderError:
            if self._request_json_object:
                # Some compatible servers reject response_format. Retry without it.
                body.pop("response_format", None)
                response = http_post_json(
                    url,
                    headers={"Authorization": f"Bearer {key}"},
                    payload=body,
                    timeout=self._timeout,
                    max_retries=self._max_retries,
                )
                self._request_json_object = False
            else:
                raise

        text = safe_get(
            response.body, "choices", 0, "message", "content", default=""
        ) or ""
        usage = response.body.get("usage", {}) or {}
        echo = EchoUsage(
            input_tokens=int(usage.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage.get("completion_tokens", 0) or 0),
            total_tokens=int(
                usage.get("total_tokens", 0)
                or (usage.get("prompt_tokens", 0) or 0)
                + (usage.get("completion_tokens", 0) or 0)
            ),
            cached_tokens=int(
                safe_get(usage, "prompt_tokens_details", "cached_tokens", default=0)
                or 0
            ),
            latency_ms=response.latency_ms,
        )
        return ModelTurnResult(
            provider=self.name,
            model=self._model,
            raw_text=str(text),
            usage=echo,
        )
