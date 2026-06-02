"""Mock provider.

Picks a deterministic, legal action from the hero's available skills based on
the current battle snapshot. Never touches the network and never reads any API
key. Behavior is seeded so that the same battle replay produces identical
output, satisfying REQ-VAL-001.
"""
from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING

from ouro_agent.i18n import DEFAULT_LANGUAGE, narration_text
from ouro_agent.providers.base import EchoUsage, ModelTurnResult, Provider

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ouro_agent.llm.prompt import PromptContext


class MockProvider(Provider):
    name = "mock"

    def __init__(
        self,
        model: str = "mock-smart",
        seed: int = 0,
        latency_ms: int = 12,
        language: str = DEFAULT_LANGUAGE,
    ):
        self._model = model
        self._latency_ms = latency_ms
        self._rng = random.Random(seed)
        self._language = language

    @property
    def model(self) -> str:
        return self._model

    def request_turn(self, prompt: "PromptContext") -> ModelTurnResult:
        snap = prompt.snapshot
        style = _prompt_style(prompt)
        action = self._choose_action(snap, style)
        narration = _narrate(snap, action, self._language)
        analysis = _analyze(snap, action, self._language)
        payload = {
            "narration": narration,
            "analysis": analysis,
            "action": action,
            "confidence": round(0.4 + self._rng.random() * 0.5, 2),
        }
        return ModelTurnResult(
            provider=self.name,
            model=self._model,
            raw_text=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            usage=EchoUsage.zero(latency_ms=self._latency_ms),
        )

    def _choose_action(self, snap: dict, style: str | None = None) -> dict:
        hero = snap["hero"]
        enemies = [e for e in snap["enemies"] if e["hp"] > 0]
        if not enemies:
            return {"type": "defend"}

        target = _select_target(enemies, style)

        usable_skills = [
            s
            for s in snap["skills"]
            if s["mp_cost"] <= hero["mp"] and s["cooldown_remaining"] == 0
        ]
        if not usable_skills:
            return {"type": "basic_attack", "targets": [target["id"]]}

        priorities = {
            "skill_corrupted_focus": _shield_priority(hero, snap, style),
            "skill_hex_seal": _hex_priority(snap, style),
            "skill_shadow_sting": _damage_priority(target, style),
            "skill_tower_brace": _shield_priority(hero, snap, style),
            "skill_ash_glare": _hex_priority(snap, style),
            "skill_ember_punish": _damage_priority(target, style),
            "skill_eclipse_step": _shield_priority(hero, snap, style),
            "skill_hook_break": _execute_priority(target, style),
            "skill_pierce_string": _damage_priority(target, style),
            "skill_sinking_veil": _shield_priority(hero, snap, style),
            "skill_omen_vial": _hex_priority(snap, style),
            "skill_mire_needle": _dot_priority(target, style),
            "skill_crank_charge": _shield_priority(hero, snap, style),
            "skill_burial_engine": _execute_priority(target, style),
            "skill_grave_nail": _dot_priority(target, style),
            "skill_bell_echo": _shield_priority(hero, snap, style),
            "skill_silent_hymn": _hex_priority(snap, style),
            "skill_returning_chime": _execute_priority(target, style),
        }
        usable_skills.sort(
            key=lambda s: (-priorities.get(s["id"], 0.1), s["mp_cost"])
        )
        chosen = usable_skills[0]
        if chosen["target_rule"] == "self":
            return {"type": "cast_skill", "skill_id": chosen["id"], "targets": [hero["id"]]}
        return {
            "type": "cast_skill",
            "skill_id": chosen["id"],
            "targets": [target["id"]],
        }


def _prompt_style(prompt: "PromptContext") -> str | None:
    style = prompt.snapshot.get("prompt_style") or prompt.static_context.get("prompt_style")
    if style:
        return str(style)
    prompt_text = prompt.hero_prompt.lower()
    for candidate in ("aggressive", "guarded", "control", "attrition"):
        if f"{candidate}:" in prompt_text:
            return candidate
    return None


def _select_target(enemies: list[dict], style: str | None) -> dict:
    if style == "control":
        return max(
            enemies,
            key=lambda e: (
                int(e.get("chant_progress", 0) > 0),
                e.get("atb", 0),
                -e.get("hp", 0),
            ),
        )
    if style == "attrition":
        return max(
            enemies,
            key=lambda e: (
                _missing_dot(e),
                e.get("max_hp", e.get("hp", 0)),
                e.get("hp", 0),
            ),
        )
    if style == "guarded":
        return max(enemies, key=lambda e: (e.get("atb", 0), -e.get("hp", 0)))
    return min(enemies, key=lambda e: e["hp"])


def _shield_priority(hero: dict, snap: dict | None = None, style: str | None = None) -> float:
    if hero["hp"] / max(1, hero["max_hp"]) < 0.5:
        return 1.0
    if style == "guarded":
        if _incoming_pressure(snap or {}):
            return 0.98
        if hero["hp"] / max(1, hero["max_hp"]) < 0.8:
            return 0.9
        return 0.55
    if style == "aggressive":
        return 0.8 if hero["hp"] / max(1, hero["max_hp"]) < 0.35 else 0.15
    if style == "control":
        return 0.75 if hero["hp"] / max(1, hero["max_hp"]) < 0.45 else 0.25
    if style == "attrition":
        return 0.7 if hero["hp"] / max(1, hero["max_hp"]) < 0.65 else 0.45
    return 0.3


