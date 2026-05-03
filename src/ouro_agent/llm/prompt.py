"""Prompt composer.

Produces a compact, model-visible context for one hero turn. The context
exposes only fields the hero is allowed to see (per G05): no hidden codex
text, no enemy AI internals, no design-only damage formulas.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ouro_agent.content.schema import ContentBundle
from ouro_agent.engine.models import BattleState
from ouro_agent.llm.actions import ACTION_SCHEMA_VERSION, ACTION_TYPES


@dataclass(frozen=True)
class PromptContext:
    """The full structured context for one model turn."""
    schema_version: str
    rules_summary: str
    hero_prompt: str
    snapshot: dict[str, Any]
    output_schema: dict[str, Any]
    extras: dict = field(default_factory=dict)

    def system_text(self) -> str:
        """The non-conversational system prompt block."""
        return (
            f"{self.rules_summary}\n\n"
            "Reply with ONE JSON object that matches the output schema below. "
            "Do not wrap it in markdown fences. Do not add commentary outside JSON.\n\n"
            "Output schema:\n"
            f"{json.dumps(self.output_schema, ensure_ascii=False, indent=2)}\n"
        )

    def user_text(self) -> str:
        """User-side block: hero prompt + battle snapshot."""
        return (
            "Hero prompt:\n"
            f"{self.hero_prompt}\n\n"
            "Battle snapshot:\n"
            f"{json.dumps(self.snapshot, ensure_ascii=False, indent=2)}\n"
        )

    def to_chat_messages(self) -> list[dict[str, str]]:
        """OpenAI Chat Completions / OpenAI-compatible message list."""
        return [
            {"role": "system", "content": self.system_text()},
            {"role": "user", "content": self.user_text()},
        ]

    def to_anthropic_payload(self) -> dict[str, Any]:
        """Body fragment for Anthropic Messages API (system + messages)."""
        return {
            "system": self.system_text(),
            "messages": [{"role": "user", "content": self.user_text()}],
        }


_RULES_SUMMARY = (
    "You are an autonomous combat agent inside Ouro Agent. "
    "Pick exactly one structured action per turn. Only valid actions are: "
    + ", ".join(ACTION_TYPES)
    + ". The local engine resolves damage, status, MP and cooldown; "
    "your action proposal does not decide outcomes."
)

_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["action"],
    "properties": {
        "narration": {"type": "string", "description": "what the hero appears to do"},
        "analysis": {"type": "string", "description": "short visible reasoning"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "action": {
            "type": "object",
            "required": ["type"],
            "properties": {
                "type": {"enum": list(ACTION_TYPES)},
                "skill_id": {"type": "string"},
                "targets": {"type": "array", "items": {"type": "string"}},
                "modifier": {"type": "string"},
            },
        },
    },
}


def compose_prompt(
    state: BattleState,
    bundle: ContentBundle,
    hero_prompt_override: str | None = None,
) -> PromptContext:
    hero = state.hero
    lang = state.language
    hero_data = bundle.heroes[hero.id]
    snapshot = {
        "schema_version": ACTION_SCHEMA_VERSION,
        "tick": state.tick,
        "language": lang,
        "hero": {
            "id": hero.id,
            "name": hero.name,
            "class_name": hero.class_name,
            "hp": hero.hp,
            "max_hp": hero.max_hp,
            "mp": hero.mp,
            "max_mp": hero.max_mp,
            "atb": hero.atb,
            "attack": hero.attack,
            "defense": hero.defense,
            "power": hero.power,
            "statuses": [
                {"id": s.id, "stacks": s.stacks, "duration": s.duration}
                for s in hero.statuses
            ],
        },
        "skills": [
            {
                "id": s.id,
                "display_name": s.display_name,
                "mp_cost": s.mp_cost,
                "cooldown_remaining": s.cooldown_remaining,
                "target_rule": s.target_rule,
                "ready": s.is_ready(hero.mp),
            }
            for s in hero.skills
        ],
        "enemies": [
            {
                "id": e.id,
                "name": e.name,
                "hp": e.hp,
                "max_hp": e.max_hp,
                "atb": e.atb,
                "statuses": [
                    {"id": s.id, "stacks": s.stacks, "duration": s.duration}
                    for s in e.statuses
                ],
                "codex": (
                    bundle.enemies[e.id].codex_stage_observed.get(lang)
                    if e.id in bundle.enemies
                    else ""
                ),
            }
            for e in state.enemies
        ],
        "recent_log": list(state.log[-6:]),
    }
    return PromptContext(
        schema_version=ACTION_SCHEMA_VERSION,
        rules_summary=_RULES_SUMMARY,
        hero_prompt=(
            hero_prompt_override
            if hero_prompt_override is not None
            else hero_data.default_prompt.get(lang)
        ),
        snapshot=snapshot,
        output_schema=_OUTPUT_SCHEMA,
    )
