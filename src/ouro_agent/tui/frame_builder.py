"""Build display-oriented battle frames from deterministic combat records."""
from __future__ import annotations

from dataclasses import dataclass, field

from ouro_agent.engine.battle import TurnRecord
from ouro_agent.engine.models import BattleState, Enemy, Hero, SkillState, StatusEffect


@dataclass(frozen=True)
class ResourceDelta:
    label: str
    text: str
    severity: str = "info"


@dataclass(frozen=True)
class SessionUsageFrame:
    battle_echo: str
    sealed_echo: str
    fresh_echo: str
    echo_cost: int
    ritual_time_ms: int


@dataclass(frozen=True)
class BossIntel:
    enemy_id: str
    name: str
    phase: str
    charge: str
    break_state: str
    enrage: str


@dataclass(frozen=True)
class BattleFrame:
    frame_id: str
    tick: int
    phase: str
    actor_id: str
    target_ids: tuple[str, ...]
    action_label: str
    judge_label: str
    intent: str
    risk: str
    align: str
    effect_kind: str
    effect_glyph: str
    floating_numbers: tuple[str, ...] = ()
    resource_deltas: tuple[ResourceDelta, ...] = ()
    impact_line: str | None = None
    event_banner: str | None = None
    counter_hint: str | None = None
    counter_clock: str | None = None
    boss_intel: BossIntel | None = None
    session_usage: SessionUsageFrame | None = None


STATUS_SHORT_NAMES: dict[str, tuple[str, str]] = {
    "status_shield": ("SHD", "shield"),
    "status_focus": ("FOC", "focus"),
    "status_haste": ("HST", "haste"),
    "status_guard": ("GRD", "guard"),
    "status_echo_charge": ("ECH", "echo"),
    "status_stealth": ("STL", "stealth"),
    "status_codex_mark": ("CDX", "codex"),
    "status_poison": ("PSN", "poison"),
    "status_bleed": ("BLD", "bleed"),
    "status_corruption": ("CRP", "corrupt"),
    "status_silence": ("SLN", "silence"),
    "status_exposed": ("EXP", "exposed"),
    "status_stagger": ("STG", "stagger"),
    "status_omen": ("OMN", "omen"),
    "status_ember": ("EMB", "ember"),
}


def format_status_short(status: StatusEffect) -> str:
    code, name = _status_display(status.id)
    return f"{code} {name}({status.stacks})"


def format_status_detail(status: StatusEffect) -> str:
    code, name = _status_display(status.id)
    return f"{code} {name} x{status.stacks} / {status.duration}t"


def build_battle_frame(state: BattleState, record: TurnRecord | None) -> BattleFrame:
    if record is None:
        return BattleFrame(
            frame_id=f"tick_{state.tick:04d}_waiting",
            tick=state.tick,
            phase="model_waiting",
            actor_id=state.hero.id,
            target_ids=(),
            action_label="awaiting first action",
            judge_label="WAIT",
            intent="read the field",
            risk="unknown until an action is selected",
            align="Prompt pending",
            effect_kind="wait",
            effect_glyph="...",
            session_usage=None,
        )

    target_ids = _target_ids(record)
    action_label = _action_label(state, record)
    judge_label = _judge_label(record)
    effect_kind, effect_glyph = _effect(record)
    floating = _floating_numbers(record)
    event_banner = _event_banner(state, record)
    deltas = _resource_deltas(state, record)
    intent, risk, align = _intent_risk_align(state, record)
    counter_hint = _counter_hint(state, record)
    counter_clock = _counter_clock(state, record)
    boss_intel = _boss_intel(state, record)
    impact_line = _impact_line(state, record)

    return BattleFrame(
        frame_id=f"tick_{record.tick:04d}_{record.side}_{record.actor_id}",
        tick=record.tick,
        phase=f"{record.side}_action",
        actor_id=record.actor_id,
        target_ids=target_ids,
        action_label=action_label,
        judge_label=judge_label,
        intent=intent,
        risk=risk,
        align=align,
        effect_kind=effect_kind,
        effect_glyph=effect_glyph,
        floating_numbers=floating,
        resource_deltas=deltas,
        impact_line=impact_line,
        event_banner=event_banner,
        counter_hint=counter_hint,
        counter_clock=counter_clock,
        boss_intel=boss_intel,
        session_usage=SessionUsageFrame(
            battle_echo=record.battle_session_id or "-",
            sealed_echo=record.static_context_hash or "-",
            fresh_echo=record.delta_context_id or "-",
            echo_cost=record.usage_total_tokens,
            ritual_time_ms=record.usage_latency_ms,
        ),
    )


