"""REQ-LLM-004 + REQ-VAL-001 + REQ-TRC-001 + REQ-ART-001 integration test."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.content import load_content_bundle
from ouro_agent.engine.battle import BattleLoop, TurnRecord
from ouro_agent.engine.judge import JudgeOutcome
from ouro_agent.engine.models import BattleState
from ouro_agent.cli.main import main
from ouro_agent.llm.actions import HeroAction
from ouro_agent.providers.mock import MockProvider
from ouro_agent.trace import TraceConfig, TraceWriter
from ouro_agent.tui import render_battle_report, render_battle_screen
from ouro_agent.engine.models import StatusEffect


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


def test_battle_llm_session_ids_static_hash_and_delta_are_traced(bundle, tmp_path):
    cfg = TraceConfig(enabled=True, directory=tmp_path)
    loop = BattleLoop(
        bundle,
        MockProvider(seed=1, language="en"),
        seed=1,
        max_ticks=300,
        language="en",
        battle_session_id="be_test_b001",
    )
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    assert loop.battle_llm_session is not None

    with TraceWriter(
        run_id="run_test",
        battle_id="run_test_b001",
        seed=1,
        provider="mock",
        model="mock-smart",
        battle_session_id=loop.battle_llm_session.battle_session_id,
        static_context_hash=loop.battle_llm_session.static_context_hash,
        config=cfg,
    ) as trace:

        def on_hero(_state, record):
            trace.write(
                "hero_turn",
                tick=record.tick,
                battle_session_id=record.battle_session_id,
                static_context_hash=record.static_context_hash,
                delta_context_id=record.delta_context_id,
                delta_context=record.delta_context,
            )

        loop.run(state, on_hero_turn=on_hero)

    text = (tmp_path / "run_test_b001.trace.jsonl").read_text(encoding="utf-8")
    assert '"battle_session_id": "be_test_b001"' in text
    assert '"static_context_hash": "ctx_' in text
    assert '"delta_context_id": "be_test_b001_d0001"' in text
    assert '"hero_delta"' in text
    assert '"skill_delta"' in text


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


def test_battle_screen_uses_duel_layout_build_and_session(bundle):
    loop = BattleLoop(
        bundle,
        MockProvider(seed=2, language="en"),
        seed=2,
        max_ticks=600,
        language="en",
        battle_session_id="be_snapshot",
    )
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.hero.add_status(StatusEffect(id="status_shield", stacks=5, duration=2))
    state.enemies[0].add_status(
        StatusEffect(id="status_corruption", stacks=1, duration=3)
    )
    last_record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_hex_seal",
            targets=("enemy_hungry_cultist",),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary="cast_skill skill_hex_seal -> enemy_hungry_cultist | 16 dmg",
            damage=16,
            target_ids=("enemy_hungry_cultist",),
            skill_id="skill_hex_seal",
            action_kind="cast_skill",
        ),
        battle_session_id="be_snapshot",
        static_context_hash=loop.battle_llm_session.static_context_hash,
        delta_context_id="be_snapshot_d0001",
    )
    screen = render_battle_screen(
        state,
        last_record,
        provider_label="mock",
        seed=2,
        unicode_mode=False,
        language="en",
    )
    assert "+---------------- HERO ----------------+" in screen
    assert "+-------------- ENEMY --------------+" in screen
    assert "WEAPON [W:STF]" in screen
    assert "BUILD [ONLINE]" in screen
    assert "Battle Echo: be_snapshot" in screen
    assert "Sealed Echo: ctx_" in screen
    assert "Fresh Echo: be_snapshot_d" in screen
    assert "BUFF   : status_shield" in screen
    assert "DEBUFF : status_corruption" in screen
    assert any(effect in screen for effect in ("-- seal -->", "-- sting ->", "-- focus ->"))


def test_battle_screen_has_80_column_compact_duel_snapshot(bundle):
    loop = BattleLoop(
        bundle,
        MockProvider(seed=2, language="en"),
        seed=2,
        max_ticks=600,
        language="en",
        battle_session_id="be_compact",
    )
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_hex_seal",
            targets=("enemy_hungry_cultist",),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary="cast_skill skill_hex_seal -> enemy_hungry_cultist | 16 dmg",
            damage=16,
            target_ids=("enemy_hungry_cultist",),
            skill_id="skill_hex_seal",
            action_kind="cast_skill",
        ),
        battle_session_id="be_compact",
        static_context_hash=loop.battle_llm_session.static_context_hash,
        delta_context_id="be_compact_d0001",
    )
    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=2,
        unicode_mode=False,
        language="en",
        width=80,
    )
    assert "[CNDL] Astia" in screen
    assert "[c] Hungry Cultist" in screen
    assert "-- seal -->" in screen
    assert "HP [########]" in screen
    assert "BUILD [ONLINE]" in screen
    compact_lines = screen.splitlines()[5:18]
    assert max(len(line) for line in compact_lines) <= 80


def test_battle_report_summarizes_action_mix(bundle):
    state, records = _run(bundle, seed=1)
    report = render_battle_report(state, records, language="en")
    assert report.isascii()
    assert "BATTLE REPORT" in report
    assert "Hero action mix" in report
    assert "Skill usage" in report
    assert "Damage dealt" in report
    assert "Fallbacks" in report


def test_cli_play_prints_turn_frames_and_report(content_root, isolated_home, capsys):
    rc = main(
        [
            "--lang",
            "en",
            "play",
            "--mock",
            "--seed",
            "1",
            "--no-trace",
            "--no-animation",
            "--content-dir",
            str(content_root),
        ]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "--- turn 1 / tick" in out
    assert out.count("--- turn ") >= 2
    assert "BATTLE COMPLETE" in out
    assert "BATTLE REPORT" in out
    assert out.isascii()


def test_cli_prompt_style_is_visible_in_trace(content_root, isolated_home, tmp_path):
    rc = main(
        [
            "--lang",
            "en",
            "play",
            "--mock",
            "--seed",
            "1",
            "--no-animation",
            "--prompt-style",
            "control",
            "--content-dir",
            str(content_root),
            "--trace-dir",
            str(tmp_path),
        ]
    )

    assert rc == 0
    trace_text = next(tmp_path.glob("*.trace.jsonl")).read_text(encoding="utf-8")
    assert '"prompt_style": "control"' in trace_text
    assert '"prompt_template": "Control:' in trace_text
    assert "interrupt high-ATB" in trace_text
