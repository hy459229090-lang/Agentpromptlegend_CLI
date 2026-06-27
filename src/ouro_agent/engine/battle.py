"""ATB battle loop.

Deterministic for a given seed and content. Hero turns delegate to a Provider
and validator; enemy turns use the rule AI in ``enemy_ai``. The loop never
calls a Provider directly without going through the validator, so a malformed
or absent action degrades to defend/basic_attack instead of crashing.
"""
from __future__ import annotations

import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Iterable

from ouro_agent.content.schema import (
    EnemyData,
    HeroData,
    SkillData,
    ContentBundle,
)
from ouro_agent.engine.build import ResolvedBuild, resolve_build
from ouro_agent.engine.diagnostics import (
    analyze_battle_tactics,
    analyze_prompt_impacts,
    classify_tempo_budget,
    classify_tempo_outlier,
)
from ouro_agent.engine.enemy_ai import decide_enemy_action, resolve_enemy_action
from ouro_agent.engine.judge import Judge, JudgeOutcome
from ouro_agent.engine.models import (
    BattleResult,
    BattleState,
    Enemy,
    Hero,
    SkillState,
    StatusEffect,
    Unit,
)
from ouro_agent.i18n import DEFAULT_LANGUAGE
from ouro_agent.llm.actions import HeroAction, FallbackReason
from ouro_agent.llm.validator import ValidationResult, parse_model_output
from ouro_agent.providers.base import ModelTurnResult, Provider
from ouro_agent.sessions import BattleLLMSession
from ouro_agent.sessions.codex import CodexProgress

ATB_THRESHOLD = 100
DEFAULT_MAX_TICKS = 600


