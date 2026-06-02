"""ASCII-safe pixel UI skin helpers.

The skin keeps rendering deterministic and dependency-free while giving the
CLI a stronger game identity than plain string concatenation.
"""
from __future__ import annotations

from dataclasses import dataclass

from ouro_agent.i18n import pad_right, visual_width
from ouro_agent.tui.layout import fit_text


@dataclass(frozen=True)
class PixelFrame:
    lines: tuple[str, ...]
    width: int


TONE_CHARS: dict[str, tuple[str, str, str, str]] = {
    "normal": ("+", "+", "-", "|"),
    "hero": ("+", "+", "=", "|"),
    "enemy": ("+", "+", "-", "|"),
    "danger": ("!", "!", "=", "!"),
    "counter": (">", "<", "=", "|"),
    "climax": ("#", "#", "=", "#"),
    "quiet": ("+", "+", ".", "|"),
}


def pixel_panel(title: str, body: list[str], width: int, *, tone: str = "normal") -> PixelFrame:
    """Render a framed pixel-style panel with exact visual width."""
    width = max(8, width)
    left, right, fill, side = TONE_CHARS.get(tone, TONE_CHARS["normal"])
    inner = width - 4
    top = _pixel_border(title, width, left=left, right=right, fill=fill)
    lines = [top]
    for row in body:
        lines.append(f"{side} {pad_right(fit_text(row, inner), inner)} {side}")
    lines.append(_pixel_border("", width, left=left, right=right, fill=fill))
    return PixelFrame(tuple(lines), width)


def pixel_lane(lines: list[str], width: int, *, tone: str = "normal") -> PixelFrame:
    """Render the center effect lane as a narrow pixel channel."""
    width = max(8, width)
    left, right, fill, side = TONE_CHARS.get(tone, TONE_CHARS["normal"])
    inner = width - 2
    top = left + fill * (width - 2) + right
    rendered = [top]
    for row in lines:
        rendered.append(side + pad_right(fit_text(row.strip(), inner), inner) + side)
    rendered.append(left + fill * (width - 2) + right)
    return PixelFrame(tuple(rendered), width)


def pixel_rule(title: str, width: int, *, tone: str = "normal") -> str:
    """Render a section divider that feels like a pixel HUD strip."""
    left, right, fill, _side = TONE_CHARS.get(tone, TONE_CHARS["normal"])
    return _pixel_border(title, max(8, width), left=left, right=right, fill=fill)


def pixel_shadow(lines: list[str], width: int) -> list[str]:
    """Add a one-column ASCII shadow without exceeding the requested width."""
    if width <= 2:
        return lines
    result: list[str] = []
    for index, line in enumerate(lines):
        fitted = fit_text(line, width - 1)
        suffix = "." if index % 2 == 0 else ":"
        result.append(pad_right(fitted, width - 1) + suffix)
    return result


def _pixel_border(title: str, width: int, *, left: str, right: str, fill: str) -> str:
    if not title:
        return left + fill * (width - 2) + right
    title_text = f"[ {title} ]"
    if visual_width(title_text) > width - 2:
        title_text = fit_text(title_text, width - 2)
    remaining = width - 2 - visual_width(title_text)
    left_fill = max(1, remaining // 2)
    right_fill = max(0, remaining - left_fill)
    return left + fill * left_fill + title_text + fill * right_fill + right
