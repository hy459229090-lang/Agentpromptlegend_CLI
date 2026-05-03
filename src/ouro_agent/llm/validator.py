"""Parse + validate model output and degrade gracefully.

Goals (REQ-LLM-002):

* Repairable JSON should be repaired and executed.
* Unknown action types or unknown skill IDs degrade to a safe fallback action.
* Completely unreadable output never crashes; it becomes ``defend``.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from ouro_agent.content.schema import ContentBundle
from ouro_agent.engine.models import BattleState
from ouro_agent.llm.actions import (
    ACTION_TYPES,
    FallbackReason,
    HeroAction,
)


@dataclass
class ValidationResult:
    action: HeroAction
    repaired: bool = False
    fallback_reason: FallbackReason = FallbackReason.NONE
    raw_action: dict | None = None
    narration: str = ""
    analysis: str = ""
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_model_output(
    raw_text: str,
    bundle: ContentBundle,
    state: BattleState,
) -> ValidationResult:
    if not raw_text or not raw_text.strip():
        return ValidationResult(
            action=_safe_fallback(state),
            fallback_reason=FallbackReason.EMPTY_RESPONSE,
            notes=["model returned empty text"],
        )

    parsed, repaired, parse_notes = _parse_json_loose(raw_text)
    if parsed is None:
        return ValidationResult(
            action=_safe_fallback(state),
            fallback_reason=FallbackReason.JSON_PARSE_FAILED,
            notes=parse_notes,
        )

    action_raw = parsed.get("action") if isinstance(parsed, dict) else None
    if not isinstance(action_raw, dict):
        return ValidationResult(
            action=_safe_fallback(state),
            repaired=repaired,
            fallback_reason=FallbackReason.MISSING_ACTION,
            raw_action=None,
            narration=str(parsed.get("narration", "") if isinstance(parsed, dict) else ""),
            analysis=str(parsed.get("analysis", "") if isinstance(parsed, dict) else ""),
            notes=parse_notes + ["missing 'action' object"],
        )

    return _validate_action(parsed, action_raw, bundle, state, repaired, parse_notes)


def _validate_action(
    parsed: dict,
    action_raw: dict,
    bundle: ContentBundle,
    state: BattleState,
    repaired: bool,
    parse_notes: list[str],
) -> ValidationResult:
    notes = list(parse_notes)
    fallback_reason = FallbackReason.NONE
    action_type = action_raw.get("type")
    if action_type not in ACTION_TYPES:
        notes.append(f"unknown action type: {action_type!r}")
        return ValidationResult(
            action=_safe_fallback(state),
            repaired=repaired,
            fallback_reason=FallbackReason.UNKNOWN_ACTION_TYPE,
            raw_action=action_raw,
            narration=str(parsed.get("narration", "")),
            analysis=str(parsed.get("analysis", "")),
            confidence=_to_confidence(parsed.get("confidence")),
            notes=notes,
        )

    skill_id = action_raw.get("skill_id")
    if action_type == "cast_skill":
        if not isinstance(skill_id, str) or skill_id not in bundle.skills:
            notes.append(f"unknown skill id: {skill_id!r}")
            return ValidationResult(
                action=HeroAction(type="basic_attack", targets=_first_enemy_tuple(state)),
                repaired=repaired,
                fallback_reason=FallbackReason.UNKNOWN_SKILL,
                raw_action=action_raw,
                narration=str(parsed.get("narration", "")),
                analysis=str(parsed.get("analysis", "")),
                confidence=_to_confidence(parsed.get("confidence")),
                notes=notes,
            )

    targets_raw = action_raw.get("targets") or []
    if not isinstance(targets_raw, list):
        targets_raw = []
        notes.append("targets must be a list; coerced to []")
    targets = tuple(str(t) for t in targets_raw if isinstance(t, str))

    if action_type in {"basic_attack", "cast_skill"} and not targets:
        targets = _first_enemy_tuple(state)
        notes.append("auto-selected default living target")

    action = HeroAction(
        type=str(action_type),
        skill_id=str(skill_id) if isinstance(skill_id, str) else None,
        targets=targets,
        modifier=str(action_raw["modifier"]) if isinstance(action_raw.get("modifier"), str) else None,
    )

    return ValidationResult(
        action=action,
        repaired=repaired,
        fallback_reason=fallback_reason,
        raw_action=action_raw,
        narration=str(parsed.get("narration", "")).strip(),
        analysis=str(parsed.get("analysis", "")).strip(),
        confidence=_to_confidence(parsed.get("confidence")),
        notes=notes,
    )


def _parse_json_loose(text: str) -> tuple[Any | None, bool, list[str]]:
    """Best-effort JSON parse. Returns (value, repaired, notes)."""
    notes: list[str] = []
    try:
        return json.loads(text), False, notes
    except json.JSONDecodeError:
        notes.append("strict json failed; attempting repair")

    match = _JSON_BLOCK_RE.search(text)
    if match:
        candidate = match.group(0)
        candidate = candidate.replace("\n", " ").replace("\r", " ")
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        try:
            return json.loads(candidate), True, notes
        except json.JSONDecodeError as err:
            notes.append(f"repair attempt failed: {err}")
    return None, False, notes


def _safe_fallback(state: BattleState) -> HeroAction:
    living = [e for e in state.enemies if e.hp > 0]
    if not living:
        return HeroAction(type="defend")
    return HeroAction(type="defend")


def _first_enemy_tuple(state: BattleState) -> tuple[str, ...]:
    living = [e for e in state.enemies if e.hp > 0]
    if not living:
        return ()
    return (living[0].id,)


def _to_confidence(value: Any) -> float:
    try:
        f = float(value)
        if 0.0 <= f <= 1.0:
            return f
        return max(0.0, min(1.0, f))
    except (TypeError, ValueError):
        return 0.0
