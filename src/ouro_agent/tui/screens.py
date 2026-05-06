"""ASCII-safe screen renderers.

These functions return plain strings and never mutate combat state, so they
can be snapshot-tested deterministically (REQ-ART-001 / REQ-VAL-001).

Both English (default ASCII-safe) and Chinese surfaces are supported via the
``language`` argument or the language carried on ``BattleState``. CJK widths
are accounted for so that bars and column alignment do not collapse.
"""
from __future__ import annotations

from collections import Counter
import os

from ouro_agent.art.glyphs import bar
from ouro_agent.content import ContentBundle, HeroData
from ouro_agent.config import OuroConfig, redacted_view
from ouro_agent.engine.battle import TurnRecord
from ouro_agent.engine.build import ResolvedBuild
from ouro_agent.engine.models import BattleState, Enemy, Hero
from ouro_agent.i18n import DEFAULT_LANGUAGE, label, pad_right
from ouro_agent.llm.prompt import PROMPT_STYLE_TEMPLATES, prompt_style_text


def render_battle_screen(
    state: BattleState,
    last_record: TurnRecord | None,
    *,
    provider_label: str,
    seed: int,
    unicode_mode: bool = False,
    floor_label: str | None = None,
    language: str | None = None,
    width: int = 100,
) -> str:
    lang = language or state.language or DEFAULT_LANGUAGE
    floor = floor_label or label("floor_label_default", lang)
    speed_word = label("speed", lang)
    seed_word = label("seed", lang)
    provider_word = label("provider_label", lang)

    lines: list[str] = []
    lines.append(f"{label('title', lang)} :: {floor}                         AUTO WATCH")
    lines.append("| ash candles flicker under a broken arch |")
    lines.append(
        f"{seed_word}: mvp_a-{seed:03d}        "
        f"{provider_word}: {provider_label}        "
        f"{speed_word}: x1"
    )
    lines.append("")
    lines.append(f"{label('hero', lang)} VS {label('enemies', lang)}")
    compact = width <= 88
    if compact:
        lines.extend(
            _render_compact_duel_panel(
                state,
                last_record,
                lang=lang,
                unicode_mode=unicode_mode,
            )
        )
    else:
        lines.extend(
            _render_duel_panel(
                state,
                last_record,
                lang=lang,
                unicode_mode=unicode_mode,
            )
        )
    lines.append("")
    if not compact:
        lines.extend(_render_build_line(state.hero))
    lines.append("")
    lines.extend(_render_session_panel(last_record, provider_label=provider_label))
    lines.append("")
    lines.append("ACTION STRIP  select -> windup -> effect lane -> impact -> judge")
    lines.append(label("model_turn", lang))
    lines.extend(_render_turn(last_record, lang=lang))
    lines.append("")
    lines.append(label("log", lang))
    if not state.log:
        lines.append(label("no_events", lang))
    for entry in state.log[-6:]:
        lines.append(f"> {entry}")
    if compact:
        lines = [line[:width] for line in lines]
    return "\n".join(lines)


