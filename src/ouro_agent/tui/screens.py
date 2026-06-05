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
import re

from ouro_agent.art.battle_assets import enemy_sprite as asset_enemy_sprite
from ouro_agent.art.battle_assets import hero_sprite as asset_hero_sprite
from ouro_agent.art.block_sprites import block_effect_rows, enemy_block_sprite, hero_block_sprite
from ouro_agent.art.battle_dialogue import select_dialogue_line
from ouro_agent.art.glyphs import bar, hp_bar, mp_bar, atb_bar, status_indicator
from ouro_agent.art.weapon_cards import battle_weapon_line, hero_weapon_card, hero_weapon_card_art
from ouro_agent.content import CodexStage, ContentBundle, EnemyData, HeroData
from ouro_agent.config import OuroConfig, redacted_view
from ouro_agent.engine.battle import TurnRecord
from ouro_agent.engine.build import (
    BuildProgress,
    BuildStage,
    HERO_BUILD_ARCHETYPES,
    HERO_CORE_TAGS,
    HERO_RISK_LEVELS,
    HERO_STRATEGIES,
    ResolvedBuild,
    resolve_build,
)
from ouro_agent.engine.models import BattleState, Enemy, Hero
from ouro_agent.i18n import DEFAULT_LANGUAGE, label, pad_right, visual_width
from ouro_agent.llm.prompt import PROMPT_STYLE_TEMPLATES, prompt_style_text
from ouro_agent.sessions import (
    CodexProgress,
    ContextProgress,
    RunPhase,
    codex_stage_badge,
    codex_stage_label,
    context_level_label,
    context_slot_label,
)
from ouro_agent.tui.frame_builder import (
    BattleFrame,
    build_battle_frame,
    format_status_detail,
    format_status_short,
)
from ouro_agent.tui.ansi import color_enabled, paint, strip_ansi
from ouro_agent.tui.canvas import Surface
from ouro_agent.tui.glyphs import get_glyph_set
from ouro_agent.tui.layout import fit_text
from ouro_agent.tui.pixel_skin import pixel_panel, pixel_rule
from ouro_agent.tui.report_analysis import (
    analyze_battle_tactics,
    render_failure_review,
    render_prompt_impacts,
    render_tactical_diagnosis,
)


_CANVAS_LABELS: dict[str, dict[str, str]] = {
    "canvas_title": {"en": "THE ECHO ALTAR", "zh": "回声祭坛"},
    "canvas_hero": {"en": "HERO", "zh": "英雄"},
    "canvas_enemy": {"en": "ENEMY", "zh": "敌方"},
    "director": {"en": "DIRECTOR", "zh": "导演"},
    "tempo": {"en": "TEMPO", "zh": "节奏"},
    "tempo_rail": {"en": "TEMPO RAIL", "zh": "节奏"},
    "plan": {"en": "PLAN", "zh": "计划"},
    "action": {"en": "ACTION", "zh": "行动"},
    "judge": {"en": "JUDGE", "zh": "裁判"},
    "intent": {"en": "INTENT", "zh": "意图"},
    "stack": {"en": "STACK", "zh": "队列"},
    "skill": {"en": "SKILL", "zh": "技能"},
    "wound": {"en": "WOUND", "zh": "伤口"},
    "pain": {"en": "PAIN", "zh": "承伤"},
    "support": {"en": "SUPPORT", "zh": "支援"},
    "delta": {"en": "DELTA", "zh": "变化"},
    "reticle": {"en": "RETICLE", "zh": "准星"},
    "threat": {"en": "THREAT", "zh": "威胁"},
    "focus": {"en": "FOCUS", "zh": "焦点"},
    "select": {"en": "SELECT", "zh": "选定"},
}


def _canvas_label(key: str, lang: str) -> str:
    values = _CANVAS_LABELS.get(key, {})
    return values.get(lang, values.get("en", key.upper()))


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
    enhanced_bars: bool = False,
    bundle: ContentBundle | None = None,
    build: ResolvedBuild | None = None,
    scene_text: str | None = None,
    color_mode: str = "never",
) -> str:
    frame = build_battle_frame(state, last_record)
    lang = language or state.language or DEFAULT_LANGUAGE
    floor = floor_label or label("floor_label_default", lang)
    speed_word = label("speed", lang)
    seed_word = label("seed", lang)
    provider_word = label("provider_label", lang)
    auto_watch_word = label("auto_watch", lang)
    action_strip_word = label("action_strip", lang)

    default_scene = label("default_scene", lang)
    scene = scene_text or default_scene
    scene_padded = pad_right(fit_text(scene, width - 4), width - 4)

    lines: list[str] = []
    lines.append(f"{label('title', lang)} :: {floor}                         {auto_watch_word}")
    lines.append(f"| {scene_padded} |")
    lines.append(
        f"{seed_word}: mvp_a-{seed:03d}        "
        f"{provider_word}: {provider_label}        "
        f"{speed_word}: x1"
    )
    lines.append("")
    lines.append(f"{label('hero', lang)} VS {label('enemies', lang)}")
    compact = width <= 88 and not unicode_mode
    if compact:
        lines.extend(
            _render_compact_duel_panel(
                state,
                last_record,
                frame=frame,
                lang=lang,
                unicode_mode=unicode_mode,
                enhanced_bars=enhanced_bars,
            )
        )
    else:
        lines.extend(
            _render_duel_panel(
                state,
                last_record,
                frame=frame,
                lang=lang,
                unicode_mode=unicode_mode,
                enhanced_bars=enhanced_bars,
                width=width,
                color_mode=color_mode,
                scene_text=scene,
            )
        )
    lines.append("")
    if not compact:
        lines.append("")
        lines.extend(_render_build_line(state.hero, bundle, build, lang=lang))
        lines.extend(_render_enemy_roster(state, last_record, lang=lang, unicode_mode=unicode_mode))
    else:
        lines.append("")
    lines.extend(_render_battle_momentum_panel(state, frame, last_record, width=width, lang=lang))
    lines.extend(_render_action_focus_panel(frame, width=width, lang=lang))
    lines.extend(
        _render_cinematic_beat_panel(
            state,
            last_record,
            frame=frame,
            width=width,
            lang=lang,
        )
    )
    lines.extend(
        _render_build_climax_panel(
            build,
            bundle=bundle,
            width=width,
            lang=lang,
            show_opening=last_record is None and not state.log,
        )
    )
    lines.append("")
    lines.extend(_render_battle_objective_panel(state, frame, last_record, width=width, lang=lang))
    lines.append("")
    lines.extend(_render_hero_line_panel(state, last_record, frame=frame, lang=lang))
    lines.append("")
    lines.extend(
        _render_evidence_panel(
            state,
            last_record,
            frame=frame,
            provider_label=provider_label,
            action_strip_word=action_strip_word,
            width=width,
            lang=lang,
        )
    )
    if compact:
        lines = [_fit_screen_line(line, width) for line in lines]
    else:
        lines = [_fit_screen_line(line, width) for line in lines]
    return "\n".join(_wrap_screen_lines(lines, width))


def _render_compact_duel_panel(
    state: BattleState,
    last_record: TurnRecord | None,
    *,
    frame: BattleFrame,
    lang: str,
    unicode_mode: bool,
    enhanced_bars: bool = False,
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
    lines.append(_stage_director_line(state, target, frame, width=80, lang=lang, framed=False))
    for idx in range(3):
        left = pad_right(hero_sprite[idx][:20], 20)
        right = enemy_sprite[idx][:22]
        mid = effect_text if idx == 1 else ""
        lines.append(f"{left} {pad_right(mid[:14], 14)} {right}".rstrip())
    lines.extend(_hero_hud(state.hero, lang=lang, unicode_mode=unicode_mode, enhanced=enhanced_bars))
    if target is not None:
        lines.extend(_enemy_hud(target, lang=lang, unicode_mode=unicode_mode, enhanced=enhanced_bars))
        enemy_statuses = _status_groups(target.statuses, lang=lang)
        lines.extend(line for line in enemy_statuses if "Status: -" not in line)
    roster = _compact_enemy_roster(state, last_record, unicode_mode=unicode_mode)
    if roster:
        lines.append(roster)
    hero_statuses = _status_groups(state.hero.statuses, lang=lang)
    lines.extend(line for line in hero_statuses if "Status: -" not in line)
    weapon, build = _hero_icons(state.hero)
    lines.append(f"{label('hud_weapon', lang)} {weapon[:28]}  {label('hud_build', lang)} {build[:32]}")
    return [line[:80] for line in lines]


def _render_enemy_roster(
    state: BattleState,
    record: TurnRecord | None,
    *,
    lang: str,
    unicode_mode: bool,
) -> list[str]:
    if not state.enemies:
        return []
    lines = [label("enemy_roster", lang)]
    active_id = _screen_target(state, record).id if _screen_target(state, record) else ""
    for idx, enemy in enumerate(state.enemies, start=1):
        marker = ">" if enemy.id == active_id else " "
        lines.append(f" {marker} {_render_enemy(idx, enemy, lang=lang, unicode_mode=unicode_mode)}")
    return lines


def _compact_enemy_roster(
    state: BattleState,
    record: TurnRecord | None,
    *,
    unicode_mode: bool,
) -> str:
    active = _screen_target(state, record)
    parts = []
    for enemy in state.enemies:
        marker = ">" if active is not None and enemy.id == active.id else "-"
        hp = bar(enemy.hp, enemy.max_hp, width=4, unicode_mode=unicode_mode)
        down = "X" if not enemy.is_alive else ""
        parts.append(f"{marker}[{enemy.short_glyph}] {hp}{down}")
    return "ENEMY ROSTER " + "  ".join(parts)


def _render_duel_panel(
    state: BattleState,
    last_record: TurnRecord | None,
    *,
    frame: BattleFrame,
    lang: str,
    unicode_mode: bool,
    enhanced_bars: bool = False,
    width: int = 100,
    color_mode: str = "never",
    scene_text: str | None = None,
) -> list[str]:
    if unicode_mode:
        return _render_canvas_duel_panel(
            state,
            last_record,
            frame=frame,
            lang=lang,
            width=width,
            color_mode=color_mode,
            scene_text=scene_text,
        )

    target = _screen_target(state, last_record)
    effect = _effect_lane(last_record)
    hero_sprite = _hero_sprite(state.hero, last_record)
    enemy_sprite = _enemy_sprite(target, last_record) if target else ["", "", "", ""]
    hero_lines = _actor_card_lines(
        title=f"{state.hero.short_tag} {state.hero.name}",
        sprite=hero_sprite,
        hud=_hero_hud(state.hero, lang=lang, unicode_mode=unicode_mode, enhanced=enhanced_bars),
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
            _enemy_hud(target, lang=lang, unicode_mode=unicode_mode, enhanced=enhanced_bars)
            if target is not None
            else []
        ),
        statuses=_status_groups(target.statuses, lang=lang) if target is not None else [],
    )
    height = max(len(hero_lines), len(enemy_lines), len(effect))
    hero_lines.extend([""] * (height - len(hero_lines)))
    enemy_lines.extend([""] * (height - len(enemy_lines)))
    effect.extend([""] * (height - len(effect)))

    tone = _battle_visual_tone(state, frame)
    altar = "回声祭坛" if lang == "zh" else "THE ECHO ALTAR"
    lines = [pixel_rule(altar, width, tone=tone)]
    lines.append(
        _stage_header(
            label("hero", lang),
            _stage_event_title(frame, lang),
            label("enemies", lang),
            width=width,
        )
    )
    lines.append(_stage_director_line(state, target, frame, width=width, lang=lang))
    for idx in range(height):
        left = pad_right(hero_lines[idx][:36], 36)
        mid = pad_right(effect[idx][:18], 18)
        right = pad_right(enemy_lines[idx][:35], 35)
        lines.append(f"| {left} | {mid}| {right} |")
    lines.append(pixel_rule("", width, tone=tone))
    return [fit_text(line, width) for line in lines]


def _render_canvas_duel_panel(
    state: BattleState,
    last_record: TurnRecord | None,
    *,
    frame: BattleFrame,
    lang: str,
    width: int,
    color_mode: str = "never",
    scene_text: str | None = None,
) -> list[str]:
    """Render the main duel as a low-resolution terminal canvas."""
    target = _screen_target(state, last_record)
    glyphs = get_glyph_set("unicode")
    height = 17
    surface = Surface(width, height)
    surface.draw_box(0, 0, width, height, glyphs)

    title = _canvas_label("canvas_title", lang)
    event = _stage_event_title(frame, lang)
    surface.draw_text(3, 0, f" {title} / {event} ")
    _draw_canvas_beat_badge(surface, width, frame, lang=lang)

    side_w = 24 if width <= 88 else 30
    left_w = side_w
    right_w = side_w
    center_x = left_w + 2
    center_w = max(18, width - left_w - right_w - 4)
    right_x = width - right_w - 1
    separator_a = left_w + 1
    separator_b = right_x - 1
    for row in range(1, height - 1):
        surface.put(separator_a, row, glyphs.v)
        surface.put(separator_b, row, glyphs.v)
    _draw_canvas_scene_texture(surface, center_x + 1, 2, center_w - 2, scene_text, lang=lang)

    hero_pose = _actor_pose(state.hero.id, last_record)
    if state.hero.hp / max(1, state.hero.max_hp) < 0.3 and hero_pose not in ("hit", "death"):
        hero_pose = "low"
    hero_art = hero_block_sprite(state.hero.id, hero_pose)
    enemy_art: list[str] = [""] * 4
    if target is not None:
        enemy_pose = _actor_pose(target.id, last_record)
        if not target.is_alive:
            enemy_pose = "death"
        elif target.hp / max(1, target.max_hp) < 0.3 and enemy_pose not in ("hit", "death"):
            enemy_pose = "low"
        enemy_art = enemy_block_sprite(target.short_glyph, enemy_pose)

    surface.draw_text(
        2,
        1,
        fit_text(
            f"{_canvas_label('canvas_hero', lang)} {state.hero.short_tag} {state.hero.name}",
            left_w - 3,
        ),
    )
    surface.draw_text(2, 2, _canvas_hero_dialogue(state, last_record, frame, lang=lang, width=left_w - 3))
    surface.draw_sprite(4, 3, hero_art)
    weapon, build_badge = _hero_icons(state.hero)
    _draw_canvas_weapon_plate(surface, 2, 7, left_w - 3, state.hero.id, weapon, build_badge)
    _draw_canvas_actor_hud(
        surface,
        3,
        10,
        hp=state.hero.hp,
        max_hp=state.hero.max_hp,
        mp=state.hero.mp,
        max_mp=state.hero.max_mp,
        atb=state.hero.atb,
        width=left_w - 6,
        lang=lang,
    )
    _draw_canvas_status_chips(surface, 3, 14, left_w - 6, state.hero.statuses)
    _draw_canvas_skill_rail(surface, 3, 15, left_w - 6, state.hero, lang=lang)

    enemy_title = (
        _canvas_enemy_title(target, right_w - 3, lang=lang)
        if target is not None
        else f"{_canvas_label('canvas_enemy', lang)} -"
    )
    surface.draw_text(right_x + 1, 1, fit_text(enemy_title, right_w - 3))
    surface.draw_text(
        right_x + 1,
        2,
        _canvas_enemy_dialogue(target, last_record, frame, lang=lang, width=right_w - 3),
    )
    surface.draw_sprite(right_x + 5, 3, enemy_art)
    _draw_canvas_stagecraft(
        surface,
        left_x=2,
        right_x=right_x + 1,
        left_w=left_w - 3,
        right_w=right_w - 3,
        record=last_record,
        target=target,
        frame=frame,
        lang=lang,
    )
    if target is not None:
        _draw_canvas_cast_meter(surface, right_x + 2, 8, right_w - 6, target)
    _draw_canvas_floating_numbers(surface, right_x + 2, 8, right_w - 4, last_record, frame)
    if target is not None:
        _draw_canvas_actor_hud(
            surface,
            right_x + 2,
            10,
            hp=target.hp,
            max_hp=target.max_hp,
            mp=None,
            max_mp=None,
            atb=target.atb,
            width=right_w - 6,
            lang=lang,
        )
        _draw_canvas_status_chips(surface, right_x + 2, 12, right_w - 6, target.statuses)
        _draw_canvas_enemy_intent(surface, right_x + 2, 13, right_w - 6, target, frame, lang=lang)
    _draw_canvas_enemy_stack(
        surface,
        right_x + 1,
        14,
        right_w - 3,
        state,
        target,
        lang=lang,
    )

    _draw_canvas_beat_strip(
        surface,
        center_x + 1,
        1,
        center_w - 2,
        last_record,
        frame,
        lang=lang,
    )
    surface.draw_text(
        center_x + 1,
        3,
        _stage_director_canvas_line(state, target, frame, lang=lang, width=center_w - 2),
    )
    _draw_canvas_tempo_rail(
        surface,
        center_x + 1,
        4,
        center_w - 2,
        state,
        target,
        frame,
        lang=lang,
    )
    _draw_canvas_effect_lane(
        surface,
        center_x + 1,
        5,
        center_w - 2,
        last_record,
        frame,
        lang=lang,
    )
    _draw_canvas_damage_rail(
        surface,
        center_x + 1,
        9,
        center_w - 2,
        state.hero,
        target,
        last_record,
        frame,
        lang=lang,
    )
    _draw_canvas_plan_ribbon(surface, center_x + 1, 11, center_w - 2, frame, lang=lang)
    action = fit_text(
        _canvas_action_label(
            frame,
            last_record,
            target,
            hero=state.hero,
            lang=lang,
        ),
        center_w - 2,
    )
    judge = fit_text(f"{_canvas_label('judge', lang)}  {_canvas_judge_label(frame.judge_label, lang=lang)}", center_w - 2)
    surface.draw_text(center_x + 1, 12, action)
    surface.draw_text(center_x + 1, 13, judge)
    if frame.counter_clock:
        surface.draw_text(center_x + 1, 14, fit_text(_canvas_counter_rail_label(frame.counter_clock), center_w - 2))
    elif frame.impact_line:
        surface.draw_text(center_x + 1, 14, fit_text(_canvas_impact_label(frame.impact_line), center_w - 2))
    _draw_canvas_delta_ribbon(
        surface,
        center_x + 1,
        15,
        center_w - 2,
        frame,
        state,
        lang=lang,
    )

    rendered = _colorize_canvas_lines(
        surface.render(),
        tone=_battle_visual_tone(state, frame),
        color_mode=color_mode,
    )
    if frame.boss_intel:
        rendered.append(fit_text(_boss_intel_summary(frame, lang), width))
    if lang == "zh":
        rendered.append(fit_text("图形化 TUI: 终端低分辨率 Canvas / ASCII 兼容输出", width))
    else:
        rendered.append(fit_text("GRAPHICAL TUI: low-resolution terminal Canvas / ASCII fallback remains available", width))
    return rendered


