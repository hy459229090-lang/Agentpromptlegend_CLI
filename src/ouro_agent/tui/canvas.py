"""Low-resolution terminal canvas.

The canvas is intentionally small and dependency-free. It lets battle screens
draw sprites, bars, and effect lanes as a surface first, then render to stable
text for snapshots and CLI output.
"""
from __future__ import annotations

from dataclasses import dataclass

from ouro_agent.i18n import visual_width
from ouro_agent.tui.glyphs import GlyphSet, get_glyph_set


@dataclass(frozen=True)
class Cell:
    char: str = " "
    fg: str | None = None
    bg: str | None = None
    style: str | None = None


class Surface:
    """A fixed-size 2D text surface with visual-column drawing semantics."""

    def __init__(self, width: int, height: int, *, fill: str = " ") -> None:
        if width <= 0 or height <= 0:
            raise ValueError("surface width and height must be positive")
        if visual_width(fill) != 1:
            raise ValueError("fill glyph must be one visual column")
        self.width = width
        self.height = height
        self._cells = [[Cell(fill) for _ in range(width)] for _ in range(height)]

    def put(self, x: int, y: int, char: str, *, fg: str | None = None, bg: str | None = None) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        if visual_width(char) != 1:
            return
        self._clear_span(x, y, 1)
        self._cells[y][x] = Cell(char, fg=fg, bg=bg)

    def draw_text(self, x: int, y: int, text: str) -> None:
        if not (0 <= y < self.height):
            return
        cursor = x
        for char in text:
            char_width = visual_width(char)
            if char_width <= 0:
                continue
            if cursor < 0:
                cursor += char_width
                continue
            if cursor >= self.width:
                break
            if cursor + char_width > self.width:
                break
            if char_width > 1:
                self._put_wide(cursor, y, char)
            else:
                self.put(cursor, y, char)
            cursor += char_width

    def _put_wide(
        self,
        x: int,
        y: int,
        char: str,
        *,
        fg: str | None = None,
        bg: str | None = None,
        style: str | None = None,
    ) -> None:
        char_width = visual_width(char)
        if char_width <= 1:
            self.put(x, y, char, fg=fg, bg=bg)
            return
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        if x + char_width > self.width:
            return
        self._clear_span(x, y, char_width)
        self._cells[y][x] = Cell(char=char, fg=fg, bg=bg, style=style)
        for offset in range(1, char_width):
            self._cells[y][x + offset] = Cell("")

    def _clear_span(self, x: int, y: int, width: int) -> None:
        for col in range(x, x + max(0, width)):
            self._clear_cell(col, y)

    def _clear_cell(self, x: int, y: int) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        cell = self._cells[y][x]
        if cell.char == "" and x > 0:
            lead = self._cells[y][x - 1]
            lead_width = visual_width(lead.char)
            if lead_width > 1:
                for offset in range(lead_width):
                    if x - 1 + offset < self.width:
                        self._cells[y][x - 1 + offset] = Cell(" ")
                return
        cell_width = visual_width(cell.char)
        if cell_width > 1:
            for offset in range(cell_width):
                if x + offset < self.width:
                    self._cells[y][x + offset] = Cell(" ")
            return
        self._cells[y][x] = Cell(" ")

    def fill_rect(self, x: int, y: int, width: int, height: int, char: str) -> None:
        if visual_width(char) != 1:
            return
        for row in range(y, y + max(0, height)):
            for col in range(x, x + max(0, width)):
                self.put(col, row, char)

    def draw_box(self, x: int, y: int, width: int, height: int, glyphs: GlyphSet | None = None) -> None:
        if width < 2 or height < 2:
            return
        glyphs = glyphs or get_glyph_set("ascii")
        for col in range(x + 1, x + width - 1):
            self.put(col, y, glyphs.h)
            self.put(col, y + height - 1, glyphs.h)
        for row in range(y + 1, y + height - 1):
            self.put(x, row, glyphs.v)
            self.put(x + width - 1, row, glyphs.v)
        self.put(x, y, glyphs.corner)
        self.put(x + width - 1, y, glyphs.corner)
        self.put(x, y + height - 1, glyphs.corner)
        self.put(x + width - 1, y + height - 1, glyphs.corner)

    def draw_bar(self, x: int, y: int, width: int, ratio: float, glyphs: GlyphSet | None = None) -> None:
        glyphs = glyphs or get_glyph_set("ascii")
        bounded = max(0.0, min(1.0, ratio))
        filled = round(width * bounded)
        for col in range(width):
            self.put(x + col, y, glyphs.solid if col < filled else glyphs.light)

    def draw_sprite(self, x: int, y: int, sprite: list[str] | tuple[str, ...]) -> None:
        for row_offset, row in enumerate(sprite):
            self.draw_text(x, y + row_offset, row)

    def compose(self, other: "Surface", x: int, y: int) -> None:
        for row in range(other.height):
            for col in range(other.width):
                cell = other._cells[row][col]
                if cell.char in {"", " "}:
                    continue
                cell_width = visual_width(cell.char)
                if cell_width > 1:
                    self._put_wide(x + col, y + row, cell.char, fg=cell.fg, bg=cell.bg, style=cell.style)
                elif cell_width == 1:
                    self.put(x + col, y + row, cell.char, fg=cell.fg, bg=cell.bg)

    def render(self) -> list[str]:
        return ["".join(cell.char for cell in row) for row in self._cells]
