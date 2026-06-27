"""Deterministic TUI animation frame builders.

The animation layer is display-only: it expands resolved state and already
rendered screens into staged phases, but never changes game rules.
"""
from __future__ import annotations

from dataclasses import dataclass

from ouro_agent.content import ContentBundle
from ouro_agent.art.sprite_atlas import SpriteAtlas
from ouro_agent.engine.battle import TurnRecord
from ouro_agent.engine.build import ResolvedBuild
from ouro_agent.engine.models import BattleState
from ouro_agent.i18n import visual_width
from ouro_agent.tui.bitmap_renderer import (
    BITMAP_RENDER_BACKENDS,
    render_bitmap_timeline_frames,
)
from ouro_agent.tui.layout import fit_text
from ouro_agent.tui.pixel_skin import pixel_panel
from ouro_agent.tui.screens import render_battle_screen
from ouro_agent.tui.stage_model import build_combat_stage_timeline
from ouro_agent.tui.timeline_renderer import render_timeline_frames


BATTLE_ANIMATION_PHASES: tuple[str, ...] = (
    "select",
    "windup",
    "travel",
    "impact",
    "judge",
)

NO_ANIMATION_BATTLE_PHASES: tuple[str, ...] = (
    "select",
    "impact",
    "judge",
)

MODE_SELECT_PHASES: tuple[str, ...] = (
    "agent",
    "prompt",
    "judge",
    "ready",
)

ENCOUNTER_BRIEFING_PHASES: tuple[str, ...] = (
    "scout",
    "threat",
    "window",
    "ready",
)

BATTLE_RESULT_PHASES: tuple[str, ...] = (
    "result",
    "reveal",
    "next",
)

REWARD_REVEAL_PHASES: tuple[str, ...] = (
    "drop",
    "cards",
    "handoff",
)

CHOICE_LOCK_PHASES: tuple[str, ...] = (
    "scan",
    "focus",
    "lock",
)

MOTION_DIRECTOR_STAGES: tuple[str, ...] = (
    "threat",
    "select",
    "impact",
    "judge",
    "meaning",
)


@dataclass(frozen=True)
class BattleAnimationFrame:
    phase: str
    text: str
    delay_multiplier: float = 1.0


@dataclass(frozen=True)
class UiAnimationFrame:
    phase: str
    text: str
    delay_multiplier: float = 1.0


def build_battle_animation_frames(
    state: BattleState,
    record: TurnRecord,
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
) -> tuple[BattleAnimationFrame, ...]:
    """Return staged render frames for a single completed turn record."""
    multipliers = {
        "select": 0.55,
        "windup": 0.75,
        "travel": 0.60,
        "impact": 0.85,
        "judge": 1.00,
    }
    frames: list[BattleAnimationFrame] = []
    for phase in BATTLE_ANIMATION_PHASES:
        frames.append(
            BattleAnimationFrame(
                phase=phase,
                delay_multiplier=multipliers[phase],
                text=render_battle_screen(
                    state,
                    record,
                    provider_label=provider_label,
                    seed=seed,
                    unicode_mode=unicode_mode,
                    floor_label=floor_label,
                    language=language,
                    width=width,
                    enhanced_bars=enhanced_bars,
                    bundle=bundle,
                    build=build,
                    scene_text=scene_text,
                    color_mode=color_mode,
                    animation_phase=phase,
                ),
            )
        )
    return tuple(frames)


def build_no_animation_battle_frames(
    state: BattleState,
    record: TurnRecord,
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
) -> tuple[BattleAnimationFrame, ...]:
    """Return deterministic compressed action frames for logs and CI."""
    frames = build_battle_animation_frames(
        state,
        record,
        provider_label=provider_label,
        seed=seed,
        unicode_mode=unicode_mode,
        floor_label=floor_label,
        language=language,
        width=width,
        enhanced_bars=enhanced_bars,
        bundle=bundle,
        build=build,
        scene_text=scene_text,
        color_mode=color_mode,
    )
    return tuple(frame for frame in frames if frame.phase in NO_ANIMATION_BATTLE_PHASES)


def build_sprite_battle_animation_frames(
    state: BattleState,
    record: TurnRecord,
    *,
    atlas: SpriteAtlas,
    mode: str = "unicode",
    width: int = 100,
    language: str = "en",
) -> tuple[BattleAnimationFrame, ...]:
    """Return display-only sprite timeline frames for a resolved combat turn."""
    timeline = build_combat_stage_timeline(state, record, atlas)
    if timeline is None:
        return ()
    if mode in BITMAP_RENDER_BACKENDS:
        frames = render_bitmap_timeline_frames(
            timeline,
            atlas,
            backend=mode,
            width=width,
            contract_line=False,
            embed_images=True,
            language=language,
        )
    else:
        frames = render_timeline_frames(
            timeline,
            atlas,
            mode=mode,
            width=width,
            contract_line=False,
            language=language,
        )
    return tuple(
        BattleAnimationFrame(
            phase=frame.frame_id,
            text=frame.text,
            delay_multiplier=max(0.45, frame.duration_ms / 80),
        )
        for frame in frames
    )


def build_mode_select_animation_frames(
    *,
    start_screen: str,
    setup_screen: str,
    ready_screen: str | None = None,
    language: str = "en",
    width: int = 100,
    unicode_mode: bool = False,
) -> tuple[UiAnimationFrame, ...]:
    """Return staged setup frames for the initial mode/loadout selection."""
    payload_by_phase = {
        "agent": start_screen,
        "prompt": setup_screen,
        "judge": setup_screen,
        "ready": ready_screen or setup_screen,
    }
    multipliers = {
        "agent": 0.70,
        "prompt": 0.75,
        "judge": 0.70,
        "ready": 0.95,
    }
    frames: list[UiAnimationFrame] = []
    for phase in MODE_SELECT_PHASES:
        frames.append(
            UiAnimationFrame(
                phase=phase,
                delay_multiplier=multipliers[phase],
                text=_compose_ui_animation_frame(
                    payload_by_phase[phase],
                    title=_mode_select_title(language),
                    phase=phase,
                    phases=MODE_SELECT_PHASES,
                    language=language,
                    width=width,
                    unicode_mode=unicode_mode,
                    extra_lines=_mode_select_ritual_lines(
                        phase,
                        language=language,
                        width=max(12, width - 4),
                        unicode_mode=unicode_mode,
                    ),
                    detail=_mode_select_detail(phase, language),
                    tone="counter" if phase != "ready" else "hero",
                ),
            )
        )
    return tuple(frames)


def build_choice_lock_animation_frames(
    screen: str,
    *,
    selected_index: int,
    selected_label: str | None = None,
    kind: str = "reward",
    language: str = "en",
    width: int = 100,
    unicode_mode: bool = False,
) -> tuple[UiAnimationFrame, ...]:
    """Return staged frames for a route/reward/rest/event choice lock."""
    multipliers = {"scan": 0.55, "focus": 0.70, "lock": 0.90}
    frames: list[UiAnimationFrame] = []
    for phase in CHOICE_LOCK_PHASES:
        focused_screen = _choice_focus_overlay(
            screen,
            phase=phase,
            selected_index=selected_index,
            selected_label=selected_label,
            language=language,
            width=width,
            unicode_mode=unicode_mode,
        )
        frames.append(
            UiAnimationFrame(
                phase=phase,
                delay_multiplier=multipliers[phase],
                text=_compose_ui_animation_frame(
                    focused_screen,
                    title=_choice_lock_title(kind, language),
                    phase=phase,
                    phases=CHOICE_LOCK_PHASES,
                    language=language,
                    width=width,
                    unicode_mode=unicode_mode,
                    extra_lines=_choice_lock_signal_lines(
                        phase,
                        selected_index=selected_index,
                        selected_label=selected_label,
                        language=language,
                        width=max(12, width - 4),
                        unicode_mode=unicode_mode,
                    ),
                    detail=_choice_lock_detail(
                        phase,
                        selected_index=selected_index,
                        selected_label=selected_label,
                        language=language,
                    ),
                    tone="hero" if phase == "lock" else "counter",
                ),
            )
        )
    return tuple(frames)


