#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_SCAN_ROOTS = (
    "README.md",
    "README.zh.md",
    "CHANGELOG.md",
    "pyproject.toml",
    "LICENSE",
    "AGENTS.md",
    "CLAUDE.md",
    "src",
    "content",
    "tests",
    "examples",
    "docs",
    "scripts",
)
IGNORED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".obsidian",
    "__pycache__",
    "build",
    "dist",
    "venv",
    "venv312",
}
TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".css",
    ".csv",
    ".example",
    ".html",
    ".ini",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SECRET_PATTERNS = (
    (
        "provider key",
        re.compile(r"\bsk-(?!\.\.\.)[A-Za-z0-9][A-Za-z0-9_-]{16,}\b"),
    ),
    (
        "bearer token",
        re.compile(r"(?i)\bBearer\s+(?!token\b)[A-Za-z0-9._~+/=-]{24,}\b"),
    ),
    (
        "secret assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token)\s*[:=]\s*['\"]?"
            r"(?!your\b|example\b|placeholder\b|none\b|null\b)"
            r"[A-Za-z0-9_./+=-]{24,}"
        ),
    ),
)


@dataclass(frozen=True)
class Gate:
    name: str
    description: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class PrivacyFinding:
    path: Path
    line_number: int
    label: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Ouro Agent release-candidate gates from repo root."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the gates without executing them.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip the pytest gate.",
    )
    parser.add_argument(
        "--skip-content",
        action="store_true",
        help="Skip the content validation gate.",
    )
    parser.add_argument(
        "--skip-doctor",
        action="store_true",
        help="Skip the isolated doctor gate.",
    )
    parser.add_argument(
        "--skip-version",
        action="store_true",
        help="Skip the release version consistency gate.",
    )
    parser.add_argument(
        "--skip-evidence",
        action="store_true",
        help="Skip the evidence count consistency gate.",
    )
    parser.add_argument(
        "--skip-scope",
        action="store_true",
        help="Skip the release-boundary scope gate.",
    )
    parser.add_argument(
        "--skip-acceptance",
        action="store_true",
        help="Skip the mock-first user acceptance path gate.",
    )
    parser.add_argument(
        "--skip-asset-status",
        action="store_true",
        help="Skip the terminal graphics asset status report gate.",
    )
    parser.add_argument(
        "--skip-combat-stage",
        action="store_true",
        help="Skip the terminal combat-stage graphics evidence gate.",
    )
    parser.add_argument(
        "--skip-timeline-coverage",
        action="store_true",
        help="Skip the terminal graphics skill timeline coverage gate.",
    )
    parser.add_argument(
        "--install-smoke",
        action="store_true",
        help="Also run the slower clean virtualenv install smoke gate.",
    )
    parser.add_argument(
        "--skip-diff",
        action="store_true",
        help="Skip the git diff whitespace gate.",
    )
    parser.add_argument(
        "--skip-privacy",
        action="store_true",
        help="Skip the release privacy scan gate.",
    )
    parser.add_argument(
        "--privacy-scan-only",
        action="store_true",
        help="Only scan release-bound text files for likely plaintext secrets.",
    )
    parser.add_argument(
        "--doctor-only",
        action="store_true",
        help="Only run doctor in an isolated temporary OURO_AGENT_HOME.",
    )
    parser.add_argument(
        "--version-only",
        action="store_true",
        help="Only verify pyproject, package, changelog, and handoff versions match.",
    )
    parser.add_argument(
        "--evidence-only",
        action="store_true",
        help="Only verify pytest/privacy evidence counts match release docs.",
    )
    parser.add_argument(
        "--scope-only",
        action="store_true",
        help="Only verify changed paths match the release-candidate boundary.",
    )
    parser.add_argument(
        "--acceptance-only",
        action="store_true",
        help="Only run the mock-first user acceptance path check.",
    )
    parser.add_argument(
        "--asset-status-only",
        action="store_true",
        help="Only report terminal graphics asset pipeline readiness.",
    )
    parser.add_argument(
        "--combat-stage-only",
        action="store_true",
        help="Only verify terminal combat-stage graphics evidence files.",
    )
    parser.add_argument(
        "--timeline-coverage-only",
        action="store_true",
        help="Only verify terminal graphics timeline coverage for all MVP skills.",
    )
    parser.add_argument(
        "--asset-status-strict",
        action="store_true",
        help=(
            "Make the asset status gate require all manifest assets to have "
            "candidates, cut metadata, QA pass records, and runtime files."
        ),
    )
    parser.add_argument(
        "--install-smoke-only",
        action="store_true",
        help="Only create a clean venv, install the package, and smoke the installed CLI.",
    )
    args = parser.parse_args(argv)

    if args.privacy_scan_only:
        return _run_privacy_scan()
    if args.doctor_only:
        return _run_isolated_doctor()
    if args.version_only:
        return _run_version_check()
    if args.evidence_only:
        return _run_evidence_count_check()
    if args.scope_only:
        return subprocess.run(
            (sys.executable, str(ROOT / "scripts/release_scope.py")),
            cwd=ROOT,
            check=False,
        ).returncode
    if args.acceptance_only:
        python_bin = os.environ.get("OURO_PYTHON", sys.executable)
        return subprocess.run(
            (python_bin, str(ROOT / "scripts/acceptance_check.py")),
            cwd=ROOT,
            env=_gate_environment(),
            check=False,
        ).returncode
    if args.asset_status_only:
        return _run_asset_status_check(strict=args.asset_status_strict)
    if args.combat_stage_only:
        return _run_combat_stage_evidence_check()
    if args.timeline_coverage_only:
        return _run_timeline_coverage_check()
    if args.install_smoke_only:
        return _run_install_smoke()

    gates = _build_gates(args)
    if not gates:
        print("No release gates selected.")
        return 2

    print("Ouro Agent release check", flush=True)
    print(f"repo: {ROOT}", flush=True)
    print("", flush=True)

    if args.dry_run:
        for gate in gates:
            print(f"[DRY-RUN] {gate.name}: {_format_command(gate.command)}")
        return 0

    env = _gate_environment()
    for gate in gates:
        print(f"==> {gate.name}: {gate.description}", flush=True)
        print(f"$ {_format_command(gate.command)}", flush=True)
        result = subprocess.run(gate.command, cwd=ROOT, env=env, check=False)
        if result.returncode != 0:
            print(f"FAIL: {gate.name} exited with {result.returncode}")
            return result.returncode
        print(f"PASS: {gate.name}", flush=True)
        print("", flush=True)

    print("All release gates passed.")
    return 0


