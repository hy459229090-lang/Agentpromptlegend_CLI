"""Provider adapter interface.

Adapters take a ``PromptContext`` and return a ``ModelTurnResult`` whose
``raw_text`` is supposed to be JSON conforming to the action schema. The
combat engine never inspects raw text directly; it goes through
``llm.parse_model_output`` first.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ouro_agent.llm.prompt import PromptContext


class ProviderError(RuntimeError):
    """Raised when a provider can't produce a turn (network, auth, etc)."""


@dataclass(frozen=True)
class EchoUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0

    @classmethod
    def zero(cls, latency_ms: int = 0) -> "EchoUsage":
        return cls(latency_ms=latency_ms)


@dataclass(frozen=True)
class ModelTurnResult:
    provider: str
    model: str
    raw_text: str
    usage: EchoUsage = field(default_factory=EchoUsage)
    error: str | None = None


class Provider(ABC):
    name: str = "base"

    @abstractmethod
    def request_turn(self, prompt: "PromptContext") -> ModelTurnResult:
        """Generate one model turn for the hero."""