def build_encounter_briefing_animation_frames(
    screen: str,
    *,
    language: str = "en",
    width: int = 100,
    unicode_mode: bool = False,
) -> tuple[UiAnimationFrame, ...]:
    """Return staged display-only frames for entering an encounter."""
    multipliers = {
        "scout": 0.55,
        "threat": 0.65,
        "window": 0.70,
        "ready": 0.85,
    }
    frames: list[UiAnimationFrame] = []
    for phase in ENCOUNTER_BRIEFING_PHASES:
        focused_screen = _encounter_briefing_overlay(
            screen,
            phase=phase,
            language=language,
            width=width,
            unicode_mode=unicode_mode,
        )
        frames.append(
            UiAnimationFrame(
                phase=phase,
                delay_multiplier=multipliers[phase],
                text=_compose_ui_animation_frame(
                    focused_screen,
                    title=_encounter_briefing_title(language),
                    phase=phase,
                    phases=ENCOUNTER_BRIEFING_PHASES,
                    language=language,
                    width=width,
                    unicode_mode=unicode_mode,
                    extra_lines=_encounter_briefing_signal_lines(
                        phase,
                        language=language,
                        width=max(12, width - 4),
                        unicode_mode=unicode_mode,
                    ),
                    detail=_encounter_briefing_detail(phase, language),
                    tone="hero" if phase == "ready" else "counter",
                ),
            )
        )
    return tuple(frames)


def build_battle_result_animation_frames(
    screen: str,
    *,
    result: str | None = None,
    language: str = "en",
    width: int = 100,
    unicode_mode: bool = False,
) -> tuple[UiAnimationFrame, ...]:
    """Return staged display-only frames for a resolved battle report."""
    multipliers = {
        "result": 0.75,
        "reveal": 0.80,
        "next": 0.90,
    }
    frames: list[UiAnimationFrame] = []
    for phase in BATTLE_RESULT_PHASES:
        focused_screen = _battle_result_overlay(
            screen,
            phase=phase,
            result=result,
            language=language,
            width=width,
            unicode_mode=unicode_mode,
        )
        frames.append(
            UiAnimationFrame(
                phase=phase,
                delay_multiplier=multipliers[phase],
                text=_compose_ui_animation_frame(
                    focused_screen,
                    title=_battle_result_title(language),
                    phase=phase,
                    phases=BATTLE_RESULT_PHASES,
                    language=language,
                    width=width,
                    unicode_mode=unicode_mode,
                    extra_lines=_battle_result_signal_lines(
                        phase,
                        result=result,
                        language=language,
                        width=max(12, width - 4),
                        unicode_mode=unicode_mode,
                    ),
                    detail=_battle_result_detail(phase, result, language),
                    tone="climax" if phase == "result" else "counter",
                ),
            )
        )
    return tuple(frames)


def build_reward_reveal_animation_frames(
    screen: str,
    *,
    gold: int = 0,
    xp: int = 0,
    choice_count: int = 0,
    language: str = "en",
    width: int = 100,
    unicode_mode: bool = False,
) -> tuple[UiAnimationFrame, ...]:
    """Return staged display-only frames for a resolved reward reveal."""
    multipliers = {
        "drop": 0.65,
        "cards": 0.80,
        "handoff": 0.90,
    }
    frames: list[UiAnimationFrame] = []
    for phase in REWARD_REVEAL_PHASES:
        focused_screen = _reward_reveal_overlay(
            screen,
            phase=phase,
            gold=gold,
            xp=xp,
            choice_count=choice_count,
            language=language,
            width=width,
            unicode_mode=unicode_mode,
        )
        frames.append(
            UiAnimationFrame(
                phase=phase,
                delay_multiplier=multipliers[phase],
                text=_compose_ui_animation_frame(
                    focused_screen,
                    title=_reward_reveal_title(language),
                    phase=phase,
                    phases=REWARD_REVEAL_PHASES,
                    language=language,
                    width=width,
                    unicode_mode=unicode_mode,
                    extra_lines=_reward_reveal_signal_lines(
                        phase,
                        gold=gold,
                        xp=xp,
                        choice_count=choice_count,
                        language=language,
                        width=max(12, width - 4),
                        unicode_mode=unicode_mode,
                    ),
                    detail=_reward_reveal_detail(
                        phase,
                        gold=gold,
                        xp=xp,
                        choice_count=choice_count,
                        language=language,
                    ),
                    tone="hero" if phase != "drop" else "climax",
                ),
            )
        )
    return tuple(frames)


def _reward_reveal_overlay(
    screen: str,
    *,
    phase: str,
    gold: int,
    xp: int,
    choice_count: int,
    language: str,
    width: int,
    unicode_mode: bool,
) -> str:
    """Decorate reward-choice lines without mutating run rewards."""
    safe_width = max(40, width)
    status = _reward_reveal_status_line(
        phase,
        gold=gold,
        xp=xp,
        choice_count=choice_count,
        language=language,
        unicode_mode=unicode_mode,
    )
    marker = _reward_reveal_marker(
        phase,
        language=language,
        unicode_mode=unicode_mode,
    )
    decorated: list[str] = [fit_text(status, safe_width)]
    matched = False
    for line in screen.splitlines():
        if _line_targets_reward_reveal_phase(line, phase):
            decorated.append(fit_text(f"{marker} {line.rstrip()}", safe_width))
            matched = True
        else:
            decorated.append(line)
    if not matched:
        decorated.insert(
            1,
            fit_text(
                f"{marker} {_reward_reveal_fallback(phase, gold, xp, choice_count, language)}",
                safe_width,
            ),
        )
    return "\n".join(decorated)


def _line_targets_reward_reveal_phase(line: str, phase: str) -> bool:
    targets = {
        "drop": (
            "+",
            "Gold:",
            "XP:",
            "金币",
            "经验",
            "REWARD FOCUS RAIL",
            "奖励焦点",
        ),
        "cards": (
            "REWARD BUILD TRACK",
            "PICK PRIORITY BOARD",
            "[1]",
            "[2]",
            "[3]",
            "奖励构筑轨道",
            "选择优先级面板",
        ),
        "handoff": (
            "CHOOSE YOUR REWARD",
            "REWARD COMMAND RAIL",
            "Select a reward",
            "选择你的奖励",
            "奖励命令",
            "选择一个奖励",
        ),
    }
    return any(token in line for token in targets.get(phase, targets["drop"]))


def _reward_reveal_status_line(
    phase: str,
    *,
    gold: int,
    xp: int,
    choice_count: int,
    language: str,
    unicode_mode: bool,
) -> str:
    prefix = "掉落覆盖" if language == "zh" else "LOOT OVERLAY"
    label = _reward_reveal_phase_label(phase, language)
    pulse = _reward_reveal_pulse(phase, unicode_mode=unicode_mode)
    summary = _reward_reveal_summary(gold, xp, choice_count, language)
    if language == "zh":
        return f"{prefix} {label} | {summary} | {pulse}"
    return f"{prefix} {label} | {summary} | {pulse}"