def _draw_canvas_weapon_plate(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    hero_id: str,
    weapon: str,
    build_badge: str,
) -> None:
    card = hero_weapon_card_art(hero_id)
    art_width = min(8, max(0, width // 3))
    for row_offset, row in enumerate(card.unicode_art[:3]):
        surface.draw_text(x, y + row_offset, fit_text(row, art_width))
    text_x = x + art_width + 1
    text_width = max(6, width - art_width - 1)
    weapon_row, build_row, tag_row = _canvas_weapon_plate_rows(card, weapon, build_badge, text_width)
    surface.draw_text(text_x, y, weapon_row)
    surface.draw_text(text_x, y + 1, build_row)
    surface.draw_text(text_x, y + 2, tag_row)


def _canvas_weapon_plate_rows(
    card,
    weapon: str,
    build_badge: str,
    width: int,
) -> tuple[str, str, str]:
    weapon_icon = card.icon or weapon.split(" ", 1)[0]
    stage = card.badge or build_badge.split(" ", 1)[0]
    tags = _canvas_build_tags(card.build_shift or build_badge)
    first_tag = tags.split("/", 1)[0] if tags else ""
    weapon_row = _canvas_fit_choice(weapon_icon, weapon.split(" ", 1)[0], width)
    build_primary = f"{stage} {first_tag}".strip()
    build_row = _canvas_fit_choice(build_primary, stage, width)
    tag_row = _canvas_fit_choice(tags, _canvas_short_build_tags(tags), width)
    return weapon_row, build_row, tag_row


def _canvas_build_tags(text: str) -> str:
    if "]" in text:
        return text.split("]", 1)[1].strip()
    parts = text.split(" ", 1)
    return parts[1].strip() if len(parts) > 1 else text.strip()


def _canvas_short_build_tags(tags: str) -> str:
    replacements = {
        "control": "ctrl",
        "execute": "exe",
        "shield": "shd",
        "poison": "psn",
        "cleanse": "cln",
    }
    parts = [replacements.get(part, part) for part in tags.replace("/", " ").split() if part]
    if len(parts) >= 2:
        return f"{parts[0]}+{parts[1]}"
    return parts[0] if parts else "tags"


def _canvas_fit_choice(primary: str, fallback: str, width: int) -> str:
    if visual_width(primary) <= width:
        return primary
    if visual_width(fallback) <= width:
        return fallback
    return fit_text(fallback, width)


def _draw_canvas_stagecraft(
    surface: Surface,
    *,
    left_x: int,
    right_x: int,
    left_w: int,
    right_w: int,
    record: TurnRecord | None,
    target: Enemy | None,
    frame: BattleFrame,
    lang: str,
) -> None:
    glyphs = get_glyph_set("unicode")
    hero_shadow_w = max(8, min(16, left_w - 4))
    enemy_shadow_w = max(8, min(16, right_w - 4))
    surface.fill_rect(left_x + 1, 6, hero_shadow_w, 1, glyphs.mid)
    surface.fill_rect(right_x + 3, 6, enemy_shadow_w, 1, glyphs.mid)

    hero_actor = record is None or record.side == "hero"
    if lang == "zh":
        hero_mark = "动>" if hero_actor else "标<"
        enemy_mark = "<标" if hero_actor else "动<"
    else:
        hero_mark = "ACT>" if hero_actor else "TGT"
        enemy_mark = "<TGT" if hero_actor else "<ACT"
    surface.draw_text(left_x, 3, hero_mark)
    if target is not None:
        surface.draw_text(right_x + max(0, right_w - 4), 3, enemy_mark)
        surface.draw_text(right_x + 1, 7, fit_text(_canvas_enemy_threat_badge(target, frame, lang=lang), right_w - 2))
        if frame.counter_clock or frame.counter_hint:
            reticle = (
                f"{_canvas_label('reticle', lang)} [窗口]"
                if lang == "zh"
                else f"{_canvas_label('reticle', lang)} [WINDOW]"
            )
            surface.draw_text(
                right_x + 1,
                9,
                fit_text(reticle, right_w - 2),
            )
        else:
            reticle = (
                f"{_canvas_label('reticle', lang)} [目标]"
                if lang == "zh"
                else f"{_canvas_label('reticle', lang)} [TARGET]"
            )
            surface.draw_text(
                right_x + 1,
                9,
                fit_text(reticle, right_w - 2),
            )


def _canvas_enemy_threat_badge(
    target: Enemy,
    frame: BattleFrame,
    lang: str,
) -> str:
    threat = _canvas_label("threat", lang)
    if lang == "zh":
        if not target.is_alive:
            return f"{threat} 清"
        if frame.counter_clock or frame.counter_hint or target.chant_progress:
            return f"{threat} 追踪 {target.chant_progress}/{target.chant_charge_turns or 1}"
        if target.atb >= 95:
            return f"{threat} 蓄势"
        if target.hp / max(1, target.max_hp) <= 0.3:
            return f"{threat} 低"
        return f"{threat} {_canvas_enemy_tier_label(target.tier, lang=lang)}"
    if not target.is_alive:
        return f"{threat} CLEARED"
    if frame.counter_clock or frame.counter_hint or target.chant_progress:
        return f"{threat} WINDOW {target.chant_progress}/{target.chant_charge_turns or 1}"
    if target.atb >= 95:
        return f"{threat} HIGH ATB"
    if target.hp / max(1, target.max_hp) <= 0.3:
        return f"{threat} LOW HP"
    return f"{threat} {target.tier.upper()}"


def _canvas_enemy_tier_label(tier: str, *, lang: str) -> str:
    if lang != "zh":
        return tier.upper()
    return {
        "trace": "追踪",
        "ritebound": "仪式",
        "archive_bound": "档案",
    }.get(tier, tier)


def _canvas_judge_label(judge_label: str, *, lang: str) -> str:
    if lang != "zh":
        return judge_label
    head, sep, tail = judge_label.partition("|")
    head_text = {
        "WAIT": "等待",
        "VALID": "有效",
        "LOCAL": "本地",
        "INVALID": "无效",
        "FALLBACK": "降级",
    }.get(head.strip().upper(), head.strip())
    tail_text = tail.strip()
    if tail_text:
        tail_text = (
            tail_text.replace("HP", "HP")
            .replace("SHD", "护盾")
            .replace("SILENCED", "沉默")
        )
    return f"{head_text} {sep} {tail_text}".strip() if sep else head_text


def _canvas_enemy_title(target: Enemy, width: int, *, lang: str) -> str:
    choices = _canvas_enemy_stage_name_choices(target)
    prefix = _canvas_label("canvas_enemy", lang)
    for choice in choices:
        title = f"{prefix} [{target.short_glyph}] {choice}"
        if visual_width(title) <= width:
            return title
    return f"{prefix} [{target.short_glyph}]"


def _canvas_enemy_stage_name(target: Enemy) -> str:
    return _canvas_enemy_stage_name_choices(target)[0]


def _canvas_enemy_stage_name_choices(target: Enemy) -> tuple[str, ...]:
    name = target.name.upper()
    replacements = (
        ("BLACK CANDLE ", ""),
        ("HOLLOW ", ""),
        ("ASH ", ""),
    )
    for old, new in replacements:
        name = name.replace(old, new)
    words = [word for word in name.split() if word]
    if len(words) > 2:
        words = words[-2:]
    primary = " ".join(words) or target.short_glyph.upper()
    fallback = words[-1] if words else target.short_glyph.upper()
    return (primary, fallback, target.short_glyph.upper())


def _draw_canvas_enemy_intent(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    target: Enemy,
    frame: BattleFrame,
    lang: str,
) -> None:
    if width < 12:
        return
    surface.fill_rect(x, y, width, 1, " ")
    surface.draw_text(x, y, fit_text(_canvas_enemy_intent_label(target, frame, lang=lang), width))


def _canvas_enemy_intent_label(
    target: Enemy,
    frame: BattleFrame,
    *,
    lang: str,
) -> str:
    intent = _canvas_label("intent", lang)
    if lang == "zh":
        if not target.is_alive:
            return f"{intent} 清"
        if target.find_status("status_silence") is not None:
            return f"{intent} 沉默"
        if target.chant_charge_turns or target.chant_progress or frame.counter_clock or frame.counter_hint:
            total = max(1, target.chant_charge_turns)
            current = max(0, min(total, target.chant_progress))
            if current >= total:
                return f"{intent} 释放"
            if current > 0:
                return f"{intent} 咏唱 {current}/{total}"
            return f"{intent} 咏唱 观测"
        if target.atb >= 95:
            return f"{intent} 攻击 就绪"
        if target.hp / max(1, target.max_hp) <= 0.3:
            return f"{intent} 失衡"
        return f"{intent} 攻击"
    if not target.is_alive:
        return f"{intent} CLEARED"
    if target.find_status("status_silence") is not None:
        return f"{intent} SILENCED"
    if target.chant_charge_turns or target.chant_progress or frame.counter_clock or frame.counter_hint:
        total = max(1, target.chant_charge_turns)
        current = max(0, min(total, target.chant_progress))
        if current >= total:
            return f"{intent} RELEASE"
        if current > 0:
            return f"{intent} CHANT {current}/{total}"
        return f"{intent} CHANT WATCH"
    if target.atb >= 95:
        return f"{intent} STRIKE RDY"
    if target.hp / max(1, target.max_hp) <= 0.3:
        return f"{intent} FALTER"
    return f"{intent} STRIKE"


def _draw_canvas_cast_meter(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    target: Enemy,
) -> None:
    if width < 12 or not target.chant_charge_turns:
        return
    surface.draw_text(x, y, fit_text(_canvas_cast_meter_label(target), width))


def _canvas_cast_meter_label(target: Enemy) -> str:
    if not target.is_alive:
        return "CAST --"
    if target.find_status("status_silence") is not None:
        return "CAST CUT"
    total = max(1, target.chant_charge_turns)
    current = max(0, min(total, target.chant_progress))
    return f"CAST {_canvas_cast_bar(current, total)} {current}/{total}"


def _canvas_cast_bar(current: int, total: int) -> str:
    glyphs = get_glyph_set("unicode")
    width = 4
    ratio = current / max(1, total)
    filled = round(width * max(0.0, min(1.0, ratio)))
    return glyphs.solid * filled + glyphs.light * (width - filled)


def _draw_canvas_damage_rail(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    hero: Hero,
    target: Enemy | None,
    record: TurnRecord | None,
    frame: BattleFrame,
    lang: str,
) -> None:
    if width < 20:
        return
    support_label = _canvas_support_rail_label(record, frame, lang=lang)
    if support_label:
        surface.draw_text(x, y, fit_text(support_label, width))
    elif _canvas_pain_damage(record) > 0:
        surface.draw_text(x, y, fit_text(_canvas_pain_label(hero, record, lang=lang), width))
    elif target is not None:
        surface.draw_text(x, y, fit_text(_canvas_wound_label(target, record, lang=lang), width))


def _canvas_wound_label(target: Enemy, record: TurnRecord | None, *, lang: str) -> str:
    label = _canvas_label("wound", lang)
    damage = _canvas_wound_damage(target, record)
    hp_text = f"{target.hp}/{target.max_hp}"
    state = _canvas_wound_state(target, lang=lang)
    if damage > 0:
        return f"{label} -{damage} {_canvas_wound_bar(target)} {hp_text} {state}"
    return f"{label} {_canvas_wound_bar(target)} {hp_text} {state}"


def _canvas_wound_damage(target: Enemy, record: TurnRecord | None) -> int:
    if record is None or record.side != "hero" or record.judge is None:
        return 0
    if target.id not in record.judge.target_ids:
        return 0
    return max(0, int(record.judge.damage))


def _canvas_wound_state(target: Enemy, *, lang: str = "en") -> str:
    if not target.is_alive:
        if lang == "zh":
            return "倒下"
        return "DOWN"
    if target.hp / max(1, target.max_hp) <= 0.3:
        if lang == "zh":
            return "处决"
        return "EXE"
    if lang == "zh":
        return "稳住"
    return "HOLD"


def _canvas_wound_bar(target: Enemy) -> str:
    glyphs = get_glyph_set("unicode")
    width = 4
    ratio = target.hp / max(1, target.max_hp)
    filled = round(width * max(0.0, min(1.0, ratio)))
    return glyphs.solid * filled + glyphs.light * (width - filled)


def _canvas_pain_label(hero: Hero, record: TurnRecord | None, *, lang: str) -> str:
    label = _canvas_label("pain", lang)
    damage = _canvas_pain_damage(record)
    hp_text = f"{hero.hp}/{hero.max_hp}"
    state = _canvas_pain_state(hero, lang=lang)
    return f"{label} -{damage} {_canvas_pain_bar(hero)} {hp_text} {state}"


def _canvas_pain_damage(record: TurnRecord | None) -> int:
    if record is None or record.side != "enemy":
        return 0
    damage = (record.enemy_action or {}).get("damage", 0)
    return max(0, damage) if isinstance(damage, int) else 0


def _canvas_pain_state(hero: Hero, *, lang: str = "en") -> str:
    if not hero.is_alive:
        if lang == "zh":
            return "倒下"
        return "FALL"
    if hero.hp / max(1, hero.max_hp) <= 0.3:
        if lang == "zh":
            return "危险"
        return "CRIT"
    if lang == "zh":
        return "安全"
    return "SAFE"


def _canvas_pain_bar(hero: Hero) -> str:
    glyphs = get_glyph_set("unicode")
    width = 4
    ratio = hero.hp / max(1, hero.max_hp)
    filled = round(width * max(0.0, min(1.0, ratio)))
    return glyphs.solid * filled + glyphs.light * (width - filled)


def _canvas_support_rail_label(record: TurnRecord | None, frame: BattleFrame, *, lang: str) -> str:
    support = _canvas_label("support", lang)
    if not _is_canvas_support_record(record):
        return ""
    return f"{support} {_canvas_support_token(frame)}"


def _canvas_support_effect_label(record: TurnRecord | None, frame: BattleFrame, *, lang: str) -> str:
    support = _canvas_label("support", lang)
    if not _is_canvas_support_record(record):
        return ""
    if record is not None and record.action is not None and record.action.type == "defend":
        tag = "GUARD"
    elif record is not None:
        tag = _canvas_skill_action_tag(record, frame)
    else:
        tag = support
    return f"{tag} {_canvas_support_token(frame)}"


def _canvas_support_token(frame: BattleFrame) -> str:
    for delta in frame.resource_deltas:
        label_code = delta.label.upper()
        if label_code in {"SHD", "FOC", "GRD", "HST"}:
            amount = delta.text.split(" ", 1)[0]
            return f"{label_code}+{amount}"
    return "READY"


def _is_canvas_support_record(record: TurnRecord | None) -> bool:
    if record is None or record.side != "hero" or record.action is None:
        return False
    if record.action.type == "defend":
        return True
    if record.action.type != "cast_skill":
        return False
    targets = tuple(str(target_id) for target_id in record.action.targets)
    return bool(targets) and record.actor_id in targets


def _canvas_counter_rail_label(counter_clock: str | None) -> str:
    if not counter_clock:
        return "CUT WATCH"
    bar = ""
    if "[" in counter_clock and "]" in counter_clock:
        bar = counter_clock.split("[", 1)[1].split("]", 1)[0]
        status_part = counter_clock.split("]", 1)[1].strip()
    else:
        status_part = counter_clock
    status = status_part.split("|", 1)[0].strip() or "WATCH"
    ready = "CHECK"
    marker = "NEXT HERO CAN INTERRUPT:"
    if marker in counter_clock:
        ready = _canvas_counter_ready_label(counter_clock.split(marker, 1)[1].strip())
    return f"CUT {_canvas_counter_bar(bar)} {status} {ready}"


def _canvas_counter_bar(bar: str) -> str:
    glyphs = get_glyph_set("unicode")
    width = 5
    padded = (bar + "-" * width)[:width]
    return "".join(glyphs.solid if char == "#" else glyphs.light for char in padded)


def _canvas_counter_ready_label(text: str) -> str:
    lower = text.lower()
    if not text:
        return "CHECK"
    if "no interrupt skill" in lower:
        return "NO SKILL"
    if "not ready:" in lower:
        reason = text.split("not ready:", 1)[1].strip()
        if reason.upper().startswith("CD "):
            return "CD" + reason.split(None, 1)[1]
        if reason.upper().startswith("MP "):
            return "MP" + reason.split(None, 1)[1]
        return reason.upper()
    if lower.endswith("ready"):
        return "READY"
    return "CHECK"


def _canvas_impact_label(impact_line: str) -> str:
    parts: list[str] = []
    for raw_part in impact_line.split("|"):
        part = raw_part.strip()
        if not part:
            continue
        compact = _canvas_impact_part(part)
        if compact:
            parts.append(compact)
    return " ".join(parts) if parts else impact_line


def _canvas_impact_part(part: str) -> str:
    lower = part.lower()
    support_match = re.match(r"^(shd|foc|grd|hst)\s+(\d+)\b", lower)
    if support_match:
        return f"{support_match.group(1).upper()}+{support_match.group(2)}"
    if lower.startswith("-") and " hp" in lower:
        damage = part.split(" ", 1)[0].lstrip("-")
        suffix = " DOWN" if "down" in lower else ""
        return f"HIT-{damage}{suffix}"
    if lower.startswith("hp ") and "->" in part:
        return "HP" + part.split(" ", 1)[1].replace("->", ">")
    if lower.startswith("mp ") and "->" in part:
        return "MP" + part.split(" ", 1)[1].replace("->", ">")
    if lower == "next interrupt: yes":
        return "INT:Y"
    if lower == "next interrupt: no":
        return "INT:N"
    if lower == "chant released":
        return "CAST:REL"
    if lower == "window opened":
        return "WIN:OPEN"
    if lower in {"attack", "basic_attack"}:
        return "STRIKE"
    if lower == "chant_charge":
        return "CHARGE"
    if lower == "chant_release":
        return "RELEASE"
    if lower.startswith("fallback:"):
        return "FB:" + _canvas_action_token(part.split(":", 1)[1].strip())
    return _canvas_action_token(part)


def _canvas_action_label(
    frame: BattleFrame,
    record: TurnRecord | None,
    target: Enemy | None,
    *,
    hero: Hero,
    lang: str,
) -> str:
    action = _canvas_label("action", lang)
    if record is None:
        if lang == "zh":
            return f"{action} 待机"
        return f"{action} WAIT"
    if record.side == "enemy":
        return f"{action} {_canvas_label('canvas_enemy', lang)} {_canvas_enemy_action_tag(record, frame, lang=lang)}"
    if record.action is None:
        if lang == "zh":
            return f"{action} 英雄 待机"
        return f"{action} HERO CHECK"
    action_type = str(record.action.type)
    target_code = _canvas_action_target_code(record, target, hero)
    if action_type == "cast_skill":
        return f"{action} {_canvas_skill_action_tag(record, frame)} -> {target_code}"
    if action_type == "basic_attack":
        if lang == "zh":
            return f"{action} 普攻 -> {target_code}"
        return f"{action} BASIC -> {target_code}"
    if action_type == "defend":
        if lang == "zh":
            return f"{action} 防御 -> {target_code}"
        return f"{action} GUARD -> {target_code}"
    if action_type == "observe":
        if lang == "zh":
            return f"{action} 观察 -> {target_code}"
        return f"{action} OBSERVE -> {target_code}"
    if action_type == "change_stance":
        if lang == "zh":
            return f"{action} 姿态 -> {target_code}"
        return f"{action} STANCE -> {target_code}"
    if action_type == "use_item":
        if lang == "zh":
            return f"{action} 道具 -> {target_code}"
        return f"{action} ITEM -> {target_code}"
    return f"{action} {_canvas_action_token(action_type)} -> {target_code}"


def _canvas_enemy_action_tag(record: TurnRecord, frame: BattleFrame, *, lang: str) -> str:
    action_type = str((record.enemy_action or {}).get("type", "basic_attack"))
    if lang == "zh":
        if action_type == "chant_charge":
            return "蓄力"
        if action_type == "chant_release":
            return "释放"
        if action_type in {"attack", "basic_attack"}:
            return "攻击"
        if action_type == "silenced" or "silenced" in frame.action_label.lower():
            return "沉默"
        return _canvas_action_token(action_type)
    if action_type == "chant_charge":
        return "CHARGE"
    if action_type == "chant_release":
        return "RELEASE"
    if action_type in {"attack", "basic_attack"}:
        return "STRIKE"
    if action_type == "silenced" or "silenced" in frame.action_label.lower():
        return "SILENCED"
    return _canvas_action_token(action_type)


def _canvas_skill_action_tag(record: TurnRecord, frame: BattleFrame) -> str:
    skill_id = ""
    if record.action is not None and record.action.skill_id:
        skill_id = record.action.skill_id
    known = {
        "skill_shadow_sting": "STING",
        "skill_hex_seal": "HEX",
        "skill_corrupted_focus": "FOCUS",
        "skill_tower_brace": "BRACE",
        "skill_ember_punish": "PUNISH",
        "skill_ash_glare": "GLARE",
        "skill_pierce_string": "PIERCE",
        "skill_hook_break": "BREAK",
        "skill_eclipse_step": "STEP",
        "skill_mire_needle": "NEEDLE",
        "skill_omen_vial": "VIAL",
        "skill_sinking_veil": "VEIL",
        "skill_grave_nail": "NAIL",
        "skill_crank_charge": "CRANK",
        "skill_burial_engine": "ENGINE",
        "skill_bell_echo": "ECHO",
        "skill_silent_hymn": "HYMN",
        "skill_returning_chime": "CHIME",
    }
    if skill_id in known:
        return known[skill_id]
    if skill_id:
        return _canvas_action_token(skill_id.removeprefix("skill_"))
    return _canvas_action_token(frame.action_label.split("->", 1)[0])


def _canvas_action_target_code(record: TurnRecord, target: Enemy | None, hero: Hero) -> str:
    target_ids: list[str] = []
    if record.action is not None and record.action.targets:
        target_ids.extend(str(target_id) for target_id in record.action.targets)
    if not target_ids and record.judge is not None and record.judge.target_ids:
        target_ids.extend(str(target_id) for target_id in record.judge.target_ids)
    if target_ids and hero.id in target_ids:
        return "HERO"
    if target is not None:
        return target.short_glyph
    if target_ids and target_ids[0].startswith("hero_"):
        return "HERO"
    return "FIELD"


def _canvas_action_token(value: str) -> str:
    parts = value.replace("-", "_").replace(" ", "_").split("_")
    words = [part for part in parts if part and part.lower() not in {"skill", "action"}]
    if not words:
        return "CHECK"
    if len(words) == 1:
        return words[0][:8].upper()
    return "".join(word[:1].upper() for word in words)[:8]


def _draw_canvas_beat_badge(surface: Surface, width: int, frame: BattleFrame, lang: str) -> None:
    label_text = _canvas_beat_badge_label(frame, lang=lang)
    x = max(3, width - visual_width(label_text) - 3)
    surface.draw_text(x, 0, label_text)


def _canvas_beat_badge_label(frame: BattleFrame, lang: str) -> str:
    if lang == "zh":
        phase = {
            "model_waiting": "等待",
            "hero_action": "英雄",
            "enemy_action": "敌方",
        }.get(frame.phase, frame.phase)
        return f" 节拍 T{frame.tick:03d} {phase} "
    phase = {
        "model_waiting": "WAIT",
        "hero_action": "HERO",
        "enemy_action": "ENEMY",
    }.get(frame.phase, frame.phase.upper()[:5])
    return f" BEAT T{frame.tick:03d} {phase} "


def _draw_canvas_plan_ribbon(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    frame: BattleFrame,
    lang: str,
) -> None:
    if width < 16:
        return
    surface.draw_text(x, y, fit_text(_canvas_plan_label(frame, lang=lang), width))


def _canvas_plan_label(frame: BattleFrame, *, lang: str) -> str:
    return f"{_canvas_label('plan', lang)} {_canvas_plan_mode(frame, lang=lang)} | {_canvas_plan_source(frame, lang=lang)}"


def _canvas_plan_mode(frame: BattleFrame, *, lang: str = "en") -> str:
    intent = frame.intent.lower()
    if lang == "zh":
        if frame.phase == "enemy_action":
            if "chant" in intent:
                return "中断"
            return "承压"
        if "read the field" in intent:
            return "读场"
        if "interrupt" in intent or "control" in intent:
            return "反制"
        if "stabilize" in intent:
            return "稳住"
        if "finish" in intent:
            return "收束"
        if "pressure" in intent:
            return "压迫"
        if "conserve" in intent:
            return "待机"
        return "战术"
    if frame.phase == "enemy_action":
        if "chant" in intent:
            return "ANSWER"
        return "BRACE"
    if "read the field" in intent:
        return "READ"
    if "interrupt" in intent or "control" in intent:
        return "CONTROL"
    if "stabilize" in intent:
        return "GUARD"
    if "finish" in intent:
        return "FINISH"
    if "pressure" in intent:
        return "BURST"
    if "conserve" in intent:
        return "CONSERVE"
    return "TACTIC"


def _canvas_plan_source(frame: BattleFrame, *, lang: str = "en") -> str:
    if lang == "zh":
        align = frame.align.lower()
        if "pending" in align:
            return "待机"
        if "counter" in align:
            return "反制"
        if "control" in align:
            return "命中"
        if "build" in align:
            return "建构"
        if "fallback" in align or "basic" in align:
            return "应对"
        if "local" in align:
            return "本机"
        if "missed" in align:
            return "失效"
        return "提示"
    align = frame.align.lower()
    if "pending" in align:
        return "PENDING"
    if "counter" in align:
        return "COUNTER"
    if "control" in align:
        return "PROMPT HIT"
    if "build" in align:
        return "BUILD SKILL"
    if "fallback" in align or "basic" in align:
        return "FALLBACK"
    if "local" in align:
        return "LOCAL AI"
    if "missed" in align:
        return "PROMPT MISS"
    return "PROMPT"


def _colorize_canvas_lines(lines: list[str], *, tone: str, color_mode: str) -> list[str]:
    if not color_enabled(color_mode):
        return lines
    colored: list[str] = []
    for line in lines:
        line_tone = tone
        if "HP CRIT" in line or "MISS" in line:
            line_tone = "danger"
        elif "WINDOW" in line or "COUNTER" in line:
            line_tone = "counter"
        elif "CLIMAX" in line or "BOSS DOWN" in line:
            line_tone = "climax"
        elif "HP " in line:
            line_tone = "hp"
        elif "MP " in line:
            line_tone = "mp"
        elif "ATB " in line:
            line_tone = "atb"
        colored.append(paint(line, line_tone))
    return colored


def _fit_screen_line(line: str, width: int) -> str:
    if "\x1b[" in line and visual_width(strip_ansi(line)) <= width:
        return line
    return fit_text(line, width)


def _canvas_hero_dialogue(
    state: BattleState,
    record: TurnRecord | None,
    frame: BattleFrame,
    *,
    lang: str,
    width: int,
) -> str:
    hero = state.hero
    hp_pct = hero.hp / hero.max_hp if hero.max_hp > 0 else 1.0
    mp_pct = hero.mp / hero.max_mp if hero.max_mp > 0 else 1.0
    line = _canvas_hero_voice_beat(hero, record, frame, hp_pct=hp_pct, mp_pct=mp_pct, lang=lang)
    return fit_text(f"VOX {line}", width)


def _canvas_hero_voice_beat(
    hero: Hero,
    record: TurnRecord | None,
    frame: BattleFrame,
    *,
    hp_pct: float,
    mp_pct: float,
    lang: str,
) -> str:
    if not hero.is_alive:
        return "candle out" if lang == "en" else "烛火熄灭"
    if hp_pct <= 0.3:
        return "hold the line" if lang == "en" else "守住血线"
    if mp_pct <= 0.25:
        return "count sparks" if lang == "en" else "省下火星"
    if record is None:
        if frame.event_banner and "BUILD" in frame.event_banner:
            return "pattern online" if lang == "en" else "阵式上线"
        return "read the room" if lang == "en" else "读场"
    if record.side == "enemy":
        action_type = str((record.enemy_action or {}).get("type", "attack"))
        if action_type == "chant_charge":
            return "cut the wick" if lang == "en" else "切断烛芯"
        if action_type == "chant_release":
            return "brace the rite" if lang == "en" else "顶住仪式"
        if action_type == "silenced":
            return "chant is cut" if lang == "en" else "咏唱已断"
        damage = (record.enemy_action or {}).get("damage", 0)
        if isinstance(damage, int) and damage > 0:
            return "stay upright" if lang == "en" else "站稳"
        return "watch the threat" if lang == "en" else "盯住威胁"
    skill_id = ""
    if record.action is not None and record.action.skill_id:
        skill_id = record.action.skill_id
    elif record.judge is not None and record.judge.skill_id:
        skill_id = record.judge.skill_id
    skill_key = skill_id.lower()
    label_text = frame.action_label.lower()
    if (
        "hex" in skill_key
        or "seal" in skill_key
        or "hex seal" in label_text
        or "seal" in label_text
        or "charge broken" in (frame.event_banner or "").lower()
    ):
        return "seal the chant" if lang == "en" else "封住咏唱"
    if "sting" in skill_key or "shadow sting" in label_text or "sting" in label_text:
        return "needle in shadow" if lang == "en" else "影针命中"
    if "focus" in skill_key or "corrupted focus" in label_text or "focus" in label_text:
        return "hold the flame" if lang == "en" else "稳住烛火"
    if "basic attack" in label_text:
        return "keep pressure" if lang == "en" else "保持压迫"
    if frame.event_banner and "KILL" in frame.event_banner:
        return "finish it" if lang == "en" else "收束"
    return "commit the turn" if lang == "en" else "执行回合"


def _canvas_enemy_dialogue(
    target: Enemy | None,
    record: TurnRecord | None,
    frame: BattleFrame,
    *,
    lang: str,
    width: int,
) -> str:
    if target is None:
        line = "no hostile echo" if lang == "en" else "无敌对回声"
        return fit_text(f"ENM {line}", width)
    if not target.is_alive:
        line = "signal collapsing" if lang == "en" else "信号崩塌"
        return fit_text(f"ENM {line}", width)
    if record is not None and record.side == "enemy":
        kind = (record.enemy_action or {}).get("type", "attack")
        if kind == "chant_charge":
            line = "the wick counts down" if lang == "en" else "烛芯正在倒数"
        elif kind == "chant_release":
            line = "the rite breaks open" if lang == "en" else "仪式裂开"
        elif kind == "silenced":
            line = "the chant is cut" if lang == "en" else "吟唱被切断"
        else:
            line = "strike pressure rising" if lang == "en" else "打击压力升高"
        return fit_text(f"ENM {line}", width)
    if (
        record is not None
        and record.side == "hero"
        and record.judge is not None
        and record.judge.damage > 0
        and target.id in record.judge.target_ids
    ):
        line = "armor cracking" if lang == "en" else "护甲开裂"
    elif frame.counter_clock or target.chant_progress > 0:
        line = "chant window open" if lang == "en" else "吟唱窗口开启"
    elif target.hp / max(1, target.max_hp) <= 0.3:
        line = "formation failing" if lang == "en" else "阵形崩坏"
    elif target.atb >= 90:
        line = "next strike loaded" if lang == "en" else "下一击已装填"
    else:
        line = "watching the agent" if lang == "en" else "盯住威胁"
    return fit_text(f"ENM {line}", width)


def _draw_canvas_scene_texture(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    scene_text: str | None,
    lang: str = "en",
) -> None:
    if width < 18:
        return
    scene = (scene_text or "").lower()
    if lang == "zh":
        if "candle" in scene or "烛" in scene:
            motifs = ("░ ·烛影· ░", "  ░ 灰烬 ░  ", "░ · 断拱 · ░")
        elif "ash" in scene or "灰" in scene:
            motifs = ("░ ·回响· ░", "  ░ 岩尘 ░  ", "░ · 断拱 · ░")
        else:
            motifs = ("░ ·回响· ░", "  ░ 现场 ░  ", "░ · 轻响 · ░")
    elif "candle" in scene or "烛" in scene:
        motifs = ("░  . candle .  ░", "  ░ wick ash ░  ", "░ . broken arch . ░")
    elif "ash" in scene or "灰" in scene:
        motifs = ("░  . ash .  ░", "  ░ ember dust ░  ", "░ . stone arch . ░")
    else:
        motifs = ("░  . echo .  ░", "  ░ field noise ░  ", "░ . rift dust . ░")
    for row, motif in enumerate(motifs):
        surface.draw_text(x, y + row * 3, fit_text(_center_canvas_text(motif, width), width))


def _center_canvas_text(text: str, width: int) -> str:
    text_width = visual_width(text)
    if text_width >= width:
        return fit_text(text, width)
    return " " * ((width - text_width) // 2) + text


def _draw_canvas_actor_hud(
    surface: Surface,
    x: int,
    y: int,
    *,
    hp: int,
    max_hp: int,
    mp: int | None,
    max_mp: int | None,
    atb: int,
    width: int,
    lang: str,
) -> None:
    glyphs = get_glyph_set("unicode")
    bar_width = max(6, width - 8)
    alerts: list[str] = []
    surface.draw_text(x, y, "HP")
    surface.draw_bar(x + 3, y, bar_width, hp / max(1, max_hp), glyphs)
    surface.draw_text(x + 4 + bar_width, y, f"{hp}/{max_hp}")
    if hp / max(1, max_hp) <= 0.3:
        alerts.append("HP 危险" if lang == "zh" else "HP CRIT")
    if mp is not None and max_mp is not None:
        mp_row = y + 1
        surface.draw_text(x, mp_row, "MP")
        surface.draw_bar(x + 3, mp_row, bar_width, mp / max(1, max_mp), glyphs)
        surface.draw_text(x + 4 + bar_width, mp_row, f"{mp}/{max_mp}")
        if mp / max(1, max_mp) <= 0.25:
            alerts.append("MP 低" if lang == "zh" else "MP LOW")
        atb_row = y + 2
    else:
        atb_row = y + 1
    surface.draw_text(x, atb_row, "ATB")
    surface.draw_bar(x + 4, atb_row, max(5, bar_width - 1), min(atb, 100) / 100, glyphs)
    if atb >= 100:
        alerts.append("ATB 就绪" if lang == "zh" else "ATB READY")
    if alerts:
        surface.draw_text(x, y + 3, fit_text(" ".join(alerts), width))


def _draw_canvas_floating_numbers(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    record: TurnRecord | None,
    frame: BattleFrame,
) -> None:
    if record is None or not frame.floating_numbers:
        return
    label_text = " ".join(frame.floating_numbers[:3])
    if record.side == "enemy":
        x = 3
        y = 5
        label_text = "HIT " + label_text
    else:
        label_text = "HIT " + label_text
    surface.draw_text(x, y, fit_text(label_text, width))


def _draw_canvas_delta_ribbon(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    frame: BattleFrame,
    state: BattleState,
    lang: str,
) -> None:
    if not frame.resource_deltas:
        return
    parts = [_compact_canvas_delta(delta.label, delta.text, state) for delta in frame.resource_deltas[:2]]
    surface.draw_text(
        x,
        y,
        fit_text(f"{_canvas_label('delta', lang)} " + " ".join(parts), width),
    )


def _compact_canvas_delta(label_text: str, delta_text: str, state: BattleState) -> str:
    label_code = label_text.upper()
    compact = _canvas_delta_actor_tokens(delta_text, state)
    if label_code == "MP":
        compact = compact.replace(" -> ", ">")
        compact = compact.replace(" | interrupt ready: yes", " I:Y")
        compact = compact.replace(" | interrupt ready: no", " I:N")
        return f"MP{compact}"
    if label_code == "HP":
        compact = compact.replace(" -> ", ">")
        compact = compact.replace(" | critical", "!")
        return f"HP{compact}"
    if label_code == "ATB":
        if compact == "hero ready":
            return "ATB:H*"
        if compact.endswith(" ready"):
            return f"ATB:{compact[:-6]}*"
        if compact.endswith("/100"):
            actor, _, value = compact.partition(" ")
            return f"ATB:{actor}{value.split('/', 1)[0]}"
        return f"ATB:{_canvas_action_token(compact)}"
    if label_code == "CD":
        skill, _, rest = compact.partition(" locked ")
        if rest.endswith("t"):
            return f"CD:{_canvas_skill_name_token(skill)}{rest[:-1]}"
        return f"CD:{_canvas_action_token(compact)}"
    if label_code == "SHD":
        amount = compact.split(" ", 1)[0]
        return f"SHD{amount}"
    return f"{label_code}:{_canvas_action_token(compact)}"


def _canvas_delta_actor_tokens(delta_text: str, state: BattleState) -> str:
    compact = delta_text
    for enemy in sorted(state.enemies, key=lambda candidate: visual_width(candidate.name), reverse=True):
        compact = compact.replace(enemy.name, enemy.short_glyph)
    return compact


def _canvas_skill_name_token(skill_name: str) -> str:
    known = {
        "Shadow Sting": "STG",
        "Hex Seal": "HEX",
        "Corrupted Focus": "FOC",
        "Tower Brace": "BRC",
        "Ember Punish": "PUN",
        "Ash Glare": "GLR",
        "Pierce String": "PRS",
        "Hook Break": "BRK",
        "Eclipse Step": "STP",
    }
    return known.get(skill_name, _canvas_action_token(skill_name))


def _draw_canvas_effect_lane(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    record: TurnRecord | None,
    frame: BattleFrame,
    lang: str,
) -> None:
    glyphs = get_glyph_set("unicode")
    surface.fill_rect(x, y, width, 3, " ")
    surface.fill_rect(x, y + 2, width, 1, glyphs.light)
    lane = _block_effect_lane(record, frame, width, lang=lang)
    for idx, row in enumerate(lane[:6]):
        surface.draw_text(x, y + idx, fit_text(row, width))


def _draw_canvas_beat_strip(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    record: TurnRecord | None,
    frame: BattleFrame,
    lang: str,
) -> None:
    glyphs = get_glyph_set("unicode")
    labels = _canvas_beat_labels(record, frame, lang)
    segment_gap = 1
    segment_width = max(7, (width - segment_gap * 2) // 3)
    for idx, label_text in enumerate(labels):
        left = x + idx * (segment_width + segment_gap)
        fill = _canvas_beat_fill(idx, record, frame, glyphs)
        surface.fill_rect(left, y, segment_width, 1, fill)
        surface.draw_text(left + 1, y, fit_text(label_text, segment_width - 2))


def _draw_canvas_tempo_rail(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    state: BattleState,
    target: Enemy | None,
    frame: BattleFrame,
    lang: str,
) -> None:
    """Draw a compact ATB pressure rail inside the battle canvas."""
    if width < 20:
        return
    hero_atb = max(0, min(100, int(state.hero.atb)))
    enemy_atb = max(0, min(100, int(target.atb))) if target is not None else 0
    state_label = _canvas_tempo_state(state, target, frame)
    line = _canvas_tempo_line(hero_atb, enemy_atb, state_label, width, lang=lang)
    surface.draw_text(x, y, line)


def _canvas_tempo_line(
    hero_atb: int,
    enemy_atb: int,
    state_label: str,
    width: int,
    *,
    lang: str,
) -> str:
    prefix = _canvas_label("tempo_rail", lang)
    hero_label = f"H{hero_atb:03d}"
    enemy_label = f"E{enemy_atb:03d}"
    compact_prefix = "RAIL" if lang == "en" else prefix
    candidates = [
        (prefix, 8, hero_label, enemy_label),
        (prefix, 4, hero_label, enemy_label),
        (compact_prefix, 2, hero_label, enemy_label),
        (prefix, 2, hero_label, enemy_label),
        (compact_prefix, 1, hero_label, enemy_label),
        ("T", 1, hero_label, enemy_label),
    ]
    for prefix, bar_width, hero_label, enemy_label in candidates:
        line = (
            f"{prefix} {hero_label} {_canvas_tempo_bar(hero_atb, bar_width)} "
            f"{enemy_label} {_canvas_tempo_bar(enemy_atb, bar_width)} {state_label}"
        )
        if visual_width(line) <= width:
            return line
    fallback = f"T H{hero_atb:03d} E{enemy_atb:03d} {state_label}"
    return fallback if visual_width(fallback) <= width else fit_text(fallback, width)


def _canvas_tempo_bar(value: int, width: int) -> str:
    glyphs = get_glyph_set("unicode")
    bounded = max(0, min(100, value))
    filled = round(width * (bounded / 100))
    return glyphs.solid * filled + glyphs.light * (width - filled)


def _canvas_tempo_state(state: BattleState, target: Enemy | None, frame: BattleFrame) -> str:
    if frame.counter_hint and "[MISSED]" in frame.counter_hint:
        return "MISS"
    if frame.counter_hint or frame.counter_clock or (target is not None and target.chant_progress):
        return "WIN"
    if not state.hero.is_alive:
        return "FALL"
    if target is not None and not target.is_alive:
        return "CLR"
    if state.hero.hp / max(1, state.hero.max_hp) <= 0.3:
        return "CRIT"
    if target is not None and target.hp / max(1, target.max_hp) <= 0.3:
        return "FIN"
    if target is not None and target.atb >= 95:
        return "PRESS"
    if state.hero.atb >= 100:
        return "RDY"
    return "FLOW"


def _draw_canvas_enemy_stack(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    state: BattleState,
    target: Enemy | None,
    lang: str,
) -> None:
    """Draw compact HP/ATB pips for the visible enemy pack."""
    if width < 14 or not state.enemies:
        return
    visible = state.enemies[:2]
    remaining = max(0, len(state.enemies) - len(visible))
    hp_parts = [_canvas_enemy_stack_part(enemy, target, attr="hp") for enemy in visible]
    atb_parts = [_canvas_enemy_stack_part(enemy, target, attr="atb") for enemy in visible]
    if remaining:
        hp_parts.append(f"+{remaining}")
        atb_parts.append(f"+{remaining}")
    surface.draw_text(x, y, fit_text(f"{_canvas_label('stack', lang)} " + " ".join(hp_parts), width))
    surface.draw_text(x, y + 1, fit_text("ATB   " + " ".join(atb_parts), width))


def _canvas_enemy_stack_part(enemy: Enemy, target: Enemy | None, *, attr: str) -> str:
    marker = ">" if target is not None and enemy.id == target.id else "-"
    value = enemy.hp / max(1, enemy.max_hp) if attr == "hp" else min(enemy.atb, 100) / 100
    return f"{marker}{enemy.short_glyph}{_canvas_mini_bar(value)}"


def _canvas_mini_bar(ratio: float) -> str:
    glyphs = get_glyph_set("unicode")
    bounded = max(0.0, min(1.0, ratio))
    width = 3
    filled = round(width * bounded)
    return glyphs.solid * filled + glyphs.light * (width - filled)


def _draw_canvas_status_chips(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    statuses: list,
) -> None:
    if width < 8 or not statuses:
        return
    chips = [_canvas_status_chip(status) for status in statuses[:3]]
    hidden = len(statuses) - len(chips)
    if hidden > 0:
        chips.append(f"+{hidden}")
    surface.draw_text(x, y, fit_text("FX " + " ".join(chips), width))


def _canvas_status_chip(status) -> str:
    code = format_status_short(status).split(" ", 1)[0]
    return f"{code}{status.stacks}"


_CANVAS_SKILL_CODES = {
    "skill_shadow_sting": "STG",
    "skill_hex_seal": "HEX",
    "skill_corrupted_focus": "FOC",
}


def _draw_canvas_skill_rail(
    surface: Surface,
    x: int,
    y: int,
    width: int,
    hero: Hero,
    lang: str,
) -> None:
    if width < 12 or not hero.skills:
        return
    max_chips = 2 if width < 22 else 3
    chips = [_canvas_skill_chip(skill, hero.mp) for skill in hero.skills[:max_chips]]
    hidden = len(hero.skills) - len(chips)
    if hidden > 0 and width >= 28:
        chips.append(f"+{hidden}")
    surface.draw_text(x, y, fit_text(f"{_canvas_label('skill', lang)} " + " ".join(chips), width))


def _canvas_skill_chip(skill, current_mp: int) -> str:
    code = _canvas_skill_code(skill)
    if skill.cooldown_remaining > 0:
        return f"{code}{min(skill.cooldown_remaining, 9)}"
    if skill.is_ready(current_mp):
        return f"{code}*"
    return f"{code}!"


def _canvas_skill_code(skill) -> str:
    if skill.id in _CANVAS_SKILL_CODES:
        return _CANVAS_SKILL_CODES[skill.id]
    display_name = getattr(skill.display_name, "get", None)
    if callable(display_name):
        source = display_name("en")
    else:
        source = str(skill.display_name)
    words = [word for word in source.replace("-", " ").split() if word]
    if len(words) >= 2:
        return "".join(word[0] for word in words[:3]).upper()[:3]
    source = (words[0] if words else skill.id).replace("skill_", "")
    return source[:3].upper()


def _canvas_beat_labels(record: TurnRecord | None, frame: BattleFrame, lang: str) -> tuple[str, str, str]:
    judge = _canvas_label("judge", lang)
    if lang == "zh":
        if record is None:
            return ("选定", "等待", judge)
        if frame.counter_hint and "[MISSED]" in frame.counter_hint:
            return ("选定", "错失", judge)
        if frame.counter_hint or frame.counter_clock:
            return ("选定", "窗口", judge)
        if frame.event_banner in {"CLIMAX HIT", "KILL CONFIRMED", "BOSS DOWN"}:
            return ("选定", "裁决", judge)
        return ("选定", "命中", judge)
    if record is None:
        return ("SELECT", "WAIT", judge)
    if frame.counter_hint and "[MISSED]" in frame.counter_hint:
        return ("SELECT", "MISS", judge)
    if frame.counter_hint or frame.counter_clock:
        return ("SELECT", "WINDOW", judge)
    if frame.event_banner in {"CLIMAX HIT", "KILL CONFIRMED", "BOSS DOWN"}:
        return ("SELECT", "CLIMAX", judge)
    return ("SELECT", "IMPACT", judge)


def _canvas_beat_fill(idx: int, record: TurnRecord | None, frame: BattleFrame, glyphs) -> str:
    if record is None and idx > 0:
        return glyphs.light
    if frame.counter_hint and "[MISSED]" in frame.counter_hint:
        return glyphs.mid if idx == 1 else glyphs.solid
    if frame.counter_hint or frame.counter_clock:
        return glyphs.solid if idx == 1 else glyphs.mid
    if frame.event_banner in {"CLIMAX HIT", "KILL CONFIRMED", "BOSS DOWN"}:
        return glyphs.solid
    return glyphs.mid if idx == 0 else glyphs.solid


def _block_effect_lane(
    record: TurnRecord | None,
    frame: BattleFrame,
    width: int,
    lang: str = "en",
) -> list[str]:
    if record is None:
        return block_effect_rows(
            "wait",
            "░░░ waiting for first echo ░░░" if lang == "en" else "░░░ 等待第一缕回声 ░░░",
            width,
        )
    damage = 0
    if record.judge is not None:
        damage = record.judge.damage
    if frame.event_banner == "CLIMAX HIT" or damage >= 40:
        return block_effect_rows("climax", f"▓▓▓▓▓▓▓▓▓▓▓▓ -{damage} HP", width)
    if record.side == "enemy":
        kind = (record.enemy_action or {}).get("type", "attack")
        amount = (record.enemy_action or {}).get("damage", 0)
        if kind == "chant_charge":
            return block_effect_rows("counter", _canvas_counter_rail_label(frame.counter_clock), width)
        if kind == "chant_release":
            return block_effect_rows("chant", f"CHANT RELEASE -{amount} HP", width)
        if kind == "silenced":
            return block_effect_rows("break", "CHANT BROKEN", width)
        return block_effect_rows("enemy_strike", f"STRIKE -{amount} HP", width)
    if record.action is not None:
        support_label = _canvas_support_effect_label(record, frame, lang=lang)
        if support_label:
            return block_effect_rows("guard", support_label, width)
        if record.action.type == "basic_attack":
            return block_effect_rows("strike", f"STRIKE -{damage} HP", width)
        if record.action.type == "defend":
            return block_effect_rows("guard", "GUARD ONLINE", width)
        if record.action.type == "observe":
            return block_effect_rows("observe", "SCAN FIELD", width)
        skill = record.action.skill_id or ""
        if "hex" in skill or "silent" in skill:
            return block_effect_rows("seal", f"SEAL -{damage} HP", width)
        if "sting" in skill or "corrupted" in skill:
            return block_effect_rows("shadow", f"SHADOW -{damage} HP", width)
        if "mire" in skill or "omen" in skill:
            return block_effect_rows("poison", f"VENOM -{damage} HP", width)
        if "ember" in skill or "burial" in skill:
            return block_effect_rows("fire", f"FIRE -{damage} HP", width)
        return block_effect_rows("skill", f"SKILL -{damage} HP", width)
    return block_effect_rows("wait", "PENDING", width)


def _battle_visual_tone(state: BattleState, frame: BattleFrame) -> str:
    if frame.event_banner in {
        "CLIMAX HIT",
        "BOSS PHASE II",
        "BOSS PHASE III",
        "BOSS DOWN",
        "BOSS BREAK",
        "KILL CONFIRMED",
    }:
        return "climax"
    if frame.event_banner == "BOSS CHARGE":
        return "counter"
    if frame.counter_hint and "[MISSED]" in frame.counter_hint:
        return "danger"
    if frame.counter_hint or frame.counter_clock:
        return "counter"
    if state.hero.hp / max(1, state.hero.max_hp) <= 0.3:
        return "danger"
    return "hero"


def _stage_event_title(frame: BattleFrame, lang: str) -> str:
    if frame.event_banner == "CLIMAX HIT":
        return "高潮" if lang == "zh" else "CLIMAX"
    if frame.event_banner in {"BOSS PHASE II", "BOSS PHASE III"}:
        return "首领转阶段" if lang == "zh" else "BOSS PHASE"
    if frame.event_banner == "BOSS DOWN":
        return "首领击破" if lang == "zh" else "BOSS DOWN"
    if frame.event_banner == "BOSS BREAK":
        return "首领破防" if lang == "zh" else "BOSS BREAK"
    if frame.event_banner == "KILL CONFIRMED":
        return "击杀确认" if lang == "zh" else "KILL"
    if frame.event_banner == "BOSS CHARGE":
        return "首领蓄力" if lang == "zh" else "BOSS CHARGE"
    if frame.counter_hint and "[MISSED]" in frame.counter_hint:
        return "错失反制" if lang == "zh" else "MISSED WINDOW"
    if frame.counter_hint or frame.counter_clock:
        return "反制窗口" if lang == "zh" else "COUNTER WINDOW"
    return "裂隙" if lang == "zh" else "RIFT LANE"


def _stage_header(left_title: str, center_title: str, right_title: str, *, width: int) -> str:
    left = fit_text(left_title.upper(), 36)
    center = fit_text(center_title.upper(), 18)
    right = fit_text(right_title.upper(), 35)
    return fit_text(
        f"| {pad_right(left, 36)} | {pad_right(center, 18)}| {pad_right(right, 35)} |",
        width,
    )


def _stage_director_line(
    state: BattleState,
    target: Enemy | None,
    frame: BattleFrame,
    *,
    width: int,
    lang: str,
    framed: bool = True,
) -> str:
    """Summarize the current battle beat as a compact readable director strip."""
    threat = _director_threat(state, target, frame)
    tempo = _director_tempo(state, target, lang=lang)
    focus = _director_focus(state, target, frame, lang=lang)
    if lang == "zh":
        tempo_display = tempo
        if "就绪" in tempo:
            tempo_display = "P:RDY"
        body = f"导演 | 威胁 {threat} | 节奏 {tempo_display} | 焦点 {focus}"
    else:
        body = f"DIRECTOR | THREAT {threat} | TEMPO {tempo} | FOCUS {focus}"
    if not framed:
        return fit_text(body, width)
    return fit_text(f"| {pad_right(fit_text(body, max(1, width - 4)), width - 4)} |", width)


def _stage_director_canvas_line(
    state: BattleState,
    target: Enemy | None,
    frame: BattleFrame,
    *,
    width: int,
    lang: str,
) -> str:
    threat = _director_threat(state, target, frame)
    tempo = _director_tempo(state, target, lang=lang).replace(
        "HERO READY", "HERO_RDY"
    ).replace("ENEMY READY", "ENEMY_RDY")
    focus = _director_focus(state, target, frame, lang=lang)
    focus = {
        "interrupt chant": "INTERRUPT",
        "review resources": "REVIEW",
        "pressure landed": "LANDED",
        "finish target": "FINISH",
        "stabilize HP": "STABILIZE",
        "keep tempo": "TEMPO",
        "复盘资源": "REVIEW" if lang == "en" else "复盘",
        "打断咏唱": "INTERRUPT" if lang == "en" else "打断",
        "压制完成": "LANDED" if lang == "en" else "压制",
        "收割目标": "FINISH" if lang == "en" else "收割",
        "稳住血线": "STABILIZE" if lang == "en" else "稳线",
        "保持节奏": "TEMPO" if lang == "en" else "节奏",
    }.get(focus, focus.upper()[:9] if lang == "en" else focus[:4])
    if width < 60:
        short_threat = {
            "WINDOW": "WIN",
            "RISING": "RISE",
            "MISS": "MISS",
            "CRIT": "CRIT",
            "HIGH": "HIGH",
            "LOW": "LOW",
        }.get(threat, threat[:4])
        short_tempo = (
            "RDY"
            if any(token in tempo for token in ("RDY", "READY", "就绪"))
            else tempo.replace("HERO ", "H").replace("ENEMY ", "E")
        )
        short_focus = {
            "INTERRUPT": "INT" if lang == "en" else "断",
            "STABILIZE": "STAB" if lang == "en" else "稳",
            "FINISH": "FIN" if lang == "en" else "收",
            "LANDED": "HIT" if lang == "en" else "压",
            "REVIEW": "REV" if lang == "en" else "复",
            "TEMPO": "TEM" if lang == "en" else "节",
        }.get(focus, focus[:4] if isinstance(focus, str) else "")
        if lang == "zh":
            return fit_text(
                f"{_canvas_label('director', lang)} T:{short_threat} P:{short_tempo} F:{short_focus}",
                width,
            )
        return fit_text(f"DIRECTOR T:{short_threat} P:{short_tempo} F:{short_focus}", width)
    if lang == "zh":
        return fit_text(
            f"{_canvas_label('director', lang)} | {_canvas_label('threat', lang)} {threat} | "
            f"{_canvas_label('tempo', lang)} {tempo} | {_canvas_label('focus', lang)} {focus}",
            width,
        )
    return fit_text(f"DIRECTOR | THREAT {threat} | TEMPO {tempo} | FOCUS {focus}", width)


def _director_threat(state: BattleState, target: Enemy | None, frame: BattleFrame) -> str:
    if frame.counter_hint and "[MISSED]" in frame.counter_hint:
        return "MISS"
    if frame.counter_hint or frame.counter_clock:
        return "WINDOW"
    hero_ratio = state.hero.hp / max(1, state.hero.max_hp)
    if hero_ratio <= 0.3:
        return "CRIT"
    if target is not None and target.atb >= 95:
        return "HIGH"
    if any(enemy.atb >= 85 for enemy in state.alive_enemies()):
        return "RISING"
    return "LOW"


def _director_tempo(state: BattleState, target: Enemy | None, *, lang: str = "en") -> str:
    if lang == "zh":
        if state.hero.atb >= 100:
            return "英雄 就绪"
        if target is not None and target.atb >= 100:
            return "敌方 就绪"
        if target is not None and target.atb >= 85:
            return f"敌方 {target.atb}/100"
        return f"英雄 {min(100, state.hero.atb)}/100"
    if state.hero.atb >= 100:
        return "HERO READY"
    if target is not None and target.atb >= 100:
        return "ENEMY READY"
    if target is not None and target.atb >= 85:
        return f"ENEMY {target.atb}/100"
    return f"HERO {min(100, state.hero.atb)}/100"


def _director_focus(
    state: BattleState,
    target: Enemy | None,
    frame: BattleFrame,
    *,
    lang: str,
) -> str:
    if frame.counter_hint and "[MISSED]" in frame.counter_hint:
        return "复盘资源" if lang == "zh" else "review resources"
    if frame.counter_hint or frame.counter_clock:
        return "打断咏唱" if lang == "zh" else "interrupt chant"
    if frame.event_banner in {"CLIMAX HIT", "KILL CONFIRMED", "BOSS DOWN"}:
        return "压制完成" if lang == "zh" else "pressure landed"
    if target is not None and target.hp / max(1, target.max_hp) <= 0.25:
        return "收割目标" if lang == "zh" else "finish target"
    if state.hero.hp / max(1, state.hero.max_hp) <= 0.3:
        return "稳住血线" if lang == "zh" else "stabilize HP"
    return "保持节奏" if lang == "zh" else "keep tempo"


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


def _hero_hud(
    hero: Hero,
    *,
    lang: str,
    unicode_mode: bool,
    enhanced: bool = False,
) -> list[str]:
    hp_str = hp_bar(
        hero.hp,
        hero.max_hp,
        width=8,
        unicode_mode=unicode_mode,
        show_percent=enhanced,
        show_value=True,
        enhanced=enhanced,
    )
    mp_str = mp_bar(
        hero.mp,
        hero.max_mp,
        width=6,
        unicode_mode=unicode_mode,
        show_percent=False,
        show_value=True,
        enhanced=enhanced,
    )
    atb_str = atb_bar(
        min(hero.atb, 100),
        100,
        width=6,
        unicode_mode=unicode_mode,
        show_ready=enhanced,
        enhanced=enhanced,
    )
    return [
        f"HP {hp_str}",
        f"MP {mp_str}  ATB {atb_str}",
    ]


def _enemy_hud(
    enemy: Enemy,
    *,
    lang: str,
    unicode_mode: bool,
    enhanced: bool = False,
) -> list[str]:
    hp_str = hp_bar(
        enemy.hp,
        enemy.max_hp,
        width=8,
        unicode_mode=unicode_mode,
        show_percent=enhanced,
        show_value=True,
        enhanced=enhanced,
    )
    atb_str = atb_bar(
        min(enemy.atb, 100),
        100,
        width=6,
        unicode_mode=unicode_mode,
        show_ready=enhanced,
        enhanced=enhanced,
    )
    down = f" {label('down', lang)}" if not enemy.is_alive else ""
    charge = (
        f" charge {enemy.chant_progress}/{enemy.chant_charge_turns}"
        if enemy.chant_charge_turns
        else ""
    )
    lines = [
        f"HP {hp_str}{down}",
        f"ATB {atb_str}{charge}",
    ]
    if enemy.tier == "archive_bound":
        lines.append(_boss_enemy_hud(enemy, lang=lang))
    return lines


def _boss_enemy_hud(enemy: Enemy, *, lang: str) -> str:
    ratio = enemy.hp / max(1, enemy.max_hp)
    if not enemy.is_alive:
        phase = "P-CLR"
    elif ratio > 0.66:
        phase = "P1"
    elif ratio > 0.33:
        phase = "P2"
    else:
        phase = "P3"
    charge = (
        f"CHG {enemy.chant_progress}/{enemy.chant_charge_turns}"
        if enemy.chant_charge_turns
        else "CHG -"
    )
    if lang == "zh":
        return f"BOSS {phase} {charge} 破防看蓄力"
    return f"BOSS {phase} {charge} BREAK via window"


def _boss_intel_summary(frame: BattleFrame, lang: str) -> str:
    intel = frame.boss_intel
    if intel is None:
        return ""
    if lang == "zh":
        return _director_text(
            f"BOSS {intel.name} | {intel.phase} | {intel.charge} | "
            f"{intel.break_state} | {intel.enrage}",
            lang,
        )
    return (
        f"BOSS {intel.name} | {intel.phase} | {intel.charge} | "
        f"{intel.break_state} | {intel.enrage}"
    )


def _status_groups(statuses: list, *, lang: str) -> list[str]:
    buffs = [_format_status(s) for s in statuses if _status_kind(s.id) == "BUFF"]
    debuffs = [_format_status(s) for s in statuses if _status_kind(s.id) == "DEBUFF"]
    lines = []
    if buffs:
        lines.append(f"{label('hud_buff', lang)}   : " + ", ".join(buffs[:4]))
    if debuffs:
        lines.append(f"{label('hud_debuff', lang)} : " + ", ".join(debuffs[:4]))
    if not lines:
        lines.append(f"{label('status_label', lang)}: {label('status_none', lang)}")
    return lines


def _format_status(status) -> str:
    return format_status_short(status)


def _status_kind(status_id: str) -> str:
    if status_id in {"status_shield", "status_focus", "status_haste", "status_guard"}:
        return "BUFF"
    return "DEBUFF"


def _render_build_line(
    hero: Hero,
    bundle: ContentBundle | None = None,
    build: ResolvedBuild | None = None,
    *,
    lang: str = DEFAULT_LANGUAGE,
) -> list[str]:
    weapon, build_badge = _hero_icons(hero)

    lines = [f"{label('hud_weapon', lang)} {weapon}        {label('hud_build', lang)} {build_badge}"]

    if bundle is not None and build is not None:
        progress = build.calculate_progress(bundle)
        next_picks: list[str] = []
        need_tags: list[str] = []

        seen_picks: set[str] = set()
        for pick in progress.best_next_picks[:3]:
            tag = pick["tag"]
            if tag in seen_picks:
                continue
            seen_picks.add(tag)
            need = pick["need"]
            res_name = pick["resonance_name"].get(lang) or pick["resonance_name"].get("en", "")
            next_picks.append(f"{tag} affix / {res_name} relic")
            need_tags.append(f"{tag} +{need}")

        if next_picks:
            shown_picks = next_picks[:2]
            if len(next_picks) > 2:
                extra = f"+{len(next_picks) - 2} more" if lang == "en" else f"+{len(next_picks) - 2}项"
                shown_picks.append(extra)
            next_pick_str = " | ".join(shown_picks)
            need_str = ", ".join(need_tags[:2])
            next_stage = {
                BuildStage.SEED: label("build_stage_seed", lang),
                BuildStage.PAIR: label("build_stage_pair", lang),
                BuildStage.ONLINE: label("build_stage_online", lang),
                BuildStage.HIGH_ROLL: label("build_stage_high", lang),
                BuildStage.LOCKED_IN: label("build_stage_locked", lang),
            }.get(progress.stage, label("build_stage_next", lang))
            lines.append(f"{label('next_pick', lang)}: {next_pick_str}")
            lines.append(f"{label('need', lang)}: {need_str} for {next_stage}")
        else:
            lines.append(label("build_complete", lang))
    else:
        lines.append(label("build_pending", lang))

    return lines


def _hero_icons(hero: Hero) -> tuple[str, str]:
    return battle_weapon_line(hero.short_tag)


def _render_session_panel(
    record: TurnRecord | None,
    *,
    provider_label: str,
    lang: str = DEFAULT_LANGUAGE,
) -> list[str]:
    battle_echo = record.battle_session_id if record and record.battle_session_id else "-"
    sealed = record.static_context_hash if record and record.static_context_hash else "-"
    fresh = record.delta_context_id if record and record.delta_context_id else "-"
    tokens = record.usage_total_tokens if record else 0
    latency = record.usage_latency_ms if record else 0
    return [
        label("model_session", lang),
        f"{label('battle_echo', lang)}: {battle_echo}   {label('provider_label', lang)}: {provider_label}   {label('sealed_echo', lang)}: {sealed}",
        f"{label('fresh_echo', lang)}: {fresh}   {label('echo_cost', lang)}: {tokens} {label('tokens_unit', lang)}   {label('ritual_time', lang)}: {latency}ms",
    ]


def _render_action_focus_panel(
    frame: BattleFrame,
    *,
    width: int,
    lang: str,
) -> list[str]:
    action_title = "ACTION" if lang == "en" else "行动"
    intent_title = "INTENT" if lang == "en" else "意图"
    risk_title = "RISK" if lang == "en" else "风险"
    align_title = "ALIGN" if lang == "en" else "契合"
    impact_title = "IMPACT" if lang == "en" else "影响"
    delta_title = "DELTA" if lang == "en" else "变化"
    banner_title = "EVENT" if lang == "en" else "事件"
    counter_title = "COUNTER" if lang == "en" else "反制"
    max_text = max(24, width - 10)

    lines = [
        f"{fit_text(_director_text(frame.action_label + ' | ' + frame.judge_label, lang), max_text)}",
        f"{intent_title}  {fit_text(_director_text(frame.intent, lang), max_text)}",
        f"{risk_title}    {fit_text(_director_text(frame.risk, lang), max_text)}",
        f"{align_title}   {fit_text(_director_text(frame.align, lang), max_text)}",
    ]
    if frame.boss_intel:
        boss_title = "BOSS" if lang == "en" else "首领"
        break_title = "BREAK" if lang == "en" else "破防"
        enrage_title = "ENRAGE" if lang == "en" else "狂暴"
        lines.extend(
            [
                f"{boss_title}    {fit_text(_director_text(frame.boss_intel.phase + ' | ' + frame.boss_intel.charge, lang), max_text)}",
                f"{break_title}   {fit_text(_director_text(frame.boss_intel.break_state, lang), max_text)}",
                f"{enrage_title} {fit_text(_director_text(frame.boss_intel.enrage, lang), max_text)}",
            ]
        )
    if frame.impact_line:
        lines.append(f"{impact_title}  {fit_text(_director_text(frame.impact_line, lang), max_text)}")
    if frame.resource_deltas:
        for delta in frame.resource_deltas:
            text = f"{delta.label} {_director_text(delta.text, lang)}"
            lines.append(f"{delta_title}   {fit_text(text, max_text)}")
    if frame.counter_clock:
        counter_clock = _director_text(frame.counter_clock, lang)
        if counter_clock.startswith("COUNTER "):
            lines.append(fit_text(counter_clock, width))
        else:
            lines.append(f"{counter_title} {fit_text(counter_clock, max_text)}")
    if frame.counter_hint:
        lines.append(f"{counter_title} {fit_text(_director_text(frame.counter_hint, lang), max_text)}")
    if frame.event_banner:
        lines.append(f"{banner_title}   {frame.event_banner}")
    return list(pixel_panel(action_title, [fit_text(line, max_text) for line in lines], width, tone=_frame_tone(frame)).lines)


def _render_cinematic_beat_panel(
    state: BattleState,
    last_record: TurnRecord | None,
    *,
    frame: BattleFrame,
    width: int,
    lang: str,
) -> list[str]:
    title = "CINEMATIC BEAT" if lang == "en" else "战斗分镜"
    max_text = max(24, width - 10)

    hero = state.hero
    hero_hp_pct = hero.hp / max(1, hero.max_hp)
    hero_mp_pct = hero.mp / max(1, hero.max_mp)
    vox_raw = _select_hero_line(
        hero_id=hero.id,
        hp_pct=hero_hp_pct,
        mp_pct=hero_mp_pct,
        record=last_record,
        frame=frame,
        lang=lang,
    )
    enm_raw = _select_enemy_line(state, last_record, frame, lang=lang, width=max_text)
    float_raw = _build_cinematic_float(frame, width=max_text, lang=lang)
    strip_raw = _build_cinematic_strip(frame, lang=lang, width=max_text)
    log_lines = _build_cinematic_logs(state.log[-2:], lang=lang, width=max_text)

    body = [
        f"VOX   {fit_text(_director_text(vox_raw, lang), max_text)}",
        f"ENM   {fit_text(_director_text(enm_raw, lang), max_text)}",
        f"{'FLOAT' if lang == 'en' else '浮字'} {fit_text(float_raw, max_text)}",
        f"{'STRIP' if lang == 'en' else '节奏'} {fit_text(strip_raw, max_text)}",
    ]
    body.extend(
        f"{'LOG' if lang == 'en' else '日志'}   {fit_text(line, max_text)}" if line else f"{'LOG' if lang == 'en' else '日志'}   {label('no_events', lang)}"
        for line in log_lines
    )
    if not log_lines:
        body.append(f"{'LOG' if lang == 'en' else '日志'}   {label('no_events', lang)}")

    return list(pixel_panel(title, body, width, tone=_frame_tone(frame)).lines)


def _select_enemy_line(
    state: BattleState,
    record: TurnRecord | None,
    frame: BattleFrame,
    *,
    lang: str,
    width: int,
) -> str:
    target = _screen_target(state, record)
    line = _canvas_enemy_dialogue(
        target,
        record,
        frame,
        lang=lang,
        width=width,
    )
    if line.startswith("ENM "):
        line = line[4:]
    return line


def _build_cinematic_float(
    frame: BattleFrame,
    *,
    width: int,
    lang: str = "en",
) -> str:
    if frame.floating_numbers:
        values = [value for value in frame.floating_numbers if value]
        if values:
            return " | ".join(values)

    impact = _canvas_impact_label(frame.impact_line) if frame.impact_line else ""
    if impact:
        return fit_text(impact, width)
    if lang == "zh":
        return "无"
    return "none"


def _build_cinematic_strip(
    frame: BattleFrame,
    *,
    lang: str,
    width: int,
) -> str:
    windup = "windup" if lang == "en" else "起势"
    lane = frame.effect_glyph or frame.effect_kind or "lane"
    if lang == "zh" and lane == "lane":
        lane = "通道"
    impact = _canvas_impact_label(frame.impact_line) if frame.impact_line else ("impact" if lang == "en" else "命中")
    judge = frame.judge_label.split("|", 1)[0].strip() if frame.judge_label else ("WAIT" if lang == "en" else "等待")
    if lang == "zh":
        judge = _director_text(judge, lang)
        impact = _director_text(impact, lang)

    strip = f"{windup} -> {lane} -> {_director_text(impact, lang)} -> {_director_text(judge, lang)}"
    return fit_text(_fit_visual(strip, width), width)


def _build_cinematic_logs(logs: list[str], *, lang: str, width: int) -> list[str]:
    if not logs:
        return []
    compacted: list[str] = []
    for event in logs[:2]:
        compact = _compact_battle_log_event(event)
        compacted.append(_director_text(_fit_visual(compact, width), lang))
    return compacted


def _render_build_climax_panel(
    build: ResolvedBuild | None,
    *,
    bundle: ContentBundle | None,
    width: int,
    lang: str,
    show_opening: bool,
) -> list[str]:
    if build is None or bundle is None or not show_opening:
        return []
    progress = build.calculate_progress(bundle)
    event = None
    if progress.stage == BuildStage.ONLINE:
        event = "BUILD ONLINE"
    elif progress.stage in {BuildStage.HIGH_ROLL, BuildStage.LOCKED_IN}:
        event = "HIGH ROLL"
    if event is None:
        return []
    title = "CLIMAX" if lang == "en" else "高潮"
    body = [
        f"EVENT   {event}",
        f"BUILD   {build.archetype(lang)} {progress.stage.badge}",
    ]
    if progress.active_resonances:
        names = _resonance_display_names(bundle, progress.active_resonances[:2], lang)
        body.append(f"RESONANCE {', '.join(names)}")
    return list(pixel_panel(title, [fit_text(line, width - 4) for line in body], width, tone="climax").lines)


def _resonance_display_name(bundle: ContentBundle | None, resonance_id: str, lang: str) -> str:
    if bundle is None:
        return resonance_id
    resonance = bundle.resonances.get(resonance_id)
    if resonance is None:
        return resonance_id
    return resonance.display_name.get(lang) or resonance.display_name.get("en", resonance_id)


def _resonance_display_names(bundle: ContentBundle | None, resonance_ids: list[str], lang: str) -> list[str]:
    return [_resonance_display_name(bundle, resonance_id, lang) for resonance_id in resonance_ids]


def _frame_tone(frame: BattleFrame) -> str:
    if frame.event_banner in {"CLIMAX HIT", "BOSS PHASE II", "BOSS PHASE III", "BOSS DOWN", "BOSS BREAK"}:
        return "climax"
    if frame.event_banner == "BOSS CHARGE":
        return "counter"
    if frame.counter_hint and "[MISSED]" in frame.counter_hint:
        return "danger"
    if frame.counter_hint or frame.counter_clock:
        return "counter"
    return "normal"


def _render_battle_momentum_panel(
    state: BattleState,
    frame: BattleFrame,
    record: TurnRecord | None,
    *,
    width: int,
    lang: str,
) -> list[str]:
    target = _screen_target(state, record)
    living = [enemy for enemy in state.enemies if enemy.is_alive]
    enemy_hp = sum(enemy.hp for enemy in living)
    enemy_max_hp = sum(enemy.max_hp for enemy in living) or 1
    hero_ratio = state.hero.hp / max(1, state.hero.max_hp)
    enemy_ratio = enemy_hp / enemy_max_hp
    peak_atb = max((enemy.atb for enemy in living), default=0)
    target_name = target.name if target is not None else ("cleared" if lang == "en" else "已清场")
    flow = _battle_momentum_flow(state, frame, target, peak_atb=peak_atb, hero_ratio=hero_ratio, enemy_ratio=enemy_ratio, lang=lang)
    swing = _battle_momentum_swing(record, frame, lang=lang)
    read = _battle_momentum_read(state, frame, target, peak_atb=peak_atb, hero_ratio=hero_ratio, enemy_ratio=enemy_ratio, lang=lang)
    hero_bar = bar(state.hero.hp, state.hero.max_hp, width=8, unicode_mode=False)
    enemy_bar = bar(enemy_hp, enemy_max_hp, width=8, unicode_mode=False)
    max_text = max(24, width - 4)
    if lang == "zh":
        body = [
            f"[流势] {flow} | 敌方 ATB {peak_atb}",
            f"[战线] 英雄 {hero_bar} {state.hero.hp}/{state.hero.max_hp} vs 敌方 {enemy_bar} {enemy_hp}/{enemy_max_hp}",
            f"[目标] {target_name}",
            f"[波动] {swing}",
            f"[读法] {read}",
        ]
        return list(pixel_panel("战斗势能板", [fit_text(line, max_text) for line in body], width, tone=_battle_momentum_tone(flow)).lines)
    body = [
        f"[FLOW] {flow} | enemy ATB {peak_atb}",
        f"[LANE] HERO {hero_bar} {state.hero.hp}/{state.hero.max_hp} vs ENEMY {enemy_bar} {enemy_hp}/{enemy_max_hp}",
        f"[TARGET] {target_name}",
        f"[SWING] {swing}",
        f"[READ] {read}",
    ]
    return list(pixel_panel("MOMENTUM BOARD", [fit_text(line, max_text) for line in body], width, tone=_battle_momentum_tone(flow)).lines)


def _battle_momentum_flow(
    state: BattleState,
    frame: BattleFrame,
    target: Enemy | None,
    *,
    peak_atb: int,
    hero_ratio: float,
    enemy_ratio: float,
    lang: str,
) -> str:
    if not target or not any(enemy.is_alive for enemy in state.enemies):
        return "CLEAR" if lang == "en" else "清场"
    if frame.counter_clock or frame.counter_hint:
        return "WINDOW" if lang == "en" else "窗口"
    if hero_ratio <= 0.3:
        return "DANGER" if lang == "en" else "危险"
    if peak_atb >= 90:
        return "PRESSURE" if lang == "en" else "受压"
    if enemy_ratio <= 0.35 or (target and target.hp / max(1, target.max_hp) <= 0.3):
        return "ADVANTAGE" if lang == "en" else "优势"
    return "EVEN" if lang == "en" else "均势"


def _battle_momentum_swing(record: TurnRecord | None, frame: BattleFrame, *, lang: str) -> str:
    if record is None:
        return "waiting for first action" if lang == "en" else "等待首次行动"
    damage = record.judge.damage if record.judge is not None else 0
    if record.side == "hero":
        if damage > 0:
            return f"hero hit -{damage} HP"
        if frame.counter_hint:
            return _director_text(frame.counter_hint, lang)
        return _director_text(frame.action_label, lang)
    action = record.enemy_action or {}
    amount = action.get("damage", 0)
    kind = action.get("type", "attack")
    if kind == "chant_charge":
        return "enemy chant charging" if lang == "en" else "敌方吟唱蓄力"
    if kind == "chant_release":
        return f"enemy chant -{amount} HP"
    if amount:
        return f"enemy hit -{amount} HP"
    return "enemy action resolved" if lang == "en" else "敌方行动结算"


def _battle_momentum_read(
    state: BattleState,
    frame: BattleFrame,
    target: Enemy | None,
    *,
    peak_atb: int,
    hero_ratio: float,
    enemy_ratio: float,
    lang: str,
) -> str:
    if target is None or not any(enemy.is_alive for enemy in state.enemies):
        return "battle is closing; preserve resources" if lang == "en" else "战斗收束；保留资源"
    if frame.counter_clock or frame.counter_hint:
        return "answer the window before damage races ahead" if lang == "en" else "先回应窗口，避免伤害失控"
    if hero_ratio <= 0.3:
        return "stabilize HP before trading tempo" if lang == "en" else "换节奏前先稳住血线"
    if peak_atb >= 90:
        return "interrupt or finish the fastest threat" if lang == "en" else "打断或击杀最快威胁"
    if enemy_ratio <= 0.35:
        return "convert advantage into a clean finish" if lang == "en" else "把优势转成干净收尾"
    if state.hero.atb >= 100:
        return "hero is ready; spend the turn with intent" if lang == "en" else "英雄已就绪；带着意图行动"
    return "watch ATB lanes before spending MP" if lang == "en" else "花 MP 前先看 ATB 轨道"


def _battle_momentum_tone(flow: str) -> str:
    if flow in {"DANGER", "危险"}:
        return "danger"
    if flow in {"WINDOW", "窗口", "PRESSURE", "受压"}:
        return "counter"
    if flow in {"ADVANTAGE", "优势", "CLEAR", "清场"}:
        return "climax"
    return "normal"


def _director_text(text: str, lang: str) -> str:
    if lang != "zh":
        return text
    replacements = {
        "Phase Clear": "阶段结束",
        "Phase I": "阶段 I",
        "Phase II": "阶段 II",
        "Phase III": "阶段 III",
        "Opening Rite": "开场仪式",
        "Black Index": "黑索引",
        "Archive Unbound": "档案解封",
        "archive sealed": "档案封存",
        "Charge": "蓄力",
        "FULL release threat": "已满，释放威胁",
        "WINDOW interrupt now": "窗口开启，立即打断",
        "arming": "蓄力中",
        "Break": "破防",
        "boss break by tower counter on": "塔盾反击破防:",
        "BROKEN by control": "已被控制破防",
        "OPEN": "开启",
        "interrupt/control before release": "释放前打断/控制",
        "EXECUTE": "处决",
        "focus damage": "集火输出",
        "locked": "锁定",
        "wait for charge or expose": "等待蓄力或破绽",
        "resolved": "已解决",
        "WAIT": "待",
        "Enrage": "狂暴",
        "cleared": "解除",
        "ACTIVE": "启动",
        "tempo collapse risk": "节奏崩溃风险",
        "rising": "上升",
        "dormant": "未启动",
        "next interrupt: yes": "下次可打断: 是",
        "next interrupt: no": "下次可打断: 否",
        "interrupt ready: yes": "打断就绪: 是",
        "interrupt ready: no": "打断就绪: 否",
        "COUNTER CLOCK": "反制时钟",
        "NEXT HERO CAN INTERRUPT": "下次英雄可打断",
        "not ready": "未就绪",
        "ready": "已就绪",
        "no interrupt skill": "无打断技能",
        "window opened": "窗口开启",
        "chant released": "吟唱释放",
        "chant_charge": "吟唱蓄力",
        "chant_release": "吟唱释放",
        "basic_attack": "普通攻击",
        "enemy chant pressure": "敌方吟唱施压",
        "enemy pressures the hero": "敌人压迫英雄血线",
        "release grows closer": "释放正在逼近",
        "HP loss may open lethal range": "失血可能进入斩杀线",
        "Counter window": "反制窗口",
        "Local AI": "本地 AI",
        "spends tempo resource": "消耗节奏资源",
        "read the field": "读取战场",
        "unknown until an action is selected": "行动选择前未知",
        "Prompt pending": "等待提示词",
        "awaiting first action": "等待第一次行动",
        "control the fastest threat": "控制最快威胁",
        "convert MP into pressure with": "用 MP 转化为压力:",
        "Prompt: Control hit | Build: shadow/control": "提示词: 控制命中 | Build: 暗影/控制",
        "Prompt: damage tempo | Build skill": "提示词: 输出节奏 | Build 技能",
        "LOCAL": "本地",
        "VALID": "有效",
        "FALLBACK": "回退",
        "PENDING": "等待",
        "overkill": "溢出",
        "fallback": "回退",
        "[WINDOW]": "[窗口]",
        "[ANSWER]": "[回应]",
        "[MISSED]": "[错失]",
        "interrupt before release": "在释放前打断",
        "released the chant": "释放了吟唱",
        "review MP/cooldown timing": "检查 MP/冷却时机",
        "counter answered on": "反制已回应:",
        "counter failed on": "反制失败:",
    }
    result = text
    for source, target in replacements.items():
        result = result.replace(source, target)
    return result


def _render_battle_objective_panel(
    state: BattleState,
    frame: BattleFrame,
    record: TurnRecord | None,
    *,
    width: int,
    lang: str,
) -> list[str]:
    if lang == "zh":
        titles = ("目标", "威胁", "失败条件", "下一步")
    else:
        titles = ("GOAL", "CLOCK", "FAIL IF", "NEXT")
    target = _screen_target(state, record)
    plan = _battle_win_plan(state, target, frame, lang=lang)
    clock = _battle_threat_clock(state, target, lang=lang)
    fail_if = _battle_fail_if(state, target, frame, lang=lang)
    next_step = _battle_next_step(state, target, frame, lang=lang)
    max_text = max(24, width - 10)
    lines = [
        f"{titles[0]}   {fit_text(plan, max_text)}",
        f"{titles[1]}  {fit_text(clock, max_text)}",
        f"{titles[2]} {fit_text(fail_if, max_text)}",
        f"{titles[3]}   {fit_text(next_step, max_text)}",
    ]
    title = "BATTLE THESIS" if lang == "en" else "战斗命题"
    return list(pixel_panel(title, [fit_text(line, max_text) for line in lines], width, tone=_frame_tone(frame)).lines)


def _render_evidence_panel(
    state: BattleState,
    record: TurnRecord | None,
    *,
    frame: BattleFrame,
    provider_label: str,
    action_strip_word: str,
    width: int,
    lang: str,
) -> list[str]:
    body: list[str] = []
    session = _render_session_panel(record, provider_label=provider_label, lang=lang)
    body.extend(session[1:])
    body.append(f"{action_strip_word}  select -> windup -> effect lane -> impact -> judge")
    body.extend(_render_battle_film_lines(state, record, frame=frame, lang=lang))
    title = "ECHO READOUT" if lang == "en" else "回声读数"
    return list(pixel_panel(title, [fit_text(line, width - 4) for line in body], width, tone="quiet").lines)


def _render_battle_film_lines(
    state: BattleState,
    record: TurnRecord | None,
    *,
    frame: BattleFrame,
    lang: str,
) -> list[str]:
    if lang == "zh":
        if record is not None and record.side == "enemy":
            header = "敌方行动 / 战斗分镜"
        else:
            header = f"{label('model_turn', lang)} / 战斗分镜"
        model_label = "模型"
        enemy_label = "敌方"
        judge_label = "裁判"
        log_label = label("log", lang)
        no_log = label("no_events", lang)
    else:
        if record is not None and record.side == "enemy":
            header = "ENEMY TURN / BEAT FILM"
        else:
            header = f"{label('model_turn', lang)} / BEAT FILM"
        model_label = "MODEL"
        enemy_label = "ENEMY"
        judge_label = "JUDGE"
        log_label = label("log", lang)
        no_log = label("no_events", lang)

    actor_label = model_label
    if record is None:
        model_text = label("awaiting", lang)
    elif record.side == "enemy":
        actor_label = enemy_label
        model_text = _battle_film_enemy_action_text(record, frame, lang=lang)
    else:
        model_text = _director_text(frame.action_label, lang)

    judge_text = _battle_film_judge_text(frame, lang=lang)
    latest_log = _battle_film_log_text(state.log[-2:], no_log=no_log)

    return [
        header,
        f"[01 {actor_label}] {label('action_label', lang)}: {model_text}",
        f"[02 {judge_label}] {label('judge_label', lang)}: {judge_text}",
        f"[03 {log_label}] {latest_log}",
    ]


def _battle_film_enemy_action_text(record: TurnRecord, frame: BattleFrame, *, lang: str) -> str:
    text = _director_text(frame.action_label, lang)
    if lang == "zh":
        return text
    action_type = str((record.enemy_action or {}).get("type", ""))
    suffixes = {
        "basic_attack": "STRIKE",
        "attack": "STRIKE",
        "chant_charge": "CHARGE",
        "chant_release": "RELEASE",
        "silenced": "SILENCED",
    }
    suffix = suffixes.get(action_type)
    if suffix:
        base = text.rsplit(" ", 1)[0] if text.endswith(f" {action_type}") else text
        return f"{base} {suffix}"
    return text


def _battle_film_log_text(logs: list[str], *, no_log: str) -> str:
    if not logs:
        return no_log
    return " / ".join(_compact_battle_log_event(log) for log in logs)


def _battle_film_judge_text(frame: BattleFrame, *, lang: str) -> str:
    status = frame.judge_label.split("|", 1)[0].strip()
    status = _director_text(status, lang)
    if not frame.impact_line:
        return status
    impact = _canvas_impact_label(frame.impact_line)
    return f"{status} {impact}".strip()


def _compact_battle_log_event(log: str) -> str:
    text = " ".join(log.split())
    lower = text.lower()
    amount = _first_number(text)
    mp = _mp_cost_token(text)
    if "casts hex seal" in lower:
        return _join_tokens("CAST HEX", mp, f"HIT-{amount}" if "damage" in lower and amount else "")
    if "casts shadow sting" in lower:
        return _join_tokens("CAST STING", mp)
    if "casts corrupted focus" in lower:
        return _join_tokens("CAST FOCUS", "SHD", mp)
    if "chant breaks" in lower or "under silence" in lower:
        return "CHANT BREAK"
    if "continues a low chant" in lower:
        return "CHANT +1"
    if "releases a shadow chant" in lower:
        return f"CHANT -{amount}" if amount else "CHANT RELEASE"
    if "shield absorbs" in lower:
        return f"SHD -{amount}" if amount else "SHD ABSORB"
    if "hits astia" in lower:
        return f"STRIKE -{amount}" if amount else "STRIKE"
    if "is silenced" in lower:
        target = "CULTIST" if "hungry cultist" in lower else "ENEMY"
        return f"SLN {target}"
    return _fit_visual(text, 42)


def _mp_cost_token(text: str) -> str:
    match = re.search(r"-MP\s*(\d+)", text)
    return f"-MP{match.group(1)}" if match else ""


def _first_number(text: str) -> str:
    match = re.search(r"\d+", text)
    return match.group(0) if match else ""


def _join_tokens(*tokens: str) -> str:
    return " ".join(token for token in tokens if token)


def _battle_win_plan(
    state: BattleState,
    target: Enemy | None,
    frame: BattleFrame,
    *,
    lang: str,
) -> str:
    living = state.alive_enemies()
    if not living:
        return "结算胜利并保留资源" if lang == "zh" else "secure victory and preserve resources"
    if target is None:
        return "寻找首个可击杀目标" if lang == "zh" else "find the first legal kill target"
    hp_ratio = target.hp / max(1, target.max_hp)
    if frame.event_banner == "BREAK WINDOW OPEN" or target.chant_progress:
        return (
            f"打断 {target.name}，阻止吟唱爆发"
            if lang == "zh"
            else f"interrupt {target.name} before the chant releases"
        )
    if hp_ratio <= 0.35:
        return (
            f"集火 {target.name}，把低血量转成击杀"
            if lang == "zh"
            else f"focus {target.name}; convert low HP into a kill"
        )
    if len(living) > 1:
        return (
            "先削减敌方数量，降低后续 ATB 压力"
            if lang == "zh"
            else "thin the roster first to reduce ATB pressure"
        )
    return (
        f"稳定输出 {target.name}，保留一次防守或打断余量"
        if lang == "zh"
        else f"pressure {target.name} while saving one defensive/interruption line"
    )


def _battle_threat_clock(state: BattleState, target: Enemy | None, *, lang: str) -> str:
    chant_enemies = [e for e in state.alive_enemies() if e.chant_charge_turns]
    if chant_enemies:
        closest = max(chant_enemies, key=lambda e: e.chant_progress)
        remaining = max(0, closest.chant_charge_turns - closest.chant_progress)
        if remaining == 0:
            return (
                f"{closest.name} 吟唱已满；下一次行动可能爆发"
                if lang == "zh"
                else f"{closest.name} chant is full; next action may release"
            )
        return (
            f"{closest.name} 吟唱还差 {remaining} 次蓄力"
            if lang == "zh"
            else f"{closest.name} chant needs {remaining} more charge"
        )
    if target is not None and target.atb >= 80:
        if not target.is_alive:
            return "敌方威胁已解除" if lang == "zh" else "enemy threat is cleared"
        return (
            f"{target.name} ATB 接近行动"
            if lang == "zh"
            else f"{target.name} ATB is close to acting"
        )
    hp_ratio = state.hero.hp / max(1, state.hero.max_hp)
    if hp_ratio <= 0.3:
        return "英雄血线危险，任何伤害都可能致命" if lang == "zh" else "hero HP is critical; any hit may become lethal"
    return "威胁可控，适合推进输出节奏" if lang == "zh" else "threat is controlled; push damage tempo"


def _battle_fail_if(
    state: BattleState,
    target: Enemy | None,
    frame: BattleFrame,
    *,
    lang: str,
) -> str:
    chant_enemies = [e for e in state.alive_enemies() if e.chant_charge_turns]
    ready_chant = [e for e in chant_enemies if e.chant_progress >= e.chant_charge_turns]
    if ready_chant:
        enemy = ready_chant[0]
        return (
            f"{enemy.name} 下次行动完成吟唱且英雄无法承伤"
            if lang == "zh"
            else f"{enemy.name} acts again with a full chant and HP cannot absorb it"
        )
    if target is not None and target.hp / max(1, target.max_hp) <= 0.25 and target.atb >= 80:
        if not target.is_alive:
            return "胜利结算前没有新失败条件" if lang == "zh" else "no new failure before victory resolves"
        return (
            f"没能在 {target.name} 行动前收掉残血"
            if lang == "zh"
            else f"the low-HP {target.name} survives until its next action"
        )
    if state.hero.hp / max(1, state.hero.max_hp) <= 0.35:
        return "继续空转而不防御或击杀" if lang == "zh" else "the model drifts instead of defending or killing"
    if frame.event_banner == "CLIMAX HIT":
        return "高潮后没有保留下一波资源" if lang == "zh" else "the spike leaves no resource for the next wave"
    return "资源被低收益行动消耗" if lang == "zh" else "tempo resources are spent on low-impact turns"


def _battle_next_step(
    state: BattleState,
    target: Enemy | None,
    frame: BattleFrame,
    *,
    lang: str,
) -> str:
    if target is None:
        return "等待模型选择合法目标" if lang == "zh" else "wait for a legal target"
    if not target.is_alive:
        return "敌人已倒下，进入结算" if lang == "zh" else "enemy is down; resolve the win"
    if target.chant_progress:
        interrupt = _first_interrupt_skill(state.hero)
        if interrupt is not None and interrupt.is_ready(state.hero.mp):
            return (
                f"优先 {interrupt.display_name}；反制已就绪"
                if lang == "zh"
                else f"prefer {interrupt.display_name}; counter is ready"
            )
        if interrupt is not None and interrupt.cooldown_remaining > 0:
            return (
                f"{interrupt.display_name} 冷却中，先击杀或防守"
                if lang == "zh"
                else f"{interrupt.display_name} is cooling down; race the kill or defend"
            )
        return (
            "打断资源不足，改用击杀或防守减伤"
            if lang == "zh"
            else "interrupt is not funded; race the kill or defend"
        )
    lethal = _basic_attack_lethal(state.hero, target)
    if lethal:
        return "普攻可击杀，保留 MP 给下一波" if lang == "zh" else "basic attack can kill; save MP for the next wave"
    ready_damage = [s for s in state.hero.skills if s.is_ready(state.hero.mp) and s.target_rule != "self"]
    if ready_damage:
        skill = ready_damage[0]
        return (
            f"用 {skill.display_name} 建立击杀线"
            if lang == "zh"
            else f"use {skill.display_name} to create a kill line"
        )
    if state.hero.hp / max(1, state.hero.max_hp) <= 0.4:
        return "技能未就绪，防御比空转更安全" if lang == "zh" else "skills are not ready; defend rather than drift"
    return frame.intent


def _first_interrupt_skill(hero: Hero) -> SkillState | None:
    for skill in hero.skills:
        if any(token in skill.id for token in ("hex", "silent", "seal", "stagger")):
            return skill
    return None


def _basic_attack_lethal(hero: Hero, enemy: Enemy) -> bool:
    damage = max(1, hero.attack - enemy.defense // 2)
    return enemy.hp <= damage


def _actor_pose(actor_id: str, record: TurnRecord | None) -> str:
    """Determine the appropriate pose for an actor based on the turn record.

    Returns:
        A pose string like "idle", "attack", "skill_shadow", "defend", "hit", etc.
    """
    if record is None:
        return "idle"

    if record.side == "enemy":
        enemy_action = record.enemy_action or {}
        action_type = enemy_action.get("type", "attack")
        if actor_id.startswith("hero_") and int(enemy_action.get("damage", 0) or 0) > 0:
            return "hit"
        if record.actor_id == actor_id:
            if action_type == "silenced":
                return "break"
            if action_type == "chant_charge":
                return "skill"
            if action_type == "chant_release":
                return "skill"
            return "attack"
        return "idle"

    # Check if this actor is being hit
    if record.side == "hero" and record.actor_id != actor_id and record.action and actor_id in record.action.targets:
        return "hit"

    # Check if this actor is the one acting
    if record.actor_id == actor_id:
        if record.side == "hero":
            # Hero action
            if record.action:
                if record.action.type == "basic_attack":
                    return "attack"
                elif record.action.type == "cast_skill":
                    skill = record.action.skill_id or ""
                    # Determine skill type based on skill ID
                    if "sting" in skill or "hex" in skill or "corrupted" in skill:
                        return "skill_shadow"
                    elif "ember" in skill or "burial" in skill:
                        return "skill_fire"
                    elif "pierce" in skill or "hook" in skill or "grave" in skill:
                        return "skill_physical"
                    elif "silent" in skill or "returning" in skill:
                        return "skill_holy"
                    elif "mire" in skill or "omen" in skill:
                        return "skill_poison"
                    elif "tower" in skill or "eclipse" in skill or "sinking" in skill or "crank" in skill or "bell" in skill:
                        return "defend"
                    # Generic skill pose
                    return "skill"
                elif record.action.type == "defend":
                    return "defend"
                elif record.action.type == "observe":
                    return "observe"
            return "cast"  # fallback
        else:
            # Enemy action
            if record.enemy_action:
                action_type = record.enemy_action.get("type", "attack")
                if action_type == "chant_release":
                    return "skill"
                elif action_type == "attack":
                    return "attack"
            return "cast"  # fallback

    return "idle"


def _effect_lane(record: TurnRecord | None) -> list[str]:
    """Generate the effect lane animation for a turn.

    Shows attack direction, skill type, damage numbers, and status effects.
    """
    if record is None:
        return ["", "     ...", "", ""]

    # Enemy turn
    if record.side == "enemy":
        kind = (record.enemy_action or {}).get("type", "attack")
        damage = (record.enemy_action or {}).get("damage", 0)
        status = (record.enemy_action or {}).get("apply_status")

        if kind == "chant_release":
            lines = ["", "<== chant", "   release", ""]
            if damage > 0:
                lines[2] = f"  -{damage} HP"
            return lines
        elif kind == "silenced":
            return ["", "<== break", "   silenced", "   [BREAK]"]
        else:
            lines = ["", "<== strike", "   impact", ""]
            if damage > 0:
                lines[2] = f"  -{damage} HP"
            if status:
                status_id = status.get("id", "")
                if "poison" in status_id:
                    lines.append("   [POISON]")
                elif "bleed" in status_id:
                    lines.append("   [BLEED]")
                elif "silence" in status_id:
                    lines.append("   [SILENCE]")
                elif "corruption" in status_id:
                    lines.append("   [CORRUPT]")
            return lines

    # Hero turn
    if record.action:
        damage = record.judge.damage if record.judge else 0
        skill = record.action.skill_id or ""
        if damage >= 40:
            return [
                "#== CLIMAX ==#",
                f"  -{damage} HP",
                "  rupture",
                "#============#",
            ]

        if record.action.type == "basic_attack":
            lines = ["", "-- strike >", "", ""]
            if damage > 0:
                lines[2] = f"  -{damage} HP"
            else:
                lines[2] = "   [MISS]"
            return lines

        elif record.action.type == "cast_skill":
            # Skill-specific animations
            if "hex" in skill:
                lines = ["", "-- seal -->", "", ""]
                if damage > 0:
                    lines[2] = f"  -{damage} HP"
                lines.append("   [SILENCE]")
                return lines

            elif "sting" in skill:
                lines = ["", "-- sting ->", "", ""]
                if damage > 0:
                    lines[2] = f"  -{damage} HP"
                lines.append("   [CORRUPT]")
                return lines

            elif "ember" in skill:
                lines = ["", "-- fire -->", "", ""]
                if damage > 0:
                    lines[2] = f"  -{damage} HP"
                lines.append("   [FIRE]")
                return lines

            elif "pierce" in skill or "hook" in skill:
                lines = ["", "-- pierce ->", "", ""]
                if damage > 0:
                    lines[2] = f"  -{damage} HP"
                lines.append("   [BLEED]")
                return lines

            elif "grave" in skill:
                lines = ["", "-- nail -->", "", ""]
                if damage > 0:
                    lines[2] = f"  -{damage} HP"
                lines.append("   [BLEED]")
                return lines

            elif "burial" in skill:
                lines = ["", "-- burst ->", "", ""]
                if damage > 0:
                    lines[2] = f"  -{damage} HP"
                lines.append("   [FIRE]")
                return lines

            elif "mire" in skill or "omen" in skill:
                lines = ["", "-- poison ->", "", ""]
                if damage > 0:
                    lines[2] = f"  -{damage} HP"
                lines.append("   [POISON]")
                return lines

            elif "silent" in skill:
                lines = ["", "-- hymn -->", "", ""]
                if damage > 0:
                    lines[2] = f"  -{damage} HP"
                lines.append("   [SILENCE]")
                return lines

            elif "returning" in skill:
                lines = ["", "-- echo -->", "", ""]
                if damage > 0:
                    lines[2] = f"  -{damage} HP"
                lines.append("   [CORRUPT]")
                return lines

            # Defensive/buff skills
            elif "corrupted" in skill or "tower" in skill or "eclipse" in skill or "sinking" in skill or "crank" in skill or "bell" in skill:
                lines = ["", "-- ward -->", "", ""]
                lines.append("   [SHIELD]")
                return lines

            # Generic skill
            else:
                lines = ["", "-- skill ->", "", ""]
                if damage > 0:
                    lines[2] = f"  -{damage} HP"
                return lines

        elif record.action.type == "defend":
            return ["", "   guard", "", "   [SHIELD]"]

        elif record.action.type == "observe":
            return ["", "  observe", "", "   [SCAN]"]

    return ["", "   ...", "", ""]


def _hero_sprite(hero: Hero, record: TurnRecord | None) -> list[str]:
    """Generate the hero sprite based on current pose and state."""
    state = _actor_pose(hero.id, record)

    # Check for low HP state (overrides other poses except hit and death)
    if hero.hp / max(1, hero.max_hp) < 0.3 and state not in ("hit", "death"):
        state = "low"
    return asset_hero_sprite(hero.id, state)


def _enemy_sprite(enemy: Enemy, record: TurnRecord | None) -> list[str]:
    """Generate the enemy sprite based on current pose and state."""
    state = _actor_pose(enemy.id, record)

    # Check for death state
    if not enemy.is_alive:
        state = "death"
    # Check for low HP state
    elif enemy.hp / max(1, enemy.max_hp) < 0.3 and state not in ("hit", "death"):
        state = "low"
    return asset_enemy_sprite(enemy.short_glyph, state)


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
            f"{config.api_key_env}: {label('menu_key_set', lang)}"
            if config.api_key_env and os.environ.get(config.api_key_env)
            else f"{config.api_key_env or '(unset)'}: {label('menu_key_missing', lang)}"
        )
    visual = "unicode" if config.unicode_mode else "ascii"
    trace = recent_trace or "-"
    lines = [
        label("menu_title", lang),
        "",
        label("menu_status", lang),
        f"{label('menu_provider', lang)} : {view['provider']}    {label('menu_model', lang)}: {view['model']}    {label('menu_key', lang)}: {key_state}",
        f"{label('menu_language', lang)} : {lang}      {label('menu_visual', lang)}: {visual}      {label('menu_trace', lang)}: {trace}",
        f"{label('menu_config', lang)}   : {config_path}",
        "",
        *(_render_main_menu_journey(lang)),
        "",
        label("menu_entries", lang),
        label("menu_entry_play", lang),
        label("menu_entry_demo", lang),
        label("menu_entry_quick_battle", lang),
        label("menu_entry_heroes", lang),
        label("menu_entry_prompt", lang),
        label("menu_entry_status", lang),
        label("menu_entry_codex", lang),
        label("menu_entry_runs", lang),
        label("menu_entry_report", lang),
        label("menu_entry_history", lang),
        label("menu_entry_replay", lang),
        label("menu_entry_doctor", lang),
        label("menu_entry_config", lang),
        label("menu_entry_quit", lang),
    ]
    return "\n".join(lines)


def _render_main_menu_journey(lang: str) -> list[str]:
    if lang == "zh":
        return [
            "PLAYER JOURNEY BOARD :: 玩家旅程",
            "  [START]  引导试玩 -> ouro demo --seed 1",
            "  [BUILD]  选英雄/Prompt -> ouro list-heroes / ouro prompt-templates",
            "  [RUN]    完整运行 -> ouro run --mock",
            "  [LEARN]  复盘图鉴/报告 -> ouro status / ouro codex / ouro run-report",
        ]
    return [
        "PLAYER JOURNEY BOARD",
        "  [START] Guided demo -> ouro demo --seed 1",
        "  [BUILD] Pick hero/prompt -> ouro list-heroes / ouro prompt-templates",
        "  [RUN]   Full run -> ouro run --mock",
        "  [LEARN] Review Codex/report -> ouro status / ouro codex / ouro run-report",
    ]


def render_progress_status(
    config: OuroConfig,
    bundle: ContentBundle,
    codex_progress: CodexProgress,
    archives: list[dict],
    deaths: list[dict],
    *,
    config_path: str,
    codex_save_path: str,
    run_archive_path: str,
    death_history_save_path: str,
    language: str = DEFAULT_LANGUAGE,
    width: int = 100,
) -> str:
    """Render one player-facing overview for returning players."""
    lang = language
    width = max(60, width)
    view = redacted_view(config, language=lang)
    title = "OURO STATUS :: ECHO LEDGER" if lang == "en" else "OURO STATUS :: 回响总览"
    provider_title = "PROFILE" if lang == "en" else "档案"
    storage_title = "LOCAL FILES" if lang == "en" else "本地文件"
    progress_title = "PROGRESS" if lang == "en" else "进度"
    last_run_title = "LAST RUN" if lang == "en" else "最近运行"
    plan_title = "NEXT RUN PLAN" if lang == "en" else "下一局计划"
    control_title = "NEXT RUN CONTROL" if lang == "en" else "下一局控制台"
    next_title = "NEXT COMMANDS" if lang == "en" else "下一步命令"

    key_state = "mock-ready"
    if config.provider != "mock":
        key_state = (
            "set (hidden)"
            if config.api_key_env and os.environ.get(config.api_key_env)
            else "MISSING"
        )
    visual = "unicode" if config.unicode_mode else "ascii"
    codex_counts = _codex_summary_counts(bundle, codex_progress)
    total_runs = len(archives)
    complete_runs = sum(1 for item in archives if str(item.get("result", "")) == "complete")
    dead_runs = sum(1 for item in archives if str(item.get("result", "")) == "dead")

    profile_body = [
        f"Provider: {view['provider']}  Model: {view['model']}  Key: {key_state}",
        f"Language: {lang}  Visual: {visual}",
    ]
    storage_body = [
        f"Config: {config_path}",
        f"Codex: {codex_save_path}",
        f"Run Archives: {run_archive_path}",
        f"Death History: {death_history_save_path}",
    ]
    progress_body = [
        (
            "Codex: "
            f"Observed {codex_counts['observed']}/{codex_counts['total']}  "
            f"Familiar {codex_counts['familiar']}/{codex_counts['total']}  "
            f"Mastered {codex_counts['mastered']}/{codex_counts['total']}  "
            f"Hunted {codex_counts['hunted']}/{codex_counts['total']}"
        ),
        f"Runs: {total_runs} total  {complete_runs} complete  {dead_runs} dead",
        f"Fallen Runs: {len(deaths)}",
    ]
    if archives:
        last_run_body = _render_status_last_run(archives[0], bundle, lang)
    else:
        last_run_body = [
            "  No run archives yet. Start with ouro run --mock."
            if lang == "en"
            else "  尚无运行归档。可先运行 ouro run --mock。"
        ]
    plan_body = _render_status_next_run_plan(
        config,
        codex_counts,
        archives,
        deaths,
        lang,
    )
    control_body = _render_status_next_run_control(
        config,
        codex_counts,
        archives,
        lang,
    )

    run_command = "ouro run --mock" if config.provider == "mock" else "ouro run"
    if lang == "zh":
        command_rows = (
            ("继续运行", run_command),
            ("引导试玩", "ouro demo --seed 1"),
            ("状态总览", "ouro status --lang zh"),
            ("运行报告", "ouro run-report --lang zh"),
            ("查看图鉴", "ouro codex --lang zh"),
            ("查看归档", "ouro runs --lang zh --limit 5"),
            ("查看陨落", "ouro history --lang zh --limit 5"),
            ("安装诊断", "ouro doctor --lang zh"),
        )
    else:
        command_rows = (
            ("Continue", run_command),
            ("Guided Demo", "ouro demo --seed 1"),
            ("Status", "ouro status --lang en"),
            ("Run Report", "ouro run-report --lang en"),
            ("Codex", "ouro codex --lang en"),
            ("Runs", "ouro runs --lang en --limit 5"),
            ("History", "ouro history --lang en --limit 5"),
            ("Doctor", "ouro doctor --lang en"),
        )
    next_body = [f"{name:<12} {command}" for name, command in command_rows]
    panels = [
        pixel_rule(title, width, tone="hero"),
        *pixel_panel(provider_title, profile_body, width, tone="hero").lines,
        *pixel_panel(storage_title, storage_body, width, tone="quiet").lines,
        *pixel_panel(progress_title, progress_body, width, tone="counter").lines,
        *_render_legend_progress_map(
            codex_counts,
            total_runs=total_runs,
            complete_runs=complete_runs,
            dead_runs=dead_runs,
            deaths=len(deaths),
            lang=lang,
            width=width,
        ),
        *pixel_panel(last_run_title, last_run_body, width, tone="normal").lines,
        *pixel_panel(plan_title, plan_body, width, tone="hero").lines,
        *pixel_panel(control_title, control_body, width, tone="counter").lines,
        *pixel_panel(next_title, next_body, width, tone="climax").lines,
    ]
    lines = list(panels)
    return "\n".join(lines)


def _render_legend_progress_map(
    codex_counts: dict[str, int],
    *,
    total_runs: int,
    complete_runs: int,
    dead_runs: int,
    deaths: int,
    lang: str,
    width: int,
) -> list[str]:
    total_codex = max(1, int(codex_counts.get("total", 0)))
    observed = int(codex_counts.get("observed", 0))
    mastered = int(codex_counts.get("mastered", 0))
    hunted = int(codex_counts.get("hunted", 0))
    codex_bar = bar(mastered, total_codex, width=10, unicode_mode=False)
    run_bar = bar(complete_runs, max(1, total_runs), width=10, unicode_mode=False)
    pressure_bar = bar(dead_runs, max(1, total_runs), width=10, unicode_mode=False)
    ready_score = min(3, int(observed > 0) + int(total_runs > 0) + int(deaths > 0))
    ready_bar = bar(ready_score, 3, width=10, unicode_mode=False)
    if lang == "zh":
        body = [
            f"[CODEX] {codex_bar} mastered {mastered}/{total_codex} / hunted {hunted}/{total_codex}",
            f"[RUNS]  {run_bar} complete {complete_runs}/{total_runs or 0} / dead {dead_runs}",
            f"[RISK]  {pressure_bar} fall pressure {dead_runs}/{total_runs or 0}",
            f"[READY] {ready_bar} next-run signals {ready_score}/3",
        ]
        return list(pixel_panel("LEGEND PROGRESS MAP :: 传奇进度地图", [fit_text(line, width - 4) for line in body], width, tone="counter").lines)
    body = [
        f"[CODEX] {codex_bar} mastered {mastered}/{total_codex} / hunted {hunted}/{total_codex}",
        f"[RUNS]  {run_bar} complete {complete_runs}/{total_runs or 0} / dead {dead_runs}",
        f"[RISK]  {pressure_bar} fall pressure {dead_runs}/{total_runs or 0}",
        f"[READY] {ready_bar} next-run signals {ready_score}/3",
    ]
    return list(pixel_panel("LEGEND PROGRESS MAP", [fit_text(line, width - 4) for line in body], width, tone="counter").lines)


def _codex_summary_counts(
    bundle: ContentBundle,
    codex_progress: CodexProgress,
) -> dict[str, int]:
    counts = {
        "total": len(bundle.enemies),
        "observed": 0,
        "familiar": 0,
        "mastered": 0,
        "hunted": 0,
    }
    for enemy_id, enemy in bundle.enemies.items():
        family_id = enemy.family_id or enemy_id
        stage = codex_progress.get_stage(family_id, enemy.tier)
        if stage >= CodexStage.OBSERVED:
            counts["observed"] += 1
        if stage >= CodexStage.FAMILIAR:
            counts["familiar"] += 1
        if stage >= CodexStage.MASTERED:
            counts["mastered"] += 1
        if stage >= CodexStage.HUNTED:
            counts["hunted"] += 1
    return counts


def _render_status_last_run(entry: dict, bundle: ContentBundle, lang: str) -> list[str]:
    run_id = str(entry.get("run_id", "-"))
    seed = str(entry.get("seed", "-"))
    result = str(entry.get("result", entry.get("battle_result", "-")))
    phase = str(entry.get("phase", "-"))
    hero_id = str(entry.get("hero_id", "-"))
    dungeon_id = str(entry.get("dungeon_id", "-"))
    wins = int(entry.get("battles_won", 0) or 0)
    losses = int(entry.get("battles_lost", 0) or 0)
    gold = int(entry.get("gold", 0) or 0)
    xp = int(entry.get("xp", 0) or 0)
    current_hp = int(entry.get("current_hp", 0) or 0)
    max_hp = int(entry.get("max_hp", 0) or 0)
    current_mp = int(entry.get("current_mp", 0) or 0)
    max_mp = int(entry.get("max_mp", 0) or 0)
    node_ids = list(entry.get("completed_node_ids", []) or [])
    build = entry.get("build", {}) if isinstance(entry.get("build", {}), dict) else {}
    hero = bundle.heroes.get(hero_id)
    dungeon = bundle.dungeons.get(dungeon_id)
    hero_name = (
        hero.display_name.get(lang) or hero.display_name.get("en", hero_id)
        if hero is not None else hero_id
    )
    dungeon_name = (
        dungeon.display_name.get(lang) or dungeon.display_name.get("en", dungeon_id)
        if dungeon is not None else dungeon_id
    )
    build_name = str(build.get("archetype", "-"))
    build_badge = str(build.get("stage_badge", ""))
    lines = [
        f"  {run_id}",
        f"  Seed: {seed}  Result: {result}  Phase: {phase}",
        f"  Hero: {hero_name}  Dungeon: {dungeon_name}",
        f"  Battles: {wins}W/{losses}L  Nodes: {len(node_ids)}  Gold: {gold}  XP: {xp}",
        f"  Resources: HP {current_hp}/{max_hp}  MP {current_mp}/{max_mp}",
        f"  Build: {build_name} {build_badge}".rstrip(),
    ]
    return lines


def _render_status_next_run_plan(
    config: OuroConfig,
    codex_counts: dict[str, int],
    archives: list[dict],
    deaths: list[dict],
    lang: str,
) -> list[str]:
    run_command = "ouro run --mock" if config.provider == "mock" else "ouro run"
    lang_flag = f"--lang {lang}"
    observed = int(codex_counts.get("observed", 0) or 0)
    total = int(codex_counts.get("total", 0) or 0)
    codex_gap = max(0, total - observed)

    if not archives:
        if lang == "zh":
            return [
                "[1] 先跑引导试玩：ouro demo --seed 1",
                f"[2] 开第一局：{run_command} --seed 7",
                f"[3] 打完后回看：ouro status {lang_flag}",
            ]
        return [
            "[1] Start guided: ouro demo --seed 1",
            f"[2] First run: {run_command} --seed 7",
            f"[3] After battle: ouro status {lang_flag}",
        ]

    latest = archives[0]
    result = str(latest.get("result", latest.get("battle_result", ""))).lower()
    phase = str(latest.get("phase", "")).lower()
    seed = _status_seed_int(latest)
    next_seed = seed + 1 if seed is not None else 7

    if result == "dead" or phase == "dead":
        if lang == "zh":
            return [
                f"[1] 复盘陨落 #{len(deaths)}：ouro history {lang_flag} --limit 3",
                f"[2] 降低节奏风险：{run_command} --prompt-style control --seed {next_seed}",
                f"[3] 补图鉴缺口 {codex_gap} 个：ouro codex {lang_flag}；Boss 前优先休整/商店",
            ]
        return [
            f"[1] Review fall #{len(deaths)}: ouro history {lang_flag} --limit 3",
            f"[2] Slow the Agent: {run_command} --prompt-style control --seed {next_seed}",
            f"[3] Patch {codex_gap} Codex gaps: ouro codex {lang_flag}; rest/shop before boss",
        ]

    if result == "complete" or phase == "complete":
        if lang == "zh":
            return [
                f"[1] 对照胜利构筑：ouro runs {lang_flag} --limit 5",
                f"[2] 追图鉴缺口 {codex_gap} 个：ouro codex {lang_flag}",
                f"[3] 换压力种子：{run_command} --prompt-style guarded --seed {next_seed}",
            ]
        return [
            f"[1] Compare winning builds: ouro runs {lang_flag} --limit 5",
            f"[2] Hunt {codex_gap} Codex gaps: ouro codex {lang_flag}",
            f"[3] New pressure seed: {run_command} --prompt-style guarded --seed {next_seed}",
        ]

    if lang == "zh":
        return [
            f"[1] 查看最近路线：ouro runs {lang_flag} --limit 3",
            f"[2] 继续稳定样本：{run_command} --seed {next_seed}",
            f"[3] 回读图鉴进度：ouro codex {lang_flag}",
        ]
    return [
        f"[1] Check latest route: ouro runs {lang_flag} --limit 3",
        f"[2] Continue a stable sample: {run_command} --seed {next_seed}",
        f"[3] Read Codex progress: ouro codex {lang_flag}",
    ]


def _render_status_next_run_control(
    config: OuroConfig,
    codex_counts: dict[str, int],
    archives: list[dict],
    lang: str,
) -> list[str]:
    run_command = "ouro run --mock" if config.provider == "mock" else "ouro run"
    observed = int(codex_counts.get("observed", 0) or 0)
    total = int(codex_counts.get("total", 0) or 0)
    codex_gap = max(0, total - observed)
    if not archives:
        if lang == "zh":
            return [
                "[PROMPT] default / 建立第一份基线",
                f"[SEED] 7 / 首局样本",
                f"[CODEX] {codex_gap} 个未知家族",
                f"[RUN] {run_command} --seed 7",
            ]
        return [
            "[PROMPT] default / establish first baseline",
            "[SEED] 7 / first-run sample",
            f"[CODEX] {codex_gap} unknown families",
            f"[RUN] {run_command} --seed 7",
        ]

    latest = archives[0]
    result = str(latest.get("result", latest.get("battle_result", ""))).lower()
    phase = str(latest.get("phase", "")).lower()
    seed = _status_seed_int(latest)
    next_seed = seed + 1 if seed is not None else 7
    if result == "dead" or phase == "dead":
        if lang == "zh":
            return [
                "[PROMPT] control / 降低敌方节奏",
                f"[SEED] {next_seed} / 固定重试样本",
                f"[CODEX] 补 {codex_gap} 个缺口",
                "[ROUTE] Boss 前找休整/商店",
            ]
        return [
            "[PROMPT] control / reduce enemy tempo",
            f"[SEED] {next_seed} / fixed retry sample",
            f"[CODEX] patch {codex_gap} gaps",
            "[ROUTE] rest/shop before boss pressure",
        ]
    if result == "complete" or phase == "complete":
        if lang == "zh":
            return [
                "[PROMPT] guarded / 压力验证",
                f"[SEED] {next_seed} / 新压力样本",
                f"[CODEX] 追 {codex_gap} 个缺口",
                "[ROUTE] 精英/事件贪心路线",
            ]
        return [
            "[PROMPT] guarded / pressure validation",
            f"[SEED] {next_seed} / new pressure sample",
            f"[CODEX] hunt {codex_gap} gaps",
            "[ROUTE] elite/event greed line",
        ]
    if lang == "zh":
        return [
            "[PROMPT] current / 保持样本稳定",
            f"[SEED] {next_seed} / 继续样本",
            f"[CODEX] 回读 {codex_gap} 个缺口",
            "[ROUTE] 按上一局风险调整",
        ]
    return [
        "[PROMPT] current / keep sample stable",
        f"[SEED] {next_seed} / continue sample",
        f"[CODEX] review {codex_gap} gaps",
        "[ROUTE] adjust from latest risk",
    ]


def _status_seed_int(entry: dict) -> int | None:
    try:
        return int(entry.get("seed", ""))
    except (TypeError, ValueError):
        return None


def render_start_screen(
    config: OuroConfig,
    *,
    provider_label: str,
    seed: int,
    language: str = DEFAULT_LANGUAGE,
    width: int = 100,
) -> str:
    lang = language
    view = redacted_view(config, language=lang)
    line = "=" * min(width, 100)
    subtitle = (
        "Configure one Agent. The model chooses; the local judge decides."
        if lang == "en"
        else "配置一名 Agent；模型选择行动，本地裁判决定胜负。"
    )
    tips = (
        [
            "New Run: choose hero, prompt style, then enter the dungeon.",
            "Mock mode needs no API key and stays deterministic.",
            "During battle you watch decisions, timing, impact, and judge results.",
        ]
        if lang == "en"
        else [
            "新运行：先选英雄与 Prompt 预设，再进入副本。",
            "Mock 模式无需 API key，且固定 seed 可复现。",
            "战斗中你会看到决策、读条、命中、裁判与日志。",
        ]
    )
    lines = [
        line,
        "OURO AGENT :: PROMPT LEGEND",
        subtitle,
        line,
        "",
        f"Provider: {provider_label}    Model: {view['model']}    Seed: {seed}",
        "",
        "+------------------+  +------------------+  +------------------+",
        "|  HERO            |  |  PROMPT          |  |  LOCAL JUDGE     |",
        "|  stats/build     |  |  style/intent    |  |  damage/victory  |",
        "+------------------+  +------------------+  +------------------+",
        "",
    ]
    lines.extend(f"- {tip}" for tip in tips)
    return "\n".join(lines)


def render_run_setup_screen(
    hero: HeroData,
    bundle: ContentBundle,
    build: ResolvedBuild,
    *,
    provider_label: str,
    prompt_style: str | None,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    lang = language
    hero_name = hero.display_name.get(lang)
    class_name = hero.class_name.get(lang)
    style = prompt_style or "default"
    style_text = prompt_style_text(prompt_style, lang) if prompt_style else hero.default_prompt.get(lang)
    progress = build.calculate_progress(bundle)
    active_resonance_names = _resonance_display_names(bundle, progress.active_resonances, lang)

    lines = [
        label("setup_title", lang),
        "",
        f"{label('run_hero', lang)}: {hero.short_tag} {hero_name} / {class_name}",
        f"{label('provider_label', lang)}: {provider_label}",
        f"{label('hero_card_prompt_template', lang)}: [{style}]",
        "",
        label("setup_prompt", lang),
    ]
    for line in _wrap_text(style_text, 92)[:6]:
        lines.append(f"  {line}")
    lines.append("")
    lines.extend(
        _render_run_ready_board(
            hero,
            build,
            progress,
            prompt_style=prompt_style,
            lang=lang,
        )
    )
    lines.append("")
    lines.extend(_render_equipment_panel(hero, bundle, build, lang=lang))
    lines.append("")
    lines.append(
        f"{label('hud_build', lang)}: {progress.stage.badge} {progress.stage_name}  "
        f"{label('hero_card_active_resonances', lang)}: "
        f"{', '.join(active_resonance_names) if active_resonance_names else label('hero_card_none', lang)}"
    )
    if progress.best_next_picks:
        picks = ", ".join(pick["tag"] for pick in progress.best_next_picks[:3])
        lines.append(f"{label('hero_card_best_next_picks', lang)}: {picks}")
    return "\n".join(lines)


def render_encounter_briefing(
    state: BattleState,
    bundle: ContentBundle,
    build: ResolvedBuild,
    *,
    language: str = DEFAULT_LANGUAGE,
    width: int = 100,
) -> str:
    lang = language
    progress = build.calculate_progress(bundle)
    enemies = [enemy for enemy in state.enemies if enemy.is_alive]
    threat = _encounter_primary_threat(enemies, lang=lang)
    roster = _encounter_roster_line(enemies, lang=lang)
    window = _encounter_counter_window(enemies, state.hero, lang=lang)
    plan = _encounter_opening_plan(enemies, progress, lang=lang)
    build_line = f"{progress.stage.badge} {build.archetype(lang)}"
    if progress.best_next_picks:
        build_line += " / next " + ", ".join(pick["tag"] for pick in progress.best_next_picks[:2])
    max_text = max(24, width - 4)
    if lang == "zh":
        body = [
            f"[ENEMY] {roster}",
            f"[THREAT] {threat}",
            f"[BUILD] {build_line}",
            f"[WINDOW] {window}",
            f"[PLAN] {plan}",
        ]
        return "\n".join(pixel_panel("ENCOUNTER BRIEFING :: 遭遇简报", [fit_text(line, max_text) for line in body], width, tone="counter").lines)
    body = [
        f"[ENEMY] {roster}",
        f"[THREAT] {threat}",
        f"[BUILD] {build_line}",
        f"[WINDOW] {window}",
        f"[PLAN] {plan}",
    ]
    return "\n".join(pixel_panel("ENCOUNTER BRIEFING", [fit_text(line, max_text) for line in body], width, tone="counter").lines)


def _encounter_roster_line(enemies: list[Enemy], *, lang: str) -> str:
    if not enemies:
        return "none" if lang == "en" else "无"
    parts = []
    for enemy in enemies[:3]:
        parts.append(f"[{enemy.short_glyph}] {enemy.name} {enemy.tier} HP {enemy.hp}/{enemy.max_hp}")
    if len(enemies) > 3:
        parts.append(f"+{len(enemies) - 3}")
    return " / ".join(parts)


def _encounter_primary_threat(enemies: list[Enemy], *, lang: str) -> str:
    if not enemies:
        return "field clear" if lang == "en" else "战场已清"
    chant = [enemy for enemy in enemies if enemy.chant_charge_turns]
    if chant:
        lead = max(chant, key=lambda enemy: (enemy.chant_progress, enemy.atb))
        if lang == "zh":
            return f"{lead.name} 吟唱 {lead.chant_progress}/{lead.chant_charge_turns} / ATB {lead.atb}"
        return f"{lead.name} chant {lead.chant_progress}/{lead.chant_charge_turns} / ATB {lead.atb}"
    lead = max(enemies, key=lambda enemy: enemy.atb)
    if lead.atb >= 90:
        return f"{lead.name} high ATB {lead.atb}" if lang == "en" else f"{lead.name} 高 ATB {lead.atb}"
    lead = max(enemies, key=lambda enemy: enemy.max_hp)
    return f"{lead.name} HP anchor {lead.max_hp}" if lang == "en" else f"{lead.name} 血量锚点 {lead.max_hp}"


def _encounter_counter_window(enemies: list[Enemy], hero: Hero, *, lang: str) -> str:
    interrupt = _first_interrupt_skill(hero)
    interrupt_name = interrupt.display_name if interrupt is not None else None
    chant = [enemy for enemy in enemies if enemy.chant_charge_turns]
    if not chant:
        return "no chant; watch high ATB lanes" if lang == "en" else "无吟唱；观察高 ATB 轨道"
    lead = max(chant, key=lambda enemy: (enemy.chant_progress, enemy.atb))
    skill_text = interrupt_name or ("no interrupt skill" if lang == "en" else "无打断技能")
    if lead.chant_progress > 0:
        if lang == "zh":
            return f"{lead.name} 已开窗；保留 {skill_text}"
        return f"{lead.name} window open; keep {skill_text}"
    if lang == "zh":
        return f"{lead.name} 将蓄力；预留 {skill_text}"
    return f"{lead.name} can charge; reserve {skill_text}"


def _encounter_opening_plan(
    enemies: list[Enemy],
    progress: BuildProgress,
    *,
    lang: str,
) -> str:
    if not enemies:
        return "collect reward" if lang == "en" else "领取奖励"
    if any(enemy.chant_charge_turns for enemy in enemies):
        return "open with control; spend MP only for window value" if lang == "en" else "以控制开局；MP 只花在窗口价值"
    if progress.stage in {BuildStage.ONLINE, BuildStage.HIGH_ROLL, BuildStage.LOCKED_IN}:
        return "convert online build into early tempo" if lang == "en" else "把在线 Build 转为前期节奏"
    if len(enemies) >= 2:
        return "thin one target before ATB overlaps" if lang == "en" else "ATB 重叠前先减员"
    return "create a kill line, then save MP" if lang == "en" else "先制造击杀线，再保留 MP"


def _render_run_ready_board(
    hero: HeroData,
    build: ResolvedBuild,
    progress: BuildProgress,
    *,
    prompt_style: str | None,
    lang: str,
) -> list[str]:
    style = prompt_style or _hero_default_prompt_style(hero.id)
    opener = _hero_loadout_opener(hero.id, prompt_style=style, lang=lang)
    next_pick = "-"
    if progress.best_next_picks:
        next_pick = ", ".join(pick["tag"] for pick in progress.best_next_picks[:3])
    core_tags = " / ".join(HERO_CORE_TAGS.get(hero.id, ())[:2]) or "-"
    if lang == "zh":
        return [
            "RUN READY BOARD :: 入局确认",
            f"  [PROMPT] {style} / {opener}",
            f"  [BUILD] {progress.stage.badge} {progress.stage_name} / {build.archetype(lang)}",
            f"  [CORE] {core_tags}",
            f"  [NEXT PICK] {next_pick}",
            "  [FIRST RULE] 模型选择行动，本地裁判结算",
        ]
    return [
        "RUN READY BOARD",
        f"  [PROMPT] {style} / {opener}",
        f"  [BUILD] {progress.stage.badge} {progress.stage_name} / {build.archetype(lang)}",
        f"  [CORE] {core_tags}",
        f"  [NEXT PICK] {next_pick}",
        "  [FIRST RULE] model chooses action, local judge resolves",
    ]


def render_prompt_templates(*, language: str = DEFAULT_LANGUAGE) -> str:
    title = "PROMPT STRATEGY TEMPLATES" if language == "en" else "PROMPT 策略预设"
    lines = [title, ""]
    lines.extend(_render_prompt_pilot_board(language))
    lines.append("")
    lines.extend(_render_prompt_scenario_board(language))
    lines.append("")
    for name, localized in PROMPT_STYLE_TEMPLATES.items():
        text = localized.get(language) or localized["en"]
        lines.append(f"[{name}]")
        for wrapped in _wrap_text(text, 88)[:3]:
            lines.append(f"  {wrapped}")
        lines.append("")
    lines.append("")
    lines.append("Use: ouro play --mock --prompt-style control")
    return "\n".join(lines)


def _render_prompt_pilot_board(lang: str) -> list[str]:
    if lang == "zh":
        lines = [
            "PROMPT PILOT BOARD :: Agent 驾驶模式",
            "  [aggressive] BURST  | 高风险 | 适配 execute / damage",
            "  [guarded]    STABLE | 低风险 | 适配 shield / sustain",
            "  [control]    DENY   | 中风险 | 适配 interrupt / silence",
            "  [attrition]  GRIND  | 中风险 | 适配 poison / bleed",
            "  RUN: ouro run --mock --prompt-style <name>",
        ]
    else:
        lines = [
            "PROMPT PILOT BOARD",
            "  [aggressive] BURST  | high risk | fits execute / damage",
            "  [guarded]    STABLE | low risk  | fits shield / sustain",
            "  [control]    DENY   | mid risk  | fits interrupt / silence",
            "  [attrition]  GRIND  | mid risk  | fits poison / bleed",
            "  RUN: ouro run --mock --prompt-style <name>",
        ]
    return lines


def _render_prompt_scenario_board(lang: str) -> list[str]:
    if lang == "zh":
        return [
            "PROMPT SCENARIO BOARD :: 战况偏置",
            "  [CHANT] control -> 先打断高 ATB / guarded -> 先护盾承伤",
            "  [LOW HP] guarded -> 防御或护盾 / attrition -> 保留续航价值",
            "  [EXECUTE] aggressive -> 收割低血 / control -> 先确认窗口",
            "  [BOSS] control -> 管蓄力 / guarded -> 保血线 / aggressive -> 只在破防后爆发",
            "  PICK: boss/chant 选 control；低血选 guarded；短战收割选 aggressive",
        ]
    return [
        "PROMPT SCENARIO BOARD",
        "  [CHANT] control -> interrupt high ATB / guarded -> shield before trade",
        "  [LOW HP] guarded -> defend or shield / attrition -> keep sustain value",
        "  [EXECUTE] aggressive -> finish low HP / control -> confirm window first",
        "  [BOSS] control -> manage charge / guarded -> hold HP / aggressive -> burst after break",
        "  PICK: boss/chant use control; low HP use guarded; short kill use aggressive",
    ]


def _render_equipment_panel(
    hero: HeroData,
    bundle: ContentBundle,
    build: ResolvedBuild,
    *,
    lang: str,
) -> list[str]:
    lines = [label("setup_equipment", lang)]
    if not build.items and not build.affixes:
        lines.append(f"  {label('hero_card_none', lang)}")
        return lines
    for item in build.items:
        name = item.display_name.get(lang)
        tags = ", ".join(item.tags[:4])
        mods = _stat_mods_line(item.stat_mods)
        desc = item.description.get(lang)
        lines.append(f"  [W:*] {name} [{item.tier}]  {mods}")
        if tags:
            lines.append(f"       tags: {tags}")
        if desc:
            lines.append(f"       {desc}")
    if build.affixes:
        lines.append(f"  {label('hero_card_affixes', lang)}:")
    for affix in build.affixes:
        name = affix.display_name.get(lang)
        tags = ", ".join(affix.tags[:4])
        mods = _stat_mods_line(affix.stat_mods)
        desc = affix.description.get(lang)
        lines.append(f"    + {name}  {mods}")
        if tags:
            lines.append(f"      tags: {tags}")
        if desc:
            lines.append(f"      {desc}")
    return lines


def _stat_mods_line(mods) -> str:
    parts = []
    for field, label_text in (
        ("hp", "HP"),
        ("mp", "MP"),
        ("speed", "SPD"),
        ("attack", "ATK"),
        ("defense", "DEF"),
        ("power", "POW"),
    ):
        value = getattr(mods, field, 0)
        if value:
            sign = "+" if value > 0 else ""
            parts.append(f"{label_text}{sign}{value}")
    return ", ".join(parts) if parts else "no stat change"


def _wrap_text(text: str, width: int) -> list[str]:
    normalized = " ".join((text or "").split())
    if not normalized:
        return [""]
    if " " not in normalized:
        lines: list[str] = []
        current = ""
        for ch in normalized:
            if current and visual_width(current + ch) > width:
                lines.append(current)
                current = ch
            else:
                current += ch
        if current:
            lines.append(current)
        return lines
    words = normalized.split(" ")
    lines: list[str] = []
    current = ""
    for word in words:
        if not current:
            current = word
        elif visual_width(current + " " + word) <= width:
            current += " " + word
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def _wrap_screen_lines(lines: list[str], width: int) -> list[str]:
    wrapped_lines: list[str] = []
    for line in lines:
        if not line or visual_width(line) <= width:
            wrapped_lines.append(line)
            continue
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]
        prefix = indent
        continuation = indent
        body = stripped
        if stripped.startswith("- "):
            prefix = f"{indent}- "
            continuation = f"{indent}  "
            body = stripped[2:]
        elif stripped[:3].endswith(". ") and stripped[0].isdigit():
            prefix = f"{indent}{stripped[:3]}"
            continuation = f"{indent}{' ' * 3}"
            body = stripped[3:]
        content_width = max(12, width - visual_width(prefix))
        for idx, wrapped in enumerate(_wrap_text(body, content_width)):
            line_prefix = prefix if idx == 0 else continuation
            wrapped_lines.append(f"{line_prefix}{wrapped}")
    return wrapped_lines


def _fit_visual(text: str, width: int) -> str:
    text = " ".join((text or "").split())
    if visual_width(text) <= width:
        return text
    result = ""
    for ch in text:
        if visual_width(result + ch + "...") > width:
            break
        result += ch
    return result.rstrip() + "..."


def _dedupe_preserve(items) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = str(item)
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def render_battle_report(
    state: BattleState,
    records: list[TurnRecord],
    *,
    language: str | None = None,
    width: int = 100,
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
        skill_line = ", ".join(
            f"{_battle_report_skill_name(state, sid)} x{count}"
            for sid, count in skill_counts.items()
        )
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
    lines.extend(
        _render_battle_result_board(
            state,
            hero_turns=len(hero_records),
            enemy_turns=len(enemy_records),
            action_ratio=ratio,
            damage_dealt=damage_dealt,
            damage_taken=damage_taken,
            fallback_count=fallback_count,
            lang=lang,
        )
    )
    lines.append("")
    lines.extend(_render_battle_turn_map(state, records, lang=lang))
    lines.append("")
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
    lines.append("")
    diagnosis = analyze_battle_tactics(state, records, language=lang)
    lines.extend(render_tactical_diagnosis(diagnosis, language=lang))
    prompt_impacts = render_prompt_impacts(records, language=lang)
    if prompt_impacts:
        lines.append("")
        lines.extend(prompt_impacts)
    lines.append("")
    if state.result == "victory":
        lines.extend(_victory_readout(state, damage_taken=damage_taken, lang=lang))
    elif state.result == "defeat":
        lines.extend(_defeat_readout(state, damage_taken=damage_taken, diagnosis=diagnosis, lang=lang))
    else:
        lines.extend(_timeout_readout(state, lang=lang))
    if state.result == "defeat":
        lines.append(
            f"{label('battle_report_death_reason', lang)}: "
            f"{state.log[-1] if state.log else label('battle_report_unknown', lang)}"
        )
    lines.append(
        f"{label('battle_report_build_note', lang)}: "
        f"{label('battle_report_build_note_value', lang)}"
    )
    status_details = _battle_report_status_details(state, lang=lang)
    if status_details:
        lines.append("")
        lines.extend(status_details)
    lines.extend(["", *_render_play_next_board(state, records, lang=lang)])
    return "\n".join(_wrap_screen_lines(lines, width))


def _battle_report_prompt_style(state: BattleState, records: list[TurnRecord]) -> str:
    for record in records:
        if record.prompt_style:
            return record.prompt_style
    return _hero_default_prompt_style(state.hero.id)


def _render_play_next_board(
    state: BattleState,
    records: list[TurnRecord],
    *,
    lang: str,
) -> list[str]:
    style = _battle_report_prompt_style(state, records)
    next_seed = state.seed + 1
    hero_id = state.hero.id
    rematch = (
        f"ouro play --mock --hero {hero_id} "
        f"--prompt-style {style} --seed {next_seed}"
    )
    if lang == "zh":
        title = "PLAY NEXT BOARD :: 下一局闭环面板"
        lines = [
            title,
            "  [复盘] ouro status | ouro run-report",
            "  [图鉴] ouro codex",
            f"  [配置] ouro list-heroes | ouro hero-card {hero_id} --prompt-style {style}",
            f"  [重开] {rematch}",
        ]
        if state.result == "defeat":
            lines.append("  [建议] 先复盘最后回合，再用 control/guarded 重开。")
        elif state.result == "victory":
            lines.append("  [建议] 保持当前打法，再用下一 seed 做压力样本。")
        else:
            lines.append("  [建议] 先回放观察关键窗口，再继续固定种子练习。")
        return lines

    title = "PLAY NEXT BOARD"
    lines = [
        f"{title} :: NEXT FIGHT LOOP",
        "  [REVIEW] ouro status | ouro run-report",
        "  [CODEX] ouro codex",
        f"  [LOADOUT] ouro list-heroes | ouro hero-card {hero_id} --prompt-style {style}",
        f"  [REMATCH] {rematch}",
    ]
    if state.result == "defeat":
        lines.append(
            "  [GUIDANCE] Review this run first, then retry with control/guarded."
        )
    elif state.result == "victory":
        lines.append("  [GUIDANCE] Keep the plan, then raise pressure with next seed.")
    else:
        lines.append(
            "  [GUIDANCE] Replay one fixed-seed sample to settle intent timing."
        )
    return lines


def _battle_report_skill_name(state: BattleState, skill_id: str) -> str:
    skill = state.hero.find_skill(skill_id)
    if skill is None:
        return skill_id
    return skill.display_name


def _render_battle_result_board(
    state: BattleState,
    *,
    hero_turns: int,
    enemy_turns: int,
    action_ratio: str,
    damage_dealt: int,
    damage_taken: int,
    fallback_count: int,
    lang: str,
) -> list[str]:
    hp_ratio = state.hero.hp / max(1, state.hero.max_hp)
    result = state.result or "ongoing"
    if lang == "zh":
        if result == "victory":
            next_step = "保持变量，挑战更高压力" if hp_ratio >= 0.5 else "先补恢复，再进高压节点"
        elif result == "defeat":
            next_step = "切 control/guarded，复盘最后两回合"
        elif result == "timeout":
            next_step = "提高输出或减少防御循环"
        else:
            next_step = "继续观察行动帧"
        pressure = "高压" if damage_taken >= max(20, state.hero.max_hp // 2) else "可控"
        return [
            "BATTLE RESULT BOARD :: 战斗结果板",
            f"  [RESULT] {result} | HP {state.hero.hp}/{state.hero.max_hp} | MP {state.hero.mp}/{state.hero.max_mp}",
            f"  [TEMPO] hero {hero_turns} / enemy {enemy_turns} / tick {state.tick}",
            f"  [ACTION] basic:skill {action_ratio} / fallbacks {fallback_count}",
            f"  [DAMAGE] dealt {damage_dealt} / taken {damage_taken} / pressure {pressure}",
            f"  [NEXT] {next_step}",
        ]
    if result == "victory":
        next_step = "keep variables, raise pressure" if hp_ratio >= 0.5 else "repair HP before elite/boss"
    elif result == "defeat":
        next_step = "switch control/guarded, review last two turns"
    elif result == "timeout":
        next_step = "raise damage or reduce defense loops"
    else:
        next_step = "keep watching turn frames"
    pressure = "high" if damage_taken >= max(20, state.hero.max_hp // 2) else "controlled"
    return [
        "BATTLE RESULT BOARD",
        f"  [RESULT] {result} | HP {state.hero.hp}/{state.hero.max_hp} | MP {state.hero.mp}/{state.hero.max_mp}",
        f"  [TEMPO] hero {hero_turns} / enemy {enemy_turns} / tick {state.tick}",
        f"  [ACTION] basic:skill {action_ratio} / fallbacks {fallback_count}",
        f"  [DAMAGE] dealt {damage_dealt} / taken {damage_taken} / pressure {pressure}",
        f"  [NEXT] {next_step}",
    ]


def _render_battle_turn_map(state: BattleState, records: list[TurnRecord], *, lang: str) -> list[str]:
    limit = 14
    visible = records[:limit]
    hidden = max(0, len(records) - limit)
    flow = " -> ".join(_battle_turn_token(record) for record in visible)
    if hidden:
        flow = f"{flow} -> +{hidden}" if flow else f"+{hidden}"
    if not flow:
        flow = "-"
    first_hero = next((record for record in records if record.side == "hero"), None)
    peak_hit = max((_battle_turn_damage(record) for record in records if record.side == "hero"), default=0)
    enemy_damage = sum(_battle_turn_damage(record) for record in records if record.side == "enemy")
    first_text = _battle_turn_label(state, first_hero, lang=lang) if first_hero else ("none" if lang == "en" else "无")
    read = _battle_turn_map_read(records, peak_hit=peak_hit, enemy_damage=enemy_damage, lang=lang)
    if lang == "zh":
        return [
            "BATTLE TURN MAP :: 回合轨道",
            f"  [FLOW] {flow}",
            f"  [FIRST HERO] {first_text}",
            f"  [IMPACT] peak hit {peak_hit} / enemy damage {enemy_damage}",
            f"  [READ] {read}",
        ]
    return [
        "BATTLE TURN MAP",
        f"  [FLOW] {flow}",
        f"  [FIRST HERO] {first_text}",
        f"  [IMPACT] peak hit {peak_hit} / enemy damage {enemy_damage}",
        f"  [READ] {read}",
    ]


def _battle_turn_token(record: TurnRecord) -> str:
    prefix = "H" if record.side == "hero" else "E"
    suffix = ""
    damage = _battle_turn_damage(record)
    if damage:
        suffix = f"-{damage}"
    elif record.side == "enemy" and (record.enemy_action or {}).get("type") == "chant_charge":
        suffix = "CHG"
    elif record.side == "enemy" and (record.enemy_action or {}).get("type") == "silenced":
        suffix = "BRK"
    return f"{prefix}{record.tick:03d}{suffix}"


def _battle_turn_damage(record: TurnRecord) -> int:
    if record.side == "hero":
        return record.judge.damage if record.judge is not None else 0
    return int((record.enemy_action or {}).get("damage", 0))


def _battle_turn_label(state: BattleState, record: TurnRecord | None, *, lang: str) -> str:
    if record is None:
        return "none" if lang == "en" else "无"
    if record.action is None:
        return "pending" if lang == "en" else "等待"
    if record.action.type == "cast_skill" and record.judge is not None and record.judge.skill_id:
        return _battle_report_skill_name(state, record.judge.skill_id)
    return record.action.type


def _battle_turn_map_read(
    records: list[TurnRecord],
    *,
    peak_hit: int,
    enemy_damage: int,
    lang: str,
) -> str:
    if not records:
        return "no resolved turns" if lang == "en" else "暂无已结算回合"
    hero_turns = sum(1 for record in records if record.side == "hero")
    enemy_turns = sum(1 for record in records if record.side == "enemy")
    if enemy_damage >= 40:
        return "enemy burst shaped the fight" if lang == "en" else "敌方爆发主导战局"
    if peak_hit >= 35:
        return "one hero hit created the swing" if lang == "en" else "一次英雄重击制造转折"
    if enemy_turns > hero_turns:
        return "enemy tempo led the map" if lang == "en" else "敌方节奏领先"
    if hero_turns > enemy_turns:
        return "hero tempo led the map" if lang == "en" else "英雄节奏领先"
    return "tempo stayed even; inspect windows" if lang == "en" else "节奏均衡；检查窗口"


def _victory_readout(state: BattleState, *, damage_taken: int, lang: str) -> list[str]:
    if lang == "zh":
        hp_ratio = state.hero.hp / max(1, state.hero.max_hp)
        pressure = "几乎无伤" if damage_taken <= 0 else ("稳住了血线" if hp_ratio >= 0.5 else "险胜，血线已经见底")
        return [
            "战术回放:",
            f"  - {pressure}；下一场开局 HP {state.hero.hp}/{state.hero.max_hp}，MP {state.hero.mp}/{state.hero.max_mp}。",
            "  - 模型行动已经过本地裁判结算；伤害、胜负和奖励没有交给模型决定。",
        ]
    hp_ratio = state.hero.hp / max(1, state.hero.max_hp)
    pressure = "clean win" if damage_taken <= 0 else ("stable HP line" if hp_ratio >= 0.5 else "thin-margin win")
    return [
        "Tactical Readout:",
        f"  - {pressure}; next fight starts at HP {state.hero.hp}/{state.hero.max_hp}, MP {state.hero.mp}/{state.hero.max_mp}.",
        "  - Model choices were judged locally; damage, victory, and rewards stayed deterministic.",
    ]


def _defeat_readout(
    state: BattleState,
    *,
    damage_taken: int,
    diagnosis,
    lang: str,
) -> list[str]:
    review = render_failure_review(diagnosis, language=lang)
    if lang == "zh":
        lines = [
            "战败回放:",
            f"  - 总承伤 {damage_taken}；最后日志：{state.log[-1] if state.log else '未知'}。",
        ]
        lines.extend(review)
        return lines
    lines = [
        "Defeat Readout:",
        f"  - Damage taken {damage_taken}; final log: {state.log[-1] if state.log else 'unknown'}.",
    ]
    lines.extend(review)
    return lines


def _timeout_readout(state: BattleState, *, lang: str) -> list[str]:
    if lang == "zh":
        return [
            "超时回放:",
            "  - 战斗拖入异常保护。建议提高输出、降低防守循环，或检查敌方治疗/护盾。",
        ]
    return [
        "Timeout Readout:",
        "  - Battle hit the safety limit. Increase damage, reduce defensive loops, or inspect enemy sustain.",
    ]


def _battle_report_status_details(state: BattleState, *, lang: str) -> list[str]:
    entries: list[str] = []
    for status in state.hero.statuses:
        entries.append(f"  - HERO {format_status_detail(status)}")
    for enemy in state.enemies:
        for status in enemy.statuses:
            entries.append(f"  - [{enemy.short_glyph}] {format_status_detail(status)}")
    if not entries:
        return []
    title = "Status Details:" if lang == "en" else "状态详情:"
    return [title, *entries]


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
    hp_bar = bar(enemy.hp, enemy.max_hp, width=6, unicode_mode=unicode_mode)
    atb_bar = bar(min(enemy.atb, 100), 100, width=6, unicode_mode=unicode_mode)
    status = _roster_status_chips(enemy.statuses)
    status_part = f" {status}" if status else ""
    state_tag = label("down", lang) if not enemy.is_alive else ""
    name_field = pad_right(_roster_enemy_name(enemy), 16)
    return (
        f"{idx}. [{enemy.short_glyph}] {name_field} "
        f"HP {hp_bar} {enemy.hp}/{enemy.max_hp}   "
        f"ATB {atb_bar}{status_part} {state_tag}"
    ).rstrip()


def _roster_status_chips(statuses: list) -> str:
    if not statuses:
        return ""
    chips = [_canvas_status_chip(status) for status in statuses[:3]]
    hidden = len(statuses) - len(chips)
    if hidden > 0:
        chips.append(f"+{hidden}")
    return "FX " + " ".join(chips)


def _roster_enemy_name(enemy: Enemy) -> str:
    if visual_width(enemy.name) <= 16:
        return enemy.name
    for choice in _canvas_enemy_stage_name_choices(enemy):
        if visual_width(choice) <= 16:
            return choice.title()
    return enemy.short_glyph.upper()


def _render_turn(record: TurnRecord | None, *, lang: str) -> list[str]:
    if record is None:
        return [label("awaiting", lang)]
    if record.side == "enemy":
        action = record.enemy_action or {}
        kind = _director_text(str(action.get("type", "wait")), lang)
        return [
            label("enemy_actor_acts", lang).format(
                actor_id=record.actor_id,
                kind=kind,
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
    result = [
        narration,
    ]
    result.extend(
        [
            f"{label('action_label', lang)}: {action_text}",
            f"{label('judge_label', lang)}: {judge_marker} | {judge_text}{fallback_marker}",
            f"{label('echo_cost', lang)}: {record.usage_total_tokens} {label('tokens_unit', lang)} | "
            f"{label('ritual_time', lang)}: {record.usage_latency_ms}ms | "
            f"{label('trace_local', lang)}",
        ]
    )
    return result


def _hero_default_act(record: TurnRecord, lang: str) -> str:
    return label("awaiting", lang)


def _render_model_thinking_panel(
    record: TurnRecord | None, *, frame: BattleFrame, width: int = 100, lang: str
) -> list[str]:
    title = "MODEL INTENT" if lang == "en" else "模型意图"
    lines = [title]

    if record is None or record.side == "enemy":
        lines.append(f"  {fit_text(_director_text(frame.intent, lang), max(20, width - 4))}")
        return lines

    validation = record.validation
    raw_thinking = None

    if validation and validation.analysis:
        raw_thinking = validation.analysis
    elif record.raw_text:
        raw_thinking = record.raw_text

    lines.append(f"  {fit_text(_director_text(frame.intent, lang), max(20, width - 4))}")
    lines.append(f"  {fit_text(_director_text(frame.risk, lang), max(20, width - 4))}")
    if raw_thinking:
        first_line = raw_thinking.strip().splitlines()[0]
        lines.append(f"  detail: {fit_text(first_line, max(12, width - 12))}")

    return lines


def _render_hero_line_panel(
    state: BattleState, last_record: TurnRecord | None, *, frame: BattleFrame, lang: str
) -> list[str]:
    lines = [label("hero_line", lang)]

    hero = state.hero
    hp_pct = hero.hp / hero.max_hp if hero.max_hp > 0 else 1.0
    mp_pct = hero.mp / hero.max_mp if hero.max_mp > 0 else 1.0
    hero_id = hero.id

    line = _select_hero_line(
        hero_id=hero_id,
        hp_pct=hp_pct,
        mp_pct=mp_pct,
        record=last_record,
        frame=frame,
        lang=lang,
    )
    lines.append(f"  {line}")
    return lines


_HERO_LINES: dict[str, dict[str, list[str]]] = {
    "hero_shadow_apprentice": {
        "en": [
            "The candle flickers... I can feel the darkness respond.",
            "Stay back. This void isn't for you to walk through.",
            "My focus is sharp. The seal is ready.",
            "These candles won't burn out. Not on my watch.",
            "The Codex grows. So do I.",
        ],
        "zh": [
            "烛火摇曳...我能感受到黑暗的回应。",
            "退下。这片虚空不是你能穿行的。",
            "我的专注如刀锋般锐利。封印已就绪。",
            "这些蜡烛不会熄灭。至少在我还站着的时候。",
            "秘典在成长。我也在。",
        ],
    },
    "hero_ash_guardian": {
        "en": [
            "This shield has weathered worse. I will not break.",
            "Stand behind me. Let this tower take the first blow.",
            "My armor remembers every scar. Every lesson.",
            "Ember and ash. That's all that will remain of you.",
            "The tower holds. I hold the tower.",
        ],
        "zh": [
            "这面盾牌承受过更糟的。我不会崩溃。",
            "站在我身后。让这座塔来承受第一击。",
            "我的护甲记得每一道伤疤。每一次教训。",
            "余烬与灰烬。这就是你最终的命运。",
            "塔在坚守。我在坚守塔。",
        ],
    },
    "hero_broken_string_hunter": {
        "en": [
            "The crossbow string snapped. I didn't.",
            "You won't see the hook coming. Trust me.",
            "Bleed them dry. Let them taste their own blood.",
            "One wrong move... and this hook finds you.",
            "Fast, precise, and always one step ahead.",
        ],
        "zh": [
            "弩弦断了。我没有。",
            "你看不到钩刃的到来。相信我。",
            "把他们的血流干。让他们尝尝自己的血。",
            "一步走错...钩子就会找上你。",
            "迅捷、精准，永远领先一步。",
        ],
    },
}


_HERO_LINE_FALLBACK: dict[str, list[str]] = {
    "en": [
        "My turn. Let's see what you've got.",
        "Stand ready. The fight continues.",
        "Victory is within reach.",
        "Stay focused. Stay alive.",
    ],
    "zh": [
        "轮到我了。让我看看你有什么本事。",
        "保持警惕。战斗仍在继续。",
        "胜利就在眼前。",
        "保持专注。活下去。",
    ],
}


def _select_hero_line(
    *,
    hero_id: str,
    hp_pct: float,
    mp_pct: float,
    record: TurnRecord | None,
    frame: BattleFrame | None = None,
    lang: str,
) -> str:
    hero_lines = _HERO_LINES.get(hero_id, _HERO_LINE_FALLBACK)
    lang_lines = hero_lines.get(lang, hero_lines.get("en", _HERO_LINE_FALLBACK["en"]))

    if len(lang_lines) == 0:
        lang_lines = _HERO_LINE_FALLBACK.get(lang, _HERO_LINE_FALLBACK["en"])

    idx = 0

    if record and record.tick > 0:
        idx = record.tick % len(lang_lines)
    else:
        idx = 0

    line = lang_lines[idx]

    if frame is not None:
        contextual = _get_contextual_line(hero_id, frame, hp_pct=hp_pct, mp_pct=mp_pct, lang=lang)
        if contextual:
            return contextual

    if hp_pct < 0.3:
        line = _get_critical_line(hero_id, lang)

    return line


def _get_contextual_line(
    hero_id: str,
    frame: BattleFrame,
    *,
    hp_pct: float,
    mp_pct: float,
    lang: str,
) -> str | None:
    return select_dialogue_line(
        hero_id,
        frame=frame,
        hp_pct=hp_pct,
        mp_pct=mp_pct,
        lang=lang,
        tick=frame.tick,
    )


def _get_critical_line(hero_id: str, lang: str) -> str:
    critical_lines = {
        "hero_shadow_apprentice": {
            "en": "The flames... fading. But I'm not done yet.",
            "zh": "火焰...正在消逝。但我还没完。",
        },
        "hero_ash_guardian": {
            "en": "The shield... is cracking. But so are you.",
            "zh": "盾牌...正在开裂。但你也是。",
        },
        "hero_broken_string_hunter": {
            "en": "Wounded... but still more dangerous than you.",
            "zh": "受伤了...但仍比你危险。",
        },
    }
    fallback = {
        "en": "I'm not falling. Not here. Not now.",
        "zh": "我不会倒下。不在这里。不是现在。",
    }
    hero_critical = critical_lines.get(hero_id, {})
    return hero_critical.get(lang, hero_critical.get("en", fallback[lang]))


def _format_status(status) -> str:
    return format_status_short(status)


def render_hero_list(
    bundle: ContentBundle, *, language: str = DEFAULT_LANGUAGE
) -> str:
    lang = language
    prompt = (
        "Enter a number to choose; use 'ouro hero-card <id>' for full details."
        if lang == "en"
        else "输入编号选择；用 ouro hero-card <id> 查看完整详情。"
    )
    lines: list[str] = [label("hero_list_title", lang), prompt]
    lines.append("")
    lines.extend(_render_hero_roster_board(bundle, lang=lang))
    lines.append("")
    lines.extend(_render_weapon_gallery_board(bundle, lang=lang))
    lines.append("")
    cards: list[list[str]] = []
    for idx, hero in enumerate(bundle.heroes.values(), start=1):
        build = _safe_resolve_build(hero, bundle)
        name = hero.display_name.get(lang)
        cls = hero.class_name.get(lang)
        weapon = (
            build.items[0].display_name.get(lang)
            if build and build.items
            else _hero_card_icons(hero.id)[0]
        )
        build_name = build.archetype(lang) if build else HERO_BUILD_ARCHETYPES.get(hero.id, {}).get(lang, "Unknown")
        risk = build.risk_level() if build else HERO_RISK_LEVELS.get(hero.id, "normal")
        stage_badge = ""
        if build:
            progress = build.calculate_progress(bundle)
            stage_badge = f" {progress.stage.badge}"
        tags = " / ".join(hero.tags[:3]) or "-"
        desc = hero.description.get(lang)
        cards.append(
            _hero_select_card(
                idx=idx,
                name=name,
                short_tag=hero.short_tag,
                class_name=cls,
                stage_badge=stage_badge,
                build_name=build_name,
                weapon=weapon,
                risk=label(f"hero_card_risk_{risk}", lang) or risk,
                tags=tags,
                hero_id=hero.id,
                description=desc,
                lang=lang,
            )
        )

    for left_idx in range(0, len(cards), 2):
        left = cards[left_idx]
        right = cards[left_idx + 1] if left_idx + 1 < len(cards) else [""] * len(left)
        row_height = max(len(left), len(right))
        left.extend([""] * (row_height - len(left)))
        right.extend([""] * (row_height - len(right)))
        for left_line, right_line in zip(left, right):
            lines.append(f"{pad_right(left_line, 39)}  {right_line}".rstrip())
    return "\n".join(lines).rstrip() + "\n"


def _render_hero_roster_board(bundle: ContentBundle, *, lang: str) -> list[str]:
    title = "HERO ROSTER BOARD" if lang == "en" else "英雄队列面板"
    lines = [title]
    for idx, hero in enumerate(bundle.heroes.values(), start=1):
        build = _safe_resolve_build(hero, bundle)
        if build:
            risk = build.risk_level()
            progress = build.calculate_progress(bundle)
            stage = progress.stage.badge
        else:
            risk = HERO_RISK_LEVELS.get(hero.id, "normal")
            stage = "[SEED]"
        prompt_style = _hero_default_prompt_style(hero.id)
        core_tags = " / ".join(HERO_CORE_TAGS.get(hero.id, ())[:2]) or "-"
        opener = _hero_loadout_opener(hero.id, prompt_style=prompt_style, lang=lang)
        name = hero.display_name.get(lang) or hero.display_name.get("en", hero.id)
        if lang == "zh":
            line = (
                f"  [{idx}] {name} {stage} | Prompt {prompt_style} | "
                f"风险 {risk} | {core_tags} | {opener}"
            )
        else:
            line = (
                f"  [{idx}] {name} {stage} | Prompt {prompt_style} | "
                f"Risk {risk} | {core_tags} | {opener}"
            )
        lines.append(fit_text(line, 96))
    next_line = (
        "Next: ouro hero-card <hero_id> --prompt-style <name>"
        if lang == "en"
        else "下一步: ouro hero-card <英雄ID> --prompt-style <name>"
    )
    lines.append(next_line)
    return lines


def _render_weapon_gallery_board(bundle: ContentBundle, *, lang: str) -> list[str]:
    title = "WEAPON GALLERY BOARD" if lang == "en" else "武器图鉴面板"
    lines = [title]
    for idx, hero in enumerate(bundle.heroes.values(), start=1):
        build = _safe_resolve_build(hero, bundle)
        progress = build.calculate_progress(bundle) if build else None
        stage = progress.stage.badge if progress else hero_weapon_card(hero.id)[1]
        stage_name = progress.stage_name if progress else "Seed"
        card = hero_weapon_card_art(hero.id)
        weapon, _badge = hero_weapon_card(hero.id)
        art = " / ".join(row.strip() for row in card.ascii_art[:2])
        name = hero.display_name.get(lang) or hero.display_name.get("en", hero.id)
        if lang == "zh":
            line = (
                f"  [{idx}] {weapon} {stage} | {name} | {art} | "
                f"{stage_name}"
            )
            detail = f"      Build: {card.build_shift} | AI: {card.ai_effect}"
        else:
            line = (
                f"  [{idx}] {weapon} {stage} | {stage_name} | {art} | "
                f"{name}"
            )
            detail = f"      Build: {card.build_shift} | AI: {card.ai_effect}"
        lines.append(fit_text(line, 96))
        lines.append(fit_text(detail, 96))
    next_line = (
        "Next: compare weapon silhouettes, then open hero-card for full Build plan"
        if lang == "en"
        else "下一步: 先比较武器轮廓，再打开 hero-card 查看完整 Build 计划"
    )
    lines.append(fit_text(next_line, 96))
    return lines


def _hero_default_prompt_style(hero_id: str) -> str:
    return {
        "hero_shadow_apprentice": "control",
        "hero_ash_guardian": "guarded",
        "hero_broken_string_hunter": "aggressive",
        "hero_mire_oracle": "attrition",
        "hero_gravewright": "control",
        "hero_echo_exile": "guarded",
    }.get(hero_id, "guarded")


def _hero_select_card(
    *,
    idx: int,
    name: str,
    short_tag: str,
    class_name: str,
    stage_badge: str,
    build_name: str,
    weapon: str,
    risk: str,
    tags: str,
    hero_id: str,
    description: str,
    lang: str,
) -> list[str]:
    header = f"[{idx}] {name} {short_tag} {stage_badge}".strip()
    subtitle = class_name
    body = [
        subtitle,
        f"{label('hero_card_build', lang)}: {build_name}  {label('hero_card_weapon', lang)}: {weapon}",
        f"{label('hero_card_risk', lang)}: {risk}  {label('hero_card_tags', lang)}: {tags}",
        hero_id,
    ]
    return _choice_card(header, body, width=39, tone="hero")


def render_hero_card(
    hero: HeroData,
    bundle: ContentBundle,
    build: ResolvedBuild,
    *,
    language: str = DEFAULT_LANGUAGE,
    prompt_style: str | None = None,
    width: int = 100,
    unicode_mode: bool = False,
) -> str:
    lang = language
    name = hero.display_name.get(lang)
    cls = hero.class_name.get(lang)
    tags = " / ".join(_dedupe_preserve(build.tags)) or label("hero_card_none", lang)

    stats = (
        f"HP {build.hp}  MP {build.mp}  SPD {build.speed}  "
        f"ATK {build.attack}  DEF {build.defense}  POW {build.power}"
    )
    build_name = build.archetype(lang)
    risk = build.risk_level()
    strategy = build.strategy_lines(lang)
    weapon, build_icon = _hero_card_icons(hero.id)

    progress = build.calculate_progress(bundle)

    skills_lines = _render_action_kit_board(hero, bundle, build, lang)

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
    lines.append(f"{label('hero_card_build', lang)}: {build_name} {progress.stage.badge}")
    lines.append(f"{label('hero_card_weapon', lang)}: {weapon}")
    lines.extend(_render_weapon_card_art(hero.id, unicode_mode=unicode_mode, lang=lang))
    lines.append(f"{label('hero_card_risk', lang)}: {label(f'hero_card_risk_{risk}', lang) or risk}")
    lines.append(f"{label('hero_card_tags', lang)}:")
    for wrapped in _wrap_text(tags, 70):
        lines.append(f"  {wrapped}")
    lines.append(f"{label('hero_card_stats', lang)}: {stats}")
    lines.append("")

    lines.extend(
        _render_hero_loadout_board(
            hero,
            build,
            progress,
            prompt_style=prompt_style,
            lang=lang,
        )
    )
    lines.append("")

    lines.extend(_render_build_progress_panel(progress, hero.id, bundle, lang))
    lines.append("")

    lines.append(label("hero_card_action_kit", lang))
    lines.extend(skills_lines)
    lines.append("")
    lines.append(label("hero_card_items", lang))
    lines.extend(items_lines)
    lines.append(label("hero_card_affixes", lang))
    lines.extend(affix_lines)
    lines.append(label("hero_card_resonances", lang))
    lines.extend(resonance_lines)
    lines.append("")
    lines.append(label("hero_card_ai_bias", lang) + ":")
    for ln in strategy:
        for idx, wrapped in enumerate(_wrap_text(ln, 70)):
            prefix = "  - " if idx == 0 else "    "
            lines.append(prefix + wrapped)
    if prompt_style:
        lines.append(f"{label('hero_card_prompt_template', lang)}: {prompt_style}")
        for wrapped in _wrap_text(prompt_style_text(prompt_style, lang), 70):
            lines.append(f"  {wrapped}")
    lines.append("")
    lines.append(label("hero_card_prompt", lang) + ":")
    for ln in hero.default_prompt.get(lang).splitlines():
        for wrapped in _wrap_text(ln, 70):
            lines.append(f"  {wrapped}")
    return "\n".join(_wrap_screen_lines(lines, width))


def _render_hero_loadout_board(
    hero: HeroData,
    build: ResolvedBuild,
    progress: BuildProgress,
    *,
    prompt_style: str | None,
    lang: str,
) -> list[str]:
    style = prompt_style or "hero default"
    core_tags = HERO_CORE_TAGS.get(hero.id, ())
    core_text = " / ".join(core_tags) if core_tags else "-"
    risk = build.risk_level()
    stage = f"{progress.stage.badge} {progress.stage_name}"
    opener = _hero_loadout_opener(hero.id, prompt_style=prompt_style, lang=lang)
    command = f"ouro run --mock --hero {hero.id}"
    if prompt_style:
        command += f" --prompt-style {prompt_style}"

    if lang == "zh":
        return [
            "HERO LOADOUT BOARD :: 英雄开局配置板",
            f"  [PROMPT] {style} / Agent 行为倾向",
            f"  [BUILD] {stage} / {build.archetype(lang)}",
            f"  [CORE] {core_text}",
            f"  [RISK] {label(f'hero_card_risk_{risk}', lang) or risk}",
            f"  [OPENER] {opener}",
            f"  [RUN] {command}",
        ]
    return [
        "HERO LOADOUT BOARD",
        f"  [PROMPT] {style} / agent behavior",
        f"  [BUILD] {stage} / {build.archetype(lang)}",
        f"  [CORE] {core_text}",
        f"  [RISK] {label(f'hero_card_risk_{risk}', lang) or risk}",
        f"  [OPENER] {opener}",
        f"  [RUN] {command}",
    ]


def _hero_loadout_opener(hero_id: str, *, prompt_style: str | None, lang: str) -> str:
    if prompt_style == "control":
        return "先控吟唱窗口" if lang == "zh" else "open by denying chant windows"
    if prompt_style == "guarded":
        return "先保血线再换节奏" if lang == "zh" else "stabilize HP before tempo"
    if prompt_style == "aggressive":
        return "优先压低第一目标" if lang == "zh" else "pressure the first target"
    if prompt_style == "attrition":
        return "先铺持续伤害" if lang == "zh" else "set damage over time early"
    defaults = {
        "hero_shadow_apprentice": {
            "en": "interrupt casters, spend MP for tempo",
            "zh": "打断施法者，用 MP 换节奏",
        },
        "hero_ash_guardian": {
            "en": "brace first, punish after telegraph",
            "zh": "先架盾，等预兆后反击",
        },
        "hero_broken_string_hunter": {
            "en": "stack bleed, execute weak targets",
            "zh": "叠流血，处决弱目标",
        },
        "hero_mire_oracle": {
            "en": "poison durable targets, mute casters",
            "zh": "给耐久目标铺毒，压制施法者",
        },
        "hero_gravewright": {
            "en": "mark targets, release engine on windows",
            "zh": "标记目标，在窗口释放机关",
        },
        "hero_echo_exile": {
            "en": "hold ward, silence heavy chants",
            "zh": "保留护壁，沉默重吟唱",
        },
    }
    entry = defaults.get(hero_id, {})
    return entry.get(lang) or entry.get("en") or "follow build plan"


def _render_build_progress_panel(
    progress: BuildProgress, hero_id: str, bundle: ContentBundle, lang: str
) -> list[str]:
    lines: list[str] = []

    stage_label = {
        "en": f"BUILD STAGE: {progress.stage_name}",
        "zh": f"构筑阶段: {progress.stage_name}",
    }.get(lang, f"BUILD STAGE: {progress.stage_name}")

    lines.append(f"{stage_label} {progress.stage.badge}")
    lines.append("")

    core_tags_label = {
        "en": "Core Tags:",
        "zh": "核心标签:",
    }.get(lang, "Core Tags:")
    lines.append(core_tags_label)
    core_tags = HERO_CORE_TAGS.get(hero_id, [])
    for tag in core_tags:
        count = progress.core_tags.get(tag, 0)
        filled = min(count, 3)
        bar_str = "[" + "#" * filled + "-" * (3 - filled) + "]"
        status_label = (
            label("hero_card_status_online", lang) if count >= 2
            else label("hero_card_status_active", lang) if count >= 1
            else label("hero_card_status_need", lang)
        )
        lines.append(f"  {tag:12} {bar_str} {count}/3  {status_label}")

    if progress.active_resonances:
        lines.append("")
        lines.append(label("hero_card_active_resonances", lang) + ":")
        for res_id in progress.active_resonances:
            lines.append(f"  [R] {_resonance_display_name(bundle, res_id, lang)}")

    if progress.near_resonances:
        lines.append("")
        lines.append(label("hero_card_near_resonances", lang) + ":")
        for near in progress.near_resonances:
            name = near["display_name"].get(lang) or near["display_name"].get("en", near["id"])
            missing_parts = []
            for miss in near["missing"]:
                need_more = miss["need"] - miss["have"]
                missing_parts.append(f"{miss['tag']} +{need_more}")
            missing_str = ", ".join(missing_parts)
            lines.append(f"  [ ] {name}  {label('hero_card_need', lang)}: {missing_str}")

    if progress.best_next_picks:
        lines.append("")
        lines.append(label("hero_card_best_next_picks", lang) + ":")
        seen: set[str] = set()
        for pick in progress.best_next_picks[:3]:
            tag = pick["tag"]
            if tag in seen:
                continue
            seen.add(tag)
            need = pick["need"]
            res_name = pick["resonance_name"].get(lang) or pick["resonance_name"].get("en", "")
            lines.append(f"  - {tag} +{need}  (for {res_name})")

    return lines


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
    return hero_weapon_card(hero_id)


_ACTION_KIT_TACTIC_PRIORITY = (
    "control",
    "interrupt",
    "guard",
    "shield",
    "buff",
    "evade",
    "execute",
    "bleed",
    "poison",
    "fire",
    "gear",
    "echo",
    "damage",
)

_ACTION_KIT_TACTIC_LABELS = {
    "control": {"en": "CONTROL", "zh": "控制"},
    "interrupt": {"en": "INTERRUPT", "zh": "打断"},
    "guard": {"en": "SURVIVE", "zh": "保命"},
    "shield": {"en": "SHIELD", "zh": "护盾"},
    "buff": {"en": "SETUP", "zh": "准备"},
    "evade": {"en": "EVADE", "zh": "躲避"},
    "execute": {"en": "EXECUTE", "zh": "处决"},
    "bleed": {"en": "BLEED", "zh": "流血"},
    "poison": {"en": "ATTRITION", "zh": "消耗"},
    "fire": {"en": "BURST", "zh": "爆发"},
    "gear": {"en": "TRAP", "zh": "机关"},
    "echo": {"en": "RESONATE", "zh": "回响"},
    "damage": {"en": "DAMAGE", "zh": "伤害"},
}

_ACTION_KIT_PURPOSE_LABELS = {
    "control": {"en": "seal chant windows", "zh": "封住吟唱窗口"},
    "interrupt": {"en": "seal chant windows", "zh": "封住吟唱窗口"},
    "guard": {"en": "brace survivability", "zh": "保护生存"},
    "shield": {"en": "keep survivability", "zh": "维持护盾"},
    "buff": {"en": "raise shield before danger", "zh": "危险前抬护盾"},
    "evade": {"en": "open dodge windows", "zh": "创造回避时机"},
    "execute": {"en": "finish weakened targets", "zh": "处决低血敌"},
    "bleed": {"en": "stack bleed pressure", "zh": "叠流血压力"},
    "poison": {"en": "start attrition", "zh": "开启消耗战"},
    "fire": {"en": "burst at pressure", "zh": "集中爆发"},
    "gear": {"en": "set up burst trap", "zh": "布置爆发机关"},
    "echo": {"en": "prepare echo reply", "zh": "准备回声"},
    "damage": {"en": "convert MP to pressure", "zh": "用 MP 换压迫"},
}


def _action_kit_tactic(skill) -> str:
    tags = _dedupe_preserve(getattr(skill, "tags", ()))
    for tag in _ACTION_KIT_TACTIC_PRIORITY:
        if tag in tags:
            label_text = _ACTION_KIT_TACTIC_LABELS.get(tag)
            return label_text["en"] if label_text else tag.upper()
    return "UTILITY"


def _action_kit_tactic_text(skill, lang: str) -> str:
    tactic = _action_kit_tactic(skill)
    if lang != "zh":
        return tactic
    lower_map = {
        value["en"]: value["zh"]
        for value in _ACTION_KIT_TACTIC_LABELS.values()
    }
    lower_map["UTILITY"] = "通用"
    return lower_map.get(tactic, tactic)


def _action_kit_purpose(skill, lang: str) -> str:
    tags = _dedupe_preserve(getattr(skill, "tags", ()))
    for tag in _ACTION_KIT_TACTIC_PRIORITY:
        if tag in tags:
            mapped = _ACTION_KIT_PURPOSE_LABELS.get(tag)
            if mapped is None:
                continue
            return mapped[lang]
    desc = skill.visible_description.get(lang)
    if desc:
        return _fit_visual(" ".join(desc.split()), 24 if lang == "en" else 20)
    return "offense" if lang == "en" else "持续输出"


def _action_kit_build_relation(skill, build: ResolvedBuild, hero: HeroData, lang: str) -> str:
    hero_core_tags = set(HERO_CORE_TAGS.get(hero.id, ()))
    build_tags = _dedupe_preserve(build.tags)
    relation = [tag for tag in _dedupe_preserve(skill.tags) if tag in build_tags]
    if not relation:
        return "off-build" if lang == "en" else "非构筑"
    if any(tag in hero_core_tags for tag in relation):
        prefix = "core" if lang == "en" else "核心"
    else:
        prefix = "support" if lang == "en" else "支援"
    return f"{prefix}/{'/'.join(relation[:2])}"


def _render_action_kit_board(
    hero: HeroData,
    bundle: ContentBundle,
    build: ResolvedBuild,
    lang: str,
) -> list[str]:
    lines: list[str] = []
    if not hero.skills:
        lines.append(f"  {label('hero_card_none', lang)}")
        return lines

    for sid in hero.skills:
        skill_data = bundle.get_skill(sid)
        code = _canvas_skill_code(skill_data)
        lines.append(
            f"  [{code}] {skill_data.display_name.get(lang)} "
            f"{label('hero_card_mp', lang)} {skill_data.mp_cost}, "
            f"{label('hero_card_cd', lang)} {skill_data.cooldown} | "
            f"{label('hero_card_positioning', lang)} {_action_kit_tactic_text(skill_data, lang)} | "
            f"{label('hero_card_use', lang)} {_action_kit_purpose(skill_data, lang)} | "
            f"{label('hero_card_build_relation', lang)} {_action_kit_build_relation(skill_data, build, hero, lang)}"
        )
    return lines


def _render_weapon_card_art(hero_id: str, *, unicode_mode: bool, lang: str) -> list[str]:
    card = hero_weapon_card_art(hero_id)
    title = "武器卡" if lang == "zh" else "WEAPON CARD"
    build_title = "构筑变化" if lang == "zh" else "Build Before -> After"
    ai_title = "AI 行为" if lang == "zh" else "AI Effect"
    art = card.unicode_art if unicode_mode else card.ascii_art
    lines = [f"{title}: {card.icon} {card.badge}"]
    lines.extend(f"  {row}" for row in art)
    lines.append(f"  {build_title}: {card.build_shift}")
    lines.append(f"  {ai_title}: {card.ai_effect}")
    return lines


def _node_type_label(node_type: str, lang: str) -> str:
    """Get a localized label for a node type."""
    labels = {
        "normal_combat": "route_node_normal",
        "elite_combat": "route_node_elite",
        "boss": "route_node_boss",
        "shop": "route_node_shop",
        "event": "route_node_event",
        "rest": "route_node_rest",
        "mimic_chest": "route_node_elite",
    }
    key = labels.get(node_type, "route_node_normal")
    return label(key, lang)


def _risk_level_label(risk_level: str | None, lang: str) -> str:
    """Get a localized label for a risk level."""
    if risk_level is None:
        return ""
    labels = {
        "low": "route_risk_low",
        "medium": "route_risk_medium",
        "high": "route_risk_high",
        "safe": "route_risk_safe",
    }
    key = labels.get(risk_level, "route_risk_low")
    return label(key, lang)


def _route_decision_hint(node, bundle: ContentBundle, *, lang: str) -> str:
    if node.node_type in ("normal_combat", "elite_combat", "boss", "mimic_chest"):
        chant_count = 0
        elite_count = 0
        for enemy_id in node.enemy_ids:
            enemy = bundle.enemies.get(enemy_id)
            if enemy is None:
                continue
            if enemy.behavior.kind == "rule_chant":
                chant_count += 1
            if enemy.tier != "trace":
                elite_count += 1
        if lang == "zh":
            parts = []
            if chant_count:
                parts.append(f"{chant_count} 个吟唱敌人，保留打断 MP")
            if elite_count:
                parts.append(f"{elite_count} 个高阶敌人，收益更高但血线压力更大")
            return "决策: " + ("；".join(parts) if parts else "标准战斗，适合补资源和 Build 节奏")
        parts = []
        if chant_count:
            parts.append(f"{chant_count} chant threat; keep interrupt MP")
        if elite_count:
            parts.append(f"{elite_count} higher-tier threat; stronger reward pressure")
        return "Decision: " + ("; ".join(parts) if parts else "standard fight for tempo and build progress")
    if node.node_type == "shop":
        return "决策: 花金币换稳定性或 Build 拼图" if lang == "zh" else "Decision: spend gold for stability or build pieces"
    if node.node_type == "rest":
        return "决策: 用节点机会换 HP/MP 安全线" if lang == "zh" else "Decision: trade a node for HP/MP safety"
    if node.node_type == "event":
        return "决策: 通常是高弹性奖励，按当前短板选择" if lang == "zh" else "Decision: flexible reward; choose against the current weakness"
    return ""


def _route_reward_preview(node, bundle: ContentBundle, *, lang: str) -> str:
    parts: list[str] = []
    if node.rewards:
        if node.rewards.gold:
            parts.append(f"{node.rewards.gold}g")
        if node.rewards.xp:
            parts.append(f"{node.rewards.xp}xp")
        for choice in node.rewards.reward_choices[:3]:
            if choice.type == "item" and choice.item_id in bundle.items:
                item = bundle.items[choice.item_id]
                tags = "/".join(item.tags[:2]) if item.tags else "item"
                parts.append(f"{item.display_name.get(lang)} [{tags}]")
            elif choice.type == "affix" and choice.affix_id in bundle.affixes:
                affix = bundle.affixes[choice.affix_id]
                tags = "/".join(affix.tags[:2]) if affix.tags else "affix"
                parts.append(f"{affix.display_name.get(lang)} [{tags}]")
            elif choice.type == "codex":
                parts.append("Codex +1" if lang == "en" else "图鉴 +1")
            elif choice.type == "heal":
                parts.append("healing" if lang == "en" else "治疗")
            elif choice.type == "gold" and choice.gold:
                parts.append(f"{choice.gold}g")

    if node.node_type == "shop":
        shop_types = {item.type for item in node.shop_items}
        if "heal" in shop_types:
            parts.append("recovery" if lang == "en" else "恢复")
        if {"item", "affix"} & shop_types:
            parts.append("targeted tags" if lang == "en" else "定向标签")
        if "strategy" in shop_types:
            parts.append("Prompt style" if lang == "en" else "Prompt 预设")
        if "scout" in shop_types:
            parts.append("scouting" if lang == "en" else "侦察")
    elif node.node_type == "rest":
        parts.extend(
            ["Recover", "Focus", "Study"]
            if lang == "en"
            else ["恢复", "专注", "研读"]
        )
    elif node.node_type == "event" and not parts:
        parts.append("flexible event reward" if lang == "en" else "弹性事件奖励")

    if not parts:
        parts.append("none" if lang == "en" else "无")
    line = ", ".join(parts[:6])
    return f"Reward: {line}" if lang == "en" else f"收益: {line}"


def _route_cost_preview(state, node, bundle: ContentBundle, *, lang: str) -> str:
    hp_ratio = state.current_hp / max(1, state.max_hp)
    mp_ratio = state.current_mp / max(1, state.max_mp)
    enemy_count = len(getattr(node, "enemy_ids", ()))
    has_chant = any(
        bundle.enemies.get(enemy_id) is not None
        and bundle.enemies[enemy_id].behavior.kind == "rule_chant"
        for enemy_id in getattr(node, "enemy_ids", ())
    )
    has_elite = any(
        bundle.enemies.get(enemy_id) is not None
        and bundle.enemies[enemy_id].tier != "trace"
        for enemy_id in getattr(node, "enemy_ids", ())
    )

    if node.node_type == "shop":
        text = "gold / no combat / no XP" if lang == "en" else "金币 / 无战斗 / 无经验"
    elif node.node_type == "rest":
        text = "route tempo / restores HP and MP" if lang == "en" else "路线节奏 / 恢复 HP 与 MP"
    elif node.node_type == "event":
        text = "variable / no guaranteed combat" if lang == "en" else "可变 / 不保证战斗"
    elif has_chant and mp_ratio <= 0.35:
        text = "high MP pressure; interrupt reserve required" if lang == "en" else "高 MP 压力；必须预留打断资源"
    elif has_elite or node.node_type in ("elite_combat", "boss", "mimic_chest"):
        text = "medium HP loss / high reward pressure" if lang == "en" else "中等 HP 损耗 / 高收益压力"
    elif enemy_count >= 2:
        text = "HP chip / 4-8 hero turns" if lang == "en" else "小幅 HP 损耗 / 4-8 次英雄行动"
    elif hp_ratio <= 0.4:
        text = "low HP risk even in a clean fight" if lang == "en" else "低血线下普通战也有风险"
    else:
        text = "low HP chip / MP safe" if lang == "en" else "低 HP 损耗 / MP 安全"

    return f"Cost: {text}" if lang == "en" else f"消耗: {text}"


def _route_build_fit(state, node, bundle: ContentBundle, *, lang: str) -> str:
    build = state.resolved_build(bundle)
    tags = build.tag_counts()
    hp_ratio = state.current_hp / max(1, state.max_hp)
    mp_ratio = state.current_mp / max(1, state.max_mp)
    has_chant = any(
        bundle.enemies.get(enemy_id) is not None
        and bundle.enemies[enemy_id].behavior.kind == "rule_chant"
        for enemy_id in getattr(node, "enemy_ids", ())
    )
    has_elite = any(
        bundle.enemies.get(enemy_id) is not None
        and bundle.enemies[enemy_id].tier != "trace"
        for enemy_id in getattr(node, "enemy_ids", ())
    )

    if node.node_type == "rest":
        fit = "synergy" if hp_ratio <= 0.55 or mp_ratio <= 0.25 else "neutral"
        reason = "repairs HP/MP before pressure" if lang == "en" else "在压力战前修复 HP/MP"
    elif node.node_type == "shop":
        fit = "synergy" if state.gold >= 14 else "neutral"
        reason = "can buy missing tags or recovery" if lang == "en" else "可购买缺失标签或恢复"
    elif node.node_type == "event":
        fit = "neutral"
        reason = "flexible pivot node" if lang == "en" else "弹性转向节点"
    elif has_chant and tags.get("control", 0) >= 2 and mp_ratio > 0.35:
        fit = "synergy"
        reason = "control build can answer chants" if lang == "en" else "控制 Build 可回应吟唱"
    elif has_chant and mp_ratio <= 0.35:
        fit = "danger"
        reason = "chant fight while interrupt MP is low" if lang == "en" else "低打断 MP 进入吟唱战"
    elif has_elite and (tags.get("guard", 0) + tags.get("armor", 0)) < 2 and hp_ratio <= 0.7:
        fit = "danger"
        reason = "elite pressure without survival tags" if lang == "en" else "缺少生存标签承接精英压力"
    else:
        fit = "neutral"
        reason = "standard tempo for current build" if lang == "en" else "适合当前 Build 的标准节奏"

    return (
        f"Build fit: {fit} - {reason}"
        if lang == "en"
        else f"Build 适配: {fit} - {reason}"
    )


def _route_recommendation(state, node, bundle: ContentBundle, *, lang: str) -> str:
    hp_ratio = state.current_hp / max(1, state.max_hp)
    mp_ratio = state.current_mp / max(1, state.max_mp)
    has_chant = any(
        bundle.enemies.get(enemy_id) is not None
        and bundle.enemies[enemy_id].behavior.kind == "rule_chant"
        for enemy_id in getattr(node, "enemy_ids", ())
    )
    risk = node.risk_level or "medium"

    if node.node_type == "rest":
        if hp_ratio <= 0.55 or mp_ratio <= 0.25:
            return "[REC] low resources; rest protects the run" if lang == "en" else "[推荐] 资源偏低，休整能保住本局"
        return "[SKIP?] healthy enough; tempo may matter more" if lang == "en" else "[可跳过] 状态健康，路线节奏可能更重要"
    if node.node_type == "shop":
        if state.gold >= 14:
            return "[REC] gold can become build power here" if lang == "en" else "[推荐] 当前金币能转化为 Build 强度"
        return "[LOW VALUE] little gold; visit only for scouting" if lang == "en" else "[低收益] 金币不足，除非想侦察"
    if node.node_type == "event":
        return "[FLEX] best when you need healing, gold, or a missing tag" if lang == "en" else "[弹性] 适合补治疗、金币或缺失标签"
    if node.node_type in ("elite_combat", "boss", "mimic_chest") or risk == "high":
        if hp_ratio <= 0.6 or (has_chant and mp_ratio <= 0.35):
            return "[DANGER] recover before taking this fight" if lang == "en" else "[危险] 建议先恢复再挑战"
        return "[GREED] high pressure, higher proof of build strength" if lang == "en" else "[贪心] 压力高，但最能验证 Build"
    if has_chant and mp_ratio <= 0.35:
        return "[RISK] chant fight while MP is low" if lang == "en" else "[风险] 低 MP 进入吟唱战"
    return "[REC] clean tempo fight" if lang == "en" else "[推荐] 节奏清晰的战斗节点"


def _choice_build_preview(
    state,
    bundle: ContentBundle,
    *,
    item_id: str | None = None,
    affix_id: str | None = None,
    lang: str,
) -> list[str]:
    current = state.resolved_build(bundle)
    item_ids = list(getattr(state, "item_ids", ()))
    affix_ids = list(getattr(state, "affix_ids", ()))
    if item_id:
        item_ids.append(item_id)
    if affix_id:
        affix_ids.append(affix_id)
    hero = bundle.get_hero(state.hero_id)
    projected = resolve_build(
        hero,
        bundle,
        item_ids=tuple(item_ids),
        affix_ids=tuple(affix_ids),
    )
    before = current.calculate_progress(bundle)
    after = projected.calculate_progress(bundle)
    stats = _stat_delta_summary(current, projected)
    tag_delta = _tag_delta_summary(current, projected)
    cross_note = _cross_build_seed_note(state.hero_id, current, projected, lang=lang)
    ai_impact = _build_ai_impact(current, projected, lang=lang)
    if lang == "zh":
        lines = [
            f"    Build 前后: {before.stage.badge} {before.stage_name} -> {after.stage.badge} {after.stage_name}",
            f"    数值变化: {stats}",
            f"    标签变化: {tag_delta}",
        ]
        advice = _build_pick_advice(after.best_next_picks, stage=after.stage, lang=lang)
    else:
        lines = [
            f"    Build before/after: {before.stage.badge} {before.stage_name} -> {after.stage.badge} {after.stage_name}",
            f"    Stat delta: {stats}",
            f"    Tag delta: {tag_delta}",
        ]
        advice = _build_pick_advice(after.best_next_picks, stage=after.stage, lang=lang)
    if cross_note:
        lines.append(f"    {cross_note}")
    if ai_impact:
        lines.append(f"    {ai_impact}")
    if advice:
        lines.append(f"    {advice}")
    return lines


def _stat_delta_summary(current: ResolvedBuild, projected: ResolvedBuild) -> str:
    pairs = [
        ("HP", projected.hp - current.hp),
        ("MP", projected.mp - current.mp),
        ("SPD", projected.speed - current.speed),
        ("ATK", projected.attack - current.attack),
        ("DEF", projected.defense - current.defense),
        ("POW", projected.power - current.power),
    ]
    changes = [f"{name}{value:+d}" for name, value in pairs if value]
    return ", ".join(changes) if changes else "no direct stat change"


def _tag_delta_summary(current: ResolvedBuild, projected: ResolvedBuild) -> str:
    before = current.tag_counts()
    after = projected.tag_counts()
    gained = [
        f"{tag} {before.get(tag, 0)}->{after[tag]}"
        for tag in sorted(after)
        if after[tag] > before.get(tag, 0)
    ]
    return ", ".join(gained[:6]) if gained else "no new tags"


def _cross_build_seed_note(
    hero_id: str,
    current: ResolvedBuild,
    projected: ResolvedBuild,
    *,
    lang: str,
) -> str:
    before = current.tag_counts()
    after = projected.tag_counts()
    gained = {tag for tag, count in after.items() if count > before.get(tag, 0)}
    if not gained:
        return ""
    core = set(HERO_CORE_TAGS.get(hero_id, ()))
    off_core = sorted(tag for tag in gained if tag not in core)
    if not off_core or len(off_core) < len(gained):
        return ""
    tags = ", ".join(off_core[:4])
    if lang == "zh":
        return f"跨 Build 种子: {tags} 不属于当前核心标签；除非想转向，否则优先级较低。"
    return f"Cross-build seed: {tags} sits outside this hero core; take mainly for a pivot."


def _build_ai_impact(current: ResolvedBuild, projected: ResolvedBuild, *, lang: str) -> str:
    before = current.tag_counts()
    after = projected.tag_counts()
    gained_tags = {tag for tag, count in after.items() if count > before.get(tag, 0)}
    stat_gain = {
        "hp": projected.hp - current.hp,
        "mp": projected.mp - current.mp,
        "speed": projected.speed - current.speed,
        "attack": projected.attack - current.attack,
        "defense": projected.defense - current.defense,
        "power": projected.power - current.power,
    }
    if gained_tags & {"control", "silence", "codex"}:
        return (
            "AI impact: reinforces interrupt and caster-control priority"
            if lang == "en"
            else "AI 影响: 强化打断和施法者控制优先级"
        )
    if gained_tags & {"guard", "armor", "shield"} or stat_gain["hp"] > 0 or stat_gain["defense"] > 0:
        return (
            "AI impact: raises survival value before risky fights"
            if lang == "en"
            else "AI 影响: 提高高风险战前的生存权重"
        )
    if gained_tags & {"poison", "omen"}:
        return (
            "AI impact: leans toward attrition and delayed payoff"
            if lang == "en"
            else "AI 影响: 更偏向消耗和延迟收益"
        )
    if gained_tags & {"bleed", "hunter", "execute", "speed"} or stat_gain["speed"] > 0:
        return (
            "AI impact: improves kill-line and execute timing"
            if lang == "en"
            else "AI 影响: 改善击杀线和处决时机"
        )
    if gained_tags & {"gear", "trap", "retribution"} or stat_gain["attack"] > 0:
        return (
            "AI impact: supports setup turns and counter pressure"
            if lang == "en"
            else "AI 影响: 支持铺设回合和反击压力"
        )
    if gained_tags & {"echo", "holy", "cleanse"}:
        return (
            "AI impact: favors cleanse, ward, and echo timing"
            if lang == "en"
            else "AI 影响: 更重视净化、护壁和回声时机"
        )
    if stat_gain["mp"] > 0 or stat_gain["power"] > 0 or gained_tags & {"shadow", "corruption"}:
        return (
            "AI impact: improves MP-to-pressure spell turns"
            if lang == "en"
            else "AI 影响: 强化用 MP 换压力的施法回合"
        )
    return (
        "AI impact: flexible pick; choose for economy or future pivots"
        if lang == "en"
        else "AI 影响: 弹性选择，偏经济或后续转向"
    )


def _build_pick_advice(picks, *, stage: BuildStage, lang: str) -> str:
    if not picks:
        return "建议: 当前选择偏泛用，按生存/经济需求判断" if lang == "zh" else "Advice: flexible pick; choose for survival or economy"
    first = picks[0]
    tag = first.get("tag", "-")
    need = first.get("need", 1)
    next_stage = {
        BuildStage.SEED: "PAIR",
        BuildStage.PAIR: "ONLINE",
        BuildStage.ONLINE: "HIGH ROLL",
        BuildStage.HIGH_ROLL: "LOCKED IN",
        BuildStage.LOCKED_IN: "PERFECT",
    }.get(stage, "NEXT")
    if lang == "zh":
        return f"建议: 下一步找 {tag} +{need} 推进 {next_stage}"
    return f"Advice: next seek {tag} +{need} to push {next_stage}"


def _choice_decision_note(choice_type: str, lang: str) -> str:
    notes = {
        "gold": {
            "en": "    Decision: take gold when shop access or future flexibility matters.",
            "zh": "    决策: 如果后续有商店或需要弹性，金币优先级上升。",
        },
        "heal": {
            "en": "    Decision: take healing when next route has elite, boss, or chant pressure.",
            "zh": "    决策: 下一路有精英、Boss 或吟唱压力时，治疗价值更高。",
        },
        "strategy": {
            "en": "    Decision: changes model bias; useful when battle diagnosis exposed repeated mistakes.",
            "zh": "    决策: 调整模型偏好；当战报暴露重复失误时更有价值。",
        },
        "scout": {
            "en": "    Decision: buy information before elite, boss, or unfamiliar route pressure.",
            "zh": "    决策: 精英、Boss 或陌生路线前，情报可降低失误。",
        },
    }
    return notes.get(choice_type, {}).get(lang, "")


def _rest_decision_preview(
    state,
    *,
    heal_percent: int,
    restore_full_mp: bool,
    lang: str,
) -> list[str]:
    heal_amount = int(state.max_hp * heal_percent / 100) if heal_percent > 0 else 0
    new_hp = min(state.max_hp, state.current_hp + heal_amount)
    new_mp = state.max_mp if restore_full_mp else state.current_mp
    hp_gain = new_hp - state.current_hp
    mp_gain = new_mp - state.current_mp
    hp_ratio = state.current_hp / max(1, state.max_hp)
    if lang == "zh":
        urgency = "高" if hp_ratio <= 0.4 or state.current_mp <= 1 else "中" if hp_ratio <= 0.7 or mp_gain else "低"
        return [
            f"休整预览: HP +{hp_gain}, MP +{mp_gain}",
            f"决策压力: {urgency}；低血线或缺 MP 时优先确认，否则可保留路线节奏。",
        ]
    urgency = "high" if hp_ratio <= 0.4 or state.current_mp <= 1 else "medium" if hp_ratio <= 0.7 or mp_gain else "low"
    return [
        f"Rest preview: HP +{hp_gain}, MP +{mp_gain}",
        f"Decision pressure: {urgency}; confirm when HP/MP is unsafe, skip when tempo matters.",
    ]


def _render_rest_decision_ring(
    state,
    *,
    heal_percent: int,
    restore_full_mp: bool,
    lang: str,
    width: int,
) -> list[str]:
    title = "REST DECISION RING" if lang == "en" else "休整决策环"
    heal_amount = int(state.max_hp * heal_percent / 100) if heal_percent > 0 else 0
    recover_hp = min(state.max_hp, state.current_hp + heal_amount)
    recover_mp = state.max_mp if restore_full_mp else state.current_mp
    if lang == "zh":
        body = [
            "[1] RECOVER => HP/MP 修复 | 稳住本局",
            f"    HP {state.current_hp}->{recover_hp} / MP {state.current_mp}->{recover_mp}",
            "[2] FOCUS   => SHD 12 下一战开局 | 抗压反制",
            "[3] STUDY   => 机制侦察笔记 | 降低未知风险",
        ]
    else:
        body = [
            "[1] RECOVER => HP/MP repair | stabilize the run",
            f"    HP {state.current_hp}->{recover_hp} / MP {state.current_mp}->{recover_mp}",
            "[2] FOCUS   => SHD 12 next battle | absorb pressure",
            "[3] STUDY   => scout note | reduce unknown risk",
        ]
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="counter").lines)


def _choice_card(title: str, body: list[str], *, width: int, tone: str = "normal") -> list[str]:
    card_width = max(36, width)
    inner = max(12, card_width - 4)
    art_lines = _choice_card_art(title, body, tone=tone)
    fitted_body = [fit_text(line.strip(), inner) for line in [*art_lines, *body]]
    return list(pixel_panel(title, fitted_body, card_width, tone=tone).lines)


def _choice_card_art(title: str, body: list[str], *, tone: str) -> list[str]:
    haystack = " ".join([title, *body]).upper()
    title_upper = title.upper()
    if "SHOP" in haystack:
        return ["[SHOP]  ##[]##  price / repair / scout", "        #____#"]
    if any(token in haystack for token in ("COST:", "BUILD FIT:", "ENEMIES:", "SCOUT:", "OMEN:")):
        if "BOSS" in haystack:
            return ["[PATH]  ######  danger route", "        ##XX##"]
        if tone == "danger" or "ELITE" in haystack or "DANGER" in haystack:
            return ["[PATH]  ##!!##  high risk", "        #====#"]
        return ["[PATH]  ##==>##  route", "        #....#"]
    if (
        any(token in title_upper for token in ("ITEM", "AFFIX", "CODEX", "GOLD", "HEAL", "REWARD"))
        or any(line.upper().startswith(("ITEM:", "AFFIX:", "GOLD:", "HEAL:")) for line in body)
    ):
        return ["[REWARD] [SEED] -> [PAIR] -> [ONLINE]", "          ##==*"]
    if "RECOVER" in haystack or "FOCUS" in haystack or "STUDY" in haystack or "REST" in haystack:
        return ["[REST]  ##+##  recover / focus / study", "        #___#"]
    if tone == "hero":
        return ["[HERO]  ##@##  prompt / build / risk", "        #====#"]
    if "BOSS" in haystack:
        return ["[PATH]  ######  danger route", "        ##XX##"]
    if tone == "danger" or "ELITE" in haystack or "DANGER" in haystack:
        return ["[PATH]  ##!!##  high risk", "        #====#"]
    return ["[PATH]  ##==>##  route", "        #....#"]


def _render_route_map(
    state,
    bundle: ContentBundle,
    available: list[tuple[int, object]],
    *,
    lang: str,
    width: int,
) -> list[str]:
    floor = state.current_floor(bundle)
    display_by_index = {node_idx: display_idx for display_idx, (node_idx, _node) in enumerate(available, start=1)}
    title = "ROUTE MAP" if lang == "en" else "路线地图"
    start = "START" if lang == "en" else "起点"
    legend = (
        "Legend: C combat, E elite, B boss, $ shop, + rest, ? event, X visited"
        if lang == "en"
        else "图例: C 战斗, E 精英, B Boss, $ 商店, + 休整, ? 事件, X 已完成"
    )
    body = [f"{start} o", legend]
    for node_idx, node_id in enumerate(floor.nodes):
        node = bundle.nodes[node_id]
        display_idx = display_by_index.get(node_idx)
        connector = "+-->" if node_idx == 0 else "|-->"
        token = _route_map_token(node, display_idx, visited=node.id in state.visited_node_ids)
        name = node.display_name.get(lang) or node.display_name.get("en", node.id)
        risk = _route_map_risk_badge(node.risk_level, node.node_type, lang=lang)
        body.append(f"{connector} {token} {name} {risk}".rstrip())
    body.append(_route_map_pressure_line(state, available, lang=lang))
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="quiet").lines)


def _route_map_token(node, display_idx: int | None, *, visited: bool) -> str:
    icon = {
        "normal_combat": "C",
        "elite_combat": "E",
        "boss": "B",
        "mimic_chest": "M",
        "shop": "$",
        "rest": "+",
        "event": "?",
    }.get(node.node_type, "?")
    slot = "X" if visited else str(display_idx) if display_idx is not None else "-"
    return f"[{slot}:{icon}]"


def _route_map_risk_badge(risk_level: str | None, node_type: str, *, lang: str) -> str:
    risk = risk_level or ("high" if node_type == "boss" else "medium")
    if node_type in {"shop", "rest", "event"} and risk_level in {None, "safe"}:
        risk = "safe"
    if lang == "zh":
        labels = {"safe": "+安全", "low": "+低压", "medium": "!中压", "high": "!!高压"}
    else:
        labels = {"safe": "+safe", "low": "+low", "medium": "!medium", "high": "!!high"}
    return labels.get(risk, f"!{risk}")


def _route_map_pressure_line(state, available: list[tuple[int, object]], *, lang: str) -> str:
    hp_ratio = state.current_hp / max(1, state.max_hp)
    mp_ratio = state.current_mp / max(1, state.max_mp)
    branch_count = len(available)
    if lang == "zh":
        pressure = "高" if hp_ratio <= 0.4 or mp_ratio <= 0.25 else "中" if branch_count >= 3 else "低"
        return f"路线压力: {branch_count} 个选择 / 本局压力 {pressure}"
    pressure = "high" if hp_ratio <= 0.4 or mp_ratio <= 0.25 else "medium" if branch_count >= 3 else "low"
    return f"Branch pressure: {branch_count} choices / run pressure {pressure}"


def _render_reward_build_track(
    state,
    bundle: ContentBundle,
    choices,
    *,
    lang: str,
    width: int,
) -> list[str]:
    title = "REWARD BUILD TRACK" if lang == "en" else "奖励 Build 轨道"
    current = state.resolved_build(bundle)
    current_progress = current.calculate_progress(bundle)
    body = [
        (
            f"Current: {current_progress.stage.badge} {current_progress.stage_name}"
            if lang == "en"
            else f"当前: {current_progress.stage.badge} {current_progress.stage_name}"
        )
    ]
    for idx, choice in enumerate(choices, start=1):
        body.append(_reward_track_line(state, bundle, choice, idx=idx, lang=lang))
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="hero").lines)


def _reward_track_line(state, bundle: ContentBundle, choice, *, idx: int, lang: str) -> str:
    current = state.resolved_build(bundle)
    if choice.type in {"item", "affix"}:
        item_ids = list(getattr(state, "item_ids", ()))
        affix_ids = list(getattr(state, "affix_ids", ()))
        if choice.type == "item" and choice.item_id:
            item_ids.append(choice.item_id)
        if choice.type == "affix" and choice.affix_id:
            affix_ids.append(choice.affix_id)
        projected = resolve_build(
            bundle.get_hero(state.hero_id),
            bundle,
            item_ids=tuple(item_ids),
            affix_ids=tuple(affix_ids),
        )
        before = current.calculate_progress(bundle)
        after = projected.calculate_progress(bundle)
        tag_delta = _tag_delta_summary(current, projected)
        arrow = "=>"
        if lang == "zh":
            return f"[{idx}] {before.stage.badge} {arrow} {after.stage.badge} | 标签 {tag_delta}"
        return f"[{idx}] {before.stage.badge} {arrow} {after.stage.badge} | tags {tag_delta}"
    if choice.type == "codex":
        amount = choice.progress or 1
        return f"[{idx}] [CODEX] => [+{amount} STUDY] | prompt intel"
    if choice.type == "gold" and choice.gold:
        return f"[{idx}] [GOLD] => +{choice.gold} | shop route power"
    if choice.type == "heal" and choice.heal_percent:
        return f"[{idx}] [HEAL] => +{choice.heal_percent}% HP | survival line"
    return f"[{idx}] [FLEX] => future pivot"


def _render_shop_fix_board(
    state,
    bundle: ContentBundle,
    items,
    *,
    lang: str,
    width: int,
) -> list[str]:
    title = "SHOP FIX BOARD" if lang == "en" else "商店修正面板"
    body = [
        (
            "Lanes: RECOVER / BUILD / PROMPT / SCOUT"
            if lang == "en"
            else "货架: 恢复 / Build / Prompt / 侦察"
        )
    ]
    for idx, item in enumerate(items, start=1):
        body.append(_shop_fix_line(state, bundle, item, idx=idx, lang=lang))
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="quiet").lines)


def _shop_fix_line(state, bundle: ContentBundle, item, *, idx: int, lang: str) -> str:
    price = item.price or 0
    afford = "READY" if state.can_afford(item) else "LOCKED"
    prefix = f"[{idx}] {_shop_lane_label(item.type)} {price}g {afford} => "
    if item.type == "heal":
        bits = []
        if item.heal_percent:
            bits.append(f"HP +{item.heal_percent}%")
        if getattr(item, "restore_mp", False):
            bits.append("MP full")
        return prefix + (", ".join(bits) if bits else "survival repair")
    if item.type in {"item", "affix"}:
        current = state.resolved_build(bundle)
        item_ids = list(getattr(state, "item_ids", ()))
        affix_ids = list(getattr(state, "affix_ids", ()))
        if item.type == "item" and item.item_id:
            item_ids.append(item.item_id)
        if item.type == "affix" and item.affix_id:
            affix_ids.append(item.affix_id)
        projected = resolve_build(
            bundle.get_hero(state.hero_id),
            bundle,
            item_ids=tuple(item_ids),
            affix_ids=tuple(affix_ids),
        )
        tag_delta = _tag_delta_summary(current, projected)
        return prefix + f"Build tags {tag_delta}"
    if item.type == "strategy":
        style = item.strategy_style or "flex"
        return prefix + f"Prompt style {style}"
    if item.type == "scout":
        return prefix + "Boss clue / route intel"
    return prefix + "future pivot"


def _shop_lane_label(item_type: str) -> str:
    if item_type == "heal":
        return "RECOVER"
    if item_type in {"item", "affix"}:
        return "BUILD"
    if item_type == "strategy":
        return "PROMPT"
    if item_type == "scout":
        return "SCOUT"
    return "FLEX"


def render_route_choice(
    state,
    bundle: ContentBundle,
    *,
    language: str = DEFAULT_LANGUAGE,
    width: int = 100,
) -> str:
    """Render the route choice screen.

    Args:
        state: RunState instance
        bundle: ContentBundle
        language: Language code
        width: Terminal width

    Returns:
        Rendered screen as string
    """
    lang = language
    dungeon = state.current_dungeon(bundle)
    floor = state.current_floor(bundle)
    available = state.get_available_nodes(bundle)

    lines: list[str] = []

    # Header
    lines.append(label("route_choice_title", lang))
    lines.append("")
    lines.append(
        f"{label('run_dungeon', lang)}: {dungeon.display_name.get(lang)}  "
        f"{label('run_floor', lang)}: {floor.floor_number}"
    )
    lines.append(
        f"{label('run_gold', lang)}: {state.gold}  "
        f"{label('run_xp', lang)}: {state.xp}  "
        f"HP: {state.current_hp}/{state.max_hp}  "
        f"MP: {state.current_mp}/{state.max_mp}"
    )
    if getattr(state, "strategy_style", None):
        style_label = "Prompt style" if lang == "en" else "Prompt 预设"
        lines.append(f"{style_label}: {state.strategy_style}")
    if getattr(state, "scout_notes", None):
        scout_label = "Scout note" if lang == "en" else "侦察笔记"
        for note in state.scout_notes[-2:]:
            lines.append(f"{scout_label}: {fit_text(note, max(20, width - 14))}")
    lines.append("")
    lines.extend(_render_route_map(state, bundle, available, lang=lang, width=width))
    lines.append("")
    lines.extend(_render_route_director_board(state, bundle, available, lang=lang, width=width))
    lines.append("")
    for wrapped in _wrap_text(label("route_choice_note", lang), max(30, width)):
        lines.append(wrapped)
    lines.append("")

    # Available nodes
    for display_idx, (node_idx, node) in enumerate(available, start=1):
        name = node.display_name.get(lang) or node.display_name.get("en", node.id)
        node_type = _node_type_label(node.node_type, lang)
        risk = _risk_level_label(node.risk_level, lang)
        card_body: list[str] = [node_type]

        desc = node.description.get(lang)
        if desc:
            for wrapped in _wrap_text(desc, 76)[:2]:
                card_body.append(wrapped)
        story_intro = node.boss_intro.get(lang) if getattr(node, "is_boss", False) else node.encounter_intro.get(lang)
        if story_intro:
            story_label = "Boss omen" if getattr(node, "is_boss", False) and lang == "en" else (
                "Boss 预兆" if getattr(node, "is_boss", False) else ("Omen" if lang == "en" else "预兆")
            )
            for wrapped in _wrap_text(story_intro, max(24, width - 4))[:2]:
                card_body.append(f"{story_label}: {wrapped}")
        if risk:
            card_body.append(risk)
        card_body.append(_route_cost_preview(state, node, bundle, lang=lang))
        for wrapped in _wrap_text(
            _route_reward_preview(node, bundle, lang=lang),
            max(24, width - 4),
        ):
            card_body.append(wrapped)
        card_body.append(_route_build_fit(state, node, bundle, lang=lang))
        recommendation = _route_recommendation(state, node, bundle, lang=lang)
        if recommendation:
            card_body.append(recommendation)
        route_hint = _route_decision_hint(node, bundle, lang=lang)
        if route_hint:
            for wrapped in _wrap_text(route_hint, max(24, width - 4)):
                card_body.append(wrapped)

        # Show enemies for combat nodes
        if node.node_type in ("normal_combat", "elite_combat", "boss", "mimic_chest"):
            if node.enemy_ids:
                enemy_names = []
                for eid in node.enemy_ids:
                    if eid in bundle.enemies:
                        enemy = bundle.enemies[eid]
                        enemy_name = enemy.display_name.get(lang) or enemy.display_name.get("en", eid)
                        enemy_names.append(f"[{enemy.short_glyph}] {enemy_name} / {enemy.tier}")
                    else:
                        enemy_names.append(eid)
                enemy_word = "Enemies" if lang == "en" else "敌人"
                scout_word = "Scout" if lang == "en" else "侦察"
                card_body.append(f"{enemy_word}: {', '.join(enemy_names)}")
                if node.enemy_ids[0] in bundle.enemies:
                    preview = bundle.enemies[node.enemy_ids[0]].codex_stage_unknown.get(lang)
                    if preview:
                        for wrapped in _wrap_text(preview, 76)[:1]:
                            card_body.append(f"{scout_word}: {wrapped}")

        tone = "danger" if node.node_type in {"elite_combat", "boss"} else "normal"
        lines.extend(_choice_card(f"[{display_idx}] {name}", card_body, width=width, tone=tone))
        lines.append("")

    # Prompt
    lines.append(label("route_choice_prompt", lang))

    return "\n".join(_wrap_screen_lines(lines, width))


def _render_route_director_board(
    state,
    bundle: ContentBundle,
    available: list[tuple[int, object]],
    *,
    lang: str,
    width: int,
) -> list[str]:
    title = "ROUTE DIRECTOR BOARD" if lang == "en" else "路线导演板"
    body = [
        (
            "Read: TAKE clean route / FIX repair node / GREED pressure for reward / RISK needs prep"
            if lang == "en"
            else "读法: TAKE 稳定路线 / FIX 修复节点 / GREED 高压高收益 / RISK 需准备"
        )
    ]
    for display_idx, (_node_idx, node) in enumerate(available, start=1):
        body.append(_route_director_line(state, node, bundle, idx=display_idx, lang=lang))
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="counter").lines)


