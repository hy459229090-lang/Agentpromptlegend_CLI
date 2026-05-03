"""Action schema shared by the model interface and the engine.

Only this module defines what an action is. The engine consumes ``HeroAction``
instances; the validator builds one from possibly malformed model output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

ACTION_SCHEMA_VERSION = "0.1"

ACTION_TYPES: tuple[str, ...] = (
    "basic_attack",
    "cast_skill",
    "use_item",
    "defend",
    "observe",
    "change_stance",
)


class FallbackReason(str, Enum):
    NONE = "none"
    JSON_PARSE_FAILED = "json_parse_failed"
    MISSING_ACTION = "missing_action"
    UNKNOWN_ACTION_TYPE = "unknown_action_type"
    UNKNOWN_SKILL = "unknown_skill"
    INVALID_TARGET = "invalid_target"
    EMPTY_RESPONSE = "empty_response"


@dataclass(frozen=True)
class HeroAction:
    type: str
    skill_id: str | None = None
    targets: tuple[str, ...] = ()
    modifier: str | None = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "skill_id": self.skill_id,
            "targets": list(self.targets),
            "modifier": self.modifier,
        }


@dataclass(frozen=True)
class ModelOutput:
    """Display-only fields plus the action that participates in resolution."""
    narration: str
    analysis: str
    confidence: float
    action: HeroAction
    schema_version: str = ACTION_SCHEMA_VERSION
    extras: dict = field(default_factory=dict)