def _reward_reveal_marker(phase: str, *, language: str, unicode_mode: bool) -> str:
    label = _reward_reveal_phase_label(phase, language)
    if unicode_mode:
        return f"█{label}█"
    return f">>{label}"


def _reward_reveal_fallback(
    phase: str,
    gold: int,
    xp: int,
    choice_count: int,
    language: str,
) -> str:
    summary = _reward_reveal_summary(gold, xp, choice_count, language)
    if language == "zh":
        return {
            "drop": f"掉落写入完成: {summary}",
            "cards": f"{choice_count} 张奖励候选卡显影",
            "handoff": "交接到奖励选择输入",
        }[phase]
    return {
        "drop": f"reward drop recorded: {summary}",
        "cards": f"{choice_count} reward cards reveal",
        "handoff": "handoff to reward choice input",
    }[phase]


def _reward_reveal_signal_lines(
    phase: str,
    *,
    gold: int,
    xp: int,
    choice_count: int,
    language: str,
    width: int,
    unicode_mode: bool,
) -> tuple[str, ...]:
    lines = (
        _reward_reveal_rail(phase, language=language, unicode_mode=unicode_mode),
        _reward_reveal_lens(
            phase,
            gold=gold,
            xp=xp,
            choice_count=choice_count,
            language=language,
        ),
        _reward_reveal_pulse_line(phase, language=language, unicode_mode=unicode_mode),
        _reward_reveal_state(phase, language=language),
    )
    return tuple(fit_text(line, width) for line in lines)


def _reward_reveal_rail(phase: str, *, language: str, unicode_mode: bool) -> str:
    tokens: list[str] = []
    for slot in REWARD_REVEAL_PHASES:
        label = _reward_reveal_phase_label(slot, language)
        if slot == phase:
            tokens.append(f"{'█' if unicode_mode else '>'}{label}{'█' if unicode_mode else '<'}")
        else:
            tokens.append(f"[{label}]")
    joiner = "──" if unicode_mode else "--"
    prefix = "掉落轨 " if language == "zh" else "LOOT RAIL "
    return prefix + joiner.join(tokens)


def _reward_reveal_lens(
    phase: str,
    *,
    gold: int,
    xp: int,
    choice_count: int,
    language: str,
) -> str:
    if language == "zh":
        return {
            "drop": f"镜头 金币 +{gold} / 经验 +{xp}",
            "cards": f"镜头 {choice_count} 张候选奖励卡显影",
            "handoff": "镜头 奖励选择输入即将接管",
        }[phase]
    return {
        "drop": f"LENS gold +{gold} / xp +{xp}",
        "cards": f"LENS {choice_count} reward cards surface",
        "handoff": "LENS reward choice input takes over",
    }[phase]


def _reward_reveal_pulse_line(
    phase: str,
    *,
    language: str,
    unicode_mode: bool,
) -> str:
    patterns = {
        "drop": "█▓░░░" if unicode_mode else ">>---",
        "cards": "███▓░" if unicode_mode else "_>>>-",
        "handoff": "████▓" if unicode_mode else "__>>>",
    }
    if language == "zh":
        text = {
            "drop": "掉落弹出",
            "cards": "卡牌显影",
            "handoff": "交接选择",
        }[phase]
        return f"掉落脉冲 {patterns[phase]} {text}"
    text = {
        "drop": "drop pops",
        "cards": "cards reveal",
        "handoff": "choice handoff",
    }[phase]
    return f"LOOT PULSE {patterns[phase]} {text}"


def _reward_reveal_state(phase: str, *, language: str) -> str:
    if language == "zh":
        return {
            "drop": "状态 只展示已写入奖励 | 本局状态不改写",
            "cards": "状态 候选奖励镜头在线 | 未自动选择",
            "handoff": "状态 显影完成 | 下一帧等待选择",
        }[phase]
    return {
        "drop": "STATE display only | reward state unchanged",
        "cards": "STATE reward lens online | no choice selected",
        "handoff": "STATE reveal complete | choice waits next",
    }[phase]


def _reward_reveal_detail(
    phase: str,
    *,
    gold: int,
    xp: int,
    choice_count: int,
    language: str,
) -> str:
    if language == "zh":
        return {
            "drop": f"掉落 本地奖励已写入：金币 +{gold} / 经验 +{xp}",
            "cards": f"卡牌 {choice_count} 个候选项显影；只展示，不选择",
            "handoff": "交接 进入奖励选择等待态或自动锁定",
        }[phase]
    return {
        "drop": f"DROP local reward recorded: gold +{gold} / xp +{xp}",
        "cards": f"CARDS {choice_count} candidates reveal; display only",
        "handoff": "HANDOFF enter reward wait or auto-lock",
    }[phase]


def _reward_reveal_title(language: str) -> str:
    return "奖励显影" if language == "zh" else "LOOT REVEAL"


def _reward_reveal_phase_label(phase: str, language: str) -> str:
    labels = {
        "drop": {"en": "DROP", "zh": "掉落"},
        "cards": {"en": "CARDS", "zh": "卡牌"},
        "handoff": {"en": "HANDOFF", "zh": "交接"},
    }
    values = labels.get(phase, {})
    return values.get(language, values.get("en", phase.upper()))


def _reward_reveal_pulse(phase: str, *, unicode_mode: bool) -> str:
    if unicode_mode:
        return {
            "drop": "█░░",
            "cards": "██░",
            "handoff": "███",
        }[phase]
    return {
        "drop": ">..",
        "cards": ">>.",
        "handoff": ">>>",
    }[phase]


def _reward_reveal_summary(
    gold: int,
    xp: int,
    choice_count: int,
    language: str,
) -> str:
    if language == "zh":
        return f"金币 +{gold} / 经验 +{xp} / 候选 {choice_count}"
    return f"gold +{gold} / xp +{xp} / choices {choice_count}"


def _battle_result_overlay(
    screen: str,
    *,
    phase: str,
    result: str | None,
    language: str,
    width: int,
    unicode_mode: bool,
) -> str:
    """Decorate resolved report lines without mutating battle or run state."""
    safe_width = max(40, width)
    status = _battle_result_status_line(
        phase,
        result=result,
        language=language,
        unicode_mode=unicode_mode,
    )
    marker = _battle_result_marker(
        phase,
        language=language,
        unicode_mode=unicode_mode,
    )
    decorated: list[str] = [fit_text(status, safe_width)]
    matched = False
    for line in screen.splitlines():
        if _line_targets_battle_result_phase(line, phase):
            decorated.append(fit_text(f"{marker} {line.rstrip()}", safe_width))
            matched = True
        else:
            decorated.append(line)
    if not matched:
        decorated.insert(1, fit_text(f"{marker} {_battle_result_fallback(phase, result, language)}", safe_width))
    return "\n".join(decorated)


