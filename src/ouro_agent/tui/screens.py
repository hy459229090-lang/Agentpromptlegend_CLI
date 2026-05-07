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

from ouro_agent.art.glyphs import bar, hp_bar, mp_bar, atb_bar, status_indicator
from ouro_agent.content import ContentBundle, HeroData
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
)
from ouro_agent.engine.models import BattleState, Enemy, Hero
from ouro_agent.i18n import DEFAULT_LANGUAGE, label, pad_right
from ouro_agent.llm.prompt import PROMPT_STYLE_TEMPLATES, prompt_style_text
from ouro_agent.sessions import RunPhase


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
                enhanced_bars=enhanced_bars,
            )
        )
    else:
        lines.extend(
            _render_duel_panel(
                state,
                last_record,
                lang=lang,
                unicode_mode=unicode_mode,
                enhanced_bars=enhanced_bars,
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
    enhanced_bars: bool = False,
) -> list[str]:
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
    return [
        f"HP {hp_str}{down}",
        f"ATB {atb_str}{charge}",
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


def _actor_pose(actor_id: str, record: TurnRecord | None) -> str:
    """Determine the appropriate pose for an actor based on the turn record.
    
    Returns:
        A pose string like "idle", "attack", "skill_shadow", "defend", "hit", etc.
    """
    if record is None:
        return "idle"
    
    # Check if this actor is being hit
    if record.action and actor_id in record.action.targets:
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
    """Generate the hero sprite based on current pose and state.
    
    Supports multiple poses: idle, attack, skill_shadow, skill_fire, 
    skill_physical, skill_holy, skill_poison, skill, defend, observe, hit, low.
    """
    state = _actor_pose(hero.id, record)
    
    # Check for low HP state (overrides other poses except hit and death)
    if hero.hp / max(1, hero.max_hp) < 0.3 and state not in ("hit", "death"):
        state = "low"
    
    sprites = {
        "hero_shadow_apprentice": {
            "idle": ["  .^.", " /|c|\\", "  / \\", " candle low"],
            "attack": ["  .^.", " /|c|-->", "  / \\", " candle thrust"],
            "skill_shadow": ["  .^.", " /|c|==*", "  / \\", " shadow burst"],
            "skill_fire": ["  .^.", " /|c|=#*", "  / \\", " flame erupt"],
            "skill_physical": ["  .^.", " /|c|-->", "  / \\", " quick strike"],
            "skill_holy": ["  .^.", " /|c|=+*", "  / \\", " light burst"],
            "skill_poison": ["  .^.", " /|c|=~*", "  / \\", " venom spray"],
            "skill": ["  .^.", " /|c|==*", "  / \\", " candle raised"],
            "defend": ["  .^.", " /|c|\\", "  / \\", " candle guard"],
            "observe": ["  .^.", " /|c|\\", "  / \\", " scanning..."],
            "hit": ["  .x.", " /|c", "  /\\", " flame bends"],
            "low": ["  .^.", " /|c|\\", "  / \\", " candle guttering"],
        },
        "hero_ash_guardian": {
            "idle": ["   O", "  /#\\", "  / \\", " shield set"],
            "attack": ["   O", "  /#\\->", "  / \\", " shield bash"],
            "skill_shadow": ["   O", "  [\\#\\", "  / \\", " dark guard"],
            "skill_fire": ["   O", "  [#]*", "  / \\", " ember burst"],
            "skill_physical": ["   O", "  /#\\->", "  / \\", " heavy strike"],
            "skill_holy": ["   O", "  [+#]", "  / \\", " light ward"],
            "skill_poison": ["   O", "  [~#]", "  / \\", " toxic shield"],
            "skill": ["   O", "  [#]", "  / \\", " guard raised"],
            "defend": ["   O", "  [#]", "  / \\", " block stance"],
            "observe": ["   O", "  /#\\", "  / \\", " assessing..."],
            "hit": ["   o", "  /#\\!", "  / \\", " ash cracks"],
            "low": ["   o", "  [#]", "  / \\", " shield low"],
        },
        "hero_broken_string_hunter": {
            "idle": ["   o", "  /|\\", "  /->", " string drawn"],
            "attack": ["   o", "  /|\\", "  /==>", " bolt loosed"],
            "skill_shadow": ["   o", "  /|\\", "  /==>", " shadow bolt"],
            "skill_fire": ["   o", "  /|\\", "  /==>*", " fire arrow"],
            "skill_physical": ["   o", "  /|\\", "  /==>", " pierce shot"],
            "skill_holy": ["   o", "  /|\\", "  /==>+", " light arrow"],
            "skill_poison": ["   o", "  /|\\", "  /==>~", " poison bolt"],
            "skill": ["   o", "  /|\\", "  /==>", " bolt loosed"],
            "defend": ["   o", "  /|\\", "  /->", " dodge stance"],
            "observe": ["   o", "  /|\\", "  /->", " aiming..."],
            "hit": ["   x", "  /|", "  /\\", " string snaps"],
            "low": ["   o", "  /|", "  /->", " breathing hard"],
        },
        "hero_mire_oracle": {
            "idle": ["  .-.", " (v v)", " /|~|\\", " vial low"],
            "attack": ["  .-.", " (v v)-->", " /| |\\", " vial strike"],
            "skill_shadow": ["  .-.", " (v v)==", " /| |\\", " dark mist"],
            "skill_fire": ["  .-.", " (v v)=*", " /| |\\", " flame vial"],
            "skill_physical": ["  .-.", " (v v)-->", " /| |\\", " quick jab"],
            "skill_holy": ["  .-.", " (v v)=+", " /| |\\", " holy mist"],
            "skill_poison": ["  .-.", " (v v)=~", " /| |\\", " poison cloud"],
            "skill": ["  .-.", " (v v)==", " /| |\\", " vial cracked"],
            "defend": ["  .-.", " (v v)", " /|~|\\", " mist shield"],
            "observe": ["  .-.", " (v v)", " /|~|\\", " scrying..."],
            "hit": ["  .x.", " (v v)", " /|", " veil torn"],
            "low": ["  .-.", " (v v)", " /|~", " mire rising"],
        },
        "hero_gravewright": {
            "idle": ["  [o]", " /|n|\\", "  / \\", " crate set"],
            "attack": ["  [o]", " /|n|-->", "  / \\", " crank strike"],
            "skill_shadow": ["  [o]", " /|n|==", "  / \\", " dark gears"],
            "skill_fire": ["  [o]", " /|n|=*", "  / \\", " engine burst"],
            "skill_physical": ["  [o]", " /|n|-->", "  / \\", " nail strike"],
            "skill_holy": ["  [o]", " /|n|=+", "  / \\", " sanctified"],
            "skill_poison": ["  [o]", " /|n|=~", "  / \\", " toxic nails"],
            "skill": ["  [o]", " /|n|==", "  / \\", " crank turns"],
            "defend": ["  [o]", " /|n|\\", "  / \\", " crate shield"],
            "observe": ["  [o]", " /|n|\\", "  / \\", " inspecting..."],
            "hit": ["  [x]", " /|n|!", "  / \\", " gears skip"],
            "low": ["  [o]", " /|n|", "  / \\", " crate smoking"],
        },
        "hero_echo_exile": {
            "idle": ["  o)o", " /| |\\", "  / \\", " bell quiet"],
            "attack": ["  o)o-->", " /| |\\", "  / \\", " bell strike"],
            "skill_shadow": ["  o)o==", " /| |\\", "  / \\", " dark echo"],
            "skill_fire": ["  o)o=*", " /| |\\", "  / \\", " flame chime"],
            "skill_physical": ["  o)o-->", " /| |\\", "  / \\", " bell jab"],
            "skill_holy": ["  o)o=+", " /| |\\", "  / \\", " holy ring"],
            "skill_poison": ["  o)o=~", " /| |\\", "  / \\", " toxic chime"],
            "skill": ["  o)o==", " /| |\\", "  / \\", " bell rings"],
            "defend": ["  o)o", " /| |\\", "  / \\", " echo ward"],
            "observe": ["  o)o", " /| |\\", "  / \\", " listening..."],
            "hit": ["  x)o", " /| |", "  /\\", " echo cracks"],
            "low": ["  o)o", " /| |", "  / \\", " hymn thin"],
        },
    }
    
    default_sprite = ["  ???", " /|?|\\", "  / \\", " unknown"]
    
    # Try to get the sprite for the current pose
    hero_sprites = sprites.get(hero.id, sprites["hero_shadow_apprentice"])
    if state in hero_sprites:
        return hero_sprites[state]
    
    # Fallback to cast or idle
    if "cast" in hero_sprites:
        return hero_sprites["cast"]
    return hero_sprites.get("idle", default_sprite)


def _enemy_sprite(enemy: Enemy, record: TurnRecord | None) -> list[str]:
    """Generate the enemy sprite based on current pose and state.
    
    Supports multiple poses: idle, attack, skill, defend, hit, low, death.
    """
    state = _actor_pose(enemy.id, record)
    
    # Check for death state
    if not enemy.is_alive:
        state = "death"
    # Check for low HP state
    elif enemy.hp / max(1, enemy.max_hp) < 0.3 and state not in ("hit", "death"):
        state = "low"
    
    sprites = {
        "c": {  # hungry cultist
            "idle": ["  (c)", "  /|\\", "  / \\", " hungry"],
            "attack": ["  (c)-->", "  /|\\", "  / \\", " knife lunge"],
            "skill": ["  (c)==", "  /|\\", "  / \\", " chant"],
            "defend": ["  (c)", "  /|\\", "  / \\", " cower"],
            "hit": ["  (x)", "  /|!", "  / \\", " staggered"],
            "low": ["  (c)", "  /|\\", "  / \\", " weak"],
            "death": ["   .", "  /_\\", "  ash", ""],
        },
        "k": {  # black candle acolyte
            "idle": ["  (k)", " /|w|\\", "  / \\", " chanting"],
            "attack": ["  (k)-->", " /|w|\\", "  / \\", " ritual strike"],
            "skill": ["  (k*", " /|w|\\", "  / \\", " wick bright"],
            "defend": ["  (k)", " /|w|\\", "  / \\", " ward cast"],
            "hit": ["  (k)", " /|w|!", "  / \\", " chant bent"],
            "low": ["  (k)", " /|w|\\", "  / \\", " flame dim"],
            "death": ["   .", "  /_\\", " wick ash", ""],
        },
    }
    
    default_sprite = ["  (?)", "  /|\\", "  / \\", " ???"]
    
    # Try to get the sprite for the current pose
    enemy_sprites = sprites.get(enemy.short_glyph, sprites["c"])
    if state in enemy_sprites:
        return enemy_sprites[state]
    
    # Fallback to cast or idle
    if "cast" in enemy_sprites:
        return enemy_sprites["cast"]
    return enemy_sprites.get("idle", default_sprite)


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
        build_name = build.archetype(lang) if build else HERO_BUILD_ARCHETYPES.get(hero.id, {}).get(lang, "Unknown")
        risk = build.risk_level() if build else HERO_RISK_LEVELS.get(hero.id, "normal")
        stage_badge = ""
        if build:
            progress = build.calculate_progress(bundle)
            stage_badge = f" {progress.stage.badge}"
        lines.append(f"[{idx}] {name}  {hero.short_tag}  {cls}{stage_badge}")
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
    build_name = build.archetype(lang)
    risk = build.risk_level()
    strategy = build.strategy_lines(lang)
    weapon, build_icon = _hero_card_icons(hero.id)

    progress = build.calculate_progress(bundle)

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
    lines.append(f"Build: {build_name} {progress.stage.badge}")
    lines.append(f"Weapon: {weapon}")
    lines.append(f"Risk: {risk}")
    lines.append(f"{label('hero_card_tags', lang)}: {tags}")
    lines.append(f"{label('hero_card_stats', lang)}: {stats}")
    lines.append("")

    lines.extend(_render_build_progress_panel(progress, hero.id, lang))
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


def _render_build_progress_panel(
    progress: BuildProgress, hero_id: str, lang: str
) -> list[str]:
    lines: list[str] = []

    stage_label = {
        "en": f"BUILD STAGE: {progress.stage_name}",
        "zh": f"构筑阶段: {progress.stage_name}",
    }.get(lang, f"BUILD STAGE: {progress.stage_name}")

    lines.append(f"{stage_label} {progress.stage.badge}")
    lines.append("")

    lines.append("Core Tags:")
    core_tags = HERO_CORE_TAGS.get(hero_id, [])
    for tag in core_tags:
        count = progress.core_tags.get(tag, 0)
        filled = min(count, 3)
        bar_str = "[" + "#" * filled + "-" * (3 - filled) + "]"
        status = "online" if count >= 2 else "active" if count >= 1 else "need"
        lines.append(f"  {tag:12} {bar_str} {count}/3  {status}")

    if progress.active_resonances:
        lines.append("")
        lines.append("Active Resonances:")
        for res_id in progress.active_resonances:
            lines.append(f"  [R] {res_id}")

    if progress.near_resonances:
        lines.append("")
        lines.append("Near Resonances:")
        for near in progress.near_resonances:
            name = near["display_name"].get(lang) or near["display_name"].get("en", near["id"])
            missing_parts = []
            for miss in near["missing"]:
                need_more = miss["need"] - miss["have"]
                missing_parts.append(f"{miss['tag']} +{need_more}")
            missing_str = ", ".join(missing_parts)
            lines.append(f"  [ ] {name}  need: {missing_str}")

    if progress.best_next_picks:
        lines.append("")
        lines.append("Best Next Picks:")
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
    return {
        "hero_shadow_apprentice": ("[W:STF] c==*", "[ONLINE]"),
        "hero_ash_guardian": ("[W:SHD] [#]", "[PAIR]"),
        "hero_broken_string_hunter": ("[W:XBW] ==>", "[PAIR]"),
        "hero_mire_oracle": ("[W:VIL] (v)", "[SEED]"),
        "hero_gravewright": ("[W:GER] [o]", "[SEED]"),
        "hero_echo_exile": ("[W:BEL] )o(", "[SEED]"),
    }.get(hero_id, ("[W:???]", "[SEED]"))


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
    lines.append("")
    
    # Available nodes
    for display_idx, (node_idx, node) in enumerate(available, start=1):
        name = node.display_name.get(lang) or node.display_name.get("en", node.id)
        node_type = _node_type_label(node.node_type, lang)
        risk = _risk_level_label(node.risk_level, lang)
        
        lines.append(f"[{display_idx}] {name}")
        lines.append(f"    {node_type}")
        if risk:
            lines.append(f"    {risk}")
        
        # Show enemies for combat nodes
        if node.node_type in ("normal_combat", "elite_combat", "boss", "mimic_chest"):
            if node.enemy_ids:
                enemy_names = []
                for eid in node.enemy_ids:
                    if eid in bundle.enemies:
                        enemy = bundle.enemies[eid]
                        enemy_names.append(enemy.display_name.get(lang) or enemy.display_name.get("en", eid))
                    else:
                        enemy_names.append(eid)
                lines.append(f"    Enemies: {', '.join(enemy_names)}")
        
        # Show rewards
        if node.rewards:
            reward_parts = []
            if node.rewards.gold:
                reward_parts.append(f"{node.rewards.gold}g")
            if node.rewards.xp:
                reward_parts.append(f"{node.rewards.xp}xp")
            if reward_parts:
                lines.append(f"    Rewards: {', '.join(reward_parts)}")
        
        lines.append("")
    
    # Prompt
    lines.append(label("route_choice_prompt", lang))
    
    return "\n".join(lines)


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
        
        lines.append(f"[{idx}] {type_label}")
        
        if choice_type == "item" and choice.item_id:
            if choice.item_id in bundle.items:
                item = bundle.items[choice.item_id]
                name = item.display_name.get(lang) or item.display_name.get("en", choice.item_id)
                lines.append(f"    {name} [{item.tier}]")
                desc = item.description.get(lang) or item.description.get("en", "")
                if desc:
                    lines.append(f"    {desc}")
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
                        lines.append(f"    {', '.join(mods)}")
            else:
                lines.append(f"    {choice.item_id}")
        
        elif choice_type == "affix" and choice.affix_id:
            if choice.affix_id in bundle.affixes:
                affix = bundle.affixes[choice.affix_id]
                name = affix.display_name.get(lang) or affix.display_name.get("en", choice.affix_id)
                lines.append(f"    {name}")
                desc = affix.description.get(lang) or affix.description.get("en", "")
                if desc:
                    lines.append(f"    {desc}")
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
                        lines.append(f"    {', '.join(mods)}")
            else:
                lines.append(f"    {choice.affix_id}")
        
        elif choice_type == "codex":
            lines.append(f"    +{choice.progress or 1} progress")
        
        elif choice_type == "gold" and choice.gold:
            lines.append(f"    +{choice.gold}g")
        
        elif choice_type == "heal" and choice.heal_percent:
            lines.append(f"    Heal {choice.heal_percent}% HP")
        
        lines.append("")
    
    # Prompt
    lines.append(label("reward_choice_prompt", lang))
    
    return "\n".join(lines)


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
    lines.append("")
    
    # Shop items
    for idx, item in enumerate(items, start=1):
        item_type = item.type
        can_afford = state.can_afford(item)
        price = item.price or 0
        
        lines.append(f"[{idx}] ({price}g) {'[CANNOT AFFORD]' if not can_afford else ''}")
        
        if item_type == "item" and item.item_id:
            if item.item_id in bundle.items:
                bundle_item = bundle.items[item.item_id]
                name = bundle_item.display_name.get(lang) or bundle_item.display_name.get("en", item.item_id)
                lines.append(f"    {name} [{bundle_item.tier}]")
                desc = bundle_item.description.get(lang) or bundle_item.description.get("en", "")
                if desc:
                    lines.append(f"    {desc}")
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
                        lines.append(f"    {', '.join(mods)}")
            else:
                lines.append(f"    {item.item_id}")
        
        elif item_type == "affix" and item.affix_id:
            if item.affix_id in bundle.affixes:
                affix = bundle.affixes[item.affix_id]
                name = affix.display_name.get(lang) or affix.display_name.get("en", item.affix_id)
                lines.append(f"    {name}")
                desc = affix.description.get(lang) or affix.description.get("en", "")
                if desc:
                    lines.append(f"    {desc}")
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
                        lines.append(f"    {', '.join(mods)}")
            else:
                lines.append(f"    {item.affix_id}")
        
        elif item_type == "strategy" and item.strategy_style:
            lines.append(f"    Strategy: {item.strategy_style}")
        
        elif item_type == "heal" and item.heal_percent:
            lines.append(f"    Heal {item.heal_percent}% HP")
        
        lines.append("")
    
    # Prompt
    lines.append(label("shop_prompt", lang))
    
    return "\n".join(lines)


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
    lines.append(f"Run ID: {state.run_id}")
    lines.append(f"Seed: {state.seed}")
    lines.append("")
    
    # Stats
    lines.append(label("run_summary", lang))
    lines.append("")
    lines.append(f"  {label('run_floor', lang)} reached: {state.current_floor_index + 1}")
    lines.append(f"  {label('run_gold', lang)} earned: {state.earned_gold_total}")
    lines.append(f"  {label('run_xp', lang)} earned: {state.earned_xp_total}")
    lines.append(f"  {label('run_battles_won', lang)}: {state.battles_won}")
    lines.append(f"  {label('run_battles_lost', lang)}: {state.battles_lost}")
    lines.append("")
    
    # Completed nodes
    lines.append(f"Nodes completed: {len(state.completed_node_ids)}")
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
    lines.append(f"Final Build: {build.archetype(lang)}")
    progress = build.calculate_progress(bundle)
    lines.append(f"  Stage: {progress.stage.badge} {progress.stage_name}")
    lines.append(f"  Items: {', '.join(i.display_name.get(lang) or i.display_name.get('en', i.id) for i in build.items)}")
    lines.append(f"  Affixes: {', '.join(a.display_name.get(lang) or a.display_name.get('en', a.id) for a in build.affixes)}")
    if build.resonances:
        lines.append(f"  Resonances: {', '.join(r.display_name.get(lang) or r.display_name.get('en', r.id) for r in build.resonances)}")
    
    return "\n".join(lines)


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
    
    lines.append("Rest will provide:")
    if heal_percent > 0:
        heal_amount = int(state.max_hp * heal_percent / 100)
        new_hp = min(state.max_hp, state.current_hp + heal_amount)
        lines.append(f"  {label('rest_heal_amount', lang).format(percent=heal_percent)} ({state.current_hp} -> {new_hp})")
    if restore_full_mp:
        lines.append(f"  {label('rest_mp_restore', lang)} ({state.current_mp} -> {state.max_mp})")
    lines.append("")
    
    lines.append(label("rest_prompt", lang))
    
    return "\n".join(lines)


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
            
            lines.append(f"[{idx}] {choice_name}")
            if choice_desc:
                lines.append(f"    {choice_desc}")
            
            if hasattr(choice, "type"):
                if choice.type == "item" and hasattr(choice, "item_id") and choice.item_id:
                    if choice.item_id in bundle.items:
                        item = bundle.items[choice.item_id]
                        item_name = item.display_name.get(lang) or item.display_name.get("en", choice.item_id)
                        lines.append(f"    Item: {item_name} [{item.tier}]")
                elif choice.type == "affix" and hasattr(choice, "affix_id") and choice.affix_id:
                    if choice.affix_id in bundle.affixes:
                        affix = bundle.affixes[choice.affix_id]
                        affix_name = affix.display_name.get(lang) or affix.display_name.get("en", choice.affix_id)
                        lines.append(f"    Affix: {affix_name}")
                elif choice.type == "gold" and hasattr(choice, "gold") and choice.gold:
                    lines.append(f"    Gold: +{choice.gold}")
                elif choice.type == "heal" and hasattr(choice, "heal_percent") and choice.heal_percent:
                    lines.append(f"    Heal: {choice.heal_percent}% HP")
            
            lines.append("")
    else:
        lines.append("No choices available.")
        lines.append("")
    
    lines.append(label("event_prompt", lang))
    
    return "\n".join(lines)
