"""REQ-PROV-001/002/003: provider config rules and key handling."""
from __future__ import annotations

import pytest

from ouro_agent.config import (
    OuroConfig,
    SUPPORTED_PROVIDERS,
    config_path,
    load_config,
    redacted_view,
    save_config,
    set_field,
)
from ouro_agent.config.model import ConfigError


def test_default_provider_is_mock(isolated_home):
    cfg = load_config()
    assert cfg.provider == "mock"
    assert cfg.api_key_env == ""
    assert cfg.language == "zh"


@pytest.mark.parametrize("provider", SUPPORTED_PROVIDERS)
def test_set_provider_accepts_supported(isolated_home, provider):
    cfg = set_field("provider", provider)
    assert cfg.provider == provider


def test_set_provider_rejects_unknown(isolated_home):
    with pytest.raises(ConfigError):
        set_field("provider", "made_up_vendor")


def test_set_field_rejects_forbidden_secret_field(isolated_home):
    with pytest.raises(ConfigError):
        set_field("api_key", "sk-test")


def test_set_api_key_env_rejects_plaintext_key(isolated_home):
    with pytest.raises(ConfigError):
        set_field("api_key_env", "sk-test")


def test_save_does_not_persist_secrets(isolated_home):
    set_field("provider", "openai")
    set_field("model", "gpt-test")
    set_field("api_key_env", "OPENAI_API_KEY")
    set_field("base_url", "https://api.openai.example/v1")

    text = config_path().read_text(encoding="utf-8")
    assert "sk-" not in text
    assert "OPENAI_API_KEY" in text
    assert "MUST NOT contain plaintext API keys" in text


def test_redacted_view_never_includes_secret(isolated_home):
    cfg = OuroConfig(provider="openai", model="gpt-test", api_key_env="OPENAI_API_KEY")
    view_en = redacted_view(cfg, language="en")
    assert view_en["api_key_env"] == "OPENAI_API_KEY"
    assert "not stored" in view_en["api_key_value"]
    assert "sk-" not in " ".join(view_en.values())

    view_zh = redacted_view(cfg, language="zh")
    assert "不保存" in view_zh["api_key_value"]
    assert "sk-" not in " ".join(view_zh.values())


def test_load_rejects_legacy_plaintext_key(isolated_home, tmp_path):
    bad = tmp_path / "config.toml"
    bad.write_text(
        "[ouro_agent]\nprovider = \"openai\"\napi_key = \"sk-leak\"\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(bad)