def _line_targets_battle_result_phase(line: str, phase: str) -> bool:
    targets = {
        "result": (
            "AFTER-ACTION STAGE",
            "BATTLE RESULT BOARD",
            "RESULT RAIL",
            "[RESULT]",
            "战后结算镜头",
            "战斗结果板",
            "结果轨道",
            "[结果]",
        ),
        "reveal": (
            "FALLEN ENEMY",
            "DAMAGE RAIL",
            "BATTLE TURN MAP",
            "CODEX REVEAL",
            "倒下敌方",
            "伤害轨道",
            "战斗回合轨道",
            "图鉴揭示",
        ),
        "next": (
            "NEXT LENS",
            "PLAY NEXT BOARD",
            "[NEXT]",
            "[REMATCH]",
            "[GUIDANCE]",
            "下一镜头",
            "下一局闭环面板",
            "[下一步]",
            "[重开]",
            "[建议]",
        ),
    }
    return any(token in line for token in targets.get(phase, targets["result"]))


def _battle_result_status_line(
    phase: str,
    *,
    result: str | None,
    language: str,
    unicode_mode: bool,
) -> str:
    prefix = "落幕覆盖" if language == "zh" else "OUTCOME OVERLAY"
    label = _battle_result_phase_label(phase, language)
    pulse = _battle_result_pulse(phase, unicode_mode=unicode_mode)
    outcome = _battle_result_value(result, language)
    if language == "zh":
        return f"{prefix} {label} | 结果 {outcome} | {pulse}"
    return f"{prefix} {label} | result {outcome} | {pulse}"


def _battle_result_marker(phase: str, *, language: str, unicode_mode: bool) -> str:
    label = _battle_result_phase_label(phase, language)
    if unicode_mode:
        return f"█{label}█"
    return f">>{label}"


def _battle_result_fallback(phase: str, result: str | None, language: str) -> str:
    outcome = _battle_result_value(result, language)
    if language == "zh":
        return {
            "result": f"本地裁判完成结算: {outcome}",
            "reveal": "倒下敌影与图鉴线索揭示",
            "next": "下一局行动交接",
        }[phase]
    return {
        "result": f"local judge resolved: {outcome}",
        "reveal": "fallen enemy and codex cues reveal",
        "next": "next fight loop handed off",
    }[phase]


def _battle_result_signal_lines(
    phase: str,
    *,
    result: str | None,
    language: str,
    width: int,
    unicode_mode: bool,
) -> tuple[str, ...]:
    lines = (
        _battle_result_rail(phase, language=language, unicode_mode=unicode_mode),
        _battle_result_lens(phase, result=result, language=language),
        _battle_result_pulse_line(phase, language=language, unicode_mode=unicode_mode),
        _battle_result_state(phase, language=language),
    )
    return tuple(fit_text(line, width) for line in lines)


def _battle_result_rail(phase: str, *, language: str, unicode_mode: bool) -> str:
    tokens: list[str] = []
    for slot in BATTLE_RESULT_PHASES:
        label = _battle_result_phase_label(slot, language)
        if slot == phase:
            tokens.append(f"{'█' if unicode_mode else '>'}{label}{'█' if unicode_mode else '<'}")
        else:
            tokens.append(f"[{label}]")
    joiner = "──" if unicode_mode else "--"
    prefix = "落幕轨 " if language == "zh" else "OUTCOME RAIL "
    return prefix + joiner.join(tokens)


def _battle_result_lens(phase: str, *, result: str | None, language: str) -> str:
    outcome = _battle_result_value(result, language)
    if language == "zh":
        return {
            "result": f"镜头 本地裁判锁定 {outcome}",
            "reveal": "镜头 倒下敌影、伤害轨和回合轨",
            "next": "镜头 下一局、复盘和重开命令",
        }[phase]
    return {
        "result": f"LENS local judge locks {outcome}",
        "reveal": "LENS fallen enemy, damage rail, and turn map",
        "next": "LENS review, codex, and rematch commands",
    }[phase]


def _battle_result_pulse_line(
    phase: str,
    *,
    language: str,
    unicode_mode: bool,
) -> str:
    patterns = {
        "result": "█▓░░░" if unicode_mode else ">>---",
        "reveal": "███▓░" if unicode_mode else "_>>>-",
        "next": "████▓" if unicode_mode else "__>>>",
    }
    if language == "zh":
        text = {
            "result": "判定落幕",
            "reveal": "敌影揭示",
            "next": "交接下一步",
        }[phase]
        return f"落幕脉冲 {patterns[phase]} {text}"
    text = {
        "result": "result settles",
        "reveal": "fallen cues reveal",
        "next": "next loop handoff",
    }[phase]
    return f"OUTCOME PULSE {patterns[phase]} {text}"


def _battle_result_state(phase: str, *, language: str) -> str:
    if language == "zh":
        return {
            "result": "状态 只展示已结算结果 | 战斗状态未改写",
            "reveal": "状态 图鉴与战报镜头在线 | 奖励尚未写入",
            "next": "状态 收束完成 | 下一帧输出稳定战报",
        }[phase]
    return {
        "result": "STATE display only | battle state unchanged",
        "reveal": "STATE codex/report lens online | rewards untouched",
        "next": "STATE outcome complete | stable report prints next",
    }[phase]


def _battle_result_detail(phase: str, result: str | None, language: str) -> str:
    outcome = _battle_result_value(result, language)
    if language == "zh":
        return {
            "result": f"结算 本地裁判已确认 {outcome}",
            "reveal": "揭示 倒下敌影、图鉴剪影和伤害轨成为复盘焦点",
            "next": "下一步 保留复盘、图鉴、配置和重开路径",
        }[phase]
    return {
        "result": f"RESULT local judge confirms {outcome}",
        "reveal": "REVEAL fallen enemy, codex silhouette, and damage rail",
        "next": "NEXT keep review, codex, loadout, and rematch paths visible",
    }[phase]


def _battle_result_title(language: str) -> str:
    return "战斗落幕" if language == "zh" else "BATTLE OUTCOME"


def _battle_result_phase_label(phase: str, language: str) -> str:
    labels = {
        "result": {"en": "RESULT", "zh": "结算"},
        "reveal": {"en": "REVEAL", "zh": "揭示"},
        "next": {"en": "NEXT", "zh": "下一步"},
    }
    values = labels.get(phase, {})
    return values.get(language, values.get("en", phase.upper()))


def _battle_result_pulse(phase: str, *, unicode_mode: bool) -> str:
    if unicode_mode:
        return {
            "result": "█░░",
            "reveal": "██░",
            "next": "███",
        }[phase]
    return {
        "result": ">..",
        "reveal": ">>.",
        "next": ">>>",
    }[phase]


def _battle_result_value(result: str | None, language: str) -> str:
    value = (result or "ongoing").lower()
    if language == "zh":
        return {
            "victory": "胜利",
            "defeat": "失败",
            "timeout": "超时",
            "ongoing": "进行中",
        }.get(value, value)
    return value


def _encounter_briefing_overlay(
    screen: str,
    *,
    phase: str,
    language: str,
    width: int,
    unicode_mode: bool,
) -> str:
    """Decorate encounter briefing lines without mutating battle state."""
    safe_width = max(40, width)
    status = _encounter_briefing_status_line(
        phase,
        language=language,
        unicode_mode=unicode_mode,
    )
    marker = _encounter_briefing_marker(
        phase,
        language=language,
        unicode_mode=unicode_mode,
    )
    decorated: list[str] = [fit_text(status, safe_width)]
    matched = False
    for line in screen.splitlines():
        if _line_targets_encounter_phase(line, phase, language):
            decorated.append(fit_text(f"{marker} {line.rstrip()}", safe_width))
            matched = True
        else:
            decorated.append(line)
    if not matched:
        decorated.insert(1, fit_text(f"{marker} {_encounter_briefing_fallback(phase, language)}", safe_width))
    return "\n".join(decorated)


