"""Bilingual UI / log / mock narration coverage."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.config import load_config, set_field
from ouro_agent.config.model import ConfigError
from ouro_agent.content import load_content_bundle
from ouro_agent.engine.battle import BattleLoop
from ouro_agent.i18n import label, log_text, narration_text, pad_right, visual_width
from ouro_agent.providers.mock import MockProvider
from ouro_agent.tui import render_battle_screen, render_config_screen


def test_label_falls_back_to_en_when_zh_missing():
    assert label("seed", "en") == "Seed"
    assert label("seed", "zh") == "种子"
    assert label("nope_key", "zh") == "nope_key"


def test_log_text_zh_and_en():
    assert log_text("hero.basic_attack", "en", hero="A", target="B", dmg=3) == (
        "A strikes B for 3."
    )
    assert log_text("hero.basic_attack", "zh", hero="阿斯缇娅", target="邪教徒", dmg=3) == (
        "阿斯缇娅 一记普攻命中 邪教徒，造成 3 点伤害。"
    )


def test_narration_text_zh_and_en():
    en = narration_text("cast_skill", "en", hero="Astia", skill="Shadow Sting")
    zh = narration_text("cast_skill", "zh", hero="阿斯缇娅", skill="暗影刺")
    assert "Astia" in en and "Shadow Sting" in en
    assert "阿斯缇娅" in zh and "暗影刺" in zh


def test_visual_width_handles_cjk():
    assert visual_width("Astia") == 5
    assert visual_width("阿斯缇娅") == 8
    assert visual_width("Astia 阿") == 8


def test_pad_right_aligns_with_cjk():
    padded = pad_right("阿斯缇娅", 12)
    assert visual_width(padded) == 12


@pytest.fixture()
def bundle(content_root: Path):
    return load_content_bundle(content_root)


def test_battle_screen_zh_contains_chinese_labels(bundle):
    loop = BattleLoop(
        bundle,
        MockProvider(seed=1, language="zh"),
        seed=1,
        max_ticks=600,
        language="zh",
    )
    state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    loop.run(state)
    last_record = loop.records[-1] if loop.records else None
    screen = render_battle_screen(
        state,
        last_record,
        provider_label="mock",
        seed=1,
    )
    assert "英雄" in screen
    assert "敌人" in screen
    assert "模型行动" in screen
    assert "战斗日志" in screen
    assert "阿斯缇娅" in screen


def test_battle_screen_en_remains_ascii_safe(bundle):
    loop = BattleLoop(
        bundle,
        MockProvider(seed=1, language="en"),
        seed=1,
        max_ticks=600,
        language="en",
    )
    state = loop.setup(
        "hero_shadow_apprentice", ["enemy_hungry_cultist"]
    )
    loop.run(state)
    last_record = loop.records[-1] if loop.records else None
    screen = render_battle_screen(
        state, last_record, provider_label="mock", seed=1
    )
    assert screen.isascii()
    assert "HERO" in screen
    assert "Astia" in screen
    assert "Echo Cost" in screen


def test_config_language_defaults_to_zh(isolated_home):
    cfg = load_config()
    assert cfg.language == "zh"


def test_set_language_validates(isolated_home):
    set_field("language", "en")
    cfg = load_config()
    assert cfg.language == "en"
    with pytest.raises(ConfigError):
        set_field("language", "fr")


def test_config_screen_uses_zh_labels(isolated_home):
    cfg = load_config()
    from ouro_agent.config import config_path, redacted_view

    text = render_config_screen(
        redacted_view(cfg, language="zh"),
        config_path=str(config_path()),
        language="zh",
    )
    assert "模型供应商配置" in text
    assert "当前配置" in text
    assert "供应商" in text
    assert "(不保存，运行时从环境变量读取)" in text


def test_config_screen_en_is_ascii_safe(isolated_home):
    cfg = load_config()
    from ouro_agent.config import config_path, redacted_view

    text = render_config_screen(
        redacted_view(cfg, language="en"),
        config_path=str(config_path()),
        language="en",
    )
    assert text.isascii()
    assert "MODEL PROVIDER" in text


def test_zh_battle_log_contains_chinese(bundle):
    loop = BattleLoop(
        bundle,
        MockProvider(seed=1, language="zh"),
        seed=1,
        max_ticks=600,
        language="zh",
    )
    state = loop.setup(
        "hero_shadow_apprentice", ["enemy_hungry_cultist"]
    )
    loop.run(state)
    full_log = "\n".join(state.log)
    assert any(zh_word in full_log for zh_word in ("伤害", "护盾", "阿斯缇娅"))
