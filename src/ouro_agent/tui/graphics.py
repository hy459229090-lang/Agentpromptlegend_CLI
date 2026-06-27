"""Terminal graphics capability selection.

The bitmap renderers arrive in later batches. This module owns the stable
capability contract now so CLI flows can choose a deterministic fallback
without touching combat rules.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Mapping

SUPPORTED_GRAPHICS_MODES: tuple[str, ...] = ("auto", "bitmap", "unicode", "ascii")
BITMAP_BACKENDS: tuple[str, ...] = ("iterm2", "kitty", "sixel")
FALLBACK_CHAIN: tuple[str, ...] = ("iterm2", "kitty", "sixel", "unicode", "ascii")


@dataclass(frozen=True)
class GraphicsCapability:
    """Resolved graphics backend and the reasons behind it."""

    requested_mode: str
    selected_backend: str
    fallback_chain: tuple[str, ...]
    is_tty: bool
    is_ci: bool
    is_pipe: bool
    is_tmux: bool
    no_animation: bool
    no_color: bool
    term: str
    term_program: str
    color_depth: str
    supports_iterm2: bool
    supports_kitty: bool
    supports_sixel: bool
    reasons: tuple[str, ...]

    @property
    def bitmap_supported(self) -> bool:
        return self.supports_iterm2 or self.supports_kitty or self.supports_sixel

    @property
    def selected_is_bitmap(self) -> bool:
        return self.selected_backend in BITMAP_BACKENDS


def normalize_graphics_mode(value: str | None) -> str:
    mode = (value or "auto").strip().lower()
    if mode not in SUPPORTED_GRAPHICS_MODES:
        supported = ", ".join(SUPPORTED_GRAPHICS_MODES)
        raise ValueError(f"graphics must be one of {supported}; got {value!r}")
    return mode


def select_graphics_backend(
    *,
    requested_mode: str = "auto",
    env: Mapping[str, str] | None = None,
    stdout_is_tty: bool | None = None,
    no_animation: bool = False,
) -> GraphicsCapability:
    """Select the best terminal graphics backend for the current environment."""

    mode = normalize_graphics_mode(requested_mode)
    env_map = dict(os.environ if env is None else env)
    is_tty = sys.stdout.isatty() if stdout_is_tty is None else bool(stdout_is_tty)
    is_ci = _truthy(env_map.get("CI")) or _truthy(env_map.get("GITHUB_ACTIONS"))
    is_pipe = not is_tty
    term = env_map.get("TERM", "")
    term_program = env_map.get("TERM_PROGRAM", "")
    color_depth = env_map.get("COLORTERM") or env_map.get("TERM_COLOR_DEPTH", "")
    is_tmux = bool(env_map.get("TMUX")) or term.startswith(("tmux", "screen"))
    no_color = "NO_COLOR" in env_map

    supports_iterm2 = _supports_iterm2(env_map)
    supports_kitty = _supports_kitty(env_map)
    supports_sixel = _supports_sixel(env_map)
    reasons: list[str] = []

    if no_color:
        reasons.append("NO_COLOR is set; color is optional and may be disabled.")
    if no_animation:
        reasons.append("--no-animation requested; live bitmap loops are disabled.")
    if is_ci:
        reasons.append("CI environment detected; deterministic fallback is preferred.")
    if is_pipe:
        reasons.append("stdout is not a TTY; terminal graphics escape output is unsafe.")
    if is_tmux and mode == "auto":
        reasons.append("tmux/screen detected; auto mode skips bitmap unless forced.")

    selected = "ascii"
    if mode == "ascii":
        selected = "ascii"
        reasons.append("--graphics ascii forces ASCII-safe rendering.")
    elif mode == "unicode":
        selected = "unicode"
        if is_pipe or is_ci:
            reasons.append("--graphics unicode forces deterministic Unicode cell output.")
        else:
            reasons.append("--graphics unicode forces Unicode cell sprite fallback.")
    elif mode == "bitmap":
        if is_pipe or is_ci or no_animation:
            selected = "unicode" if is_tty and not is_ci else "ascii"
            reasons.append("--graphics bitmap requested but bitmap is unsafe here; using fallback.")
        else:
            selected = _best_bitmap_backend(
                supports_iterm2=supports_iterm2,
                supports_kitty=supports_kitty,
                supports_sixel=supports_sixel,
            )
            if selected in BITMAP_BACKENDS:
                reasons.append(f"--graphics bitmap selected {selected}.")
            else:
                selected = "unicode"
                reasons.append("No bitmap protocol detected; using Unicode cell fallback.")
    else:
        if is_pipe or is_ci or no_animation:
            selected = "ascii"
            reasons.append("auto selected ASCII fallback for deterministic output.")
        elif is_tmux:
            selected = "unicode"
            reasons.append("auto selected Unicode fallback under tmux/screen.")
        else:
            selected = _best_bitmap_backend(
                supports_iterm2=supports_iterm2,
                supports_kitty=supports_kitty,
                supports_sixel=supports_sixel,
            )
            if selected in BITMAP_BACKENDS:
                reasons.append(f"auto selected {selected} bitmap graphics.")
            else:
                selected = "unicode"
                reasons.append("auto selected Unicode cell sprite fallback.")

    return GraphicsCapability(
        requested_mode=mode,
        selected_backend=selected,
        fallback_chain=FALLBACK_CHAIN,
        is_tty=is_tty,
        is_ci=is_ci,
        is_pipe=is_pipe,
        is_tmux=is_tmux,
        no_animation=no_animation,
        no_color=no_color,
        term=term or "-",
        term_program=term_program or "-",
        color_depth=color_depth or "-",
        supports_iterm2=supports_iterm2,
        supports_kitty=supports_kitty,
        supports_sixel=supports_sixel,
        reasons=tuple(reasons),
    )


def graphics_prefers_unicode(capability: GraphicsCapability) -> bool:
    """Return whether the selected backend should use Unicode-enhanced HUD."""

    return capability.selected_backend in {"unicode", *BITMAP_BACKENDS}


def render_graphics_doctor(capability: GraphicsCapability) -> str:
    """Render an ASCII-safe capability report for `ouro doctor graphics`."""

    lines = [
        "GRAPHICS PREFLIGHT",
        f"requested    : {capability.requested_mode}",
        f"selected     : {capability.selected_backend}",
        "fallback     : " + " -> ".join(capability.fallback_chain),
        f"tty          : {_yes_no(capability.is_tty)}",
        f"ci           : {_yes_no(capability.is_ci)}",
        f"pipe         : {_yes_no(capability.is_pipe)}",
        f"tmux/screen  : {_yes_no(capability.is_tmux)}",
        f"no animation : {_yes_no(capability.no_animation)}",
        f"no color     : {_yes_no(capability.no_color)}",
        f"TERM         : {capability.term}",
        f"TERM_PROGRAM : {capability.term_program}",
        f"color depth  : {capability.color_depth}",
        f"iterm2 image : {_yes_no(capability.supports_iterm2)}",
        f"kitty image  : {_yes_no(capability.supports_kitty)}",
        f"sixel image  : {_yes_no(capability.supports_sixel)}",
        f"unicode cell : yes",
        f"ascii safe   : yes",
        "",
        "Reasons:",
    ]
    if capability.reasons:
        lines.extend(f"- {reason}" for reason in capability.reasons)
    else:
        lines.append("- No special fallback reason detected.")
    lines.extend(
        [
            "",
            "Force with: --graphics auto | bitmap | unicode | ascii",
            "Runtime image generation: disabled; assets must be local and QA passed.",
        ]
    )
    return "\n".join(lines)


def _best_bitmap_backend(
    *,
    supports_iterm2: bool,
    supports_kitty: bool,
    supports_sixel: bool,
) -> str:
    if supports_iterm2:
        return "iterm2"
    if supports_kitty:
        return "kitty"
    if supports_sixel:
        return "sixel"
    return ""


def _supports_iterm2(env: Mapping[str, str]) -> bool:
    program = env.get("TERM_PROGRAM", "").lower()
    return program in {"iterm.app", "iterm2"}


def _supports_kitty(env: Mapping[str, str]) -> bool:
    term = env.get("TERM", "").lower()
    program = env.get("TERM_PROGRAM", "").lower()
    return (
        "xterm-kitty" in term
        or "xterm-ghostty" in term
        or program in {"kitty", "ghostty"}
        or bool(env.get("KITTY_WINDOW_ID"))
    )


def _supports_sixel(env: Mapping[str, str]) -> bool:
    if _truthy(env.get("OURO_GRAPHICS_SIXEL")):
        return True
    term = env.get("TERM", "").lower()
    program = env.get("TERM_PROGRAM", "").lower()
    return "sixel" in term or program in {"rio", "wezterm"}


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
