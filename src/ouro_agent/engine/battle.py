"""ATB battle loop.

Deterministic for a given seed and content. Hero turns delegate to a Provider
and validator; enemy turns use the rule AI in ``enemy_ai``. The loop never
calls a Provider directly without going through the validator, so a malformed
or absent action degrades to defend/basic_attack instead of crashing.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Iterable

from ouro_agent.content.schema import (
    EnemyData,
    HeroData,
    SkillData,
    ContentBundle,
)
from ouro_agent.engine.build import ResolvedBuild, resolve_build
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
                lines.append(f"  {skill_id}: {count}")
        
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
    )


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


HeroTurnHook = Callable[[BattleState, "TurnRecord"], None]
EnemyTurnHook = Callable[[BattleState, "TurnRecord"], None]


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
            compose_static_context(state, self.bundle, self.hero_prompt_override),
        )
        return state

    def run(
        self,
        state: BattleState,
        on_hero_turn: HeroTurnHook | None = None,
        on_enemy_turn: EnemyTurnHook | None = None,
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
) -> tuple[BattleState, list[TurnRecord]]:
    """Convenience helper used by tests and the CLI."""
    loop = BattleLoop(
        bundle, provider, seed=seed, max_ticks=max_ticks, language=language
    )
    state = loop.setup(hero_id, enemy_ids)
    loop.run(state)
    return state, loop.records