def _target_ids(record: TurnRecord) -> tuple[str, ...]:
    if record.action and record.action.targets:
        return tuple(record.action.targets)
    if record.judge and record.judge.target_ids:
        return tuple(record.judge.target_ids)
    return ()


def _action_label(state: BattleState, record: TurnRecord) -> str:
    if record.side == "enemy":
        kind = (record.enemy_action or {}).get("type", "basic_attack")
        actor = _unit_name(state, record.actor_id)
        return f"{actor} {kind}"
    if record.action is None:
        return "action unavailable"
    target = _target_display(state, record.action.targets)
    if record.action.type == "cast_skill" and record.action.skill_id:
        skill_name = _skill_name(state.hero, record.action.skill_id)
        return f"{skill_name} -> {target}"
    if record.action.type == "basic_attack":
        return f"Basic Attack -> {target}"
    return f"{record.action.type} -> {target}"


def _judge_label(record: TurnRecord) -> str:
    if record.side == "enemy":
        damage = (record.enemy_action or {}).get("damage", 0)
        return f"LOCAL | -{damage} HP" if damage else "LOCAL"
    if record.judge is None:
        return "PENDING"
    status = "VALID" if record.judge.valid else "FALLBACK"
    damage = f" | -{record.judge.damage} HP" if record.judge.damage else ""
    return f"{status}{damage}"


def _effect(record: TurnRecord) -> tuple[str, str]:
    if record.side == "enemy":
        kind = (record.enemy_action or {}).get("type", "attack")
        if kind == "silenced":
            return kind, "<== break"
        return kind, "<== chant" if "chant" in kind else "<== strike"
    if not record.action:
        return "wait", "..."
    if record.action.type == "basic_attack":
        return "attack", "-- strike >"
    skill = record.action.skill_id or ""
    if "hex" in skill:
        return "interrupt", "--x seal --"
    if "sting" in skill:
        return "shadow", "--* sting >"
    if "mire" in skill or "omen" in skill:
        return "poison", "~~~ poison >"
    if "pierce" in skill or "hook" in skill:
        return "arrow", "====>"
    if "tower" in skill or "focus" in skill or "bell" in skill:
        return "ward", "<[#]>"
    return "skill", "-- skill ->"


def _floating_numbers(record: TurnRecord) -> tuple[str, ...]:
    values: list[str] = []
    if record.side == "enemy":
        damage = (record.enemy_action or {}).get("damage", 0)
        if damage:
            values.append(f"-{damage} HP")
        return tuple(values)
    if record.judge and record.judge.damage:
        values.append(f"-{record.judge.damage} HP")
    if record.judge and record.judge.skill_id:
        if "hex" in record.judge.skill_id:
            values.append("SLN")
        elif "sting" in record.judge.skill_id:
            values.append("CRP")
        elif record.judge.skill_id == "skill_tower_brace" and record.judge.damage:
            values.append("BRK")
    return tuple(values)


def _event_banner(state: BattleState, record: TurnRecord) -> str | None:
    boss_phase = _boss_phase_banner(state, record)
    if boss_phase is not None:
        return boss_phase
    if record.side == "hero" and record.judge and record.judge.damage:
        target = _first_target_enemy(state, record.judge.target_ids)
        if target is not None and not target.is_alive:
            return "KILL CONFIRMED"
    if record.side == "hero" and record.judge and record.judge.skill_id:
        if record.judge.skill_id == "skill_tower_brace" and record.judge.damage:
            return "BOSS BREAK"
        if "hex" in record.judge.skill_id:
            return "CHARGE BROKEN" if _targets_charging(state, record) else "SEAL PLACED"
        if record.judge.damage >= 40:
            return "CLIMAX HIT"
    if record.side == "enemy":
        enemy_action_type = (record.enemy_action or {}).get("type")
        enemy = _enemy_by_id(state, record.actor_id)
        if enemy_action_type == "chant_charge":
            if enemy is not None and enemy.tier == "archive_bound":
                return "BOSS CHARGE"
            return "BREAK WINDOW OPEN"
        if enemy_action_type == "chant_release":
            return "CHANT RELEASED"
    return None


