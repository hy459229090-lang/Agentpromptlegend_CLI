"""Deterministic battle diagnostics shared by reports and TUI."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ouro_agent.engine.models import BattleState


_CONTROL_SKILLS = frozenset(
    {
        "skill_hex_seal",
        "skill_ash_glare",
        "skill_omen_vial",
        "skill_silent_hymn",
        "skill_tower_brace",
    }
)
_SHIELD_SKILLS = frozenset(
    {
        "skill_corrupted_focus",
        "skill_tower_brace",
        "skill_eclipse_step",
        "skill_sinking_veil",
        "skill_crank_charge",
        "skill_bell_echo",
    }
)
_DOT_SKILLS = frozenset(
    {
        "skill_mire_needle",
        "skill_grave_nail",
        "skill_omen_vial",
    }
)


@dataclass(frozen=True)
class TacticalDiagnosis:
    mp_dry_turns: int
    low_impact_turns: int
    max_defense_loop: int
    targeting_drift_turns: int
    counter_windows_opened: int
    counter_windows_answered: int
    counter_windows_missed: int
    notes: tuple[str, ...]
    prescription: tuple[str, str, str]
    failure_reasons: tuple[str, ...]
    next_run_advice: tuple[str, ...]


@dataclass(frozen=True)
class TempoBudget:
    label: str
    min_hero_turns: int
    max_hero_turns: int

    def describe(self) -> str:
        return f"{self.label} {self.min_hero_turns}-{self.max_hero_turns} hero turns"


def classify_tempo_budget(state: BattleState) -> TempoBudget:
    """Classify expected fight length from deterministic enemy state."""
    tiers = {enemy.tier for enemy in state.enemies}
    if "archive_bound" in tiers:
        return TempoBudget("boss", 8, 18)
    if "ritebound" in tiers:
        return TempoBudget("elite", 5, 12)
    if len(state.enemies) >= 3:
        return TempoBudget("normal", 4, 11)
    return TempoBudget("normal", 3, 8)


def classify_tempo_outlier(
    state: BattleState,
    diagnosis: TacticalDiagnosis,
    *,
    hero_turn_count: int,
) -> str | None:
    budget = classify_tempo_budget(state)
    if state.result == "timeout":
        if diagnosis.counter_windows_missed:
            return _counter_miss_reason(state)
        if diagnosis.targeting_drift_turns:
            return "target_drift"
        if diagnosis.mp_dry_turns:
            return "mp_drought"
        if diagnosis.max_defense_loop >= 2:
            return "defense_loop"
        if diagnosis.low_impact_turns >= 2:
            return "low_output"
        return "safety_limit"
    if hero_turn_count < budget.min_hero_turns:
        return "under_budget_burst"
    if hero_turn_count <= budget.max_hero_turns:
        return None
    if diagnosis.counter_windows_missed:
        return _counter_miss_reason(state)
    if diagnosis.targeting_drift_turns:
        return "target_drift"
    if diagnosis.mp_dry_turns:
        return "mp_drought"
    if diagnosis.max_defense_loop >= 2:
        return "defense_loop"
    if diagnosis.low_impact_turns >= 2:
        return "low_output"
    return "over_budget"


def _counter_miss_reason(state: BattleState) -> str:
    if any(enemy.tier == "archive_bound" for enemy in state.enemies):
        return "boss_break_missed"
    return "missed_counter"


def analyze_battle_tactics(
    state: BattleState,
    records: list[Any],
    *,
    language: str = "en",
) -> TacticalDiagnosis:
    mp_dry_turns = 0
    low_impact_turns = 0
    defense_streak = 0
    max_defense_loop = 0
    targeting_drift_turns = 0
    counter_windows_opened = 0
    counter_windows_answered = 0
    counter_windows_missed = 0
    pending_counter_windows = 0

    for record in records:
        if record.side == "enemy":
            kind = (record.enemy_action or {}).get("type")
            if kind == "chant_charge":
                counter_windows_opened += 1
                pending_counter_windows += 1
            elif kind == "chant_release":
                if pending_counter_windows > 0:
                    counter_windows_missed += 1
                    pending_counter_windows -= 1
            defense_streak = 0
            continue

        action_kind = _hero_action_kind(record)
        if action_kind == "defend":
            defense_streak += 1
            max_defense_loop = max(max_defense_loop, defense_streak)
        else:
            defense_streak = 0

        if _is_mp_dry(record):
            mp_dry_turns += 1
        if _is_low_impact(record):
            low_impact_turns += 1
        if _is_targeting_drift(record):
            targeting_drift_turns += 1
        if pending_counter_windows > 0 and _answers_counter_window(record):
            counter_windows_answered += 1
            pending_counter_windows -= 1

    notes = tuple(
        _diagnosis_notes(
            state,
            mp_dry_turns=mp_dry_turns,
            low_impact_turns=low_impact_turns,
            max_defense_loop=max_defense_loop,
            targeting_drift_turns=targeting_drift_turns,
            counter_windows_opened=counter_windows_opened,
            counter_windows_answered=counter_windows_answered,
            counter_windows_missed=counter_windows_missed,
            language=language,
        )
    )
    prescription = tuple(
        _diagnosis_prescription(
            state,
            mp_dry_turns=mp_dry_turns,
            low_impact_turns=low_impact_turns,
            max_defense_loop=max_defense_loop,
            targeting_drift_turns=targeting_drift_turns,
            counter_windows_opened=counter_windows_opened,
            counter_windows_answered=counter_windows_answered,
            counter_windows_missed=counter_windows_missed,
            language=language,
        )
    )
    failure_reasons = tuple(
        _failure_reasons(
            state,
            mp_dry_turns=mp_dry_turns,
            low_impact_turns=low_impact_turns,
            max_defense_loop=max_defense_loop,
            targeting_drift_turns=targeting_drift_turns,
            counter_windows_opened=counter_windows_opened,
            counter_windows_answered=counter_windows_answered,
            counter_windows_missed=counter_windows_missed,
            language=language,
        )
    )
    next_run_advice = tuple(
        _next_run_advice(
            state,
            mp_dry_turns=mp_dry_turns,
            low_impact_turns=low_impact_turns,
            max_defense_loop=max_defense_loop,
            targeting_drift_turns=targeting_drift_turns,
            counter_windows_missed=counter_windows_missed,
            language=language,
        )
    )
    return TacticalDiagnosis(
        mp_dry_turns=mp_dry_turns,
        low_impact_turns=low_impact_turns,
        max_defense_loop=max_defense_loop,
        targeting_drift_turns=targeting_drift_turns,
        counter_windows_opened=counter_windows_opened,
        counter_windows_answered=counter_windows_answered,
        counter_windows_missed=counter_windows_missed,
        notes=notes,
        prescription=prescription,
        failure_reasons=failure_reasons,
        next_run_advice=next_run_advice,
    )


def analyze_prompt_impacts(
    records: list[Any],
    *,
    language: str = "en",
) -> tuple[str, ...]:
    """Explain one or two traceable choices caused by a prompt template."""
    impacts: list[str] = []
    active_style: str | None = None

    for record in records:
        if record.side != "hero":
            continue
        style = getattr(record, "prompt_style", None)
        if not style:
            continue
        active_style = str(style)
        line = _prompt_impact_for_record(record, active_style, language)
        if line:
            impacts.append(line)
        if len(impacts) >= 2:
            break

    if impacts:
        return tuple(_dedupe(impacts))
    if active_style:
        return (_prompt_impact_fallback(active_style, language),)
    return ()


def _hero_action_kind(record: Any) -> str | None:
    if record.judge and record.judge.action_kind:
        return record.judge.action_kind
    if record.action:
        return record.action.type
    return None


def _is_mp_dry(record: Any) -> bool:
    if record.judge is None:
        return False
    reason = f"{record.judge.reason} {record.judge.summary}".lower()
    return "insufficient mp" in reason or "mana too low" in reason


def _is_low_impact(record: Any) -> bool:
    action_kind = _hero_action_kind(record)
    if action_kind in {"observe", "change_stance"}:
        return True
    if record.judge is None:
        return False
    if not record.judge.valid:
        return True
    if action_kind == "basic_attack" and record.judge.damage <= 6:
        return True
    if action_kind == "cast_skill" and record.judge.damage <= 0:
        return True
    return False


def _answers_counter_window(record: Any) -> bool:
    if record.judge is None or not record.judge.valid:
        return False
    skill_id = record.judge.skill_id or ""
    if skill_id == "skill_tower_brace" and record.judge.damage > 0:
        return True
    if any(token in skill_id for token in ("hex", "silent", "seal", "stagger")):
        return True
    summary = record.judge.summary.lower()
    return any(token in summary for token in ("silence", "stagger", "break"))


def _prompt_impact_for_record(record: Any, style: str, language: str) -> str | None:
    action_kind = _hero_action_kind(record)
    skill_id = record.judge.skill_id if record.judge is not None else None
    if skill_id is None and record.action is not None:
        skill_id = record.action.skill_id
    target = _target_delta(record)
    hero = _hero_delta(record)

    if style == "control":
        return _control_prompt_impact(record, skill_id, target, language)
    if style == "aggressive":
        return _aggressive_prompt_impact(action_kind, skill_id, target, language)
    if style == "guarded":
        return _guarded_prompt_impact(action_kind, skill_id, hero, record, language)
    if style == "attrition":
        return _attrition_prompt_impact(skill_id, target, language)
    return None


def _control_prompt_impact(
    record: Any,
    skill_id: str | None,
    target: dict[str, Any] | None,
    language: str,
) -> str | None:
    if skill_id is None or target is None:
        return None
    if skill_id not in _CONTROL_SKILLS and not _answers_counter_window(record):
        return None
    atb = _int(target.get("atb"))
    chant = _int(target.get("chant_progress"))
    target_id = str(target.get("id") or "-")
    if chant <= 0 and atb < 60:
        return None
    if language == "zh":
        if chant > 0:
            return (
                "Prompt impact: Control 预设把行动用于打断 "
                f"{target_id} 的吟唱窗口（ATB {atb}，技能 {skill_id}）。"
            )
        return (
            "Prompt impact: Control 预设优先处理高 ATB 威胁 "
            f"{target_id}（ATB {atb}，技能 {skill_id}）。"
        )
    if chant > 0:
        return (
            "Prompt impact: Control template spent a skill turn interrupting "
            f"{target_id}'s chant window at {atb} ATB with {skill_id}."
        )
    return (
        "Prompt impact: Control template prioritized high-ATB threat "
        f"{target_id} at {atb} ATB with {skill_id}."
    )


def _aggressive_prompt_impact(
    action_kind: str | None,
    skill_id: str | None,
    target: dict[str, Any] | None,
    language: str,
) -> str | None:
    if action_kind != "cast_skill" or skill_id is None or target is None:
        return None
    hp = _int(target.get("hp"))
    hp_text = _hp_text(target)
    target_id = str(target.get("id") or "-")
    max_hp = _int(target.get("max_hp"), 0)
    if hp > 45 and (max_hp <= 0 or hp / max(1, max_hp) > 0.55):
        return None
    if language == "zh":
        return (
            "Prompt impact: Aggressive 预设把技能投入收割线，"
            f"瞄准 {target_id}（HP {hp_text}，技能 {skill_id}）。"
        )
    return (
        "Prompt impact: Aggressive template pushed a finisher into "
        f"{target_id} at {hp_text} HP with {skill_id}."
    )


def _guarded_prompt_impact(
    action_kind: str | None,
    skill_id: str | None,
    hero: dict[str, Any] | None,
    record: Any,
    language: str,
) -> str | None:
    if action_kind != "defend" and skill_id not in _SHIELD_SKILLS:
        return None
    if hero is None:
        return None
    hp = _int(hero.get("hp"))
    max_hp = max(1, _int(hero.get("max_hp"), hp))
    if hp / max_hp >= 0.8 and not _record_incoming_pressure(record):
        return None
    if language == "zh":
        return (
            "Prompt impact: Guarded 预设在压力窗口前保住血线，"
            f"行动时 HP {hp}/{max_hp}。"
        )
    return (
        "Prompt impact: Guarded template protected the HP line before pressure, "
        f"acting at {hp}/{max_hp} HP."
    )


def _attrition_prompt_impact(
    skill_id: str | None,
    target: dict[str, Any] | None,
    language: str,
) -> str | None:
    if skill_id not in _DOT_SKILLS or target is None:
        return None
    target_id = str(target.get("id") or "-")
    hp_text = _hp_text(target)
    if language == "zh":
        return (
            "Prompt impact: Attrition 预设先铺持续伤害，"
            f"把 {skill_id} 放到 {target_id}（HP {hp_text}）。"
        )
    return (
        "Prompt impact: Attrition template established damage-over-time with "
        f"{skill_id} on {target_id} at {hp_text} HP."
    )


def _prompt_impact_fallback(style: str, language: str) -> str:
    if language == "zh":
        names = {
            "aggressive": "Aggressive",
            "guarded": "Guarded",
            "control": "Control",
            "attrition": "Attrition",
        }
        return f"Prompt impact: {names.get(style, style)} 预设已启用，但本场没有触发可归因阈值。"
    names = {
        "aggressive": "Aggressive",
        "guarded": "Guarded",
        "control": "Control",
        "attrition": "Attrition",
    }
    return f"Prompt impact: {names.get(style, style)} template was active, but no traceable threshold fired."


def _target_delta(record: Any) -> dict[str, Any] | None:
    target_ids: tuple[str, ...] = ()
    if record.judge is not None and record.judge.target_ids:
        target_ids = tuple(record.judge.target_ids)
    elif record.action is not None and record.action.targets:
        target_ids = tuple(record.action.targets)
    if not target_ids:
        return None

    delta = record.delta_context or {}
    enemy_delta = delta.get("enemy_delta") if isinstance(delta, dict) else None
    if not isinstance(enemy_delta, list):
        return None

    for enemy in enemy_delta:
        if isinstance(enemy, dict) and str(enemy.get("id")) in target_ids:
            return enemy
    return None


def _hero_delta(record: Any) -> dict[str, Any] | None:
    delta = record.delta_context or {}
    hero_delta = delta.get("hero_delta") if isinstance(delta, dict) else None
    return hero_delta if isinstance(hero_delta, dict) else None


def _hp_text(unit: dict[str, Any]) -> str:
    hp = _int(unit.get("hp"))
    max_hp = _int(unit.get("max_hp"), 0)
    if max_hp > 0:
        return f"{hp}/{max_hp}"
    return str(hp)


def _record_incoming_pressure(record: Any) -> bool:
    delta = record.delta_context or {}
    enemy_delta = delta.get("enemy_delta") if isinstance(delta, dict) else None
    if not isinstance(enemy_delta, list):
        return False
    return any(
        isinstance(enemy, dict)
        and _int(enemy.get("hp")) > 0
        and (_int(enemy.get("atb")) >= 85 or _int(enemy.get("chant_progress")) > 0)
        for enemy in enemy_delta
    )


def _is_targeting_drift(record: Any) -> bool:
    """Return True when the trace shows a lower-threat target was chosen."""
    if record.side != "hero":
        return False
    if record.judge is None or not record.judge.valid:
        return False

    target_ids = tuple(record.judge.target_ids or ())
    if not target_ids and record.action is not None:
        target_ids = tuple(record.action.targets or ())
    if not target_ids:
        return False

    delta = record.delta_context or {}
    enemy_delta = delta.get("enemy_delta") if isinstance(delta, dict) else None
    if not isinstance(enemy_delta, list):
        return False

    alive_enemies = [
        enemy
        for enemy in enemy_delta
        if isinstance(enemy, dict) and _int(enemy.get("hp")) > 0
    ]
    if len(alive_enemies) < 2:
        return False

    targeted = [enemy for enemy in alive_enemies if str(enemy.get("id")) in target_ids]
    if not targeted:
        return False

    target_score = max(_enemy_threat_score(enemy) for enemy in targeted)
    other_high_threats = [
        enemy
        for enemy in alive_enemies
        if str(enemy.get("id")) not in target_ids and _enemy_threat_score(enemy) >= 80
    ]
    return any(_enemy_threat_score(enemy) - target_score >= 35 for enemy in other_high_threats)


def _enemy_threat_score(enemy: dict[str, Any]) -> int:
    score = 0
    if _int(enemy.get("chant_progress")) > 0:
        score += 100

    atb = _int(enemy.get("atb"))
    if atb >= 95:
        score += 45
    elif atb >= 80:
        score += 30
    elif atb >= 60:
        score += 15

    tier = str(enemy.get("tier") or "")
    if tier == "archive_bound":
        score += 35
    elif tier == "ritebound":
        score += 20
    elif tier:
        score += 8

    hp = _int(enemy.get("hp"))
    if hp <= 8:
        score -= 15
    return score


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _diagnosis_notes(
    state: BattleState,
    *,
    mp_dry_turns: int,
    low_impact_turns: int,
    max_defense_loop: int,
    targeting_drift_turns: int,
    counter_windows_opened: int,
    counter_windows_answered: int,
    counter_windows_missed: int,
    language: str,
) -> list[str]:
    if language == "zh":
        notes: list[str] = []
        if mp_dry_turns:
            notes.append("下次优先保留一次打断技能的 MP，避免关键回合只能回退普攻。")
        if low_impact_turns >= 2:
            notes.append("模型有连续低收益倾向；提示词应提高击杀线、集火和技能价值权重。")
        if max_defense_loop >= 2:
            notes.append("防御循环偏长；除非血线危险，否则下一轮应更早转入输出或控制。")
        if targeting_drift_turns:
            notes.append("目标选择偏离威胁；高 ATB 或吟唱敌人应比低压残血目标更优先。")
        if counter_windows_missed:
            notes.append("敌方吟唱释放前没有被稳定打断；Build 应补控制、沉默或速度。")
        if not notes:
            notes.append("行动节奏健康；下一轮可以强化优势标签而不是重写策略。")
        if state.result == "defeat" and counter_windows_opened > counter_windows_answered:
            notes.append("战败与反制窗口处理相关，优先检查打断技能冷却和 MP。")
        return notes[:3]

    notes = []
    if mp_dry_turns:
        notes.append("Reserve enough MP for one interrupt so key turns do not collapse into fallback attacks.")
    if low_impact_turns >= 2:
        notes.append("The model drifted into low-impact turns; raise kill-line, focus-fire, and skill-value priority.")
    if max_defense_loop >= 2:
        notes.append("Defense looping is high; leave guard mode earlier unless HP is in lethal range.")
    if targeting_drift_turns:
        notes.append("Target priority drifted; high-ATB or chanting enemies should outrank low-pressure targets.")
    if counter_windows_missed:
        notes.append("Chants reached release; add control, silence, speed, or clearer interrupt prompts.")
    if not notes:
        notes.append("Tempo looked healthy; strengthen the current build tags instead of rewriting the plan.")
    if state.result == "defeat" and counter_windows_opened > counter_windows_answered:
        notes.append("Defeat is linked to counter timing; inspect interrupt cooldown and MP availability first.")
    return notes[:3]


def _diagnosis_prescription(
    state: BattleState,
    *,
    mp_dry_turns: int,
    low_impact_turns: int,
    max_defense_loop: int,
    targeting_drift_turns: int,
    counter_windows_opened: int,
    counter_windows_answered: int,
    counter_windows_missed: int,
    language: str,
) -> list[str]:
    if language == "zh":
        if counter_windows_missed:
            problem = "反制窗口没有被稳定回应，敌方吟唱转化成了真实伤害。"
            cause = f"{counter_windows_opened} 次窗口只回应 {counter_windows_answered} 次。"
            pick = "优先选择 control、silence、speed 或降低高耗蓝技能优先级。"
        elif targeting_drift_turns:
            problem = "目标优先级偏离威胁源，给高压敌人留下了行动窗口。"
            cause = f"{targeting_drift_turns} 个英雄回合攻击了较低威胁目标。"
            pick = "使用 Control 预设，并提高高 ATB、吟唱、精英目标权重。"
        elif mp_dry_turns:
            problem = "关键回合 MP 不足，模型只能降级成低收益行动。"
            cause = f"{mp_dry_turns} 个回合出现 MP 枯竭或施法失败。"
            pick = "优先选择 MP、echo、focus 标签，或更保守的 Control 策略。"
        elif low_impact_turns >= 2:
            problem = "战斗节奏被低收益行动拖慢。"
            cause = f"{low_impact_turns} 个英雄回合没有形成击杀线或控制收益。"
            pick = "优先选择 attack、power、corrupt 标签，并提高集火提示权重。"
        elif max_defense_loop >= 2:
            problem = "防御循环保护了血线，但损失了击杀节奏。"
            cause = f"连续防御最长达到 {max_defense_loop} 回合。"
            pick = "选择反击、护盾转伤害或更低冷却的输出补件。"
        else:
            problem = "本场节奏健康，没有明显致命短板。"
            cause = "模型行动、Build 标签和本地裁判形成了稳定闭环。"
            pick = "继续补当前核心标签，追求共鸣从 PAIR 到 ONLINE。"
        if state.result == "defeat" and problem.startswith("本场"):
            problem = "失败来自整体资源线不足，而不是单一错误。"
            cause = "血量、MP 和击杀速度没有同时满足后半场压力。"
            pick = "选择生存或控制补件，先保证下一场能进入稳定循环。"
        return [problem, cause, pick]

    if counter_windows_missed:
        problem = "Counter windows were not answered reliably, letting chants become real damage."
        cause = f"{counter_windows_answered}/{counter_windows_opened} windows were answered."
        pick = "Take control, silence, speed, or lower high-MP skill priority."
    elif targeting_drift_turns:
        problem = "Target priority drifted away from the real threat."
        cause = f"{targeting_drift_turns} hero turns hit lower-pressure targets."
        pick = "Use the Control prompt and raise high-ATB, chanting, and elite target priority."
    elif mp_dry_turns:
        problem = "Key turns ran out of MP and collapsed into weaker actions."
        cause = f"{mp_dry_turns} turns showed MP drought or failed casting."
        pick = "Take MP, echo, focus, or a more conservative Control plan."
    elif low_impact_turns >= 2:
        problem = "The fight lost tempo to low-impact turns."
        cause = f"{low_impact_turns} hero turns did not create kill-line or control value."
        pick = "Take attack, power, corrupt, or stronger focus-fire prompt support."
    elif max_defense_loop >= 2:
        problem = "Defense protected HP but cost too much kill tempo."
        cause = f"The longest defense loop lasted {max_defense_loop} turns."
        pick = "Take counter, shield-to-damage, or lower-cooldown pressure pieces."
    else:
        problem = "Tempo was healthy; no fatal weakness stood out."
        cause = "Model choices, build tags, and local judging formed a stable loop."
        pick = "Keep stacking the current core tags toward PAIR or ONLINE."
    if state.result == "defeat" and problem.startswith("Tempo was healthy"):
        problem = "Defeat came from the total resource line rather than one clear mistake."
        cause = "HP, MP, and kill speed did not all survive late-fight pressure."
        pick = "Take survival or control pieces before pushing greedier rewards."
    return [problem, cause, pick]


def _failure_reasons(
    state: BattleState,
    *,
    mp_dry_turns: int,
    low_impact_turns: int,
    max_defense_loop: int,
    targeting_drift_turns: int,
    counter_windows_opened: int,
    counter_windows_answered: int,
    counter_windows_missed: int,
    language: str,
) -> list[str]:
    if state.result not in {"defeat", "timeout"}:
        return []

    damage_taken = _damage_taken(state)
    high_tier = _highest_tier_label(state)

    if language == "zh":
        reasons: list[str] = []
        if mp_dry_turns:
            reasons.append(f"资源: {mp_dry_turns} 个英雄回合出现 MP 枯竭或施法失败。")
        elif damage_taken:
            reasons.append(
                f"资源: 承伤 {damage_taken}，HP 续航没有扛过后半场压力。"
            )

        if targeting_drift_turns:
            reasons.append(
                f"目标: {targeting_drift_turns} 个回合把行动交给较低威胁目标，"
                "高 ATB/吟唱敌人获得窗口。"
            )
        elif counter_windows_missed:
            reasons.append(
                "目标: "
                f"{counter_windows_opened} 次反制窗口只回应 {counter_windows_answered} 次。"
            )

        if low_impact_turns >= 2:
            reasons.append(
                f"Build: {low_impact_turns} 个低收益回合暴露了输出或控制标签缺口。"
            )
        elif max_defense_loop >= 2:
            reasons.append(
                f"Build: 最长 {max_defense_loop} 回合防御循环保护了血线，但损失击杀节奏。"
            )

        if high_tier:
            reasons.append(
                f"路线: {high_tier} 压力到来前，Build 还缺少稳定续航或打断补件。"
            )
        elif len(reasons) < 3:
            reasons.append("路线: 连续战斗后进入下一节点前，应优先确认 HP/MP 是否能支撑节奏。")
        return _dedupe(reasons)[:3]

    reasons = []
    if mp_dry_turns:
        reasons.append(f"Resource: {mp_dry_turns} hero turns hit MP drought or failed casting.")
    elif damage_taken:
        reasons.append(f"Resource: {damage_taken} damage taken outpaced HP sustain.")

    if targeting_drift_turns:
        reasons.append(
            f"Targeting: {targeting_drift_turns} turns spent actions on lower-pressure targets "
            "while a high-ATB or chanting enemy had a window."
        )
    elif counter_windows_missed:
        reasons.append(
            f"Targeting: only {counter_windows_answered}/{counter_windows_opened} counter windows were answered."
        )

    if low_impact_turns >= 2:
        reasons.append(f"Build: {low_impact_turns} low-impact turns exposed a damage or control gap.")
    elif max_defense_loop >= 2:
        reasons.append(
            f"Build: the longest defense loop lasted {max_defense_loop} turns and cost kill tempo."
        )

    if high_tier:
        reasons.append(
            f"Route: {high_tier} pressure arrived before the build had reliable sustain or interrupts."
        )
    elif len(reasons) < 3:
        reasons.append("Route: check HP/MP before chaining another combat node.")
    return _dedupe(reasons)[:3]


def _next_run_advice(
    state: BattleState,
    *,
    mp_dry_turns: int,
    low_impact_turns: int,
    max_defense_loop: int,
    targeting_drift_turns: int,
    counter_windows_missed: int,
    language: str,
) -> list[str]:
    if state.result not in {"defeat", "timeout"}:
        return []

    high_tier = _highest_tier_label(state)

    if language == "zh":
        advice: list[str] = []
        if counter_windows_missed or targeting_drift_turns:
            advice.append("下一局使用 Control 预设，奖励优先拿 control、silence、speed。")
        if mp_dry_turns:
            advice.append("保留一次关键技能 MP；奖励优先拿 MP、echo、focus。")
        if low_impact_turns >= 2:
            advice.append("补 attack、power、corrupt，降低无伤害技能的连续使用。")
        if max_defense_loop >= 2:
            advice.append("补反击或护盾转伤害，让防御回合能转化为击杀压力。")
        if high_tier:
            advice.append("挑战精英/Boss 前优先休息或进商店修正资源线。")
        if not advice:
            advice.append("先拿生存或控制补件，再选择金币/贪心奖励。")
        return _dedupe(advice)[:3]

    advice = []
    if counter_windows_missed or targeting_drift_turns:
        advice.append("Use the Control prompt; prioritize control, silence, or speed rewards.")
    if mp_dry_turns:
        advice.append("Reserve MP for one key skill; take MP, echo, or focus rewards.")
    if low_impact_turns >= 2:
        advice.append("Patch damage with attack, power, or corrupt pieces and reduce zero-damage turns.")
    if max_defense_loop >= 2:
        advice.append("Add counter or shield-to-damage pieces so guard turns convert into pressure.")
    if high_tier:
        advice.append("Rest or shop before the next elite/boss pressure node.")
    if not advice:
        advice.append("Take survival or control pieces before choosing greedier gold rewards.")
    return _dedupe(advice)[:3]


def _damage_taken(state: BattleState) -> int:
    total = 0
    for event in state.events:
        if event.kind != "enemy_attack":
            continue
        total += _int(event.payload.get("damage"))
    return total


def _highest_tier_label(state: BattleState) -> str | None:
    tiers = {enemy.tier for enemy in state.enemies}
    if "archive_bound" in tiers:
        return "Boss"
    if "ritebound" in tiers:
        return "elite"
    return None


def _dedupe(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        result.append(line)
    return result
