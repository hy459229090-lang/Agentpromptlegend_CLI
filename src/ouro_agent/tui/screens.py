"""ASCII-safe screen renderers.

These functions return plain strings and never mutate combat state, so they
can be snapshot-tested deterministically (REQ-ART-001 / REQ-VAL-001).

Both English (default ASCII-safe) and Chinese surfaces are supported via the
``language`` argument or the language carried on ``BattleState``. CJK widths
are accounted for so that bars and column alignment do not collapse.
"""
from __future__ import annotations

from ouro_agent.art.glyphs import bar
from ouro_agent.content import ContentBundle, HeroData
from ouro_agent.engine.battle import TurnRecord
from ouro_agent.engine.build import ResolvedBuild
from ouro_agent.engine.models import BattleState, Enemy, Hero
from ouro_agent.i18n import DEFAULT_LANGUAGE, label, pad_right


def render_battle_screen(
    state: BattleState,
    last_record: TurnRecord | None,
    *,
    provider_label: str,
    seed: int,
    unicode_mode: bool = False,
    floor_label: str | None = None,
    language: str | None = None,
) -> str:
    lang = language or state.language or DEFAULT_LANGUAGE
    floor = floor_label or label("floor_label_default", lang)
    speed_word = label("speed", lang)
    seed_word = label("seed", lang)
    provider_word = label("provider_label", lang)

    lines: list[str] = []
    lines.append(f"{label('title', lang)} :: {floor}")
    lines.append(
        f"{seed_word}: mvp_a-{seed:03d}        "
        f"{provider_word}: {provider_label}        "
        f"{speed_word}: x1"
    )
    lines.append("")
    lines.append(label("hero", lang))
    lines.extend(_render_hero(state.hero, lang=lang, unicode_mode=unicode_mode))
    lines.append("")
    lines.append(label("enemies", lang))
    if not state.enemies:
        lines.append(label("no_enemies", lang))
    for idx, enemy in enumerate(state.enemies, start=1):
        lines.append(_render_enemy(idx, enemy, lang=lang, unicode_mode=unicode_mode))
    lines.append("")
    lines.append(label("model_turn", lang))
    lines.extend(_render_turn(last_record, lang=lang))
    lines.append("")
    lines.append(label("log", lang))
    if not state.log:
        lines.append(label("no_events", lang))
    for entry in state.log[-6:]:
        lines.append(f"> {entry}")
    return "\n".join(lines)