def _build_gates(args: argparse.Namespace) -> list[Gate]:
    python_bin = os.environ.get("OURO_PYTHON", sys.executable)
    gates: list[Gate] = []

    if not args.skip_tests:
        gates.append(
            Gate(
                name="pytest",
                description="unit, integration, visual, archive, docs, and matrix tests",
                command=(python_bin, "-m", "pytest"),
            )
        )
    if not args.skip_content:
        gates.append(
            Gate(
                name="validate-content",
                description="content schema and reference validation",
                command=(python_bin, "-m", "ouro_agent.cli.main", "validate-content"),
            )
        )
    if not args.skip_doctor:
        gates.append(
            Gate(
                name="doctor",
                description="isolated install/config/content readiness check",
                command=(python_bin, str(ROOT / "scripts/release_check.py"), "--doctor-only"),
            )
        )
    if not args.skip_version:
        gates.append(
            Gate(
                name="version-consistency",
                description="pyproject, package, changelog, and handoff versions match",
                command=(python_bin, str(ROOT / "scripts/release_check.py"), "--version-only"),
            )
        )
    if not args.skip_evidence:
        gates.append(
            Gate(
                name="evidence-count",
                description="pytest and privacy evidence counts match release docs",
                command=(python_bin, str(ROOT / "scripts/release_check.py"), "--evidence-only"),
            )
        )
    if not args.skip_scope:
        gates.append(
            Gate(
                name="scope-boundary",
                description="git status paths match the release-candidate boundary",
                command=(python_bin, str(ROOT / "scripts/release_check.py"), "--scope-only"),
            )
        )
    if not args.skip_acceptance:
        gates.append(
            Gate(
                name="acceptance-path",
                description="mock-first user acceptance commands still run",
                command=(
                    python_bin,
                    str(ROOT / "scripts/release_check.py"),
                    "--acceptance-only",
                ),
            )
        )
    if not args.skip_asset_status:
        command = [python_bin, str(ROOT / "scripts/release_check.py"), "--asset-status-only"]
        if args.asset_status_strict:
            command.append("--asset-status-strict")
        gates.append(
            Gate(
                name="asset-status",
                description=(
                    "terminal graphics asset pipeline status"
                    + (" strict gate" if args.asset_status_strict else " report")
                ),
                command=tuple(command),
            )
        )
    if not args.skip_combat_stage:
        gates.append(
            Gate(
                name="combat-stage-evidence",
                description="terminal graphics bitmap/cell stage evidence parity",
                command=(
                    python_bin,
                    str(ROOT / "scripts/release_check.py"),
                    "--combat-stage-only",
                ),
            )
        )
    if not args.skip_timeline_coverage:
        gates.append(
            Gate(
                name="timeline-coverage",
                description="terminal graphics timeline coverage for every MVP skill",
                command=(
                    python_bin,
                    str(ROOT / "scripts/release_check.py"),
                    "--timeline-coverage-only",
                ),
            )
        )
    if not args.skip_diff:
        gates.append(
            Gate(
                name="diff-check",
                description="git whitespace check for the release diff",
                command=("git", "diff", "--check"),
            )
        )
    if args.install_smoke:
        gates.append(
            Gate(
                name="install-smoke",
                description="clean venv package install and installed CLI smoke",
                command=(python_bin, str(ROOT / "scripts/release_check.py"), "--install-smoke-only"),
            )
        )
    if not args.skip_privacy:
        gates.append(
            Gate(
                name="privacy-scan",
                description="release-bound text files contain no likely secrets",
                command=(python_bin, str(ROOT / "scripts/release_check.py"), "--privacy-scan-only"),
            )
        )

    return gates


