"""Run / Battle session identifiers and seed wiring."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RunSession:
    run_id: str
    seed: int


@dataclass(frozen=True)
class BattleSession:
    run_id: str
    battle_id: str
    seed: int


@dataclass
class BattleLLMSession:
    """Local model-session envelope for one battle.

    Providers may be stateless, so this object keeps the reusable static
    context and stable ids on our side for prompt composition and trace replay.
    """

    battle_session_id: str
    static_context_hash: str
    static_context: dict[str, Any]
    turn_index: int = 0

    @classmethod
    def start(
        cls, battle_session_id: str, static_context: dict[str, Any]
    ) -> "BattleLLMSession":
        return cls(
            battle_session_id=battle_session_id,
            static_context_hash=hash_static_context(static_context),
            static_context=static_context,
        )

    def claim_delta_context_id(self) -> str:
        self.turn_index += 1
        return f"{self.battle_session_id}_d{self.turn_index:04d}"


def new_run_id(prefix: str = "run") -> str:
    return f"{prefix}_{int(time.time())}"


def new_battle_id(run_id: str, index: int) -> str:
    return f"{run_id}_b{index:03d}"


def new_battle_llm_session_id(battle_id: str) -> str:
    return f"be_{battle_id}"


def hash_static_context(static_context: dict[str, Any]) -> str:
    payload = json.dumps(static_context, ensure_ascii=True, sort_keys=True)
    return "ctx_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