def _render_compact_duel_panel(
    state: BattleState,
    last_record: TurnRecord | None,
    *,
    lang: str,
    unicode_mode: bool,
) -> list[str]:
    target = _screen_target(state, last_record)
    hero_sprite = _hero_sprite(state.hero, last_record)[:3]
    enemy_sprite = _enemy_sprite(target, last_record)[:3] if target else ["", "", ""]
    effect = _effect_lane(last_record)
    effect_text = next((line.strip() for line in effect if line.strip()), "...")

    left_name = f"{state.hero.short_tag} {state.hero.name}"[:28]
    right_name = (
        f"[{target.short_glyph}] {target.name}"[:28]
        if target is not None
        else label("no_enemies", lang)[:28]
    )
    lines = [f"{pad_right(left_name, 34)} {right_name}"]
    for idx in range(3):
        left = pad_right(hero_sprite[idx][:20], 20)
        right = enemy_sprite[idx][:22]
        mid = effect_text if idx == 1 else ""
        lines.append(f"{left} {pad_right(mid[:14], 14)} {right}".rstrip())
    lines.extend(_hero_hud(state.hero, lang=lang, unicode_mode=unicode_mode))
    if target is not None:
        lines.extend(_enemy_hud(target, lang=lang, unicode_mode=unicode_mode))
        enemy_statuses = _status_groups(target.statuses, lang=lang)
        lines.extend(line for line in enemy_statuses if "Status: -" not in line)
    hero_statuses = _status_groups(state.hero.statuses, lang=lang)
    lines.extend(line for line in hero_statuses if "Status: -" not in line)
    weapon, build = _hero_icons(state.hero)
    lines.append(f"{weapon[:28]}  BUILD {build[:32]}")
    return [line[:80] for line in lines]


def _render_duel_panel(
    state: BattleState,
    last_record: TurnRecord | None,
    *,
    lang: str,
    unicode_mode: bool,
) -> list[str]:
    target = _screen_target(state, last_record)
    effect = _effect_lane(last_record)
    hero_sprite = _hero_sprite(state.hero, last_record)
    enemy_sprite = _enemy_sprite(target, last_record) if target else ["", "", "", ""]
    hero_lines = _actor_card_lines(
        title=f"{state.hero.short_tag} {state.hero.name}",
        sprite=hero_sprite,
        hud=_hero_hud(state.hero, lang=lang, unicode_mode=unicode_mode),
        statuses=_status_groups(state.hero.statuses, lang=lang),
    )
    enemy_lines = _actor_card_lines(
        title=(
            f"[{target.short_glyph}] {target.name}"
            if target is not None
            else label("no_enemies", lang)
        ),
        sprite=enemy_sprite,
        hud=(
            _enemy_hud(target, lang=lang, unicode_mode=unicode_mode)
            if target is not None
            else []
        ),
        statuses=_status_groups(target.statuses, lang=lang) if target is not None else [],
    )
    height = max(len(hero_lines), len(enemy_lines), len(effect))
    hero_lines.extend([""] * (height - len(hero_lines)))
    enemy_lines.extend([""] * (height - len(enemy_lines)))
    effect.extend([""] * (height - len(effect)))

    lines = [
        "+---------------- HERO ----------------+      +-------------- ENEMY --------------+"
    ]
    for idx in range(height):
        left = pad_right(hero_lines[idx][:36], 36)
        mid = pad_right(effect[idx][:18], 18)
        right = pad_right(enemy_lines[idx][:35], 35)
        lines.append(f"| {left} | {mid}| {right} |")
    lines.append("+--------------------------------------+      +-----------------------------------+")
    return lines


def _actor_card_lines(
    *,
    title: str,
    sprite: list[str],
    hud: list[str],
    statuses: list[str],
) -> list[str]:
    lines = [title]
    lines.extend(sprite[:5])
    lines.extend(hud)
    lines.extend(statuses)
    return lines


def _screen_target(state: BattleState, record: TurnRecord | None) -> Enemy | None:
    if record is not None and record.action is not None and record.action.targets:
        for enemy in state.enemies:
            if enemy.id in record.action.targets:
                return enemy
    if record is not None and record.side == "enemy":
        for enemy in state.enemies:
            if enemy.id == record.actor_id:
                return enemy
    alive = state.alive_enemies()
    if alive:
        return alive[0]
    return state.enemies[0] if state.enemies else None


def _hero_hud(hero: Hero, *, lang: str, unicode_mode: bool) -> list[str]:
    hp_bar = bar(hero.hp, hero.max_hp, width=8, unicode_mode=unicode_mode)
    mp_bar = bar(hero.mp, hero.max_mp, width=6, unicode_mode=unicode_mode)
    atb_bar = bar(min(hero.atb, 100), 100, width=6, unicode_mode=unicode_mode)
    return [
        f"HP {hp_bar} {hero.hp}/{hero.max_hp}",
        f"MP {mp_bar} {hero.mp}/{hero.max_mp}  ATB {atb_bar}",
    ]


