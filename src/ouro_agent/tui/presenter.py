"""Presenter helpers for deterministic battle frame output."""
from __future__ import annotations

from dataclasses import dataclass

from ouro_agent.tui.frame_builder import BattleFrame
from ouro_agent.tui.layout import Block, assert_width, fit_text, panel, vstack
from ouro_agent.tui.components import render_command_rail
from ouro_agent.tui.pixel_skin import pixel_panel


@dataclass(frozen=True)
class PresentedFrame:
    heading: str
    body: str

    @property
    def text(self) -> str:
        return self.heading + "\n" + self.body if self.heading else self.body


def render_live_chrome(
    body: str,
    *,
    mode: str,
    phase: str,
    provider_label: str,
    seed: int | str | None,
    language: str = "en",
    width: int = 100,
    unicode_mode: bool = False,
    input_hint: str | None = None,
) -> str:
    """Wrap a TTY animation frame in display-only live app chrome."""
    safe_width = max(40, width)
    title = "OURO LIVE" if language == "en" else "OURO 实况"
    mode_label = _live_mode_label(mode, language)
    phase_label = _live_phase_label(phase, language)
    seed_label = "-" if seed is None else str(seed)
    alt_state = "ALT 1049 █ON█" if unicode_mode else "ALT 1049 ON"
    if language == "zh":
        rows = [
            f"模式 {mode_label} | 阶段 {phase_label} | Provider {provider_label} | Seed {seed_label}",
            f"输入 {input_hint or _live_input_hint(mode, language)} | Ctrl+C 安全退出",
            f"状态 {alt_state} | 本地裁判结算 | shell 退出后恢复",
        ]
    else:
        rows = [
            f"MODE {mode_label} | PHASE {phase_label} | PROVIDER {provider_label} | SEED {seed_label}",
            f"INPUT {input_hint or _live_input_hint(mode, language)} | Ctrl+C exits safely",
            f"STATE {alt_state} | local judge resolves | shell restores on exit",
        ]
    chrome = pixel_panel(f"{title} / {mode_label}", rows, safe_width, tone="counter")
    fitted_body = tuple(
        line.rstrip() if _is_terminal_image_escape(line) else fit_text(line.rstrip(), safe_width)
        for line in body.rstrip("\n").splitlines()
    )
    return "\n".join((*chrome.lines, "", *fitted_body))


def _is_terminal_image_escape(line: str) -> bool:
    """Return whether a line is an inline bitmap payload that must not be clipped."""

    return line.startswith(("\x1b_G", "\x1b]1337;File=", "\x1bPq"))


def render_choice_prompt_chrome(
    body: str,
    *,
    mode: str,
    prompt_text: str,
    option_count: int | None,
    provider_label: str,
    seed: int | str | None,
    language: str = "en",
    width: int = 100,
    unicode_mode: bool = False,
    allow_leave: bool = False,
    allow_skip: bool = False,
    focus_index: int | None = None,
    focus_label: str | None = None,
    wait_phase: str | None = None,
) -> str:
    """Wrap a TTY choice screen in display-only waiting-input chrome."""
    safe_width = max(40, width)
    focused_body = _choice_wait_focus_overlay(
        body,
        focus_index=focus_index,
        focus_label=focus_label,
        wait_phase=wait_phase,
        language=language,
        width=safe_width,
        unicode_mode=unicode_mode,
    )
    command_rail = render_command_rail(
        _choice_prompt_commands(
            mode,
            prompt_text=prompt_text,
            option_count=option_count,
            language=language,
            allow_leave=allow_leave,
            allow_skip=allow_skip,
        ),
        width=safe_width,
        title="INPUT KEYS" if language == "en" else "输入键",
    )
    payload = "\n".join((*focused_body.rstrip("\n").splitlines(), "", *command_rail))
    return render_live_chrome(
        payload,
        mode=mode,
        phase=_choice_wait_live_phase(wait_phase),
        provider_label=provider_label,
        seed=seed,
        language=language,
        width=safe_width,
        unicode_mode=unicode_mode,
        input_hint=_choice_prompt_hint(
            mode,
            option_count=option_count,
            language=language,
            allow_leave=allow_leave,
            allow_skip=allow_skip,
        ),
    )


