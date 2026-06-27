"""REQ-BTL-001..005 deterministic combat behavior."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.content import load_content_bundle
from ouro_agent.engine import run_batch
from ouro_agent.engine.battle import BatchResult, BattleLoop, TurnRecord, generate_battle_report, run_mock_battle
from ouro_agent.engine.diagnostics import classify_tempo_budget
from ouro_agent.engine.enemy_ai import decide_enemy_action, resolve_enemy_action
from ouro_agent.engine.judge import Judge, JudgeOutcome
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


def test_hero_thinking_hook_fires_before_model_turn(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1, max_ticks=600)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    events: list[tuple[str, int, int]] = []

    def on_thinking(state):
        events.append(("thinking", state.tick, len(loop.records)))

    def on_hero(state, record):
        events.append(("hero", record.tick, len(loop.records)))

    loop.run(state, on_hero_thinking=on_thinking, on_hero_turn=on_hero)

    first_thinking = next(item for item in events if item[0] == "thinking")
    first_hero = next(item for item in events if item[0] == "hero")
    assert first_thinking[1] == first_hero[1]
    assert first_thinking[2] == first_hero[2] == 0


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


def test_silence_breaks_chant_locally(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1)
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_acolyte"])
    enemy = state.enemies[0]
    enemy.chant_progress = enemy.chant_charge_turns
    enemy.add_status(StatusEffect(id="status_silence", stacks=1, duration=1))

    action = decide_enemy_action(enemy, state, loop._rng)  # noqa: SLF001
    resolve_enemy_action(enemy, action, state)

    assert action["type"] == "silenced"
    assert enemy.chant_progress == 0
    assert state.hero.hp == state.hero.max_hp
    assert any(event.kind == "enemy_silenced" for event in state.events)


def test_tower_brace_breaks_archive_boss_charge(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1)
    state = loop.setup("hero_ash_guardian", ["enemy_black_candle_high_priest_archive"])
    boss = state.enemies[0]
    boss.chant_progress = 1
    before_hp = boss.hp

    outcome = Judge(bundle.skills).resolve(
        HeroAction(
            type="cast_skill",
            skill_id="skill_tower_brace",
            targets=("hero_ash_guardian",),
        ),
        state,
    )

    assert outcome.valid
    assert outcome.damage > 0
    assert boss.hp < before_hp
    assert boss.chant_progress == 0
    assert boss.find_status("status_silence") is not None
    assert boss.id in outcome.target_ids
    assert any(event.kind == "boss_break" for event in state.events)


def test_norn_archive_boss_resolves_inside_tempo_budget(bundle):
    state, records = run_mock_battle(
        bundle,
        MockProvider(seed=7, language="en"),
        hero_id="hero_ash_guardian",
        enemy_ids=["enemy_black_candle_high_priest_archive"],
        seed=7,
        language="en",
    )
    report = generate_battle_report(state, records)

    assert state.result == "victory"
    assert report.tempo_budget_label == "boss"
    assert report.hero_turn_count <= report.tempo_budget_max_turns
    assert report.skill_usage["skill_tower_brace"] > 0
    assert report.counter_windows_answered > 0
    assert report.counter_windows_missed == 0


def test_batch_run_produces_reproducible_results(bundle):
    result = run_batch(
        bundle,
        hero_id="hero_shadow_apprentice",
        enemy_ids=["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
        count=3,
        base_seed=1,
        language="en",
    )

    assert result.total_runs == 3
    assert result.victories >= 0
    assert result.defeats + result.victories + result.timeouts == 3
    assert 0.0 <= result.win_rate <= 1.0
    assert result.avg_hero_turns > 0
    assert result.skill_usage_counter
    assert result.total_fallbacks >= 0
    summary = "\n".join(result.summary("en"))
    assert result.build_name == "Black Candle Interrupt"
    assert result.enemy_tier_counts == {"trace": 2}
    assert result.hero_id == "hero_shadow_apprentice"
    assert result.enemy_ids == ("enemy_hungry_cultist", "enemy_black_candle_acolyte")
    assert "Hero: Astia" in summary
    assert "Enemies: Hungry Cultist, Black Candle Acolyte" in summary
    assert "Build: Black Candle Interrupt" in summary
    assert "Enemy tiers: trace=2" in summary
    assert "Group key: hero=Astia | build=Black Candle Interrupt" in summary
    assert "Skill Usage Detail:" in summary
    assert "Shadow Sting:" in summary
    assert "Hex Seal:" in summary
    assert "Corrupted Focus:" in summary
    assert "hero_shadow_apprentice" not in summary
    assert "enemy_hungry_cultist" not in summary
    assert "hero_" not in summary
    assert "enemy_" not in summary
    assert "skill_" not in summary
    assert "Tempo Diagnostics:" in summary
    assert "BALANCE TUNING BOARD" in summary
    assert "[WIN]" in summary
    assert "[TEMPO] outliers" in summary
    assert "[ACTION] skill" in summary
    assert "[RESOURCE] MP dry" in summary
    assert "[TUNE]" in summary
    assert "BATCH SAMPLE HEATMAP" in summary
    assert "[KEY] V victory" in summary
    assert "[RESULT]" in summary
    assert "hero turns / budget" in summary
    assert "[ALERT]" in summary
    assert "[READ]" in summary
    assert "Tempo outliers:" in summary
    assert "Hero turn spread:" in summary
    assert "Tick spread:" in summary
    assert "MP dry turns:" in summary
    assert "Low-impact turns:" in summary
    assert "Max defense loop:" in summary
    assert "Counter windows:" in summary
    assert len(summary) > 0

    for report in result.reports:
        assert report.result in {"victory", "defeat", "timeout"}
        assert report.hero_turn_count >= 0
        assert report.skill_usage is not None
        assert report.tempo_budget_label in {"normal", "elite", "boss"}
        assert report.mp_dry_turns >= 0
        assert report.low_impact_turns >= 0
        assert report.max_defense_loop >= 0
        assert report.counter_windows_opened >= report.counter_windows_answered


def test_batch_report_includes_length_distribution_and_timeout_causes(bundle):
    """REQ-BAL-002: batch balance output should explain long and timeout fights."""
    long_result = run_batch(
        bundle,
        hero_id="hero_shadow_apprentice",
        enemy_ids=["enemy_black_candle_high_priest_archive"],
        count=2,
        base_seed=1,
        language="en",
    )
    long_summary = "\n".join(long_result.summary("en"))

    assert long_result.long_fight_reason_counter
    assert "Hero turn spread:" in long_summary
    assert "Tick spread:" in long_summary
    assert "Long fight causes:" in long_summary

    timeout_result = run_batch(
        bundle,
        hero_id="hero_shadow_apprentice",
        enemy_ids=["enemy_black_candle_high_priest_archive"],
        count=2,
        base_seed=1,
        max_ticks=20,
        language="en",
    )
    timeout_summary = "\n".join(timeout_result.summary("en"))

    assert timeout_result.timeouts == 2
    assert timeout_result.timeout_reason_counter
    assert "Timeout causes:" in timeout_summary
    assert "safety_limit:" in timeout_summary


def test_batch_tempo_metrics_distinguish_resource_loop_and_boss_break(bundle):
    """REQ-BAL-003: budget labels and metric keys should separate tuning causes."""
    normal_state = BattleLoop(bundle, MockProvider(seed=0), seed=1).setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist"],
    )
    elite_state = BattleLoop(bundle, MockProvider(seed=0), seed=1).setup(
        "hero_shadow_apprentice",
        ["enemy_black_candle_priest_rite"],
    )
    boss_state = BattleLoop(bundle, MockProvider(seed=0), seed=1).setup(
        "hero_ash_guardian",
        ["enemy_black_candle_high_priest_archive"],
    )

    assert classify_tempo_budget(normal_state).describe() == "normal 3-8 hero turns"
    assert classify_tempo_budget(elite_state).describe() == "elite 5-12 hero turns"
    assert classify_tempo_budget(boss_state).describe() == "boss 8-18 hero turns"

    normal_state.tick = 90
    normal_state.result = "victory"
    normal_state.enemies[0].hp = 0
    mp_records = [
        TurnRecord(
            tick=10 + index,
            actor_id="hero_shadow_apprentice",
            side="hero",
            raw_text=None,
            validation=None,
            action=HeroAction(
                type="cast_skill",
                skill_id="skill_shadow_sting",
                targets=("enemy_hungry_cultist",),
            ),
            judge=JudgeOutcome(
                valid=False,
                reason="insufficient MP",
                summary="insufficient MP for skill_shadow_sting",
                damage=0,
                target_ids=("enemy_hungry_cultist",),
                skill_id="skill_shadow_sting",
                action_kind="cast_skill",
            ),
        )
        for index in range(9)
    ]
    mp_report = generate_battle_report(normal_state, mp_records)

    defense_state = BattleLoop(bundle, MockProvider(seed=0), seed=1).setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist"],
    )
    defense_state.tick = 90
    defense_state.result = "victory"
    defense_state.enemies[0].hp = 0
    defense_records = [
        TurnRecord(
            tick=30 + index,
            actor_id="hero_shadow_apprentice",
            side="hero",
            raw_text=None,
            validation=None,
            action=HeroAction(type="defend"),
            judge=JudgeOutcome(
                valid=True,
                reason="defend resolved",
                summary="defend -> guard",
                damage=0,
                action_kind="defend",
            ),
        )
        for index in range(9)
    ]
    defense_report = generate_battle_report(defense_state, defense_records)

    boss_state.tick = 220
    boss_state.result = "victory"
    boss_state.enemies[0].hp = 0
    boss_records = [
        TurnRecord(
            tick=12,
            actor_id="enemy_black_candle_high_priest_archive",
            side="enemy",
            raw_text=None,
            validation=None,
            action=None,
            judge=None,
            enemy_action={"type": "chant_charge"},
        ),
        TurnRecord(
            tick=13,
            actor_id="hero_ash_guardian",
            side="hero",
            raw_text=None,
            validation=None,
            action=HeroAction(
                type="basic_attack",
                targets=("enemy_black_candle_high_priest_archive",),
            ),
            judge=JudgeOutcome(
                valid=True,
                reason="basic attack landed",
                summary="basic_attack -> enemy_black_candle_high_priest_archive | 7 dmg",
                damage=7,
                target_ids=("enemy_black_candle_high_priest_archive",),
                action_kind="basic_attack",
            ),
        ),
        TurnRecord(
            tick=14,
            actor_id="enemy_black_candle_high_priest_archive",
            side="enemy",
            raw_text=None,
            validation=None,
            action=None,
            judge=None,
            enemy_action={"type": "chant_release"},
        ),
    ]
    boss_records.extend(
        TurnRecord(
            tick=20 + index,
            actor_id="hero_ash_guardian",
            side="hero",
            raw_text=None,
            validation=None,
            action=HeroAction(
                type="basic_attack",
                targets=("enemy_black_candle_high_priest_archive",),
            ),
            judge=JudgeOutcome(
                valid=True,
                reason="basic attack landed",
                summary="basic_attack -> enemy_black_candle_high_priest_archive | 7 dmg",
                damage=7,
                target_ids=("enemy_black_candle_high_priest_archive",),
                action_kind="basic_attack",
            ),
        )
        for index in range(18)
    )
    boss_report = generate_battle_report(boss_state, boss_records)

    assert mp_report.tempo_outlier_reason == "mp_drought"
    assert mp_report.mp_dry_turns == 9
    assert defense_report.tempo_outlier_reason == "defense_loop"
    assert defense_report.defense_loop_turns == 9
    assert boss_report.tempo_outlier_reason == "boss_break_missed"
    assert boss_report.boss_break_missed == 1

    batch = BatchResult(
        hero_id="mixed",
        enemy_ids=("synthetic",),
        reports=[mp_report, defense_report, boss_report],
    )
    summary = "\n".join(batch.summary("en"))

    assert "Metric keys:" in summary
    assert "tempo_outlier=3" in summary
    assert "mp_dry_turns=9" in summary
    assert "defense_loop_turns=9" in summary
    assert "boss_break_missed=1" in summary
    assert "mp_drought: 1" in summary
    assert "defense_loop: 1" in summary
    assert "boss_break_missed: 1" in summary


def test_battle_report_flags_low_output_tempo_outlier(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=0), seed=1)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.tick = 90
    state.result = "victory"
    state.enemies[0].hp = 0
    records = [
        TurnRecord(
            tick=10 + index,
            actor_id="hero_shadow_apprentice",
            side="hero",
            raw_text=None,
            validation=None,
            action=HeroAction(
                type="basic_attack",
                targets=("enemy_hungry_cultist",),
            ),
            judge=JudgeOutcome(
                valid=True,
                reason="basic attack landed",
                summary="basic_attack -> enemy_hungry_cultist | 1 dmg",
                damage=1,
                target_ids=("enemy_hungry_cultist",),
                action_kind="basic_attack",
            ),
        )
        for index in range(9)
    ]

    report = generate_battle_report(state, records)
    summary = "\n".join(report.summary("en"))

    assert report.tempo_budget_label == "normal"
    assert report.tempo_outlier_reason == "low_output"
    assert report.low_impact_turns == 9
    assert "Tempo Diagnostics:" in summary
    assert "Outlier reason: low_output" in summary


def test_battle_report_includes_trace_based_failure_review(bundle):
    """REQ-PLAY-004: defeat reports should explain resource/target/build/route lessons."""
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
                    {
                        "id": cultist.id,
                        "hp": 12,
                        "atb": 20,
                        "tier": cultist.tier,
                        "chant_progress": 0,
                    },
                    {
                        "id": acolyte.id,
                        "hp": 78,
                        "atb": 96,
                        "tier": acolyte.tier,
                        "chant_progress": 1,
                    },
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

    report = generate_battle_report(state, records)
    summary = "\n".join(report.summary("en"))

    assert report.targeting_drift_turns == 1
    assert report.counter_windows_missed == 1
    assert report.failure_reasons
    assert report.next_run_advice
    assert "Targeting drift turns: 1" in summary
    assert "Failure Review:" in summary
    assert "Targeting:" in summary
    assert "Next run advice:" in summary


def test_battle_report_includes_prompt_impact_for_style(bundle):
    """REQ-PLAY-005: prompt template impact should be visible in reports."""
    state, records = run_mock_battle(
        bundle,
        MockProvider(seed=7, language="en"),
        hero_id="hero_shadow_apprentice",
        enemy_ids=["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
        seed=7,
        language="en",
        prompt_style="control",
    )

    report = generate_battle_report(state, records)
    summary = "\n".join(report.summary("en"))

    assert report.prompt_style == "control"
    assert report.prompt_impacts
    assert "Prompt Impact:" in summary
    assert "Control template" in summary
    assert "Hex Seal" in summary
    assert "\n  skill_hex_seal:" not in summary


def test_batch_run_is_reproducible_with_same_seed(bundle):
    result_a = run_batch(
        bundle,
        hero_id="hero_shadow_apprentice",
        enemy_ids=["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
        count=5,
        base_seed=42,
        language="en",
    )

    result_b = run_batch(
        bundle,
        hero_id="hero_shadow_apprentice",
        enemy_ids=["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
        count=5,
        base_seed=42,
        language="en",
    )

    assert result_a.total_runs == result_b.total_runs
    assert result_a.victories == result_b.victories
    assert result_a.defeats == result_b.defeats
    assert [r.result for r in result_a.reports] == [r.result for r in result_b.reports]
