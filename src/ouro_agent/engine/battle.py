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