def _run_asset_status_check(*, strict: bool = False) -> int:
    python_bin = os.environ.get("OURO_PYTHON", sys.executable)
    command = [
        python_bin,
        str(ROOT / "scripts/asset_status_report.py"),
        "--content-dir",
        "content",
    ]
    if strict:
        command.extend(
            [
                "--require-all-candidates",
                "--require-all-cut-metadata",
                "--require-all-qa-passed",
                "--require-all-runtime",
            ]
        )
    return subprocess.run(command, cwd=ROOT, env=_gate_environment(), check=False).returncode


def _run_combat_stage_evidence_check() -> int:
    python_bin = os.environ.get("OURO_PYTHON", sys.executable)
    with tempfile.TemporaryDirectory(prefix="ouro_release_combat_stage_") as output_dir:
        command = (
            python_bin,
            str(ROOT / "scripts/record_combat_stage.py"),
            "--content-dir",
            "content",
            "--output-dir",
            output_dir,
            "--width",
            "96",
            "--max-frames",
            "6",
        )
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=_gate_environment(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.returncode != 0:
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)
            return result.returncode
        issues = _combat_stage_evidence_issues(Path(output_dir))
        if issues:
            print("Combat stage evidence failed:")
            for issue in issues:
                print(f"  - {issue}")
            return 2
    print("Combat stage evidence OK: bitmap, Unicode, and ASCII filmstrips verified.")
    return 0


def _run_timeline_coverage_check() -> int:
    python_bin = os.environ.get("OURO_PYTHON", sys.executable)
    command = (
        python_bin,
        str(ROOT / "scripts/timeline_coverage_report.py"),
        "--content-dir",
        "content",
        "--require-all-skills",
    )
    return subprocess.run(command, cwd=ROOT, env=_gate_environment(), check=False).returncode