def _route_director_line(state, node, bundle: ContentBundle, *, idx: int, lang: str) -> str:
    recommendation = _route_recommendation(state, node, bundle, lang=lang)
    if "[DANGER]" in recommendation or "[危险]" in recommendation or "[RISK]" in recommendation or "[风险]" in recommendation:
        verdict = "RISK"
    elif "[GREED]" in recommendation or "[贪心]" in recommendation:
        verdict = "GREED"
    elif node.node_type in {"shop", "rest"}:
        verdict = "FIX"
    elif "[FLEX]" in recommendation or "[弹性]" in recommendation:
        verdict = "FLEX"
    elif "[LOW VALUE]" in recommendation or "[低收益]" in recommendation or "[SKIP?]" in recommendation or "[可跳过]" in recommendation:
        verdict = "WAIT"
    else:
        verdict = "TAKE"
    node_name = node.display_name.get(lang) or node.display_name.get("en", node.id)
    risk = _route_map_risk_badge(node.risk_level, node.node_type, lang=lang)
    summary = recommendation
    for token in ("[REC] ", "[DANGER] ", "[GREED] ", "[RISK] ", "[FLEX] ", "[LOW VALUE] ", "[SKIP?] "):
        summary = summary.replace(token, "")
    for token in ("[推荐] ", "[危险] ", "[贪心] ", "[风险] ", "[弹性] ", "[低收益] ", "[可跳过] "):
        summary = summary.replace(token, "")
    if lang == "zh":
        return f"[{idx}] {verdict:<5} {risk} | {node_name} | {summary}"
    return f"[{idx}] {verdict:<5} {risk} | {node_name} | {summary}"


