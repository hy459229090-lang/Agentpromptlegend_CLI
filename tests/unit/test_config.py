"""REQ-PROV-001/002/003: provider config rules and key handling."""
from __future__ import annotations

from argparse import Namespace

import pytest

from ouro_agent.cli.main import _effective_game_config, main
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


def test_game_config_uses_saved_provider_unless_mock(isolated_home):
    """REQ-PROV-004: game commands should use saved provider config."""
    saved = OuroConfig(
        provider="openai-compatible",
        model="qwen-live",
        api_key_env="OURO_API_KEY",
        base_url="https://llm.example.test/v1",
        api_version="",
        timeout_seconds=77,
        max_retries=4,
        trace_level="summary",
        unicode_mode=False,
        language="en",
    )
    args = Namespace(mock=False, unicode=True, lang=None)

    effective = _effective_game_config(args, saved)

    assert effective.provider == "openai-compatible"
    assert effective.model == "qwen-live"
    assert effective.api_key_env == "OURO_API_KEY"
    assert effective.base_url == "https://llm.example.test/v1"
    assert effective.timeout_seconds == 77
    assert effective.max_retries == 4
    assert effective.unicode_mode is True
    assert effective.language == "en"

    forced = _effective_game_config(
        Namespace(mock=True, unicode=False, lang="zh"),
        saved,
    )

    assert forced.provider == "mock"
    assert forced.model == "mock-smart"
    assert forced.api_key_env == ""
    assert forced.timeout_seconds == 77
    assert forced.language == "zh"


