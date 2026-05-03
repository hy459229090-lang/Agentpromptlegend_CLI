"""JSONL trace writer.

One line per event. The trace records technical token field names; the TUI
may render them with game-flavored labels (Echo Cost, Ritual Time, etc.).

Privacy:
* Trace is local by default (G09 L0).
* No API keys are written. Provider name and model name only.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ouro_agent import (
    CONTENT_VERSION,
    RULESET_VERSION,
    SCHEMA_VERSION,
    __version__,
)


def default_trace_dir() -> Path:
    env_dir = os.environ.get("OURO_AGENT_HOME")
    base = Path(env_dir) if env_dir else Path.home() / ".ouro_agent"
    return base / "traces"


@dataclass
class TraceConfig:
    enabled: bool = True
    directory: Path = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.directory is None:
            self.directory = default_trace_dir()


class TraceWriter:
    def __init__(
        self,
        run_id: str,
        battle_id: str,
        seed: int,
        provider: str,
        model: str,
        config: TraceConfig | None = None,
    ):
        self.run_id = run_id
        self.battle_id = battle_id
        self.seed = seed
        self.provider = provider
        self.model = model
        self.config = config or TraceConfig()
        self._fp = None
        self._path: Path | None = None
        if self.config.enabled:
            self.config.directory.mkdir(parents=True, exist_ok=True)
            self._path = self.config.directory / f"{battle_id}.trace.jsonl"
            self._fp = self._path.open("w", encoding="utf-8")
            self.write(
                "battle_start",
                run_id=self.run_id,
                battle_id=self.battle_id,
                seed=self.seed,
                provider=self.provider,
                model=self.model,
                schema_version=SCHEMA_VERSION,
                ruleset_version=RULESET_VERSION,
                content_version=CONTENT_VERSION,
                ouro_version=__version__,
                ts=_now_iso(),
            )

    @property
    def path(self) -> Path | None:
        return self._path

    def write(self, kind: str, **payload: Any) -> None:
        if self._fp is None:
            return
        record = {
            "kind": kind,
            "run_id": self.run_id,
            "battle_id": self.battle_id,
            **payload,
        }
        self._fp.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
        self._fp.flush()

    def close(self) -> None:
        if self._fp is not None:
            self._fp.close()
            self._fp = None

    def __enter__(self) -> "TraceWriter":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