def _choice_wait_focus_overlay(
    body: str,
    *,
    focus_index: int | None,
    focus_label: str | None,
    wait_phase: str | None,
    language: str,
    width: int,
    unicode_mode: bool,
) -> str:
    """Add a display-only focus preview to a waiting choice screen."""
    if focus_index is None or focus_index < 0:
        return body
    safe_width = max(40, width)
    phase = _choice_wait_phase(wait_phase)
    explicit_phase = wait_phase is not None
    label = _choice_wait_choice_label(focus_index, focus_label)
    header = _choice_wait_focus_header(
        label,
        phase=phase,
        explicit_phase=explicit_phase,
        language=language,
    )
    pulse = _choice_wait_pulse_line(phase, language=language, unicode_mode=unicode_mode)
    marker = _choice_wait_focus_marker(
        phase=phase,
        explicit_phase=explicit_phase,
        language=language,
        unicode_mode=unicode_mode,
    )
    lines = body.splitlines()
    matched = False
    decorated: list[str] = [fit_text(header, safe_width), fit_text(pulse, safe_width)]
    for line in lines:
        if focus_index > 0 and _line_targets_choice(line, focus_index):
            decorated.append(fit_text(f"{marker} {line.rstrip()}", safe_width))
            matched = True
        else:
            decorated.append(line)
    if focus_index >= 0 and not matched:
        decorated.insert(1, fit_text(f"{marker} {label}", safe_width))
    return "\n".join(decorated)


def _choice_wait_choice_label(focus_index: int, focus_label: str | None) -> str:
    if focus_index <= 0:
        return focus_label or "[0]"
    if focus_label:
        return f"[{focus_index}] {focus_label}"
    return f"[{focus_index}]"


def _choice_wait_phase(wait_phase: str | None) -> str:
    phase = (wait_phase or "focus").lower().replace("-", "_")
    if phase in {"wait_scan", "scan"}:
        return "scan"
    if phase in {"wait_ready", "ready"}:
        return "ready"
    return "focus"


def _choice_wait_live_phase(wait_phase: str | None) -> str:
    if wait_phase is None:
        return "wait"
    return f"wait_{_choice_wait_phase(wait_phase)}"


def _choice_wait_focus_header(
    choice_label: str,
    *,
    phase: str,
    explicit_phase: bool,
    language: str,
) -> str:
    if not explicit_phase or phase == "focus":
        if language == "zh":
            return f"等待焦点 {choice_label} / 输入编号锁定，q 取消"
        return f"WAIT FOCUS {choice_label} / type number to lock, q abort"
    if phase == "scan":
        if language == "zh":
            return f"等待扫描 {choice_label} / 预览候选，准备输入"
        return f"WAIT SCAN {choice_label} / preview options before input"
    if language == "zh":
        return f"等待就绪 {choice_label} / 输入编号锁定，q 取消"
    return f"WAIT READY {choice_label} / type number to lock, q abort"


def _choice_wait_focus_marker(
    *,
    phase: str,
    explicit_phase: bool,
    language: str,
    unicode_mode: bool,
) -> str:
    if not explicit_phase:
        if unicode_mode:
            return "█等待█" if language == "zh" else "█WAIT█"
        return ">>WAIT"
    labels = {
        "scan": {"en": "SCAN", "zh": "扫描"},
        "focus": {"en": "FOCUS", "zh": "聚焦"},
        "ready": {"en": "READY", "zh": "就绪"},
    }
    phase_labels = labels.get(phase, labels["focus"])
    label = phase_labels.get(language, phase_labels["en"])
    if unicode_mode:
        return f"█{label}█"
    return f">>{label}"


def _choice_wait_pulse_line(phase: str, *, language: str, unicode_mode: bool) -> str:
    if unicode_mode:
        patterns = {
            "scan": "█░░░",
            "focus": "██░░",
            "ready": "████",
        }
    else:
        patterns = {
            "scan": ">...",
            "focus": ">>..",
            "ready": ">>>>",
        }
    if language == "zh":
        actions = {
            "scan": "扫描选项",
            "focus": "点亮候选",
            "ready": "等待输入",
        }
        pattern = patterns.get(phase, patterns["focus"])
        action = actions.get(phase, actions["focus"])
        return f"等待脉冲 {pattern} {action}"
    actions = {
        "scan": "scanning options",
        "focus": "default lane lit",
        "ready": "keys armed",
    }
    pattern = patterns.get(phase, patterns["focus"])
    action = actions.get(phase, actions["focus"])
    return f"WAIT PULSE {pattern} {action}"


