"""REQ-BTL-001..005 deterministic combat behavior."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.content import load_content_bundle
from ouro_agent.engine.battle import BattleLoop
from ouro_agent.engine.judge import Judge
from ouro_agent.engine.models import StatusEffect
from ouro_agent.llm.actions import HeroAction
from ouro_agent.providers.mock import MockProvider


@pytest.fixture()
def bundle(content_root: Path):
    return load_content_bundle(content_root)


def test_atb_progression_is_deterministic(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1, max_ticks=5)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    initial_atb = state.hero.atb
    loop._advance_atb(state)  # noqa: SLF001
    assert state.hero.atb == initial_atb + state.hero.speed


def test_skill_consumes_mp_and_sets_cooldown(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    judge = Judge(bundle.skills)
    hero = state.hero
    initial_mp = hero.mp
    outcome = judge.resolve(
        HeroAction(
            type="cast_skill",
            skill_id="skill_shadow_sting",
            targets=("enemy_hungry_cultist",),
        ),
        state,
    )
    assert outcome.valid
    assert hero.mp == initial_mp - 12
    assert hero.find_skill("skill_shadow_sting").cooldown_remaining == 2


def test_skill_blocked_when_no_mp(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.hero.mp = 0
    outcome = Judge(bundle.skills).resolve(
        HeroAction(
            type="cast_skill",
            skill_id="skill_shadow_sting",
            targets=("enemy_hungry_cultist",),
        ),
        state,
    )
    assert not outcome.valid
    assert "MP" in outcome.reason


def test_skill_blocked_when_on_cooldown(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    skill = state.hero.find_skill("skill_shadow_sting")
    skill.cooldown_remaining = 2
    outcome = Judge(bundle.skills).resolve(
        HeroAction(type="cast_skill", skill_id="skill_shadow_sting"),
        state,
    )
    assert not outcome.valid
    assert "cooldown" in outcome.reason


def test_unknown_skill_falls_back_via_judge(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    outcome = Judge(bundle.skills).resolve(
        HeroAction(type="cast_skill", skill_id="skill_made_up"),
        state,
    )
    assert not outcome.valid
    assert outcome.fallback_to == "basic_attack"


def test_full_mock_battle_resolves(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1, max_ticks=600)
    state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    result = loop.run(state)
    assert result in {"victory", "defeat"}
    assert result != "timeout"
    assert state.hero.is_alive == (result == "victory")


def test_status_shield_absorbs_damage(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.hero.add_status(StatusEffect(id="status_shield", stacks=10, duration=2))
    enemy = state.enemies[0]
    from ouro_agent.engine.enemy_ai import resolve_enemy_action

    initial_hp = state.hero.hp
    resolve_enemy_action(enemy, {"type": "basic_attack"}, state)
    assert state.hero.find_status("status_shield").stacks < 10
    assert state.hero.hp >= initial_hp - max(1, enemy.attack)
