"""Small ANSI helpers for optional, no-color-safe TUI theming."""
from __future__ import annotations

import os
import re


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
RESET = "\x1b[0m"

TONE_STYLES: dict[str, str] = {
    "normal": "\x1b[38;5;250m",
    "hero": "\x1b[38;5;220m",
    "enemy": "\x1b[38;5;203m",
    "danger": "\x1b[38;5;196m",
    "counter": "\x1b[38;5;81m",
    "climax": "\x1b[1;38;5;226m",
    "quiet": "\x1b[38;5;245m",
    "hp": "\x1b[38;5;82m",
    "mp": "\x1b[38;5;75m",
    "atb": "\x1b[38;5;220m",
}


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def color_enabled(mode: str | None, *, is_tty: bool | None = None) -> bool:
    normalized = (mode or "never").lower()
    if normalized in {"never", "false", "0", "no"}:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    if normalized in {"always", "true", "1", "yes"}:
        return True
    return bool(is_tty)


def paint(text: str, tone: str) -> str:
    style = TONE_STYLES.get(tone, TONE_STYLES["normal"])
    return f"{style}{text}{RESET}"