def render_reward_choice(
    state,
    bundle: ContentBundle,
    *,
    language: str = DEFAULT_LANGUAGE,
    width: int = 100,
) -> str:
    """Render the reward choice screen.

    Args:
        state: RunState instance
        bundle: ContentBundle
        language: Language code
        width: Terminal width

    Returns:
        Rendered screen as string
    """
    lang = language
    node = state.current_node(bundle)
    choices = state.current_choices

    lines: list[str] = []

    # Header
    lines.append(label("reward_choice_title", lang))
    lines.append("")

    # Show what we earned
    if node.rewards:
        if node.rewards.gold:
            lines.append(f"+{node.rewards.gold} {label('run_gold', lang)}")
        if node.rewards.xp:
            lines.append(f"+{node.rewards.xp} {label('run_xp', lang)}")
        lines.append("")

    # Current stats
    lines.append(
        f"{label('run_gold', lang)}: {state.gold}  "
        f"{label('run_xp', lang)}: {state.xp}  "
        f"HP: {state.current_hp}/{state.max_hp}  "
        f"MP: {state.current_mp}/{state.max_mp}"
    )
    lines.append(label("reward_choice_note", lang))
    lines.append("")
    lines.extend(_render_reward_build_track(state, bundle, choices, lang=lang, width=width))
    lines.append("")
    lines.extend(_render_reward_priority_board(state, bundle, choices, lang=lang, width=width))
    lines.append("")

    # Reward choices
    for idx, choice in enumerate(choices, start=1):
        choice_type = choice.type
        type_label = {
            "item": label("reward_type_item", lang),
            "affix": label("reward_type_affix", lang),
            "codex": label("reward_type_codex", lang),
            "gold": label("reward_type_gold", lang),
            "heal": label("reward_type_heal", lang),
        }.get(choice_type, choice_type)
        card_body: list[str] = []

        if choice_type == "item" and choice.item_id:
            if choice.item_id in bundle.items:
                item = bundle.items[choice.item_id]
                name = item.display_name.get(lang) or item.display_name.get("en", choice.item_id)
                card_body.append(f"{name} [{item.tier}]")
                desc = item.description.get(lang) or item.description.get("en", "")
                if desc:
                    card_body.append(desc)
                if item.stat_mods:
                    mods = []
                    if item.stat_mods.hp:
                        mods.append(f"HP+{item.stat_mods.hp}")
                    if item.stat_mods.mp:
                        mods.append(f"MP+{item.stat_mods.mp}")
                    if item.stat_mods.speed:
                        mods.append(f"SPD+{item.stat_mods.speed}")
                    if item.stat_mods.attack:
                        mods.append(f"ATK+{item.stat_mods.attack}")
                    if item.stat_mods.defense:
                        mods.append(f"DEF+{item.stat_mods.defense}")
                    if item.stat_mods.power:
                        mods.append(f"POW+{item.stat_mods.power}")
                    if mods:
                        card_body.append(f"Impact: {', '.join(mods)}")
                if item.tags:
                    card_body.append(f"Build tags: {', '.join(item.tags[:4])}")
                card_body.extend(_choice_build_preview(state, bundle, item_id=choice.item_id, lang=lang))
            else:
                card_body.append(choice.item_id)

        elif choice_type == "affix" and choice.affix_id:
            if choice.affix_id in bundle.affixes:
                affix = bundle.affixes[choice.affix_id]
                name = affix.display_name.get(lang) or affix.display_name.get("en", choice.affix_id)
                card_body.append(name)
                desc = affix.description.get(lang) or affix.description.get("en", "")
                if desc:
                    card_body.append(desc)
                if affix.stat_mods:
                    mods = []
                    if affix.stat_mods.hp:
                        mods.append(f"HP+{affix.stat_mods.hp}")
                    if affix.stat_mods.mp:
                        mods.append(f"MP+{affix.stat_mods.mp}")
                    if affix.stat_mods.speed:
                        mods.append(f"SPD+{affix.stat_mods.speed}")
                    if affix.stat_mods.attack:
                        mods.append(f"ATK+{affix.stat_mods.attack}")
                    if affix.stat_mods.defense:
                        mods.append(f"DEF+{affix.stat_mods.defense}")
                    if affix.stat_mods.power:
                        mods.append(f"POW+{affix.stat_mods.power}")
                    if mods:
                        card_body.append(f"Impact: {', '.join(mods)}")
                if affix.tags:
                    card_body.append(f"Build tags: {', '.join(affix.tags[:4])}")
                card_body.extend(_choice_build_preview(state, bundle, affix_id=choice.affix_id, lang=lang))
            else:
                card_body.append(choice.affix_id)

        elif choice_type == "codex":
            card_body.append(label("reward_codex_progress", lang).format(amount=choice.progress or 1))

        elif choice_type == "gold" and choice.gold:
            card_body.append(f"+{choice.gold}{label('reward_gold_suffix', lang)}")
            card_body.append(_choice_decision_note("gold", lang))

        elif choice_type == "heal" and choice.heal_percent:
            card_body.append(label("reward_heal_percent", lang).format(percent=choice.heal_percent))
            card_body.append(_choice_decision_note("heal", lang))

        lines.extend(_choice_card(f"[{idx}] {type_label}", card_body, width=width, tone="hero"))
        lines.append("")

    # Prompt
    lines.append(label("reward_choice_prompt", lang))

    return "\n".join(_wrap_screen_lines(lines, width))


