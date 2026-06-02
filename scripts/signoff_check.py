#!/usr/bin/env python3
"""Report external sign-offs still needed before marking the goal complete."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE_PLAN_COMMAND = "venv312/bin/python scripts/release_scope.py --stage-plan"
ACCEPTANCE_COMMANDS = (
    "venv312/bin/ouro demo --lang en --seed 1 --content-dir content",
    (
        "env OURO_AGENT_HOME=/private/tmp/ouro_user_acceptance_seed7_20260601 "
        "venv312/bin/ouro --lang en run --mock --seed 7 --no-animation --auto "
        "--no-trace --content-dir content"
    ),
    "venv312/bin/python scripts/completion_audit.py --json",
)


@dataclass(frozen=True)
class SignoffItem:
    key: str
    title: str
    status: str
    evidence: str
    action: str
    details: tuple[str, ...] = ()

    @property
    def ready(self) -> bool:
        return self.status == "READY"

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "title": self.title,
            "status": self.status,
            "ready": self.ready,
            "evidence": self.evidence,
            "action": self.action,
            "details": list(self.details),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Show release sign-off items that require human or external evidence."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return nonzero while any sign-off item is still pending.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write a machine-readable JSON report.",
    )
    args = parser.parse_args(argv)

    items = _signoff_items()
    pending = [item for item in items if not item.ready]

    if args.json:
        json.dump(
            {
                "root": str(ROOT),
                "pending_count": len(pending),
                "total": len(items),
                "all_ready": not pending,
                "items": [item.to_dict() for item in items],
            },
            sys.stdout,
            indent=2,
            ensure_ascii=False,
        )
        print()
        return 3 if args.strict and pending else 0

    print("OURO RELEASE SIGN-OFF")
    print(f"repo: {ROOT}")
    print("")
    for item in items:
        print(f"[{item.status}] {item.key}: {item.title}")
        print(f"  evidence : {item.evidence}")
        print(f"  action   : {item.action}")
        for detail in item.details:
            print(f"  detail   : {detail}")
    print("")
    if pending:
        print(f"Pending sign-offs: {len(pending)}/{len(items)}")
        return 3 if args.strict else 0
    print("All sign-offs ready.")
    return 0


def _signoff_items(root: Path = ROOT) -> tuple[SignoffItem, ...]:
    return (
        _satisfaction_item(root),
        _license_item(root),
        _live_provider_item(root),
        _git_boundary_item(root),
    )


def _satisfaction_item(root: Path) -> SignoffItem:
    marker = Path("docs/engineering/USER_ACCEPTANCE_20260601.md")
    if _marker_file_has(root, marker, "SIGN-OFF: accepted"):
        return SignoffItem(
            key="satisfaction",
            title="User confirms the game meets the requested experience bar",
            status="READY",
            evidence=f"{marker} contains SIGN-OFF: accepted",
            action="No action required.",
        )
    return SignoffItem(
        key="satisfaction",
        title="User confirms the game meets the requested experience bar",
        status="PENDING",
        evidence=(
            "docs/product/25_人工试玩记录_20260601.md records agent playtest only; "
            f"{marker} does not contain SIGN-OFF: accepted"
        ),
        action=f"User plays or explicitly accepts the current build, then update {marker}.",
        details=tuple(f"acceptance command: {command}" for command in ACCEPTANCE_COMMANDS),
    )


def _license_item(root: Path) -> SignoffItem:
    marker = Path("docs/engineering/LICENSE_DECISION_20260601.md")
    project_license = _project_license(root)
    readme = _read_text(root / "README.md")
    readme_zh = _read_text(root / "README.zh.md")
    pending_sources = []

    if _contains_pending_license(project_license):
        pending_sources.append(f"pyproject.toml license={project_license!r}")
    if _contains_pending_license(readme):
        pending_sources.append("README.md contains a pending license statement")
    if _contains_pending_license(readme_zh):
        pending_sources.append("README.zh.md contains a pending license statement")

    has_license_file = (root / "LICENSE").is_file()
    policy_ready = _has_private_distribution_policy(readme) or _has_private_distribution_policy(
        readme_zh
    )

    if pending_sources:
        return SignoffItem(
            key="license",
            title="Release license or private distribution policy is selected",
            status="PENDING",
            evidence="; ".join(pending_sources),
            action=f"Choose a license, or document private/internal distribution policy, then update {marker}.",
            details=(f"{marker} is guidance only until release metadata is updated",),
        )

    if has_license_file or policy_ready:
        evidence = "LICENSE file exists" if has_license_file else "README documents private/internal distribution policy"
        return SignoffItem(
            key="license",
            title="Release license or private distribution policy is selected",
            status="READY",
            evidence=evidence,
            action="No action required.",
            details=(f"pyproject.toml license={project_license!r}",),
        )

    return SignoffItem(
        key="license",
        title="Release license or private distribution policy is selected",
        status="PENDING",
        evidence="No LICENSE file or private/internal distribution policy was found",
        action=f"Choose a license, or document private/internal distribution policy, then update {marker}.",
        details=(
            f"pyproject.toml license={project_license!r}",
            f"{marker} is guidance only until release metadata is updated",
        ),
    )


def _live_provider_item(root: Path) -> SignoffItem:
    marker = Path("docs/engineering/PROVIDER_LIVE_SMOKE_20260601.md")
    if _marker_file_has(root, marker, "SIGN-OFF: passed"):
        return SignoffItem(
            key="live-provider",
            title="Optional real-provider live smoke is run with user-provided env",
            status="READY",
            evidence=f"{marker} contains SIGN-OFF: passed",
            action="No action required.",
        )
    return SignoffItem(
        key="live-provider",
        title="Optional real-provider live smoke is run with user-provided env",
        status="PENDING",
        evidence=(
            "scripts/provider_smoke.py can preflight safely; "
            f"{marker} does not contain SIGN-OFF: passed"
        ),
        action=(
            "Run scripts/provider_smoke.py --live after setting the configured "
            f"env var, then update {marker}."
        ),
    )


def _git_boundary_item(root: Path) -> SignoffItem:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return SignoffItem(
            key="git-boundary",
            title="Release changes are intentionally staged and committed",
            status="PENDING",
            evidence=f"git status failed: {result.stderr.strip() or result.returncode}",
            action="Run git status from the repository root and resolve the release boundary.",
        )

    changed = [line for line in result.stdout.splitlines() if line.strip()]
    if not changed:
        return SignoffItem(
            key="git-boundary",
            title="Release changes are intentionally staged and committed",
            status="READY",
            evidence="git status --short reports a clean working tree",
            action="No action required.",
        )

    shown = tuple(changed[:8])
    more = (f"... {len(changed) - len(shown)} more paths",) if len(changed) > len(shown) else ()
    scope_details = _release_scope_details(root)
    return SignoffItem(
        key="git-boundary",
        title="Release changes are intentionally staged and committed",
        status="PENDING",
        evidence=f"git status --short reports {len(changed)} changed path(s)",
        action=f"Run {STAGE_PLAN_COMMAND}, review, stage release files, commit, then tag.",
        details=scope_details + shown + more,
    )


def _release_scope_details(root: Path) -> tuple[str, ...]:
    script = root / "scripts/release_scope.py"
    if not script.is_file():
        return (
            "scope boundary: scripts/release_scope.py not found",
            f"staging plan: {STAGE_PLAN_COMMAND}",
        )

    result = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if not result.stdout.strip():
        detail = result.stderr.strip() or f"exit {result.returncode}"
        return (
            f"scope boundary: unavailable ({detail})",
            f"staging plan: {STAGE_PLAN_COMMAND}",
        )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        return (
            "scope boundary: unavailable (invalid JSON from release_scope.py)",
            f"staging plan: {STAGE_PLAN_COMMAND}",
        )
    return (
        "scope boundary: "
        f"release-bound={report.get('release_bound_count', '?')}, "
        f"local-only={report.get('local_only_count', '?')}, "
        f"unknown={report.get('unknown_count', '?')}",
        f"staging plan: {STAGE_PLAN_COMMAND}",
    )


def _project_license(root: Path) -> str:
    try:
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return ""
    license_value = data.get("project", {}).get("license", "")
    if isinstance(license_value, dict):
        return str(license_value.get("text", "") or license_value.get("file", ""))
    return str(license_value)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _contains_pending_license(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "license is not selected",
            "license selection pending",
            "license pending",
            "unlicensed",
            "tbd",
            "待定",
        )
    )


def _has_private_distribution_policy(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "private distribution",
            "internal distribution",
            "internal-only distribution",
            "not for public distribution",
            "私有发布",
            "内部发布",
        )
    )


def _marker_file_has(root: Path, relative: Path, expected_line: str) -> bool:
    text = _read_text(root / relative)
    return any(line.strip().lower() == expected_line.lower() for line in text.splitlines())


if __name__ == "__main__":
    raise SystemExit(main())
