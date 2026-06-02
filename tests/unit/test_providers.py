"""Real-provider adapter tests with mocked HTTP layer.

Tests must never make a real network call. We monkeypatch ``http_post_json``
so wire format and error handling are validated deterministically.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ouro_agent.config import OuroConfig
from ouro_agent.content import load_content_bundle
from ouro_agent.engine.battle import BattleLoop
from ouro_agent.llm.prompt import compose_prompt
from ouro_agent.providers import (
    AnthropicProvider,
    FallbackOnErrorProvider,
    MockProvider,
    OpenAICompatibleProvider,
    OpenAIProvider,
    provider_preflight,
)
from ouro_agent.providers.base import ProviderError
from ouro_agent.providers.http import HttpResponse


@pytest.fixture()
def prompt_ctx(content_root: Path):
    bundle = load_content_bundle(content_root)
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    return compose_prompt(state, bundle)


def _fake_chat_response(text: str, prompt_tokens: int = 7, completion_tokens: int = 3) -> HttpResponse:
    return HttpResponse(
        status=200,
        body={
            "id": "chatcmpl-test",
            "choices": [{"message": {"role": "assistant", "content": text}}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        },
        headers={},
        latency_ms=42,
    )


def _fake_anthropic_response(text: str, in_tok: int = 9, out_tok: int = 4) -> HttpResponse:
    return HttpResponse(
        status=200,
        body={
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": text}],
            "usage": {"input_tokens": in_tok, "output_tokens": out_tok},
        },
        headers={},
        latency_ms=55,
    )


def test_openai_provider_sends_chat_messages_and_extracts(monkeypatch, prompt_ctx):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured: dict = {}

    def fake_post(url, *, headers, payload, timeout, max_retries):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        return _fake_chat_response('{"action":{"type":"defend"}}')

    monkeypatch.setattr("ouro_agent.providers.openai.http_post_json", fake_post)

    provider = OpenAIProvider(model="gpt-test")
    result = provider.request_turn(prompt_ctx)

    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["payload"]["model"] == "gpt-test"
    assert captured["payload"]["messages"][0]["role"] == "system"
    assert captured["payload"]["messages"][1]["role"] == "user"

    assert "action" in result.raw_text
    assert result.usage.input_tokens == 7
    assert result.usage.output_tokens == 3
    assert result.usage.total_tokens == 10
    assert result.usage.latency_ms == 42


def test_openai_provider_requires_env_var(monkeypatch, prompt_ctx):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIProvider(model="gpt-test")
    with pytest.raises(ProviderError):
        provider.request_turn(prompt_ctx)


def test_provider_preflight_reports_missing_env_without_secret():
    cfg = OuroConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key_env="OPENAI_API_KEY",
    )

    report = provider_preflight(cfg, env={})

    assert report.ready is False
    assert report.api_key_env == "OPENAI_API_KEY"
    assert report.env_present is False
    assert report.base_url == "https://api.openai.com/v1"
    assert report.issues == ("environment variable OPENAI_API_KEY is not set",)
    assert "sk-" not in " ".join(report.issues)


def test_provider_preflight_ready_for_configured_compatible_without_network():
    cfg = OuroConfig(
        provider="openai-compatible",
        model="qwen-live",
        api_key_env="OURO_API_KEY",
        base_url="https://llm.example.test/v1",
        timeout_seconds=45,
        max_retries=3,
    )

    report = provider_preflight(cfg, env={"OURO_API_KEY": "secret-value"})

    assert report.ready is True
    assert report.env_present is True
    assert report.base_url == "https://llm.example.test/v1"
    assert report.timeout_seconds == 45
    assert report.max_retries == 3
    assert report.issues == ()


def test_openai_compatible_requires_explicit_base_url():
    with pytest.raises(ProviderError):
        OpenAICompatibleProvider(model="m", base_url="")


def test_openai_compatible_uses_custom_base(monkeypatch, prompt_ctx):
    monkeypatch.setenv("OURO_API_KEY", "compat-key")
    captured: dict = {}

    def fake_post(url, *, headers, payload, timeout, max_retries):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        return _fake_chat_response('{"action":{"type":"basic_attack","targets":["enemy_hungry_cultist"]}}')

    monkeypatch.setattr("ouro_agent.providers.openai.http_post_json", fake_post)

    provider = OpenAICompatibleProvider(
        model="qwen3.6-plus",
        base_url="https://example.test/v1",
        api_key_env="OURO_API_KEY",
    )
    provider.request_turn(prompt_ctx)
    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer compat-key"
    assert "response_format" not in captured["payload"]  # disabled by default


def test_anthropic_provider_sends_dual_auth_and_messages(monkeypatch, prompt_ctx):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-key")
    captured: dict = {}

    def fake_post(url, *, headers, payload, timeout, max_retries):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        return _fake_anthropic_response('{"action":{"type":"defend"}}')

    monkeypatch.setattr("ouro_agent.providers.anthropic.http_post_json", fake_post)

    provider = AnthropicProvider(model="claude-test")
    result = provider.request_turn(prompt_ctx)

    assert captured["url"].endswith("/v1/messages")
    assert captured["headers"]["x-api-key"] == "ant-key"
    assert captured["headers"]["Authorization"] == "Bearer ant-key"
    assert captured["headers"]["anthropic-version"]
    assert "system" in captured["payload"]
    assert captured["payload"]["messages"][0]["role"] == "user"

    assert result.raw_text.startswith("{")
    assert result.usage.input_tokens == 9
    assert result.usage.output_tokens == 4
    assert result.usage.total_tokens == 13


def test_anthropic_compatible_against_dashscope_style(monkeypatch, prompt_ctx):
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "ant-bridge-token")
    captured: dict = {}

    def fake_post(url, *, headers, payload, timeout, max_retries):
        captured["url"] = url
        captured["headers"] = headers
        return _fake_anthropic_response('{"action":{"type":"defend"}}')

    monkeypatch.setattr("ouro_agent.providers.anthropic.http_post_json", fake_post)

    provider = AnthropicProvider(
        model="qwen3.6-plus",
        api_key_env="ANTHROPIC_AUTH_TOKEN",
        base_url="https://coding.dashscope.aliyuncs.com/apps/anthropic",
    )
    provider.request_turn(prompt_ctx)
    assert captured["url"] == (
        "https://coding.dashscope.aliyuncs.com/apps/anthropic/v1/messages"
    )
    assert captured["headers"]["Authorization"] == "Bearer ant-bridge-token"


def test_fallback_provider_recovers_on_error(monkeypatch, prompt_ctx):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_post(*args, **kwargs):
        raise ProviderError("simulated 503")

    monkeypatch.setattr("ouro_agent.providers.openai.http_post_json", fake_post)

    primary = OpenAIProvider(model="gpt-test")
    fb = FallbackOnErrorProvider(primary, MockProvider(seed=1))

    result = fb.request_turn(prompt_ctx)
    assert fb.error and "simulated 503" in fb.error
    parsed = json.loads(result.raw_text)
    assert "action" in parsed

    # Subsequent calls go straight to mock without re-trying primary.
    result2 = fb.request_turn(prompt_ctx)
    assert result2.provider == "mock"


def test_prompt_serializers(prompt_ctx):
    chat = prompt_ctx.to_chat_messages()
    assert {m["role"] for m in chat} == {"system", "user"}
    assert "Output schema" in chat[0]["content"]
    assert "Hero prompt" in chat[1]["content"]

    ant = prompt_ctx.to_anthropic_payload()
    assert "system" in ant
    assert ant["messages"][0]["role"] == "user"
    assert "Battle snapshot" in ant["messages"][0]["content"]


def test_mock_prompt_style_changes_tactical_choice(content_root: Path):
    bundle = load_content_bundle(content_root)
    loop = BattleLoop(bundle, MockProvider(seed=0, language="en"), seed=1, language="en")
    state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    cultist = state.enemies[0]
    acolyte = state.enemies[1]
    cultist.hp = 18
    cultist.atb = 10
    acolyte.hp = 70
    acolyte.atb = 90
    acolyte.chant_progress = 1

    aggressive_prompt = compose_prompt(state, bundle, prompt_style="aggressive")
    control_prompt = compose_prompt(state, bundle, prompt_style="control")

    aggressive = json.loads(MockProvider(seed=1, language="en").request_turn(aggressive_prompt).raw_text)
    control = json.loads(MockProvider(seed=1, language="en").request_turn(control_prompt).raw_text)

    assert aggressive_prompt.snapshot["prompt_style"] == "aggressive"
    assert control_prompt.static_context["prompt_style"] == "control"
    assert aggressive["action"]["skill_id"] == "skill_shadow_sting"
    assert aggressive["action"]["targets"] == ["enemy_hungry_cultist"]
    assert control["action"]["skill_id"] == "skill_hex_seal"
    assert control["action"]["targets"] == ["enemy_black_candle_acolyte"]


def test_mock_guarded_style_raises_defensive_threshold(content_root: Path):
    """REQ-PLAY-005: Guarded should defend earlier under incoming pressure."""
    bundle = load_content_bundle(content_root)
    loop = BattleLoop(bundle, MockProvider(seed=0, language="en"), seed=1, language="en")
    state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    state.hero.hp = 60
    state.enemies[1].atb = 95

    guarded_prompt = compose_prompt(state, bundle, prompt_style="guarded")
    aggressive_prompt = compose_prompt(state, bundle, prompt_style="aggressive")

    guarded = json.loads(MockProvider(seed=1, language="en").request_turn(guarded_prompt).raw_text)
    aggressive = json.loads(MockProvider(seed=1, language="en").request_turn(aggressive_prompt).raw_text)

    assert guarded["action"]["skill_id"] == "skill_corrupted_focus"
    assert guarded["action"]["targets"] == ["hero_shadow_apprentice"]
    assert aggressive["action"]["skill_id"] == "skill_shadow_sting"


def test_mock_attrition_style_changes_target_and_dot_priority(content_root: Path):
    """REQ-PLAY-005: Attrition should prefer durable targets for damage-over-time."""
    bundle = load_content_bundle(content_root)
    loop = BattleLoop(bundle, MockProvider(seed=0, language="en"), seed=1, language="en")
    state = loop.setup(
        "hero_mire_oracle",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    state.enemies[0].hp = 20
    state.enemies[1].hp = 100
    state.enemies[1].atb = 30

    attrition_prompt = compose_prompt(state, bundle, prompt_style="attrition")
    aggressive_prompt = compose_prompt(state, bundle, prompt_style="aggressive")

    attrition = json.loads(MockProvider(seed=1, language="en").request_turn(attrition_prompt).raw_text)
    aggressive = json.loads(MockProvider(seed=1, language="en").request_turn(aggressive_prompt).raw_text)

    assert attrition["action"]["skill_id"] == "skill_mire_needle"
    assert attrition["action"]["targets"] == ["enemy_black_candle_acolyte"]
    assert aggressive["action"]["targets"] == ["enemy_hungry_cultist"]