def _render_reward_priority_board(
    state,
    bundle: ContentBundle,
    choices,
    *,
    lang: str,
    width: int,
) -> list[str]:
    title = "PICK PRIORITY BOARD" if lang == "en" else "选择优先级面板"
    body = [
        (
            "Read: BEST stage push / CORE main tags / PIVOT off-core / INFO economy"
            if lang == "en"
            else "读法: BEST 推阶段 / CORE 主标签 / PIVOT 转向 / INFO 经济情报"
        )
    ]
    for idx, choice in enumerate(choices, start=1):
        body.append(_reward_priority_line(state, bundle, choice, idx=idx, lang=lang))
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="counter").lines)


def _reward_priority_line(state, bundle: ContentBundle, choice, *, idx: int, lang: str) -> str:
    if choice.type in {"item", "affix"}:
        current = state.resolved_build(bundle)
        item_ids = list(getattr(state, "item_ids", ()))
        affix_ids = list(getattr(state, "affix_ids", ()))
        if choice.type == "item" and choice.item_id:
            item_ids.append(choice.item_id)
        if choice.type == "affix" and choice.affix_id:
            affix_ids.append(choice.affix_id)
        projected = resolve_build(
            bundle.get_hero(state.hero_id),
            bundle,
            item_ids=tuple(item_ids),
            affix_ids=tuple(affix_ids),
        )
        return _build_priority_line(state.hero_id, current, projected, bundle, idx=idx, lang=lang)
    if choice.type == "codex":
        return (
            f"[{idx}] INFO   => prompt intel +{choice.progress or 1}; take before unknown/boss routes"
            if lang == "en"
            else f"[{idx}] INFO   => 提示词情报 +{choice.progress or 1}；未知/Boss 前优先"
        )
    if choice.type == "gold":
        amount = choice.gold or 0
        return (
            f"[{idx}] ECON   => +{amount}g; buy shop fixes or future pivots"
            if lang == "en"
            else f"[{idx}] ECON   => +{amount} 金；购买商店修正或后续转向"
        )
    if choice.type == "heal":
        amount = choice.heal_percent or 0
        return (
            f"[{idx}] SAFE   => +{amount}% HP; take if next route is elite/boss/chant"
            if lang == "en"
            else f"[{idx}] SAFE   => +{amount}% HP；下一路精英/Boss/吟唱时优先"
        )
    return f"[{idx}] FLEX   => future pivot"


