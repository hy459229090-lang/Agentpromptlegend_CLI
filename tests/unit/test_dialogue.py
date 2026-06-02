from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.art.battle_dialogue import DIALOGUE_CATEGORIES, HERO_DIALOGUE, select_dialogue_line
from ouro_agent.content import load_content_bundle
from ouro_agent.tui.frame_builder import BattleFrame


@pytest.fixture()
def bundle(content_root: Path):
    return load_content_bundle(content_root)


def _frame(*, event_banner: str | None = None, risk: str = "stable", tick: int = 0) -> BattleFrame:
    return BattleFrame(
        frame_id=f"dialogue_{tick}",
        tick=tick,
        phase="hero_action",
        actor_id="hero_shadow_apprentice",
        target_ids=("enemy_hungry_cultist",),
        action_label="Hex Seal -> Hungry Cultist",
        judge_label="VALID | -16 HP",
        intent="control the fastest threat",
        risk=risk,
        align="Control",
        effect_kind="seal",
        effect_glyph="--x seal --",
        event_banner=event_banner,
    )


def test_every_hero_has_three_lines_for_each_situational_dialogue_category(bundle):
    """REQ-DLG-001: six heroes carry 8 categories with EN/ZH variants."""
    assert set(HERO_DIALOGUE) == set(bundle.heroes)

    for hero_id, table in HERO_DIALOGUE.items():
        assert set(DIALOGUE_CATEGORIES).issubset(table), hero_id
        for category in DIALOGUE_CATEGORIES:
            localized = table[category]
            assert set(localized) >= {"en", "zh"}, (hero_id, category)
            assert len(localized["en"]) >= 3, (hero_id, category, "en")
            assert len(localized["zh"]) >= 3, (hero_id, category, "zh")
            assert all(line.strip() for line in localized["en"]), (hero_id, category, "en")
            assert all(line.strip() for line in localized["zh"]), (hero_id, category, "zh")


def test_dialogue_selector_responds_to_distinct_battle_situations():
    """REQ-DLG-001: low HP, MP pressure, interrupt, build, and boss phase differ."""
    hero_id = "hero_shadow_apprentice"
    samples = {
        "intro": select_dialogue_line(hero_id, frame=None, hp_pct=1.0, mp_pct=1.0, lang="en", tick=0),
        "low_hp": select_dialogue_line(hero_id, frame=None, hp_pct=0.25, mp_pct=1.0, lang="en", tick=0),
        "mp_low": select_dialogue_line(hero_id, frame=None, hp_pct=1.0, mp_pct=0.1, lang="en", tick=0),
        "interrupt_success": select_dialogue_line(
            hero_id,
            frame=_frame(event_banner="CHARGE BROKEN"),
            hp_pct=1.0,
            mp_pct=1.0,
            lang="en",
            tick=0,
        ),
        "build_trigger": select_dialogue_line(
            hero_id,
            frame=_frame(event_banner="BUILD ONLINE"),
            hp_pct=1.0,
            mp_pct=1.0,
            lang="en",
            tick=0,
        ),
        "boss_phase": select_dialogue_line(
            hero_id,
            frame=_frame(event_banner="BOSS PHASE II"),
            hp_pct=1.0,
            mp_pct=1.0,
            lang="en",
            tick=0,
        ),
        "near_defeat": select_dialogue_line(hero_id, frame=None, hp_pct=0.1, mp_pct=1.0, lang="en", tick=0),
    }

    assert all(samples.values())
    assert len(set(samples.values())) == len(samples)
    assert "candle" in samples["intro"].lower()
    assert "guttering" in samples["low_hp"].lower()
    assert "echo" in samples["mp_low"].lower()
    assert "wick" in samples["interrupt_success"].lower()
    assert "pattern" in samples["build_trigger"].lower()
    assert "second wick" in samples["boss_phase"].lower()
    assert "last candle" in samples["near_defeat"].lower()


def test_dialogue_selector_uses_localized_lines():
    line = select_dialogue_line(
        "hero_ash_guardian",
        frame=_frame(event_banner="BOSS PHASE II", tick=2),
        hp_pct=1.0,
        mp_pct=1.0,
        lang="zh",
        tick=2,
    )

    assert line == "它伸得太远时，高塔会回应。"