def _enemy_hud(enemy: Enemy, *, lang: str, unicode_mode: bool) -> list[str]:
    hp_bar = bar(enemy.hp, enemy.max_hp, width=8, unicode_mode=unicode_mode)
    atb_bar = bar(min(enemy.atb, 100), 100, width=6, unicode_mode=unicode_mode)
    down = f" {label('down', lang)}" if not enemy.is_alive else ""
    charge = (
        f" charge {enemy.chant_progress}/{enemy.chant_charge_turns}"
        if enemy.chant_charge_turns
        else ""
    )
    return [
        f"HP {hp_bar} {enemy.hp}/{enemy.max_hp}{down}",
        f"ATB {atb_bar}{charge}",
    ]


def _status_groups(statuses: list, *, lang: str) -> list[str]:
    buffs = [_format_status(s) for s in statuses if _status_kind(s.id) == "BUFF"]
    debuffs = [_format_status(s) for s in statuses if _status_kind(s.id) == "DEBUFF"]
    lines = []
    if buffs:
        lines.append("BUFF   : " + ", ".join(buffs[:4]))
    if debuffs:
        lines.append("DEBUFF : " + ", ".join(debuffs[:4]))
    if not lines:
        lines.append(f"{label('status_label', lang)}: {label('status_none', lang)}")
    return lines


def _status_kind(status_id: str) -> str:
    if status_id in {"status_shield", "status_focus", "status_haste", "status_guard"}:
        return "BUFF"
    return "DEBUFF"


def _render_build_line(hero: Hero) -> list[str]:
    weapon, build = _hero_icons(hero)
    return [
        f"WEAPON {weapon}        BUILD {build}",
        "NEXT PICK: control affix / silence relic       NEED: control +1 for HIGH ROLL",
    ]


def _hero_icons(hero: Hero) -> tuple[str, str]:
    by_tag = {
        "[CNDL]": ("[W:STF] c==* Black Candle Staff", "[ONLINE] shadow 3/3 control 2/3"),
        "[SHLD]": ("[W:SHD] [#] Warden Aegis", "[PAIR] guard 2/3 shield 2/3"),
        "[XBOW]": ("[W:XBW] ==> Severed String", "[PAIR] bleed 2/3 execute 1/2"),
        "[VENM]": ("[W:VIL] (v) Omen Vial", "[SEED] poison 2/3 omen 1/2"),
        "[GEAR]": ("[W:GER] [o] Burial Crank", "[SEED] gear 2/3 trap 1/2"),
        "[ECHO]": ("[W:BEL] )o( Cracked Bell", "[SEED] echo 2/3 cleanse 1/2"),
    }
    return by_tag.get(hero.short_tag, ("[W:???] unknown", "[SEED] tags pending"))


def _render_session_panel(
    record: TurnRecord | None,
    *,
    provider_label: str,
) -> list[str]:
    battle_echo = record.battle_session_id if record and record.battle_session_id else "-"
    sealed = record.static_context_hash if record and record.static_context_hash else "-"
    fresh = record.delta_context_id if record and record.delta_context_id else "-"
    tokens = record.usage_total_tokens if record else 0
    latency = record.usage_latency_ms if record else 0
    return [
        "MODEL SESSION",
        f"Battle Echo: {battle_echo}   Provider: {provider_label}   Sealed Echo: {sealed}",
        f"Fresh Echo: {fresh}   Echo Cost: {tokens} tokens   Ritual Time: {latency}ms",
    ]