@dataclass
class BattleReport:
    result: str
    total_ticks: int
    hero_turn_count: int
    enemy_turn_count: int

    basic_attack_count: int
    skill_cast_count: int
    defend_count: int
    observe_count: int
    stance_count: int

    hero_damage_dealt: int
    enemy_damage_dealt: int

    skill_usage: dict[str, int]
    fallback_count: int
    invalid_action_count: int

    killed_by: str | None
    last_enemy_attacker: str | None

    hero_hp_remaining: int
    hero_mp_remaining: int
    enemies_remaining: int
    tempo_budget_label: str
    tempo_budget_min_turns: int
    tempo_budget_max_turns: int
    tempo_outlier_reason: str | None
    mp_dry_turns: int
    low_impact_turns: int
    max_defense_loop: int
    targeting_drift_turns: int
    counter_windows_opened: int
    counter_windows_answered: int
    counter_windows_missed: int
    failure_reasons: tuple[str, ...] = ()
    next_run_advice: tuple[str, ...] = ()
    prompt_style: str | None = None
    prompt_impacts: tuple[str, ...] = ()
    skill_display_names: dict[str, str] = field(default_factory=dict)

    @property
    def total_hero_actions(self) -> int:
        return (
            self.basic_attack_count
            + self.skill_cast_count
            + self.defend_count
            + self.observe_count
            + self.stance_count
        )

    @property
    def skill_usage_ratio(self) -> float:
        if self.total_hero_actions == 0:
            return 0.0
        return self.skill_cast_count / self.total_hero_actions

    @property
    def basic_attack_ratio(self) -> float:
        if self.total_hero_actions == 0:
            return 0.0
        return self.basic_attack_count / self.total_hero_actions

    @property
    def tempo_outlier(self) -> bool:
        return self.tempo_outlier_reason is not None

    @property
    def defense_loop_turns(self) -> int:
        return self.max_defense_loop

    @property
    def boss_break_missed(self) -> int:
        if self.tempo_budget_label != "boss":
            return 0
        return self.counter_windows_missed

    def summary(self, language: str = "en") -> list[str]:
        lines: list[str] = []

        header = {
            "en": f"=== BATTLE REPORT :: {self.result.upper()} ===",
            "zh": f"=== 战斗报告 :: {_result_display(self.result, 'zh').upper()} ===",
        }.get(language, f"=== BATTLE REPORT :: {self.result.upper()} ===")
        lines.append(header)
        lines.append("")

        stats_label = {
            "en": "Battle Stats",
            "zh": "战斗统计",
        }.get(language, "Battle Stats")
        lines.append(f"{stats_label}:")
        ticks_label = {
            "en": f"  Total ticks: {self.total_ticks}",
            "zh": f"  总刻度数: {self.total_ticks}",
        }.get(language, f"  Total ticks: {self.total_ticks}")
        lines.append(ticks_label)

        hero_turns_label = {
            "en": f"  Hero turns: {self.hero_turn_count}",
            "zh": f"  英雄回合: {self.hero_turn_count}",
        }.get(language, f"  Hero turns: {self.hero_turn_count}")
        lines.append(hero_turns_label)

        enemy_turns_label = {
            "en": f"  Enemy turns: {self.enemy_turn_count}",
            "zh": f"  敌人回合: {self.enemy_turn_count}",
        }.get(language, f"  Enemy turns: {self.enemy_turn_count}")
        lines.append(enemy_turns_label)
        lines.append("")

        actions_label = {
            "en": "Hero Action Breakdown",
            "zh": "英雄行动分布",
        }.get(language, "Hero Action Breakdown")
        lines.append(f"{actions_label}:")
        basic_label = {
            "en": f"  Basic Attack: {self.basic_attack_count} ({self.basic_attack_ratio:.0%})",
            "zh": f"  普通攻击: {self.basic_attack_count} ({self.basic_attack_ratio:.0%})",
        }.get(language, f"  Basic Attack: {self.basic_attack_count} ({self.basic_attack_ratio:.0%})")
        lines.append(basic_label)

        skill_label = {
            "en": f"  Skill Cast: {self.skill_cast_count} ({self.skill_usage_ratio:.0%})",
            "zh": f"  技能释放: {self.skill_cast_count} ({self.skill_usage_ratio:.0%})",
        }.get(language, f"  Skill Cast: {self.skill_cast_count} ({self.skill_usage_ratio:.0%})")
        lines.append(skill_label)

        defend_label = {
            "en": f"  Defend: {self.defend_count}",
            "zh": f"  防御: {self.defend_count}",
        }.get(language, f"  Defend: {self.defend_count}")
        lines.append(defend_label)

        if self.skill_usage:
            lines.append("")
            skill_detail_label = {
                "en": "Skill Usage Detail",
                "zh": "技能使用详情",
            }.get(language, "Skill Usage Detail")
            lines.append(f"{skill_detail_label}:")
            for skill_id, count in self.skill_usage.items():
                lines.append(f"  {self._skill_display_name(skill_id)}: {count}")

        lines.append("")
        damage_label = {
            "en": "Damage Summary",
            "zh": "伤害统计",
        }.get(language, "Damage Summary")
        lines.append(f"{damage_label}:")
        hero_dealt_label = {
            "en": f"  Hero dealt: {self.hero_damage_dealt}",
            "zh": f"  英雄输出: {self.hero_damage_dealt}",
        }.get(language, f"  Hero dealt: {self.hero_damage_dealt}")
        lines.append(hero_dealt_label)

        enemy_dealt_label = {
            "en": f"  Enemy dealt: {self.enemy_damage_dealt}",
            "zh": f"  敌人输出: {self.enemy_damage_dealt}",
        }.get(language, f"  Enemy dealt: {self.enemy_damage_dealt}")
        lines.append(enemy_dealt_label)

        if self.prompt_style or self.prompt_impacts:
            lines.append("")
            prompt_label = {
                "en": "Prompt Impact",
                "zh": "Prompt 影响",
            }.get(language, "Prompt Impact")
            lines.append(f"{prompt_label}:")
            if self.prompt_style:
                style_label = {
                    "en": f"  Style: {self.prompt_style}",
                    "zh": f"  预设: {self.prompt_style}",
                }.get(language, f"  Style: {self.prompt_style}")
                lines.append(style_label)
            for impact in self.prompt_impacts:
                lines.append(f"  {impact}")

        lines.append("")
        tempo_label = {
            "en": "Tempo Diagnostics",
            "zh": "节奏诊断",
        }.get(language, "Tempo Diagnostics")
        lines.append(f"{tempo_label}:")
        budget_label = {
            "en": (
                f"  Budget: {self.tempo_budget_label} "
                f"{self.tempo_budget_min_turns}-{self.tempo_budget_max_turns} hero turns"
            ),
            "zh": (
                f"  预算: {self.tempo_budget_label} "
                f"{self.tempo_budget_min_turns}-{self.tempo_budget_max_turns} 英雄回合"
            ),
        }.get(
            language,
            f"  Budget: {self.tempo_budget_label} "
            f"{self.tempo_budget_min_turns}-{self.tempo_budget_max_turns} hero turns",
        )
        lines.append(budget_label)
        outlier_label = {
            "en": f"  Outlier reason: {self.tempo_outlier_reason or 'none'}",
            "zh": f"  异常原因: {self.tempo_outlier_reason or 'none'}",
        }.get(language, f"  Outlier reason: {self.tempo_outlier_reason or 'none'}")
        lines.append(outlier_label)
        lines.append(
            {
                "en": f"  MP dry / low-impact: {self.mp_dry_turns} / {self.low_impact_turns}",
                "zh": f"  MP 枯竭 / 低收益: {self.mp_dry_turns} / {self.low_impact_turns}",
            }.get(language, f"  MP dry / low-impact: {self.mp_dry_turns} / {self.low_impact_turns}")
        )
        lines.append(
            {
                "en": f"  Targeting drift turns: {self.targeting_drift_turns}",
                "zh": f"  目标偏移回合: {self.targeting_drift_turns}",
            }.get(language, f"  Targeting drift turns: {self.targeting_drift_turns}")
        )
        lines.append(
            {
                "en": (
                    "  Counter windows: "
                    f"{self.counter_windows_answered}/{self.counter_windows_opened} answered, "
                    f"{self.counter_windows_missed} missed"
                ),
                "zh": (
                    "  反制窗口: "
                    f"{self.counter_windows_answered}/{self.counter_windows_opened} 已回应, "
                    f"{self.counter_windows_missed} 次错失"
                ),
            }.get(
                language,
                "  Counter windows: "
                f"{self.counter_windows_answered}/{self.counter_windows_opened} answered, "
                f"{self.counter_windows_missed} missed",
            )
        )

        if self.fallback_count > 0 or self.invalid_action_count > 0:
            lines.append("")
            issues_label = {
                "en": "Action Issues",
                "zh": "行动问题",
            }.get(language, "Action Issues")
            lines.append(f"{issues_label}:")
            if self.fallback_count > 0:
                fallback_label = {
                    "en": f"  Fallback actions: {self.fallback_count}",
                    "zh": f"  回退行动: {self.fallback_count}",
                }.get(language, f"  Fallback actions: {self.fallback_count}")
                lines.append(fallback_label)
            if self.invalid_action_count > 0:
                invalid_label = {
                    "en": f"  Invalid actions: {self.invalid_action_count}",
                    "zh": f"  无效行动: {self.invalid_action_count}",
                }.get(language, f"  Invalid actions: {self.invalid_action_count}")
                lines.append(invalid_label)

        if self.result == "defeat" and self.killed_by:
            lines.append("")
            defeat_label = {
                "en": "Defeat Analysis",
                "zh": "战败分析",
            }.get(language, "Defeat Analysis")
            lines.append(f"{defeat_label}:")
            killed_label = {
                "en": f"  Killed by: {self.killed_by}",
                "zh": f"  击败者: {self.killed_by}",
            }.get(language, f"  Killed by: {self.killed_by}")
            lines.append(killed_label)
            if self.last_enemy_attacker:
                last_attacker_label = {
                    "en": f"  Last attacker: {self.last_enemy_attacker}",
                    "zh": f"  最后攻击者: {self.last_enemy_attacker}",
                }.get(language, f"  Last attacker: {self.last_enemy_attacker}")
                lines.append(last_attacker_label)

        if self.result in {"defeat", "timeout"} and (
            self.failure_reasons or self.next_run_advice
        ):
            lines.append("")
            review_label = {
                "en": "Failure Review",
                "zh": "失败复盘",
            }.get(language, "Failure Review")
            lines.append(f"{review_label}:")
            if self.failure_reasons:
                reason_label = {
                    "en": "  Failure reasons:",
                    "zh": "  失败原因:",
                }.get(language, "  Failure reasons:")
                lines.append(reason_label)
                for index, reason in enumerate(self.failure_reasons, start=1):
                    lines.append(f"    {index}. {reason}")
            if self.next_run_advice:
                advice_label = {
                    "en": "  Next run advice:",
                    "zh": "  下一局建议:",
                }.get(language, "  Next run advice:")
                lines.append(advice_label)
                for index, advice in enumerate(self.next_run_advice, start=1):
                    lines.append(f"    {index}. {advice}")

        lines.append("")
        final_label = {
            "en": "Final State",
            "zh": "最终状态",
        }.get(language, "Final State")
        lines.append(f"{final_label}:")
        hp_label = {
            "en": f"  Hero HP: {self.hero_hp_remaining}",
            "zh": f"  英雄HP: {self.hero_hp_remaining}",
        }.get(language, f"  Hero HP: {self.hero_hp_remaining}")
        lines.append(hp_label)

        mp_label = {
            "en": f"  Hero MP: {self.hero_mp_remaining}",
            "zh": f"  英雄MP: {self.hero_mp_remaining}",
        }.get(language, f"  Hero MP: {self.hero_mp_remaining}")
        lines.append(mp_label)

        enemies_label = {
            "en": f"  Enemies alive: {self.enemies_remaining}",
            "zh": f"  存活敌人: {self.enemies_remaining}",
        }.get(language, f"  Enemies alive: {self.enemies_remaining}")
        lines.append(enemies_label)

        return lines

    def _skill_display_name(self, skill_id: str) -> str:
        return self.skill_display_names.get(skill_id, skill_id)


def _result_display(result: str, lang: str) -> str:
    mapping = {
        "en": {
            "victory": "Victory",
            "defeat": "Defeat",
            "timeout": "Timeout",
            "ongoing": "Ongoing",
        },
        "zh": {
            "victory": "胜利",
            "defeat": "战败",
            "timeout": "超时",
            "ongoing": "进行中",
        },
    }
    return mapping.get(lang, mapping["en"]).get(result, result)