def test_load_rejects_legacy_plaintext_key(isolated_home, tmp_path):
    bad = tmp_path / "config.toml"
    bad.write_text(
        "[ouro_agent]\nprovider = \"openai\"\napi_key = \"sk-leak\"\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError):
        load_config(bad)


def test_config_setup_prompts_step_by_step(isolated_home, monkeypatch, capsys):
    answers = iter(["2", "gpt-test", "OPENAI_API_KEY", "", "en"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    rc = main(["--lang", "en", "config", "setup"])

    out = capsys.readouterr().out
    cfg = load_config()
    assert rc == 0
    assert cfg.provider == "openai"
    assert cfg.model == "gpt-test"
    assert cfg.api_key_env == "OPENAI_API_KEY"
    assert cfg.base_url == ""
    assert cfg.language == "en"
    assert "Configuration saved." in out
    assert "OPENAI_API_KEY is not set yet" in out
    assert "sk-" not in config_path().read_text(encoding="utf-8")


def test_config_setup_rejects_plaintext_api_key_env(isolated_home, monkeypatch, capsys):
    answers = iter(["openai", "gpt-test", "sk-test"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    rc = main(["--lang", "en", "config", "wizard"])

    err = capsys.readouterr().err
    assert rc == 2
    assert "api_key_env stores a variable NAME" in err


def test_config_preflight_redacts_env_value_and_reports_ready(
    isolated_home,
    monkeypatch,
    capsys,
):
    save_config(
        OuroConfig(
            provider="openai-compatible",
            model="qwen-live",
            api_key_env="OURO_API_KEY",
            base_url="https://llm.example.test/v1",
            language="en",
        )
    )
    fake_secret = "sk-" + "live-secret-value"
    monkeypatch.setenv("OURO_API_KEY", fake_secret)

    rc = main(["--lang", "en", "config", "preflight"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "PROVIDER PREFLIGHT" in out
    assert "provider     : openai-compatible" in out
    assert "model        : qwen-live" in out
    assert "api_key_env  : OURO_API_KEY" in out
    assert "env value    : set (hidden)" in out
    assert "network      : not called" in out
    assert "status       : READY" in out
    assert fake_secret not in out


def test_config_preflight_missing_real_env_returns_not_ready(
    isolated_home,
    monkeypatch,
    capsys,
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    save_config(
        OuroConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="OPENAI_API_KEY",
            language="en",
        )
    )

    rc = main(["--lang", "en", "config", "preflight"])

    out = capsys.readouterr().out
    assert rc == 3
    assert "status       : NOT READY" in out
    assert "environment variable OPENAI_API_KEY is not set" in out
    assert "env value    : MISSING" in out


def test_cli_default_shows_main_menu(isolated_home, capsys):
    rc = main(["--lang", "en"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "OURO AGENT :: PROMPT LEGEND" in out
    assert "MAIN MENU CONSOLE" in out
    assert "[NEXT] Recommended: ouro demo --seed 1" in out
    assert "Mock Path : mock-ready" in out
    assert "Provider : mock" in out
    assert "PLAYER JOURNEY BOARD" in out
    assert "[START] Guided demo -> ouro demo --seed 1" in out
    assert "[BUILD] Pick hero/weapon -> ouro list-heroes / ouro weapons" in out
    assert "[RUN] Full run -> ouro run --mock" in out
    assert "[LEARN] Review Codex/report -> ouro status / ouro codex / ouro run-report" in out
    assert "ENTRY COMMANDS" in out
    assert "[PLAY] New Run        ouro run --mock" in out
    assert "[BUILD] Hero/Weapon" in out
    assert "[LEARN] Run Report" in out
    assert "New Run" in out
    assert "ouro run --mock" in out
    assert "Guided Demo" in out
    assert "ouro demo --seed 1" in out
    assert "Quick Battle" in out
    assert "Hero/Weapon" in out
    assert "Prompt Style" in out
    assert "Status" in out
    assert "ouro status" in out
    assert "Codex" in out
    assert "Runs" in out
    assert "Run Report" in out
    assert "ouro run-report" in out
    assert "History" in out
    assert "Doctor" in out


def test_cli_weapons_shows_gallery(content_root, isolated_home, capsys):
    rc = main(["--lang", "en", "weapons", "--content-dir", str(content_root)])

    out = capsys.readouterr().out
    assert rc == 0
    assert "WEAPON GALLERY :: BUILD ARSENAL" in out
    assert "[1] [W:STF] c==* Astia" in out
    assert "[OPEN] ouro hero-card astia" in out
    assert "NEXT WEAPON ROUTE" in out
    assert "hero_shadow_apprentice" not in out


def test_cli_prompt_templates_show_pilot_board(isolated_home, capsys):
    rc = main(["--lang", "en", "prompt-templates"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "PROMPT STRATEGY TEMPLATES" in out
    assert "PROMPT PILOT BOARD" in out
    assert "[aggressive] BURST" in out
    assert "[guarded]    STABLE" in out
    assert "[control]    DENY" in out
    assert "[attrition]  GRIND" in out
    assert "PROMPT SCENARIO BOARD" in out
    assert "[CHANT] control -> interrupt high ATB" in out
    assert "[LOW HP] guarded -> defend or shield" in out
    assert "[EXECUTE] aggressive -> finish low HP" in out
    assert "[BOSS] control -> manage charge" in out
    assert "PICK: boss/chant use control; low HP use guarded" in out
    assert "RUN: ouro run --mock --prompt-style <name>" in out
    assert "Use: ouro play --mock --prompt-style control" in out


def test_cli_accepts_global_language_after_subcommand(isolated_home, capsys):
    """REQ-QOL-001: new players can write `ouro menu --lang en`."""
    rc = main(["menu", "--lang", "en"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "OURO AGENT :: PROMPT LEGEND" in out
    assert "Language : en" in out
    assert "New Run" in out
    assert "ouro run --mock" in out


def test_cli_demo_runs_guided_mock_smoke(isolated_home, content_root, capsys):
    """REQ-EXP-008: one command shows the first playable loop without network."""
    rc = main(
        [
            "--lang",
            "en",
            "demo",
            "--seed",
            "1",
            "--content-dir",
            str(content_root),
        ]
    )

    out = capsys.readouterr().out

    assert rc == 0
    assert "OURO DEMO :: FIRST ECHO" in out
    assert "STEP 1: Status and next commands" in out
    assert "Guided Demo" in out
    assert "Trace: -" in out
    assert "STEP 2: Hero card and build plan" in out
    assert "HERO CARD" in out
    assert "[W:" in out
    assert "STEP 3: Deterministic mock battle" in out
    assert "Provider: mock" in out
    assert "BATTLE COMPLETE" in out
    assert "Result : victory" in out
    assert "STEP 4: Codex readback" in out
    assert "CODEX :: MONSTER ARCHIVE" in out
    assert "Observed: 2/9" in out
    assert "[OB] [c] Hungry Cultist [I: Trace]" in out
    assert "STEP 5: Continue from here" in out
    assert "Next commands" in out
    assert "Full run" in out
    assert "ouro run --mock" in out
    assert "Status" in out
    assert "ouro status --lang en" in out
    assert "Run Report" in out
    assert "ouro run-report --lang en" in out
    assert "Review Codex" in out
    assert "ouro codex --lang en" in out
    assert "Review runs" in out
    assert "ouro runs --lang en --limit 5" in out
    assert "Doctor" in out
    assert "ouro doctor --lang en" in out
    assert "Trace :" not in out


def test_cli_hero_entry_accepts_player_refs_and_reports_errors(
    isolated_home,
    content_root,
    capsys,
):
    rc = main(["--lang", "en", "hero-card", "1", "--content-dir", str(content_root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "HERO CARD :: Astia [CNDL]" in out
    assert "[RUN] ouro run --mock --hero astia" in out
    assert "hero_shadow_apprentice" not in out

    rc = main(["--lang", "zh", "hero-card", "阿斯缇娅", "--content-dir", str(content_root)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "英雄详情 :: 阿斯缇娅 [CNDL]" in out
    assert "[RUN] ouro run --mock --hero astia" in out

    rc = main(["--lang", "en", "hero-card", "foo", "--content-dir", str(content_root)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "HERO PICK ERROR" in captured.err
    assert "Unknown hero: foo" in captured.err
    assert "[1] astia / Astia [CNDL]" in captured.err
    assert "Example: ouro hero-card 1 | ouro run --mock --hero astia" in captured.err
    assert "Traceback" not in captured.err + captured.out
    assert "SchemaError" not in captured.err + captured.out

    rc = main(
        [
            "--lang",
            "zh",
            "run",
            "--mock",
            "--auto",
            "--hero",
            "foo",
            "--no-animation",
            "--no-trace",
            "--content-dir",
            str(content_root),
        ]
    )
    captured = capsys.readouterr()
    assert rc == 2
    assert "英雄选择错误" in captured.err
    assert "未识别英雄: foo" in captured.err
    assert "示例: ouro hero-card 1 | ouro run --mock --hero astia" in captured.err
    assert "Traceback" not in captured.err + captured.out


@pytest.mark.parametrize(
    "command",
    [
        "demo",
        "play",
        "list-heroes",
        "weapons",
        "hero-card",
        "status",
        "codex",
        "runs",
        "history",
        "validate-content",
        "doctor",
        "run",
        "batch",
    ],
)
def test_content_dir_help_describes_installed_fallback(command, capsys):
    """REQ-CLIUX-003: help text matches install-time bundled content fallback."""
    with pytest.raises(SystemExit) as exc:
        main([command, "--help"])

    out = capsys.readouterr().out

    assert exc.value.code == 0
    assert "--content-dir" in out
    assert "bundled" in out
    assert "installed content" in out
    assert "defaults to ./content" not in out


def test_interactive_run_abort_returns_code_without_system_exit(
    isolated_home,
    content_root,
    monkeypatch,
    capsys,
):
    """REQ-CLIUX-002: interactive abort returns a code instead of killing callers."""
    monkeypatch.setattr("builtins.input", lambda _prompt: (_ for _ in ()).throw(EOFError()))

    rc = main(
        [
            "run",
            "--mock",
            "--seed",
            "7",
            "--no-animation",
            "--no-trace",
            "--content-dir",
            str(content_root),
            "--lang",
            "en",
        ]
    )

    err = capsys.readouterr().err

    assert rc == 130
    assert "Aborted." in err


def test_doctor_respects_language_override_and_validates_content(
    isolated_home,
    content_root,
    capsys,
):
    """REQ-DIAG-001: doctor should prove install/config/content readiness."""
    rc = main(["doctor", "--lang", "en", "--content-dir", str(content_root)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "language     : en" in out
    assert "provider chk : READY" in out
    assert "content      : OK heroes=6 skills=18 enemies=9" in out
    assert "items=15 affixes=12 resonances=5" in out
    assert "mock play    : ready (no API key required)" in out


def test_doctor_reports_real_provider_preflight_without_leaking_env(
    isolated_home,
    content_root,
    monkeypatch,
    capsys,
):
    secret = "sk-" + "doctor-hidden-value"
    monkeypatch.setenv("OURO_API_KEY", secret)
    save_config(
        OuroConfig(
            provider="openai-compatible",
            model="qwen-live",
            api_key_env="OURO_API_KEY",
            base_url="https://llm.example.test/v1",
            language="en",
        )
    )

    rc = main(["--lang", "en", "doctor", "--content-dir", str(content_root)])

    out = capsys.readouterr().out
    assert rc == 0
    assert "provider     : openai-compatible" in out
    assert "env var      : OURO_API_KEY = set (hidden)" in out
    assert "provider chk : READY" in out
    assert "provider err :" not in out
    assert secret not in out


def test_doctor_returns_not_ready_when_real_provider_env_is_missing(
    isolated_home,
    content_root,
    monkeypatch,
    capsys,
):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    save_config(
        OuroConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="OPENAI_API_KEY",
            language="en",
        )
    )

    rc = main(["--lang", "en", "doctor", "--content-dir", str(content_root)])

    out = capsys.readouterr().out
    assert rc == 3
    assert "content      : OK heroes=6 skills=18 enemies=9" in out
    assert "provider chk : NOT READY" in out
    assert "provider err : environment variable OPENAI_API_KEY is not set" in out


def test_doctor_fails_when_content_is_invalid(isolated_home, tmp_path, capsys):
    """REQ-DIAG-001: doctor exits nonzero when content cannot be loaded."""
    missing_content = tmp_path / "missing-content"

    rc = main(["--lang", "en", "doctor", "--content-dir", str(missing_content)])
    out = capsys.readouterr().out

    assert rc == 3
    assert "content      : FAIL heroes=0 skills=0 enemies=0" in out
    assert "content err  :" in out