def _line_targets_choice(line: str, selected_index: int) -> bool:
    token = f"[{selected_index}]"
    map_token = f"[{selected_index}:"
    return token in line or map_token in line


def _live_mode_label(mode: str, language: str) -> str:
    labels = {
        "setup": {"en": "SETUP", "zh": "装配"},
        "battle": {"en": "BATTLE", "zh": "战斗"},
        "route": {"en": "ROUTE", "zh": "路线"},
        "reward": {"en": "REWARD", "zh": "奖励"},
        "shop": {"en": "SHOP", "zh": "商店"},
        "rest": {"en": "REST", "zh": "休整"},
        "event": {"en": "EVENT", "zh": "事件"},
        "choice": {"en": "CHOICE", "zh": "选择"},
        "run": {"en": "RUN", "zh": "本局"},
    }
    values = labels.get(mode.lower(), {})
    return values.get(language, values.get("en", mode.upper()))


def _live_phase_label(phase: str, language: str) -> str:
    labels = {
        "agent": {"en": "AGENT", "zh": "英雄"},
        "prompt": {"en": "PROMPT", "zh": "提示词"},
        "judge": {"en": "JUDGE", "zh": "裁判"},
        "ready": {"en": "READY", "zh": "就绪"},
        "select": {"en": "SELECT", "zh": "选定"},
        "windup": {"en": "WINDUP", "zh": "起手"},
        "travel": {"en": "TRAVEL", "zh": "飞行"},
        "impact": {"en": "IMPACT", "zh": "命中"},
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
        "wait": {"en": "WAIT", "zh": "等待"},
        "wait_scan": {"en": "WAIT SCAN", "zh": "等待扫描"},
        "wait_focus": {"en": "WAIT FOCUS", "zh": "等待聚焦"},
        "wait_ready": {"en": "WAIT READY", "zh": "等待就绪"},
        "thinking": {"en": "THINKING", "zh": "读取"},
        "frame": {"en": "FRAME", "zh": "帧"},
    }
    values = labels.get(phase.lower(), {})
    return values.get(language, values.get("en", phase.upper()))


def _live_input_hint(mode: str, language: str) -> str:
    if mode.lower() in {"route", "reward", "shop", "rest", "event", "choice"}:
        return "选项已锁定" if language == "zh" else "choice locked"
    if mode.lower() == "battle":
        return "只观看；模型选行动" if language == "zh" else "watch-only; model chooses"
    return "只观看；装配中" if language == "zh" else "watch-only; staging"


def _choice_prompt_hint(
    mode: str,
    *,
    option_count: int | None,
    language: str,
    allow_leave: bool,
    allow_skip: bool,
) -> str:
    choice_range = _choice_prompt_range(option_count)
    noun = _choice_prompt_noun(mode, language)
    if language == "zh":
        suffixes: list[str] = []
        if allow_leave:
            suffixes.append("0/q/l 离开")
        if allow_skip:
            suffixes.append("n 跳过")
        suffix = " / " + " / ".join(suffixes) if suffixes else ""
        return f"{choice_range} 选择{noun}{suffix}；等待玩家"
    suffixes_en: list[str] = []
    if allow_leave:
        suffixes_en.append("0/q/l leave")
    if allow_skip:
        suffixes_en.append("n skip")
    suffix_en = " or " + " / ".join(suffixes_en) if suffixes_en else ""
    return f"enter {choice_range}{suffix_en}; {noun} waiting"