def _line_targets_encounter_phase(line: str, phase: str, language: str) -> bool:
    targets = {
        "scout": (
            "MINI STAGE",
            "HERO ",
            "ENEMY ",
            "入场镜头",
            "英雄 ",
            "敌方 ",
        ),
        "threat": ("THREAT RAIL", "[THREAT]", "威胁轨道", "[威胁]"),
        "window": ("WINDOW RAIL", "[WINDOW]", "窗口轨道", "[窗口]"),
        "ready": ("[PLAN]", "[计划]", "BRIEF FIELDS:", "简报字段:"),
    }
    return any(token in line for token in targets.get(phase, targets["scout"]))


def _encounter_briefing_status_line(
    phase: str,
    *,
    language: str,
    unicode_mode: bool,
) -> str:
    prefix = "简报覆盖" if language == "zh" else "BRIEFING OVERLAY"
    label = _encounter_briefing_phase_label(phase, language)
    pulse = _encounter_briefing_pulse(phase, unicode_mode=unicode_mode)
    return f"{prefix} {label} | {pulse}"


def _encounter_briefing_marker(phase: str, *, language: str, unicode_mode: bool) -> str:
    label = _encounter_briefing_phase_label(phase, language)
    if unicode_mode:
        return f"█{label}█"
    return f">>{label}"


def _encounter_briefing_fallback(phase: str, language: str) -> str:
    if language == "zh":
        return {
            "scout": "英雄与敌方剪影入场",
            "threat": "锁定主威胁",
            "window": "确认反制窗口",
            "ready": "开局计划交接",
        }[phase]
    return {
        "scout": "hero and enemy silhouettes staged",
        "threat": "primary threat locked",
        "window": "counter window confirmed",
        "ready": "opening plan handed off",
    }[phase]


def _encounter_briefing_signal_lines(
    phase: str,
    *,
    language: str,
    width: int,
    unicode_mode: bool,
) -> tuple[str, ...]:
    lines = (
        _encounter_briefing_rail(phase, language=language, unicode_mode=unicode_mode),
        _encounter_briefing_lens(phase, language=language),
        _encounter_briefing_pulse_line(phase, language=language, unicode_mode=unicode_mode),
        _encounter_briefing_state(phase, language=language),
    )
    return tuple(fit_text(line, width) for line in lines)


def _encounter_briefing_rail(phase: str, *, language: str, unicode_mode: bool) -> str:
    tokens: list[str] = []
    for slot in ENCOUNTER_BRIEFING_PHASES:
        label = _encounter_briefing_phase_label(slot, language)
        if slot == phase:
            tokens.append(f"{'█' if unicode_mode else '>'}{label}{'█' if unicode_mode else '<'}")
        else:
            tokens.append(f"[{label}]")
    joiner = "──" if unicode_mode else "--"
    prefix = "入场轨 " if language == "zh" else "ENTRY RAIL "
    return prefix + joiner.join(tokens)


def _encounter_briefing_lens(phase: str, *, language: str) -> str:
    if language == "zh":
        return {
            "scout": "镜头 英雄/敌方剪影对位",
            "threat": "镜头 主威胁与 ATB 压力",
            "window": "镜头 反制窗口与保留资源",
            "ready": "镜头 开局计划交给模型行动",
        }[phase]
    return {
        "scout": "LENS hero/enemy silhouettes align",
        "threat": "LENS primary threat and ATB pressure",
        "window": "LENS counter window and reserve resource",
        "ready": "LENS opening plan hands off to model action",
    }[phase]


def _encounter_briefing_pulse_line(
    phase: str,
    *,
    language: str,
    unicode_mode: bool,
) -> str:
    patterns = {
        "scout": "█▓░░░░░" if unicode_mode else ">>---__",
        "threat": "██▓░░░░" if unicode_mode else "_>>---_",
        "window": "████▓░░" if unicode_mode else "__>>>--",
        "ready": "██████▓" if unicode_mode else "____>>>",
    }
    if language == "zh":
        text = {
            "scout": "扫描站位",
            "threat": "锁定威胁",
            "window": "确认窗口",
            "ready": "准备开战",
        }[phase]
        return f"入场脉冲 {patterns[phase]} {text}"
    text = {
        "scout": "scanning lineup",
        "threat": "threat lock",
        "window": "window confirm",
        "ready": "battle handoff",
    }[phase]
    return f"ENTRY PULSE {patterns[phase]} {text}"


def _encounter_briefing_state(phase: str, *, language: str) -> str:
    if language == "zh":
        return {
            "scout": "状态 只预览 | 战斗状态未改写",
            "threat": "状态 威胁镜头在线 | 本地裁判待命",
            "window": "状态 反制窗口在线 | 资源压力可见",
            "ready": "状态 入场完成 | 下一帧进入战斗",
        }[phase]
    return {
        "scout": "STATE preview only | battle state unchanged",
        "threat": "STATE threat lens online | local judge standing by",
        "window": "STATE counter window online | resource pressure visible",
        "ready": "STATE briefing complete | next frame enters battle",
    }[phase]


def _encounter_briefing_detail(phase: str, language: str) -> str:
    if language == "zh":
        return {
            "scout": "侦察 建立英雄、敌方和战场站位",
            "threat": "威胁 标记主威胁；玩家先读风险再看行动",
            "window": "窗口 标记反制窗口；保留 MP/冷却认知",
            "ready": "就绪 开局计划就绪；模型下一步选择行动",
        }[phase]
    return {
        "scout": "SCOUT staging hero, enemies, and battlefield lanes",
        "threat": "THREAT marks the main risk before action starts",
        "window": "WINDOW marks counter timing and resource reserve",
        "ready": "READY opening plan armed; model chooses next",
    }[phase]


def _encounter_briefing_title(language: str) -> str:
    return "遭遇简报" if language == "zh" else "ENCOUNTER BRIEFING"


def _encounter_briefing_phase_label(phase: str, language: str) -> str:
    labels = {
        "scout": {"en": "SCOUT", "zh": "侦察"},
        "threat": {"en": "THREAT", "zh": "威胁"},
        "window": {"en": "WINDOW", "zh": "窗口"},
        "ready": {"en": "READY", "zh": "就绪"},
    }
    values = labels.get(phase, {})
    return values.get(language, values.get("en", phase.upper()))


def _encounter_briefing_pulse(phase: str, *, unicode_mode: bool) -> str:
    if unicode_mode:
        return {
            "scout": "█░░░",
            "threat": "██░░",
            "window": "███░",
            "ready": "████",
        }[phase]
    return {
        "scout": ">...",
        "threat": ">>..",
        "window": ">>>.",
        "ready": ">>>>",
    }[phase]


def _choice_focus_overlay(
    screen: str,
    *,
    phase: str,
    selected_index: int,
    selected_label: str | None,
    language: str,
    width: int,
    unicode_mode: bool,
) -> str:
    """Decorate the selected choice lines without mutating run state."""
    safe_width = max(40, width)
    lines = screen.splitlines()
    focus_line = _choice_focus_status_line(
        phase,
        selected_index=selected_index,
        selected_label=selected_label,
        language=language,
        unicode_mode=unicode_mode,
    )
    marker = _choice_focus_marker(phase, language=language, unicode_mode=unicode_mode)
    matched = False
    decorated: list[str] = [fit_text(focus_line, safe_width)]
    for line in lines:
        if selected_index > 0 and _line_targets_choice(line, selected_index):
            decorated.append(fit_text(f"{marker} {line.rstrip()}", safe_width))
            matched = True
        else:
            decorated.append(line)
    if selected_index >= 0 and not matched:
        choice_label = _choice_lock_choice_label(selected_index, selected_label)
        decorated.insert(1, fit_text(f"{marker} {choice_label}", safe_width))
    return "\n".join(decorated)


