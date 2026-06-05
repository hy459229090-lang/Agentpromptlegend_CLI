"""REQ-LLM-004 + REQ-VAL-001 + REQ-TRC-001 + REQ-ART-001 integration test."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.content import load_content_bundle
from ouro_agent.config import OuroConfig, save_config
from ouro_agent.engine.battle import BattleLoop, TurnRecord
from ouro_agent.engine.judge import JudgeOutcome
from ouro_agent.engine.models import BattleState
from ouro_agent.cli.main import main
from ouro_agent.llm.actions import HeroAction
from ouro_agent.providers.mock import MockProvider
from ouro_agent.sessions import codex_path, load_codex_progress
from ouro_agent.sessions.run_state import create_run_state
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
    assert "CINEMATIC BEAT" in screen
    assert "VOX" in screen
    assert "ENM" in screen
    assert "FLOAT" in screen
    assert "STRIP" in screen
    assert "LOG" in screen


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
    assert "THE ECHO ALTAR" in screen
    assert "[ ACTION ]" in screen
    assert "[ BATTLE THESIS ]" in screen
    assert "[ ECHO READOUT ]" in screen
    assert "WEAPON [W:STF]" in screen
    assert "BUILD [ONLINE]" in screen
    assert "Battle Echo: be_snapshot" in screen
    assert "Sealed Echo: ctx_" in screen
    assert "Fresh Echo: be_snapshot_d" in screen
    assert "BUFF   : SHD shield" in screen
    assert "DEBUFF : CRP corrupt" in screen
    assert "ACTION" in screen
    assert "INTENT" in screen
    assert "RISK" in screen
    assert "ALIGN" in screen
    assert any(effect in screen for effect in ("-- seal -->", "-- sting ->", "-- focus ->"))
    assert "CINEMATIC BEAT" in screen
    assert "VOX" in screen
    assert "ENM" in screen
    assert "FLOAT" in screen
    assert "STRIP" in screen
    assert "LOG" in screen


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
    assert "BATTLE RESULT BOARD" in report
    assert "BATTLE TURN MAP" in report
    assert "[FLOW] H" in report
    assert "[FIRST HERO]" in report
    assert "[FIRST HERO] Hex Seal" in report
    assert "[FIRST HERO] skill_" not in report
    assert "[IMPACT] peak hit" in report
    assert "[READ]" in report
    assert "[RESULT] victory" in report
    assert "[TEMPO] hero" in report
    assert "[ACTION] basic:skill" in report
    assert "[DAMAGE] dealt" in report
    assert "[NEXT]" in report
    assert "Hero action mix" in report
    assert "Skill usage" in report
    assert "Hex Seal" in report
    assert "Skill usage: skill_" not in report
    assert "Damage dealt" in report
    assert "Fallbacks" in report
    assert "PLAY NEXT BOARD" in report
    assert (
        "  [REMATCH] ouro play --mock --hero hero_shadow_apprentice "
        "--prompt-style control --seed 2" in report
    )
    assert "  [REVIEW] ouro status | ouro run-report" in report
    assert "[CODEX] ouro codex" in report
    assert "ouro hero-card hero_shadow_apprentice --prompt-style control" in report
    assert "  [GUIDANCE] Keep the plan, then raise pressure with next seed." in report


def test_battle_report_shows_prompt_impact(bundle):
    loop = BattleLoop(
        bundle,
        MockProvider(seed=7, language="en"),
        seed=7,
        max_ticks=600,
        language="en",
        prompt_style="control",
    )
    state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    loop.run(state)

    report = render_battle_report(state, loop.records, language="en")

    assert "Prompt Impact:" in report
    assert "Control template" in report
    assert "Hex Seal" in report


def test_battle_report_shows_trace_based_defeat_lessons(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0, language="en"), seed=1, language="en")
    state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    cultist, acolyte = state.enemies
    state.tick = 72
    state.result = "defeat"
    state.hero.hp = 0
    state.emit(
        "enemy_attack",
        enemy_id=acolyte.id,
        target_id=state.hero.id,
        damage=72,
        kind="chant_release",
    )
    records = [
        TurnRecord(
            tick=18,
            actor_id=acolyte.id,
            side="enemy",
            raw_text=None,
            validation=None,
            action=None,
            judge=None,
            enemy_action={"type": "chant_charge"},
        ),
        TurnRecord(
            tick=24,
            actor_id=state.hero.id,
            side="hero",
            raw_text=None,
            validation=None,
            action=HeroAction(type="basic_attack", targets=(cultist.id,)),
            judge=JudgeOutcome(
                valid=True,
                reason="basic attack landed",
                summary=f"basic_attack -> {cultist.id} | 4 dmg",
                damage=4,
                target_ids=(cultist.id,),
                action_kind="basic_attack",
            ),
            delta_context={
                "enemy_delta": [
                    {"id": cultist.id, "hp": 12, "atb": 20, "tier": cultist.tier, "chant_progress": 0},
                    {"id": acolyte.id, "hp": 78, "atb": 96, "tier": acolyte.tier, "chant_progress": 1},
                ]
            },
        ),
        TurnRecord(
            tick=36,
            actor_id=acolyte.id,
            side="enemy",
            raw_text=None,
            validation=None,
            action=None,
            judge=None,
            enemy_action={"type": "chant_release", "damage": 72},
        ),
    ]

    report = render_battle_report(state, records, language="en")

    assert "Failure Reasons:" in report
    assert "Next Run Advice:" in report
    assert "Targeting:" in report
    assert "Targeting drift turns: 1" in report
    assert "PLAY NEXT BOARD" in report
    assert "  [GUIDANCE] Review this run first, then retry with control/guarded." in report


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
    assert out.startswith("=")
    assert "OURO AGENT :: PROMPT LEGEND" in out
    assert "RUN SETUP" in out
    assert "Equipment Loadout" in out
    assert "ENCOUNTER BRIEFING" in out
    assert "[ENEMY]" in out
    assert "[THREAT]" in out
    assert "[WINDOW]" in out
    assert "[PLAN]" in out
    assert "model reading field" in out
    assert "ENEMY ROSTER" in out
    assert "Tactical Readout" in out
    assert "--- turn 1 / tick" in out
    assert out.count("--- turn ") >= 2
    assert "IMPACT" in out
    assert "FAIL IF" in out
    assert "COUNTER CLOCK" in out
    assert "CINEMATIC BEAT" in out
    assert "VOX" in out
    assert "ENM" in out
    assert "FLOAT" in out
    assert "STRIP" in out
    assert "Problem:" in out
    assert "Next Build Pick:" in out
    assert "BATTLE COMPLETE" in out
    assert "BATTLE REPORT" in out
    assert "PLAY NEXT BOARD" in out
    assert (
        "  [REMATCH] ouro play --mock --hero hero_shadow_apprentice "
        "--prompt-style control --seed 2" in out
    )
    assert "  [REVIEW] ouro status | ouro run-report" in out
    assert out.isascii()


def test_cli_play_persists_codex_progress(content_root, isolated_home, capsys):
    """REQ-CODEX-002: a local mock battle writes reusable codex knowledge."""
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
    progress = load_codex_progress()
    hungry = progress.find_entry("family_hungry_cultist", "trace")
    candle = progress.find_entry("family_black_candle", "trace")
    assert rc == 0
    assert codex_path().exists()
    assert f"Codex : {codex_path()}" in out
    assert hungry is not None
    assert hungry.encounters >= 1
    assert hungry.defeats >= 1
    assert candle is not None
    assert candle.encounters >= 1
    assert "sk-" not in codex_path().read_text(encoding="utf-8")


def test_cli_play_warns_when_codex_save_is_unavailable(
    content_root,
    tmp_path,
    monkeypatch,
    capsys,
):
    """REQ-CODEX-002: optional persistence cannot break mock play."""
    blocked_home = tmp_path / "blocked-home"
    blocked_home.write_text("not a directory", encoding="utf-8")
    monkeypatch.setenv("OURO_AGENT_HOME", str(blocked_home))

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
    assert "Warning: could not save Codex progress" in out
    assert "BATTLE COMPLETE" in out
    assert "Codex :" not in out


def test_cli_play_uses_saved_provider_config_when_not_mock(
    content_root,
    isolated_home,
    monkeypatch,
    capsys,
):
    """REQ-PROV-004: play should honor saved provider config unless --mock is used."""
    save_config(
        OuroConfig(
            provider="openai-compatible",
            model="qwen-live",
            api_key_env="OURO_API_KEY",
            base_url="https://llm.example.test/v1",
            timeout_seconds=66,
            max_retries=3,
            language="en",
        )
    )
    captured: dict[str, object] = {}

    def fake_build_provider(config, *, seed=0, force_mock=False, language="zh"):
        captured["config"] = config
        captured["seed"] = seed
        captured["force_mock"] = force_mock
        captured["language"] = language
        return MockProvider(seed=seed, language=language, model="fake-live")

    monkeypatch.setattr("ouro_agent.cli.main.build_provider", fake_build_provider)

    rc = main(
        [
            "play",
            "--seed",
            "1",
            "--no-trace",
            "--no-animation",
            "--content-dir",
            str(content_root),
        ]
    )

    capsys.readouterr()
    config = captured["config"]

    assert rc == 0
    assert isinstance(config, OuroConfig)
    assert config.provider == "openai-compatible"
    assert config.model == "qwen-live"
    assert config.api_key_env == "OURO_API_KEY"
    assert config.base_url == "https://llm.example.test/v1"
    assert config.timeout_seconds == 66
    assert config.max_retries == 3
    assert captured["force_mock"] is False
    assert captured["language"] == "en"


def test_cli_run_death_returns_successful_session_code(content_root, isolated_home, capsys):
    """REQ-CLIUX-001: player death is a valid game ending, not a CLI failure."""
    rc = main(
        [
            "--lang",
            "en",
            "run",
            "--mock",
            "--seed",
            "7",
            "--no-animation",
            "--auto",
            "--no-trace",
            "--content-dir",
            str(content_root),
        ]
    )

    out = capsys.readouterr().out

    assert rc == 0
    assert "YOU DIED" in out
    assert "Run Archive:" in out
    assert "Death History:" in out


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
    assert '"model_analysis":' in trace_text
    assert '"model_narration":' in trace_text
    assert '"raw_text":' in trace_text


def test_cli_batch_prompt_style_is_reported(content_root, isolated_home, capsys):
    rc = main(
        [
            "--lang",
            "en",
            "batch",
            "--count",
            "2",
            "--seed",
            "7",
            "--hero",
            "hero_shadow_apprentice",
            "--enemies",
            "enemy_hungry_cultist",
            "enemy_black_candle_acolyte",
            "--prompt-style",
            "control",
            "--content-dir",
            str(content_root),
            "--quiet",
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "Hero: Astia" in out
    assert "Enemies: Hungry Cultist, Black Candle Acolyte" in out
    assert "skill_" not in out
    assert "Prompt style: control" in out
    assert "Prompt Impact:" in out
    assert "Control template" in out
    assert "Tempo Diagnostics:" in out
    assert "Hero turn spread:" in out
    assert "Tick spread:" in out


def test_cli_batch_reports_timeout_causes(content_root, isolated_home, capsys):
    rc = main(
        [
            "--lang",
            "en",
            "batch",
            "--count",
            "2",
            "--seed",
            "1",
            "--hero",
            "hero_shadow_apprentice",
            "--enemies",
            "enemy_black_candle_high_priest_archive",
            "--max-ticks",
            "20",
            "--content-dir",
            str(content_root),
            "--quiet",
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "Timeouts: 2" in out
    assert "Timeout causes:" in out
    assert "safety_limit:" in out


def test_norn_seed7_boss_batch_is_explained_and_within_budget(content_root, isolated_home, capsys):
    """REQ-BOSSUI-001: Norn seed 7 Boss run should not be an unexplained 600 tick slog."""
    rc = main(
        [
            "--lang",
            "en",
            "batch",
            "--hero",
            "hero_ash_guardian",
            "--enemies",
            "enemy_black_candle_high_priest_archive",
            "--count",
            "1",
            "--seed",
            "7",
            "--quiet",
            "--content-dir",
            str(content_root),
        ]
    )

    assert rc == 0
    out = capsys.readouterr().out
    assert "Budget: boss 8-18 hero turns" in out
    assert "Tick spread: min 138 / p50 138 / p90 138 / max 138" in out
    assert "Timeouts: 0" in out
    assert "Counter windows: 5/5 answered, 0 missed" in out
    assert "Hero: Norn" in out
    assert "Enemies: Black Candle High Priest" in out
    assert "Tower Brace: 5" in out
    assert "skill_tower_brace" not in out


def test_shop_strategy_change_is_visible_in_next_battle_trace(bundle, tmp_path):
    """REQ-PLAY-003: shop strategy repair should alter the next battle context."""
    run_state = create_run_state(
        "run_shop_trace",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    run_state.current_floor_index = 1
    run_state.current_node_index = 1
    run_state.set_shop_items(list(run_state.current_node(bundle).shop_items))
    run_state.gold = 50
    strategy_index = next(
        index
        for index, item in enumerate(run_state.current_choices)
        if item.type == "strategy"
    )
    assert run_state.buy_shop_item(strategy_index, bundle)
    assert run_state.strategy_style == "control"

    loop = BattleLoop(
        bundle,
        MockProvider(seed=7, language="en"),
        seed=7,
        max_ticks=120,
        language="en",
        battle_session_id="be_shop_trace",
        prompt_style=run_state.strategy_style,
    )
    state = loop.setup(
        run_state.hero_id,
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
        item_ids=tuple(run_state.item_ids),
        affix_ids=tuple(run_state.affix_ids),
    )

    with TraceWriter(
        run_id=run_state.run_id,
        battle_id="run_shop_trace_b001",
        seed=7,
        provider="mock",
        model="mock-smart",
        config=TraceConfig(enabled=True, directory=tmp_path),
    ) as trace:

        def on_hero(_state, record):
            trace.write(
                "hero_turn",
                tick=record.tick,
                prompt_style=record.prompt_style,
                delta_context=record.delta_context,
            )

        loop.run(state, on_hero_turn=on_hero)

    trace_text = (tmp_path / "run_shop_trace_b001.trace.jsonl").read_text(encoding="utf-8")
    assert '"prompt_style": "control"' in trace_text
    assert '"enemy_delta"' in trace_text