def _build_priority_line(
    hero_id: str,
    current: ResolvedBuild,
    projected: ResolvedBuild,
    bundle: ContentBundle,
    *,
    idx: int,
    lang: str,
) -> str:
    before_tags = current.tag_counts()
    after_tags = projected.tag_counts()
    gained = sorted(tag for tag, count in after_tags.items() if count > before_tags.get(tag, 0))
    core = set(HERO_CORE_TAGS.get(hero_id, ()))
    core_gain = [tag for tag in gained if tag in core]
    off_core = [tag for tag in gained if tag not in core]
    stage_order = {
        BuildStage.SEED: 0,
        BuildStage.PAIR: 1,
        BuildStage.ONLINE: 2,
        BuildStage.HIGH_ROLL: 3,
        BuildStage.LOCKED_IN: 4,
    }
    before_stage = current.calculate_progress(bundle).stage
    after_stage = projected.calculate_progress(bundle).stage
    tag_text = ", ".join((core_gain or gained or off_core)[:3]) or "stats"
    if stage_order[after_stage] > stage_order[before_stage]:
        label_text = "BEST"
        reason = (
            f"{before_stage.badge}->{after_stage.badge} stage push"
            if lang == "en"
            else f"{before_stage.badge}->{after_stage.badge} 阶段推进"
        )
    elif core_gain:
        label_text = "CORE"
        reason = f"main tags {tag_text}" if lang == "en" else f"主标签 {tag_text}"
    elif off_core and not core_gain:
        label_text = "PIVOT"
        reason = f"off-core tags {tag_text}" if lang == "en" else f"非核心标签 {tag_text}"
    else:
        label_text = "FLEX"
        reason = "stats/economy fit" if lang == "en" else "数值/经济补强"
    before_stats = current.hp + current.mp + current.attack + current.defense + current.power + current.speed
    after_stats = projected.hp + projected.mp + projected.attack + projected.defense + projected.power + projected.speed
    if after_stats > before_stats + 10 and label_text == "FLEX":
        label_text = "BEST"
        reason = "large stat push" if lang == "en" else "大幅数值推进"
    if lang == "zh":
        return f"[{idx}] {label_text:<5} => {reason} | AI 会更重视对应回合"
    return f"[{idx}] {label_text:<5} => {reason} | AI weights matching turns higher"


