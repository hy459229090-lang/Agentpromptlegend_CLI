"""Semantic terminal theme tokens for future ANSI/color rendering."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tone:
    name: str
    ink: str
    accent: str


TONES: dict[str, Tone] = {
    "normal": Tone("normal", "mist", "ash"),
    "hero": Tone("hero", "candle", "gold"),
    "enemy": Tone("enemy", "blood", "wick"),
    "danger": Tone("danger", "blood", "red"),
    "counter": Tone("counter", "echo", "blue"),
    "climax": Tone("climax", "white", "gold"),
    "quiet": Tone("quiet", "ash", "mist"),
}


def resolve_tone(name: str | None) -> Tone:
    return TONES.get(name or "normal", TONES["normal"])