def _choice_focus_status_line(
    phase: str,
    *,
    selected_index: int,
    selected_label: str | None,
    language: str,
    unicode_mode: bool,
) -> str:
    choice = _choice_lock_choice_label(selected_index, selected_label)
    label = _choice_focus_phase_label(phase, language)
    prefix = "焦点覆盖" if language == "zh" else "FOCUS OVERLAY"
    pulse = _choice_focus_pulse(phase, unicode_mode=unicode_mode)
    if language == "zh":
        return f"{prefix} {label} {choice} | {pulse}"
    return f"{prefix} {label} {choice} | {pulse}"


def _choice_focus_marker(phase: str, *, language: str, unicode_mode: bool) -> str:
    label = _choice_focus_phase_label(phase, language)
    if unicode_mode:
        return f"█{label}█"
    return f">>{label}"


def _choice_focus_phase_label(phase: str, language: str) -> str:
    labels = {
        "scan": {"en": "SCAN", "zh": "扫描"},
        "focus": {"en": "FOCUS", "zh": "聚焦"},
        "lock": {"en": "LOCK", "zh": "锁定"},
    }
    values = labels.get(phase, {})
    return values.get(language, values.get("en", phase.upper()))


def _choice_focus_pulse(phase: str, *, unicode_mode: bool) -> str:
    if unicode_mode:
        return {
            "scan": "█░░",
            "focus": "██░",
            "lock": "███",
        }.get(phase, "█░░")
    return {
        "scan": ">..",
        "focus": ">>.",
        "lock": ">>>",
    }.get(phase, ">..")


def _line_targets_choice(line: str, selected_index: int) -> bool:
    token = f"[{selected_index}]"
    map_token = f"[{selected_index}:"
    return token in line or map_token in line


def _compose_ui_animation_frame(
    payload: str,
    *,
    title: str,
    phase: str,
    phases: tuple[str, ...],
    language: str,
    width: int,
    unicode_mode: bool,
    detail: str,
    tone: str,
    extra_lines: tuple[str, ...] = (),
) -> str:
    safe_width = max(40, width)
    hud = pixel_panel(
        f"{title} / {_phase_label(phase, language)}",
        [
            _phase_strip(phases, active=phase, language=language, unicode_mode=unicode_mode),
            *extra_lines,
            *_motion_director_lines(
                phase,
                language=language,
                width=safe_width - 4,
                unicode_mode=unicode_mode,
            ),
            detail,
        ],
        safe_width,
        tone=tone,
    )
    return "\n".join((*hud.lines, "", *_fit_payload(payload, safe_width)))


def _fit_payload(payload: str, width: int) -> tuple[str, ...]:
    fitted: list[str] = []
    for line in payload.splitlines():
        if visual_width(line) <= width:
            fitted.append(line.rstrip())
        else:
            fitted.append(fit_text(line, width))
    return tuple(fitted)


def _phase_strip(
    phases: tuple[str, ...],
    *,
    active: str,
    language: str,
    unicode_mode: bool,
) -> str:
    parts: list[str] = []
    for phase in phases:
        label = _short_phase_label(phase, language)
        if phase == active:
            parts.append(f"{'█' if unicode_mode else '>'}{label}{'█' if unicode_mode else '<'}")
        else:
            parts.append(f"[{label}]")
    return "PHASE " + " ".join(parts) if language == "en" else "阶段 " + " ".join(parts)


def _mode_select_title(language: str) -> str:
    return "MODE SELECT" if language == "en" else "模式选择"


def _choice_lock_title(kind: str, language: str) -> str:
    if language == "zh":
        return {
            "route": "路线锁定",
            "reward": "奖励锁定",
            "rest": "休整锁定",
            "event": "事件锁定",
            "shop": "商店锁定",
        }.get(kind, "选择锁定")
    return {
        "route": "ROUTE LOCK",
        "reward": "REWARD LOCK",
        "rest": "REST LOCK",
        "event": "EVENT LOCK",
        "shop": "SHOP LOCK",
    }.get(kind, "CHOICE LOCK")


def _mode_select_detail(phase: str, language: str) -> str:
    if language == "zh":
        return {
            "agent": "FOCUS 英雄槽接入；读取构筑、武器和初始资源",
            "prompt": "FOCUS 提示词预设接入；模型只选择行动",
            "judge": "FOCUS 本地裁判接入；伤害、掉落和胜负由规则决定",
            "ready": "LOCK 试玩舞台已装配；进入可观看战斗",
        }[phase]
    return {
        "agent": "FOCUS agent slot online; build, weapon, resources loaded",
        "prompt": "FOCUS prompt mode online; model only chooses actions",
        "judge": "FOCUS local judge online; rules own outcomes",
        "ready": "LOCK stage armed; entering watchable combat",
    }[phase]


def _mode_select_ritual_lines(
    phase: str,
    *,
    language: str,
    width: int,
    unicode_mode: bool,
) -> tuple[str, ...]:
    """Return Claude-style mode dial lines without touching gameplay state."""
    lines = (
        _mode_select_ritual_dial(phase, language=language, unicode_mode=unicode_mode),
        _mode_select_pulse(phase, language=language, unicode_mode=unicode_mode),
        _mode_select_status(language),
    )
    return tuple(fit_text(line, width) for line in lines)


def _mode_select_ritual_dial(
    phase: str,
    *,
    language: str,
    unicode_mode: bool,
) -> str:
    slots = ("agent", "prompt", "judge", "ready")
    tokens: list[str] = []
    for slot in slots:
        label = _mode_select_slot_label(slot, language)
        if slot == phase:
            tokens.append(f"{'█' if unicode_mode else '>'}{label}{'█' if unicode_mode else '<'}")
        else:
            tokens.append(f"[{label}]")
    joiner = "──" if unicode_mode else "--"
    prefix = "仪式拨盘 " if language == "zh" else "RITUAL DIAL "
    return prefix + joiner.join(tokens)


def _mode_select_slot_label(phase: str, language: str) -> str:
    labels = {
        "agent": {"en": "AGENT", "zh": "英雄"},
        "prompt": {"en": "PROMPT", "zh": "提示词"},
        "judge": {"en": "JUDGE", "zh": "裁判"},
        "ready": {"en": "STAGE", "zh": "舞台"},
    }
    values = labels.get(phase, {})
    return values.get(language, values.get("en", phase.upper()))


def _mode_select_pulse(
    phase: str,
    *,
    language: str,
    unicode_mode: bool,
) -> str:
    ascii_patterns = {
        "agent": ">>>---____",
        "prompt": "__>>>---__",
        "judge": "____>>>--_",
        "ready": "______>>>>",
    }
    unicode_patterns = {
        "agent": "█▓▒░░░░░░░",
        "prompt": "░░█▓▒░░░░░",
        "judge": "░░░░█▓▒░░░",
        "ready": "░░░░░░█▓▒█",
    }
    phase_text = {
        "agent": {"en": "agent slot waking", "zh": "英雄槽唤醒"},
        "prompt": {"en": "prompt bias syncing", "zh": "提示词倾向同步"},
        "judge": {"en": "local judge arming", "zh": "本地裁判上锁"},
        "ready": {"en": "stage handoff ready", "zh": "舞台交接就绪"},
    }.get(phase, {"en": phase, "zh": phase})
    label_text = "脉冲" if language == "zh" else "PULSE"
    pattern = (unicode_patterns if unicode_mode else ascii_patterns).get(
        phase,
        unicode_patterns["prompt"] if unicode_mode else ascii_patterns["prompt"],
    )
    return f"{label_text} {pattern} {phase_text.get(language, phase_text['en'])}"


