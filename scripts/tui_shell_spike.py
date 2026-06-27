#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ShellProbe:
    name: str
    module: str
    import_status: str
    version: str
    role: str
    default_path: str
    install_impact: str
    ci_pipe_behavior: str
    snapshot_strategy: str
    fallback: str
    decision: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate optional Rich/Textual TUI shell candidates without changing gameplay."
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable spike evidence.")
    args = parser.parse_args(argv)

    probes = build_shell_probes()
    if args.json:
        print(json.dumps({"ok": True, "probes": [asdict(probe) for probe in probes]}, indent=2))
    else:
        print(render_report(probes))
    return 0


def build_shell_probes() -> tuple[ShellProbe, ...]:
    return (
        ShellProbe(
            name="current-ansi-renderer",
            module="ouro_agent.tui.terminal",
            import_status="available",
            version="repo-local",
            role="default renderer for Slice 0/A and current mock play",
            default_path="keep",
            install_impact="none; no new runtime dependency",
            ci_pipe_behavior="stable plain text; --no-animation keeps turn frames and logs",
            snapshot_strategy="pytest captures deterministic strings and width matrices",
            fallback="ascii-safe output is the renderer itself",
            decision="remain default until optional shell proves equal fallback coverage",
        ),
        ShellProbe(
            name="rich-live",
            module="rich",
            import_status=_module_status("rich"),
            version=_module_version("rich"),
            role="candidate live display adapter for local refresh, status lines, and progress HUDs",
            default_path="defer",
            install_impact="optional dependency only; do not add to base install yet",
            ci_pipe_behavior="must disable live refresh when stdout is not a TTY",
            snapshot_strategy="render through existing frame strings before introducing Rich renderables",
            fallback="fall back to current-ansi-renderer when Rich is absent",
            decision="prototype first for battle/mode/reward playback, then decide",
        ),
        ShellProbe(
            name="textual-app-shell",
            module="textual",
            import_status=_module_status("textual"),
            version=_module_version("textual"),
            role="candidate full app shell for keyboard routing, panels, and future browser-like layout",
            default_path="defer",
            install_impact="larger optional dependency; not suitable for base mock install yet",
            ci_pipe_behavior="requires explicit headless/snapshot path and non-TTY fallback",
            snapshot_strategy="needs app-level snapshot fixtures before default adoption",
            fallback="fall back to current-ansi-renderer when Textual is absent or unsupported",
            decision="defer default; revisit after Rich Live adapter and input contract are proven",
        ),
    )


def render_report(probes: tuple[ShellProbe, ...]) -> str:
    lines = [
        "OURO TUI SHELL SPIKE",
        "",
        "Goal: evaluate Rich Live and Textual without changing gameplay, provider behavior, or mock installability.",
        "",
        "Non-negotiable invariants:",
        "- combat engine owns validation, damage, rewards, drops, and victory",
        "- provider adapters return decisions only; no shell reads API keys or network state",
        "- --no-animation remains deterministic and keeps full turn frames",
        "- ASCII-safe output remains the fallback for CI, pipes, and low-compat terminals",
        "- optional shell adapters must wrap existing frame strings before changing render models",
        "",
        "Dependency probe:",
    ]
    for probe in probes:
        lines.extend(
            [
                f"- {probe.name}",
                f"  module          : {probe.module}",
                f"  import          : {probe.import_status}",
                f"  version         : {probe.version}",
                f"  role            : {probe.role}",
                f"  default path    : {probe.default_path}",
                f"  install impact  : {probe.install_impact}",
                f"  CI / pipe       : {probe.ci_pipe_behavior}",
                f"  snapshot        : {probe.snapshot_strategy}",
                f"  fallback        : {probe.fallback}",
                f"  decision        : {probe.decision}",
            ]
        )
    lines.extend(
        [
            "",
            "Dry-run adapter contract:",
            "Engine Event -> BattleFrame -> BattleScreenModel -> PresentedFrame -> ShellAdapter",
            "ShellAdapter.render(frame_text, refresh=True, alternate_screen=True)",
            "ShellAdapter.close() restores cursor/screen and never mutates RunState",
            "",
            "Recommendation:",
            "KEEP current-ansi-renderer as default. Prototype rich-live as an optional adapter first.",
            "DEFER textual-app-shell as default until keyboard routing, snapshots, and install smoke are proven.",
        ]
    )
    return "\n".join(lines)


def _module_status(module: str) -> str:
    return "available" if importlib.util.find_spec(module) is not None else "not installed"


def _module_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "n/a"


if __name__ == "__main__":
    raise SystemExit(main())
