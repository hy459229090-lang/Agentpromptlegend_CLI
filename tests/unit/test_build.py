"""Slice B: build resolver + bilingual content extension."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.content import load_content_bundle
from ouro_agent.engine import resolve_build
from ouro_agent.engine.battle import BattleLoop
from ouro_agent.providers.mock import MockProvider


@pytest.fixture()
def bundle(content_root: Path):
    return load_content_bundle(content_root)


def test_six_heroes_loaded(bundle):
    assert {
        "hero_shadow_apprentice",
        "hero_ash_guardian",
        "hero_broken_string_hunter",
        "hero_mire_oracle",
        "hero_gravewright",
        "hero_echo_exile",
    } == set(bundle.heroes)


def test_eighteen_skills_loaded(bundle):
    assert len(bundle.skills) >= 18
    for hero in bundle.heroes.values():
        for sid in hero.skills:
            assert sid in bundle.skills


def test_items_with_tier_breakdown(bundle):
    assert len(bundle.items) >= 6
    tiers = [item.tier for item in bundle.items.values()]
    assert tiers.count("common") >= 3
    assert tiers.count("heroic") >= 2
    assert tiers.count("legendary") >= 1


def test_legendary_item_has_allowed_effects(bundle):
    legendaries = [i for i in bundle.items.values() if i.tier == "legendary"]
    assert legendaries
    for item in legendaries:
        assert item.allowed_effects, "legendary must declare allowed_effects"


def test_affixes_loaded(bundle):
    assert len(bundle.affixes) >= 6


def test_two_resonances(bundle):
    assert len(bundle.resonances) >= 2


def test_resolve_build_for_norn_triggers_iron_legion(bundle):
    norn = bundle.get_hero("hero_ash_guardian")
    build = resolve_build(norn, bundle)
    res_ids = {r.id for r in build.resonances}
    assert "resonance_iron_legion" in res_ids
    assert build.hp > norn.base_stats.hp  # items + affix + resonance buffed hp
    assert build.defense > norn.base_stats.defense
    assert any(s.id == "status_shield" for s in build.battle_start_statuses)


def test_resolve_build_for_astia_triggers_corruption_school(bundle):
    astia = bundle.get_hero("hero_shadow_apprentice")
    build = resolve_build(astia, bundle)
    res_ids = {r.id for r in build.resonances}
    assert "resonance_corruption_school" in res_ids
    assert build.power > astia.base_stats.power


def test_battle_loop_uses_resolved_build(bundle):
    loop = BattleLoop(
        bundle,
        MockProvider(seed=1, language="en"),
        seed=1,
        max_ticks=600,
        language="en",
    )
    state = loop.setup(
        "hero_ash_guardian",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    norn = bundle.get_hero("hero_ash_guardian")
    assert state.hero.max_hp > norn.base_stats.hp
    # Iron Legion gives a starting shield
    assert state.hero.find_status("status_shield") is not None
    result = loop.run(state)
    assert result in {"victory", "defeat"}


def test_dangling_item_reference_in_hero_fails(tmp_path: Path):
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "s.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nskills:\n"
        "  - id: skill_x\n    display_name: X\n    mp_cost: 0\n"
        "    cooldown: 0\n    target_rule: self\n    tags: []\n"
        "    effect:\n      kind: status\n      base: 0\n"
        "      power_scale: 0\n      damage_type: none\n"
        "    visible_description: ''\n",
        encoding="utf-8",
    )
    (tmp_path / "enemies").mkdir()
    (tmp_path / "enemies" / "e.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nenemies:\n"
        "  - id: enemy_x\n    display_name: X\n    short_glyph: x\n"
        "    base_stats: { hp: 1, mp: 0, speed: 1, attack: 1, defense: 0, power: 0 }\n"
        "    behavior: { kind: rule_basic, attack_chance: 1.0 }\n",
        encoding="utf-8",
    )
    (tmp_path / "items").mkdir()
    (tmp_path / "items" / "i.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nitems: []\n",
        encoding="utf-8",
    )
    (tmp_path / "heroes").mkdir()
    (tmp_path / "heroes" / "h.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nheroes:\n"
        "  - id: hero_x\n    display_name: X\n    class_name: c\n"
        "    short_tag: '[X]'\n    tags: []\n    avatar_ascii: ['x']\n"
        "    base_stats: { hp: 1, mp: 0, speed: 1, attack: 1, defense: 0, power: 0 }\n"
        "    skills: [skill_x]\n    default_prompt: ''\n    description: ''\n"
        "    default_build: { items: [item_does_not_exist], affixes: [] }\n",
        encoding="utf-8",
    )
    from ouro_agent.content import ContentError

    with pytest.raises(ContentError):
        load_content_bundle(tmp_path)


def test_legendary_without_allowed_effects_rejected(tmp_path: Path):
    (tmp_path / "items").mkdir()
    (tmp_path / "items" / "bad.yaml").write_text(
        "schema_version: '0.1'\ncontent_version: t\nitems:\n"
        "  - id: item_bad\n    display_name: bad\n    tier: legendary\n"
        "    tags: []\n    stat_mods: {}\n    description: ''\n",
        encoding="utf-8",
    )
    from ouro_agent.content import ContentError

    with pytest.raises(ContentError):
        load_content_bundle(tmp_path)


def test_validation_report_includes_b_counts(bundle, content_root):
    from ouro_agent.validation import validate_content_dir

    report = validate_content_dir(content_root)
    assert report.ok
    assert report.heroes == 6
    assert report.skills == 18
    assert report.items >= 6
    assert report.affixes >= 6
    assert report.resonances >= 2


def test_render_hero_card_zh(bundle):
    from ouro_agent.tui import render_hero_card

    norn = bundle.get_hero("hero_ash_guardian")
    build = resolve_build(norn, bundle)
    text = render_hero_card(norn, bundle, build, language="zh")
    assert "诺恩" in text
    assert "灰烬守卫" in text
    assert "守望塔盾" in text
    assert "铁色军团" in text


def test_render_hero_list_en_is_ascii_safe(bundle):
    from ouro_agent.tui import render_hero_list

    text = render_hero_list(bundle, language="en")
    assert text.isascii()
    assert "Astia" in text
    assert "Norn" in text
    assert "Vela" in text
    assert "Build:" in text
    assert "Weapon:" in text
    assert "Risk:" in text


def test_render_hero_card_shows_build_strategy_and_prompt_template(bundle):
    from ouro_agent.tui import render_hero_card

    astia = bundle.get_hero("hero_shadow_apprentice")
    build = resolve_build(astia, bundle)
    text = render_hero_card(
        astia,
        bundle,
        build,
        language="en",
        prompt_style="control",
    )
    assert text.isascii()
    assert "Build: Black Candle Interrupt" in text
    assert "Weapon: [W:STF]" in text
    assert "AI Bias:" in text
    assert "Prompt Template: control" in text
    assert "interrupt high-ATB" in text


def test_render_all_six_hero_cards_explain_play_and_risk(bundle):
    from ouro_agent.tui import render_hero_card

    for hero_id in (
        "hero_shadow_apprentice",
        "hero_ash_guardian",
        "hero_broken_string_hunter",
        "hero_mire_oracle",
        "hero_gravewright",
        "hero_echo_exile",
    ):
        hero = bundle.get_hero(hero_id)
        build = resolve_build(hero, bundle)
        text = render_hero_card(hero, bundle, build, language="en")
        assert "Build:" in text
        assert "Weapon:" in text
        assert "Risk:" in text
        assert "AI Bias:" in text
        assert "MP " in text
        assert "cd " in text