def generate_battle_report(
    state: BattleState,
    records: list[TurnRecord],
) -> BattleReport:
    hero_turn_count = sum(1 for r in records if r.side == "hero")
    enemy_turn_count = sum(1 for r in records if r.side == "enemy")

    basic_attack_count = 0
    skill_cast_count = 0
    defend_count = 0
    observe_count = 0
    stance_count = 0
    skill_usage: dict[str, int] = {}
    skill_display_names = {skill.id: skill.display_name for skill in state.hero.skills}
    hero_damage_dealt = 0
    enemy_damage_dealt = 0
    fallback_count = 0
    invalid_action_count = 0
    last_enemy_attacker: str | None = None
    killed_by: str | None = None

    for record in records:
        if record.side == "hero":
            action_kind = None
            if record.judge and record.judge.action_kind:
                action_kind = record.judge.action_kind
            elif record.action:
                action_kind = record.action.type

            if action_kind == "basic_attack":
                basic_attack_count += 1
            elif action_kind == "cast_skill":
                skill_cast_count += 1
                if record.judge and record.judge.skill_id:
                    skill_usage[record.judge.skill_id] = skill_usage.get(record.judge.skill_id, 0) + 1
            elif action_kind == "defend":
                defend_count += 1
            elif action_kind == "observe":
                observe_count += 1
            elif action_kind == "change_stance":
                stance_count += 1

            if record.judge and record.judge.damage:
                hero_damage_dealt += record.judge.damage

            if record.validation:
                if record.validation.fallback_reason.value != "none":
                    fallback_count += 1
                    invalid_action_count += 1

        else:
            if record.enemy_action:
                last_enemy_attacker = record.actor_id
                dmg = record.enemy_action.get("damage", 0)
                if isinstance(dmg, int) and dmg > 0:
                    enemy_damage_dealt += dmg

    if state.result == "defeat":
        killed_by = last_enemy_attacker

    diagnosis = analyze_battle_tactics(state, records, language=state.language)
    prompt_style = next(
        (record.prompt_style for record in records if record.prompt_style),
        None,
    )
    enemy_display_names = {enemy.id: enemy.name for enemy in state.enemies}
    prompt_impacts = _display_prompt_impacts(
        analyze_prompt_impacts(records, language=state.language),
        skill_display_names=skill_display_names,
        enemy_display_names=enemy_display_names,
        hero_id=state.hero.id,
        hero_name=state.hero.name,
    )
    tempo_budget = classify_tempo_budget(state)
    tempo_outlier_reason = classify_tempo_outlier(
        state,
        diagnosis,
        hero_turn_count=hero_turn_count,
    )

    return BattleReport(
        result=state.result,
        total_ticks=state.tick,
        hero_turn_count=hero_turn_count,
        enemy_turn_count=enemy_turn_count,
        basic_attack_count=basic_attack_count,
        skill_cast_count=skill_cast_count,
        defend_count=defend_count,
        observe_count=observe_count,
        stance_count=stance_count,
        hero_damage_dealt=hero_damage_dealt,
        enemy_damage_dealt=enemy_damage_dealt,
        skill_usage=skill_usage,
        fallback_count=fallback_count,
        invalid_action_count=invalid_action_count,
        killed_by=killed_by,
        last_enemy_attacker=last_enemy_attacker,
        hero_hp_remaining=state.hero.hp,
        hero_mp_remaining=state.hero.mp,
        enemies_remaining=len(state.alive_enemies()),
        tempo_budget_label=tempo_budget.label,
        tempo_budget_min_turns=tempo_budget.min_hero_turns,
        tempo_budget_max_turns=tempo_budget.max_hero_turns,
        tempo_outlier_reason=tempo_outlier_reason,
        mp_dry_turns=diagnosis.mp_dry_turns,
        low_impact_turns=diagnosis.low_impact_turns,
        max_defense_loop=diagnosis.max_defense_loop,
        targeting_drift_turns=diagnosis.targeting_drift_turns,
        counter_windows_opened=diagnosis.counter_windows_opened,
        counter_windows_answered=diagnosis.counter_windows_answered,
        counter_windows_missed=diagnosis.counter_windows_missed,
        failure_reasons=diagnosis.failure_reasons,
        next_run_advice=diagnosis.next_run_advice,
        prompt_style=prompt_style,
        prompt_impacts=prompt_impacts,
        skill_display_names=skill_display_names,
    )


def _display_prompt_impacts(
    impacts: tuple[str, ...],
    *,
    skill_display_names: dict[str, str],
    enemy_display_names: dict[str, str],
    hero_id: str,
    hero_name: str,
) -> tuple[str, ...]:
    display_names = {
        **skill_display_names,
        **enemy_display_names,
        hero_id: hero_name,
    }
    return tuple(_replace_display_ids(impact, display_names) for impact in impacts)