def _combat_stage_evidence_issues(output_dir: Path) -> list[str]:
    required_markers = {
        "summary.txt": (
            "COMBAT STAGE EVIDENCE",
            "bitmap_filmstrip_iterm2: hex_seal_bitmap_iterm2_filmstrip.txt",
            "bitmap_filmstrip_kitty: hex_seal_bitmap_kitty_filmstrip.txt",
            "bitmap_filmstrip_sixel: hex_seal_bitmap_sixel_filmstrip.txt",
            "Runtime image generation: disabled",
        ),
        "hex_seal_bitmap_iterm2_filmstrip.txt": (
            "BITMAP FRAME 06/12 hit_stop 90ms",
            "[BITMAP iterm2 role=effect",
            "sha256=",
            "DAMAGE -16 HP | HUD impact | HIT STOP",
        ),
        "hex_seal_bitmap_kitty_filmstrip.txt": (
            "BITMAP FRAME 06/12 hit_stop 90ms",
            "[BITMAP kitty role=enemy",
            "sha256=",
            "DAMAGE -16 HP | HUD impact | HIT STOP",
        ),
        "hex_seal_bitmap_sixel_filmstrip.txt": (
            "BITMAP FRAME 06/12 hit_stop 90ms",
            "[BITMAP sixel role=hero",
            "sha256=",
            "DAMAGE -16 HP | HUD impact | HIT STOP",
        ),
        "hex_seal_unicode_filmstrip.txt": (
            "FRAME 06/12 hit_stop 90ms",
            "-16 HP",
            "HIT STOP",
        ),
        "hex_seal_ascii_filmstrip.txt": (
            "FRAME 06/12 hit_stop 90ms",
            "DAMAGE -16 HP",
            "HIT STOP",
        ),
    }
    issues: list[str] = []
    for filename, markers in required_markers.items():
        path = output_dir / filename
        if not path.is_file():
            issues.append(f"missing evidence file: {filename}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                issues.append(f"{filename} missing {marker!r}")
        if filename.endswith("_ascii_filmstrip.txt") and not text.isascii():
            issues.append(f"{filename} must be ASCII-safe")
    return issues


def _run_isolated_doctor() -> int:
    python_bin = os.environ.get("OURO_PYTHON", sys.executable)
    with tempfile.TemporaryDirectory(prefix="ouro_release_check_home_") as home:
        env = _gate_environment()
        env["OURO_AGENT_HOME"] = home
        command = (
            python_bin,
            "-m",
            "ouro_agent.cli.main",
            "--lang",
            "en",
            "doctor",
            "--content-dir",
            "content",
        )
        return subprocess.run(command, cwd=ROOT, env=env, check=False).returncode


def _run_version_check() -> int:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(pyproject["project"]["version"])
    tag = f"v{version}"
    issues: list[str] = []

    init_text = (ROOT / "src/ouro_agent/__init__.py").read_text(encoding="utf-8")
    init_match = re.search(r'^__version__\s*=\s*"([^"]+)"', init_text, re.MULTILINE)
    init_version = init_match.group(1) if init_match else ""
    if init_version != version:
        issues.append(f"src/ouro_agent/__init__.py __version__={init_version!r}")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {version} - " not in changelog:
        issues.append(f"CHANGELOG.md missing release heading for {version}")

    handoff = (ROOT / "docs/engineering/RELEASE_HANDOFF_20260601.md").read_text(
        encoding="utf-8"
    )
    expected_handoff_markers = (
        f"# Release Handoff - {tag}",
        f"- Version: `{version}`",
        f"- Recommended tag: `{tag}`",
        f"@{tag}",
        f"git tag -a {tag}",
    )
    for marker in expected_handoff_markers:
        if marker not in handoff:
            issues.append(f"release handoff missing {marker!r}")

    if issues:
        print("Version consistency failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print(f"Version consistency OK: {version} / {tag}")
    return 0


def _run_evidence_count_check() -> int:
    python_bin = os.environ.get("OURO_PYTHON", sys.executable)
    collect = subprocess.run(
        (python_bin, "-m", "pytest", "--collect-only", "-q"),
        cwd=ROOT,
        env=_gate_environment(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if collect.returncode != 0:
        print(collect.stdout)
        print(collect.stderr)
        return collect.returncode

    test_count = _parse_pytest_collect_count(collect.stdout)
    privacy_count = len(_iter_privacy_scan_files())
    issues: list[str] = []
    if test_count <= 0:
        issues.append("pytest collect-only did not report any tests")

    expected_markers = {
        "README.md": (
            f"tests-{test_count}%20passing",
            f"`{test_count} tests passing`",
        ),
        "README.zh.md": (
            f"tests-{test_count}%20passing",
            f"`{test_count} 测试通过`",
        ),
        "CHANGELOG.md": (f"`{test_count} passed`",),
        "docs/engineering/RELEASE_HANDOFF_20260601.md": (
            f"`{test_count} passed`",
        ),
        "docs/product/23_QA证据与固定Seed试玩记录_20260601.md": (
            f"`{test_count} passed`",
            f"Privacy scan OK: {privacy_count} release-bound text files checked.",
        ),
        "docs/product/24_最终产品验收审计_20260601.md": (
            f"`{test_count} passed`",
            f"Privacy scan OK: {privacy_count} release-bound text files checked.",
        ),
        "docs/product/06_需求追踪矩阵_20260503.md": (
            f"`{test_count} passed`",
            f"Privacy scan OK: {privacy_count} release-bound text files checked.",
        ),
    }

    for relative, markers in expected_markers.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                issues.append(f"{relative} missing {marker!r}")

    if issues:
        print("Evidence count consistency failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print(
        "Evidence counts OK: "
        f"{test_count} tests collected; {privacy_count} release-bound text files."
    )
    return 0


def _parse_pytest_collect_count(output: str) -> int:
    count = 0
    for line in output.splitlines():
        match = re.search(r":\s+(\d+)\s*$", line)
        if match:
            count += int(match.group(1))
    return count


def _run_install_smoke() -> int:
    host_python = os.environ.get("OURO_PYTHON", sys.executable)
    with tempfile.TemporaryDirectory(prefix="ouro_install_smoke_") as tmp:
        tmp_path = Path(tmp)
        venv_dir = tmp_path / "venv"
        home_dir = tmp_path / "home"
        run_cwd = tmp_path / "outside-source"
        run_cwd.mkdir()
        home_dir.mkdir()

        rc = _run_step((host_python, "-m", "venv", str(venv_dir)), cwd=ROOT)
        if rc != 0:
            return rc

        venv_python = _venv_executable(venv_dir, "python")
        ouro_bin = _venv_executable(venv_dir, "ouro")

        install_env = os.environ.copy()
        install_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        rc = _run_step(
            (str(venv_python), "-m", "pip", "install", "-q", "."),
            cwd=ROOT,
            env=install_env,
        )
        if rc != 0:
            return rc

        smoke_env = os.environ.copy()
        smoke_env.pop("PYTHONPATH", None)
        smoke_env["OURO_AGENT_HOME"] = str(home_dir)
        smoke_env["PYTHONIOENCODING"] = "utf-8"

        rc = _run_step((str(ouro_bin), "--version"), cwd=run_cwd, env=smoke_env)
        if rc != 0:
            return rc

        rc = _run_step((str(ouro_bin), "--lang", "en", "doctor"), cwd=run_cwd, env=smoke_env)
        if rc != 0:
            return rc

        try_demo = _run_capture(
            (
                str(ouro_bin),
                "--lang",
                "en",
                "try",
                "--seed",
                "1",
            ),
            cwd=run_cwd,
            env=smoke_env,
        )
        if try_demo.returncode != 0:
            print(try_demo.stdout)
            return try_demo.returncode
        _print_smoke_lines(try_demo.stdout)
        if "OURO DEMO :: FIRST ECHO" not in try_demo.stdout:
            print("install smoke failed: missing guided try header")
            return 1
        if "BATTLE COMPLETE" not in try_demo.stdout:
            print("install smoke failed: guided try did not finish battle")
            return 1
        if "CODEX :: MONSTER ARCHIVE" not in try_demo.stdout:
            print("install smoke failed: guided try did not read back Codex")
            return 1
        if "Next commands" not in try_demo.stdout or "ouro try --seed 1" not in try_demo.stdout:
            print("install smoke failed: guided try did not print try next command")
            return 1
        if "ouro run --mock" not in try_demo.stdout:
            print("install smoke failed: guided try did not print full-run next command")
            return 1

        play = _run_capture(
            (
                str(ouro_bin),
                "--lang",
                "en",
                "play",
                "--mock",
                "--seed",
                "1",
                "--no-animation",
                "--no-trace",
            ),
            cwd=run_cwd,
            env=smoke_env,
        )
        if play.returncode != 0:
            print(play.stdout)
            return play.returncode

        _print_smoke_lines(play.stdout)
        if "BATTLE COMPLETE" not in play.stdout:
            print("install smoke failed: missing BATTLE COMPLETE")
            return 1

        codex = _run_capture(
            (
                str(ouro_bin),
                "--lang",
                "en",
                "codex",
            ),
            cwd=run_cwd,
            env=smoke_env,
        )
        if codex.returncode != 0:
            print(codex.stdout)
            return codex.returncode
        _print_smoke_lines(codex.stdout)
        if "CODEX :: MONSTER ARCHIVE" not in codex.stdout:
            print("install smoke failed: missing codex listing")
            return 1
        if "Observed:" not in codex.stdout:
            print("install smoke failed: missing codex observed count")
            return 1
        if not _has_unlocked_codex_entry(codex.stdout):
            print("install smoke failed: codex listing did not include unlocked enemies")
            return 1

        run = _run_capture(
            (
                str(ouro_bin),
                "--lang",
                "en",
                "run",
                "--mock",
                "--auto",
                "--seed",
                "7",
                "--no-animation",
                "--no-trace",
            ),
            cwd=run_cwd,
            env=smoke_env,
        )
        if run.returncode != 0:
            print(run.stdout)
            return run.returncode

        _print_smoke_lines(run.stdout)
        if "Run Summary" not in run.stdout:
            print("install smoke failed: missing Run Summary")
            return 1
        if "Run Archive:" not in run.stdout:
            print("install smoke failed: missing Run Archive")
            return 1

        runs = _run_capture(
            (
                str(ouro_bin),
                "--lang",
                "en",
                "runs",
                "--limit",
                "1",
            ),
            cwd=run_cwd,
            env=smoke_env,
        )
        if runs.returncode != 0:
            print(runs.stdout)
            return runs.returncode
        _print_smoke_lines(runs.stdout)
        if "RUN ARCHIVE :: ALL RUNS" not in runs.stdout:
            print("install smoke failed: missing run archive listing")
            return 1
        if "Seed: 7" not in runs.stdout:
            print("install smoke failed: run archive listing did not include seed 7")
            return 1

        run_report = _run_capture(
            (
                str(ouro_bin),
                "--lang",
                "en",
                "run-report",
            ),
            cwd=run_cwd,
            env=smoke_env,
        )
        if run_report.returncode != 0:
            print(run_report.stdout)
            return run_report.returncode
        _print_smoke_lines(run_report.stdout)
        if "RUN REPORT :: LAST ECHO" not in run_report.stdout:
            print("install smoke failed: missing compact run report")
            return 1
        if "NEXT RUN" not in run_report.stdout:
            print("install smoke failed: run report did not print next-run advice")
            return 1
        if "ouro run --mock --prompt-style control" not in run_report.stdout:
            print("install smoke failed: run report did not print defeat recovery command")
            return 1

        history = _run_capture(
            (
                str(ouro_bin),
                "--lang",
                "en",
                "history",
                "--limit",
                "1",
            ),
            cwd=run_cwd,
            env=smoke_env,
        )
        if history.returncode != 0:
            print(history.stdout)
            return history.returncode
        _print_smoke_lines(history.stdout)
        if "DEATH HISTORY :: FALLEN RUNS" not in history.stdout:
            print("install smoke failed: missing death history listing")
            return 1
        if "Seed: 7" not in history.stdout:
            print("install smoke failed: death history did not include seed 7")
            return 1

        status = _run_capture(
            (
                str(ouro_bin),
                "--lang",
                "en",
                "status",
            ),
            cwd=run_cwd,
            env=smoke_env,
        )
        if status.returncode != 0:
            print(status.stdout)
            return status.returncode
        _print_smoke_lines(status.stdout)
        if "OURO STATUS :: ECHO LEDGER" not in status.stdout:
            print("install smoke failed: missing status overview")
            return 1
        if "Runs: 1 total" not in status.stdout:
            print("install smoke failed: status did not summarize run archives")
            return 1
        if "Fallen Runs: 1" not in status.stdout:
            print("install smoke failed: status did not summarize death history")
            return 1
        if "NEXT RUN PLAN" not in status.stdout:
            print("install smoke failed: status did not print next-run plan")
            return 1
        if "ouro run --mock --prompt-style control" not in status.stdout:
            print("install smoke failed: status did not print defeat recovery advice")
            return 1
        if "ouro run --mock" not in status.stdout:
            print("install smoke failed: status did not print next commands")
            return 1

    print("Install smoke OK.")
    return 0


def _venv_executable(venv_dir: Path, name: str) -> Path:
    scripts_dir = "Scripts" if os.name == "nt" else "bin"
    suffix = ".exe" if os.name == "nt" else ""
    return venv_dir / scripts_dir / f"{name}{suffix}"


def _run_step(
    command: tuple[str, ...],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> int:
    print(f"$ {_format_command(command)}", flush=True)
    return subprocess.run(command, cwd=cwd, env=env, check=False).returncode


def _run_capture(
    command: tuple[str, ...],
    *,
    cwd: Path,
    env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    print(f"$ {_format_command(command)}", flush=True)
    return subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def _print_smoke_lines(output: str) -> None:
    interesting = (
        "OURO DEMO :: FIRST ECHO",
        "OURO STATUS :: ECHO LEDGER",
        "STEP 1:",
        "STEP 2:",
        "STEP 3:",
        "STEP 4:",
        "STEP 5:",
        "Next commands",
        "NEXT COMMANDS",
        "ouro run --mock",
        "ouro try --seed 1",
        "ouro status --lang en",
        "ouro codex --lang en",
        "ouro runs --lang en --limit 5",
        "ouro run-report --lang en",
        "ouro doctor --lang en",
        "BATTLE COMPLETE",
        "Run Summary",
        "RUN ARCHIVE :: ALL RUNS",
        "RUN REPORT :: LAST ECHO",
        "NEXT RUN",
        "DEATH HISTORY :: FALLEN RUNS",
        "CODEX :: MONSTER ARCHIVE",
        "YOU DIED",
        "RUN COMPLETE",
        "Result :",
        "Status :",
        "Observed:",
        "Floor reached:",
        "Battles Won:",
        "Battles Lost:",
        "Run Archive:",
        "Run Archives:",
        "Runs:",
        "Death History:",
        "Fallen Runs:",
        "Codex :",
    )
    for line in output.splitlines():
        stripped = line.strip()
        if (
            _is_unlocked_codex_line(stripped)
            or stripped.startswith("Seed: 7")
            or any(marker in line for marker in interesting)
        ):
            print(line)


def _has_unlocked_codex_entry(output: str) -> bool:
    return any(_is_unlocked_codex_line(line.strip()) for line in output.splitlines())


def _is_unlocked_codex_line(line: str) -> bool:
    return line.startswith(("[OB]", "[FM]", "[MS]", "[HT]"))


def _run_privacy_scan() -> int:
    scanned = 0
    findings: list[PrivacyFinding] = []
    for path in _iter_privacy_scan_files():
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="ignore")
        findings.extend(_find_secret_markers(path, text))

    if findings:
        print(f"Privacy scan found {len(findings)} possible secret(s):")
        for finding in findings:
            relative = finding.path.relative_to(ROOT)
            print(f"  {relative}:{finding.line_number}: {finding.label}")
        return 1

    print(f"Privacy scan OK: {scanned} release-bound text files checked.")
    return 0


def _iter_privacy_scan_files() -> list[Path]:
    files: list[Path] = []
    for name in RELEASE_SCAN_ROOTS:
        root = ROOT / name
        if root.is_file() and _is_scannable_text_file(root):
            files.append(root)
        elif root.is_dir():
            files.extend(
                candidate
                for candidate in root.rglob("*")
                if candidate.is_file() and _is_scannable_text_file(candidate)
            )
    return sorted(set(files))


def _is_scannable_text_file(path: Path) -> bool:
    relative_parts = path.relative_to(ROOT).parts
    if any(part in IGNORED_PARTS or part.endswith(".egg-info") for part in relative_parts):
        return False
    if any(part.startswith(".") for part in relative_parts):
        return False
    if path.suffix not in TEXT_SUFFIXES:
        return False
    return path.stat().st_size <= 1_000_000


def _find_secret_markers(path: Path, text: str) -> list[PrivacyFinding]:
    findings: list[PrivacyFinding] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(PrivacyFinding(path, line_number, label))
                break
    return findings


def _gate_environment() -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        env["PYTHONPATH"] = src_path + os.pathsep + existing_pythonpath
    else:
        env["PYTHONPATH"] = src_path
    return env


def _format_command(command: tuple[str, ...]) -> str:
    return " ".join(shlex.quote(part) for part in command)


if __name__ == "__main__":
    raise SystemExit(main())
