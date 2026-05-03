"""Internationalization for UI labels and engine log strings.

Two languages are supported in this slice: ``en`` (ASCII-safe default for
PowerShell/CI) and ``zh`` (default for Chinese players, requires a UTF-8
capable terminal).
"""
from ouro_agent.i18n.strings import (
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    label,
    log_text,
    narration_text,
    visual_width,
    pad_right,
)

__all__ = [
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "label",
    "log_text",
    "narration_text",
    "visual_width",
    "pad_right",
]
