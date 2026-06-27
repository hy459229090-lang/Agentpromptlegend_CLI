"""Local judge: validate hero actions and resolve damage.

The judge is the only place that resolves damage, status, MP, cooldowns, and
death. The model does not decide any of these; it only proposes an action.
"""
from __future__ import annotations

from dataclasses import dataclass

from ouro_agent.content.schema import SkillData, StatusApplication
from ouro_agent.engine.models import (
    BattleState,
    Enemy,
    Hero,
    SkillState,
    StatusEffect,
)
from ouro_agent.llm.actions import HeroAction


@dataclass(frozen=True)
class JudgeOutcome:
    valid: bool
    reason: str
    summary: str
    damage: int = 0
    target_ids: tuple[str, ...] = ()
    skill_id: str | None = None
    action_kind: str | None = None
    fallback_to: str | None = None


class Judge:
    """Pure rules. No randomness, no I/O."""

    def __init__(self, skills: dict[str, SkillData]):
        self._skills = skills

    def resolve(self, action: HeroAction, state: BattleState) -> JudgeOutcome:
        hero: Hero = state.hero
        kind = action.type

        if kind == "basic_attack":
            return self._resolve_basic_attack(action, hero, state)
        if kind == "cast_skill":
            return self._resolve_cast_skill(action, hero, state)
        if kind == "defend":
            return self._resolve_defend(hero, state)
        if kind == "observe":
            return self._resolve_observe(state)
        if kind == "change_stance":
            return self._resolve_stance(state)
        if kind == "use_item":
            return JudgeOutcome(
                valid=False,
                reason="items not available in MVP",
                summary="Astia hesitates: no items in hand.",
                fallback_to="defend",
            )
        return JudgeOutcome(
            valid=False,
            reason=f"unknown action type '{kind}'",
            summary="Astia hesitates.",
            fallback_to="defend",
        )

    def _resolve_basic_attack(
        self, action: HeroAction, hero: Hero, state: BattleState
    ) -> JudgeOutcome:
        target = self._first_living_target(action.targets, state)
        if target is None:
            return JudgeOutcome(
                valid=False,
                reason="no living target",
                summary="Astia swings at nothing.",
                fallback_to="defend",
                action_kind="basic_attack",
            )
        damage = max(1, hero.attack - target.defense // 2)
        target.hp = max(0, target.hp - damage)
        state.push_log(
            "hero.basic_attack", hero=hero.name, target=target.name, dmg=damage
        )
        state.emit(
            "hero_attack",
            target_id=target.id,
            damage=damage,
            kind="basic_attack",
        )
        return JudgeOutcome(
            valid=True,
            reason="basic attack landed",
            summary=f"basic_attack -> {target.id} | {damage} dmg",
            damage=damage,
            target_ids=(target.id,),
            action_kind="basic_attack",
        )

    def _resolve_cast_skill(
        self, action: HeroAction, hero: Hero, state: BattleState
    ) -> JudgeOutcome:
        if action.skill_id is None:
            return JudgeOutcome(
                valid=False,
                reason="cast_skill missing skill_id",
                summary="Astia's incantation falters.",
                fallback_to="basic_attack",
                action_kind="cast_skill",
            )
        if action.skill_id not in self._skills:
            return JudgeOutcome(
                valid=False,
                reason=f"unknown skill '{action.skill_id}'",
                summary="Astia tries to cast a memory she doesn't have.",
                fallback_to="basic_attack",
                action_kind="cast_skill",
                skill_id=action.skill_id,
            )
        skill_state: SkillState | None = hero.find_skill(action.skill_id)
        if skill_state is None:
            return JudgeOutcome(
                valid=False,
                reason="hero does not know this skill",
                summary="The skill is unknown to this hero.",
                fallback_to="basic_attack",
                action_kind="cast_skill",
                skill_id=action.skill_id,
            )
        if skill_state.cooldown_remaining > 0:
            return JudgeOutcome(
                valid=False,
                reason=f"on cooldown ({skill_state.cooldown_remaining})",
                summary="The skill is still cooling.",
                fallback_to="basic_attack",
                action_kind="cast_skill",
                skill_id=action.skill_id,
            )
        if hero.mp < skill_state.mp_cost:
            return JudgeOutcome(
                valid=False,
                reason=f"insufficient MP ({hero.mp}/{skill_state.mp_cost})",
                summary="Mana too low.",
                fallback_to="basic_attack",
                action_kind="cast_skill",
                skill_id=action.skill_id,
            )

        skill = self._skills[action.skill_id]
        targets = self._select_skill_targets(skill, action, hero, state)
        if not targets:
            return JudgeOutcome(
                valid=False,
                reason="no valid target for skill",
                summary="No legal target for the skill.",
                fallback_to="basic_attack",
                action_kind="cast_skill",
                skill_id=action.skill_id,
            )

        hero.mp -= skill_state.mp_cost
        skill_state.cooldown_remaining = skill_state.cooldown
        damage_total = 0
        target_ids: list[str] = []
        for target in targets:
            damage = self._apply_skill_to(skill, hero, target, state)
            damage_total += damage
            target_ids.append(target.id)
        counter = self._tower_brace_counter(skill, hero, state)
        if counter is not None:
            counter_target, counter_damage = counter
            damage_total += counter_damage
            target_ids.append(counter_target.id)

        state.push_log(
            "hero.cast_skill",
            hero=hero.name,
            skill=skill.display_name.get(state.language),
            mp=skill_state.mp_cost,
            cd=skill_state.cooldown,
        )
        if counter is not None:
            state.push_log(
                "hero.ash_counter",
                hero=hero.name,
                enemy=counter_target.name,
                dmg=counter_damage,
            )
        state.emit(
            "hero_skill",
            skill_id=skill.id,
            target_ids=target_ids,
            damage=damage_total,
        )
        return JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary=(
                f"cast_skill {skill.id} -> {','.join(target_ids)} | "
                f"{damage_total} dmg"
                f"{' | boss_break' if counter is not None else ''}"
            ),
            damage=damage_total,
            target_ids=tuple(target_ids),
            skill_id=skill.id,
            action_kind="cast_skill",
        )

    def _apply_skill_to(
        self,
        skill: SkillData,
        hero: Hero,
        target,
        state: BattleState,
    ) -> int:
        damage = 0
        if skill.effect.kind == "damage" or skill.effect.base > 0:
            raw = skill.effect.base + int(hero.power * skill.effect.power_scale)
            damage = max(1, raw - target.defense // 2) if target.side != "hero" else 0
            if target.side != "hero":
                target.hp = max(0, target.hp - damage)
        if skill.effect.apply_status is not None:
            self._apply_status(skill.effect.apply_status, target, state)
        return damage

    def _apply_status(
        self,
        application: StatusApplication,
        target,
        state: BattleState,
    ) -> None:
        target.add_status(
            StatusEffect(
                id=application.status_id,
                stacks=application.stacks,
                duration=application.duration,
            )
        )
        state.emit(
            "status_applied",
            target_id=target.id,
            status=application.status_id,
            stacks=application.stacks,
            duration=application.duration,
        )

    def _tower_brace_counter(
        self,
        skill: SkillData,
        hero: Hero,
        state: BattleState,
    ) -> tuple[Enemy, int] | None:
        if skill.id != "skill_tower_brace":
            return None
        target = _archive_chant_target(state)
        if target is None:
            return None
        raw = hero.defense + hero.power + 6
        damage = max(18, raw - target.defense // 3)
        target.hp = max(0, target.hp - damage)
        target.chant_progress = 0
        target.add_status(StatusEffect(id="status_silence", stacks=1, duration=2))
        state.emit(
            "boss_break",
            enemy_id=target.id,
            damage=damage,
            source=skill.id,
        )
        return target, damage

    def _resolve_defend(self, hero: Hero, state: BattleState) -> JudgeOutcome:
        hero.add_status(StatusEffect(id="status_shield", stacks=4, duration=2))
        state.push_log("hero.defend", hero=hero.name)
        state.emit("hero_defend", target_id=hero.id, shield=4)
        return JudgeOutcome(
            valid=True,
            reason="defend stance",
            summary="defend | shield +4 (2 turns)",
            target_ids=(hero.id,),
            action_kind="defend",
        )

    def _resolve_observe(self, state: BattleState) -> JudgeOutcome:
        state.push_log("hero.observe", hero=state.hero.name)
        state.emit("hero_observe")
        return JudgeOutcome(
            valid=True,
            reason="observe noted",
            summary="observe",
            action_kind="observe",
        )

    def _resolve_stance(self, state: BattleState) -> JudgeOutcome:
        state.push_log("hero.stance", hero=state.hero.name)
        state.emit("hero_stance")
        return JudgeOutcome(
            valid=True,
            reason="stance change noted",
            summary="change_stance",
            action_kind="change_stance",
        )

    def _first_living_target(self, target_ids: tuple[str, ...], state: BattleState) -> Enemy | None:
        for tid in target_ids:
            for enemy in state.alive_enemies():
                if enemy.id == tid:
                    return enemy
        living = state.alive_enemies()
        return living[0] if living else None

    def _select_skill_targets(
        self,
        skill: SkillData,
        action: HeroAction,
        hero: Hero,
        state: BattleState,
    ):
        if skill.target_rule == "self":
            return [hero]
        if skill.target_rule == "single_enemy":
            t = self._first_living_target(action.targets, state)
            return [t] if t else []
        if skill.target_rule == "all_enemies":
            return state.alive_enemies()
        if skill.target_rule == "single_ally":
            return [hero]
        if skill.target_rule == "all_allies":
            return [hero]
        return []


def _archive_chant_target(state: BattleState) -> Enemy | None:
    candidates = [
        enemy
        for enemy in state.alive_enemies()
        if enemy.tier == "archive_bound" and enemy.chant_progress > 0
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda enemy: enemy.chant_progress)