def _mode_select_status(language: str) -> str:
    if language == "zh":
        return "状态 mock 离线 | seed 锁定 | 本地裁判结算"
    return "STATUS mock offline | seed locked | local judge rules"


def _choice_lock_signal_lines(
    phase: str,
    *,
    selected_index: int,
    selected_label: str | None,
    language: str,
    width: int,
    unicode_mode: bool,
) -> tuple[str, ...]:
    """Return lock-on HUD lines for route/reward/shop/rest/event choices."""
    choice = _choice_lock_choice_label(selected_index, selected_label)
    lines = (
        _choice_lock_rail(phase, language=language, unicode_mode=unicode_mode),
        _choice_lock_target(choice, language=language),
        _choice_lock_pulse(phase, language=language, unicode_mode=unicode_mode),
        _choice_lock_state(phase, language=language),
    )
    return tuple(fit_text(line, width) for line in lines)


def _choice_lock_choice_label(selected_index: int, selected_label: str | None) -> str:
    choice = f"[{selected_index}]"
    if selected_label:
        choice += f" {selected_label}"
    return choice


def _choice_lock_rail(
    phase: str,
    *,
    language: str,
    unicode_mode: bool,
) -> str:
    tokens: list[str] = []
    for slot in CHOICE_LOCK_PHASES:
        label = _choice_lock_slot_label(slot, language)
        if slot == phase:
            tokens.append(f"{'█' if unicode_mode else '>'}{label}{'█' if unicode_mode else '<'}")
        else:
            tokens.append(f"[{label}]")
    joiner = "──" if unicode_mode else "--"
    prefix = "锁定轨 " if language == "zh" else "LOCK RAIL "
    return prefix + joiner.join(tokens)


def _choice_lock_slot_label(phase: str, language: str) -> str:
    labels = {
        "scan": {"en": "SCAN", "zh": "扫描"},
        "focus": {"en": "FOCUS", "zh": "聚焦"},
        "lock": {"en": "CONFIRM", "zh": "确认"},
    }
    values = labels.get(phase, {})
    return values.get(language, values.get("en", phase.upper()))


def _choice_lock_target(choice: str, *, language: str) -> str:
    return f"目标 {choice}" if language == "zh" else f"TARGET {choice}"


def _choice_lock_pulse(
    phase: str,
    *,
    language: str,
    unicode_mode: bool,
) -> str:
    ascii_patterns = {
        "scan": ">>>---____",
        "focus": "__>>>---__",
        "lock": "______>>>>",
    }
    unicode_patterns = {
        "scan": "█▓▒░░░░░░░",
        "focus": "░░█▓▒░░░░░",
        "lock": "░░░░░░█▓▒█",
    }
    pulse_text = {
        "scan": {"en": "reading choices", "zh": "读取选项"},
        "focus": {"en": "preview deltas", "zh": "预览变化"},
        "lock": {"en": "confirm armed", "zh": "确认就绪"},
    }.get(phase, {"en": phase, "zh": phase})
    label = "脉冲" if language == "zh" else "PULSE"
    pattern = (unicode_patterns if unicode_mode else ascii_patterns).get(
        phase,
        unicode_patterns["scan"] if unicode_mode else ascii_patterns["scan"],
    )
    return f"{label} {pattern} {pulse_text.get(language, pulse_text['en'])}"


def _choice_lock_state(phase: str, *, language: str) -> str:
    if language == "zh":
        return {
            "scan": "状态 只预览 | 本局状态等待写入",
            "focus": "状态 构筑/资源/风险镜头在线",
            "lock": "状态 已锁定 | 动画后写入本局状态",
        }[phase]
    return {
        "scan": "STATE preview only | run state waits",
        "focus": "STATE build/resource/risk lenses online",
        "lock": "STATE selection locked | write after frame",
    }[phase]


def _choice_lock_detail(
    phase: str,
    *,
    selected_index: int,
    selected_label: str | None,
    language: str,
) -> str:
    choice = _choice_lock_choice_label(selected_index, selected_label)
    if language == "zh":
        return {
            "scan": f"SCAN 扫描可选项；当前焦点 {choice}",
            "focus": f"FOCUS 预览构筑、资源和风险变化；当前焦点 {choice}",
            "lock": f"LOCK 已锁定 {choice}；准备写入本局状态",
        }[phase]
    return {
        "scan": f"SCAN reading options; focus {choice}",
        "focus": f"FOCUS previewing build, resource, and risk deltas; focus {choice}",
        "lock": f"LOCK {choice} selected; ready to write run state",
    }[phase]


def _phase_label(phase: str, language: str) -> str:
    labels = {
        "agent": {"en": "AGENT", "zh": "英雄"},
        "prompt": {"en": "PROMPT", "zh": "提示词"},
        "judge": {"en": "JUDGE", "zh": "裁判"},
        "ready": {"en": "READY", "zh": "就绪"},
        "scan": {"en": "SCAN", "zh": "扫描"},
        "scout": {"en": "SCOUT", "zh": "侦察"},
        "threat": {"en": "THREAT", "zh": "威胁"},
        "window": {"en": "WINDOW", "zh": "窗口"},
        "result": {"en": "RESULT", "zh": "结算"},
        "reveal": {"en": "REVEAL", "zh": "揭示"},
        "next": {"en": "NEXT", "zh": "下一步"},
        "drop": {"en": "DROP", "zh": "掉落"},
        "cards": {"en": "CARDS", "zh": "卡牌"},
        "handoff": {"en": "HANDOFF", "zh": "交接"},
        "focus": {"en": "FOCUS", "zh": "聚焦"},
        "lock": {"en": "LOCK", "zh": "锁定"},
    }
    values = labels.get(phase, {})
    return values.get(language, values.get("en", phase.upper()))


def _short_phase_label(phase: str, language: str) -> str:
    label = _phase_label(phase, language)
    if language == "zh":
        return label
    return label[:6]


def _motion_director_lines(
    phase: str,
    *,
    language: str,
    width: int,
    unicode_mode: bool,
) -> tuple[str, ...]:
    active_stage = _motion_stage_for_phase(phase)
    lines = [
        _motion_stage_strip(active_stage, language=language, unicode_mode=unicode_mode),
        _motion_semantic_line("focus", phase, language),
        _motion_semantic_line("risk", phase, language),
        _motion_semantic_line("next", phase, language),
    ]
    return tuple(fit_text(line, width) for line in lines)


def _motion_stage_for_phase(phase: str) -> str:
    return {
        "agent": "threat",
        "prompt": "select",
        "scout": "threat",
        "threat": "threat",
        "window": "judge",
        "result": "judge",
        "reveal": "impact",
        "next": "meaning",
        "drop": "impact",
        "cards": "select",
        "handoff": "meaning",
        "scan": "threat",
        "focus": "select",
        "windup": "select",
        "travel": "impact",
        "impact": "impact",
        "judge": "judge",
        "lock": "meaning",
        "ready": "meaning",
    }.get(phase, "select")


