"""Prompt composer.

Produces a compact, model-visible context for one hero turn. The context
exposes only fields the hero is allowed to see (per G05): no hidden codex
text, no enemy AI internals, no design-only damage formulas.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ouro_agent.content.schema import ContentBundle, CodexStage
from ouro_agent.engine.build import ResolvedBuild, resolve_build
from ouro_agent.engine.models import BattleState
from ouro_agent.llm.actions import ACTION_SCHEMA_VERSION, ACTION_TYPES
from ouro_agent.sessions import BattleLLMSession, hash_static_context
from ouro_agent.sessions.codex import CodexProgress


@dataclass(frozen=True)
class PromptContext:
    """The full structured context for one model turn."""
    schema_version: str
    rules_summary: str
    hero_prompt: str
    snapshot: dict[str, Any]
    output_schema: dict[str, Any]
    battle_session_id: str = "be_local"
    static_context_hash: str = ""
    delta_context_id: str = "delta_local"
    static_context: dict[str, Any] = field(default_factory=dict)
    delta_context: dict[str, Any] = field(default_factory=dict)
    extras: dict = field(default_factory=dict)

    def system_text(self) -> str:
        """The non-conversational system prompt block."""
        return (
            f"{self.rules_summary}\n\n"
            "Reply with ONE JSON object that matches the output schema below. "
            "Do not wrap it in markdown fences. Do not add commentary outside JSON.\n\n"
            "Output schema:\n"
            f"{json.dumps(self.output_schema, ensure_ascii=False, indent=2)}\n\n"
            "Static battle context:\n"
            f"{json.dumps(self.static_context, ensure_ascii=False, indent=2)}\n"
        )

    def user_text(self) -> str:
        """User-side block: hero prompt + battle snapshot."""
        return (
            "Hero prompt:\n"
            f"{self.hero_prompt}\n\n"
            f"Battle Echo: {self.battle_session_id}\n"
            f"Sealed Echo: {self.static_context_hash}\n"
            f"Delta Context: {self.delta_context_id}\n\n"
            "Battle snapshot / turn delta:\n"
            f"{json.dumps(self.delta_context, ensure_ascii=False, indent=2)}\n"
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


PROMPT_STYLE_TEMPLATES: dict[str, dict[str, str]] = {
    "aggressive": {
        "en": "Aggressive: prefer decisive skill casts and finishing low-HP enemies.",
        "zh": "激进：优先释放关键技能并收割低血敌人。",
    },
    "guarded": {
        "en": "Guarded: keep HP safe, defend or shield before risky trades.",
        "zh": "稳守：保持 HP 安全，危险交换前优先防御或护盾。",
    },
    "control": {
        "en": "Control: interrupt high-ATB or chanting enemies before dealing damage.",
        "zh": "控制：先打断高 ATB 或吟唱敌人，再追求伤害。",
    },
    "attrition": {
        "en": "Attrition: keep damage-over-time and defensive value rolling.",
        "zh": "消耗：维持持续伤害与防御收益，稳步压低敌人。",
    },
}


def supported_prompt_styles() -> tuple[str, ...]:
    return tuple(PROMPT_STYLE_TEMPLATES)


def prompt_style_text(style: str, language: str) -> str:
    if style not in PROMPT_STYLE_TEMPLATES:
        raise ValueError(
            "prompt style must be one of "
            + ", ".join(PROMPT_STYLE_TEMPLATES)
            + f"; got {style!r}"
        )
    return PROMPT_STYLE_TEMPLATES[style].get(language) or PROMPT_STYLE_TEMPLATES[style]["en"]


def apply_prompt_style(base_prompt: str, style: str | None, language: str) -> str:
    if not style:
        return base_prompt
    return base_prompt.rstrip() + "\n\nStrategy template:\n" + prompt_style_text(style, language)


def compose_prompt(
    state: BattleState,
    bundle: ContentBundle,
    hero_prompt_override: str | None = None,
    battle_session: BattleLLMSession | None = None,
    prompt_style: str | None = None,
    build: ResolvedBuild | None = None,
) -> PromptContext:
    lang = state.language
    hero_data = bundle.heroes[state.hero.id]
    base_prompt = hero_data.default_prompt.get(lang)
    effective_prompt = (
        hero_prompt_override
        if hero_prompt_override is not None
        else apply_prompt_style(base_prompt, prompt_style, lang)
    )
    static_context = (
        battle_session.static_context
        if battle_session is not None
        else compose_static_context(
            state,
            bundle,
            effective_prompt,
            prompt_style=prompt_style,
            build=build,
        )
    )
    static_context_hash = (
        battle_session.static_context_hash
        if battle_session is not None
        else hash_static_context(static_context)
    )
    delta_context_id = (
        battle_session.claim_delta_context_id()
        if battle_session is not None
        else "delta_local_0001"
    )
    delta_context = compose_turn_delta(state, bundle)
    snapshot = compose_snapshot(state, bundle, prompt_style=prompt_style)
    return PromptContext(
        schema_version=ACTION_SCHEMA_VERSION,
        rules_summary=_RULES_SUMMARY,
        hero_prompt=effective_prompt,
        snapshot=snapshot,
        output_schema=_OUTPUT_SCHEMA,
        battle_session_id=(
            battle_session.battle_session_id if battle_session is not None else "be_local"
        ),
        static_context_hash=static_context_hash,
        delta_context_id=delta_context_id,
        static_context=static_context,
        delta_context=delta_context,
    )


def compose_static_context(
    state: BattleState,
    bundle: ContentBundle,
    hero_prompt_override: str | None = None,
    codex_progress: CodexProgress | None = None,
    prompt_style: str | None = None,
    build: ResolvedBuild | None = None,
) -> dict[str, Any]:
    hero = state.hero
    lang = state.language
    hero_data = bundle.heroes[hero.id]
    effective_prompt = (
        hero_prompt_override
        if hero_prompt_override is not None
        else hero_data.default_prompt.get(lang)
    )
    resolved_build = build or resolve_build(hero_data, bundle)
    enemies = []
    for e in state.enemies:
        enemy_data = bundle.enemies.get(e.id)
        if enemy_data is None:
            codex_text = ""
        else:
            if codex_progress is not None and enemy_data.family_id:
                stage = codex_progress.get_stage(enemy_data.family_id, enemy_data.tier)
            else:
                stage = CodexStage.UNKNOWN
            codex_text = enemy_data.codex_text_for_stage(stage, lang)

        enemies.append({
            "id": e.id,
            "name": e.name,
            "max_hp": e.max_hp,
            "tier": e.tier,
            "codex": codex_text,
        })

    return {
        "schema_version": ACTION_SCHEMA_VERSION,
        "language": lang,
        "prompt_style": prompt_style,
        "prompt_template": (
            prompt_style_text(prompt_style, lang) if prompt_style else None
        ),
        "rules": {
            "valid_actions": list(ACTION_TYPES),
            "local_judge": "damage, status, MP, cooldown and victory are resolved locally",
        },
        "hero": {
            "id": hero.id,
            "name": hero.name,
            "class_name": hero.class_name,
            "prompt": effective_prompt,
            "max_hp": hero.max_hp,
            "max_mp": hero.max_mp,
            "attack": hero.attack,
            "defense": hero.defense,
            "power": hero.power,
        },
        "build": _build_context(resolved_build, bundle, lang),
        "skills": [
            {
                "id": s.id,
                "display_name": s.display_name,
                "mp_cost": s.mp_cost,
                "target_rule": s.target_rule,
            }
            for s in hero.skills
        ],
        "enemies": enemies,
    }


def _build_context(
    build: ResolvedBuild,
    bundle: ContentBundle,
    language: str,
) -> dict[str, Any]:
    progress = build.calculate_progress(bundle)
    return {
        "archetype": build.archetype(language),
        "risk_level": build.risk_level(),
        "stage": progress.stage.value,
        "stage_badge": progress.stage.badge,
        "core_tags": progress.core_tags,
        "tags": list(build.tags),
        "items": [
            {
                "id": item.id,
                "name": item.display_name.get(language),
                "tier": item.tier,
                "tags": list(item.tags),
            }
            for item in build.items
        ],
        "affixes": [
            {
                "id": affix.id,
                "name": affix.display_name.get(language),
                "tags": list(affix.tags),
            }
            for affix in build.affixes
        ],
        "resonances": [
            {
                "id": resonance.id,
                "name": resonance.display_name.get(language),
            }
            for resonance in build.resonances
        ],
        "strategy": build.strategy_lines(language),
        "passive_tags": list(build.passive_tags),
    }


def compose_turn_delta(state: BattleState, bundle: ContentBundle) -> dict[str, Any]:
    hero = state.hero
    return {
        "tick": state.tick,
        "hero_delta": {
            "hp": hero.hp,
            "mp": hero.mp,
            "atb": hero.atb,
            "statuses": [
                {"id": s.id, "stacks": s.stacks, "duration": s.duration}
                for s in hero.statuses
            ],
        },
        "skill_delta": [
            {
                "id": s.id,
                "cooldown_remaining": s.cooldown_remaining,
                "ready": s.is_ready(hero.mp),
            }
            for s in hero.skills
        ],
        "enemy_delta": [
            {
                "id": e.id,
                "hp": e.hp,
                "atb": e.atb,
                "tier": e.tier,
                "chant_progress": e.chant_progress,
                "chant_charge_turns": e.chant_charge_turns,
                "statuses": [
                    {"id": s.id, "stacks": s.stacks, "duration": s.duration}
                    for s in e.statuses
                ],
            }
            for e in state.enemies
        ],
        "recent_log": list(state.log[-6:]),
    }


def compose_snapshot(
    state: BattleState,
    bundle: ContentBundle,
    *,
    prompt_style: str | None = None,
) -> dict[str, Any]:
    """Legacy full snapshot kept for mock/provider compatibility."""
    static_context = compose_static_context(state, bundle, prompt_style=prompt_style)
    delta_context = compose_turn_delta(state, bundle)
    hero = dict(static_context["hero"])
    hero.update(delta_context["hero_delta"])

    skill_delta_by_id = {s["id"]: s for s in delta_context["skill_delta"]}
    skills = []
    for skill in static_context["skills"]:
        merged = dict(skill)
        merged.update(skill_delta_by_id.get(skill["id"], {}))
        skills.append(merged)

    enemy_delta_by_id = {e["id"]: e for e in delta_context["enemy_delta"]}
    enemies = []
    for enemy in static_context["enemies"]:
        merged = dict(enemy)
        merged.update(enemy_delta_by_id.get(enemy["id"], {}))
        enemies.append(merged)

    return {
        "schema_version": static_context["schema_version"],
        "tick": delta_context["tick"],
        "language": static_context["language"],
        "prompt_style": prompt_style,
        "prompt_template": static_context.get("prompt_template"),
        "hero": hero,
        "skills": skills,
        "enemies": enemies,
        "recent_log": delta_context["recent_log"],
    }
