"""Player-facing rendering for deterministic battle diagnostics."""
from __future__ import annotations

from ouro_agent.engine.diagnostics import (
    TacticalDiagnosis,
    analyze_battle_tactics,
    analyze_prompt_impacts,
)


def render_tactical_diagnosis(
    diagnosis: TacticalDiagnosis,
    *,
    language: str = "en",
) -> list[str]:
    if language == "zh":
        lines = [
            "战术诊断:",
            f"  - MP 枯竭回合: {diagnosis.mp_dry_turns}",
            f"  - 低收益回合: {diagnosis.low_impact_turns}",
            f"  - 最长防御循环: {diagnosis.max_defense_loop}",
            f"  - 目标偏移回合: {diagnosis.targeting_drift_turns}",
            "  - 反制窗口: "
            f"{diagnosis.counter_windows_answered}/{diagnosis.counter_windows_opened} 已回应, "
            f"{diagnosis.counter_windows_missed} 次错失",
        ]
        lines.extend(f"  - {note}" for note in diagnosis.notes)
        lines.extend(
            [
                f"  - 致命原因: {diagnosis.prescription[0]}",
                f"  - 错过机会: {diagnosis.prescription[1]}",
                f"  - 下一局改法: {diagnosis.prescription[2]}",
            ]
        )
        return lines

    lines = [
        "Tactical Diagnosis:",
        f"  - MP dry turns: {diagnosis.mp_dry_turns}",
        f"  - Low-impact turns: {diagnosis.low_impact_turns}",
        f"  - Longest defense loop: {diagnosis.max_defense_loop}",
        f"  - Targeting drift turns: {diagnosis.targeting_drift_turns}",
        "  - Counter windows: "
        f"{diagnosis.counter_windows_answered}/{diagnosis.counter_windows_opened} answered, "
        f"{diagnosis.counter_windows_missed} missed",
    ]
    lines.extend(f"  - {note}" for note in diagnosis.notes)
    lines.extend(
        [
            f"  - Problem: {diagnosis.prescription[0]}",
            f"  - Cause: {diagnosis.prescription[1]}",
            f"  - Next Build Pick: {diagnosis.prescription[2]}",
        ]
    )
    return lines


def render_prompt_impacts(
    records: list,
    *,
    language: str = "en",
) -> list[str]:
    impacts = analyze_prompt_impacts(records, language=language)
    if not impacts:
        return []
    title = "Prompt 影响:" if language == "zh" else "Prompt Impact:"
    return [title, *(f"  - {impact}" for impact in impacts)]


def render_failure_review(
    diagnosis: TacticalDiagnosis,
    *,
    language: str = "en",
) -> list[str]:
    if not diagnosis.failure_reasons and not diagnosis.next_run_advice:
        return []

    if language == "zh":
        lines = ["失败原因:"]
        for index, reason in enumerate(diagnosis.failure_reasons, start=1):
            lines.append(f"  {index}. {reason}")
        lines.append("下一局建议:")
        for index, advice in enumerate(diagnosis.next_run_advice, start=1):
            lines.append(f"  {index}. {advice}")
        return lines

    lines = ["Failure Reasons:"]
    for index, reason in enumerate(diagnosis.failure_reasons, start=1):
        lines.append(f"  {index}. {reason}")
    lines.append("Next Run Advice:")
    for index, advice in enumerate(diagnosis.next_run_advice, start=1):
        lines.append(f"  {index}. {advice}")
    return lines