def _effect_lane(record: TurnRecord | None) -> list[str]:
    if record is None:
        return ["", "     ...", "", ""]
    if record.side == "enemy":
        kind = (record.enemy_action or {}).get("type", "attack")
        glyph = "<== chant" if kind == "chant_release" else "<== strike"
        return ["", glyph, "   impact", ""]
    if record.action and record.action.type == "cast_skill":
        skill = record.action.skill_id or ""
        if "hex" in skill:
            return ["", "-- seal -->", "   break", ""]
        if "sting" in skill:
            return ["", "-- sting ->", f"   {record.judge.damage if record.judge else 0} dmg", ""]
        return ["", "-- focus ->", "   ward", ""]
    if record.action and record.action.type == "basic_attack":
        return ["", "-- strike >", f"   {record.judge.damage if record.judge else 0} dmg", ""]
    return ["", "   guard", "", ""]


def _hero_sprite(hero: Hero, record: TurnRecord | None) -> list[str]:
    state = _actor_pose(hero.id, record)
    sprites = {
        "hero_shadow_apprentice": {
            "idle": ["  .^.", " /|c|\\", "  / \\", " candle low"],
            "cast": ["  .^.", " /|c|==*", "  / \\", " candle raised"],
            "hit": ["  .x.", " /|c", "  /\\", " flame bends"],
            "low": ["  .^.", " /|c|\\", "  / \\", " candle guttering"],
        },
        "hero_ash_guardian": {
            "idle": ["   O", "  /#\\", "  / \\", " shield set"],
            "cast": ["   O", "  [#]", "  / \\", " guard raised"],
            "hit": ["   o", "  /#\\!", "  / \\", " ash cracks"],
            "low": ["   o", "  [#]", "  / \\", " shield low"],
        },
        "hero_broken_string_hunter": {
            "idle": ["   o", "  /|\\", "  /->", " string drawn"],
            "cast": ["   o", "  /|\\", "  /==>", " bolt loosed"],
            "hit": ["   x", "  /|", "  /\\", " string snaps"],
            "low": ["   o", "  /|", "  /->", " breathing hard"],
        },
        "hero_mire_oracle": {
            "idle": ["  .-.", " (v v)", " /|~|\\", " vial low"],
            "cast": ["  .-.", " (v v)==", " /| |\\", " vial cracked"],
            "hit": ["  .x.", " (v v)", " /|", " veil torn"],
            "low": ["  .-.", " (v v)", " /|~", " mire rising"],
        },
        "hero_gravewright": {
            "idle": ["  [o]", " /|n|\\", "  / \\", " crate set"],
            "cast": ["  [o]", " /|n|==", "  / \\", " crank turns"],
            "hit": ["  [x]", " /|n|!", "  / \\", " gears skip"],
            "low": ["  [o]", " /|n|", "  / \\", " crate smoking"],
        },
        "hero_echo_exile": {
            "idle": ["  o)o", " /| |\\", "  / \\", " bell quiet"],
            "cast": ["  o)o==", " /| |\\", "  / \\", " bell rings"],
            "hit": ["  x)o", " /| |", "  /\\", " echo cracks"],
            "low": ["  o)o", " /| |", "  / \\", " hymn thin"],
        },
    }
    if hero.hp / max(1, hero.max_hp) < 0.3:
        state = "low"
    return sprites.get(hero.id, {}).get(state, sprites["hero_shadow_apprentice"]["idle"])


def _enemy_sprite(enemy: Enemy, record: TurnRecord | None) -> list[str]:
    state = _actor_pose(enemy.id, record)
    if not enemy.is_alive:
        state = "death"
    sprites = {
        "c": {
            "idle": ["  (c)", "  /|\\", "  / \\", " hungry"],
            "cast": ["  (c)", "  /|\\", "  / \\", " knife lifted"],
            "hit": ["  (x)", "  /|!", "  / \\", " staggered"],
            "death": ["   .", "  /_\\", "  ash", ""],
        },
        "k": {
            "idle": ["  (k)", " /|w|\\", "  / \\", " chanting"],
            "cast": ["  (k*", " /|w|\\", "  / \\", " wick bright"],
            "hit": ["  (k)", " /|w|!", "  / \\", " chant bent"],
            "death": ["   .", "  /_\\", " wick ash", ""],
        },
    }
    return sprites.get(enemy.short_glyph, sprites["c"]).get(state, sprites["c"]["idle"])


