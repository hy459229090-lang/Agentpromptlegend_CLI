#!/usr/bin/env python3
"""Audit the git working tree against the release-candidate boundary."""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

RELEASE_EXACT = {
    ".gitignore",
    "AGENTS.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "LICENSE",
    "README.md",
    "README.zh.md",
    "pyproject.toml",
}
RELEASE_PREFIXES = (
    "content/",
    "docs/",
    "examples/",
    "scripts/",
    "src/ouro_agent/",
    "tests/",
)
LOCAL_PREFIXES = (
    ".git/",
    ".mypy_cache/",
    ".obsidian/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".venv/",
    "build/",
    "dist/",
    "logs/",
    "runs/",
    "traces/",
    "venv/",
    "venv312/",
)
LOCAL_SUFFIXES = (
    ".egg-info/",
)
LOCAL_EXACT = {
    ".env",
}
STAGE_GROUP_ORDER = (
    "root",
    "content",
    "docs",
    "examples",
    "scripts",
    "src",
    "tests",
)
STAGE_GROUP_LABELS = {
    "root": "root release files",
    "content": "structured content",
    "docs": "product and engineering docs",
    "examples": "examples",
    "scripts": "developer scripts",
    "src": "runtime package",
    "tests": "tests",
}


@dataclass(frozen=True)
class ScopeReport:
    release_bound: tuple[str, ...]
    local_only: tuple[str, ...]
    unknown: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.local_only and not self.unknown

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "release_bound_count": len(self.release_bound),
            "local_only_count": len(self.local_only),
            "unknown_count": len(self.unknown),
            "release_bound": list(self.release_bound),
            "local_only": list(self.local_only),
            "unknown": list(self.unknown),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that changed paths fit the v0.1.0 release boundary."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write a machine-readable scope report.",
    )
    parser.add_argument(
        "--stage-plan",
        action="store_true",
        help="Print grouped git add commands for release-bound paths without staging.",
    )
    parser.add_argument(
        "--root",
        default=str(ROOT),
        help="Repository root to inspect (default: current project root).",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    try:
        report = build_scope_report(root)
    except RuntimeError as err:
        if args.json:
            json.dump({"ok": False, "error": str(err)}, sys.stdout, indent=2)
            print()
        else:
            print(f"Release scope check failed: {err}")
        return 1

    if args.json:
        payload = {"root": str(root), **report.to_dict()}
        if args.stage_plan:
            payload["stage_plan_ready"] = report.ok
            payload["stage_plan"] = (
                list(stage_plan_commands(report.release_bound)) if report.ok else []
            )
        json.dump(payload, sys.stdout, indent=2)
        print()
    elif args.stage_plan:
        if report.ok:
            _print_stage_plan(root, report)
        else:
            _print_report(root, report)
            print("")
            print("Stage plan blocked: resolve local-only or unknown paths first.")
    else:
        _print_report(root, report)
    return 0 if report.ok else 1


def build_scope_report(root: Path = ROOT) -> ScopeReport:
    paths = _git_status_paths(root)
    release_bound: list[str] = []
    local_only: list[str] = []
    unknown: list[str] = []
    for path in paths:
        category = classify_path(path)
        if category == "release-bound":
            release_bound.append(path)
        elif category == "local-only":
            local_only.append(path)
        else:
            unknown.append(path)
    return ScopeReport(
        release_bound=tuple(sorted(release_bound)),
        local_only=tuple(sorted(local_only)),
        unknown=tuple(sorted(unknown)),
    )


def classify_path(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        return "unknown"
    if _is_local_only(normalized):
        return "local-only"
    if normalized in RELEASE_EXACT:
        return "release-bound"
    if normalized.startswith(RELEASE_PREFIXES):
        return "release-bound"
    return "unknown"


def stage_plan_commands(paths: tuple[str, ...], chunk_size: int = 12) -> tuple[str, ...]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    commands: list[str] = []
    for _, group_paths in iter_stage_plan_sections(paths, chunk_size=chunk_size):
        commands.extend(group_paths)
    return tuple(commands)


def iter_stage_plan_sections(
    paths: tuple[str, ...], chunk_size: int = 12
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")

    grouped: dict[str, list[str]] = {}
    for path in sorted(paths):
        group = _stage_group(path)
        grouped.setdefault(group, []).append(path)

    sections: list[tuple[str, tuple[str, ...]]] = []
    for group in STAGE_GROUP_ORDER:
        group_paths = grouped.get(group, [])
        if not group_paths:
            continue
        commands = tuple(
            _stage_command(chunk) for chunk in _chunked(group_paths, chunk_size)
        )
        sections.append((STAGE_GROUP_LABELS.get(group, group), commands))
    return tuple(sections)


def _is_local_only(path: str) -> bool:
    if path in LOCAL_EXACT:
        return True
    if path.startswith(".env."):
        return True
    if path.endswith(".local") or ".local." in path:
        return True
    if path.startswith(LOCAL_PREFIXES):
        return True
    return any(part in path for part in LOCAL_SUFFIXES)


def _stage_group(path: str) -> str:
    normalized = path.strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized in RELEASE_EXACT or "/" not in normalized:
        return "root"
    if normalized.startswith("src/ouro_agent/"):
        return "src"
    return normalized.split("/", 1)[0]


def _stage_command(paths: tuple[str, ...]) -> str:
    quoted = " ".join(shlex.quote(path) for path in paths)
    return f"git add -- {quoted}"


def _chunked(paths: list[str], chunk_size: int) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(paths[index : index + chunk_size])
        for index in range(0, len(paths), chunk_size)
    )


def _git_status_paths(root: Path) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(detail or f"git status exited with {result.returncode}")

    paths: list[str] = []
    parts = result.stdout.split(b"\0")
    index = 0
    while index < len(parts):
        entry = parts[index]
        if not entry:
            index += 1
            continue
        if len(entry) < 4:
            index += 1
            continue
        status = entry[:2].decode("ascii", errors="replace")
        path = entry[3:].decode("utf-8", errors="surrogateescape")
        paths.append(path)
        index += 1
        if "R" in status or "C" in status:
            index += 1
    return tuple(paths)


def _print_report(root: Path, report: ScopeReport) -> None:
    print("RELEASE SCOPE CHECK")
    print(f"repo: {root}")
    print(f"release-bound changes : {len(report.release_bound)}")
    print(f"local-only changes    : {len(report.local_only)}")
    print(f"unknown changes       : {len(report.unknown)}")
    if report.local_only:
        print("")
        print("Local-only paths should not be staged:")
        for path in report.local_only:
            print(f"  - {path}")
    if report.unknown:
        print("")
        print("Unknown paths need manifest review:")
        for path in report.unknown:
            print(f"  - {path}")
    if report.ok:
        print("")
        print("Scope OK: all changed paths match the release-candidate boundary.")


def _print_stage_plan(root: Path, report: ScopeReport) -> None:
    print("RELEASE STAGE PLAN")
    print("This script did not stage files. Review before running these commands.")
    print(f"repo: {root}")
    print(f"release-bound changes : {len(report.release_bound)}")
    print(f"local-only changes    : {len(report.local_only)}")
    print(f"unknown changes       : {len(report.unknown)}")
    sections = iter_stage_plan_sections(report.release_bound)
    if not sections:
        print("")
        print("No release-bound changes found.")
        return
    for label, commands in sections:
        print("")
        print(f"# {label}")
        for command in commands:
            print(command)


if __name__ == "__main__":
    raise SystemExit(main())
