"""Local run archive and death-history persistence."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from ouro_agent.content.schema import ContentBundle
from ouro_agent.sessions.run_state import RunPhase, RunState


class RunArchiveError(ValueError):
    """Raised when a local run archive cannot be read or written."""


def run_archive_dir(override: Path | None = None) -> Path:
    if override is not None:
        return override
    env_dir = os.environ.get("OURO_AGENT_HOME")
    base = Path(env_dir) if env_dir else Path.home() / ".ouro_agent"
    return base / "runs"


def death_history_path(override: Path | None = None) -> Path:
    if override is not None:
        return override
    env_dir = os.environ.get("OURO_AGENT_HOME")
    base = Path(env_dir) if env_dir else Path.home() / ".ouro_agent"
    return base / "death_history.json"


def build_run_archive(run_state: RunState, bundle: ContentBundle) -> dict[str, Any]:
    build = run_state.resolved_build(bundle)
    progress = build.calculate_progress(bundle)
    return {
        "schema_version": "0.1",
        "run_id": run_state.run_id,
        "seed": run_state.seed,
        "result": _result_for_phase(run_state.phase),
        "phase": run_state.phase.name.lower(),
        "hero_id": run_state.hero_id,
        "dungeon_id": run_state.dungeon_id,
        "current_floor_index": run_state.current_floor_index,
        "current_node_index": run_state.current_node_index,
        "completed_node_ids": list(run_state.completed_node_ids),
        "visited_node_ids": sorted(run_state.visited_node_ids),
        "battle_result": run_state.battle_result,
        "battles_won": run_state.battles_won,
        "battles_lost": run_state.battles_lost,
        "gold": run_state.gold,
        "xp": run_state.xp,
        "earned_gold_total": run_state.earned_gold_total,
        "earned_xp_total": run_state.earned_xp_total,
        "current_hp": run_state.current_hp,
        "current_mp": run_state.current_mp,
        "max_hp": run_state.max_hp,
        "max_mp": run_state.max_mp,
        "strategy_style": run_state.strategy_style,
        "item_ids": list(run_state.item_ids),
        "affix_ids": list(run_state.affix_ids),
        "build": {
            "archetype": build.archetype("en"),
            "stage": progress.stage.value,
            "stage_badge": progress.stage.badge,
            "active_resonances": list(progress.active_resonances),
            "tags": list(build.tags),
        },
        "scout_notes": list(run_state.scout_notes),
        "codex": run_state.codex_progress.to_dict(),
    }


def save_run_archive(
    run_state: RunState,
    bundle: ContentBundle,
    directory: Path | None = None,
) -> Path:
    target_dir = run_archive_dir(directory)
    target = target_dir / f"{run_state.run_id}.run.json"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                build_run_archive(run_state, bundle),
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError as err:
        raise RunArchiveError(f"{target}: cannot write run archive ({err})") from err
    return target


def load_run_archive(path: Path) -> dict[str, Any]:
    """Load one saved run archive and include local metadata."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        stat = path.stat()
    except json.JSONDecodeError as err:
        raise RunArchiveError(f"{path}: invalid run archive JSON") from err
    except OSError as err:
        raise RunArchiveError(f"{path}: cannot read run archive ({err})") from err
    if not isinstance(raw, Mapping):
        raise RunArchiveError(f"{path}: run archive must be an object")
    entry = dict(raw)
    entry["_archive_path"] = str(path)
    entry["_mtime"] = stat.st_mtime
    return entry


def load_run_archives(directory: Path | None = None) -> list[dict[str, Any]]:
    """Load saved run archive summaries, newest first."""
    target_dir = run_archive_dir(directory)
    if not target_dir.exists():
        return []
    if not target_dir.is_dir():
        raise RunArchiveError(f"{target_dir}: run archive path must be a directory")

    archives: list[dict[str, Any]] = []
    for path in sorted(target_dir.glob("*.run.json")):
        archives.append(load_run_archive(path))

    return sorted(
        archives,
        key=lambda entry: (float(entry.get("_mtime", 0) or 0), str(entry.get("run_id", ""))),
        reverse=True,
    )


def append_death_history(
    run_state: RunState,
    bundle: ContentBundle,
    path: Path | None = None,
) -> Path | None:
    if run_state.phase is not RunPhase.DEAD:
        return None
    target = death_history_path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        raise RunArchiveError(
            f"{target}: cannot create death history directory ({err})"
        ) from err
    history = load_death_history(target)
    archive = build_run_archive(run_state, bundle)
    history.append(
        {
            "run_id": archive["run_id"],
            "seed": archive["seed"],
            "hero_id": archive["hero_id"],
            "dungeon_id": archive["dungeon_id"],
            "battle_result": archive["battle_result"],
            "battles_won": archive["battles_won"],
            "battles_lost": archive["battles_lost"],
            "completed_node_ids": archive["completed_node_ids"],
            "build": archive["build"],
        }
    )
    try:
        target.write_text(
            json.dumps({"deaths": history}, ensure_ascii=True, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    except OSError as err:
        raise RunArchiveError(f"{target}: cannot write death history ({err})") from err
    return target


def load_death_history(path: Path | None = None) -> list[dict[str, Any]]:
    target = death_history_path(path)
    if not target.exists():
        return []
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise RunArchiveError(f"{target}: invalid death history JSON") from err
    except OSError as err:
        raise RunArchiveError(f"{target}: cannot read death history ({err})") from err
    if not isinstance(raw, Mapping):
        raise RunArchiveError(f"{target}: death history must be an object")
    deaths = raw.get("deaths", [])
    if not isinstance(deaths, list):
        raise RunArchiveError(f"{target}: deaths must be a list")
    return [item for item in deaths if isinstance(item, dict)]


def _result_for_phase(phase: RunPhase) -> str:
    if phase is RunPhase.COMPLETE:
        return "complete"
    if phase is RunPhase.DEAD:
        return "dead"
    return "in_progress"
