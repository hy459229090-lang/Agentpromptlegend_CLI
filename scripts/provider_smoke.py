#!/usr/bin/env python3
"""Optional real-provider smoke helper.

Default mode is an offline preflight. Passing ``--live`` runs one short battle
through the configured real provider and fails if the CLI falls back to mock.
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ouro_agent.config.model import OuroConfig, SUPPORTED_PROVIDERS  # noqa: E402
from ouro_agent.config.store import load_config, save_config  # noqa: E402
from ouro_agent.providers import provider_preflight  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Preflight or smoke-test a configured real provider without storing "
            "plaintext API keys."
        )
    )
    parser.add_argument(
        "--provider",
        choices=SUPPORTED_PROVIDERS,
        help="Provider to test. Defaults to the saved config provider.",
    )
    parser.add_argument("--model", help="Model name to test.")
    parser.add_argument(
        "--api-key-env",
        help="Environment variable name containing the provider API key.",
    )
    parser.add_argument("--base-url", help="Base URL for openai-compatible providers.")
    parser.add_argument("--api-version", default=None, help="Optional provider API version.")
    parser.add_argument("--timeout-seconds", type=int, default=None)
    parser.add_argument("--max-retries", type=int, default=None)
    parser.add_argument("--lang", default="en", choices=("en", "zh"))
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--content-dir",
        default="content",
        help="Content directory for the live smoke battle.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="After preflight, run one real-provider battle. May call the network.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned live command without calling the provider.",
    )
    args = parser.parse_args(argv)

    config = _config_from_args(args)
    report = provider_preflight(config)
    real_provider_issue = (
        "select a real provider; mock is already covered by release_check.py"
        if report.provider == "mock"
        else ""
    )
    issues = tuple(issue for issue in (*report.issues, real_provider_issue) if issue)
    ready = not issues

    print(_render_preflight(report, issues, ready))

    if args.dry_run:
        command = _live_command(args)
        print("")
        print("DRY RUN")
        print("would write config : temporary OURO_AGENT_HOME")
        print(f"would run          : {_format_command(command)}")
        print("network           : not called")
        return 0

    if not args.live:
        return 0 if ready else 3

    if not ready:
        print("")
        print("Live smoke not started because preflight is NOT READY.")
        return 3

    return _run_live_smoke(args, config)


def _config_from_args(args: argparse.Namespace) -> OuroConfig:
    if args.provider is None:
        config = load_config().with_field("language", args.lang)
    else:
        config = OuroConfig(provider=args.provider, language=args.lang)
    overrides = {
        "model": args.model,
        "api_key_env": args.api_key_env,
        "base_url": args.base_url,
        "api_version": args.api_version,
        "timeout_seconds": args.timeout_seconds,
        "max_retries": args.max_retries,
        "language": args.lang,
    }
    for field, value in overrides.items():
        if value is not None:
            config = config.with_field(field, value)
    return config


def _render_preflight(report, issues: tuple[str, ...], ready: bool) -> str:
    lines = [
        "REAL PROVIDER SMOKE PREFLIGHT",
        f"provider     : {report.provider}",
        f"model        : {report.model or '(not configured)'}",
    ]
    if report.api_key_env:
        env_status = "set (hidden)" if report.env_present else "MISSING"
        lines.append(f"api_key_env  : {report.api_key_env}")
        lines.append(f"env value    : {env_status}")
    else:
        lines.append("api_key_env  : not configured")
        lines.append("env value    : not required")
    lines.extend(
        [
            f"base_url     : {report.base_url or '-'}",
            f"timeout      : {report.timeout_seconds}s",
            f"retries      : {report.max_retries}",
            "network      : not called",
            f"status       : {'READY' if ready else 'NOT READY'}",
        ]
    )
    for issue in issues:
        lines.append(f"issue        : {issue}")
    return "\n".join(lines)


def _run_live_smoke(args: argparse.Namespace, config: OuroConfig) -> int:
    with tempfile.TemporaryDirectory(prefix="ouro_provider_smoke_") as home:
        home_path = Path(home)
        save_config(config, home_path / "config.toml")

        env = _smoke_environment(home_path)
        command = _live_command(args)
        print("")
        print("LIVE SMOKE")
        print(f"$ {_format_command(command)}")
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        _print_summary(result.stdout)
        if result.returncode != 0:
            print(f"Live smoke failed: command exited with {result.returncode}")
            return result.returncode
        if "BATTLE COMPLETE" not in result.stdout and "战斗结束" not in result.stdout:
            print("Live smoke failed: missing battle completion marker")
            return 1
        if "Note: provider" in result.stdout or "finished on the local mock" in result.stdout:
            print("Live smoke failed: provider fell back to mock")
            return 1
        print("Live provider smoke OK.")
        return 0


def _live_command(args: argparse.Namespace) -> tuple[str, ...]:
    python_bin = os.environ.get("OURO_PYTHON", sys.executable)
    return (
        python_bin,
        "-m",
        "ouro_agent.cli.main",
        "--lang",
        args.lang,
        "play",
        "--seed",
        str(args.seed),
        "--no-animation",
        "--no-trace",
        "--content-dir",
        args.content_dir,
    )


def _smoke_environment(home: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["OURO_AGENT_HOME"] = str(home)
    env["PYTHONIOENCODING"] = "utf-8"
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        env["PYTHONPATH"] = str(SRC) + os.pathsep + existing_pythonpath
    else:
        env["PYTHONPATH"] = str(SRC)
    return env


def _print_summary(output: str) -> None:
    interesting = (
        "BATTLE COMPLETE",
        "战斗结束",
        "Result :",
        "结果",
        "Echo Cost",
        "Read Echo",
        "Spoken Echo",
        "Ritual Time",
        "Trace :",
        "Codex :",
        "Note: provider",
        "finished on the local mock",
    )
    for line in output.splitlines():
        if any(marker in line for marker in interesting):
            print(line)


def _format_command(command: tuple[str, ...]) -> str:
    return " ".join(shlex.quote(part) for part in command)


if __name__ == "__main__":
    raise SystemExit(main())
