"""REQ-LLM-004 + REQ-VAL-001 + REQ-TRC-001 + REQ-ART-001 integration test."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.content import load_content_bundle
from ouro_agent.engine.battle import BattleLoop, TurnRecord
from ouro_agent.engine.models import BattleState
from ouro_agent.providers.mock import MockProvider
from ouro_agent.trace import TraceConfig, TraceWriter
from ouro_agent.tui import render_battle_screen


@pytest.fixture()
def bundle(content_root: Path):
    return load_content_bundle(content_root)


def _run(bundle, seed: int) -> tuple[BattleState, list[TurnRecord]]:
    loop = BattleLoop(
        bundle,
        MockProvider(seed=seed, language="en"),
        seed=seed,
        max_ticks=600,
        language="en",
    )
    state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    loop.run(state)
    return state, loop.records


def test_fixed_seed_is_repeatable(bundle):
    state_a, records_a = _run(bundle, seed=1)
    state_b, records_b = _run(bundle, seed=1)
    assert state_a.result == state_b.result
    assert state_a.tick == state_b.tick
    assert state_a.hero.hp == state_b.hero.hp
    assert [(r.tick, r.side, r.actor_id, r.action.type if r.action else r.enemy_action.get("type"))
            for r in records_a] == [
        (r.tick, r.side, r.actor_id, r.action.type if r.action else r.enemy_action.get("type"))
        for r in records_b
    ]


def test_trace_is_written_locally(bundle, tmp_path):
    cfg = TraceConfig(enabled=True, directory=tmp_path)
    with TraceWriter(
        run_id="run_test",
        battle_id="run_test_b001",
        seed=1,
        provider="mock",
        model="mock-smart",
        config=cfg,
    ) as trace:
        loop = BattleLoop(bundle, MockProvider(seed=1), seed=1, max_ticks=300)
        state = loop.setup(
            "hero_shadow_apprentice",
            ["enemy_hungry_cultist"],
        )

        def on_hero(_state, record):
            trace.write(
                "hero_turn",
                tick=record.tick,
                action=record.action.to_dict() if record.action else None,
                judge={
                    "valid": record.judge.valid if record.judge else False,
                    "summary": record.judge.summary if record.judge else "",
                },
                input_tokens=0,
                output_tokens=0,
                total_tokens=record.usage_total_tokens,
                latency_ms=record.usage_latency_ms,
            )

        def on_enemy(_state, record):
            trace.write("enemy_turn", tick=record.tick, action=record.enemy_action)

        loop.run(state, on_hero_turn=on_hero, on_enemy_turn=on_enemy)
        trace.write("battle_end", result=state.result, tick=state.tick)

    path = tmp_path / "run_test_b001.trace.jsonl"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "battle_start" in text
    assert "battle_end" in text
    assert "sk-" not in text


def test_battle_screen_is_ascii_safe(bundle):
    loop = BattleLoop(
        bundle,
        MockProvider(seed=2, language="en"),
        seed=2,
        max_ticks=600,
        language="en",
    )
    state = loop.setup(
        "hero_shadow_apprentice", ["enemy_hungry_cultist"]
    )
    loop.run(state)
    last_record = loop.records[-1] if loop.records else None
    screen = render_battle_screen(
        state,
        last_record,
        provider_label="mock",
        seed=2,
        unicode_mode=False,
        language="en",
    )
    assert screen.isascii()
    assert "OURO AGENT" in screen
    assert "HERO" in screen
    assert "ENEMIES" in screen
    assert "MODEL TURN" in screen
    assert "Echo Cost" in screen
