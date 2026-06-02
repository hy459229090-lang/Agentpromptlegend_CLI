#!/usr/bin/env python3
"""Run the mock-first user acceptance command path without signing off."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AcceptanceStep:
    key: str
    title: str
    command: tuple[str, ...]
    expected_returncodes: tuple[int, ...]
    markers: tuple[str, ...]


@dataclass(frozen=True)
class StepResult:
    step: AcceptanceStep
    returncode: int
    missing_markers: tuple[str, ...]
    summary: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.returncode in self.step.expected_returncodes and not self.missing_markers

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.step.key,
            "title": self.step.title,
            "ok": self.ok,
            "returncode": self.returncode,
            "expected_returncodes": list(self.step.expected_returncodes),
            "missing_markers": list(self.missing_markers),
            "summary": list(self.summary),
            "command": list(self.step.command),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the mock-first user acceptance path. This does not write "
            "SIGN-OFF: accepted."
        )
    )
    parser.add_argument("--json", action="store_true", help="Write a machine-readable report.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned commands without executing them.",
    )
    args = parser.parse_args(argv)

    steps = acceptance_steps(sys.executable)
    if args.dry_run:
        _print_dry_run(steps)
        return 0

    results = _run_steps(steps)
    report = _build_report(results)
    if args.json:
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        _print_report(report)
    return 0 if report["ok"] else 1


def acceptance_steps(python_bin: str) -> tuple[AcceptanceStep, ...]:
    return (
        AcceptanceStep(
            key="guided-demo",
            title="Guided demo",
            command=(
                python_bin,
                "-m",
                "ouro_agent.cli.main",
                "--lang",
                "en",
                "demo",
                "--seed",
                "1",
                "--content-dir",
                "content",
            ),
            expected_returncodes=(0,),
            markers=(
                "OURO DEMO :: FIRST ECHO",
                "STEP 5: Continue from here",
                "BATTLE COMPLETE",
                "CODEX :: MONSTER ARCHIVE",
            ),
        ),
        AcceptanceStep(
            key="fixed-seed-run",
            title="Fixed seed full run",
            command=(
                python_bin,
                "-m",
                "ouro_agent.cli.main",
                "--lang",
                "en",
                "run",
                "--mock",
                "--seed",
                "7",
                "--no-animation",
                "--auto",
                "--no-trace",
                "--content-dir",
                "content",
            ),
            expected_returncodes=(0,),
            markers=("YOU DIED", "Run Summary", "Run Archive:", "Death History:"),
        ),
        AcceptanceStep(
            key="completion-audit",
            title="Completion audit",
            command=(
                python_bin,
                str(ROOT / "scripts/completion_audit.py"),
                "--json",
                "--skip-release-check",
            ),
            expected_returncodes=(3,),
            markers=(
                '"goal_complete_ready": false',
                '"pending_items"',
                '"satisfaction"',
                '"git-boundary"',
            ),
        ),
    )


def _run_steps(steps: tuple[AcceptanceStep, ...]) -> tuple[StepResult, ...]:
    with tempfile.TemporaryDirectory(prefix="ouro_acceptance_check_") as home:
        env = os.environ.copy()
        env["OURO_AGENT_HOME"] = home
        env["PYTHONIOENCODING"] = "utf-8"
        results = []
        for step in steps:
            completed = subprocess.run(
                step.command,
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            missing = tuple(marker for marker in step.markers if marker not in completed.stdout)
            results.append(
                StepResult(
                    step=step,
                    returncode=completed.returncode,
                    missing_markers=missing,
                    summary=_summarize_output(completed.stdout, step.markers),
                )
            )
        return tuple(results)


def _build_report(results: tuple[StepResult, ...]) -> dict[str, Any]:
    return {
        "ok": all(result.ok for result in results),
        "marks_signoff": False,
        "signoff_file": "docs/engineering/USER_ACCEPTANCE_20260601.md",
        "steps": [result.to_dict() for result in results],
    }


def _summarize_output(output: str, markers: tuple[str, ...]) -> tuple[str, ...]:
    summary: list[str] = []
    interesting = (
        *markers,
        "Result :",
        "Floor reached:",
        "Battles Won:",
        "Battles Lost:",
        "goal_complete_ready",
        "pending_count",
    )
    for line in output.splitlines():
        if any(marker in line for marker in interesting):
            stripped = line.strip()
            if stripped and stripped not in summary:
                summary.append(stripped)
    return tuple(summary[:16])


def _print_dry_run(steps: tuple[AcceptanceStep, ...]) -> None:
    print("OURO USER ACCEPTANCE CHECK - DRY RUN")
    print("This script does not write SIGN-OFF: accepted.")
    for step in steps:
        print(f"[DRY-RUN] {step.key}: {_format_command(step.command)}")


def _print_report(report: dict[str, Any]) -> None:
    print("OURO USER ACCEPTANCE CHECK")
    print("This script does not write SIGN-OFF: accepted.")
    for step in report["steps"]:
        status = "PASS" if step["ok"] else "FAIL"
        print(f"[{status}] {step['key']}: {step['title']} (returncode={step['returncode']})")
        for line in step["summary"]:
            print(f"  observed: {line}")
        for marker in step["missing_markers"]:
            print(f"  missing : {marker}")
    print("")
    print(f"Acceptance commands ready: {'yes' if report['ok'] else 'no'}")
    print("User satisfaction sign-off remains manual.")


def _format_command(command: tuple[str, ...]) -> str:
    return " ".join(shlex.quote(part) for part in command)


if __name__ == "__main__":
    raise SystemExit(main())
