from __future__ import annotations

import json
from pathlib import Path

import pytest

from ouro_agent.cli.main import main
from ouro_agent.trace import TraceReplayError, render_trace_replay


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_TRACE = ROOT / "examples/traces/mvp_a_seed7_mock.trace.jsonl"


def test_trace_replay_renders_example_timeline():
    """REQ-REPLAY-001: checked-in traces can be replayed without network."""
    text = render_trace_replay(EXAMPLE_TRACE, language="en", limit=4)

    assert "OURO TRACE REPLAY" in text
    assert "Battle: run_1777795937_b001" in text
    assert "REPLAY DIRECTOR BOARD" in text
    assert "[TURNS] hero" in text
    assert "[FIRST HERO] Hex Seal -> Hungry Cultist" in text
    assert "REPLAY BEAT MAP" in text
    assert "[FLOW] H009 -> E010" in text
    assert "[SPAN] tick 9->209 / events" in text
    assert "[PRESSURE] hero dealt" in text
    assert "[READ] H=hero action, E=enemy action, +N=hidden tail" in text
    assert "Timeline:" in text
    assert "[009] HERO" in text
    assert "Hex Seal -> Hungry Cultist" in text
    assert "Judge: Hex Seal -> Hungry Cultist" in text
    assert "ENEMY Black Candle Acolyte" in text
    assert "Echo Cost" in text
    assert "Ritual Time" in text
    assert "more events omitted" in text
    assert "skill_" not in text
    assert "enemy_" not in text
    assert "hero_" not in text


def test_trace_replay_falls_back_to_readable_ids_without_content_bundle(tmp_path: Path):
    trace = tmp_path / "trace_without_content.trace.jsonl"
    rows = [
        {
            "kind": "battle_start",
            "run_id": "run_y",
            "battle_id": "run_y_b001",
            "seed": 11,
            "provider": "mock",
            "model": "mock-smart",
            "battle_session_id": "be_y",
            "static_context_hash": "ctx_y",
        },
        {
            "kind": "hero_turn",
            "run_id": "run_y",
            "battle_id": "run_y_b001",
            "tick": 8,
            "action": {
                "type": "cast_skill",
                "skill_id": "skill_shadow_sting",
                "targets": ["enemy_mire_rat"],
            },
            "judge": {
                "summary": (
                    "cast_skill skill_shadow_sting -> enemy_mire_rat | 14 dmg"
                )
            },
        },
        {
            "kind": "enemy_turn",
            "run_id": "run_y",
            "battle_id": "run_y_b001",
            "tick": 9,
            "actor_id": "enemy_mire_rat",
            "action": {"type": "basic_attack"},
        },
        {
            "kind": "battle_end",
            "run_id": "run_y",
            "battle_id": "run_y_b001",
            "result": "victory",
            "tick": 13,
        },
    ]
    trace.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows),
        encoding="utf-8",
    )

    text = render_trace_replay(
        trace,
        language="en",
        content_dir=tmp_path / "missing-content",
    )

    assert "Shadow Sting -> Mire Rat" in text
    assert "Judge: Shadow Sting -> Mire Rat | 14 dmg" in text
    assert "ENEMY Mire Rat" in text


def test_trace_replay_shows_model_summary_and_result(tmp_path: Path):
    trace = tmp_path / "sample.trace.jsonl"
    rows = [
        {
            "kind": "battle_start",
            "run_id": "run_x",
            "battle_id": "run_x_b001",
            "seed": 3,
            "provider": "mock",
            "model": "mock-smart",
            "battle_session_id": "be_x",
            "static_context_hash": "ctx_x",
        },
        {
            "kind": "hero_turn",
            "run_id": "run_x",
            "battle_id": "run_x_b001",
            "tick": 12,
            "prompt_style": "control",
            "model_analysis": "interrupt the chant before damage racing",
            "model_narration": "Astia snaps the seal shut.",
            "action": {
                "type": "cast_skill",
                "skill_id": "skill_hex_seal",
                "targets": ["enemy_black_candle_acolyte"],
            },
            "judge": {
                "summary": (
                    "cast_skill skill_hex_seal -> enemy_black_candle_acolyte | 16 dmg"
                )
            },
            "total_tokens": 9,
            "latency_ms": 42,
        },
        {
            "kind": "enemy_turn",
            "run_id": "run_x",
            "battle_id": "run_x_b001",
            "tick": 16,
            "actor_id": "enemy_black_candle_acolyte",
            "action": {"type": "silenced"},
        },
        {
            "kind": "battle_end",
            "run_id": "run_x",
            "battle_id": "run_x_b001",
            "result": "victory",
            "tick": 31,
        },
    ]
    trace.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows),
        encoding="utf-8",
    )

    text = render_trace_replay(trace, language="en")

    assert "Battle Echo: be_x" in text
    assert "Prompt style: control" in text
    assert "REPLAY DIRECTOR BOARD" in text
    assert "[PROMPT] control" in text
    assert "[RESULT] victory @ tick 31" in text
    assert "[ECHO] Echo Cost 9 / Ritual Time 42ms" in text
    assert "REPLAY BEAT MAP" in text
    assert "[FLOW] H012 -> E016" in text
    assert "[SPAN] tick 12->16 / events 2" in text
    assert "[PRESSURE] hero dealt 16 / enemy listed 0" in text
    assert "[FIRST HERO] Hex Seal -> Black Candle Acolyte" in text
    assert "Judge: Hex Seal -> Black Candle Acolyte | 16 dmg" in text
    assert "ENEMY Black Candle Acolyte | action: Silenced" in text
    assert "Model: interrupt the chant before damage racing" in text
    assert "Narration: Astia snaps the seal shut." in text
    assert "Echo Cost 9 | Ritual Time 42ms" in text
    assert "Result: victory @ tick 31" in text


def test_cli_replay_accepts_language_after_subcommand(isolated_home, capsys):
    rc = main(["replay", str(EXAMPLE_TRACE), "--limit", "2", "--lang", "en"])

    out = capsys.readouterr().out
    assert rc == 0
    assert "OURO TRACE REPLAY" in out
    assert "Timeline:" in out
    assert "more events omitted" in out
    assert "Hex Seal -> Hungry Cultist" in out
    assert "skill_" not in out
    assert "enemy_" not in out


def test_trace_replay_rejects_invalid_json(tmp_path: Path):
    trace = tmp_path / "bad.trace.jsonl"
    trace.write_text("{not json}\n", encoding="utf-8")

    with pytest.raises(TraceReplayError, match="invalid JSON"):
        render_trace_replay(trace)
