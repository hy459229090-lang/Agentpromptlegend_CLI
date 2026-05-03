"""Run / Battle session identifiers and seed wiring."""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class RunSession:
    run_id: str
    seed: int


@dataclass(frozen=True)
class BattleSession:
    run_id: str
    battle_id: str
    seed: int


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{int(time.time())}"


def new_battle_id(run_id: str, index: int) -> str:
    return f"{run_id}_b{index:03d}"
