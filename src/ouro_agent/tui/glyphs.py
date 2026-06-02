"""Terminal glyph sets for low-resolution TUI drawing."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GlyphSet:
    name: str
    empty: str
    light: str
    mid: str
    solid: str
    upper: str
    lower: str
    left: str
    right: str
    h: str
    v: str
    corner: str


ASCII_GLYPHS = GlyphSet(
    name="ascii",
    empty=" ",
    light=".",
    mid="=",
    solid="#",
    upper="#",
    lower="#",
    left="#",
    right="#",
    h="=",
    v="#",
    corner="#",
)

UNICODE_BLOCK_GLYPHS = GlyphSet(
    name="unicode",
    empty=" ",
    light="░",
    mid="▓",
    solid="█",
    upper="▀",
    lower="▄",
    left="▌",
    right="▐",
    h="▀",
    v="█",
    corner="█",
)


def get_glyph_set(mode: str | bool | None) -> GlyphSet:
    """Return a deterministic single-width glyph set."""
    if mode is True:
        return UNICODE_BLOCK_GLYPHS
    normalized = (str(mode or "ascii")).lower()
    if normalized in {"unicode", "block", "unicode-block", "true"}:
        return UNICODE_BLOCK_GLYPHS
    return ASCII_GLYPHS

