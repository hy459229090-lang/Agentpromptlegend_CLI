"""ASCII glyph helpers.

ASCII-safe by default; Unicode is an optional enhancement and never required
by the engine or tests.
"""
from __future__ import annotations

from typing import Literal


def bar(value: int, maximum: int, width: int = 10, *, unicode_mode: bool = False) -> str:
    """Render a bracket-style bar that is readable in PowerShell and CI."""
    if maximum <= 0:
        return "[" + (" " * width) + "]"
    ratio = max(0.0, min(1.0, value / maximum))
    filled = int(round(ratio * width))
    if unicode_mode:
        return "[" + ("\u2588" * filled) + ("\u2591" * (width - filled)) + "]"
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def hp_bar(
    value: int,
    maximum: int,
    width: int = 10,
    *,
    unicode_mode: bool = False,
    show_percent: bool = False,
    show_value: bool = True,
    enhanced: bool = False,
) -> str:
    """Render a stylized HP bar.
    
    Default behavior matches the classic bar() function for backward compatibility.
    Set enhanced=True to enable additional features.
    
    Classic format (default):
        HP [########--] 82/100
    
    Enhanced format (enhanced=True):
        HP {~~~~~~~~} [!] 82/100 (82%)
        - Different borders based on state: [] / {} / <>
        - State indicators: [!] wounded, [!!!] critical
        - Optional percentage display
    
    Args:
        value: Current HP
        maximum: Maximum HP
        width: Width of the bar (excluding brackets and labels)
        unicode_mode: Use Unicode block characters
        show_percent: Show percentage after the bar
        show_value: Show value/maximum after the bar
        enhanced: Enable enhanced visual features
    
    Returns:
        Formatted HP bar string
    """
    if maximum <= 0:
        empty = " " * width
        bar_str = f"[ {empty} ]"
        if show_value:
            bar_str += f" 0/0"
        if show_percent:
            bar_str += " (0%)"
        return bar_str
    
    ratio = max(0.0, min(1.0, value / maximum))
    percent = int(ratio * 100)
    filled = int(round(ratio * width))
    
    # Determine health state (for enhanced mode
    if ratio > 0.7:
        state = "healthy"
    elif ratio > 0.3:
        state = "wounded"
    else:
        state = "critical"
    
    # Build the bar
    if unicode_mode:
        filled_char = "\u2588"  # Full block
        empty_char = "\u2591"  # Light shade
        border_left = "["
        border_right = "]"
    else:
        if enhanced:
            # Enhanced mode: different characters based on state
            filled_char = {
                "healthy": "#",
                "wounded": "#",
                "critical": "#",
            }.get(state, "#")
            border_left = {
                "healthy": "[",
                "wounded": "{",
                "critical": "<",
            }.get(state, "[")
            border_right = {
                "healthy": "]",
                "wounded": "}",
                "critical": ">",
            }.get(state, "]")
        else:
            # Classic mode: same as bar()
            filled_char = "#"
            border_left = "["
            border_right = "]"
        empty_char = "-"
    
    bar_inner = (filled_char * filled) + (empty_char * (width - filled))
    bar_str = f"{border_left}{bar_inner}{border_right}"
    
    # Add state indicator for enhanced mode
    if enhanced:
        state_indicator = {
            "healthy": "",
            "wounded": " [!]",
            "critical": " [!!!]",
        }.get(state, "")
        bar_str += state_indicator
    
    # Add value display
    if show_value:
        bar_str += f" {value}/{maximum}"
    
    # Add percentage display
    if show_percent:
        bar_str += f" ({percent}%)"
    
    return bar_str


def mp_bar(
    value: int,
    maximum: int,
    width: int = 8,
    *,
    unicode_mode: bool = False,
    show_percent: bool = False,
    show_value: bool = True,
    enhanced: bool = False,
) -> str:
    """Render a stylized MP bar.
    
    Default behavior matches the classic bar() function for backward compatibility.
    Set enhanced=True to enable additional features.
    
    Classic format (default):
        MP [#####---] 31/48
    
    Enhanced format (enhanced=True):
        MP (      ) [EMPTY] 0/48
        MP [*****] [LOW] 12/48
        - Different borders for empty/low
        - State indicators: [LOW], [EMPTY]
        - Optional percentage display
    
    Args:
        value: Current MP
        maximum: Maximum MP
        width: Width of the bar (excluding brackets and labels)
        unicode_mode: Use Unicode block characters
        show_percent: Show percentage after the bar
        show_value: Show value/maximum after the bar
        enhanced: Enable enhanced visual features
    
    Returns:
        Formatted MP bar string
    """
    if maximum <= 0:
        empty = " " * width
        bar_str = f"[ {empty} ]"
        if show_value:
            bar_str += f" 0/0"
        if show_percent:
            bar_str += " (0%)"
        return bar_str
    
    ratio = max(0.0, min(1.0, value / maximum))
    percent = int(ratio * 100)
    filled = int(round(ratio * width))
    
    # Check if MP is empty or low (for enhanced mode
    is_low = ratio < 0.3
    is_empty = ratio == 0.0
    
    if unicode_mode:
        filled_char = "\u2588"  # Full block
        empty_char = "\u2591"  # Light shade
        border_left = "["
        border_right = "]"
    else:
        if enhanced:
            # Enhanced mode: different borders for empty/low
            filled_char = "#"  # Same as bar()
            border_left = "(" if is_empty else "["
            border_right = ")" if is_empty else "]"
        else:
            # Classic mode: same as bar()
            filled_char = "#"
            border_left = "["
            border_right = "]"
        empty_char = "-"  # Same as bar()
    
    bar_inner = (filled_char * filled) + (empty_char * (width - filled))
    bar_str = f"{border_left}{bar_inner}{border_right}"
    
    # Add state indicator for enhanced mode
    if enhanced:
        if is_empty:
            bar_str += " [EMPTY]"
        elif is_low:
            bar_str += " [LOW]"
    
    # Add value display
    if show_value:
        bar_str += f" {value}/{maximum}"
    
    # Add percentage display
    if show_percent:
        bar_str += f" ({percent}%)"
    
    return bar_str


