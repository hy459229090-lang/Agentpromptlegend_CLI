from __future__ import annotations

import sys

from ouro_agent.tui.terminal import (
    ANSI_CLEAR_LINE,
    ANSI_HIDE_CURSOR,
    ANSI_RESTORE_SCREEN,
    ANSI_SAVE_SCREEN,
    ANSI_SHOW_CURSOR,
    Terminal,
)


class _FakeStdout:
    def __init__(self, *, tty: bool) -> None:
        self.tty = tty
        self.chunks: list[str] = []

    def isatty(self) -> bool:
        return self.tty

    def write(self, text: str) -> int:
        self.chunks.append(text)
        return len(text)

    def flush(self) -> None:
        return None

    def clear(self) -> None:
        self.chunks.clear()

    @property
    def text(self) -> str:
        return "".join(self.chunks)


def test_terminal_partial_refresh_repaints_only_changed_rows(monkeypatch):
    """REQ-TUIMOTION-011: TTY animation should use row-level refresh."""
    fake = _FakeStdout(tty=True)
    monkeypatch.setattr(sys, "stdout", fake)
    term = Terminal(refresh=True, hide_cursor=False)

    term.render("LOCK\nPULSE\nJUDGE", partial=True)
    assert "\x1b[1;1H" in fake.text
    assert "LOCK" in fake.text
    assert "PULSE" in fake.text
    assert "JUDGE" in fake.text

    fake.clear()
    term.render("LOCK\nIMPACT\nJUDGE", partial=True)

    assert "\x1b[2;1H" in fake.text
    assert ANSI_CLEAR_LINE in fake.text
    assert "IMPACT" in fake.text
    assert "LOCK" not in fake.text
    assert "\x1b[1;1H" not in fake.text

    fake.clear()
    term.render("APPEND", partial=True, clear_previous=False)
    assert fake.text == "APPEND\n"


def test_terminal_partial_refresh_does_not_emit_ansi_for_pipes(monkeypatch):
    """REQ-TUIMOTION-011: non-TTY and captured output stay log-safe."""
    fake = _FakeStdout(tty=False)
    monkeypatch.setattr(sys, "stdout", fake)
    term = Terminal(refresh=True, hide_cursor=False)

    term.render("LOCK\nIMPACT", partial=True)

    assert fake.text == "LOCK\nIMPACT\n"
    assert "\x1b[" not in fake.text


def test_terminal_refresh_session_uses_alternate_screen(monkeypatch):
    """REQ-TUIMOTION-012: default TTY animation should feel like a modern TUI."""
    fake = _FakeStdout(tty=True)
    monkeypatch.setattr(sys, "stdout", fake)

    with Terminal(refresh=True, hide_cursor=True, save_screen=True) as term:
        term.render("MODE\nFRAME", partial=True)

    text = fake.text
    assert ANSI_SAVE_SCREEN == "\x1b[?1049h"
    assert ANSI_RESTORE_SCREEN == "\x1b[?1049l"
    assert ANSI_SAVE_SCREEN in text
    assert ANSI_HIDE_CURSOR in text
    assert "MODE" in text
    assert "FRAME" in text
    assert ANSI_SHOW_CURSOR in text
    assert ANSI_RESTORE_SCREEN in text
    assert text.index(ANSI_SAVE_SCREEN) < text.index(ANSI_HIDE_CURSOR)
    assert text.index(ANSI_SHOW_CURSOR) < text.index(ANSI_RESTORE_SCREEN)


def test_terminal_alternate_screen_does_not_emit_for_pipes(monkeypatch):
    """REQ-TUIMOTION-012: captured output stays plain text."""
    fake = _FakeStdout(tty=False)
    monkeypatch.setattr(sys, "stdout", fake)

    with Terminal(refresh=True, hide_cursor=True, save_screen=True) as term:
        term.render("MODE\nFRAME", partial=True)

    assert fake.text == "MODE\nFRAME\n\n"
    assert ANSI_SAVE_SCREEN not in fake.text
    assert ANSI_RESTORE_SCREEN not in fake.text
    assert ANSI_HIDE_CURSOR not in fake.text


def test_terminal_input_mode_temporarily_restores_cursor(monkeypatch):
    """REQ-TUIMOTION-015: live TTY input should have a visible cursor."""
    fake = _FakeStdout(tty=True)
    monkeypatch.setattr(sys, "stdout", fake)

    with Terminal(refresh=True, hide_cursor=True, save_screen=False) as term:
        assert ANSI_HIDE_CURSOR in fake.text
        fake.clear()
        with term.input_mode():
            sys.stdout.write("typing")
        term.clear_input_echo_line()

    text = fake.text
    assert ANSI_SHOW_CURSOR in text
    assert "typing" in text
    assert ANSI_HIDE_CURSOR in text
    assert "\x1b[1A" in text
    assert ANSI_CLEAR_LINE in text
    assert text.index(ANSI_SHOW_CURSOR) < text.index("typing")
    assert text.index("typing") < text.index(ANSI_HIDE_CURSOR)
    assert text.index(ANSI_HIDE_CURSOR) < text.index("\x1b[1A")

    fake_pipe = _FakeStdout(tty=False)
    monkeypatch.setattr(sys, "stdout", fake_pipe)
    with Terminal(refresh=True, hide_cursor=True, save_screen=False) as term:
        with term.input_mode():
            sys.stdout.write("typing")
        term.clear_input_echo_line()

    assert fake_pipe.text == "typing\n"
    assert ANSI_SHOW_CURSOR not in fake_pipe.text
    assert ANSI_HIDE_CURSOR not in fake_pipe.text
