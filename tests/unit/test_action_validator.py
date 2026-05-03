"""REQ-LLM-001/002 action validator behavior."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.content import load_content_bundle
from ouro_agent.engine.battle import BattleLoop
from ouro_agent.llm.actions import FallbackReason
from ouro_agent.llm.validator import parse_model_output
from ouro_agent.providers.mock import MockProvider


@pytest.fixture()
def state_and_bundle(content_root: Path):
    bundle = load_content_bundle(content_root)
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=42)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    return state, bundle


def test_valid_action_parses(state_and_bundle):
    state, bundle = state_and_bundle
    raw = (
        '{"narration": "n", "analysis": "a", "confidence": 0.7, '
        '"action": {"type": "cast_skill", "skill_id": "skill_shadow_sting", '
        '"targets": ["enemy_hungry_cultist"]}}'
    )
    res = parse_model_output(raw, bundle, state)
    assert res.fallback_reason is FallbackReason.NONE
    assert res.action.type == "cast_skill"
    assert res.action.skill_id == "skill_shadow_sting"
    assert res.action.targets == ("enemy_hungry_cultist",)


def test_repairable_json_is_repaired(state_and_bundle):
    state, bundle = state_and_bundle
    raw = (
        "Here is my plan: {\"action\": {\"type\": \"basic_attack\", "
        "\"targets\": [\"enemy_hungry_cultist\"],}}"
    )
    res = parse_model_output(raw, bundle, state)
    assert res.repaired is True
    assert res.action.type == "basic_attack"


def test_unknown_skill_falls_back_to_basic_attack(state_and_bundle):
    state, bundle = state_and_bundle
    raw = (
        '{"action": {"type": "cast_skill", "skill_id": "skill_does_not_exist", '
        '"targets": ["enemy_hungry_cultist"]}}'
    )
    res = parse_model_output(raw, bundle, state)
    assert res.fallback_reason is FallbackReason.UNKNOWN_SKILL
    assert res.action.type == "basic_attack"
    assert res.action.targets == ("enemy_hungry_cultist",)


def test_unparseable_text_falls_back_to_defend(state_and_bundle):
    state, bundle = state_and_bundle
    res = parse_model_output("complete gibberish, not json", bundle, state)
    assert res.fallback_reason is FallbackReason.JSON_PARSE_FAILED
    assert res.action.type == "defend"


def test_empty_text_falls_back(state_and_bundle):
    state, bundle = state_and_bundle
    res = parse_model_output("", bundle, state)
    assert res.fallback_reason is FallbackReason.EMPTY_RESPONSE
    assert res.action.type == "defend"


def test_unknown_action_type(state_and_bundle):
    state, bundle = state_and_bundle
    raw = '{"action": {"type": "explode_galaxy", "targets": []}}'
    res = parse_model_output(raw, bundle, state)
    assert res.fallback_reason is FallbackReason.UNKNOWN_ACTION_TYPE
    assert res.action.type == "defend"
