"""Codex progress tracking for monster knowledge.

This module implements the codex tracking system from G07:
- Track encounters and defeats per monster family/tier
- Calculate codex stage based on experience
- Store state that persists across runs (codex only)
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ouro_agent.content.schema import CodexStage, ContentBundle


_CODEX_FILENAME = "codex.json"


class CodexStoreError(ValueError):
    """Raised when the local codex save cannot be read or written."""


@dataclass
class CodexEntry:
    """Codex progress for a single monster family/tier."""
    family_id: str
    encounters: int = 0
    defeats: int = 0
    tier: str = ""

    @property
    def stage(self) -> CodexStage:
        """Calculate current codex stage."""
        return CodexStage.from_encounters(self.encounters, self.defeats)

    def record_encounter(self) -> None:
        """Record an encounter with this monster."""
        self.encounters += 1

    def record_defeat(self) -> None:
        """Record a defeat of this monster."""
        self.defeats += 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "family_id": self.family_id,
            "tier": self.tier,
            "encounters": self.encounters,
            "defeats": self.defeats,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "CodexEntry":
        """Deserialize from dict."""
        return cls(
            family_id=str(raw.get("family_id", "")),
            encounters=int(raw.get("encounters", 0)),
            defeats=int(raw.get("defeats", 0)),
            tier=str(raw.get("tier", "") or ""),
        )


def codex_entry_key(family_id: str, tier: str | None = None) -> str:
    """Stable storage key for family+tier codex progress."""
    return f"{family_id}:{tier}" if tier else family_id


@dataclass
class CodexProgress:
    """Overall codex progress tracking.

    Tracks knowledge about monsters across runs.
    """
    entries: dict[str, CodexEntry] = field(default_factory=dict)

    def get_entry(self, family_id: str, tier: str | None = None) -> CodexEntry:
        """Get or create a codex entry for a family."""
        key = codex_entry_key(family_id, tier)
        if key not in self.entries:
            self.entries[key] = CodexEntry(family_id=family_id, tier=tier or "")
        return self.entries[key]

    def find_entry(self, family_id: str, tier: str | None = None) -> CodexEntry | None:
        """Find a codex entry without creating one."""
        entry = self.entries.get(codex_entry_key(family_id, tier))
        if entry is None and tier:
            # Backward-compatible read for older family-only saves.
            entry = self.entries.get(codex_entry_key(family_id))
        return entry

    def record_encounter(self, family_id: str, tier: str | None = None) -> CodexEntry:
        """Record an encounter and return the entry."""
        entry = self.get_entry(family_id, tier)
        entry.record_encounter()
        return entry

    def record_defeat(self, family_id: str, tier: str | None = None) -> CodexEntry:
        """Record a defeat and return the entry."""
        entry = self.get_entry(family_id, tier)
        entry.record_defeat()
        return entry

    def get_stage(self, family_id: str, tier: str | None = None) -> CodexStage:
        """Get the codex stage for a family."""
        entry = self.find_entry(family_id, tier)
        return entry.stage if entry is not None else CodexStage.UNKNOWN

    def record_study(
        self,
        family_id: str,
        tier: str | None = None,
        amount: int = 1,
    ) -> CodexEntry:
        """Record non-combat research progress as defeat-equivalent knowledge."""
        entry = self.get_entry(family_id, tier)
        if entry.encounters == 0:
            entry.record_encounter()
        for _ in range(max(0, amount)):
            entry.record_defeat()
        return entry

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "entries": {
                family_id: entry.to_dict()
                for family_id, entry in self.entries.items()
            },
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "CodexProgress":
        """Deserialize from dict."""
        entries_raw = raw.get("entries", {}) or {}
        if not isinstance(entries_raw, Mapping):
            return cls()
        entries: dict[str, CodexEntry] = {}
        for fallback_key, entry_raw in entries_raw.items():
            if not isinstance(entry_raw, Mapping):
                continue
            entry = CodexEntry.from_dict(entry_raw)
            key = (
                codex_entry_key(entry.family_id, entry.tier)
                if entry.family_id
                else str(fallback_key)
            )
            entries[key] = entry
        return cls(entries=entries)


def codex_path(override: Path | None = None) -> Path:
    if override is not None:
        return override
    env_dir = os.environ.get("OURO_AGENT_HOME")
    base = Path(env_dir) if env_dir else Path.home() / ".ouro_agent"
    return base / _CODEX_FILENAME


def load_codex_progress(path: Path | None = None) -> CodexProgress:
    target = codex_path(path)
    if not target.exists():
        return CodexProgress()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise CodexStoreError(f"{target}: invalid codex JSON") from err
    except OSError as err:
        raise CodexStoreError(f"{target}: cannot read codex save ({err})") from err
    if not isinstance(raw, Mapping):
        raise CodexStoreError(f"{target}: codex save must be an object")
    return CodexProgress.from_dict(raw)


def save_codex_progress(
    progress: CodexProgress,
    path: Path | None = None,
) -> Path:
    target = codex_path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(progress.to_dict(), ensure_ascii=True, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    except OSError as err:
        raise CodexStoreError(f"{target}: cannot write codex save ({err})") from err
    return target


def record_battle_codex(
    progress: CodexProgress,
    bundle: ContentBundle,
    enemy_ids: list[str] | tuple[str, ...],
    defeated_enemy_ids: set[str] | list[str] | tuple[str, ...] = (),
) -> None:
    defeated = set(defeated_enemy_ids)
    for enemy_id in enemy_ids:
        enemy = bundle.get_enemy(enemy_id)
        if not enemy.family_id:
            continue
        progress.record_encounter(enemy.family_id, enemy.tier)
        if enemy_id in defeated:
            progress.record_defeat(enemy.family_id, enemy.tier)


def record_codex_study(
    progress: CodexProgress,
    bundle: ContentBundle,
    enemy_ids: list[str] | tuple[str, ...],
    amount: int = 1,
) -> None:
    for enemy_id in enemy_ids:
        enemy = bundle.get_enemy(enemy_id)
        if enemy.family_id:
            progress.record_study(enemy.family_id, enemy.tier, amount)


def codex_stage_label(stage: CodexStage, lang: str = "zh") -> str:
    """Get display label for a codex stage."""
    labels = {
        CodexStage.UNKNOWN: {"en": "Unknown", "zh": "未知"},
        CodexStage.OBSERVED: {"en": "Observed", "zh": "观察"},
        CodexStage.FAMILIAR: {"en": "Familiar", "zh": "熟悉"},
        CodexStage.MASTERED: {"en": "Mastered", "zh": "掌握"},
        CodexStage.HUNTED: {"en": "Hunted", "zh": "猎杀"},
    }
    return labels.get(stage, {}).get(lang, stage.name)


def codex_stage_badge(stage: CodexStage) -> str:
    """Get badge-style label for a codex stage."""
    badges = {
        CodexStage.UNKNOWN: "[??]",
        CodexStage.OBSERVED: "[OB]",
        CodexStage.FAMILIAR: "[FM]",
        CodexStage.MASTERED: "[MS]",
        CodexStage.HUNTED: "[HT]",
    }
    return badges.get(stage, "[??]")