def _actor_pose(actor_id: str, record: TurnRecord | None) -> str:
    if record is None:
        return "idle"
    if record.actor_id == actor_id:
        return "cast"
    if record.action and actor_id in record.action.targets:
        return "hit"
    return "idle"


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


def render_main_menu(
    config: OuroConfig,
    *,
    config_path: str,
    recent_trace: str | None = None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    lang = language
    view = redacted_view(config, language=lang)
    key_state = "mock-ready"
    if config.provider != "mock":
        key_state = (
            f"{config.api_key_env}: set"
            if config.api_key_env and os.environ.get(config.api_key_env)
            else f"{config.api_key_env or '(unset)'}: missing"
        )
    visual = "unicode" if config.unicode_mode else "ascii"
    trace = recent_trace or "-"
    lines = [
        "OURO AGENT :: PROMPT LEGEND",
        "",
        "STATUS",
        f"Provider : {view['provider']}    Model: {view['model']}    Key: {key_state}",
        f"Language : {config.language}      Visual: {visual}      Trace: {trace}",
        f"Config   : {config_path}",
        "",
        "ENTRIES",
        "[1] New Run        ouro play --mock --no-animation",
        "[2] Hero Card      ouro list-heroes / ouro hero-card <hero_id>",
        "[3] Prompt Style   ouro prompt-templates",
        "[4] Configure      ouro config setup",
        "[5] Replay         ouro replay <trace>  (locked)",
        "[q] Quit",
    ]
    return "\n".join(lines)


def render_prompt_templates(*, language: str = DEFAULT_LANGUAGE) -> str:
    lines = ["PROMPT STRATEGY TEMPLATES", ""]
    for name, localized in PROMPT_STYLE_TEMPLATES.items():
        lines.append(f"[{name}] {localized.get(language) or localized['en']}")
    lines.append("")
    lines.append("Use: ouro play --mock --prompt-style control")
    return "\n".join(lines)


def render_battle_report(
    state: BattleState,
    records: list[TurnRecord],
    *,
    language: str | None = None,
) -> str:
    lang = language or state.language or DEFAULT_LANGUAGE
    hero_records = [r for r in records if r.side == "hero"]
    enemy_records = [r for r in records if r.side == "enemy"]
    action_counts = Counter(
        r.action.type for r in hero_records if r.action is not None
    )
    skill_counts = Counter(
        r.judge.skill_id
        for r in hero_records
        if r.judge is not None and r.judge.skill_id is not None
    )
    damage_dealt = sum(r.judge.damage for r in hero_records if r.judge is not None)
    damage_taken = sum(
        int(event.payload.get("damage", 0))
        for event in state.events
        if event.kind == "enemy_attack"
    )
    fallback_count = sum(
        1
        for r in hero_records
        if r.validation is not None and r.validation.fallback_reason.value != "none"
    )
    basic = action_counts.get("basic_attack", 0)
    skill_total = action_counts.get("cast_skill", 0)
    ratio = f"{basic}:{skill_total}"

    if skill_counts:
        skill_line = ", ".join(f"{sid} x{count}" for sid, count in skill_counts.items())
    else:
        skill_line = label("battle_report_none", lang)
    if action_counts:
        action_line = ", ".join(
            f"{kind} x{count}" for kind, count in sorted(action_counts.items())
        )
    else:
        action_line = label("battle_report_none", lang)

    result_label_key = {
        "victory": "result_victory",
        "defeat": "result_defeat",
        "timeout": "result_timeout",
        "ongoing": "result_ongoing",
    }.get(state.result, "result_ongoing")

    lines = [label("battle_report_title", lang), ""]
    lines.append(f"{label('result', lang)}: {label(result_label_key, lang)}")
    lines.append(
        f"{label('battle_report_duration', lang)}: "
        f"{state.tick} ticks / {len(hero_records)} hero turns / "
        f"{len(enemy_records)} enemy turns"
    )
    lines.append(f"{label('battle_report_actions', lang)}: {action_line}")
    lines.append(f"{label('battle_report_skills', lang)}: {skill_line}")
    lines.append(f"{label('battle_report_basic_skill_ratio', lang)}: {ratio}")
    lines.append(f"{label('battle_report_damage_dealt', lang)}: {damage_dealt}")
    lines.append(f"{label('battle_report_damage_taken', lang)}: {damage_taken}")
    lines.append(f"{label('battle_report_fallbacks', lang)}: {fallback_count}")
    if state.result == "defeat":
        lines.append(
            f"{label('battle_report_death_reason', lang)}: "
            f"{state.log[-1] if state.log else label('battle_report_unknown', lang)}"
        )
    lines.append(
        f"{label('battle_report_build_note', lang)}: "
        f"{label('battle_report_build_note_value', lang)}"
    )
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
        build = _safe_resolve_build(hero, bundle)
        name = hero.display_name.get(lang)
        cls = hero.class_name.get(lang)
        tags = " / ".join(hero.tags) or "-"
        weapon = (
            build.items[0].display_name.get(lang)
            if build and build.items
            else _hero_card_icons(hero.id)[0]
        )
        build_name = _build_archetype(hero.id, lang)
        risk = _hero_risk(hero.id)
        lines.append(f"[{idx}] {name}  {hero.short_tag}  {cls}")
        lines.append(f"    Build: {build_name}    Weapon: {weapon}    Risk: {risk}")
        lines.append(f"    Tags : {tags}")
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
    prompt_style: str | None = None,
) -> str:
    lang = language
    name = hero.display_name.get(lang)
    cls = hero.class_name.get(lang)
    tags = " / ".join(build.tags) or label("hero_card_none", lang)

    stats = (
        f"HP {build.hp}  MP {build.mp}  SPD {build.speed}  "
        f"ATK {build.attack}  DEF {build.defense}  POW {build.power}"
    )
    build_name = _build_archetype(hero.id, lang)
    risk = _hero_risk(hero.id)
    strategy = _hero_strategy(hero.id, lang)
    weapon, build_icon = _hero_card_icons(hero.id)

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
    lines.append(f"Build: {build_name} {build_icon}")
    lines.append(f"Weapon: {weapon}")
    lines.append(f"Risk: {risk}")
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
    lines.append("AI Bias:")
    for ln in strategy:
        lines.append(f"  - {ln}")
    if prompt_style:
        lines.append(f"Prompt Template: {prompt_style}")
        lines.append(f"  {prompt_style_text(prompt_style, lang)}")
    lines.append("")
    lines.append(label("hero_card_prompt", lang) + ":")
    for ln in hero.default_prompt.get(lang).splitlines():
        lines.append(f"  {ln}")
    return "\n".join(lines)


