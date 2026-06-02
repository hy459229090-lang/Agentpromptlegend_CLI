"""Read-only rendering for local JSONL battle traces."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TraceReplayError(ValueError):
    """Raised when a trace cannot be loaded for replay."""


def load_trace_events(path: str | Path) -> list[dict[str, Any]]:
    trace_path = Path(path)
    if not trace_path.exists():
        raise TraceReplayError(f"trace file not found: {trace_path}")
    if not trace_path.is_file():
        raise TraceReplayError(f"trace path is not a file: {trace_path}")

    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), 1):
        text = line.strip()
        if not text:
            continue
        try:
            event = json.loads(text)
        except json.JSONDecodeError as err:
            raise TraceReplayError(
                f"invalid JSON in trace line {line_no}: {err.msg}"
            ) from err
        if not isinstance(event, dict):
            raise TraceReplayError(f"trace line {line_no} is not an object")
        if not isinstance(event.get("kind"), str):
            raise TraceReplayError(f"trace line {line_no} is missing kind")
        events.append(event)

    if not events:
        raise TraceReplayError(f"trace file is empty: {trace_path}")
    return events


def render_trace_replay(
    path: str | Path,
    *,
    language: str = "en",
    limit: int | None = None,
) -> str:
    events = load_trace_events(path)
    start = _first(events, "battle_start") or events[0]
    end = _last(events, "battle_end")
    timeline = [e for e in events if e.get("kind") in {"hero_turn", "enemy_turn"}]
    shown = timeline if limit is None or limit <= 0 else timeline[:limit]
    omitted = max(0, len(timeline) - len(shown))

    hero_turns = [e for e in timeline if e.get("kind") == "hero_turn"]
    enemy_turns = [e for e in timeline if e.get("kind") == "enemy_turn"]
    total_tokens = sum(_as_int(e.get("total_tokens")) for e in hero_turns)
    total_latency = sum(_as_int(e.get("latency_ms")) for e in hero_turns)

    labels = _labels(language)
    lines = [
        labels["title"],
        "",
        f"{labels['run']}: {start.get('run_id', '-')}",
        f"{labels['battle']}: {start.get('battle_id', '-')}",
        (
            f"{labels['seed']}: {start.get('seed', '-')}    "
            f"{labels['provider']}: {start.get('provider', '-')}    "
            f"{labels['model']}: {start.get('model', '-')}"
        ),
    ]
    session = start.get("battle_session_id")
    context_hash = start.get("static_context_hash")
    if session or context_hash:
        lines.append(
            f"{labels['session']}: {session or '-'}    "
            f"{labels['context']}: {context_hash or '-'}"
        )

    prompt_styles = [e.get("prompt_style") for e in hero_turns if e.get("prompt_style")]
    if prompt_styles:
        lines.append(f"{labels['prompt']}: {prompt_styles[0]}")

    lines.extend([
        "",
        *(_render_replay_director_board(
            hero_turns,
            enemy_turns,
            end,
            prompt_styles[0] if prompt_styles else "-",
            total_tokens,
            total_latency,
            labels,
        )),
    ])

    lines.extend([
        "",
        *(_render_replay_beat_map(timeline, shown, omitted, labels)),
    ])

    lines.extend([
        "",
        labels["timeline"],
    ])
    for event in shown:
        lines.extend(_format_timeline_event(event, labels))

    if omitted:
        lines.append(labels["omitted"].format(count=omitted))

    lines.extend([
        "",
        (
            f"{labels['turns']}: hero={len(hero_turns)} enemy={len(enemy_turns)}"
        ),
        (
            f"{labels['echo']}: Echo Cost {total_tokens} | "
            f"Ritual Time {total_latency}ms"
        ),
    ])
    if end is not None:
        lines.append(
            f"{labels['result']}: {end.get('result', '-')} @ tick {end.get('tick', '-')}"
        )
    return "\n".join(lines)


def _render_replay_director_board(
    hero_turns: list[dict[str, Any]],
    enemy_turns: list[dict[str, Any]],
    end: dict[str, Any] | None,
    prompt_style: str,
    total_tokens: int,
    total_latency: int,
    labels: dict[str, str],
) -> list[str]:
    first_action = "-"
    if hero_turns:
        first_action = _format_action(hero_turns[0].get("action"))
    result = end.get("result", "-") if end is not None else "-"
    tick = end.get("tick", "-") if end is not None else "-"
    return [
        labels["director"],
        f"  [TURNS] hero {len(hero_turns)} / enemy {len(enemy_turns)}",
        f"  [PROMPT] {prompt_style}",
        f"  [FIRST HERO] {_clip(first_action, 96)}",
        f"  [RESULT] {result} @ tick {tick}",
        f"  [ECHO] Echo Cost {total_tokens} / Ritual Time {total_latency}ms",
    ]


def _render_replay_beat_map(
    timeline: list[dict[str, Any]],
    shown: list[dict[str, Any]],
    omitted: int,
    labels: dict[str, str],
) -> list[str]:
    sample = shown[:10] if shown else timeline[:10]
    if not sample:
        flow = "-"
    else:
        flow = " -> ".join(_beat_token(event) for event in sample)
        if omitted:
            flow += f" -> +{omitted}"
    hero_damage = 0
    enemy_pressure = 0
    for event in timeline:
        if event.get("kind") == "hero_turn":
            judge = event.get("judge") if isinstance(event.get("judge"), dict) else {}
            hero_damage += _extract_damage(judge.get("summary"))
        elif event.get("kind") == "enemy_turn":
            action = event.get("action") if isinstance(event.get("action"), dict) else {}
            enemy_pressure += _as_int(action.get("damage"))
    first_tick = _as_int(timeline[0].get("tick")) if timeline else 0
    last_tick = _as_int(timeline[-1].get("tick")) if timeline else 0
    return [
        labels["beat_map"],
        f"  [FLOW] {_clip(flow, 96)}",
        f"  [SPAN] tick {first_tick}->{last_tick} / events {len(timeline)}",
        f"  [PRESSURE] hero dealt {hero_damage} / enemy listed {enemy_pressure}",
        f"  [READ] H=hero action, E=enemy action, +N=hidden tail",
    ]


def _beat_token(event: dict[str, Any]) -> str:
    tick = _as_int(event.get("tick"))
    prefix = "H" if event.get("kind") == "hero_turn" else "E"
    return f"{prefix}{tick:03d}"


def _extract_damage(summary: object) -> int:
    if not isinstance(summary, str):
        return 0
    marker = "|"
    if marker not in summary:
        return 0
    tail = summary.rsplit(marker, 1)[-1]
    digits = ""
    for char in tail:
        if char.isdigit():
            digits += char
        elif digits:
            break
    return int(digits) if digits else 0


def _format_timeline_event(event: dict[str, Any], labels: dict[str, str]) -> list[str]:
    tick = _as_int(event.get("tick"))
    if event.get("kind") == "hero_turn":
        judge = event.get("judge") if isinstance(event.get("judge"), dict) else {}
        line = (
            f"  [{tick:03d}] HERO  {_format_action(event.get('action'))} | "
            f"{labels['judge']}: {_clip(str(judge.get('summary') or '-'), 96)}"
        )
        lines = [line]
        analysis = event.get("model_analysis")
        narration = event.get("model_narration")
        if analysis:
            lines.append(f"        {labels['model_thought']}: {_clip(str(analysis), 120)}")
        if narration:
            lines.append(f"        {labels['narration']}: {_clip(str(narration), 120)}")
        return lines

    actor = event.get("actor_id") or "enemy"
    return [
        (
            f"  [{tick:03d}] ENEMY {actor} | "
            f"{labels['action']}: {_format_action(event.get('action'))}"
        )
    ]


def _format_action(action: object) -> str:
    if not isinstance(action, dict):
        return "-"
    action_type = str(action.get("type") or "?")
    skill = action.get("skill_id")
    targets = action.get("targets")
    parts = [action_type]
    if skill:
        parts.append(str(skill))
    if isinstance(targets, list) and targets:
        parts.append("-> " + ", ".join(str(target) for target in targets))
    damage = action.get("damage")
    if damage is not None:
        parts.append(f"damage={damage}")
    return " ".join(parts)


def _labels(language: str) -> dict[str, str]:
    if language == "zh":
        return {
            "title": "OURO TRACE REPLAY",
            "run": "运行",
            "battle": "战斗",
            "seed": "Seed",
            "provider": "Provider",
            "model": "Model",
            "session": "Battle Echo",
            "context": "Sealed Echo",
            "prompt": "Prompt 预设",
            "timeline": "时间线:",
            "director": "REPLAY DIRECTOR BOARD :: 回放导演板",
            "beat_map": "REPLAY BEAT MAP :: 回合节奏图",
            "omitted": "  ... 省略 {count} 个事件",
            "turns": "回合",
            "echo": "回声消耗",
            "result": "结果",
            "judge": "裁判",
            "model_thought": "模型摘要",
            "narration": "旁白",
            "action": "行动",
        }
    return {
        "title": "OURO TRACE REPLAY",
        "run": "Run",
        "battle": "Battle",
        "seed": "Seed",
        "provider": "Provider",
        "model": "Model",
        "session": "Battle Echo",
        "context": "Sealed Echo",
        "prompt": "Prompt style",
        "timeline": "Timeline:",
        "director": "REPLAY DIRECTOR BOARD",
        "beat_map": "REPLAY BEAT MAP",
        "omitted": "  ... {count} more events omitted",
        "turns": "Turns",
        "echo": "Echo",
        "result": "Result",
        "judge": "Judge",
        "model_thought": "Model",
        "narration": "Narration",
        "action": "action",
    }


def _first(events: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    return next((event for event in events if event.get("kind") == kind), None)


def _last(events: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
    return next((event for event in reversed(events) if event.get("kind") == kind), None)


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."
