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


def test_six_heroes_have_identity_and_build_tendency(bundle):
    assert {"hero_mire_oracle", "hero_gravewright", "hero_echo_exile"}.issubset(
        bundle.heroes
    )
    for hero in bundle.heroes.values():
        assert hero.id.startswith("hero_")
        assert hero.short_tag.startswith("[") and hero.short_tag.endswith("]")
        assert hero.class_name.en
        assert hero.class_name.zh
        assert hero.tags
        assert len(hero.skills) == 3
        assert hero.default_prompt.en
        assert hero.default_prompt.zh
        assert hero.default_build.items or hero.default_build.affixes

        build = resolve_build(hero, bundle)
        assert build.archetype("en")
        assert build.strategy_lines("en")
        assert build.tags


def test_monster_families_have_tier_ladders_and_boss_mock_battle(bundle):
    from collections import defaultdict

    by_family: dict[str, set[str]] = defaultdict(set)
    for enemy in bundle.enemies.values():
        assert enemy.id.startswith("enemy_")
        assert enemy.family_id.startswith("family_")
        assert enemy.tier in {"trace", "ritebound", "archive_bound"}
        assert enemy.codex_stage_unknown.en
        assert enemy.codex_stage_observed.en
        assert enemy.codex_stage_familiar.en
        assert enemy.codex_stage_mastered.en
        by_family[enemy.family_id].add(enemy.tier)

    assert len(by_family) >= 4
    for tiers in by_family.values():
        assert {"trace", "ritebound"}.issubset(tiers)

    bosses = [enemy for enemy in bundle.enemies.values() if enemy.tier == "archive_bound"]
    assert bosses
    assert any(enemy.behavior.kind == "rule_chant" for enemy in bosses)

    loop = BattleLoop(
        bundle,
        MockProvider(seed=3, language="en"),
        seed=3,
        max_ticks=20,
        language="en",
    )
    state = loop.setup("hero_shadow_apprentice", [bosses[0].id])
    result = loop.run(state)
    assert result in {"victory", "defeat", "timeout"}
    assert state.enemies[0].tier == "archive_bound"


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
    assert "resonance_iron_legion" not in text

    astia = bundle.get_hero("hero_shadow_apprentice")
    astia_build = resolve_build(astia, bundle)
    astia_text = render_hero_card(astia, bundle, astia_build, language="zh")
    assert "腐化学派" in astia_text
    assert "resonance_corruption_school" not in astia_text


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
    assert "[HERO]  ##@##  prompt / build / ..." in text
    assert "[PATH]  ##==>##  route" not in text
    assert "HERO ROSTER BOARD" in text
    assert "WEAPON GALLERY BOARD" in text
    assert "[1] [W:STF] c==* [ONLINE] | Online" in text
    assert "[2] [W:SHD] [#] [ONLINE] | Online" in text
    assert "[3] [W:XBW] ==> [PAIR] | Pair" in text
    assert "[4] [W:VIL] (v) [ONLINE] | Online" in text
    assert "[5] [W:GER] [o] [ONLINE] | Online" in text
    assert "[6] [W:BEL] )o( [ONLINE] | Online" in text
    assert "AI: AI favors interrupts and tempo skills." in text
    assert "Next: compare weapon silhouettes, then open hero-card for full Build plan" in text
    assert "[1] Astia [ONLINE] | Prompt control | Risk normal | shadow / control" in text
    assert "[2] Norn" in text
    assert "Prompt guarded" in text
    assert "[3] Vela" in text
    assert "Prompt aggressive" in text
    assert "Next: ouro hero-card <hero_id> --prompt-style <name>" in text


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
    assert "WEAPON CARD: [W:STF] c==* [ONLINE]" in text
    assert "Build Before -> After: [ONLINE] shadow/control" in text
    assert "AI Effect: AI favors interrupts and tempo skills." in text
    assert "HERO LOADOUT BOARD" in text
    assert "[PROMPT] control / agent behavior" in text
    assert "[BUILD] [ONLINE] Online / Black Candle Interrupt" in text
    assert "[CORE] shadow / control" in text
    assert "[OPENER] open by denying chant windows" in text
    assert "[RUN] ouro run --mock --hero hero_shadow_apprentice --prompt-style control" in text
    assert "Corruption School" in text
    assert "resonance_corruption_school" not in text
    assert "AI Bias:" in text
    assert "Prompt Template: control" in text
    assert "interrupt high-ATB" in text