def _safe_resolve_build(hero: HeroData, bundle: ContentBundle) -> ResolvedBuild | None:
    from ouro_agent.engine import resolve_build

    try:
        return resolve_build(hero, bundle)
    except Exception:
        return None


def _build_archetype(hero_id: str, lang: str) -> str:
    names = {
        "hero_shadow_apprentice": {
            "en": "Black Candle Interrupt",
            "zh": "黑烛打断",
        },
        "hero_ash_guardian": {"en": "Iron Wall Counter", "zh": "铁壁反击"},
        "hero_broken_string_hunter": {
            "en": "Bleed Execution",
            "zh": "流血处决",
        },
        "hero_mire_oracle": {"en": "Poison Attrition", "zh": "毒沼消耗"},
        "hero_gravewright": {"en": "Gear Trap Setup", "zh": "机关陷阱"},
        "hero_echo_exile": {"en": "Echo Ward Control", "zh": "回声护壁"},
    }
    return names.get(hero_id, {"en": "Unknown Build", "zh": "未知 Build"}).get(lang) or names.get(hero_id, {}).get("en", "Unknown Build")


def _hero_risk(hero_id: str) -> str:
    return {
        "hero_shadow_apprentice": "normal",
        "hero_ash_guardian": "easy",
        "hero_broken_string_hunter": "hard",
        "hero_mire_oracle": "normal",
        "hero_gravewright": "normal",
        "hero_echo_exile": "easy",
    }.get(hero_id, "normal")


