"""Presenter helpers for deterministic battle frame output."""
from __future__ import annotations

from dataclasses import dataclass

from ouro_agent.tui.frame_builder import BattleFrame
from ouro_agent.tui.layout import Block, assert_width, panel, vstack


@dataclass(frozen=True)
class PresentedFrame:
    heading: str
    body: str

    @property
    def text(self) -> str:
        return self.heading + "\n" + self.body if self.heading else self.body


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
    if thinking:
        suffix = "model reading field" if language == "en" else "模型读取战场"
        return f"--- turn {turn_index} / tick {tick} :: {suffix} ---"
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