def atb_bar(
    value: int,
    maximum: int = 100,
    width: int = 6,
    *,
    unicode_mode: bool = False,
    show_ready: bool = False,
    enhanced: bool = False,
) -> str:
    """Render a stylized ATB (Active Time Battle) bar.
    
    Default behavior matches the classic bar() function for backward compatibility.
    Set enhanced=True to enable additional features.
    
    Classic format (default):
        ATB [####--]
    
    Enhanced format (enhanced=True):
        ATB [>>>>>>] [READY]
        ATB [====--] 40
        - Different characters for charging vs ready
        - Ready indicator
        - Shows value when charging
    
    Args:
        value: Current ATB value
        maximum: Maximum ATB (usually 100)
        width: Width of the bar (excluding brackets)
        unicode_mode: Use Unicode block characters
        show_ready: Show "READY" indicator when full
        enhanced: Enable enhanced visual features
    
    Returns:
        Formatted ATB bar string
    """
    ratio = max(0.0, min(1.0, value / maximum))
    filled = int(round(ratio * width))
    is_ready = ratio >= 1.0
    
    if unicode_mode:
        filled_char = "\u2588"  # Full block
        empty_char = "\u2591"  # Light shade
        border_left = "["
        border_right = "]"
    else:
        if enhanced:
            # Enhanced mode: different characters for charging vs ready
            filled_char = ">" if is_ready else "="
        else:
            # Classic mode: same as bar()
            filled_char = "#"
        border_left = "["
        border_right = "]"
        empty_char = "-"  # Same as bar()
    
    bar_inner = (filled_char * filled) + (empty_char * (width - filled))
    bar_str = f"{border_left}{bar_inner}{border_right}"
    
    # Add ready indicator for enhanced mode
    if enhanced or show_ready:
        if is_ready:
            bar_str += " [READY]"
        elif not is_ready and enhanced:
            bar_str += f" {value}"
    
    return bar_str


def shield_indicator(
    shield_stacks: int,
    *,
    unicode_mode: bool = False,
) -> str:
    """Render a shield indicator.
    
    Args:
        shield_stacks: Number of shield stacks
        unicode_mode: Use Unicode symbols
    
    Returns:
        Formatted shield indicator
    """
    if shield_stacks <= 0:
        return ""
    
    if unicode_mode:
        shield_char = "\u2592"  # Medium shade
        return f"[SHIELD:{shield_stacks}]"
    else:
        return f"[SHIELD:{shield_stacks}]"


def status_indicator(
    statuses: list,
    *,
    max_display: int = 3,
    unicode_mode: bool = False,
) -> str:
    """Render a compact status indicator.
    
    Args:
        statuses: List of status effects
        max_display: Maximum number of statuses to display
        unicode_mode: Use Unicode symbols
    
    Returns:
        Formatted status indicator string
    """
    if not statuses:
        return ""
    
    # Sort statuses by importance (buffs first, then debuffs)
    buffs = []
    debuffs = []
    for s in statuses:
        status_id = s.id if hasattr(s, "id") else str(s)
        is_buff = status_id in {"status_shield", "status_focus", "status_haste", "status_guard"}
        if is_buff:
            buffs.append(s)
        else:
            debuffs.append(s)
    
    sorted_statuses = buffs + debuffs
    display_count = min(max_display, len(sorted_statuses))
    
    parts = []
    for i in range(display_count):
        s = sorted_statuses[i]
        status_id = s.id if hasattr(s, "id") else str(s)
        stacks = s.stacks if hasattr(s, "stacks") else 1
        duration = s.duration if hasattr(s, "duration") else "?"
        
        # Short status name
        short_name = {
            "status_shield": "SHLD",
            "status_focus": "FOCS",
            "status_haste": "HSTE",
            "status_guard": "GRD",
            "status_poison": "PSN",
            "status_bleed": "BLD",
            "status_silence": "SLNC",
            "status_corruption": "CORR",
        }.get(status_id, status_id.replace("status_", "")[:4].upper())
        
        parts.append(f"{short_name}:{stacks}")
    
    if len(sorted_statuses) > max_display:
        parts.append(f"+{len(sorted_statuses) - max_display}")
    
    return " " + " ".join(parts)


def hero_short_tag(short_tag: str, name: str, class_name: str) -> str:
    return f"{short_tag} {name}  {class_name}"


def hero_avatar(lines: list[str] | tuple[str, ...]) -> list[str]:
    """Return a copy with no leading/trailing blank lines."""
    return [line.rstrip() for line in lines]