def _hex_priority(snap: dict, style: str | None = None) -> float:
    enemies = snap["enemies"]
    has_charge = any(e.get("chant_progress", 0) > 0 for e in enemies if e["hp"] > 0)
    biggest = max((e["atb"] for e in enemies if e["hp"] > 0), default=0)
    if style == "control":
        if has_charge:
            return 1.2
        return 1.05 if biggest >= 60 else 0.65
    if style == "guarded":
        return 0.9 if has_charge or biggest >= 85 else 0.45
    if style == "aggressive":
        return 0.55 if has_charge or biggest >= 90 else 0.2
    if style == "attrition":
        return 0.8 if has_charge else 0.45
    if biggest >= 70:
        return 0.95
    return 0.4


def _damage_priority(target: dict, style: str | None = None) -> float:
    if style == "aggressive":
        return 1.05 if target["hp"] <= 45 else 0.9
    if style == "control":
        return 0.55 if target["hp"] <= 30 else 0.45
    if style == "guarded":
        return 0.65 if target["hp"] <= 30 else 0.45
    if style == "attrition":
        return 0.6 if target["hp"] <= 30 else 0.5
    return 0.7 if target["hp"] <= 30 else 0.6


def _execute_priority(target: dict, style: str | None = None) -> float:
    hp_ratio = target["hp"] / max(1, target["max_hp"])
    if style == "aggressive":
        return 1.15 if hp_ratio <= 0.55 else 0.75
    if style == "control":
        return 0.75 if hp_ratio <= 0.35 else 0.45
    return 0.9 if hp_ratio <= 0.45 else 0.55


def _dot_priority(target: dict, style: str | None = None) -> float:
    status_ids = {s.get("id") for s in target.get("statuses", [])}
    if "status_poison" in status_ids or "status_bleed" in status_ids:
        return 0.45
    if style == "attrition":
        return 1.1
    if style == "aggressive":
        return 0.7
    if style == "control":
        return 0.55
    return 0.75


def _incoming_pressure(snap: dict) -> bool:
    for enemy in snap.get("enemies", []):
        if enemy.get("hp", 0) <= 0:
            continue
        if enemy.get("atb", 0) >= 85:
            return True
        if enemy.get("chant_progress", 0) > 0:
            return True
    return False


def _missing_dot(enemy: dict) -> int:
    status_ids = {s.get("id") for s in enemy.get("statuses", [])}
    return 0 if status_ids.intersection({"status_poison", "status_bleed", "status_corruption"}) else 1


def _narrate(snap: dict, action: dict, language: str = DEFAULT_LANGUAGE) -> str:
    hero_name = snap["hero"]["name"]
    if action["type"] == "basic_attack":
        return narration_text("basic_attack", language, hero=hero_name)
    if action["type"] == "cast_skill":
        skill_label = _skill_display(snap, action.get("skill_id", ""))
        return narration_text("cast_skill", language, hero=hero_name, skill=skill_label)
    if action["type"] == "defend":
        return narration_text("defend", language, hero=hero_name)
    return narration_text("hesitate", language, hero=hero_name)


def _skill_display(snap: dict, skill_id: str) -> str:
    for s in snap.get("skills", []):
        if s.get("id") == skill_id:
            return s.get("display_name", skill_id)
    return skill_id


def _analyze(snap: dict, action: dict, language: str = DEFAULT_LANGUAGE) -> str:
    hero_hp = snap['hero']['hp']
    hero_max_hp = max(1, snap["hero"].get("max_hp", hero_hp))
    hero_mp = snap['hero']['mp']
    action_type = action.get('type')
    skill_id = action.get('skill_id', '')
    enemies = [e for e in snap.get("enemies", []) if e.get("hp", 0) > 0]
    target_id = (action.get("targets") or ["-"])[0]
    target = next((e for e in enemies if e.get("id") == target_id), None)
    target_hp = target.get("hp") if target else "-"
    target_atb = target.get("atb") if target else "-"
    ready_skills = [
        s["id"]
        for s in snap.get("skills", [])
        if s.get("mp_cost", 0) <= hero_mp and s.get("cooldown_remaining", 0) == 0
    ]
    if language == "zh":
        return "\n".join(
            [
                f"读取：生命 {hero_hp}/{hero_max_hp}，蓝量 {hero_mp}，可用技能 {', '.join(ready_skills) or '无'}。",
                f"威胁：目标 {target_id}，HP {target_hp}，ATB {target_atb}；优先压低最快行动的敌人。",
                f"决定：{action_type} {skill_id}".strip(),
            ]
        )
    return "\n".join(
        [
            f"Read: hp {hero_hp}/{hero_max_hp}, mp {hero_mp}, ready skills {', '.join(ready_skills) or 'none'}.",
            f"Threat: target {target_id}, hp {target_hp}, atb {target_atb}; pressure the nearest active foe.",
            f"Decision: {action_type} {skill_id}".strip(),
        ]
    )
