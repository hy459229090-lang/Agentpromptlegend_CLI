"""Content path discovery for source trees and installed wheels."""
from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_CONTENT_DIR = "content"
DATA_SHARE_DIR = Path("share") / "ouro-agent" / "content"


def source_content_dir() -> Path:
    return Path(__file__).resolve().parents[3] / DEFAULT_CONTENT_DIR


def installed_content_dir() -> Path:
    return Path(sys.prefix) / DATA_SHARE_DIR


def default_content_dir() -> Path:
    cwd_content = Path(DEFAULT_CONTENT_DIR)
    if cwd_content.exists():
        return cwd_content
    packaged = installed_content_dir()
    if packaged.exists():
        return packaged
    return cwd_content


def resolve_content_dir(content_dir: str | Path) -> Path:
    path = Path(content_dir)
    if path == Path(DEFAULT_CONTENT_DIR) and not path.exists():
        return default_content_dir()
    return path