def _counter_hint(state: BattleState, record: TurnRecord) -> str | None:
    if record.side == "enemy":
        action_type = (record.enemy_action or {}).get("type")
        enemy = _enemy_by_id(state, record.actor_id)
        if action_type == "chant_charge" and enemy is not None:
            tier = enemy.tier.upper().replace("_", "-")
            progress = f"{enemy.chant_progress}/{max(1, enemy.chant_charge_turns)}"
            return f"[WINDOW] {enemy.name} {tier} charge {progress}; interrupt before release"
        if action_type == "chant_release":
            actor = _unit_name(state, record.actor_id)
            return f"[MISSED] {actor} released the chant; review MP/cooldown timing"
    if record.side == "hero" and record.judge and record.judge.skill_id:
        if record.judge.skill_id == "skill_tower_brace" and record.judge.damage:
            enemy = _first_target_enemy(state, record.judge.target_ids)
            target = enemy.name if enemy is not None else _target_display(state, record.judge.target_ids)
            return f"[ANSWER] boss break by tower counter on {target}"
        if any(token in record.judge.skill_id for token in ("hex", "silent", "seal", "stagger")):
            status = "answered" if record.judge.valid else "failed"
            target = _target_display(state, record.judge.target_ids)
            return f"[ANSWER] counter {status} on {target}"
    return None


def _counter_clock(state: BattleState, record: TurnRecord) -> str | None:
    enemy = _active_chant_enemy(state, record)
    if enemy is None:
        return None
    total = max(1, enemy.chant_charge_turns)
    current = min(total, max(0, enemy.chant_progress))
    bar_width = 5
    filled = min(bar_width, int(round(bar_width * current / total)))
    clock = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
    interrupt = _first_interrupt_skill(state.hero)
    if interrupt is None:
        ready = "no interrupt skill"
    elif state.hero.mp < interrupt.mp_cost:
        ready = f"{interrupt.display_name} not ready: MP {state.hero.mp}/{interrupt.mp_cost}"
    elif interrupt.cooldown_remaining > 0:
        ready = f"{interrupt.display_name} not ready: CD {interrupt.cooldown_remaining}"
    else:
        ready = f"{interrupt.display_name} ready"
    status = "FULL" if current >= total else f"{current}/{total}"
    return f"COUNTER CLOCK {clock} {status} | NEXT HERO CAN INTERRUPT: {ready}"


def _boss_intel(state: BattleState, record: TurnRecord) -> BossIntel | None:
    boss = _boss_enemy(state, record)
    if boss is None:
        return None
    phase = _boss_phase_text(boss)
    charge = _boss_charge_text(boss)
    break_state = _boss_break_text(boss)
    enrage = _boss_enrage_text(state, boss)
    return BossIntel(
        enemy_id=boss.id,
        name=boss.name,
        phase=phase,
        charge=charge,
        break_state=break_state,
        enrage=enrage,
    )


def _boss_enemy(state: BattleState, record: TurnRecord | None) -> Enemy | None:
    bosses = [enemy for enemy in state.enemies if enemy.tier == "archive_bound"]
    if not bosses:
        return None
    if record is not None:
        target_ids = set(_target_ids(record))
        for boss in bosses:
            if boss.id in target_ids or boss.id == record.actor_id:
                return boss
    alive = [boss for boss in bosses if boss.is_alive]
    return alive[0] if alive else bosses[0]