def render_shop(
    state,
    bundle: ContentBundle,
    *,
    language: str = DEFAULT_LANGUAGE,
    width: int = 100,
) -> str:
    """Render the shop screen.

    Args:
        state: RunState instance
        bundle: ContentBundle
        language: Language code
        width: Terminal width

    Returns:
        Rendered screen as string
    """
    lang = language
    node = state.current_node(bundle)
    items = state.current_choices

    lines: list[str] = []

    # Header
    lines.append(label("shop_title", lang))
    lines.append("")

    # Shopkeeper name and description
    shop_name = node.display_name.get(lang) or node.display_name.get("en", "Shop")
    lines.append(shop_name)
    desc = node.description.get(lang) or node.description.get("en", "")
    if desc:
        lines.append(desc)
    lines.append("")

    # Current gold
    lines.append(f"{label('run_gold', lang)}: {state.gold}")
    lines.append(label("shop_note", lang))
    lines.append("")
    lines.extend(_render_shop_fix_board(state, bundle, items, lang=lang, width=width))
    lines.append("")
    lines.extend(_render_shop_budget_board(state, items, lang=lang, width=width))
    lines.append("")

    # Shop items
    for idx, item in enumerate(items, start=1):
        item_type = item.type
        can_afford = state.can_afford(item)
        price = item.price or 0

        afford = label("shop_cannot_afford", lang) if not can_afford else label("shop_ready", lang)
        card_body: list[str] = [f"{price}{label('reward_gold_suffix', lang)}  {afford}"]

        if item_type == "item" and item.item_id:
            if item.item_id in bundle.items:
                bundle_item = bundle.items[item.item_id]
                name = bundle_item.display_name.get(lang) or bundle_item.display_name.get("en", item.item_id)
                card_body.append(f"{name} [{bundle_item.tier}]")
                desc = bundle_item.description.get(lang) or bundle_item.description.get("en", "")
                if desc:
                    card_body.append(desc)
                if bundle_item.stat_mods:
                    mods = []
                    if bundle_item.stat_mods.hp:
                        mods.append(f"HP+{bundle_item.stat_mods.hp}")
                    if bundle_item.stat_mods.mp:
                        mods.append(f"MP+{bundle_item.stat_mods.mp}")
                    if bundle_item.stat_mods.speed:
                        mods.append(f"SPD+{bundle_item.stat_mods.speed}")
                    if bundle_item.stat_mods.attack:
                        mods.append(f"ATK+{bundle_item.stat_mods.attack}")
                    if bundle_item.stat_mods.defense:
                        mods.append(f"DEF+{bundle_item.stat_mods.defense}")
                    if bundle_item.stat_mods.power:
                        mods.append(f"POW+{bundle_item.stat_mods.power}")
                    if mods:
                        card_body.append(f"Impact: {', '.join(mods)}")
                if bundle_item.tags:
                    card_body.append(f"Build tags: {', '.join(bundle_item.tags[:4])}")
                card_body.extend(_choice_build_preview(state, bundle, item_id=item.item_id, lang=lang))
            else:
                card_body.append(item.item_id)

        elif item_type == "affix" and item.affix_id:
            if item.affix_id in bundle.affixes:
                affix = bundle.affixes[item.affix_id]
                name = affix.display_name.get(lang) or affix.display_name.get("en", item.affix_id)
                card_body.append(name)
                desc = affix.description.get(lang) or affix.description.get("en", "")
                if desc:
                    card_body.append(desc)
                if affix.stat_mods:
                    mods = []
                    if affix.stat_mods.hp:
                        mods.append(f"HP+{affix.stat_mods.hp}")
                    if affix.stat_mods.mp:
                        mods.append(f"MP+{affix.stat_mods.mp}")
                    if affix.stat_mods.speed:
                        mods.append(f"SPD+{affix.stat_mods.speed}")
                    if affix.stat_mods.attack:
                        mods.append(f"ATK+{affix.stat_mods.attack}")
                    if affix.stat_mods.defense:
                        mods.append(f"DEF+{affix.stat_mods.defense}")
                    if affix.stat_mods.power:
                        mods.append(f"POW+{affix.stat_mods.power}")
                    if mods:
                        card_body.append(f"Impact: {', '.join(mods)}")
                if affix.tags:
                    card_body.append(f"Build tags: {', '.join(affix.tags[:4])}")
                card_body.extend(_choice_build_preview(state, bundle, affix_id=item.affix_id, lang=lang))
            else:
                card_body.append(item.affix_id)

        elif item_type == "strategy" and item.strategy_style:
            card_body.append(f"{label('shop_strategy', lang)}: {item.strategy_style}")
            card_body.append(_choice_decision_note("strategy", lang))

        elif item_type == "heal" and item.heal_percent:
            card_body.append(label("shop_heal_percent", lang).format(percent=item.heal_percent))
            if getattr(item, "restore_mp", False):
                card_body.append("Restore MP to full" if lang == "en" else "MP 恢复至满")
            card_body.append(_choice_decision_note("heal", lang))

        elif item_type == "scout":
            hint = item.scout_hint.get(lang) if item.scout_hint else (
                "Reveal one route or boss mechanism clue."
                if lang == "en"
                else "揭示一条路线或 Boss 机制线索。"
            )
            for wrapped in _wrap_text(hint, 70):
                card_body.append(wrapped)
            card_body.append(_choice_decision_note("scout", lang))

        tone = "quiet" if not can_afford else "hero"
        lines.extend(_choice_card(f"[{idx}] SHOP", card_body, width=width, tone=tone))
        lines.append("")

    # Prompt
    lines.append(label("shop_prompt", lang))

    return "\n".join(_wrap_screen_lines(lines, width))


def _render_shop_budget_board(
    state,
    items,
    *,
    lang: str,
    width: int,
) -> list[str]:
    title = "BUDGET TACTICS BOARD" if lang == "en" else "预算战术面板"
    body = [
        (
            f"Wallet: {state.gold}g | Read: BUY fixes weakness / WAIT keeps route tempo"
            if lang == "en"
            else f"钱包: {state.gold} 金 | 读法: BUY 修短板 / WAIT 保路线节奏"
        )
    ]
    for idx, item in enumerate(items, start=1):
        body.append(_shop_budget_line(state, item, idx=idx, lang=lang))
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="counter").lines)


def _shop_budget_line(state, item, *, idx: int, lang: str) -> str:
    price = item.price or 0
    remaining = state.gold - price
    lane = _shop_lane_label(item.type)
    if remaining < 0:
        if lang == "zh":
            return f"[{idx}] WAIT   {lane} {price}g | 缺 {abs(remaining)}g，先存钱或选低价修正"
        return f"[{idx}] WAIT   {lane} {price}g | short {abs(remaining)}g; bank gold or pick cheaper"

    hp_ratio = state.current_hp / max(1, state.max_hp)
    mp_ratio = state.current_mp / max(1, state.max_mp)
    if item.type == "heal" and (hp_ratio <= 0.55 or mp_ratio <= 0.35 or getattr(item, "restore_mp", False)):
        verdict = "BUY"
        reason = "repairs HP/MP before pressure" if lang == "en" else "压力前修复 HP/MP"
    elif item.type in {"item", "affix"}:
        verdict = "BUY" if remaining >= 4 else "THINK"
        reason = "turns gold into Build tags" if lang == "en" else "金币转 Build 标签"
    elif item.type == "strategy":
        verdict = "BUY" if state.gold >= price + 4 else "THINK"
        reason = "fixes model bias" if lang == "en" else "修正模型偏好"
    elif item.type == "scout":
        verdict = "BUY" if remaining >= 0 else "WAIT"
        reason = "cheap boss/route intel" if lang == "en" else "低价 Boss/路线情报"
    else:
        verdict = "THINK"
        reason = "future flexibility" if lang == "en" else "后续弹性"

    if lang == "zh":
        return f"[{idx}] {verdict:<5} {lane} {price}g -> {remaining}g | {reason}"
    return f"[{idx}] {verdict:<5} {lane} {price}g -> {remaining}g | {reason}"


def render_run_summary(
    state,
    bundle: ContentBundle,
    *,
    language: str = DEFAULT_LANGUAGE,
    width: int = 100,
) -> str:
    """Render the run summary screen.

    Args:
        state: RunState instance
        bundle: ContentBundle
        language: Language code
        width: Terminal width

    Returns:
        Rendered screen as string
    """
    lang = language
    dungeon = state.current_dungeon(bundle)

    lines: list[str] = []

    # Header
    if state.phase == RunPhase.COMPLETE:
        lines.append(label("run_complete_title", lang))
    else:
        lines.append(label("run_dead_title", lang))
    lines.append("")

    # Dungeon info
    lines.append(f"{label('run_dungeon', lang)}: {dungeon.display_name.get(lang)}")
    lines.append(f"{label('run_id_label', lang)}: {state.run_id}")
    lines.append(f"{label('seed_label', lang)}: {state.seed}")
    lines.append("")

    # Stats
    lines.append(label("run_summary", lang))
    lines.append("")
    lines.extend(_render_run_result_board(state, bundle, lang=lang, width=width))
    lines.append("")
    lines.extend(_render_run_retry_loadout_board(state, bundle, lang=lang, width=width))
    lines.append("")
    lines.append(f"  {label('run_floor', lang)} reached: {state.current_floor_index + 1}")
    lines.append(f"  {label('run_gold', lang)} earned: {state.earned_gold_total}")
    lines.append(f"  {label('run_xp', lang)} earned: {state.earned_xp_total}")
    lines.append(f"  {label('run_battles_won', lang)}: {state.battles_won}")
    lines.append(f"  {label('run_battles_lost', lang)}: {state.battles_lost}")
    if getattr(state, "strategy_style", None):
        strategy_label = "Prompt style" if lang == "en" else "Prompt 预设"
        lines.append(f"  {strategy_label}: {state.strategy_style}")
    if getattr(state, "next_battle_shield", 0):
        shield_label = "Stored focus shield" if lang == "en" else "保留专注护盾"
        lines.append(f"  {shield_label}: {state.next_battle_shield}")
    lines.append("")

    # Completed nodes
    lines.append(f"{label('run_nodes_completed', lang)}: {len(state.completed_node_ids)}")
    for nid in state.completed_node_ids:
        if nid in bundle.nodes:
            node = bundle.nodes[nid]
            name = node.display_name.get(lang) or node.display_name.get("en", nid)
            lines.append(f"  - {name}")
        else:
            lines.append(f"  - {nid}")
    lines.append("")

    # Final build
    build = state.resolved_build(bundle)
    lines.append(f"{label('run_final_build', lang)}: {build.archetype(lang)}")
    progress = build.calculate_progress(bundle)
    lines.append(f"  {label('run_final_build_stage', lang)}: {progress.stage.badge} {progress.stage_name}")
    lines.append(f"  {label('run_final_build_items', lang)}: {', '.join(i.display_name.get(lang) or i.display_name.get('en', i.id) for i in build.items)}")
    lines.append(f"  {label('run_final_build_affixes', lang)}: {', '.join(a.display_name.get(lang) or a.display_name.get('en', a.id) for a in build.affixes)}")
    if build.resonances:
        lines.append(f"  {label('run_final_build_resonances', lang)}: {', '.join(r.display_name.get(lang) or r.display_name.get('en', r.id) for r in build.resonances)}")
    if getattr(state, "scout_notes", None):
        lines.append("")
        lines.append("Scout Notes:" if lang == "en" else "侦察笔记:")
        for note in state.scout_notes[-3:]:
            lines.append(f"  - {note}")

    return "\n".join(_wrap_screen_lines(lines, width))


def _render_run_result_board(
    state,
    bundle: ContentBundle,
    *,
    lang: str,
    width: int,
) -> list[str]:
    title = "RUN RESULT BOARD" if lang == "en" else "本局结算板"
    result = "complete" if state.phase == RunPhase.COMPLETE else "dead"
    result_badge = "[WIN]" if state.phase == RunPhase.COMPLETE else "[FALL]"
    build = state.resolved_build(bundle)
    progress = build.calculate_progress(bundle)
    body = [
        (
            f"{result_badge} Result: {result} | Floor {state.current_floor_index + 1} | Nodes {len(state.completed_node_ids)}"
            if lang == "en"
            else f"{result_badge} 结果: {result} | 第 {state.current_floor_index + 1} 层 | 节点 {len(state.completed_node_ids)}"
        ),
        (
            f"Combat: {state.battles_won}W/{state.battles_lost}L | Resources HP {state.current_hp}/{state.max_hp} MP {state.current_mp}/{state.max_mp}"
            if lang == "en"
            else f"战斗: {state.battles_won}胜/{state.battles_lost}负 | 资源 HP {state.current_hp}/{state.max_hp} MP {state.current_mp}/{state.max_mp}"
        ),
        (
            f"Build: {progress.stage.badge} {progress.stage_name} | {build.archetype(lang)}"
            if lang == "en"
            else f"Build: {progress.stage.badge} {progress.stage_name} | {build.archetype(lang)}"
        ),
        _run_result_next_hint(state, lang=lang),
    ]
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="climax" if state.phase == RunPhase.COMPLETE else "danger").lines)


def _run_result_next_hint(state, *, lang: str) -> str:
    if state.phase == RunPhase.COMPLETE:
        return "Next: raise risk, try a new hero, or chase HIGH ROLL" if lang == "en" else "下一步: 提高风险、换英雄或追求 HIGH ROLL"
    if state.battles_lost:
        return "Next: review route/rest timing and prompt style before retry" if lang == "en" else "下一步: 复盘路线/休整时机和 Prompt 风格"
    return "Next: inspect archive and prepare another run" if lang == "en" else "下一步: 查看归档并准备下一局"


def _render_run_retry_loadout_board(
    state,
    bundle: ContentBundle,
    *,
    lang: str,
    width: int,
) -> list[str]:
    title = "RETRY LOADOUT BOARD" if lang == "en" else "重开配置板"
    next_seed = state.seed + 1
    build = state.resolved_build(bundle)
    progress = build.calculate_progress(bundle)
    if state.phase == RunPhase.COMPLETE:
        body = (
            [
                f"[PROMPT] guarded / validate {progress.stage.badge} under pressure",
                f"[SEED] {next_seed} / pressure sample",
                "[ROUTE] elite/event greed line",
                "[BUILD] compare winning tags before changing hero",
            ]
            if lang == "en"
            else [
                f"[PROMPT] guarded / 在压力下验证 {progress.stage.badge}",
                f"[SEED] {next_seed} / 压力样本",
                "[ROUTE] 精英/事件贪心路线",
                "[BUILD] 换英雄前先比较通关标签",
            ]
        )
    else:
        body = (
            [
                "[PROMPT] control / slow enemy tempo",
                f"[SEED] {next_seed} / fixed retry sample",
                "[ROUTE] rest/shop before boss pressure",
                "[CODEX] patch unknown enemy families",
            ]
            if lang == "en"
            else [
                "[PROMPT] control / 降低敌方节奏",
                f"[SEED] {next_seed} / 固定重试样本",
                "[ROUTE] Boss 压力前找休整/商店",
                "[CODEX] 补未知敌人家族",
            ]
        )
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="hero").lines)


def render_rest(
    state,
    bundle: ContentBundle,
    *,
    language: str = DEFAULT_LANGUAGE,
    width: int = 100,
    heal_percent: int = 30,
    restore_full_mp: bool = True,
) -> str:
    """Render the rest screen.

    Args:
        state: RunState instance
        bundle: ContentBundle
        language: Language code
        width: Terminal width
        heal_percent: Percentage of HP to heal
        restore_full_mp: Whether to restore full MP

    Returns:
        Rendered screen as string
    """
    lang = language
    node = state.current_node(bundle)

    lines: list[str] = []

    lines.append(label("rest_title", lang))
    lines.append("")

    rest_name = node.display_name.get(lang) or node.display_name.get("en", "Rest Site")
    lines.append(rest_name)
    desc = node.description.get(lang) or node.description.get("en", "")
    if desc:
        lines.append(desc)
    lines.append("")

    lines.append(f"Current HP: {state.current_hp}/{state.max_hp}")
    lines.append(f"Current MP: {state.current_mp}/{state.max_mp}")
    lines.append("")
    lines.extend(_rest_decision_preview(state, heal_percent=heal_percent, restore_full_mp=restore_full_mp, lang=lang))
    lines.append("")
    lines.extend(
        _render_rest_decision_ring(
            state,
            heal_percent=heal_percent,
            restore_full_mp=restore_full_mp,
            lang=lang,
            width=width,
        )
    )
    lines.append("")
    lines.extend(
        _render_rest_priority_board(
            state,
            heal_percent=heal_percent,
            restore_full_mp=restore_full_mp,
            lang=lang,
            width=width,
        )
    )
    lines.append("")

    if lang == "zh":
        lines.append("选择一个休整方式:")
        recover_hp = min(state.max_hp, state.current_hp + int(state.max_hp * heal_percent / 100))
        rest_cards = [
            ("[1] Recover", [f"HP {state.current_hp}->{recover_hp}, MP {state.current_mp}->{state.max_mp}"], "hero"),
            ("[2] Focus", ["下一战开局获得 SHD 12 护盾"], "counter"),
            ("[3] Study", ["记录一条下一路线/敌方机制侦察提示"], "quiet"),
        ]
    else:
        lines.append("Choose one rest option:")
        recover_hp = min(state.max_hp, state.current_hp + int(state.max_hp * heal_percent / 100))
        rest_cards = [
            ("[1] Recover", [f"HP {state.current_hp}->{recover_hp}, MP {state.current_mp}->{state.max_mp}"], "hero"),
            ("[2] Focus", ["next battle starts with SHD 12 shield"], "counter"),
            ("[3] Study", ["add one route/enemy mechanism scout note"], "quiet"),
        ]
    for title, body, tone in rest_cards:
        lines.extend(_choice_card(title, body, width=width, tone=tone))
    lines.append("")

    lines.append(label("rest_prompt", lang))

    return "\n".join(_wrap_screen_lines(lines, width))


def _render_rest_priority_board(
    state,
    *,
    heal_percent: int,
    restore_full_mp: bool,
    lang: str,
    width: int,
) -> list[str]:
    title = "REST PRIORITY BOARD" if lang == "en" else "休整优先级面板"
    hp_ratio = state.current_hp / max(1, state.max_hp)
    mp_ratio = state.current_mp / max(1, state.max_mp)
    heal_amount = int(state.max_hp * heal_percent / 100) if heal_percent > 0 else 0
    recover_hp = min(state.max_hp, state.current_hp + heal_amount)
    recover_mp = state.max_mp if restore_full_mp else state.current_mp
    body = [
        (
            "Read: PICK now / FLEX optional / LOW value this moment"
            if lang == "en"
            else "读法: PICK 当前优先 / FLEX 可选 / LOW 此刻低收益"
        )
    ]
    if hp_ratio <= 0.45 or mp_ratio <= 0.25:
        recover_tag = "PICK"
        focus_tag = "FLEX"
        study_tag = "LOW"
    elif hp_ratio <= 0.7 or mp_ratio <= 0.5:
        recover_tag = "FLEX"
        focus_tag = "PICK"
        study_tag = "FLEX"
    else:
        recover_tag = "LOW"
        focus_tag = "FLEX"
        study_tag = "PICK"
    if lang == "zh":
        body.extend(
            [
                f"[1] {recover_tag:<4} RECOVER | HP {state.current_hp}->{recover_hp} / MP {state.current_mp}->{recover_mp}",
                "[2] {tag:<4} FOCUS   | 下一战 SHD 12，适合高压/精英前".format(tag=focus_tag),
                "[3] {tag:<4} STUDY   | 侦察未知机制，适合血蓝健康时".format(tag=study_tag),
            ]
        )
    else:
        body.extend(
            [
                f"[1] {recover_tag:<4} RECOVER | HP {state.current_hp}->{recover_hp} / MP {state.current_mp}->{recover_mp}",
                f"[2] {focus_tag:<4} FOCUS   | SHD 12 next battle; best before pressure",
                f"[3] {study_tag:<4} STUDY   | scout unknown mechanics when resources are safe",
            ]
        )
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="counter").lines)


def render_event(
    state,
    bundle: ContentBundle,
    *,
    language: str = DEFAULT_LANGUAGE,
    width: int = 100,
) -> str:
    """Render the event screen.

    Args:
        state: RunState instance
        bundle: ContentBundle
        language: Language code
        width: Terminal width

    Returns:
        Rendered screen as string
    """
    lang = language
    node = state.current_node(bundle)
    choices = state.current_choices

    lines: list[str] = []

    lines.append(label("event_title", lang))
    lines.append("")

    event_name = node.display_name.get(lang) or node.display_name.get("en", "Event")
    lines.append(event_name)
    desc = node.description.get(lang) or node.description.get("en", "")
    if desc:
        lines.append(desc)
    lines.append("")

    if choices:
        lines.extend(_render_event_fate_board(state, bundle, choices, lang=lang, width=width))
        lines.append("")
        lines.extend(_render_event_risk_board(state, bundle, choices, lang=lang, width=width))
        lines.append("")
        lines.append("Choices:")
        lines.append("")
        for idx, choice in enumerate(choices, start=1):
            choice_name = None
            choice_desc = None

            if hasattr(choice, "display_name"):
                if hasattr(choice.display_name, "get"):
                    choice_name = choice.display_name.get(lang) or choice.display_name.get("en")
                else:
                    choice_name = str(choice.display_name)
            elif hasattr(choice, "description"):
                if hasattr(choice.description, "get"):
                    choice_desc = choice.description.get(lang) or choice.description.get("en")
                else:
                    choice_desc = str(choice.description)

            if not choice_name:
                choice_name = f"Choice {idx}"

            card_body: list[str] = []
            if choice_desc:
                card_body.append(choice_desc)

            if hasattr(choice, "type"):
                if choice.type == "item" and hasattr(choice, "item_id") and choice.item_id:
                    if choice.item_id in bundle.items:
                        item = bundle.items[choice.item_id]
                        item_name = item.display_name.get(lang) or item.display_name.get("en", choice.item_id)
                        card_body.append(f"Item: {item_name} [{item.tier}]")
                elif choice.type == "affix" and hasattr(choice, "affix_id") and choice.affix_id:
                    if choice.affix_id in bundle.affixes:
                        affix = bundle.affixes[choice.affix_id]
                        affix_name = affix.display_name.get(lang) or affix.display_name.get("en", choice.affix_id)
                        card_body.append(f"Affix: {affix_name}")
                elif choice.type == "gold" and hasattr(choice, "gold") and choice.gold:
                    card_body.append(f"Gold: +{choice.gold}")
                elif choice.type == "heal" and hasattr(choice, "heal_percent") and choice.heal_percent:
                    card_body.append(f"Heal: {choice.heal_percent}% HP")

            lines.extend(_choice_card(f"[{idx}] {choice_name}", card_body, width=width, tone="normal"))
            lines.append("")
    else:
        lines.append("No choices available.")
        lines.append("")

    lines.append(label("event_prompt", lang))

    return "\n".join(_wrap_screen_lines(lines, width))


def _render_event_risk_board(
    state,
    bundle: ContentBundle,
    choices,
    *,
    lang: str,
    width: int,
) -> list[str]:
    title = "EVENT RISK BOARD" if lang == "en" else "事件风险面板"
    body = [
        (
            "Read: TAKE fits state / GREED high value / SAFE repairs run / INFO reduces unknowns"
            if lang == "en"
            else "读法: TAKE 贴合状态 / GREED 高收益 / SAFE 修复本局 / INFO 降低未知"
        )
    ]
    for idx, choice in enumerate(choices, start=1):
        body.append(_event_risk_line(state, bundle, choice, idx=idx, lang=lang))
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="counter").lines)


def _event_risk_line(state, bundle: ContentBundle, choice, *, idx: int, lang: str) -> str:
    choice_type = getattr(choice, "type", "")
    hp_ratio = state.current_hp / max(1, state.max_hp)
    if choice_type in {"item", "affix"}:
        current = state.resolved_build(bundle)
        item_ids = list(getattr(state, "item_ids", ()))
        affix_ids = list(getattr(state, "affix_ids", ()))
        if choice_type == "item" and getattr(choice, "item_id", None):
            item_ids.append(choice.item_id)
        if choice_type == "affix" and getattr(choice, "affix_id", None):
            affix_ids.append(choice.affix_id)
        projected = resolve_build(
            bundle.get_hero(state.hero_id),
            bundle,
            item_ids=tuple(item_ids),
            affix_ids=tuple(affix_ids),
        )
        tags = _tag_delta_summary(current, projected)
        if any(tag in tags for tag in HERO_CORE_TAGS.get(state.hero_id, ())):
            verdict = "TAKE"
            reason = f"core Build tags {tags}" if lang == "en" else f"核心 Build 标签 {tags}"
        else:
            verdict = "GREED"
            reason = f"pivot tags {tags}" if lang == "en" else f"转向标签 {tags}"
    elif choice_type == "heal":
        verdict = "SAFE" if hp_ratio <= 0.7 else "LOW"
        reason = "HP line is stressed" if hp_ratio <= 0.7 and lang == "en" else (
            "血线有压力" if hp_ratio <= 0.7 else "HP already safe"
        )
        if lang == "zh" and hp_ratio > 0.7:
            reason = "血线安全"
    elif choice_type == "gold":
        verdict = "GREED" if hp_ratio > 0.45 else "THINK"
        reason = "funds shop fixes" if lang == "en" else "补商店修正资金"
    elif choice_type == "codex":
        verdict = "INFO"
        reason = "adds prompt intel" if lang == "en" else "增加提示词情报"
    else:
        verdict = "FLEX"
        reason = "unknown event branch" if lang == "en" else "未知事件分支"
    return f"[{idx}] {verdict:<5} => {reason}"


def _render_event_fate_board(
    state,
    bundle: ContentBundle,
    choices,
    *,
    lang: str,
    width: int,
) -> list[str]:
    title = "EVENT FATE BOARD" if lang == "en" else "事件命运板"
    body = [
        (
            "Read the altar before choosing: build, economy, or survival."
            if lang == "en"
            else "先读祭坛: Build、经济或生存三种走向。"
        )
    ]
    for idx, choice in enumerate(choices, start=1):
        body.append(_event_fate_line(state, bundle, choice, idx=idx, lang=lang))
    return list(pixel_panel(title, [fit_text(line, max(12, width - 4)) for line in body], width, tone="quiet").lines)


def _event_fate_line(state, bundle: ContentBundle, choice, *, idx: int, lang: str) -> str:
    if getattr(choice, "type", "") in {"item", "affix"}:
        current = state.resolved_build(bundle)
        item_ids = list(getattr(state, "item_ids", ()))
        affix_ids = list(getattr(state, "affix_ids", ()))
        if choice.type == "item" and getattr(choice, "item_id", None):
            item_ids.append(choice.item_id)
        if choice.type == "affix" and getattr(choice, "affix_id", None):
            affix_ids.append(choice.affix_id)
        projected = resolve_build(
            bundle.get_hero(state.hero_id),
            bundle,
            item_ids=tuple(item_ids),
            affix_ids=tuple(affix_ids),
        )
        tag_delta = _tag_delta_summary(current, projected)
        if lang == "zh":
            return f"[{idx}] BUILD => 标签 {tag_delta}"
        return f"[{idx}] BUILD => tags {tag_delta}"
    if getattr(choice, "type", "") == "gold" and getattr(choice, "gold", None):
        return f"[{idx}] GOLD  => +{choice.gold} shop power"
    if getattr(choice, "type", "") == "heal" and getattr(choice, "heal_percent", None):
        heal_amount = int(state.max_hp * choice.heal_percent / 100)
        healed = min(state.max_hp, state.current_hp + heal_amount)
        return f"[{idx}] HEAL  => HP {state.current_hp}->{healed}"
    if getattr(choice, "type", "") == "codex":
        amount = getattr(choice, "progress", None) or 1
        return f"[{idx}] CODEX => +{amount} study"
    return f"[{idx}] FATE  => flexible outcome"


def _codex_fog_text(text: str, *, show: bool, width: int = 40) -> str:
    """Return text or fog placeholder based on show flag."""
    if show:
        return text
    return "░" * min(width, len(text) + 4)


def render_codex_card(
    enemy_id: str,
    bundle: ContentBundle,
    codex_progress: CodexProgress | None = None,
    *,
    language: str = DEFAULT_LANGUAGE,
    width: int = 60,
) -> str:
    """Render a codex card for a monster.

    Based on G07: Codex cards show information based on unlock stage.
    - UNKNOWN: silhouette only, fog for all details
    - OBSERVED: name, HP range, common skills
    - FAMILIAR: resistances, weaknesses, read speed
    - MASTERED: full mechanics, stage behavior, recommended builds
    - HUNTED: special counter strategies, drop tendencies

    Args:
        enemy_id: Enemy ID
        bundle: Content bundle
        codex_progress: Codex progress tracking (None means UNKNOWN)
        language: Language code
        width: Card width

    Returns:
        Rendered codex card as string
    """
    lang = language
    enemy = bundle.enemies.get(enemy_id)

    if enemy is None:
        lines = [
            "+" + "-" * (width - 2) + "+",
            _codex_line("[??] UNKNOWN MONSTER", width),
            _codex_line("id: " + enemy_id, width),
            "+" + "-" * (width - 2) + "+",
        ]
        return "\n".join(lines)

    family_id = enemy.family_id or enemy_id
    stage = (
        codex_progress.get_stage(family_id, enemy.tier)
        if codex_progress
        else CodexStage.UNKNOWN
    )
    stage_badge = codex_stage_badge(stage)
    stage_label = codex_stage_label(stage, lang)

    name = enemy.display_name.get(lang) or enemy.display_name.get("en", enemy_id)
    tier_display = enemy.tier_display(lang)
    glyph = enemy.short_glyph

    is_unknown = stage == CodexStage.UNKNOWN
    is_observed = stage >= CodexStage.OBSERVED
    is_familiar = stage >= CodexStage.FAMILIAR
    is_mastered = stage >= CodexStage.MASTERED
    is_hunted = stage >= CodexStage.HUNTED

    lines: list[str] = []
    border = "+" + "-" * (width - 2) + "+"

    lines.append(border)

    if is_unknown:
        header = f"[??] UNKNOWN FAMILY"
        lines.append(_codex_line(header, width))
        lines.append(_codex_line("tier: ???", width))
        lines.extend(_codex_sprite_lines(glyph, stage, width=width))
        lines.extend(_render_codex_counter_plan(enemy, stage, lang=lang, width=width))
        lines.append(_codex_line("known: never encountered", width))
        lines.append(_codex_line("unlock: encounter once", width))
    else:
        reveal = f"EVENT: CODEX REVEAL {stage_badge}"
        lines.append(_codex_line(reveal, width))
        header = f"{stage_badge} {name}"
        lines.append(_codex_line(header, width))
        lines.append(_codex_line("Codex: " + stage_label, width))
        lines.append(_codex_line("Tier: " + tier_display, width))

        if family_id:
            family_label = "家系" if lang == "zh" else "Family"
            family_name = _codex_gallery_family(enemy, lang=lang)
            lines.append(_codex_line(f"{family_label}: {family_name}", width))

        lines.append(_codex_line("Glyph: [" + glyph + "]", width))
        lines.extend(_codex_sprite_lines(glyph, stage, width=width))

        if is_observed:
            codex_text = enemy.codex_text_for_stage(stage, lang)
            if codex_text:
                lines.append(_codex_rule(width))
                for line in codex_text.splitlines():
                    wrapped = [line[i:i + (width - 4)] for i in range(0, len(line), width - 4)]
                    for w in wrapped:
                        lines.append(_codex_line(w, width))

        lines.append(_codex_rule(width))

        hp_text = _codex_fog_text(
            f"HP: {enemy.base_stats.hp}  MP: {enemy.base_stats.mp}",
            show=is_observed,
            width=20
        )
        lines.append(_codex_line(hp_text, width))

        spd_text = _codex_fog_text(
            f"SPD: {enemy.base_stats.speed}",
            show=is_observed,
            width=20
        )
        lines.append(_codex_line(spd_text, width))

        if is_familiar:
            behavior_text = f"Behavior: {enemy.behavior.kind}"
            lines.append(_codex_line(behavior_text, width))
            lines.append(_codex_line("MECHANIC READ: telegraph / break / punish", width))

        if is_mastered:
            atk_def_text = f"ATK: {enemy.base_stats.attack}  DEF: {enemy.base_stats.defense}  POW: {enemy.base_stats.power}"
            lines.append(_codex_line(atk_def_text, width))
            lines.append(_codex_line("WEAKNESS MAP: interrupt windows and build tags known", width))

        lines.extend(_render_codex_counter_plan(enemy, stage, lang=lang, width=width))
        lines.append(_codex_rule(width))

        if codex_progress:
            entry = codex_progress.find_entry(family_id, enemy.tier)
            if entry is None:
                entry = codex_progress.get_entry(family_id, enemy.tier)
            progress_text = f"Encounters: {entry.encounters}  Defeats: {entry.defeats}"
            lines.append(_codex_line(progress_text, width))

            next_stage = ""
            if stage == CodexStage.UNKNOWN:
                next_stage = "Next: encounter once → OBSERVED"
            elif stage == CodexStage.OBSERVED:
                next_stage = f"Next: defeat {2 - entry.defeats} more → FAMILIAR"
            elif stage == CodexStage.FAMILIAR:
                next_stage = f"Next: defeat {5 - entry.defeats} more → MASTERED"
            elif stage == CodexStage.MASTERED:
                next_stage = f"Next: defeat {10 - entry.defeats} more → HUNTED"
            else:
                next_stage = "MAX STAGE: HUNTED"
            lines.append(_codex_line(next_stage, width))
        else:
            lines.append(_codex_line("Progress: unknown", width))

    lines.append(border)

    return "\n".join(lines)


def _render_codex_counter_plan(
    enemy: EnemyData,
    stage: CodexStage,
    *,
    lang: str,
    width: int,
) -> list[str]:
    title = "COUNTER PLAN BOARD" if lang == "en" else "反制计划板"
    lines = [_codex_rule(width), _codex_line(title, width)]
    if stage == CodexStage.UNKNOWN:
        unknown_lines = (
            [
                "[THREAT] ????? / encounter to reveal",
                "[WINDOW] ????? / watch first turn",
                "[BUILD] ????? / keep flexible",
            ]
            if lang == "en"
            else [
                "[威胁] ????? / 遭遇后解锁",
                "[窗口] ????? / 观察首回合",
                "[构筑] ????? / 保持弹性",
            ]
        )
        return lines + [_codex_line(line, width) for line in unknown_lines]

    threat = _codex_threat_line(enemy, lang=lang)
    lines.append(_codex_line(threat, width))

    if stage >= CodexStage.FAMILIAR:
        lines.append(_codex_line(_codex_window_line(enemy, lang=lang), width))
    else:
        lines.append(
            _codex_line(
                "[WINDOW] fogged / survive one more read"
                if lang == "en"
                else "[窗口] 迷雾 / 再观察一轮",
                width,
            )
        )

    if stage >= CodexStage.MASTERED:
        lines.append(_codex_line(_codex_build_line(enemy, lang=lang), width))
    else:
        lines.append(
            _codex_line(
                "[BUILD] locked / reach MASTERED"
                if lang == "en"
                else "[构筑] 锁定 / 达到掌握解锁",
                width,
            )
        )

    if stage >= CodexStage.HUNTED:
        lines.append(_codex_line(_codex_hunted_loop_line(enemy, lang=lang), width))
    return lines