def test_render_hero_card_unicode_shows_block_weapon_art(bundle):
    from ouro_agent.tui import render_hero_card

    astia = bundle.get_hero("hero_shadow_apprentice")
    build = resolve_build(astia, bundle)
    text = render_hero_card(astia, bundle, build, language="en", unicode_mode=True)

    assert "WEAPON CARD: [W:STF] c==* [ONLINE]" in text
    assert "░▓███░" in text
    assert "AI Effect:" in text


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
        assert "HERO LOADOUT BOARD" in text
        assert "[PROMPT] hero default / agent behavior" in text
        assert f"[RUN] ouro run --mock --hero {hero_id}" in text
        assert "AI Bias:" in text
        assert "MP " in text
        assert "cd " in text


def test_build_progress_calculates_stage_for_astia(bundle):
    from ouro_agent.engine.build import BuildStage

    astia = bundle.get_hero("hero_shadow_apprentice")
    build = resolve_build(astia, bundle)
    progress = build.calculate_progress(bundle)

    assert progress.stage in {BuildStage.ONLINE, BuildStage.HIGH_ROLL, BuildStage.LOCKED_IN}
    assert progress.stage_name
    assert progress.stage.badge in {"[SEED]", "[PAIR]", "[ONLINE]", "[HIGH]", "[LOCK]"}
    assert "shadow" in progress.core_tags
    assert "control" in progress.core_tags
    assert progress.active_resonances
    assert any(r == "resonance_corruption_school" for r in progress.active_resonances)


def test_build_progress_identifies_near_resonances(bundle):
    astia = bundle.get_hero("hero_shadow_apprentice")
    build = resolve_build(astia, bundle)
    progress = build.calculate_progress(bundle)

    assert progress.near_resonances is not None
    for near in progress.near_resonances:
        assert "id" in near
        assert "display_name" in near
        assert "missing" in near
        assert near["missing"]


def test_build_progress_provides_best_next_picks(bundle):
    astia = bundle.get_hero("hero_shadow_apprentice")
    build = resolve_build(astia, bundle)
    progress = build.calculate_progress(bundle)

    assert progress.best_next_picks is not None
    for pick in progress.best_next_picks:
        assert "tag" in pick
        assert "need" in pick
        assert pick["need"] > 0


def test_build_stage_badge_display(bundle):
    from ouro_agent.engine.build import BuildStage

    assert BuildStage.SEED.badge == "[SEED]"
    assert BuildStage.PAIR.badge == "[PAIR]"
    assert BuildStage.ONLINE.badge == "[ONLINE]"
    assert BuildStage.HIGH_ROLL.badge == "[HIGH]"
    assert BuildStage.LOCKED_IN.badge == "[LOCK]"

    assert BuildStage.SEED.display_name == "Seed"
    assert BuildStage.PAIR.display_name == "Pair"
    assert BuildStage.ONLINE.display_name == "Online"
    assert BuildStage.HIGH_ROLL.display_name == "High Roll"
    assert BuildStage.LOCKED_IN.display_name == "Locked In"


def test_hero_card_shows_build_stage_badge(bundle):
    from ouro_agent.tui import render_hero_card

    astia = bundle.get_hero("hero_shadow_apprentice")
    build = resolve_build(astia, bundle)
    text = render_hero_card(astia, bundle, build, language="en")

    assert "[ONLINE]" in text or "[HIGH]" in text or "[LOCK]" in text
    assert "BUILD STAGE:" in text or "构筑阶段:" in text
    assert "Core Tags:" in text
    assert "Active Resonances:" in text
    assert "Corruption School" in text
    assert "resonance_corruption_school" not in text