def _motion_stage_strip(active_stage: str, *, language: str, unicode_mode: bool) -> str:
    parts: list[str] = []
    for stage in MOTION_DIRECTOR_STAGES:
        label = _motion_stage_label(stage, language)
        if stage == active_stage:
            parts.append(f"{'█' if unicode_mode else '>'}{label}{'█' if unicode_mode else '<'}")
        else:
            parts.append(f"[{label}]")
    return "FLOW " + " ".join(parts) if language == "en" else "流向 " + " ".join(parts)


def _motion_stage_label(stage: str, language: str) -> str:
    labels = {
        "threat": {"en": "THREAT", "zh": "威胁"},
        "select": {"en": "SELECT", "zh": "选择"},
        "impact": {"en": "IMPACT", "zh": "冲击"},
        "judge": {"en": "JUDGE", "zh": "裁判"},
        "meaning": {"en": "MEANING", "zh": "意义"},
    }
    values = labels.get(stage, {})
    return values.get(language, values.get("en", stage.upper()))


def _motion_semantic_line(kind: str, phase: str, language: str) -> str:
    if language == "zh":
        label = {"focus": "焦点", "risk": "风险", "next": "下一步"}[kind]
        values = {
            "agent": {
                "focus": "英雄、武器和构筑身份",
                "risk": "开局信息不足；先建立观看上下文",
                "next": "进入提示词与本地裁判校验",
            },
            "prompt": {
                "focus": "Prompt 倾向如何驱动模型选择",
                "risk": "模型能选择行动，但不能决定结算",
                "next": "交给本地裁判约束伤害、掉落和胜负",
            },
            "judge": {
                "focus": "本地裁判与规则边界",
                "risk": "非法行动必须降级或拒绝",
                "next": "进入可观看战斗或锁定选择",
            },
            "ready": {
                "focus": "试玩舞台、seed 和 mock provider 已就绪",
                "risk": "无真实 key；保持离线确定性",
                "next": "开始默认可观看体验",
            },
            "scout": {
                "focus": "英雄、敌方剪影和站位",
                "risk": "未读威胁前先不要判断节奏",
                "next": "锁定主威胁与 ATB 压力",
            },
            "threat": {
                "focus": "主威胁、敌方队列和风险轨道",
                "risk": "忽视威胁会错过第一反制窗口",
                "next": "确认窗口、冷却和 MP 余量",
            },
            "window": {
                "focus": "反制窗口与资源保留",
                "risk": "MP/CD 不足会让模型只能降级行动",
                "next": "交接开局计划并进入战斗",
            },
            "result": {
                "focus": "本地裁判确认的胜负与资源余量",
                "risk": "不要把战报当成新结算来源",
                "next": "揭示倒下敌影、图鉴线索和伤害轨",
            },
            "reveal": {
                "focus": "倒下敌影、图鉴剪影和回合轨",
                "risk": "复盘信息不能改写奖励或掉落",
                "next": "交接复盘、配置和重开路径",
            },
            "next": {
                "focus": "下一局行动槽和复盘入口",
                "risk": "玩家离开 live 舞台前需要明确去向",
                "next": "输出稳定战报并恢复 shell",
            },
            "drop": {
                "focus": "金币、经验和奖励写入后的可见反馈",
                "risk": "掉落显影只能读取，不能二次发放",
                "next": "显影候选卡与构筑变化",
            },
            "cards": {
                "focus": "候选奖励卡、构筑轨和优先级面板",
                "risk": "动画不能替玩家选择奖励",
                "next": "交接到等待输入或自动锁定",
            },
            "handoff": {
                "focus": "奖励选择入口和输入状态",
                "risk": "选择写入必须发生在锁定后",
                "next": "进入奖励等待态或选择锁定动效",
            },
            "scan": {
                "focus": "可选项、收益和风险",
                "risk": "盲选会错过资源、Build 或反制窗口",
                "next": "移动到具体候选项并预览变化",
            },
            "focus": {
                "focus": "当前候选项的 Build、资源和路线压力",
                "risk": "选择会改变下一战窗口",
                "next": "锁定后写入本局状态",
            },
            "lock": {
                "focus": "已选项和本局状态变化",
                "risk": "回退成本升高；准备进入下一节点",
                "next": "播放结果帧并继续 run",
            },
        }
        return f"{label} {values.get(phase, values['focus'])[kind]}"

    label = {"focus": "FOCUS", "risk": "RISK", "next": "NEXT"}[kind]
    values = {
        "agent": {
            "focus": "hero, weapon, and build identity",
            "risk": "opening context is incomplete until the stage is armed",
            "next": "connect prompt bias and local judge boundaries",
        },
        "prompt": {
            "focus": "prompt bias that steers model choices",
            "risk": "model chooses actions but never resolves outcomes",
            "next": "hand the action to local rules",
        },
        "judge": {
            "focus": "local judge and rules boundary",
            "risk": "illegal actions must fall back or be denied",
            "next": "enter watchable combat or lock the choice",
        },
        "ready": {
            "focus": "stage, seed, and mock provider ready",
            "risk": "no live key; keep the run offline and deterministic",
            "next": "start the default watchable experience",
        },
        "scout": {
            "focus": "hero, enemy silhouettes, and positions",
            "risk": "tempo is unclear until the threat is read",
            "next": "lock primary threat and ATB pressure",
        },
        "threat": {
            "focus": "primary threat, enemy queue, and risk rail",
            "risk": "ignoring threat can miss the first counter window",
            "next": "confirm window, cooldown, and MP reserve",
        },
        "window": {
            "focus": "counter window and resource reserve",
            "risk": "low MP/CD can force model fallback actions",
            "next": "hand off opening plan and enter battle",
        },
        "result": {
            "focus": "locally judged result and remaining resources",
            "risk": "report display must not become a new resolver",
            "next": "reveal fallen enemy, codex cues, and damage rail",
        },
        "reveal": {
            "focus": "fallen enemy, codex silhouette, and turn map",
            "risk": "review cues never change rewards or drops",
            "next": "hand off review, loadout, and rematch paths",
        },
        "next": {
            "focus": "next-run action slots and review entry points",
            "risk": "player needs direction before the shell restores",
            "next": "print stable report and restore the shell",
        },
        "drop": {
            "focus": "visible feedback after gold, XP, and rewards are recorded",
            "risk": "reveal display must not grant rewards a second time",
            "next": "surface candidate cards and build deltas",
        },
        "cards": {
            "focus": "reward cards, build track, and priority board",
            "risk": "animation must not choose for the player",
            "next": "hand off to wait input or auto-lock",
        },
        "handoff": {
            "focus": "reward choice entry and input state",
            "risk": "choice write must happen after lock",
            "next": "enter reward wait or lock animation",
        },
        "scan": {
            "focus": "available options, reward, and route pressure",
            "risk": "blind picks can miss resource, build, or counter windows",
            "next": "focus one candidate and preview deltas",
        },
        "focus": {
            "focus": "candidate build, resource, and route pressure",
            "risk": "this choice changes the next battle window",
            "next": "lock the choice into run state",
        },
        "lock": {
            "focus": "selected option and run-state delta",
            "risk": "rollback cost is higher; next node is armed",
            "next": "play result frame and continue the run",
        },
    }
    return f"{label} {values.get(phase, values['focus'])[kind]}"
