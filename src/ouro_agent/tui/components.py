"""Reusable dependency-free TUI components.

The helpers here are intentionally plain strings. They provide a component
boundary that can later be backed by Rich/Textual without changing combat or
content code.
"""
from __future__ import annotations

from dataclasses import dataclass

from ouro_agent.i18n import pad_right, visual_width
from ouro_agent.tui.layout import fit_text
from ouro_agent.tui.pixel_skin import pixel_panel


@dataclass(frozen=True)
class TuiTab:
    label: str
    active: bool = False
    badge: str | None = None


@dataclass(frozen=True)
class TuiChip:
    label: str
    value: str
    tone: str = "normal"


def render_tab_bar(tabs: list[TuiTab], *, width: int, title: str | None = None) -> list[str]:
    """Render a compact tab strip with deterministic width."""
    inner = max(12, width - 4)
    rendered_tabs: list[str] = []
    for tab in tabs:
        label = tab.label.upper()
        if tab.badge:
            label = f"{label} {tab.badge}"
        rendered_tabs.append(f"[{label}]" if tab.active else f" {label} ")
    row = " | ".join(rendered_tabs)
    panel_title = title or "NAV"
    return list(pixel_panel(panel_title, [fit_text(row, inner)], width, tone="counter").lines)


def render_chip_rail(chips: list[TuiChip], *, width: int, title: str) -> list[str]:
    """Render status chips that stay readable without color."""
    inner = max(12, width - 4)
    rows: list[str] = []
    current = ""
    for chip in chips:
        token = _chip_token(chip)
        if not current:
            current = token
        elif visual_width(current + "  " + token) <= inner:
            current += "  " + token
        else:
            rows.append(current)
            current = token
    if current:
        rows.append(current)
    return list(pixel_panel(title, [fit_text(row, inner) for row in rows], width, tone="quiet").lines)


def render_command_rail(commands: list[tuple[str, str]], *, width: int, title: str) -> list[str]:
    """Render keyboard/CLI actions as a bottom rail."""
    inner = max(12, width - 4)
    rows: list[str] = []
    for label, command in commands:
        rows.append(f"[{label}] {command}")
    return list(pixel_panel(title, [fit_text(row, inner) for row in rows], width, tone="counter").lines)


def render_meter(label: str, current: int, total: int, *, width: int = 14) -> str:
    """Render a tiny ASCII meter for page dashboards."""
    total = max(1, total)
    current = max(0, min(current, total))
    fill_width = max(3, width)
    filled = round(fill_width * (current / total))
    bar = "#" * filled + "-" * (fill_width - filled)
    prefix = f"{label} " if label else ""
    return f"{prefix}[{bar}] {current}/{total}"


def _chip_token(chip: TuiChip) -> str:
    prefix = {
        "danger": "!",
        "counter": ">",
        "hero": "*",
        "quiet": ".",
    }.get(chip.tone, "#")
    return f"{prefix} {chip.label}: {chip.value}"