def render_config_screen(
    redacted: dict[str, str],
    *,
    config_path: str,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    lang = language
    fields = [
        ("config_field_provider", "provider"),
        ("config_field_model", "model"),
        ("config_field_api_key_env", "api_key_env"),
        ("config_field_api_key_value", "api_key_value"),
        ("config_field_base_url", "base_url"),
        ("config_field_api_version", "api_version"),
        ("config_field_timeout", "timeout_seconds"),
        ("config_field_retries", "max_retries"),
        ("config_field_trace_level", "trace_level"),
        ("config_field_unicode_mode", "unicode_mode"),
        ("config_field_language", "language"),
    ]

    label_width = max(len(label(k, lang)) for k, _ in fields)
    rendered_fields = [
        f"{label(k, lang).ljust(label_width)} : {redacted.get(value_key, '')}"
        for k, value_key in fields
    ]

    lines: list[str] = [label("config_title", lang), ""]
    lines.append(label("provider_line_mock", lang))
    lines.append(label("provider_line_openai", lang))
    lines.append(label("provider_line_anthropic", lang))
    lines.append(label("provider_line_compatible", lang))
    lines.append("")
    lines.append(label("config_current", lang))
    lines.extend(rendered_fields)
    lines.append("")
    lines.append(f"{label('config_path', lang)}: {config_path}")
    return "\n".join(lines)


def _render_hero(hero: Hero, *, lang: str, unicode_mode: bool) -> list[str]:
    hp_bar = bar(hero.hp, hero.max_hp, width=10, unicode_mode=unicode_mode)
    mp_bar = bar(hero.mp, hero.max_mp, width=8, unicode_mode=unicode_mode)
    atb_bar = bar(min(hero.atb, 100), 100, width=10, unicode_mode=unicode_mode)
    status = (
        ", ".join(_format_status(s) for s in hero.statuses)
        or label("status_none", lang)
    )
    return [
        f"{hero.short_tag} {hero.name}  {hero.class_name}",
        f"HP {hp_bar} {hero.hp}/{hero.max_hp}   "
        f"MP {mp_bar} {hero.mp}/{hero.max_mp}   "
        f"ATB {atb_bar}",
        f"{label('status_label', lang)}: {status}",
    ]


def _render_enemy(idx: int, enemy: Enemy, *, lang: str, unicode_mode: bool) -> str:
    hp_bar = bar(enemy.hp, enemy.max_hp, width=8, unicode_mode=unicode_mode)
    atb_bar = bar(min(enemy.atb, 100), 100, width=10, unicode_mode=unicode_mode)
    status = ", ".join(_format_status(s) for s in enemy.statuses)
    status_part = f" {status}" if status else ""
    state_tag = label("down", lang) if not enemy.is_alive else ""
    name_field = pad_right(enemy.name, 22)
    return (
        f"{idx}. [{enemy.short_glyph}] {name_field} "
        f"HP {hp_bar} {enemy.hp}/{enemy.max_hp}   "
        f"ATB {atb_bar}{status_part} {state_tag}"
    ).rstrip()


def _render_turn(record: TurnRecord | None, *, lang: str) -> list[str]:
    if record is None:
        return [label("awaiting", lang)]
    if record.side == "enemy":
        action = record.enemy_action or {}
        return [
            label("enemy_actor_acts", lang).format(
                actor_id=record.actor_id,
                kind=action.get("type", "wait"),
            ),
            f"{label('echo_cost', lang)}: 0 {label('tokens_unit', lang)} | "
            f"{label('ritual_time', lang)}: 0ms | "
            f"{label('trace_local', lang)}",
        ]
    judge = record.judge
    validation = record.validation
    narration = (validation.narration if validation else "") or _hero_default_act(
        record, lang
    )
    fallback = (
        validation.fallback_reason.value
        if validation and validation.fallback_reason.value != "none"
        else None
    )
    judge_text = f"{judge.summary}" if judge else label("no_judge", lang)
    judge_marker = (
        label("judge_valid", lang)
        if judge and judge.valid
        else label("judge_fallback", lang)
    )
    fallback_marker = (
        f" | {label('fallback_label', lang)}: {fallback}" if fallback else ""
    )
    action_text = (
        f"{record.action.type if record.action else '?'} "
        + (f"{record.action.skill_id} " if record.action and record.action.skill_id else "")
        + (
            f"-> {','.join(record.action.targets)}"
            if record.action and record.action.targets
            else ""
        )
    )
    return [
        narration,
        f"{label('action_label', lang)}: {action_text}",
        f"{label('judge_label', lang)}: {judge_marker} | {judge_text}{fallback_marker}",
        f"{label('echo_cost', lang)}: {record.usage_total_tokens} {label('tokens_unit', lang)} | "
        f"{label('ritual_time', lang)}: {record.usage_latency_ms}ms | "
        f"{label('trace_local', lang)}",
    ]


def _hero_default_act(record: TurnRecord, lang: str) -> str:
    return label("awaiting", lang)


def _format_status(status) -> str:
    return f"{status.id}({status.stacks})"


def render_hero_list(
    bundle: ContentBundle, *, language: str = DEFAULT_LANGUAGE
) -> str:
    lang = language
    lines: list[str] = [label("hero_list_title", lang), ""]
    for idx, hero in enumerate(bundle.heroes.values(), start=1):
        name = hero.display_name.get(lang)
        cls = hero.class_name.get(lang)
        tags = " / ".join(hero.tags) or "-"
        lines.append(f"[{idx}] {name}  {hero.short_tag}  {cls}    {tags}")
        desc = hero.description.get(lang)
        if desc:
            lines.append(f"    {desc}")
        lines.append(f"    id: {hero.id}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_hero_card(
    hero: HeroData,
    bundle: ContentBundle,
    build: ResolvedBuild,
    *,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    lang = language
    name = hero.display_name.get(lang)
    cls = hero.class_name.get(lang)
    tags = " / ".join(build.tags) or label("hero_card_none", lang)

    stats = (
        f"HP {build.hp}  MP {build.mp}  SPD {build.speed}  "
        f"ATK {build.attack}  DEF {build.defense}  POW {build.power}"
    )

    skills_lines: list[str] = []
    for sid in hero.skills:
        skill = bundle.get_skill(sid)
        skills_lines.append(
            f"  - {skill.display_name.get(lang)} ({skill.id}) "
            f"MP {skill.mp_cost}, cd {skill.cooldown}"
        )
        desc = skill.visible_description.get(lang)
        if desc:
            skills_lines.append(f"      {desc}")

    items_lines = [
        f"  - {item.display_name.get(lang)} [{item.tier}] "
        f"({', '.join(item.tags) or '-'})"
        for item in build.items
    ] or [f"  {label('hero_card_none', lang)}"]
    affix_lines = [
        f"  - {affix.display_name.get(lang)} ({', '.join(affix.tags) or '-'})"
        for affix in build.affixes
    ] or [f"  {label('hero_card_none', lang)}"]
    resonance_lines = [
        f"  - {res.display_name.get(lang)} ({', '.join(res.required_tag_counts) or '-'})"
        for res in build.resonances
    ] or [f"  {label('hero_card_none', lang)}"]

    avatar = list(hero.avatar_ascii) or [""]
    header = f"{label('hero_card_title', lang)} :: {name} {hero.short_tag}"
    lines: list[str] = [header, ""]
    lines.extend(avatar)
    lines.append("")
    lines.append(f"{label('hero_card_class', lang)}: {cls}")
    lines.append(f"{label('hero_card_tags', lang)}: {tags}")
    lines.append(f"{label('hero_card_stats', lang)}: {stats}")
    lines.append("")
    lines.append(label("hero_card_skills", lang))
    lines.extend(skills_lines)
    lines.append("")
    lines.append(label("hero_card_items", lang))
    lines.extend(items_lines)
    lines.append(label("hero_card_affixes", lang))
    lines.extend(affix_lines)
    lines.append(label("hero_card_resonances", lang))
    lines.extend(resonance_lines)
    lines.append("")
    lines.append(label("hero_card_prompt", lang) + ":")
    for ln in hero.default_prompt.get(lang).splitlines():
        lines.append(f"  {ln}")
    return "\n".join(lines)