def _replace_display_ids(text: str, display_names: dict[str, str]) -> str:
    result = text
    for stable_id, display_name in sorted(
        display_names.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        result = result.replace(stable_id, display_name)
    return result


@dataclass
class TurnRecord:
    tick: int
    actor_id: str
    side: str
    raw_text: str | None
    validation: ValidationResult | None
    action: HeroAction | None
    judge: JudgeOutcome | None
    usage_total_tokens: int = 0
    usage_latency_ms: int = 0
    enemy_action: dict | None = None
    battle_session_id: str | None = None
    static_context_hash: str | None = None
    delta_context_id: str | None = None
    delta_context: dict | None = None
    prompt_style: str | None = None


HeroTurnHook = Callable[[BattleState, "TurnRecord"], None]
EnemyTurnHook = Callable[[BattleState, "TurnRecord"], None]
HeroThinkingHook = Callable[[BattleState], None]


class BattleLoop:
    def __init__(
        self,
        bundle: ContentBundle,
        provider: Provider,
        seed: int = 0,
        max_ticks: int = DEFAULT_MAX_TICKS,
        language: str = DEFAULT_LANGUAGE,
        battle_session_id: str | None = None,
        hero_prompt_override: str | None = None,
        prompt_style: str | None = None,
        codex_progress: "CodexProgress | None" = None,
    ):
        self.bundle = bundle
        self.provider = provider
        self.seed = seed
        self.max_ticks = max_ticks
        self.language = language
        self.battle_session_id = battle_session_id or f"be_seed_{seed:04d}"
        self.battle_llm_session: BattleLLMSession | None = None
        self.hero_prompt_override = hero_prompt_override
        self.prompt_style = prompt_style
        self.codex_progress = codex_progress
        self._rng = random.Random(seed)
        self.judge = Judge(bundle.skills)
        self.records: list[TurnRecord] = []

    def setup(
        self,
        hero_id: str,
        enemy_ids: Iterable[str],
        *,
        item_ids: tuple[str, ...] | None = None,
        affix_ids: tuple[str, ...] | None = None,
    ) -> BattleState:
        hero_data: HeroData = self.bundle.get_hero(hero_id)
        build = resolve_build(
            hero_data,
            self.bundle,
            item_ids=item_ids,
            affix_ids=affix_ids,
        )
        hero = _hero_from_data(hero_data, self.bundle.skills, self.language, build=build)
        for status in build.battle_start_statuses:
            hero.add_status(
                StatusEffect(id=status.id, stacks=status.stacks, duration=status.duration)
            )
        enemies = [
            _enemy_from_data(self.bundle.get_enemy(eid), self.language)
            for eid in enemy_ids
        ]
        state = BattleState(
            seed=self.seed,
            tick=0,
            hero=hero,
            enemies=enemies,
            language=self.language,
        )
        for resonance in build.resonances:
            state.emit(
                "resonance_active",
                resonance_id=resonance.id,
                tags=list(build.tags),
            )
        from ouro_agent.llm.prompt import compose_static_context

        self.battle_llm_session = BattleLLMSession.start(
            self.battle_session_id,
            compose_static_context(
                state,
                self.bundle,
                self.hero_prompt_override,
                self.codex_progress,
                prompt_style=self.prompt_style,
                build=build,
            ),
        )
        return state

    def run(
        self,
        state: BattleState,
        on_hero_turn: HeroTurnHook | None = None,
        on_enemy_turn: EnemyTurnHook | None = None,
        on_hero_thinking: HeroThinkingHook | None = None,
    ) -> BattleResult:
        while state.result == "ongoing" and state.tick < self.max_ticks:
            state.tick += 1
            self._advance_atb(state)
            actor = self._select_next_actor(state)
            if actor is None:
                continue

            self._tick_statuses(actor, state)
            if not actor.is_alive:
                actor.atb = 0
                self._check_end(state)
                continue

            if actor.side == "hero":
                if on_hero_thinking:
                    on_hero_thinking(state)
                record = self._take_hero_turn(state)
                if on_hero_turn:
                    on_hero_turn(state, record)
                state.hero.tick_cooldowns()
            else:
                record = self._take_enemy_turn(actor, state)
                if on_enemy_turn:
                    on_enemy_turn(state, record)
            self.records.append(record)

            actor.atb = max(0, actor.atb - ATB_THRESHOLD)
            self._check_end(state)

        if state.result == "ongoing":
            state.result = "timeout"
        return state.result

    def _advance_atb(self, state: BattleState) -> None:
        for unit in state.all_units():
            if unit.is_alive:
                unit.atb += unit.speed

    def _select_next_actor(self, state: BattleState) -> Unit | None:
        ready = [u for u in state.all_units() if u.is_alive and u.atb >= ATB_THRESHOLD]
        if not ready:
            return None
        ready.sort(key=lambda u: (-u.atb, 0 if u.side == "hero" else 1))
        return ready[0]

    def _tick_statuses(self, actor: Unit, state: BattleState) -> None:
        for status in list(actor.statuses):
            if status.id == "status_poison":
                damage = status.stacks
                actor.hp = max(0, actor.hp - damage)
                state.push_log("poison.tick", name=actor.name, dmg=damage)
                state.emit("poison_tick", target_id=actor.id, damage=damage)
            if status.id == "status_bleed":
                damage = status.stacks
                actor.hp = max(0, actor.hp - damage)
                state.push_log("bleed.tick", name=actor.name, dmg=damage)
                state.emit("bleed_tick", target_id=actor.id, damage=damage)
            if status.tick():
                actor.statuses.remove(status)

    def _take_hero_turn(self, state: BattleState) -> TurnRecord:
        from ouro_agent.llm.prompt import compose_prompt

        prompt = compose_prompt(
            state,
            self.bundle,
            hero_prompt_override=self.hero_prompt_override,
            battle_session=self.battle_llm_session,
            prompt_style=self.prompt_style,
        )
        try:
            turn_result: ModelTurnResult = self.provider.request_turn(prompt)
        except Exception as err:  # pragma: no cover - defensive fallback path
            turn_result = ModelTurnResult(
                provider=self.provider.name,
                model=getattr(self.provider, "model", "unknown"),
                raw_text="",
                error=str(err),
            )

        validation = parse_model_output(turn_result.raw_text, self.bundle, state)
        action = validation.action

        outcome = self.judge.resolve(action, state)
        if not outcome.valid and outcome.fallback_to is not None:
            fallback = HeroAction(type=outcome.fallback_to, targets=action.targets)
            outcome = self.judge.resolve(fallback, state)
            action = fallback

        record = TurnRecord(
            tick=state.tick,
            actor_id=state.hero.id,
            side="hero",
            raw_text=turn_result.raw_text,
            validation=validation,
            action=action,
            judge=outcome,
            usage_total_tokens=turn_result.usage.total_tokens,
            usage_latency_ms=turn_result.usage.latency_ms,
            battle_session_id=prompt.battle_session_id,
            static_context_hash=prompt.static_context_hash,
            delta_context_id=prompt.delta_context_id,
            delta_context=prompt.delta_context,
            prompt_style=prompt.snapshot.get("prompt_style"),
        )
        return record

    def _take_enemy_turn(self, actor: Enemy, state: BattleState) -> TurnRecord:
        action = decide_enemy_action(actor, state, self._rng)
        resolve_enemy_action(actor, action, state)
        return TurnRecord(
            tick=state.tick,
            actor_id=actor.id,
            side="enemy",
            raw_text=None,
            validation=None,
            action=None,
            judge=None,
            enemy_action=action,
            battle_session_id=(
                self.battle_llm_session.battle_session_id
                if self.battle_llm_session
                else self.battle_session_id
            ),
            static_context_hash=(
                self.battle_llm_session.static_context_hash
                if self.battle_llm_session
                else None
            ),
        )

    def _check_end(self, state: BattleState) -> None:
        if not state.hero.is_alive:
            state.result = "defeat"
            state.emit("battle_end", result="defeat", tick=state.tick)
            state.push_log("hero.fall", hero=state.hero.name)
            return
        if not state.alive_enemies():
            state.result = "victory"
            state.emit("battle_end", result="victory", tick=state.tick)
            state.push_log("hero.routed")


def _hero_from_data(
    data: HeroData,
    skills: dict[str, SkillData],
    language: str = DEFAULT_LANGUAGE,
    *,
    build: ResolvedBuild | None = None,
) -> Hero:
    skill_states = [
        SkillState(
            id=sid,
            display_name=skills[sid].display_name.get(language),
            mp_cost=skills[sid].mp_cost,
            cooldown=skills[sid].cooldown,
            target_rule=skills[sid].target_rule,
        )
        for sid in data.skills
    ]
    if build is not None:
        max_hp = build.hp
        max_mp = build.mp
        attack = build.attack
        defense = build.defense
        power = build.power
        speed = build.speed
    else:
        max_hp = data.base_stats.hp
        max_mp = data.base_stats.mp
        attack = data.base_stats.attack
        defense = data.base_stats.defense
        power = data.base_stats.power
        speed = data.base_stats.speed
    return Hero(
        id=data.id,
        name=data.display_name.get(language),
        side="hero",
        max_hp=max_hp,
        hp=max_hp,
        max_mp=max_mp,
        mp=max_mp,
        attack=attack,
        defense=defense,
        power=power,
        speed=speed,
        skills=skill_states,
        short_tag=data.short_tag,
        class_name=data.class_name.get(language),
    )


def _enemy_from_data(data: EnemyData, language: str = DEFAULT_LANGUAGE) -> Enemy:
    return Enemy(
        id=data.id,
        name=data.display_name.get(language),
        side="enemy",
        max_hp=data.base_stats.hp,
        hp=data.base_stats.hp,
        max_mp=data.base_stats.mp,
        mp=data.base_stats.mp,
        attack=data.base_stats.attack,
        defense=data.base_stats.defense,
        power=data.base_stats.power,
        speed=data.base_stats.speed,
        behavior_kind=data.behavior.kind,
        attack_chance=data.behavior.attack_chance,
        chant_damage=data.behavior.chant_damage,
        chant_charge_turns=data.behavior.chant_charge_turns,
        short_glyph=data.short_glyph,
        family_id=data.family_id,
        tier=data.tier,
    )


def run_mock_battle(
    bundle: ContentBundle,
    provider: Provider,
    *,
    hero_id: str,
    enemy_ids: list[str],
    seed: int = 1,
    max_ticks: int = DEFAULT_MAX_TICKS,
    language: str = DEFAULT_LANGUAGE,
    prompt_style: str | None = None,
) -> tuple[BattleState, list[TurnRecord]]:
    """Convenience helper used by tests and the CLI."""
    loop = BattleLoop(
        bundle,
        provider,
        seed=seed,
        max_ticks=max_ticks,
        language=language,
        prompt_style=prompt_style,
    )
    state = loop.setup(hero_id, enemy_ids)
    loop.run(state)
    return state, loop.records


@dataclass
class BatchResult:
    hero_id: str
    enemy_ids: tuple[str, ...]
    hero_display_name: str = ""
    enemy_display_names: dict[str, str] = field(default_factory=dict)
    skill_display_names: dict[str, str] = field(default_factory=dict)
    build_name: str = ""
    build_stage_badge: str = ""
    enemy_tier_counts: dict[str, int] = field(default_factory=dict)
    prompt_style: str | None = None
    reports: list[BattleReport] = field(default_factory=list)

    @property
    def total_runs(self) -> int:
        return len(self.reports)

    @property
    def victories(self) -> int:
        return sum(1 for r in self.reports if r.result == "victory")

    @property
    def defeats(self) -> int:
        return sum(1 for r in self.reports if r.result == "defeat")

    @property
    def timeouts(self) -> int:
        return sum(1 for r in self.reports if r.result == "timeout")

    @property
    def win_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.victories / self.total_runs

    @property
    def avg_hero_turns(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return sum(r.hero_turn_count for r in self.reports) / self.total_runs

    @property
    def hero_turn_spread(self) -> tuple[int, int, int, int]:
        return _spread(r.hero_turn_count for r in self.reports)

    @property
    def tick_spread(self) -> tuple[int, int, int, int]:
        return _spread(r.total_ticks for r in self.reports)

    @property
    def avg_basic_attack_ratio(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return sum(r.basic_attack_ratio for r in self.reports) / self.total_runs

    @property
    def avg_skill_ratio(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return sum(r.skill_usage_ratio for r in self.reports) / self.total_runs

    @property
    def build_text(self) -> str:
        if not self.build_name:
            return "unknown"
        badge = f" {self.build_stage_badge}" if self.build_stage_badge else ""
        return f"{self.build_name}{badge}"

    @property
    def enemy_tier_text(self) -> str:
        if not self.enemy_tier_counts:
            return "unknown"
        tier_order = ("trace", "ritebound", "archive_bound")
        ordered = [
            (tier, self.enemy_tier_counts[tier])
            for tier in tier_order
            if tier in self.enemy_tier_counts
        ]
        ordered.extend(
            sorted(
                (tier, count)
                for tier, count in self.enemy_tier_counts.items()
                if tier not in tier_order
            )
        )
        return ", ".join(f"{tier}={count}" for tier, count in ordered)

    @property
    def hero_text(self) -> str:
        return self.hero_display_name or self.hero_id

    @property
    def enemy_text(self) -> str:
        names = [self.enemy_display_names.get(enemy_id, enemy_id) for enemy_id in self.enemy_ids]
        return ", ".join(names)

    @property
    def group_key_text(self) -> str:
        return (
            f"hero={self.hero_text} | "
            f"build={self.build_text} | "
            f"tier={self.enemy_tier_text}"
        )

    @property
    def total_fallbacks(self) -> int:
        return sum(r.fallback_count for r in self.reports)

    @property
    def skill_usage_counter(self) -> Counter:
        counter: Counter = Counter()
        for r in self.reports:
            counter.update(r.skill_usage)
        return counter

    @property
    def killed_by_counter(self) -> Counter:
        counter: Counter = Counter()
        for r in self.reports:
            if r.killed_by:
                counter[r.killed_by] += 1
        return counter

    @property
    def avg_damage_dealt(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return sum(r.hero_damage_dealt for r in self.reports) / self.total_runs

    @property
    def avg_damage_taken(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return sum(r.enemy_damage_dealt for r in self.reports) / self.total_runs

    @property
    def tempo_budget_text(self) -> str:
        if not self.reports:
            return "unknown"
        report = self.reports[0]
        return (
            f"{report.tempo_budget_label} "
            f"{report.tempo_budget_min_turns}-{report.tempo_budget_max_turns}"
        )

    @property
    def tempo_outliers(self) -> int:
        return sum(1 for r in self.reports if r.tempo_outlier)

    @property
    def tempo_outlier_counter(self) -> Counter:
        counter: Counter = Counter()
        for report in self.reports:
            if report.tempo_outlier_reason:
                counter[report.tempo_outlier_reason] += 1
        return counter

    @property
    def long_fight_reason_counter(self) -> Counter:
        counter: Counter = Counter()
        for report in self.reports:
            if report.hero_turn_count <= report.tempo_budget_max_turns:
                continue
            reason = report.tempo_outlier_reason or "over_budget"
            if reason == "under_budget_burst":
                continue
            counter[reason] += 1
        return counter

    @property
    def timeout_reason_counter(self) -> Counter:
        counter: Counter = Counter()
        for report in self.reports:
            if report.result != "timeout":
                continue
            counter[report.tempo_outlier_reason or "safety_limit"] += 1
        return counter

    @property
    def total_mp_dry_turns(self) -> int:
        return sum(r.mp_dry_turns for r in self.reports)

    @property
    def total_low_impact_turns(self) -> int:
        return sum(r.low_impact_turns for r in self.reports)

    @property
    def total_targeting_drift_turns(self) -> int:
        return sum(r.targeting_drift_turns for r in self.reports)

    @property
    def max_defense_loop(self) -> int:
        if not self.reports:
            return 0
        return max(r.max_defense_loop for r in self.reports)

    @property
    def total_counter_windows_opened(self) -> int:
        return sum(r.counter_windows_opened for r in self.reports)

    @property
    def total_counter_windows_answered(self) -> int:
        return sum(r.counter_windows_answered for r in self.reports)

    @property
    def total_counter_windows_missed(self) -> int:
        return sum(r.counter_windows_missed for r in self.reports)

    @property
    def total_boss_break_missed(self) -> int:
        return sum(r.boss_break_missed for r in self.reports)

    @property
    def failure_reason_counter(self) -> Counter:
        counter: Counter = Counter()
        for report in self.reports:
            counter.update(report.failure_reasons)
        return counter

    @property
    def next_run_advice_counter(self) -> Counter:
        counter: Counter = Counter()
        for report in self.reports:
            counter.update(report.next_run_advice)
        return counter

    @property
    def prompt_impact_counter(self) -> Counter:
        counter: Counter = Counter()
        for report in self.reports:
            counter.update(self._display_prompt_impact(impact) for impact in report.prompt_impacts)
        return counter

    def summary(self, language: str = "en") -> list[str]:
        lines: list[str] = []

        header = {
            "en": "=== BATCH RUN REPORT ===",
            "zh": "=== 批量运行报告 ===",
        }.get(language, "=== BATCH RUN REPORT ===")
        lines.append(header)
        lines.append("")

        hero_label = {
            "en": f"Hero: {self.hero_text}",
            "zh": f"英雄: {self.hero_text}",
        }.get(language, f"Hero: {self.hero_text}")
        lines.append(hero_label)

        enemy_label = {
            "en": f"Enemies: {self.enemy_text}",
            "zh": f"敌人: {self.enemy_text}",
        }.get(language, f"Enemies: {self.enemy_text}")
        lines.append(enemy_label)
        build_label = {
            "en": f"Build: {self.build_text}",
            "zh": f"Build: {self.build_text}",
        }.get(language, f"Build: {self.build_text}")
        lines.append(build_label)
        tier_label = {
            "en": f"Enemy tiers: {self.enemy_tier_text}",
            "zh": f"敌人阶层: {self.enemy_tier_text}",
        }.get(language, f"Enemy tiers: {self.enemy_tier_text}")
        lines.append(tier_label)
        group_label = {
            "en": f"Group key: {self.group_key_text}",
            "zh": f"分组键: {self.group_key_text}",
        }.get(language, f"Group key: {self.group_key_text}")
        lines.append(group_label)
        if self.prompt_style:
            style_label = {
                "en": f"Prompt style: {self.prompt_style}",
                "zh": f"Prompt 预设: {self.prompt_style}",
            }.get(language, f"Prompt style: {self.prompt_style}")
            lines.append(style_label)
        prompt_impacts = self.prompt_impact_counter
        if prompt_impacts:
            prompt_header = {
                "en": "Prompt Impact:",
                "zh": "Prompt 影响:",
            }.get(language, "Prompt Impact:")
            lines.append(prompt_header)
            for impact, count in prompt_impacts.most_common(3):
                lines.append(f"  {count}x {impact}")
        lines.append("")

        lines.extend(self._balance_tuning_board(language))
        lines.append("")
        lines.extend(self._sample_heatmap_board(language))
        lines.append("")

        stats_header = {
            "en": "Overall Stats:",
            "zh": "总体统计:",
        }.get(language, "Overall Stats:")
        lines.append(stats_header)

        total_label = {
            "en": f"  Total runs: {self.total_runs}",
            "zh": f"  总运行数: {self.total_runs}",
        }.get(language, f"  Total runs: {self.total_runs}")
        lines.append(total_label)

        victory_label = {
            "en": f"  Victories: {self.victories} ({self.win_rate:.1%})",
            "zh": f"  胜利: {self.victories} ({self.win_rate:.1%})",
        }.get(language, f"  Victories: {self.victories} ({self.win_rate:.1%})")
        lines.append(victory_label)

        defeat_label = {
            "en": f"  Defeats: {self.defeats}",
            "zh": f"  战败: {self.defeats}",
        }.get(language, f"  Defeats: {self.defeats}")
        lines.append(defeat_label)

        timeout_label = {
            "en": f"  Timeouts: {self.timeouts}",
            "zh": f"  超时: {self.timeouts}",
        }.get(language, f"  Timeouts: {self.timeouts}")
        lines.append(timeout_label)
        lines.append("")

        action_header = {
            "en": "Action Patterns:",
            "zh": "行动模式:",
        }.get(language, "Action Patterns:")
        lines.append(action_header)

        turns_label = {
            "en": f"  Avg hero turns: {self.avg_hero_turns:.1f}",
            "zh": f"  平均英雄回合: {self.avg_hero_turns:.1f}",
        }.get(language, f"  Avg hero turns: {self.avg_hero_turns:.1f}")
        lines.append(turns_label)

        hero_spread_label = {
            "en": f"  Hero turn spread: {_format_spread(self.hero_turn_spread)}",
            "zh": f"  英雄回合分布: {_format_spread(self.hero_turn_spread)}",
        }.get(language, f"  Hero turn spread: {_format_spread(self.hero_turn_spread)}")
        lines.append(hero_spread_label)

        tick_spread_label = {
            "en": f"  Tick spread: {_format_spread(self.tick_spread)}",
            "zh": f"  刻度分布: {_format_spread(self.tick_spread)}",
        }.get(language, f"  Tick spread: {_format_spread(self.tick_spread)}")
        lines.append(tick_spread_label)

        basic_label = {
            "en": f"  Avg basic attack ratio: {self.avg_basic_attack_ratio:.1%}",
            "zh": f"  平均普攻占比: {self.avg_basic_attack_ratio:.1%}",
        }.get(language, f"  Avg basic attack ratio: {self.avg_basic_attack_ratio:.1%}")
        lines.append(basic_label)

        skill_label = {
            "en": f"  Avg skill usage ratio: {self.avg_skill_ratio:.1%}",
            "zh": f"  平均技能使用率: {self.avg_skill_ratio:.1%}",
        }.get(language, f"  Avg skill usage ratio: {self.avg_skill_ratio:.1%}")
        lines.append(skill_label)

        fallback_label = {
            "en": f"  Total fallbacks/invalid: {self.total_fallbacks}",
            "zh": f"  总回退/无效: {self.total_fallbacks}",
        }.get(language, f"  Total fallbacks/invalid: {self.total_fallbacks}")
        lines.append(fallback_label)
        lines.append("")

        tempo_header = {
            "en": "Tempo Diagnostics:",
            "zh": "节奏诊断:",
        }.get(language, "Tempo Diagnostics:")
        lines.append(tempo_header)

        budget_label = {
            "en": f"  Budget: {self.tempo_budget_text} hero turns",
            "zh": f"  预算: {self.tempo_budget_text} 英雄回合",
        }.get(language, f"  Budget: {self.tempo_budget_text} hero turns")
        lines.append(budget_label)

        outlier_label = {
            "en": f"  Tempo outliers: {self.tempo_outliers}/{self.total_runs}",
            "zh": f"  节奏异常: {self.tempo_outliers}/{self.total_runs}",
        }.get(language, f"  Tempo outliers: {self.tempo_outliers}/{self.total_runs}")
        lines.append(outlier_label)

        mp_dry_label = {
            "en": f"  MP dry turns: {self.total_mp_dry_turns}",
            "zh": f"  MP 枯竭回合: {self.total_mp_dry_turns}",
        }.get(language, f"  MP dry turns: {self.total_mp_dry_turns}")
        lines.append(mp_dry_label)

        low_impact_label = {
            "en": f"  Low-impact turns: {self.total_low_impact_turns}",
            "zh": f"  低收益回合: {self.total_low_impact_turns}",
        }.get(language, f"  Low-impact turns: {self.total_low_impact_turns}")
        lines.append(low_impact_label)

        target_drift_label = {
            "en": f"  Targeting drift turns: {self.total_targeting_drift_turns}",
            "zh": f"  目标偏移回合: {self.total_targeting_drift_turns}",
        }.get(language, f"  Targeting drift turns: {self.total_targeting_drift_turns}")
        lines.append(target_drift_label)

        defense_loop_label = {
            "en": f"  Max defense loop: {self.max_defense_loop}",
            "zh": f"  最长防御循环: {self.max_defense_loop}",
        }.get(language, f"  Max defense loop: {self.max_defense_loop}")
        lines.append(defense_loop_label)

        counters_label = {
            "en": (
                "  Counter windows: "
                f"{self.total_counter_windows_answered}/"
                f"{self.total_counter_windows_opened} answered, "
                f"{self.total_counter_windows_missed} missed"
            ),
            "zh": (
                "  反制窗口: "
                f"{self.total_counter_windows_answered}/"
                f"{self.total_counter_windows_opened} 已回应, "
                f"{self.total_counter_windows_missed} 次错失"
            ),
        }.get(
            language,
            "  Counter windows: "
            f"{self.total_counter_windows_answered}/"
            f"{self.total_counter_windows_opened} answered, "
            f"{self.total_counter_windows_missed} missed",
        )
        lines.append(counters_label)

        metric_key_label = {
            "en": (
                "  Metric keys: "
                f"tempo_outlier={self.tempo_outliers}, "
                f"mp_dry_turns={self.total_mp_dry_turns}, "
                f"defense_loop_turns={self.max_defense_loop}, "
                f"boss_break_missed={self.total_boss_break_missed}"
            ),
            "zh": (
                "  指标键: "
                f"tempo_outlier={self.tempo_outliers}, "
                f"mp_dry_turns={self.total_mp_dry_turns}, "
                f"defense_loop_turns={self.max_defense_loop}, "
                f"boss_break_missed={self.total_boss_break_missed}"
            ),
        }.get(
            language,
            "  Metric keys: "
            f"tempo_outlier={self.tempo_outliers}, "
            f"mp_dry_turns={self.total_mp_dry_turns}, "
            f"defense_loop_turns={self.max_defense_loop}, "
            f"boss_break_missed={self.total_boss_break_missed}",
        )
        lines.append(metric_key_label)

        outlier_counter = self.tempo_outlier_counter
        if outlier_counter:
            reason_label = {
                "en": "  Outlier reasons:",
                "zh": "  异常原因:",
            }.get(language, "  Outlier reasons:")
            lines.append(reason_label)
            for reason, count in outlier_counter.most_common(5):
                lines.append(f"    {reason}: {count}")

        long_fight_counter = self.long_fight_reason_counter
        if long_fight_counter:
            long_label = {
                "en": "  Long fight causes:",
                "zh": "  拖长原因:",
            }.get(language, "  Long fight causes:")
            lines.append(long_label)
            for reason, count in long_fight_counter.most_common(5):
                lines.append(f"    {reason}: {count}")

        timeout_counter = self.timeout_reason_counter
        if timeout_counter:
            timeout_reason_label = {
                "en": "  Timeout causes:",
                "zh": "  超时原因:",
            }.get(language, "  Timeout causes:")
            lines.append(timeout_reason_label)
            for reason, count in timeout_counter.most_common(5):
                lines.append(f"    {reason}: {count}")
        lines.append("")

        skill_counter = self.skill_usage_counter
        if skill_counter:
            skill_header = {
                "en": "Skill Usage Detail:",
                "zh": "技能使用详情:",
            }.get(language, "Skill Usage Detail:")
            lines.append(skill_header)
            for skill_id, count in skill_counter.most_common(10):
                lines.append(f"  {self._skill_display_name(skill_id)}: {count}")
            lines.append("")

        damage_header = {
            "en": "Damage Stats:",
            "zh": "伤害统计:",
        }.get(language, "Damage Stats:")
        lines.append(damage_header)

        dealt_label = {
            "en": f"  Avg damage dealt: {self.avg_damage_dealt:.1f}",
            "zh": f"  平均输出: {self.avg_damage_dealt:.1f}",
        }.get(language, f"  Avg damage dealt: {self.avg_damage_dealt:.1f}")
        lines.append(dealt_label)

        taken_label = {
            "en": f"  Avg damage taken: {self.avg_damage_taken:.1f}",
            "zh": f"  平均承伤: {self.avg_damage_taken:.1f}",
        }.get(language, f"  Avg damage taken: {self.avg_damage_taken:.1f}")
        lines.append(taken_label)

        killed_by = self.killed_by_counter
        if killed_by:
            lines.append("")
            defeat_cause = {
                "en": "Defeat Causes:",
                "zh": "战败原因:",
            }.get(language, "Defeat Causes:")
            lines.append(defeat_cause)
            for enemy_id, count in killed_by.most_common(5):
                lines.append(f"  {self.enemy_display_names.get(enemy_id, enemy_id)}: {count}")

        failure_reasons = self.failure_reason_counter
        advice = self.next_run_advice_counter
        if failure_reasons or advice:
            lines.append("")
            lesson_header = {
                "en": "Failure Lessons:",
                "zh": "失败复盘:",
            }.get(language, "Failure Lessons:")
            lines.append(lesson_header)
            if failure_reasons:
                reason_header = {
                    "en": "  Top reasons:",
                    "zh": "  高频原因:",
                }.get(language, "  Top reasons:")
                lines.append(reason_header)
                for reason, count in failure_reasons.most_common(3):
                    lines.append(f"    {count}x {reason}")
            if advice:
                advice_header = {
                    "en": "  Next run advice:",
                    "zh": "  下一局建议:",
                }.get(language, "  Next run advice:")
                lines.append(advice_header)
                for line, count in advice.most_common(3):
                    lines.append(f"    {count}x {line}")

        return lines

    def _skill_display_name(self, skill_id: str) -> str:
        return self.skill_display_names.get(skill_id, skill_id)

    def _display_prompt_impact(self, impact: str) -> str:
        return _replace_display_ids(
            impact,
            {
                **self.skill_display_names,
                **self.enemy_display_names,
                self.hero_id: self.hero_text,
            },
        )

    def _balance_tuning_board(self, language: str) -> list[str]:
        action = self._balance_tuning_action(language)
        if language == "zh":
            return [
                "BALANCE TUNING BOARD :: 数值调参板",
                f"  [WIN] {self.win_rate:.1%} / {self.victories}/{self.total_runs}",
                f"  [TEMPO] outliers {self.tempo_outliers}/{self.total_runs} / budget {self.tempo_budget_text}",
                f"  [ACTION] skill {self.avg_skill_ratio:.1%} / basic {self.avg_basic_attack_ratio:.1%}",
                f"  [RESOURCE] MP dry {self.total_mp_dry_turns} / defense loop {self.max_defense_loop}",
                f"  [TUNE] {action}",
            ]
        return [
            "BALANCE TUNING BOARD",
            f"  [WIN] {self.win_rate:.1%} / {self.victories}/{self.total_runs}",
            f"  [TEMPO] outliers {self.tempo_outliers}/{self.total_runs} / budget {self.tempo_budget_text}",
            f"  [ACTION] skill {self.avg_skill_ratio:.1%} / basic {self.avg_basic_attack_ratio:.1%}",
            f"  [RESOURCE] MP dry {self.total_mp_dry_turns} / defense loop {self.max_defense_loop}",
            f"  [TUNE] {action}",
        ]

    def _sample_heatmap_board(self, language: str) -> list[str]:
        sample_limit = 12
        samples = self.reports[:sample_limit]
        omitted = max(0, self.total_runs - sample_limit)
        result_tokens = [self._sample_result_token(report) for report in samples]
        tempo_tokens = [self._sample_tempo_token(report) for report in samples]
        alert_tokens = [self._sample_alert_token(report) for report in samples]

        if omitted:
            result_tokens.append(f"+{omitted}")
            tempo_tokens.append("..")
            alert_tokens.append("..")

        result_line = " ".join(result_tokens) if result_tokens else "-"
        tempo_line = " ".join(tempo_tokens) if tempo_tokens else "-"
        alert_line = " ".join(alert_tokens) if alert_tokens else "-"
        read = self._sample_heatmap_read(language)

        if language == "zh":
            return [
                "BATCH SAMPLE HEATMAP :: 样本热力图",
                "  [KEY] V 胜利 / D 战败 / T 超时 / ! 节奏异常 / M MP 枯竭 / B 破防错失 / C 反制错失 / L 防御循环",
                f"  [RESULT] {result_line}",
                f"  [TEMPO]  {tempo_line} hero turns / budget {self.tempo_budget_text}",
                f"  [ALERT]  {alert_line}",
                f"  [READ] {read}",
            ]
        return [
            "BATCH SAMPLE HEATMAP",
            "  [KEY] V victory / D defeat / T timeout / ! tempo outlier / M MP dry / B break missed / C counter missed / L defense loop",
            f"  [RESULT] {result_line}",
            f"  [TEMPO]  {tempo_line} hero turns / budget {self.tempo_budget_text}",
            f"  [ALERT]  {alert_line}",
            f"  [READ] {read}",
        ]

    @staticmethod
    def _sample_result_token(report: BattleReport) -> str:
        if report.result == "victory":
            return "V"
        if report.result == "defeat":
            return "D"
        if report.result == "timeout":
            return "T"
        return "?"

    @staticmethod
    def _sample_tempo_token(report: BattleReport) -> str:
        prefix = "!" if report.tempo_outlier else " "
        return f"{prefix}{report.hero_turn_count:02d}"

    @staticmethod
    def _sample_alert_token(report: BattleReport) -> str:
        alerts: list[str] = []
        if report.tempo_outlier:
            alerts.append("!")
        if report.mp_dry_turns:
            alerts.append("M")
        if report.boss_break_missed:
            alerts.append("B")
        if report.max_defense_loop >= 3:
            alerts.append("L")
        if report.counter_windows_missed and "B" not in alerts:
            alerts.append("C")
        return "".join(alerts[:2]) if alerts else "."

    def _sample_heatmap_read(self, language: str) -> str:
        if self.total_runs == 0:
            return "run more samples" if language == "en" else "增加样本"
        if self.timeouts:
            return "timeout lane visible; inspect sustain loops" if language == "en" else "已出现超时通道；检查循环拖延"
        if self.tempo_outliers:
            return "outlier lane visible; tune by alert token first" if language == "en" else "已出现异常通道；先按警示 token 调参"
        if self.total_counter_windows_missed:
            return "counter lane visible; verify interrupt/read timing" if language == "en" else "已出现反制错失；检查打断与读条时机"
        if self.max_defense_loop >= 3:
            return "defense loop lane visible; verify sustain incentives" if language == "en" else "已出现防御循环；检查生存收益"
        if self.win_rate in (0.0, 1.0) and self.total_runs < 10:
            return "small sample is clean; expand count before locking balance" if language == "en" else "小样本干净；锁数值前扩大样本"
        if self.win_rate > 0.85:
            return "stable but easy; raise pressure in next group" if language == "en" else "稳定但偏易；下一组提高压力"
        if self.win_rate < 0.35:
            return "stable but harsh; ease pressure in next group" if language == "en" else "稳定但偏难；下一组降低压力"
        return "stable lane; compare larger count or harder tier" if language == "en" else "样本稳定；对比更大样本或更高阶敌人"

    def _balance_tuning_action(self, language: str) -> str:
        if self.total_runs == 0:
            return "run more samples" if language == "en" else "增加样本"
        if self.timeouts:
            return "reduce sustain loops or raise damage budget" if language == "en" else "降低循环拖延或提高输出预算"
        if self.tempo_outliers:
            return "inspect outlier reasons before tuning stats" if language == "en" else "先看异常原因再调数值"
        if self.win_rate < 0.35:
            return "ease early pressure or improve survival picks" if language == "en" else "降低前期压力或增强生存选择"
        if self.win_rate > 0.85:
            return "raise elite/boss pressure or lower free tempo" if language == "en" else "提高精英/Boss 压力或削弱免费节奏"
        if self.avg_basic_attack_ratio > 0.55:
            return "add MP recovery or improve skill incentives" if language == "en" else "增加 MP 回复或提高技能收益"
        return "stable sample; compare another hero/build group" if language == "en" else "样本稳定；对比另一组英雄/Build"


def run_batch(
    bundle: ContentBundle,
    *,
    hero_id: str,
    enemy_ids: list[str],
    count: int = 10,
    base_seed: int = 1,
    max_ticks: int = DEFAULT_MAX_TICKS,
    language: str = DEFAULT_LANGUAGE,
    prompt_style: str | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> BatchResult:
    """Run multiple battles with sequential seeds for balance testing.

    Args:
        bundle: Content bundle
        hero_id: Hero to use
        enemy_ids: Enemies to fight
        count: Number of battles to run
        base_seed: Starting seed (will use base_seed, base_seed+1, ...)
        max_ticks: Safety limit per battle
        language: Language for mock provider
        progress_callback: Optional callback (current, total) for progress updates

    Returns:
        BatchResult with aggregated statistics
    """
    from ouro_agent.providers.mock import MockProvider

    hero_data = bundle.get_hero(hero_id)
    build = resolve_build(hero_data, bundle)
    progress = build.calculate_progress(bundle)
    hero_display_name = hero_data.display_name.get(language)
    enemy_display_names = {
        eid: bundle.get_enemy(eid).display_name.get(language)
        for eid in enemy_ids
    }
    skill_display_names = {
        sid: bundle.get_skill(sid).display_name.get(language)
        for sid in hero_data.skills
    }
    enemy_tiers = Counter(bundle.get_enemy(eid).tier for eid in enemy_ids)
    result = BatchResult(
        hero_id=hero_id,
        enemy_ids=tuple(enemy_ids),
        hero_display_name=hero_display_name,
        enemy_display_names=enemy_display_names,
        skill_display_names=skill_display_names,
        build_name=build.archetype(language),
        build_stage_badge=progress.stage.badge,
        enemy_tier_counts=dict(enemy_tiers),
        prompt_style=prompt_style,
    )

    for i in range(count):
        seed = base_seed + i
        provider = MockProvider(seed=seed, language=language)
        state, records = run_mock_battle(
            bundle,
            provider,
            hero_id=hero_id,
            enemy_ids=enemy_ids,
            seed=seed,
            max_ticks=max_ticks,
            language=language,
            prompt_style=prompt_style,
        )
        report = generate_battle_report(state, records)
        result.reports.append(report)

        if progress_callback:
            progress_callback(i + 1, count)

    return result


def _spread(values: Iterable[int]) -> tuple[int, int, int, int]:
    sorted_values = sorted(int(value) for value in values)
    if not sorted_values:
        return (0, 0, 0, 0)
    return (
        sorted_values[0],
        _percentile(sorted_values, 50),
        _percentile(sorted_values, 90),
        sorted_values[-1],
    )


def _percentile(sorted_values: list[int], pct: int) -> int:
    if not sorted_values:
        return 0
    index = ((pct * len(sorted_values) + 99) // 100) - 1
    index = max(0, min(len(sorted_values) - 1, index))
    return sorted_values[index]


def _format_spread(spread: tuple[int, int, int, int]) -> str:
    low, p50, p90, high = spread
    return f"min {low} / p50 {p50} / p90 {p90} / max {high}"