def _hero_strategy(hero_id: str, lang: str) -> list[str]:
    data = {
        "hero_shadow_apprentice": {
            "en": [
                "Interrupt high-ATB casters.",
                "Spend MP for tempo, not vanity.",
                "Use shield before HP drops too far.",
            ],
            "zh": [
                "优先打断高 ATB 施法者。",
                "用 MP 换节奏，不为炫技乱放。",
                "血线危险前先补护盾。",
            ],
        },
        "hero_ash_guardian": {
            "en": [
                "Keep HP above the safe line.",
                "Brace before enemy telegraphs.",
                "Punish casters after they commit.",
            ],
            "zh": [
                "保持 HP 在安全线以上。",
                "敌人预兆前先架盾。",
                "等施法者露出破绽再反击。",
            ],
        },
        "hero_broken_string_hunter": {
            "en": [
                "Stack bleed on durable targets.",
                "Execute weakened enemies quickly.",
                "Use speed to create action gaps.",
            ],
            "zh": [
                "给高耐久目标叠流血。",
                "快速处决残血敌人。",
                "用速度制造行动差。",
            ],
        },
        "hero_mire_oracle": {
            "en": [
                "Poison durable targets early.",
                "Mute high-ATB casters with Omen Vial.",
                "Use Sinking Veil before the attrition race turns.",
            ],
            "zh": [
                "开局给耐久目标铺毒。",
                "用预兆毒瓶压制高 ATB 施法者。",
                "消耗战失控前使用沉沼纱幕。",
            ],
        },
        "hero_gravewright": {
            "en": [
                "Mark targets with Grave Nail.",
                "Brace with Crank Charge under pressure.",
                "Release Burial Engine into weakened or chanting enemies.",
            ],
            "zh": [
                "用坟钉标记目标。",
                "压力上升时用曲柄充能稳住。",
                "把葬仪机关打向虚弱或吟唱敌人。",
            ],
        },
        "hero_echo_exile": {
            "en": [
                "Keep Bell Echo ready before heavy turns.",
                "Silence chants with Silent Hymn.",
                "Use Returning Chime to end fights cleanly.",
            ],
            "zh": [
                "敌人大回合前保留铃声回响。",
                "用静默圣歌封住吟唱。",
                "用回返钟声干净结束战斗。",
            ],
        },
    }
    return data.get(hero_id, {}).get(lang) or data.get(hero_id, {}).get("en", [])


def _hero_card_icons(hero_id: str) -> tuple[str, str]:
    return {
        "hero_shadow_apprentice": ("[W:STF] c==*", "[ONLINE]"),
        "hero_ash_guardian": ("[W:SHD] [#]", "[PAIR]"),
        "hero_broken_string_hunter": ("[W:XBW] ==>", "[PAIR]"),
        "hero_mire_oracle": ("[W:VIL] (v)", "[SEED]"),
        "hero_gravewright": ("[W:GER] [o]", "[SEED]"),
        "hero_echo_exile": ("[W:BEL] )o(", "[SEED]"),
    }.get(hero_id, ("[W:???]", "[SEED]"))