def _choice_prompt_commands(
    mode: str,
    *,
    prompt_text: str,
    option_count: int | None,
    language: str,
    allow_leave: bool,
    allow_skip: bool,
) -> list[tuple[str, str]]:
    choice_range = _choice_prompt_range(option_count)
    noun = _choice_prompt_noun(mode, language)
    if language == "zh":
        commands = [("提示", prompt_text), (choice_range, f"选择{noun}")]
        if allow_leave:
            commands.append(("0/Q/L", "离开商店"))
        if allow_skip:
            commands.append(("N", "跳过休整"))
        commands.append(("Ctrl+C", "安全退出"))
        return commands

    commands = [("PROMPT", prompt_text), (choice_range, f"choose {noun}")]
    if allow_leave:
        commands.append(("0/Q/L", "leave shop"))
    if allow_skip:
        commands.append(("N", "skip rest"))
    commands.append(("Ctrl+C", "abort safely"))
    return commands


def _choice_prompt_range(option_count: int | None) -> str:
    count = max(1, option_count or 1)
    return "1" if count == 1 else f"1-{count}"


def _choice_prompt_noun(mode: str, language: str) -> str:
    labels = {
        "route": {"en": "route", "zh": "路线"},
        "reward": {"en": "reward", "zh": "奖励"},
        "shop": {"en": "shop action", "zh": "商店行动"},
        "rest": {"en": "rest action", "zh": "休整行动"},
        "event": {"en": "event", "zh": "事件"},
    }
    values = labels.get(mode.lower(), {})
    return values.get(language, values.get("en", "choice"))


@dataclass(frozen=True)
class BattleScreenModel:
    frame_id: str
    width: int
    blocks: tuple[Block, ...]

    @property
    def text(self) -> str:
        return "\n".join(vstack(*self.blocks).lines) if self.blocks else ""


def battle_turn_heading(
    *,
    turn_index: int,
    tick: int,
    thinking: bool = False,
    language: str = "en",
) -> str:
    if language == "zh":
        if thinking:
            return f"--- 回合 {turn_index} / 刻度 {tick} :: 模型读取战场 ---"
        return f"--- 回合 {turn_index} / 刻度 {tick} ---"
    if thinking:
        return f"--- turn {turn_index} / tick {tick} :: model reading field ---"
    return f"--- turn {turn_index} / tick {tick} ---"


def present_battle_frame(
    body: str,
    *,
    turn_index: int,
    tick: int,
    thinking: bool = False,
    language: str = "en",
) -> PresentedFrame:
    return PresentedFrame(
        heading=battle_turn_heading(
            turn_index=turn_index,
            tick=tick,
            thinking=thinking,
            language=language,
        ),
        body=body,
    )


def battle_screen_model_from_frame(frame: BattleFrame, *, width: int = 100) -> BattleScreenModel:
    """Build layout blocks from a display-only BattleFrame."""
    action_body = [
        f"Action: {frame.action_label}",
        f"Judge: {frame.judge_label}",
        f"Intent: {frame.intent}",
        f"Risk: {frame.risk}",
        f"Align: {frame.align}",
    ]
    if frame.impact_line:
        action_body.append(f"Impact: {frame.impact_line}")
    if frame.counter_hint:
        action_body.append(f"Counter: {frame.counter_hint}")
    if frame.counter_clock:
        action_body.append(frame.counter_clock)
    if frame.boss_intel:
        boss = frame.boss_intel
        action_body.append(
            f"Boss: {boss.phase} | {boss.charge} | {boss.break_state} | {boss.enrage}"
        )
    for delta in frame.resource_deltas:
        action_body.append(f"Delta: {delta.label} {delta.text}")

    blocks: list[Block] = [panel("BattleFrame ACTION", action_body, width)]
    if frame.session_usage:
        usage = frame.session_usage
        blocks.append(
            panel(
                "Session",
                [
                    f"Battle Echo: {usage.battle_echo}",
                    f"Sealed Echo: {usage.sealed_echo}",
                    f"Fresh Echo: {usage.fresh_echo}",
                    f"Echo Cost: {usage.echo_cost}",
                    f"Ritual Time: {usage.ritual_time_ms}ms",
                ],
                width,
            )
        )
    model = BattleScreenModel(frame_id=frame.frame_id, width=width, blocks=tuple(blocks))
    assert_width(model.text, width)
    return model


def present_battle_screen_model(
    model: BattleScreenModel,
    *,
    turn_index: int,
    tick: int,
    thinking: bool = False,
    language: str = "en",
) -> PresentedFrame:
    return present_battle_frame(
        model.text,
        turn_index=turn_index,
        tick=tick,
        thinking=thinking,
        language=language,
    )
