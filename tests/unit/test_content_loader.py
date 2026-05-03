"""REQ-DATA-001/002 content loading and reference checks."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.content import load_content_bundle, ContentError


def test_load_default_content_bilingual(content_root: Path):
    bundle = load_content_bundle(content_root)
    assert "hero_shadow_apprentice" in bundle.heroes
    hero = bundle.heroes["hero_shadow_apprentice"]
    assert hero.display_name.en == "Astia"
    assert hero.display_name.zh == "阿斯缇娅"
    assert hero.class_name.en == "Shadow Apprentice"
    assert hero.class_name.zh == "暗影学徒"

    assert {"skill_shadow_sting", "skill_hex_seal", "skill_corrupted_focus"}.issubset(
        bundle.skills
    )
    assert bundle.skills["skill_shadow_sting"].display_name.zh == "暗影刺"

    assert {"enemy_hungry_cultist", "enemy_black_candle_acolyte"}.issubset(
        bundle.enemies
    )
    assert bundle.enemies["enemy_hungry_cultist"].display_name.zh == "饥饿邪教徒"


def test_localized_text_falls_back_when_one_lang_missing(tmp_path: Path):
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "s.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nskills:\n"
        "  - id: skill_only_en\n"
        "    display_name: { en: Only En }\n"
        "    mp_cost: 0\n    cooldown: 0\n    target_rule: self\n    tags: []\n"
        "    effect:\n      kind: status\n      base: 0\n      power_scale: 0\n"
        "      damage_type: none\n"
        "    visible_description: ''\n",
        encoding="utf-8",
    )
    (tmp_path / "enemies").mkdir()
    (tmp_path / "enemies" / "e.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nenemies:\n"
        "  - id: enemy_x\n    display_name: X\n    short_glyph: x\n"
        "    base_stats:\n      hp: 1\n      mp: 0\n      speed: 1\n"
        "      attack: 1\n      defense: 0\n      power: 0\n"
        "    behavior:\n      kind: rule_basic\n      attack_chance: 1.0\n"
        "    codex_stage_unknown: u\n    codex_stage_observed: o\n",
        encoding="utf-8",
    )
    (tmp_path / "heroes").mkdir()
    (tmp_path / "heroes" / "h.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nheroes:\n"
        "  - id: hero_x\n    display_name: X\n    class_name: c\n"
        "    short_tag: '[X]'\n    tags: []\n    avatar_ascii: ['x']\n"
        "    base_stats:\n      hp: 1\n      mp: 0\n      speed: 1\n"
        "      attack: 1\n      defense: 0\n      power: 0\n"
        "    skills: [skill_only_en]\n    default_prompt: ''\n"
        "    description: ''\n",
        encoding="utf-8",
    )
    bundle = load_content_bundle(tmp_path)
    skill = bundle.skills["skill_only_en"]
    assert skill.display_name.en == "Only En"
    assert skill.display_name.zh == "Only En"  # fell back to en


def test_dangling_skill_reference_fails(tmp_path: Path):
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "s.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nskills: []\n",
        encoding="utf-8",
    )
    (tmp_path / "enemies").mkdir()
    (tmp_path / "enemies" / "e.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nenemies:\n"
        "  - id: enemy_x\n    display_name: X\n    short_glyph: x\n"
        "    base_stats:\n      hp: 1\n      mp: 0\n      speed: 1\n"
        "      attack: 1\n      defense: 0\n      power: 0\n"
        "    behavior:\n      kind: rule_basic\n      attack_chance: 1.0\n",
        encoding="utf-8",
    )
    (tmp_path / "heroes").mkdir()
    (tmp_path / "heroes" / "h.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nheroes:\n"
        "  - id: hero_x\n    display_name: X\n    class_name: c\n"
        "    short_tag: '[X]'\n    tags: []\n    avatar_ascii: ['x']\n"
        "    base_stats:\n      hp: 1\n      mp: 0\n      speed: 1\n"
        "      attack: 1\n      defense: 0\n      power: 0\n"
        "    skills: [skill_does_not_exist]\n    default_prompt: ''\n"
        "    description: ''\n",
        encoding="utf-8",
    )
    with pytest.raises(ContentError):
        load_content_bundle(tmp_path)


def test_invalid_id_prefix_rejected(tmp_path: Path):
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "s.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nskills:\n"
        "  - id: bogus_id\n    display_name: X\n    mp_cost: 0\n    cooldown: 0\n"
        "    target_rule: self\n    tags: []\n"
        "    effect:\n      kind: status\n      base: 0\n      power_scale: 0\n"
        "      damage_type: none\n"
        "    visible_description: ''\n",
        encoding="utf-8",
    )
    with pytest.raises(ContentError):
        load_content_bundle(tmp_path)
