"""Shared test fixtures."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def repo_root() -> Path:
    return ROOT


@pytest.fixture()
def content_root(repo_root: Path) -> Path:
    return repo_root / "content"


@pytest.fixture()
def isolated_home(tmp_path, monkeypatch) -> Path:
    monkeypatch.setenv("OURO_AGENT_HOME", str(tmp_path))
    yield tmp_path