def _codex_threat_line(enemy: EnemyData, *, lang: str) -> str:
    if enemy.behavior.kind == "rule_chant":
        if lang == "zh":
            return f"[威胁] 吟唱爆发 / {enemy.behavior.chant_damage} 伤害"
        return f"[THREAT] chant burst / {enemy.behavior.chant_damage} damage"
    if enemy.base_stats.speed >= 12:
        return "[威胁] 高速压血 / 先手风险" if lang == "zh" else "[THREAT] fast pressure / tempo risk"
    return "[威胁] 近战压迫 / 低防可破" if lang == "zh" else "[THREAT] brawler pressure / low armor"


def _codex_window_line(enemy: EnemyData, *, lang: str) -> str:
    if enemy.behavior.kind == "rule_chant":
        turns = max(1, enemy.behavior.chant_charge_turns)
        if lang == "zh":
            return f"[窗口] 吟唱 {turns} 回合 / 打断或沉默"
        return f"[WINDOW] chant {turns} turn(s) / interrupt or silence"
    if enemy.base_stats.speed >= 12:
        return "[窗口] 先清小怪 / 护盾抗首轮" if lang == "zh" else "[WINDOW] shield first / focus fast adds"
    return "[窗口] 低血狂暴前爆发" if lang == "zh" else "[WINDOW] burst before low-HP rage"


def _codex_build_line(enemy: EnemyData, *, lang: str) -> str:
    family = enemy.family_id
    if "black_candle" in family or enemy.behavior.kind == "rule_chant":
        return "[构筑] control + silence + holy" if lang == "zh" else "[BUILD] control + silence + holy"
    if "mire" in family:
        return "[构筑] cleanse + fire + focus" if lang == "zh" else "[BUILD] cleanse + fire + focus"
    if "hungry" in family:
        return "[构筑] bleed + execute + shield" if lang == "zh" else "[BUILD] bleed + execute + shield"
    return "[构筑] damage + defense + scout" if lang == "zh" else "[BUILD] damage + defense + scout"


def _codex_hunted_loop_line(enemy: EnemyData, *, lang: str) -> str:
    if enemy.behavior.kind == "rule_chant":
        turns = max(1, enemy.behavior.chant_charge_turns)
        if lang == "zh":
            return f"[循环] 每 {turns + 1} 拍预留反制"
        return f"[LOOP] reserve counter every {turns + 1} beats"
    return "[循环] 压低血线后收割" if lang == "zh" else "[LOOP] hold burst for execute range"


def _codex_sprite_lines(glyph: str, stage: CodexStage, *, width: int) -> list[str]:
    if stage == CodexStage.UNKNOWN:
        title = "FOG SILHOUETTE"
        art = _fog_sprite(enemy_block_sprite(glyph, "idle"))
    else:
        title = "BLOCK SILHOUETTE"
        pose = "break" if stage >= CodexStage.MASTERED else "idle"
        art = enemy_block_sprite(glyph, pose)
    lines = [_codex_line(title, width)]
    for row in art[:5]:
        lines.append(_codex_line("  " + row, width))
    return lines


def _codex_line(text: str, width: int) -> str:
    inner = max(0, width - 4)
    return "| " + pad_right(fit_text(text, inner), inner) + " |"


def _codex_rule(width: int) -> str:
    inner = max(0, width - 4)
    return "| " + "-" * inner + " |"


def _fog_sprite(sprite: list[str]) -> list[str]:
    fogged: list[str] = []
    for row in sprite:
        fogged.append("".join("░" if char != " " else " " for char in row))
    return fogged


def render_codex_summary(
    bundle: ContentBundle,
    codex_progress: CodexProgress | None = None,
    *,
    language: str = DEFAULT_LANGUAGE,
) -> str:
    """Render a summary of all codex entries.

    Args:
        bundle: Content bundle
        codex_progress: Codex progress tracking
        language: Language code

    Returns:
        Rendered codex summary as string
    """
    lang = language
    lines: list[str] = []

    title = {
        "en": "CODEX :: MONSTER ARCHIVE",
        "zh": "图鉴 :: 怪物档案",
    }.get(lang, "CODEX :: MONSTER ARCHIVE")

    lines.append(title)
    lines.append("")

    total = len(bundle.enemies)
    observed = 0
    familiar = 0
    mastered = 0
    hunted = 0

    if codex_progress:
        for enemy_id, enemy in bundle.enemies.items():
            family_id = enemy.family_id or enemy_id
            stage = codex_progress.get_stage(family_id, enemy.tier)
            if stage >= CodexStage.OBSERVED:
                observed += 1
            if stage >= CodexStage.FAMILIAR:
                familiar += 1
            if stage >= CodexStage.MASTERED:
                mastered += 1
            if stage >= CodexStage.HUNTED:
                hunted += 1

    lines.append(f"Total: {total} monsters")
    lines.append(f"Observed: {observed}/{total}")
    lines.append(f"Familiar: {familiar}/{total}")
    lines.append(f"Mastered: {mastered}/{total}")
    lines.append(f"Hunted: {hunted}/{total}")
    lines.append("")
    lines.extend(_render_codex_hunt_board(bundle, codex_progress, lang=lang))
    lines.append("")
    lines.extend(_render_codex_gallery_board(bundle, codex_progress, lang=lang))
    lines.append("")

    return "\n".join(lines)


def _render_codex_gallery_board(
    bundle: ContentBundle,
    codex_progress: CodexProgress | None,
    *,
    lang: str,
) -> list[str]:
    title = "MONSTER GALLERY BOARD" if lang == "en" else "怪物图鉴画廊"
    lines = [title]
    family_label, behavior_label, silhouette_label, card_label = _codex_gallery_field_labels(lang)
    for enemy_id, enemy in bundle.enemies.items():
        family_id = enemy.family_id or enemy_id
        stage = (
            codex_progress.get_stage(family_id, enemy.tier)
            if codex_progress
            else CodexStage.UNKNOWN
        )
        badge = codex_stage_badge(stage)
        glyph = f"[{enemy.short_glyph}]"
        name = (
            enemy.display_name.get(lang) or enemy.display_name.get("en", enemy_id)
            if stage >= CodexStage.OBSERVED
            else "????"
        )
        threat = _codex_gallery_threat(enemy, lang=lang)
        silhouette = _codex_gallery_silhouette(enemy, stage)
        next_action = _codex_gallery_next_action(stage, lang=lang)
        family = _codex_gallery_family(enemy, lang=lang)
        card_code = _codex_gallery_card_code(enemy)
        lines.append(fit_text(f"  {badge} {glyph} {name} [{enemy.tier_display(lang)}]", 80))
        lines.append(fit_text(f"    {family_label}: {family}", 80))
        lines.append(fit_text(f"    {behavior_label}: {threat}", 80))
        lines.append(fit_text(f"    {silhouette_label}: {silhouette}", 80))
        lines.append(fit_text(f"    {card_label}: {card_code} | -> {next_action}", 80))
    lines.append(
        "Next: ouro codex <card> for counter plan"
        if lang == "en"
        else "下一步: ouro codex <卡片> 查看反制计划"
    )
    return lines


def _codex_gallery_field_labels(lang: str) -> tuple[str, str, str, str]:
    if lang == "zh":
        return ("家系", "行为", "剪影", "卡片")
    return ("Family", "Behavior", "Silhouette", "Card")


def _codex_gallery_card_code(enemy: EnemyData) -> str:
    return enemy.short_glyph or "?"


def _codex_gallery_threat(enemy: EnemyData, *, lang: str) -> str:
    if enemy.behavior.kind == "rule_chant":
        return "吟唱" if lang == "zh" else "chant"
    if enemy.base_stats.speed >= 12:
        return "高速" if lang == "zh" else "fast"
    return "近战" if lang == "zh" else "brawler"


def _codex_gallery_silhouette(enemy: EnemyData, stage: CodexStage) -> str:
    if stage == CodexStage.UNKNOWN:
        return "????"
    sprite = asset_enemy_sprite(enemy.short_glyph, "idle")
    row = next((line.strip() for line in sprite if line.strip()), "???")
    return row


def _codex_gallery_next_action(stage: CodexStage, *, lang: str) -> str:
    if stage == CodexStage.UNKNOWN:
        return "遭遇一次" if lang == "zh" else "encounter once"
    if stage == CodexStage.OBSERVED:
        return "击败至熟悉" if lang == "zh" else "defeat to familiar"
    if stage == CodexStage.FAMILIAR:
        return "刷到掌握" if lang == "zh" else "push mastered"
    if stage == CodexStage.MASTERED:
        return "追猎循环" if lang == "zh" else "hunt loop"
    return "已追猎" if lang == "zh" else "hunted"


def _codex_gallery_family(enemy: EnemyData, *, lang: str) -> str:
    family_id = enemy.family_id or ""
    if family_id.startswith("family_"):
        family_id = family_id.removeprefix("family_")
    family_id = family_id.replace("_", " ").strip()
    if not family_id:
        return "Unknown family" if lang == "en" else "未知家系"

    if lang == "zh":
        zh_family_map = {
            "hungry cultist": "饥饿邪教",
            "black candle": "黑烛教团",
            "mire vermin": "瘟沼毒虫",
            "ash warden": "灰烬守卫",
        }
        return zh_family_map.get(family_id, family_id)

    return " ".join(part.capitalize() for part in family_id.split())


def _render_codex_hunt_board(
    bundle: ContentBundle,
    codex_progress: CodexProgress | None,
    *,
    lang: str,
) -> list[str]:
    rows: list[tuple[str, EnemyData, CodexStage]] = []
    for enemy_id, enemy in bundle.enemies.items():
        family_id = enemy.family_id or enemy_id
        stage = (
            codex_progress.get_stage(family_id, enemy.tier)
            if codex_progress
            else CodexStage.UNKNOWN
        )
        rows.append((enemy_id, enemy, stage))

    unknown = sum(1 for _, _, stage in rows if stage == CodexStage.UNKNOWN)
    familiar_gap = sum(1 for _, _, stage in rows if stage < CodexStage.FAMILIAR)
    mastered_gap = sum(1 for _, _, stage in rows if stage < CodexStage.MASTERED)
    threat_pool = _codex_summary_threat_pool(rows, lang=lang)

    target = _codex_next_hunt_target(rows, lang=lang)
    if lang == "zh":
        title = "CODEX HUNT BOARD :: 图鉴狩猎板"
        lines = [
            title,
            f"  缺口: 未观察 {unknown} / 未熟悉 {familiar_gap} / 未掌握 {mastered_gap}",
            f"  威胁池: {threat_pool}",
            f"  优先目标: {target}",
            "  下一步: ouro codex <卡片> 查看反制计划",
        ]
    else:
        title = "CODEX HUNT BOARD"
        lines = [
            title,
            f"  Gaps: unknown {unknown} / familiar {familiar_gap} / mastered {mastered_gap}",
            f"  Threat pool: {threat_pool}",
            f"  Priority target: {target}",
            "  Next: ouro codex <card> for counter plan",
        ]
    return lines


def _codex_next_hunt_target(
    rows: list[tuple[str, EnemyData, CodexStage]],
    *,
    lang: str,
) -> str:
    priority = {
        CodexStage.UNKNOWN: 0,
        CodexStage.OBSERVED: 1,
        CodexStage.FAMILIAR: 2,
        CodexStage.MASTERED: 3,
        CodexStage.HUNTED: 4,
    }
    candidates = [
        (priority[stage], enemy.tier == "archive_bound", index, enemy_id, enemy, stage)
        for index, (enemy_id, enemy, stage) in enumerate(rows)
        if stage < CodexStage.HUNTED
    ]
    if not candidates:
        return "全部猎杀完成" if lang == "zh" else "all monsters hunted"
    _, _, _, _, enemy, stage = min(candidates)
    name = enemy.display_name.get(lang) or enemy.display_name.get("en", "Unknown monster")
    badge = codex_stage_badge(stage)
    card = _codex_gallery_card_code(enemy)
    if lang == "zh":
        return (
            f"{badge} {name} / {_codex_gallery_family(enemy, lang=lang)} / "
            f"{enemy.tier_display(lang)} / 卡片 {card}"
        )
    return (
        f"{badge} {name} / {_codex_gallery_family(enemy, lang=lang)} / "
        f"{enemy.tier_display(lang)} / Card {card}"
    )


def _codex_summary_threat_pool(
    rows: list[tuple[str, EnemyData, CodexStage]],
    *,
    lang: str,
) -> str:
    counts = {"chant": 0, "fast": 0, "brawler": 0}
    for _, enemy, stage in rows:
        if stage >= CodexStage.MASTERED:
            continue
        if enemy.behavior.kind == "rule_chant":
            counts["chant"] += 1
        elif enemy.base_stats.speed >= 12:
            counts["fast"] += 1
        else:
            counts["brawler"] += 1
    if lang == "zh":
        parts = [
            f"吟唱 {counts['chant']}",
            f"高速 {counts['fast']}",
            f"近战 {counts['brawler']}",
        ]
    else:
        parts = [
            f"chant {counts['chant']}",
            f"fast {counts['fast']}",
            f"brawler {counts['brawler']}",
        ]
    return " / ".join(parts)


def render_death_history(
    deaths: list[dict],
    bundle: ContentBundle,
    *,
    language: str = DEFAULT_LANGUAGE,
    limit: int = 10,
) -> str:
    """Render durable death-history entries as a player-facing archive."""
    lang = language
    title = "DEATH HISTORY :: FALLEN RUNS" if lang == "en" else "死亡历史 :: 陨落记录"
    empty = "No fallen runs recorded yet." if lang == "en" else "尚无陨落记录。"
    shown = list(reversed(deaths))[: max(0, limit)]

    lines = [title, ""]
    lines.append(f"Total: {len(deaths)}" if lang == "en" else f"总计: {len(deaths)}")
    lines.append(f"Showing: {len(shown)}" if lang == "en" else f"显示: {len(shown)}")
    lines.append("")

    if not shown:
        lines.append(empty)
        return "\n".join(lines)

    lines.extend(_render_death_review_board(shown, lang=lang))
    lines.append("")

    for index, entry in enumerate(shown, start=1):
        run_id = str(entry.get("run_id", "-"))
        seed = str(entry.get("seed", "-"))
        hero_id = str(entry.get("hero_id", "-"))
        dungeon_id = str(entry.get("dungeon_id", "-"))
        result = str(entry.get("battle_result", "-"))
        wins = int(entry.get("battles_won", 0) or 0)
        losses = int(entry.get("battles_lost", 0) or 0)
        node_ids = list(entry.get("completed_node_ids", []) or [])
        build = entry.get("build", {}) if isinstance(entry.get("build", {}), dict) else {}

        hero = bundle.heroes.get(hero_id)
        dungeon = bundle.dungeons.get(dungeon_id)
        hero_name = (
            hero.display_name.get(lang) or hero.display_name.get("en", hero_id)
            if hero is not None else hero_id
        )
        dungeon_name = (
            dungeon.display_name.get(lang) or dungeon.display_name.get("en", dungeon_id)
            if dungeon is not None else dungeon_id
        )
        build_name = str(build.get("archetype", "-"))
        build_badge = str(build.get("stage_badge", ""))

        lines.append(f"[{index}] {run_id}")
        lines.append(f"  Seed: {seed}  Result: {result}")
        lines.append(f"  Hero: {hero_name}  Dungeon: {dungeon_name}")
        lines.append(f"  Battles: {wins}W/{losses}L  Nodes: {len(node_ids)}")
        lines.append(f"  Build: {build_name} {build_badge}".rstrip())
        if node_ids:
            node_names: list[str] = []
            for node_id in node_ids[:4]:
                node = bundle.nodes.get(str(node_id))
                node_names.append(
                    node.display_name.get(lang) or node.display_name.get("en", str(node_id))
                    if node is not None else str(node_id)
                )
            extra = len(node_ids) - len(node_names)
            node_line = " -> ".join(node_names)
            if extra > 0:
                node_line += f" -> +{extra}"
            lines.append(f"  Path: {node_line}")
        lines.append("")

    return "\n".join(lines).rstrip()


def _render_death_review_board(deaths: list[dict], *, lang: str) -> list[str]:
    latest = deaths[0]
    deepest = max(deaths, key=lambda entry: int(entry.get("battles_won", 0) or 0))
    latest_seed = str(latest.get("seed", "-"))
    deepest_seed = str(deepest.get("seed", "-"))
    deepest_wins = int(deepest.get("battles_won", 0) or 0)
    latest_wins = int(latest.get("battles_won", 0) or 0)
    retry_seed = _next_seed_text(latest_seed)
    if lang == "zh":
        return [
            "DEATH REVIEW BOARD :: 陨落复盘板",
            f"  [SAMPLES] {len(deaths)} 次陨落",
            f"  [LATEST] seed {latest_seed} / {latest_wins}W",
            f"  [DEEPEST] seed {deepest_seed} / {deepest_wins}W",
            f"  [RETRY] ouro run --mock --prompt-style control --seed {retry_seed}",
        ]
    return [
        "DEATH REVIEW BOARD",
        f"  [SAMPLES] {len(deaths)} fallen runs",
        f"  [LATEST] seed {latest_seed} / {latest_wins}W",
        f"  [DEEPEST] seed {deepest_seed} / {deepest_wins}W",
        f"  [RETRY] ouro run --mock --prompt-style control --seed {retry_seed}",
    ]


def _next_seed_text(seed: str) -> str:
    try:
        return str(int(seed) + 1)
    except (TypeError, ValueError):
        return "7"


def render_run_archives(
    archives: list[dict],
    bundle: ContentBundle,
    *,
    language: str = DEFAULT_LANGUAGE,
    limit: int = 10,
) -> str:
    """Render durable run archives as a player-facing run log."""
    lang = language
    title = "RUN ARCHIVE :: ALL RUNS" if lang == "en" else "运行归档 :: 全部记录"
    empty = "No run archives recorded yet." if lang == "en" else "尚无运行归档。"
    shown = archives[: max(0, limit)]

    lines = [title, ""]
    lines.append(f"Total: {len(archives)}" if lang == "en" else f"总计: {len(archives)}")
    lines.append(f"Showing: {len(shown)}" if lang == "en" else f"显示: {len(shown)}")
    lines.append("")

    if not shown:
        lines.append(empty)
        return "\n".join(lines)

    lines.extend(_render_run_archive_board(shown, lang=lang))
    lines.append("")

    for index, entry in enumerate(shown, start=1):
        run_id = str(entry.get("run_id", "-"))
        seed = str(entry.get("seed", "-"))
        result = str(entry.get("result", entry.get("battle_result", "-")))
        phase = str(entry.get("phase", "-"))
        hero_id = str(entry.get("hero_id", "-"))
        dungeon_id = str(entry.get("dungeon_id", "-"))
        wins = int(entry.get("battles_won", 0) or 0)
        losses = int(entry.get("battles_lost", 0) or 0)
        gold = int(entry.get("gold", 0) or 0)
        xp = int(entry.get("xp", 0) or 0)
        current_hp = int(entry.get("current_hp", 0) or 0)
        max_hp = int(entry.get("max_hp", 0) or 0)
        current_mp = int(entry.get("current_mp", 0) or 0)
        max_mp = int(entry.get("max_mp", 0) or 0)
        node_ids = list(entry.get("completed_node_ids", []) or [])
        build = entry.get("build", {}) if isinstance(entry.get("build", {}), dict) else {}

        hero = bundle.heroes.get(hero_id)
        dungeon = bundle.dungeons.get(dungeon_id)
        hero_name = (
            hero.display_name.get(lang) or hero.display_name.get("en", hero_id)
            if hero is not None else hero_id
        )
        dungeon_name = (
            dungeon.display_name.get(lang) or dungeon.display_name.get("en", dungeon_id)
            if dungeon is not None else dungeon_id
        )
        build_name = str(build.get("archetype", "-"))
        build_badge = str(build.get("stage_badge", ""))

        lines.append(f"[{index}] {run_id}")
        lines.append(f"  Seed: {seed}  Result: {result}  Phase: {phase}")
        lines.append(f"  Hero: {hero_name}  Dungeon: {dungeon_name}")
        lines.append(f"  Battles: {wins}W/{losses}L  Nodes: {len(node_ids)}  Gold: {gold}  XP: {xp}")
        lines.append(f"  Resources: HP {current_hp}/{max_hp}  MP {current_mp}/{max_mp}")
        lines.append(f"  Build: {build_name} {build_badge}".rstrip())
        archive_path = entry.get("_archive_path")
        if archive_path:
            lines.append(f"  Archive: {archive_path}")
        lines.append("")

    return "\n".join(lines).rstrip()


def _render_run_archive_board(archives: list[dict], *, lang: str) -> list[str]:
    complete = sum(1 for entry in archives if str(entry.get("result", "")) == "complete")
    dead = sum(1 for entry in archives if str(entry.get("result", "")) == "dead")
    best = max(archives, key=lambda entry: int(entry.get("battles_won", 0) or 0))
    latest = archives[0]
    best_seed = str(best.get("seed", "-"))
    latest_seed = str(latest.get("seed", "-"))
    best_wins = int(best.get("battles_won", 0) or 0)
    best_losses = int(best.get("battles_lost", 0) or 0)
    latest_result = str(latest.get("result", latest.get("battle_result", "-")))
    latest_path = str(latest.get("_archive_path", "-"))
    if lang == "zh":
        return [
            "RUN ARCHIVE BOARD :: 运行归档面板",
            f"  [RESULTS] 通关 {complete} / 阵亡 {dead}",
            f"  [BEST] seed {best_seed} / {best_wins}W/{best_losses}L",
            f"  [LATEST] seed {latest_seed} / {latest_result}",
            f"  [REPORT] ouro run-report {latest_path}",
        ]
    return [
        "RUN ARCHIVE BOARD",
        f"  [RESULTS] complete {complete} / dead {dead}",
        f"  [BEST] seed {best_seed} / {best_wins}W/{best_losses}L",
        f"  [LATEST] seed {latest_seed} / {latest_result}",
        f"  [REPORT] ouro run-report {latest_path}",
    ]


def render_run_report(
    entry: dict | None,
    bundle: ContentBundle,
    *,
    language: str = DEFAULT_LANGUAGE,
    width: int = 100,
) -> str:
    """Render one compact run archive report for post-run review."""
    lang = language
    width = max(72, width)
    title = "RUN REPORT :: LAST ECHO" if lang == "en" else "运行报告 :: 最近回响"

    if entry is None:
        body = (
            [
                "No saved run archive yet.",
                "Start: ouro run --mock --seed 7",
                "After battle: ouro run-report --lang en",
            ]
            if lang == "en"
            else [
                "尚无运行归档。",
                "开始：ouro run --mock --seed 7",
                "打完后：ouro run-report --lang zh",
            ]
        )
        panel_title = "NO ARCHIVE" if lang == "en" else "无归档"
        return "\n".join(
            [
                pixel_rule(title, width, tone="hero"),
                *pixel_panel(panel_title, body, width, tone="quiet").lines,
            ]
        )

    summary_title = "SUMMARY" if lang == "en" else "总览"
    build_title = "BUILD" if lang == "en" else "构筑"
    route_title = "ROUTE" if lang == "en" else "路线"
    progress_title = "PROGRESSION" if lang == "en" else "进度"
    loadout_title = "NEXT RUN LOADOUT" if lang == "en" else "下一局配置"
    next_title = "NEXT RUN" if lang == "en" else "下一局"
    panels = [
        pixel_rule(title, width, tone="hero"),
        *pixel_panel(
            summary_title,
            _run_report_summary(entry, bundle, lang),
            width,
            tone="hero",
        ).lines,
        *pixel_panel(
            build_title,
            _run_report_build(entry, lang),
            width,
            tone="normal",
        ).lines,
        *pixel_panel(
            route_title,
            _run_report_route(entry, bundle, lang),
            width,
            tone="quiet",
        ).lines,
        *pixel_panel(
            progress_title,
            _run_report_progress(entry, bundle, lang),
            width,
            tone="counter",
        ).lines,
        *pixel_panel(
            loadout_title,
            _run_report_next_loadout(entry, bundle, lang),
            width,
            tone="climax",
        ).lines,
        *pixel_panel(
            next_title,
            _run_report_next(entry, lang),
            width,
            tone="climax",
        ).lines,
    ]
    return "\n".join(panels)


def _run_report_summary(entry: dict, bundle: ContentBundle, lang: str) -> list[str]:
    run_id = str(entry.get("run_id", "-"))
    seed = str(entry.get("seed", "-"))
    result = str(entry.get("result", entry.get("battle_result", "-")))
    phase = str(entry.get("phase", "-"))
    hero_id = str(entry.get("hero_id", "-"))
    dungeon_id = str(entry.get("dungeon_id", "-"))
    wins = int(entry.get("battles_won", 0) or 0)
    losses = int(entry.get("battles_lost", 0) or 0)
    gold = int(entry.get("gold", 0) or 0)
    xp = int(entry.get("xp", 0) or 0)
    current_hp = int(entry.get("current_hp", 0) or 0)
    max_hp = int(entry.get("max_hp", 0) or 0)
    current_mp = int(entry.get("current_mp", 0) or 0)
    max_mp = int(entry.get("max_mp", 0) or 0)
    node_ids = list(entry.get("completed_node_ids", []) or [])
    floor = int(entry.get("current_floor_index", 0) or 0) + 1
    hero_name = _run_report_hero_name(bundle, hero_id, lang)
    dungeon_name = _run_report_dungeon_name(bundle, dungeon_id, lang)

    if lang == "zh":
        return [
            f"Run: {run_id}",
            f"Seed: {seed}  结果: {result}  阶段: {phase}",
            f"英雄: {hero_name}  副本: {dungeon_name}",
            f"战斗: {wins}胜/{losses}败  到达层: {floor}  节点: {len(node_ids)}",
            f"资源: HP {current_hp}/{max_hp}  MP {current_mp}/{max_mp}  Gold {gold}  XP {xp}",
        ]
    return [
        f"Run: {run_id}",
        f"Seed: {seed}  Result: {result}  Phase: {phase}",
        f"Hero: {hero_name}  Dungeon: {dungeon_name}",
        f"Battles: {wins}W/{losses}L  Floor reached: {floor}  Nodes: {len(node_ids)}",
        f"Resources: HP {current_hp}/{max_hp}  MP {current_mp}/{max_mp}  Gold {gold}  XP {xp}",
    ]


def _run_report_build(entry: dict, lang: str) -> list[str]:
    build = entry.get("build", {}) if isinstance(entry.get("build", {}), dict) else {}
    archetype = str(build.get("archetype", "-"))
    stage = str(build.get("stage", "-"))
    badge = str(build.get("stage_badge", ""))
    tags = _run_report_join(build.get("tags", []), fallback="-")
    resonances = _run_report_join(build.get("active_resonances", []), fallback="-")
    style = str(entry.get("strategy_style") or "-")

    if lang == "zh":
        return [
            f"原型: {archetype} {badge}".rstrip(),
            f"阶段: {stage}  Prompt: {style}",
            f"标签: {tags}",
            f"共鸣: {resonances}",
        ]
    return [
        f"Archetype: {archetype} {badge}".rstrip(),
        f"Stage: {stage}  Prompt: {style}",
        f"Tags: {tags}",
        f"Resonances: {resonances}",
    ]


def _run_report_route(
    entry: dict,
    bundle: ContentBundle,
    lang: str,
) -> list[str]:
    node_ids = [str(item) for item in list(entry.get("completed_node_ids", []) or [])]
    path = _run_report_path(node_ids, bundle, lang)
    scout_notes = [str(item) for item in list(entry.get("scout_notes", []) or [])]
    archive_path = str(entry.get("_archive_path") or "-")

    if lang == "zh":
        lines = [f"Path: {path}", f"Archive: {archive_path}"]
        if scout_notes:
            lines.append(f"Scout: {_run_report_join(scout_notes[:3], fallback='-')}")
        return lines
    lines = [f"Path: {path}", f"Archive: {archive_path}"]
    if scout_notes:
        lines.append(f"Scout: {_run_report_join(scout_notes[:3], fallback='-')}")
    return lines


def _run_report_progress(entry: dict, bundle: ContentBundle, lang: str) -> list[str]:
    codex_raw = entry.get("codex", {})
    codex_progress = (
        CodexProgress.from_dict(codex_raw)
        if isinstance(codex_raw, dict)
        else CodexProgress()
    )
    counts = _codex_summary_counts(bundle, codex_progress)
    earned_gold = int(entry.get("earned_gold_total", 0) or 0)
    earned_xp = int(entry.get("earned_xp_total", 0) or 0)
    if lang == "zh":
        return [
            (
                "Codex: "
                f"Observed {counts['observed']}/{counts['total']}  "
                f"Familiar {counts['familiar']}/{counts['total']}  "
                f"Mastered {counts['mastered']}/{counts['total']}"
            ),
            f"Earned: Gold {earned_gold}  XP {earned_xp}",
        ]
    return [
        (
            "Codex: "
            f"Observed {counts['observed']}/{counts['total']}  "
            f"Familiar {counts['familiar']}/{counts['total']}  "
            f"Mastered {counts['mastered']}/{counts['total']}"
        ),
        f"Earned: Gold {earned_gold}  XP {earned_xp}",
    ]


def _run_report_next_loadout(entry: dict, bundle: ContentBundle, lang: str) -> list[str]:
    result = str(entry.get("result", entry.get("battle_result", ""))).lower()
    phase = str(entry.get("phase", "")).lower()
    seed = _status_seed_int(entry)
    next_seed = seed + 1 if seed is not None else 7
    codex_raw = entry.get("codex", {})
    codex_progress = (
        CodexProgress.from_dict(codex_raw)
        if isinstance(codex_raw, dict)
        else CodexProgress()
    )
    counts = _codex_summary_counts(bundle, codex_progress)
    codex_gap = max(0, counts["total"] - counts["observed"])

    if result == "dead" or phase == "dead":
        if lang == "zh":
            return [
                "[PROMPT] control / 降低 Boss 前节奏风险",
                f"[SEED] {next_seed} / 固定样本复验",
                f"[CODEX] 补 {codex_gap} 个观察缺口",
                "[ROUTE] Boss 前优先 rest/shop",
            ]
        return [
            "[PROMPT] control / reduce boss tempo risk",
            f"[SEED] {next_seed} / fixed retry sample",
            f"[CODEX] patch {codex_gap} observation gaps",
            "[ROUTE] rest/shop before boss pressure",
        ]

    if result == "complete" or phase == "complete":
        if lang == "zh":
            return [
                "[PROMPT] guarded / 提高压力验证稳定性",
                f"[SEED] {next_seed} / 压力样本",
                "[CODEX] 比较通关构筑",
                "[ROUTE] 尝试精英或事件高收益线",
            ]
        return [
            "[PROMPT] guarded / validate under higher pressure",
            f"[SEED] {next_seed} / pressure sample",
            "[CODEX] compare winning build",
            "[ROUTE] try elite or event greed line",
        ]

    if lang == "zh":
        return [
            "[PROMPT] current / 保持变量",
            f"[SEED] {next_seed} / 补完整样本",
            f"[CODEX] 补 {codex_gap} 个观察缺口",
            "[ROUTE] 完成一局再复盘",
        ]
    return [
        "[PROMPT] current / keep variables stable",
        f"[SEED] {next_seed} / complete sample",
        f"[CODEX] patch {codex_gap} observation gaps",
        "[ROUTE] finish one run before tuning",
    ]


def _run_report_next(entry: dict, lang: str) -> list[str]:
    result = str(entry.get("result", entry.get("battle_result", ""))).lower()
    phase = str(entry.get("phase", "")).lower()
    seed = _status_seed_int(entry)
    next_seed = seed + 1 if seed is not None else 7
    wins = int(entry.get("battles_won", 0) or 0)

    if result == "dead" or phase == "dead":
        if lang == "zh":
            return [
                f"结论: {wins} 胜后陨落，下一局先降低节奏风险。",
                f"Retry: ouro run --mock --prompt-style control --seed {next_seed}",
                "Review: ouro history --lang zh --limit 3",
            ]
        return [
            f"Takeaway: fell after {wins} wins; reduce tempo risk before the boss.",
            f"Retry: ouro run --mock --prompt-style control --seed {next_seed}",
            "Review: ouro history --lang en --limit 3",
        ]

    if result == "complete" or phase == "complete":
        if lang == "zh":
            return [
                "结论: 通关构筑成立，下一步提高压力种子验证稳定性。",
                f"Pressure: ouro run --mock --prompt-style guarded --seed {next_seed}",
                "Compare: ouro runs --lang zh --limit 5",
            ]
        return [
            "Takeaway: clear confirmed; compare this build before raising pressure.",
            f"Pressure: ouro run --mock --prompt-style guarded --seed {next_seed}",
            "Compare: ouro runs --lang en --limit 5",
        ]

    if lang == "zh":
        return [
            "结论: 归档未形成最终胜负，建议用固定 seed 重跑完整样本。",
            f"Retry: ouro run --mock --seed {next_seed}",
            "List: ouro runs --lang zh --limit 5",
        ]
    return [
        "Takeaway: archive has no final result; rerun a fixed mock sample.",
        f"Retry: ouro run --mock --seed {next_seed}",
        "List: ouro runs --lang en --limit 5",
    ]


def _run_report_path(
    node_ids: list[str],
    bundle: ContentBundle,
    lang: str,
) -> str:
    if not node_ids:
        return "no completed nodes" if lang == "en" else "尚无完成节点"
    names: list[str] = []
    for node_id in node_ids[:5]:
        node = bundle.nodes.get(node_id)
        names.append(
            node.display_name.get(lang) or node.display_name.get("en", node_id)
            if node is not None else node_id
        )
    extra = len(node_ids) - len(names)
    rendered = " -> ".join(names)
    if extra > 0:
        rendered += f" -> +{extra}"
    return rendered


def _run_report_hero_name(bundle: ContentBundle, hero_id: str, lang: str) -> str:
    hero = bundle.heroes.get(hero_id)
    return (
        hero.display_name.get(lang) or hero.display_name.get("en", hero_id)
        if hero is not None else hero_id
    )


def _run_report_dungeon_name(bundle: ContentBundle, dungeon_id: str, lang: str) -> str:
    dungeon = bundle.dungeons.get(dungeon_id)
    return (
        dungeon.display_name.get(lang) or dungeon.display_name.get("en", dungeon_id)
        if dungeon is not None else dungeon_id
    )


def _run_report_join(raw: object, *, fallback: str) -> str:
    if not isinstance(raw, list) or not raw:
        return fallback
    values = [str(item) for item in raw if str(item)]
    return ", ".join(values[:6]) if values else fallback


def render_context_window(
    context: ContextProgress | None = None,
    *,
    lang: str = DEFAULT_LANGUAGE,
) -> str:
    """Render context window progression card.

    Args:
        context: The context progress to render, or None for default
        lang: Language for display labels ("en" or "zh")

    Returns:
        Formatted context window display string
    """
    if context is None:
        context = ContextProgress()

    lines: list[str] = []

    width = 56
    title = "CONTEXT WINDOW" if lang == "en" else "上下文窗口"
    lines.append("+" + "-" * (width - 2) + "+")
    lines.append("| " + pad_right(title, width - 4) + " |")
    lines.append("+" + "-" * (width - 2) + "+")

    level_label = context_level_label(context.level, lang)
    xp_line = (
        f"XP: {context.xp}" if lang == "en"
        else f"经验: {context.xp}"
    )
    if context.is_max_level:
        next_line = "MAX LEVEL" if lang == "en" else "已满级"
    else:
        next_line = (
            f"Next: {context.xp_for_next_level} XP -> {context.next_level_reward}"
            if lang == "en"
            else f"下次升级: 还需 {context.xp_for_next_level} 经验 -> {context.next_level_reward}"
        )

    lines.append(f"| {pad_right(f'{level_label} | {xp_line}', width - 4)} |")
    lines.append("+" + "-" * (width - 2) + "+")

    strategy_label = context_slot_label("strategy", lang)
    codex_label = context_slot_label("codex", lang)
    memory_label = context_slot_label("memory", lang)
    prompt_edit_label = context_slot_label("prompt_edit", lang)
    build_hint_label = context_slot_label("build_hint", lang)

    max_strategy = 3
    max_codex = 2
    max_memory = 500
    max_prompt_edit = 2
    max_build_hint = 2

    lines.append(f"| {pad_right(f'{strategy_label}: {context.strategy_slots}/{max_strategy}', width - 4)} |")
    lines.append(f"| {pad_right(f'{codex_label}: {context.codex_slots}/{max_codex}', width - 4)} |")
    lines.append(f"| {pad_right(f'{memory_label}: {context.memory_echo}/{max_memory}', width - 4)} |")
    lines.append(f"| {pad_right(f'{prompt_edit_label}: {context.prompt_edit_budget}/{max_prompt_edit}', width - 4)} |")
    lines.append(f"| {pad_right(f'{build_hint_label}: {context.build_hint_slots}/{max_build_hint}', width - 4)} |")
    lines.append("+" + "-" * (width - 2) + "+")
    lines.extend(_render_context_growth_board(context, lang=lang, width=width))
    lines.append("+" + "-" * (width - 2) + "+")

    lines.append(f"| {pad_right(next_line, width - 4)} |")
    lines.append("+" + "-" * (width - 2) + "+")

    return "\n".join(lines)


def _render_context_growth_board(context: ContextProgress, *, lang: str, width: int) -> list[str]:
    inner = width - 4
    if context.is_max_level:
        progress = "MAX" if lang == "en" else "已满"
    else:
        next_threshold = context.xp + context.xp_for_next_level
        progress = f"{context.xp}/{next_threshold} XP"
    if lang == "zh":
        rows = [
            "CONTEXT GROWTH BOARD :: Agent 记忆成长",
            f"  [LEVEL] {context_level_label(context.level, lang)} / {progress}",
            f"  [NEXT] {context.next_level_reward}",
            f"  [STRATEGY] {context.strategy_slots} 槽 / 驾驶模式与路线策略",
            f"  [CODEX] {context.codex_slots} 槽 / 怪物知识注入",
            f"  [MEMORY] {context.memory_echo} Echo / 长期战斗记忆",
            f"  [PROMPT] {context.prompt_edit_budget} 次 / 局内 Prompt 修正",
            f"  [BUILD] {context.build_hint_slots} 槽 / 构筑提示",
        ]
    else:
        rows = [
            "CONTEXT GROWTH BOARD",
            f"  [LEVEL] {context_level_label(context.level, lang)} / {progress}",
            f"  [NEXT] {context.next_level_reward}",
            f"  [STRATEGY] {context.strategy_slots} slot(s) / pilot and route plans",
            f"  [CODEX] {context.codex_slots} slot(s) / monster intel injected",
            f"  [MEMORY] {context.memory_echo} Echo / long-run battle memory",
            f"  [PROMPT] {context.prompt_edit_budget} edit(s) / mid-run prompt repair",
            f"  [BUILD] {context.build_hint_slots} slot(s) / build hint feed",
        ]
    return [f"| {pad_right(fit_text(row, inner), inner)} |" for row in rows]
