"""Deterministic rule AI for enemies.

The AI is intentionally simple. The model never sees these rules; the engine
fully controls them so combat is decidable.
"""
from __future__ import annotations

import random

from ouro_agent.engine.models import BattleState, Enemy, Hero


def decide_enemy_action(enemy: Enemy, state: BattleState, rng: random.Random) -> dict:
    """Return a structured action dict for an enemy turn."""
    if enemy.behavior_kind == "rule_chant":
        if enemy.chant_progress < enemy.chant_charge_turns:
            return {"type": "chant_charge"}
        if rng.random() < enemy.attack_chance:
            return {"type": "chant_release", "damage": enemy.chant_damage}
        return {"type": "basic_attack"}

    if rng.random() < enemy.attack_chance:
        return {"type": "basic_attack"}
    return {"type": "defend"}


def resolve_enemy_action(
    enemy: Enemy,
    action: dict,
    state: BattleState,
) -> None:
    """Apply the enemy action to the BattleState. Engine-only resolution."""
    hero: Hero = state.hero
    kind = action.get("type")

    if kind == "basic_attack":
        damage = max(1, enemy.attack - hero.defense // 2)
        damage = _absorb_shield(hero, damage, state)
        hero.hp = max(0, hero.hp - damage)
        state.push_log("enemy.basic_attack", enemy=enemy.name, hero=hero.name, dmg=damage)
        state.emit(
            "enemy_attack",
            enemy_id=enemy.id,
            target_id=hero.id,
            damage=damage,
            kind="basic_attack",
        )
        return

    if kind == "chant_charge":
        enemy.chant_progress += 1
        state.push_log("enemy.chant_charge", enemy=enemy.name)
        state.emit("enemy_charge", enemy_id=enemy.id, progress=enemy.chant_progress)
        return

    if kind == "chant_release":
        damage = max(1, int(action.get("damage", enemy.chant_damage)) - hero.defense // 3)
        damage = _absorb_shield(hero, damage, state)
        hero.hp = max(0, hero.hp - damage)
        enemy.chant_progress = 0
        state.push_log("enemy.chant_release", enemy=enemy.name, dmg=damage)
        state.emit(
            "enemy_attack",
            enemy_id=enemy.id,
            target_id=hero.id,
            damage=damage,
            kind="chant_release",
        )
        return

    state.push_log("enemy.defend", enemy=enemy.name)
    state.emit("enemy_defend", enemy_id=enemy.id)


def _absorb_shield(hero: Hero, damage: int, state: BattleState) -> int:
    shield = hero.find_status("status_shield")
    if shield is None or shield.stacks <= 0:
        return damage
    absorbed = min(shield.stacks, damage)
    shield.stacks -= absorbed
    if shield.stacks <= 0:
        hero.statuses = [s for s in hero.statuses if s.id != "status_shield"]
    state.push_log("shield.absorb", n=absorbed)
    state.emit("shield_absorb", target_id=hero.id, absorbed=absorbed)
    return damage - absorbed
