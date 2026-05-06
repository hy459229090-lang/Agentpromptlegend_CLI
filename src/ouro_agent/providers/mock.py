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
        action = self._choose_action(snap)
        narration = _narrate(snap, action, self._language)
        analysis = _analyze(snap, action)
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

    def _choose_action(self, snap: dict) -> dict:
        hero = snap["hero"]
        enemies = [e for e in snap["enemies"] if e["hp"] > 0]
        if not enemies:
            return {"type": "defend"}

        target = min(enemies, key=lambda e: e["hp"])

        usable_skills = [
            s
            for s in snap["skills"]
            if s["mp_cost"] <= hero["mp"] and s["cooldown_remaining"] == 0
        ]
        if not usable_skills:
            return {"type": "basic_attack", "targets": [target["id"]]}

        priorities = {
            "skill_corrupted_focus": _shield_priority(hero),
            "skill_hex_seal": _hex_priority(snap),
            "skill_shadow_sting": _damage_priority(target),
            "skill_tower_brace": _shield_priority(hero),
            "skill_ash_glare": _hex_priority(snap),
            "skill_ember_punish": _damage_priority(target),
            "skill_eclipse_step": _shield_priority(hero),
            "skill_hook_break": _execute_priority(target),
            "skill_pierce_string": _damage_priority(target),
            "skill_sinking_veil": _shield_priority(hero),
            "skill_omen_vial": _hex_priority(snap),
            "skill_mire_needle": _dot_priority(target),
            "skill_crank_charge": _shield_priority(hero),
            "skill_burial_engine": _execute_priority(target),
            "skill_grave_nail": _dot_priority(target),
            "skill_bell_echo": _shield_priority(hero),
            "skill_silent_hymn": _hex_priority(snap),
            "skill_returning_chime": _execute_priority(target),
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


def _shield_priority(hero: dict) -> float:
    if hero["hp"] / max(1, hero["max_hp"]) < 0.5:
        return 1.0
    return 0.3


def _hex_priority(snap: dict) -> float:
    enemies = snap["enemies"]
    biggest = max((e["atb"] for e in enemies if e["hp"] > 0), default=0)
    if biggest >= 70:
        return 0.95
    return 0.4


def _damage_priority(target: dict) -> float:
    return 0.7 if target["hp"] <= 30 else 0.6


def _execute_priority(target: dict) -> float:
    hp_ratio = target["hp"] / max(1, target["max_hp"])
    return 0.9 if hp_ratio <= 0.45 else 0.55


def _dot_priority(target: dict) -> float:
    status_ids = {s.get("id") for s in target.get("statuses", [])}
    if "status_poison" in status_ids or "status_bleed" in status_ids:
        return 0.45
    return 0.75


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


def _analyze(snap: dict, action: dict) -> str:
    return (
        f"hp={snap['hero']['hp']} mp={snap['hero']['mp']} "
        f"-> {action.get('type')} {action.get('skill_id', '')}"
    ).strip()
