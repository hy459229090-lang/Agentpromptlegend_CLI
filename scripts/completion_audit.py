#!/usr/bin/env python3
"""Aggregate final-goal readiness without replacing human sign-offs."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AuditCommand:
    key: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class AuditResult:
    key: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize whether the Ouro Agent goal is ready to mark complete."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write a machine-readable completion audit report.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the audit commands without executing them.",
    )
    parser.add_argument(
        "--skip-release-check",
        action="store_true",
        help="Skip the slower full release_check.py run; useful after it has just passed.",
    )
    args = parser.parse_args(argv)

    commands = _audit_commands(skip_release_check=args.skip_release_check)
    if args.dry_run:
        _print_dry_run(commands)
        return 0

    results = [_run(command) for command in commands]
    report = _build_report(results, skipped_release_check=args.skip_release_check)
    if args.json:
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        _print_report(report)
    return 0 if report["goal_complete_ready"] else 3


def _audit_commands(*, skip_release_check: bool) -> tuple[AuditCommand, ...]:
    python_bin = sys.executable
    commands: list[AuditCommand] = []
    if not skip_release_check:
        commands.append(
            AuditCommand(
                "release",
                (python_bin, str(ROOT / "scripts/release_check.py")),
            )
        )
    commands.extend(
        (
            AuditCommand(
                "asset-status-strict",
                (
                    python_bin,
                    str(ROOT / "scripts/asset_status_report.py"),
                    "--content-dir",
                    "content",
                    "--require-all-candidates",
                    "--require-all-cut-metadata",
                    "--require-all-qa-passed",
                    "--require-all-runtime",
                ),
            ),
            AuditCommand(
                "asset-qa",
                (
                    python_bin,
                    str(ROOT / "scripts/asset_qa_check.py"),
                    "--content-dir",
                    "content",
                ),
            ),
            AuditCommand(
                "asset-manifest",
                (
                    python_bin,
                    str(ROOT / "scripts/asset_manifest_check.py"),
                    "--content-dir",
                    "content",
                ),
            ),
            AuditCommand(
                "scope",
                (python_bin, str(ROOT / "scripts/release_scope.py"), "--json"),
            ),
            AuditCommand(
                "signoff",
                (python_bin, str(ROOT / "scripts/signoff_check.py"), "--json"),
            ),
        )
    )
    return tuple(commands)


def _run(command: AuditCommand) -> AuditResult:
    result = subprocess.run(
        command.command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return AuditResult(
        key=command.key,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _build_report(
    results: list[AuditResult],
    *,
    skipped_release_check: bool,
) -> dict[str, Any]:
    by_key = {result.key: result for result in results}
    release = by_key.get("release")
    asset_status = by_key.get("asset-status-strict")
    asset_qa = by_key.get("asset-qa")
    asset_manifest = by_key.get("asset-manifest")
    scope = by_key.get("scope")
    signoff = by_key.get("signoff")
    scope_report = _loads_object(scope.stdout if scope else "")
    signoff_report = _loads_object(signoff.stdout if signoff else "")

    release_ready = True if skipped_release_check else bool(release and release.ok)
    asset_results = [asset_status, asset_qa, asset_manifest]
    assets_ready = all(result is not None and result.ok for result in asset_results)
    scope_ready = bool(scope and scope.ok and scope_report.get("ok") is True)
    signoff_ready = bool(signoff and signoff.ok and signoff_report.get("all_ready") is True)
    pending_signoffs = [
        str(item.get("key", ""))
        for item in signoff_report.get("items", [])
        if isinstance(item, dict) and not item.get("ready", False)
    ]
    pending_items = [
        _pending_signoff_item(item)
        for item in signoff_report.get("items", [])
        if isinstance(item, dict) and not item.get("ready", False)
    ]

    return {
        "root": str(ROOT),
        "goal_complete_ready": release_ready and assets_ready and scope_ready and signoff_ready,
        "release_check": {
            "skipped": skipped_release_check,
            "ready": release_ready,
            "returncode": None if release is None else release.returncode,
        },
        "asset_hard_gates": {
            "ready": assets_ready,
            "commands": [
                _asset_gate_result("asset-status-strict", asset_status, "asset pipeline strict gate: OK"),
                _asset_gate_result("asset-qa", asset_qa, "asset QA records: OK"),
                _asset_gate_result("asset-manifest", asset_manifest, "asset manifest: OK"),
            ],
        },
        "scope": {
            "ready": scope_ready,
            "returncode": None if scope is None else scope.returncode,
            "release_bound_count": scope_report.get("release_bound_count"),
            "local_only_count": scope_report.get("local_only_count"),
            "unknown_count": scope_report.get("unknown_count"),
        },
        "signoff": {
            "ready": signoff_ready,
            "returncode": None if signoff is None else signoff.returncode,
            "pending_count": signoff_report.get("pending_count"),
            "pending_keys": pending_signoffs,
            "pending_items": pending_items,
        },
        "commands": [
            {
                "key": result.key,
                "returncode": result.returncode,
            }
            for result in results
        ],
    }


def _asset_gate_result(
    key: str,
    result: AuditResult | None,
    marker: str,
) -> dict[str, Any]:
    stdout = "" if result is None else result.stdout
    return {
        "key": key,
        "ready": bool(result and result.ok and marker in stdout),
        "returncode": None if result is None else result.returncode,
        "marker": marker,
    }


def _pending_signoff_item(item: dict[str, Any]) -> dict[str, Any]:
    details = item.get("details", [])
    if not isinstance(details, list):
        details = []
    return {
        "key": str(item.get("key", "")),
        "title": str(item.get("title", "")),
        "evidence": str(item.get("evidence", "")),
        "action": str(item.get("action", "")),
        "details": [str(detail) for detail in details],
    }


def _loads_object(text: str) -> dict[str, Any]:
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return raw if isinstance(raw, dict) else {}


def _print_dry_run(commands: tuple[AuditCommand, ...]) -> None:
    print("OURO COMPLETION AUDIT - DRY RUN")
    for command in commands:
        print(f"[DRY-RUN] {command.key}: {' '.join(command.command)}")


def _print_report(report: dict[str, Any]) -> None:
    print("OURO COMPLETION AUDIT")
    print(f"repo: {report['root']}")
    release = report["release_check"]
    assets = report["asset_hard_gates"]
    scope = report["scope"]
    signoff = report["signoff"]
    release_label = "SKIPPED" if release["skipped"] else _status_word(bool(release["ready"]))
    print(f"release gates : {release_label}")
    print(f"asset gates   : {_status_word(bool(assets['ready']))}")
    print(
        "scope boundary: "
        f"{_status_word(bool(scope['ready']))} "
        f"(release-bound={scope['release_bound_count']}, "
        f"local-only={scope['local_only_count']}, unknown={scope['unknown_count']})"
    )
    print(
        "sign-offs     : "
        f"{_status_word(bool(signoff['ready']))} "
        f"(pending={signoff['pending_count']}, keys={', '.join(signoff['pending_keys']) or '-'})"
    )
    print("")
    if report["goal_complete_ready"]:
        print("Goal complete readiness: READY")
    else:
        print("Goal complete readiness: NOT READY")
        print(
            "Do not mark the goal complete until release gates, asset hard gates, "
            "scope, and all sign-offs are ready."
        )
        pending_items = signoff.get("pending_items", [])
        if pending_items:
            print("")
            print("Required sign-offs:")
            for item in pending_items:
                print(f"- {item['key']}: {item['action']}")


def _status_word(ready: bool) -> str:
    return "READY" if ready else "PENDING"


if __name__ == "__main__":
    raise SystemExit(main())
