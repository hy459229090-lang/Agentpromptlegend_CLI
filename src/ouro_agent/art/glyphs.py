"""ASCII glyph helpers.

ASCII-safe by default; Unicode is an optional enhancement and never required
by the engine or tests.
"""
from __future__ import annotations


def bar(value: int, maximum: int, width: int = 10, *, unicode_mode: bool = False) -> str:
    """Render a bracket-style bar that is readable in PowerShell and CI."""
    if maximum <= 0:
        return "[" + (" " * width) + "]"
    ratio = max(0.0, min(1.0, value / maximum))
    filled = int(round(ratio * width))
    if unicode_mode:
        return "[" + ("\u2588" * filled) + ("\u2591" * (width - filled)) + "]"
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def hero_short_tag(short_tag: str, name: str, class_name: str) -> str:
    return f"{short_tag} {name}  {class_name}"


def hero_avatar(lines: list[str] | tuple[str, ...]) -> list[str]:
    """Return a copy with no leading/trailing blank lines."""
    return [line.rstrip() for line in lines]