def _boss_phase_text(boss: Enemy) -> str:
    if not boss.is_alive:
        return "Phase Clear | archive sealed"
    ratio = boss.hp / max(1, boss.max_hp)
    if ratio > 0.66:
        return "Phase I | Opening Rite >66%"
    if ratio > 0.33:
        return "Phase II | Black Index 66-33%"
    return "Phase III | Archive Unbound <33%"


def _boss_charge_text(boss: Enemy) -> str:
    if boss.chant_charge_turns <= 0:
        return "Charge none"
    total = max(1, boss.chant_charge_turns)
    current = min(total, max(0, boss.chant_progress))
    if current >= total:
        state = "FULL release threat"
    elif current > 0:
        state = "WINDOW interrupt now"
    else:
        state = "arming"
    return f"Charge {current}/{total} | {state}"


def _boss_break_text(boss: Enemy) -> str:
    if not boss.is_alive:
        return "Break resolved"
    status_ids = {status.id for status in boss.statuses}
    if any(status in status_ids for status in ("status_silence", "status_stagger", "status_exposed")):
        return "Break BROKEN by control"
    if boss.chant_progress > 0:
        return "Break OPEN: interrupt/control before release"
    if boss.hp / max(1, boss.max_hp) <= 0.25:
        return "Break EXECUTE: focus damage"
    return "Break locked: wait for charge or expose"


def _boss_enrage_text(state: BattleState, boss: Enemy) -> str:
    if not boss.is_alive:
        return "Enrage cleared"
    ratio = boss.hp / max(1, boss.max_hp)
    if state.tick >= 420 or ratio <= 0.25:
        return "Enrage ACTIVE: tempo collapse risk"
    if state.tick >= 300 or ratio <= 0.4:
        return "Enrage rising"
    return "Enrage dormant"


def _boss_phase_banner(state: BattleState, record: TurnRecord) -> str | None:
    if record.side != "hero" or record.judge is None or record.judge.damage <= 0:
        return None
    boss = _first_target_enemy(state, record.judge.target_ids)
    if boss is None or boss.tier != "archive_bound":
        return None
    if boss.hp <= 0:
        return "BOSS DOWN"
    before_hp = min(boss.max_hp, boss.hp + record.judge.damage)
    before_ratio = before_hp / max(1, boss.max_hp)
    after_ratio = boss.hp / max(1, boss.max_hp)
    if before_ratio > 0.66 >= after_ratio:
        return "BOSS PHASE II"
    if before_ratio > 0.33 >= after_ratio:
        return "BOSS PHASE III"
    return None


def _impact_line(state: BattleState, record: TurnRecord) -> str | None:
    if record.side == "enemy":
        kind = str((record.enemy_action or {}).get("type", "basic_attack"))
        damage = (record.enemy_action or {}).get("damage", 0)
        parts = [kind]
        if isinstance(damage, int) and damage > 0:
            before = min(state.hero.max_hp, state.hero.hp + damage)
            parts.append(f"HP {before}->{state.hero.hp}")
        if kind == "chant_release":
            parts.append("chant released")
        elif kind == "chant_charge":
            parts.append("window opened")
        return " | ".join(parts)

    judge = record.judge
    action = record.action
    if judge is None:
        return None
    parts: list[str] = []
    if judge.damage:
        target = _first_target_enemy(state, judge.target_ids)
        if target is not None:
            before_hp = min(target.max_hp, target.hp + judge.damage)
            overkill = max(0, judge.damage - before_hp)
            damage_part = f"-{judge.damage} HP"
            if target.hp <= 0:
                damage_part += " / DOWN"
            if overkill:
                damage_part += f" / overkill {overkill}"
            parts.append(damage_part)
        else:
            parts.append(f"-{judge.damage} HP")
    if action and action.type == "cast_skill" and action.skill_id:
        if state.hero.id in action.targets:
            parts.extend(_hero_support_impact_parts(state.hero))
        skill = state.hero.find_skill(action.skill_id)
        if skill is not None:
            before_mp = min(state.hero.max_mp, state.hero.mp + skill.mp_cost)
            parts.append(f"MP {before_mp}->{state.hero.mp}")
            next_interrupt = "yes" if _interrupt_available_after(state.hero, state.hero.mp) else "no"
            parts.append(f"next interrupt: {next_interrupt}")
    if not judge.valid:
        parts.append(f"fallback: {judge.fallback_to or 'none'}")
    return " | ".join(parts) if parts else judge.reason


