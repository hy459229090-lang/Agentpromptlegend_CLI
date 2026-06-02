"""Terminal control utilities for refreshing displays.

This module provides cross-platform terminal control for:
- Clearing the screen
- Moving the cursor
- Hiding/showing the cursor
- Refreshing the display

ANSI escape codes are used for terminal control. These work on:
- macOS Terminal
- Linux terminals
- Windows 10+ with VT100 support

For Windows compatibility, we also provide fallbacks.
"""
import os
import sys
from typing import Optional

# ANSI escape codes for terminal control
ANSI_CLEAR_SCREEN = "\x1b[2J"
ANSI_CLEAR_TO_END = "\x1b[0J"
ANSI_CLEAR_TO_BEGINNING = "\x1b[1J"
ANSI_CLEAR_LINE = "\x1b[2K"
ANSI_CLEAR_LINE_TO_END = "\x1b[0K"
ANSI_CLEAR_LINE_TO_BEGINNING = "\x1b[1K"

ANSI_MOVE_TO = "\x1b[{row};{col}H"
ANSI_MOVE_HOME = "\x1b[H"
ANSI_MOVE_UP = "\x1b[{n}A"
ANSI_MOVE_DOWN = "\x1b[{n}B"
ANSI_MOVE_RIGHT = "\x1b[{n}C"
ANSI_MOVE_LEFT = "\x1b[{n}D"

ANSI_SAVE_CURSOR = "\x1b[s"
ANSI_RESTORE_CURSOR = "\x1b[u"

ANSI_HIDE_CURSOR = "\x1b[?25l"
ANSI_SHOW_CURSOR = "\x1b[?25h"

ANSI_SAVE_SCREEN = "\x1b[?47h"
ANSI_RESTORE_SCREEN = "\x1b[?47l"


class Terminal:
    """Terminal control for refreshing displays.

    This class provides a high-level interface for terminal control,
    with support for refreshing displays and handling animations.

    Usage:
        with Terminal(refresh=True) as term:
            for frame in frames:
                term.render(frame)
                time.sleep(0.1)
    """

    def __init__(
        self,
        refresh: bool = False,
        clear_screen: bool = False,
        hide_cursor: bool = True,
        save_screen: bool = False,
    ):
        """Initialize terminal control.
        
        Args:
            refresh: If True, use cursor positioning for refresh instead of scrolling
            clear_screen: If True, clear the screen when starting
            hide_cursor: If True, hide the cursor during the session
            save_screen: If True, save the screen state and restore it when done
        """
        self.refresh = refresh
        self.clear_screen = clear_screen
        self.hide_cursor = hide_cursor
        self.save_screen = save_screen
        
        self._cursor_hidden = False
        self._screen_saved = False
        self._last_frame_lines: int = 0

    def __enter__(self) -> "Terminal":
        """Enter context manager."""
        if self.save_screen:
            self._save_screen()
        if self.clear_screen:
            self.clear()
        if self.hide_cursor:
            self._hide_cursor()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self.hide_cursor and self._cursor_hidden:
            self._show_cursor()
        if self.save_screen and self._screen_saved:
            self._restore_screen()
        else:
            # Ensure we're at the start of a new line
            sys.stdout.write("\n")
            sys.stdout.flush()
    
    def clear(self) -> None:
        """Clear the screen and move cursor to home position."""
        if self._is_terminal():
            sys.stdout.write(ANSI_MOVE_HOME)
            sys.stdout.write(ANSI_CLEAR_TO_END)
            sys.stdout.flush()
        else:
            sys.stdout.write("\n" * 100)
            sys.stdout.flush()
    
    def _hide_cursor(self) -> None:
        """Hide the cursor."""
        if self._is_terminal():
            sys.stdout.write(ANSI_HIDE_CURSOR)
            sys.stdout.flush()
            self._cursor_hidden = True
    
    def _show_cursor(self) -> None:
        """Show the cursor."""
        if self._is_terminal():
            sys.stdout.write(ANSI_SHOW_CURSOR)
            sys.stdout.flush()
            self._cursor_hidden = False
    
    def _save_screen(self) -> None:
        """Save the current screen state."""
        if self._is_terminal():
            sys.stdout.write(ANSI_SAVE_SCREEN)
            sys.stdout.flush()
            self._screen_saved = True
    
    def _restore_screen(self) -> None:
        """Restore the saved screen state."""
        if self._is_terminal():
            sys.stdout.write(ANSI_RESTORE_SCREEN)
            sys.stdout.flush()
            self._screen_saved = False
    
    def _is_terminal(self) -> bool:
        """Check if stdout is a terminal."""
        return sys.stdout.isatty()
    
    def _move_up(self, lines: int) -> None:
        """Move cursor up N lines to the start of the frame."""
        if self._is_terminal() and lines > 0:
            sys.stdout.write(ANSI_MOVE_UP.format(n=lines))
            sys.stdout.flush()

    def _clear_from_cursor(self) -> None:
        """Clear from cursor position to end of screen."""
        if self._is_terminal():
            sys.stdout.write(ANSI_CLEAR_TO_END)
            sys.stdout.flush()
    
    def _count_lines(self, text: str) -> int:
        """Count the number of lines in text, accounting for wrapped lines."""
        lines = text.split("\n")
        total = 0
        width = self._get_terminal_width()
        for line in lines:
            if width > 0:
                line_length = len(line)
                if line_length == 0:
                    total += 1
                elif line_length % width == 0:
                    total += line_length // width
                else:
                    total += (line_length + width - 1) // width
            else:
                total += 1
        return total
    
    def _get_terminal_width(self) -> int:
        """Get terminal width."""
        try:
            return os.get_terminal_size().columns
        except OSError:
            return 0
    
    def render(
        self,
        content: str,
        *,
        clear_previous: bool = True,
    ) -> None:
        """Render content to the terminal.
        
        Args:
            content: The content to render
            clear_previous: If True, clear the previous frame (only in refresh mode)
        """
        if self.refresh and self._is_terminal():
            new_lines = self._count_lines(content)

            if clear_previous and self._last_frame_lines > 0:
                self._move_up(self._last_frame_lines)
                self._clear_from_cursor()

            self._last_frame_lines = new_lines

            sys.stdout.write(content)
            if not content.endswith("\n"):
                sys.stdout.write("\n")
            sys.stdout.flush()
        else:
            sys.stdout.write(content)
            if not content.endswith("\n"):
                sys.stdout.write("\n")
            sys.stdout.flush()


def get_terminal(
    refresh: bool = False,
    clear_screen: bool = False,
    hide_cursor: bool = True,
    save_screen: bool = False,
) -> Terminal:
    """Get a Terminal instance for display control.
    
    Args:
        refresh: If True, use refresh mode instead of scrolling
        clear_screen: If True, clear the screen when starting
        hide_cursor: If True, hide the cursor during the session
        save_screen: If True, save and restore the screen state
    
    Returns:
        A Terminal instance
    """
    return Terminal(
        refresh=refresh,
        clear_screen=clear_screen,
        hide_cursor=hide_cursor,
        save_screen=save_screen,
    )
