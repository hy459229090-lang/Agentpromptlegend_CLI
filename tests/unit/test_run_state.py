"""Run-state progression tests for non-combat strategy repair."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.cli.main import _run_battle_floor_label, _run_exit_code
from ouro_agent.content import load_content_bundle
from ouro_agent.sessions.run_state import RunPhase, create_run_state
from ouro_agent.content.schema import CodexStage


@pytest.fixture()
def bundle(content_root: Path):
    return load_content_bundle(content_root)


def _shop_state(bundle):
    state = create_run_state(
        "run_shop",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    state.current_floor_index = 1
    state.current_node_index = 1
    state.set_shop_items(list(state.current_node(bundle).shop_items))
    state.gold = 50
    return state


def test_shop_repairs_resources_strategy_and_scouting(bundle):
    """REQ-PLAY-003: shop purchases should change run strategy state."""
    state = _shop_state(bundle)
    state.current_hp = max(1, state.max_hp // 2)
    state.current_mp = 0

    heal_index = next(i for i, item in enumerate(state.current_choices) if item.type == "heal")
    strategy_index = next(i for i, item in enumerate(state.current_choices) if item.type == "strategy")
    scout_index = next(i for i, item in enumerate(state.current_choices) if item.type == "scout")

    assert state.buy_shop_item(heal_index, bundle)
    assert state.current_hp > state.max_hp // 2
    assert state.current_mp == state.max_mp

    assert state.buy_shop_item(strategy_index, bundle)
    assert state.strategy_style == "control"

    assert state.buy_shop_item(scout_index, bundle)
    assert state.scout_notes
    assert "chant" in state.scout_notes[-1].lower()


def test_rest_options_are_mutually_exclusive_strategy_repairs(bundle):
    """REQ-PLAY-003: Recover, Focus, and Study should have distinct effects."""
    recover = create_run_state("run_recover", 7, "hero_shadow_apprentice", "dungeon_ember_crypt", bundle)
    recover.current_floor_index = 1
    recover.current_node_index = 2
    recover.set_rest_phase()
    recover.current_hp = recover.max_hp // 2
    recover.current_mp = 0
    recover.apply_rest(option="recover")
    assert recover.current_hp > recover.max_hp // 2
    assert recover.current_mp == recover.max_mp
    assert recover.next_battle_shield == 0

    focus = create_run_state("run_focus", 7, "hero_shadow_apprentice", "dungeon_ember_crypt", bundle)
    focus.current_floor_index = 1
    focus.current_node_index = 2
    focus.set_rest_phase()
    focus.current_hp = focus.max_hp // 2
    focus.current_mp = 0
    focus.apply_rest(option="focus")
    assert focus.current_hp == focus.max_hp // 2
    assert focus.current_mp == 0
    assert focus.next_battle_shield >= 12

    study = create_run_state("run_study", 7, "hero_shadow_apprentice", "dungeon_ember_crypt", bundle)
    study.current_floor_index = 1
    study.current_node_index = 2
    study.set_rest_phase()
    study.apply_rest(option="study")
    assert study.scout_notes
    assert study.next_battle_shield == 0


def test_run_state_records_battle_and_codex_reward_progress(bundle):
    """REQ-CODEX-002: run state carries codex combat and study progress."""
    state = create_run_state(
        "run_codex",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )

    state.record_codex_battle(
        bundle,
        ["enemy_hungry_cultist"],
        {"enemy_hungry_cultist"},
    )
    assert (
        state.codex_progress.get_stage("family_hungry_cultist", "trace")
        == CodexStage.OBSERVED
    )

    node = state.current_node(bundle)
    state.set_reward_choices(list(node.rewards.reward_choices))
    codex_index = next(
        index
        for index, choice in enumerate(state.current_choices)
        if choice.type == "codex"
    )
    state.choose_reward(codex_index, bundle)

    entry = state.codex_progress.find_entry("family_hungry_cultist", "trace")
    assert entry is not None
    assert entry.defeats == 2
    assert entry.stage == CodexStage.FAMILIAR
    assert "Codex study" in state.scout_notes[-1]


def test_run_state_reports_floor_completion_from_visited_nodes(bundle):
    """REQ-RUNSTATE-001: route state exposes reliable floor completion."""
    state = create_run_state(
        "run_floor",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )

    assert not state.is_floor_complete(bundle)

    first_floor = state.current_floor(bundle)
    state.visited_node_ids.update(first_floor.nodes)
    assert state.is_floor_complete(bundle)

    state.advance_to_next_floor(bundle)
    assert not state.is_floor_complete(bundle)

    second_floor = state.current_floor(bundle)
    state.visited_node_ids.update(second_floor.nodes[:-1])
    assert not state.is_floor_complete(bundle)
    state.visited_node_ids.add(second_floor.nodes[-1])
    assert state.is_floor_complete(bundle)


def test_run_battle_floor_label_follows_current_floor(bundle):
    """REQ-RUNSTATE-002: battle headers should reflect run floor context."""
    state = create_run_state(
        "run_floor_label",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )

    assert _run_battle_floor_label(state, bundle, "en") == "EMBER CRYPT :: FLOOR 1"

    state.advance_to_next_floor(bundle)

    assert _run_battle_floor_label(state, bundle, "en") == "EMBER CRYPT :: FLOOR 2"
    assert _run_battle_floor_label(state, bundle, "zh") == "灰烬墓室 :: 第 2 层"


def test_run_exit_code_treats_death_as_played_session_by_default(bundle):
    """REQ-CLIUX-001: a normal death is a game result, not a CLI crash."""
    state = create_run_state(
        "run_exit",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    state.phase = RunPhase.DEAD

    assert _run_exit_code(state) == 0
    assert _run_exit_code(state, strict_result_exit_code=True) == 1

    state.phase = RunPhase.COMPLETE

    assert _run_exit_code(state, strict_result_exit_code=True) == 0