def _hero_support_impact_parts(hero: Hero) -> list[str]:
    parts: list[str] = []
    for status_id, label in (
        ("status_shield", "SHD"),
        ("status_focus", "FOC"),
        ("status_guard", "GRD"),
        ("status_haste", "HST"),
    ):
        status = hero.find_status(status_id)
        if status is not None and status.stacks > 0:
            parts.append(f"{label} {status.stacks} {STATUS_SHORT_NAMES[status_id][1]}")
    return parts


def _resource_deltas(state: BattleState, record: TurnRecord) -> tuple[ResourceDelta, ...]:
    deltas: list[ResourceDelta] = []
    if record.side == "hero" and record.action:
        if record.action.type == "cast_skill" and record.action.skill_id:
            skill = state.hero.find_skill(record.action.skill_id)
            if skill is not None:
                before = min(state.hero.max_mp, state.hero.mp + skill.mp_cost)
                enough_next = _next_interrupt_ready(state.hero, after_mp=state.hero.mp)
                severity = "warn" if not enough_next else "info"
                deltas.append(
                    ResourceDelta(
                        "MP",
                        f"{before} -> {state.hero.mp} | interrupt ready: {'yes' if enough_next else 'no'}",
                        severity,
                    )
                )
        hp_ratio = state.hero.hp / max(1, state.hero.max_hp)
        if hp_ratio <= 0.3:
            deltas.append(ResourceDelta("HP", f"{state.hero.hp}/{state.hero.max_hp} | critical", "danger"))
    elif record.side == "enemy":
        damage = (record.enemy_action or {}).get("damage", 0)
        if isinstance(damage, int) and damage > 0:
            before = min(state.hero.max_hp, state.hero.hp + damage)
            severity = "danger" if state.hero.hp / max(1, state.hero.max_hp) <= 0.3 else "warn"
            deltas.append(ResourceDelta("HP", f"{before} -> {state.hero.hp}", severity))

    if state.hero.atb >= 100:
        deltas.append(ResourceDelta("ATB", "hero ready", "info"))
    else:
        ready_enemy = next((enemy for enemy in state.alive_enemies() if enemy.atb >= 100), None)
        if ready_enemy is not None:
            deltas.append(ResourceDelta("ATB", f"{ready_enemy.name} ready", "warn"))
        else:
            near_enemy = max(state.alive_enemies(), key=lambda enemy: enemy.atb, default=None)
            if near_enemy is not None and near_enemy.atb >= 85:
                deltas.append(ResourceDelta("ATB", f"{near_enemy.name} {near_enemy.atb}/100", "warn"))

    locked_skill = next((skill for skill in state.hero.skills if skill.cooldown_remaining > 0), None)
    if locked_skill is not None:
        deltas.append(ResourceDelta("CD", f"{locked_skill.display_name} locked {locked_skill.cooldown_remaining}t", "warn"))

    shield = state.hero.find_status("status_shield")
    if shield is not None and shield.stacks > 0:
        deltas.append(ResourceDelta("SHD", f"{shield.stacks} shield | absorbs next hit", "info"))

    return tuple(deltas[:5])


