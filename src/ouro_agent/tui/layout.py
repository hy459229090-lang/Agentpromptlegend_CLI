"""Small visual-width-aware layout helpers for deterministic TUI output."""
from __future__ import annotations

from dataclasses import dataclass

from ouro_agent.i18n import pad_right, visual_width


@dataclass(frozen=True)
class Block:
    lines: tuple[str, ...]
    width: int

    @property
    def height(self) -> int:
        return len(self.lines)


def fit_text(text: str, width: int, *, ellipsis: str = "...") -> str:
    """Fit text to a visual column width without splitting CJK widths blindly."""
    if width <= 0:
        return ""
    if visual_width(text) <= width:
        return text
    if width <= visual_width(ellipsis):
        return ellipsis[:width]

    result = ""
    for ch in text:
        candidate = result + ch + ellipsis
        if visual_width(candidate) > width:
            break
        result += ch
    return result + ellipsis


def wrap_visual(text: str, width: int) -> list[str]:
    """Wrap text using visual width; keeps words together when possible."""
    if width <= 0:
        return [""]
    lines: list[str] = []
    current = ""
    for word in text.split():
        if not current:
            if visual_width(word) <= width:
                current = word
                continue
            lines.extend(_wrap_long_token(word, width))
            continue
        candidate = current + " " + word
        if visual_width(candidate) <= width:
            current = candidate
        else:
            lines.append(current)
            if visual_width(word) <= width:
                current = word
            else:
                wrapped = _wrap_long_token(word, width)
                lines.extend(wrapped[:-1])
                current = wrapped[-1] if wrapped else ""
    if current:
        lines.append(current)
    return lines or [""]


def _wrap_long_token(text: str, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for ch in text:
        if current and visual_width(current + ch) > width:
            lines.append(current)
            current = ch
        else:
            current += ch
    if current:
        lines.append(current)
    return lines


def panel(title: str, body: list[str], width: int) -> Block:
    inner = max(0, width - 4)
    border = "+" + "-" * (width - 2) + "+"
    lines = [border, "| " + pad_right(fit_text(title, inner), inner) + " |"]
    lines.append(border)
    for line in body:
        lines.append("| " + pad_right(fit_text(line, inner), inner) + " |")
    lines.append(border)
    return Block(tuple(lines), width)


def assert_width(text: str, width: int) -> None:
    """Raise AssertionError when any rendered line exceeds visual width."""
    for index, line in enumerate(text.splitlines(), start=1):
        line_width = visual_width(line)
        if line_width > width:
            raise AssertionError(
                f"line {index} exceeds width {width}: {line_width} columns: {line!r}"
            )


def hstack(left: Block, right: Block, *, gap: int = 1) -> Block:
    width = left.width + gap + right.width
    height = max(left.height, right.height)
    lines: list[str] = []
    for idx in range(height):
        l_line = left.lines[idx] if idx < left.height else ""
        r_line = right.lines[idx] if idx < right.height else ""
        lines.append(pad_right(l_line, left.width) + (" " * gap) + r_line)
    return Block(tuple(lines), width)


def vstack(*blocks: Block) -> Block:
    width = max((b.width for b in blocks), default=0)
    lines: list[str] = []
    for block in blocks:
        lines.extend(pad_right(line, width) for line in block.lines)
    return Block(tuple(lines), width)