def _intent_risk_align(state: BattleState, record: TurnRecord) -> tuple[str, str, str]:
    if record.side == "enemy":
        kind = (record.enemy_action or {}).get("type", "attack")
        if "chant" in kind:
            return "enemy chant pressure", "release grows closer", "Counter window"
        return "enemy pressures the hero", "HP loss may open lethal range", "Local AI"

    action = record.action
    if action is None:
        return "recover from invalid output", "fallback may lose tempo", "Prompt missed"
    if action.type == "cast_skill" and action.skill_id:
        skill_name = _skill_name(state.hero, action.skill_id)
        if "hex" in action.skill_id:
            intent = (
                "interrupt a charging caster"
                if _targets_charging(state, record)
                else "control the fastest threat"
            )
            align = "Prompt: Control hit | Build: shadow/control"
        elif "focus" in action.skill_id or "tower" in action.skill_id:
            intent = "stabilize before lethal damage"
            align = "Prompt: Guarded hit | Build: survival"
        else:
            intent = f"convert MP into pressure with {skill_name}"
            align = "Prompt: damage tempo | Build skill"
        skill = state.hero.find_skill(action.skill_id)
        if skill and state.hero.mp < skill.mp_cost:
            risk = f"MP below repeat cost ({state.hero.mp}/{skill.mp_cost})"
        elif skill and state.hero.mp == 0:
            risk = "MP empty after this action"
        else:
            risk = "spends tempo resource"
        return intent, risk, align
    if action.type == "basic_attack":
        return "finish or conserve MP", "low impact if enemy survives", "Prompt: fallback/basic"
    return action.type, "unusual action", "Prompt alignment unknown"


def _targets_charging(state: BattleState, record: TurnRecord) -> bool:
    targets = set(_target_ids(record))
    for enemy in state.enemies:
        if enemy.id in targets and (enemy.chant_charge_turns or enemy.chant_progress):
            return True
    return False


def _next_interrupt_ready(hero: Hero, *, after_mp: int) -> bool:
    return _interrupt_available_after(hero, after_mp)


def _interrupt_available_after(hero: Hero, after_mp: int) -> bool:
    interrupt = _first_interrupt_skill(hero)
    if interrupt is None:
        return True
    return after_mp >= interrupt.mp_cost and interrupt.cooldown_remaining <= 0


def _first_interrupt_skill(hero: Hero) -> SkillState | None:
    for skill in hero.skills:
        if any(token in skill.id for token in ("hex", "silent", "seal", "stagger")):
            return skill
    return None


def _active_chant_enemy(state: BattleState, record: TurnRecord) -> Enemy | None:
    if record.side == "enemy":
        enemy = _enemy_by_id(state, record.actor_id)
        action_type = (record.enemy_action or {}).get("type")
        if enemy is not None and enemy.chant_charge_turns and action_type in {"chant_charge", "chant_release"}:
            return enemy
    targets = set(_target_ids(record))
    candidates = [
        enemy
        for enemy in state.alive_enemies()
        if enemy.chant_charge_turns and enemy.chant_progress > 0 and (not targets or enemy.id in targets)
    ]
    if not candidates:
        candidates = [
            enemy
            for enemy in state.alive_enemies()
            if enemy.chant_charge_turns and enemy.chant_progress > 0
        ]
    if not candidates:
        return None
    return max(candidates, key=lambda enemy: enemy.chant_progress)


def _first_target_enemy(state: BattleState, target_ids: tuple[str, ...]) -> Enemy | None:
    for target_id in target_ids:
        enemy = _enemy_by_id(state, target_id)
        if enemy is not None:
            return enemy
    return None


def _unit_name(state: BattleState, unit_id: str) -> str:
    if state.hero.id == unit_id:
        return state.hero.name
    for enemy in state.enemies:
        if enemy.id == unit_id:
            return enemy.name
    return unit_id


def _enemy_by_id(state: BattleState, unit_id: str) -> Enemy | None:
    for enemy in state.enemies:
        if enemy.id == unit_id:
            return enemy
    return None


def _target_display(state: BattleState, targets: tuple[str, ...]) -> str:
    if not targets:
        return "-"
    return ", ".join(_unit_name(state, target) for target in targets)


def _skill_name(hero: Hero, skill_id: str) -> str:
    skill: SkillState | None = hero.find_skill(skill_id)
    return skill.display_name if skill is not None else skill_id


def _fallback_status_code(status_id: str) -> str:
    cleaned = status_id.replace("status_", "")
    return cleaned[:3].upper()


def _fallback_status_name(status_id: str) -> str:
    return status_id.replace("status_", "").replace("_", " ")


def _status_display(status_id: str) -> tuple[str, str]:
    return STATUS_SHORT_NAMES.get(
        status_id,
        (_fallback_status_code(status_id), _fallback_status_name(status_id)),
    )
