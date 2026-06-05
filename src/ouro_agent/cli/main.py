"""Ouro Agent CLI entrypoint.

Subcommands:
* ``ouro --version``
* ``ouro config show``
* ``ouro config set <field> <value>``
* ``ouro play --mock [--seed N] [--no-trace] [--unicode] [--color always]``
* ``ouro validate-content``
* ``ouro doctor`` (install, config, provider, and content sanity checks)

The CLI never resolves combat or stores keys. It composes pieces from the
other modules.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import textwrap
import time
from collections.abc import Callable
from pathlib import Path

from ouro_agent import __version__
from ouro_agent.config import (
    DEFAULT_API_KEY_ENV,
    OuroConfig,
    config_path,
    load_config,
    redacted_view,
    save_config,
    set_field,
)
from ouro_agent.config.model import ConfigError, SUPPORTED_PROVIDERS
from ouro_agent.content import ContentError, load_content_bundle, resolve_content_dir
from ouro_agent.engine.battle import BattleLoop, TurnRecord
from ouro_agent.engine.models import BattleState, StatusEffect
from ouro_agent.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, label
from ouro_agent.llm.prompt import apply_prompt_style, supported_prompt_styles
from ouro_agent.llm.prompt import prompt_style_text
from ouro_agent.providers import (
    FallbackOnErrorProvider,
    MockProvider,
    build_provider,
    provider_preflight,
)
from ouro_agent.providers.base import ProviderError
from ouro_agent.sessions import (
    RunPhase,
    RunState,
    CodexStoreError,
    RunArchiveError,
    append_death_history,
    codex_path,
    create_run_state,
    death_history_path,
    load_codex_progress,
    load_death_history,
    load_run_archive,
    load_run_archives,
    new_battle_id,
    new_battle_llm_session_id,
    new_run_id,
    record_battle_codex,
    run_archive_dir,
    save_run_archive,
    save_codex_progress,
)
from ouro_agent.trace import TraceConfig, TraceReplayError, TraceWriter, render_trace_replay
from ouro_agent.tui import (
    render_battle_report,
    render_battle_screen,
    render_codex_card,
    render_codex_summary,
    render_config_screen,
    render_death_history,
    render_encounter_briefing,
    render_event,
    render_main_menu,
    render_progress_status,
    render_prompt_templates,
    render_rest,
    render_run_setup_screen,
    render_route_choice,
    render_reward_choice,
    render_shop,
    render_start_screen,
    render_run_report,
    render_run_summary,
    render_run_archives,
    get_terminal,
)
from ouro_agent.tui.presenter import present_battle_frame
from ouro_agent.validation import validate_content_dir


def _ensure_utf8_stdout() -> None:
    """On Windows the default console may be cp936/GBK and choke on Chinese.

    Reconfigure stdout/stderr to UTF-8 once, defensively. Safe on POSIX too.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass

from ouro_agent.engine import resolve_build, run_batch
from ouro_agent.tui.screens import render_hero_card, render_hero_list

DEFAULT_CONTENT_DIR = "content"
DEFAULT_HERO_ID = "hero_shadow_apprentice"
DEFAULT_ENEMY_IDS = ["enemy_hungry_cultist", "enemy_black_candle_acolyte"]
CONTENT_DIR_HELP = (
    "Path to content root (uses ./content when present; otherwise bundled "
    "installed content)"
)
ABORT_EXIT_CODE = 130


class CliAbort(RuntimeError):
    """Raised when an interactive command is cancelled by the user."""


def _read_input(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError) as err:
        sys.stderr.write("\nAborted.\n")
        raise CliAbort() from err


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = _build_parser()
    normalized_argv = _normalize_global_options(
        list(sys.argv[1:] if argv is None else argv)
    )
    args = parser.parse_args(normalized_argv)

    try:
        if args.command is None:
            return _cmd_menu(args)
        return args.handler(args)
    except CliAbort:
        return ABORT_EXIT_CODE
    except (
        ConfigError,
        ContentError,
        ProviderError,
        CodexStoreError,
        RunArchiveError,
    ) as err:
        sys.stderr.write(f"error: {err}\n")
        return 2


def _storage_warning(kind: str, err: Exception, lang: str) -> str:
    labels = {
        "codex": {"en": "Codex progress", "zh": "图鉴进度"},
        "run_archive": {"en": "run archive", "zh": "运行归档"},
        "death_history": {"en": "death history", "zh": "死亡历史"},
    }
    display = labels.get(kind, {}).get(lang, kind)
    if lang == "zh":
        return f"警告：无法保存{display}：{err}\n"
    return f"Warning: could not save {display}: {err}\n"


def _run_battle_floor_label(run_state: RunState, bundle, lang: str) -> str:
    dungeon = bundle.dungeons.get(run_state.dungeon_id)
    dungeon_name = (
        dungeon.display_name.get(lang) or dungeon.display_name.get("en", run_state.dungeon_id)
        if dungeon is not None
        else run_state.dungeon_id
    )
    floor_number = run_state.current_floor(bundle).floor_number
    if lang == "zh":
        return f"{dungeon_name} :: 第 {floor_number} 层"
    return f"{dungeon_name.upper()} :: FLOOR {floor_number}"


def _run_exit_code(run_state: RunState, *, strict_result_exit_code: bool = False) -> int:
    if strict_result_exit_code and run_state.phase is not RunPhase.COMPLETE:
        return 1
    return 0


def _effective_game_config(args: argparse.Namespace, saved_config: OuroConfig) -> OuroConfig:
    lang = _resolve_lang(args, saved_config)
    unicode_mode = bool(getattr(args, "unicode", False)) or saved_config.unicode_mode
    if getattr(args, "mock", False):
        return OuroConfig(
            provider="mock",
            model="mock-smart",
            api_key_env="",
            base_url="",
            api_version="",
            timeout_seconds=saved_config.timeout_seconds,
            max_retries=saved_config.max_retries,
            trace_level=saved_config.trace_level,
            unicode_mode=unicode_mode,
            language=lang,
        )
    return OuroConfig(
        provider=saved_config.provider,
        model=saved_config.model,
        api_key_env=saved_config.api_key_env,
        base_url=saved_config.base_url,
        api_version=saved_config.api_version,
        timeout_seconds=saved_config.timeout_seconds,
        max_retries=saved_config.max_retries,
        trace_level=saved_config.trace_level,
        unicode_mode=unicode_mode,
        language=lang,
    )


def _effective_color_mode(args: argparse.Namespace) -> str:
    mode = str(getattr(args, "color", "never") or "never").lower()
    if mode == "auto":
        return "always" if sys.stdout.isatty() and not os.environ.get("NO_COLOR") else "never"
    return mode


def _write_storage_warning_once(
    kind: str,
    err: Exception,
    lang: str,
    writer: Callable[[str], object],
    warned: set[str] | None = None,
) -> None:
    if warned is not None and kind in warned:
        return
    writer(_storage_warning(kind, err, lang))
    if warned is not None:
        warned.add(kind)


def _try_save_codex_progress(
    progress,
    lang: str,
    writer: Callable[[str], object] | None = None,
    warned: set[str] | None = None,
) -> Path | None:
    try:
        return save_codex_progress(progress)
    except (CodexStoreError, OSError) as err:
        _write_storage_warning_once(
            "codex",
            err,
            lang,
            writer or sys.stdout.write,
            warned,
        )
        return None


def _try_save_run_records(
    run_state: RunState,
    bundle,
    lang: str,
    writer: Callable[[str], object] | None = None,
    warned: set[str] | None = None,
) -> tuple[Path | None, Path | None]:
    warning_writer = writer or sys.stdout.write
    archive_path: Path | None = None
    death_path: Path | None = None
    try:
        archive_path = save_run_archive(run_state, bundle)
    except (RunArchiveError, OSError) as err:
        _write_storage_warning_once("run_archive", err, lang, warning_writer, warned)
    try:
        death_path = append_death_history(run_state, bundle)
    except (RunArchiveError, OSError) as err:
        _write_storage_warning_once("death_history", err, lang, warning_writer, warned)
    return archive_path, death_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ouro",
        description="Ouro Agent: Prompt Legend - command-line AI roguelike",
    )
    parser.add_argument("--version", action="version", version=f"ouro {__version__}")
    parser.set_defaults(command=None)

    sub = parser.add_subparsers(dest="command")

    parser.add_argument(
        "--lang",
        choices=SUPPORTED_LANGUAGES,
        default=None,
        help="Override UI language for this command (en/zh).",
    )

    # menu
    menu = sub.add_parser("menu", help="Show game status and entry commands")
    menu.set_defaults(handler=_cmd_menu)

    # guided demo
    demo = sub.add_parser(
        "demo",
        help="Run a deterministic mock guided demo for first-time players",
    )
    demo.add_argument("--seed", type=int, default=1)
    demo.add_argument("--unicode", action="store_true")
    demo.add_argument("--color", choices=("never", "auto", "always"), default="never")
    demo.add_argument(
        "--hero",
        default=DEFAULT_HERO_ID,
        help="Hero id to showcase (see 'ouro list-heroes')",
    )
    demo.add_argument(
        "--content-dir",
        default=DEFAULT_CONTENT_DIR,
        help=CONTENT_DIR_HELP,
    )
    demo.add_argument(
        "--prompt-style",
        choices=supported_prompt_styles(),
        default=None,
        help="Apply a strategy template to the demo battle.",
    )
    demo.set_defaults(handler=_cmd_demo)

    # config
    config = sub.add_parser("config", help="View or change configuration")
    config_sub = config.add_subparsers(dest="config_command")
    cfg_show = config_sub.add_parser("show", help="Show current configuration")
    cfg_show.set_defaults(handler=_cmd_config_show)
    cfg_set = config_sub.add_parser("set", help="Set a configuration field")
    cfg_set.add_argument("field")
    cfg_set.add_argument("value")
    cfg_set.set_defaults(handler=_cmd_config_set)
    cfg_setup = config_sub.add_parser(
        "setup",
        aliases=["wizard"],
        help="Step-by-step provider configuration",
    )
    cfg_setup.set_defaults(handler=_cmd_config_setup)
    cfg_preflight = config_sub.add_parser(
        "preflight",
        help="Check provider readiness without a network call",
    )
    cfg_preflight.set_defaults(handler=_cmd_config_preflight)
    config.set_defaults(handler=_cmd_config_show)

    # play
    play = sub.add_parser("play", help="Play a battle")
    play.add_argument("--mock", action="store_true", help="Force the mock provider")
    play.add_argument("--seed", type=int, default=1)
    play.add_argument("--no-trace", action="store_true")
    play.add_argument(
        "--no-animation",
        action="store_true",
        help="Print every turn frame without sleeping between frames.",
    )
    play.add_argument(
        "--delay",
        type=float,
        default=0.18,
        help="Seconds to wait after each turn frame (default: 0.18).",
    )
    play.add_argument("--unicode", action="store_true")
    play.add_argument("--color", choices=("never", "auto", "always"), default="never")
    play.add_argument(
        "--hero",
        default=None,
        help="Hero id to use (see 'ouro list-heroes')",
    )
    play.add_argument(
        "--content-dir",
        default=DEFAULT_CONTENT_DIR,
        help=CONTENT_DIR_HELP,
    )
    play.add_argument(
        "--trace-dir",
        default=None,
        help="Override trace output directory (defaults to ~/.ouro_agent/traces)",
    )
    play.add_argument(
        "--prompt-style",
        choices=supported_prompt_styles(),
        default=None,
        help="Apply a strategy template to this battle.",
    )
    play.set_defaults(handler=_cmd_play)

    # list-heroes
    listh = sub.add_parser("list-heroes", help="List all heroes")
    listh.add_argument("--content-dir", default=DEFAULT_CONTENT_DIR, help=CONTENT_DIR_HELP)
    listh.set_defaults(handler=_cmd_list_heroes)

    # hero-card
    card = sub.add_parser("hero-card", help="Show a single hero detail card")
    card.add_argument("hero_id")
    card.add_argument("--content-dir", default=DEFAULT_CONTENT_DIR, help=CONTENT_DIR_HELP)
    card.add_argument("--prompt-style", choices=supported_prompt_styles(), default=None)
    card.add_argument("--unicode", action="store_true")
    card.set_defaults(handler=_cmd_hero_card)

    templates = sub.add_parser(
        "prompt-templates", help="List strategy templates for hero prompts"
    )
    templates.set_defaults(handler=_cmd_prompt_templates)

    status = sub.add_parser("status", help="Show player progress and next commands")
    status.add_argument("--content-dir", default=DEFAULT_CONTENT_DIR, help=CONTENT_DIR_HELP)
    status.set_defaults(handler=_cmd_status)

    codex = sub.add_parser("codex", help="Show persisted monster Codex progress")
    codex.add_argument(
        "enemy_id",
        nargs="?",
        default=None,
        help="Optional enemy id for a detailed Codex card",
    )
    codex.add_argument("--content-dir", default=DEFAULT_CONTENT_DIR, help=CONTENT_DIR_HELP)
    codex.set_defaults(handler=_cmd_codex)

    runs = sub.add_parser("runs", help="Show persisted run archives")
    runs.add_argument("--content-dir", default=DEFAULT_CONTENT_DIR, help=CONTENT_DIR_HELP)
    runs.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of run archives to show (default: 10)",
    )
    runs.set_defaults(handler=_cmd_runs)

    run_report = sub.add_parser("run-report", help="Show a compact saved-run report")
    run_report.add_argument(
        "archive_path",
        nargs="?",
        default=None,
        help="Optional .run.json path (defaults to the latest saved run)",
    )
    run_report.add_argument(
        "--content-dir",
        default=DEFAULT_CONTENT_DIR,
        help=CONTENT_DIR_HELP,
    )
    run_report.set_defaults(handler=_cmd_run_report)

    history = sub.add_parser("history", help="Show persisted death history")
    history.add_argument("--content-dir", default=DEFAULT_CONTENT_DIR, help=CONTENT_DIR_HELP)
    history.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of death records to show (default: 10)",
    )
    history.set_defaults(handler=_cmd_history)

    replay = sub.add_parser("replay", help="Replay a local JSONL battle trace")
    replay.add_argument("trace_path", help="Path to a .trace.jsonl file")
    replay.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Show only the first N timeline events (default: all)",
    )
    replay.set_defaults(handler=_cmd_replay)

    # validate-content
    validate = sub.add_parser("validate-content", help="Validate content/ directory")
    validate.add_argument(
        "--content-dir",
        default=DEFAULT_CONTENT_DIR,
        help=CONTENT_DIR_HELP,
    )
    validate.set_defaults(handler=_cmd_validate_content)

    # doctor
    doctor = sub.add_parser("doctor", help="Run install + config sanity checks")
    doctor.add_argument(
        "--content-dir",
        default=DEFAULT_CONTENT_DIR,
        help=CONTENT_DIR_HELP,
    )
    doctor.set_defaults(handler=_cmd_doctor)

    # run
    run = sub.add_parser("run", help="Play a full roguelike run with dungeon traversal")
    run.add_argument("--mock", action="store_true", help="Force the mock provider")
    run.add_argument("--seed", type=int, default=1)
    run.add_argument("--no-trace", action="store_true")
    run.add_argument(
        "--no-animation",
        action="store_true",
        help="Print every turn frame without sleeping between frames.",
    )
    run.add_argument(
        "--delay",
        type=float,
        default=0.18,
        help="Seconds to wait after each turn frame (default: 0.18).",
    )
    run.add_argument("--unicode", action="store_true")
    run.add_argument("--color", choices=("never", "auto", "always"), default="never")
    run.add_argument(
        "--hero",
        default=None,
        help="Hero id to use (see 'ouro list-heroes')",
    )
    run.add_argument(
        "--dungeon",
        default="dungeon_ember_crypt",
        help="Dungeon id to use",
    )
    run.add_argument(
        "--content-dir",
        default=DEFAULT_CONTENT_DIR,
        help=CONTENT_DIR_HELP,
    )
    run.add_argument(
        "--trace-dir",
        default=None,
        help="Override trace output directory (defaults to ~/.ouro_agent/traces)",
    )
    run.add_argument(
        "--prompt-style",
        choices=supported_prompt_styles(),
        default=None,
        help="Apply a strategy template to all battles.",
    )
    run.add_argument(
        "--auto",
        action="store_true",
        help="Auto-select first option in route/reward/shop choices",
    )
    run.add_argument(
        "--strict-result-exit-code",
        action="store_true",
        help="Return nonzero when the game run ends in death or timeout.",
    )
    run.set_defaults(handler=_cmd_run)

    batch = sub.add_parser(
        "batch", help="Run multiple battles for balance testing and statistics"
    )
    batch.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of battles to run (default: 10)",
    )
    batch.add_argument(
        "--seed",
        type=int,
        default=1,
        help="Starting seed (will use seed, seed+1, ..., seed+count-1)",
    )
    batch.add_argument(
        "--max-ticks",
        type=int,
        default=600,
        help="Safety tick limit per battle (default: 600)",
    )
    batch.add_argument(
        "--hero",
        default=DEFAULT_HERO_ID,
        help="Hero id to use (see 'ouro list-heroes')",
    )
    batch.add_argument(
        "--enemies",
        nargs="+",
        default=DEFAULT_ENEMY_IDS,
        help="Enemy ids to fight (default: hungry cultist + black candle acolyte)",
    )
    batch.add_argument(
        "--content-dir",
        default=DEFAULT_CONTENT_DIR,
        help=CONTENT_DIR_HELP,
    )
    batch.add_argument(
        "--prompt-style",
        choices=supported_prompt_styles(),
        default=None,
        help="Apply a strategy template to every mock battle.",
    )
    batch.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    batch.set_defaults(handler=_cmd_batch)

    return parser


def _normalize_global_options(argv: list[str]) -> list[str]:
    """Allow global options in the common `ouro command --lang en` position."""
    global_args: list[str] = []
    remaining: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--lang":
            if index + 1 >= len(argv):
                remaining.append(token)
                index += 1
                continue
            global_args.extend((token, argv[index + 1]))
            index += 2
            continue
        if token.startswith("--lang="):
            global_args.append(token)
            index += 1
            continue
        remaining.append(token)
        index += 1
    return [*global_args, *remaining]


def _resolve_lang(args: argparse.Namespace, config: OuroConfig) -> str:
    return getattr(args, "lang", None) or config.language or DEFAULT_LANGUAGE


def _cmd_menu(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    sys.stdout.write(
        render_main_menu(
            config,
            config_path=str(config_path()),
            recent_trace=_latest_trace_label(),
            language=lang,
        )
        + "\n"
    )
    return 0


def _cmd_demo(args: argparse.Namespace) -> int:
    """Run a deterministic, no-network first experience smoke."""
    saved_config = load_config()
    lang = _resolve_lang(args, saved_config)
    content_dir = resolve_content_dir(args.content_dir)
    bundle = load_content_bundle(content_dir)
    demo_config = OuroConfig(
        provider="mock",
        model="mock-smart",
        api_key_env="",
        base_url="",
        api_version="",
        timeout_seconds=saved_config.timeout_seconds,
        max_retries=saved_config.max_retries,
        trace_level=saved_config.trace_level,
        unicode_mode=bool(args.unicode) or saved_config.unicode_mode,
        language=lang,
    )
    hero_id = args.hero or DEFAULT_HERO_ID
    hero = bundle.get_hero(hero_id)
    build = resolve_build(hero, bundle)

    sys.stdout.write(_demo_heading("OURO DEMO :: FIRST ECHO", "OURO DEMO :: 初次回响", lang))
    sys.stdout.write(
        "\n"
        + _demo_step(
            1,
            "Status and next commands",
            "状态与下一步命令",
            lang,
        )
        + "\n"
    )
    sys.stdout.write(
        render_main_menu(
            demo_config,
            config_path=str(config_path()),
            recent_trace=None,
            language=lang,
        )
        + "\n"
    )

    sys.stdout.write(
        "\n"
        + _demo_step(
            2,
            "Hero card and build plan",
            "英雄卡与构筑计划",
            lang,
        )
        + "\n"
    )
    sys.stdout.write(
        render_hero_card(
            hero,
            bundle,
            build,
            language=lang,
            prompt_style=args.prompt_style,
            unicode_mode=demo_config.unicode_mode,
        )
        + "\n"
    )

    sys.stdout.write(
        "\n"
        + _demo_step(
            3,
            "Deterministic mock battle",
            "确定性 Mock 战斗",
            lang,
        )
        + "\n"
    )
    play_args = argparse.Namespace(
        lang=lang,
        mock=True,
        seed=args.seed,
        no_trace=True,
        no_animation=True,
        delay=0.0,
        unicode=bool(args.unicode),
        hero=hero_id,
        content_dir=str(content_dir),
        trace_dir=None,
        prompt_style=args.prompt_style,
        color=args.color,
    )
    rc = _cmd_play(play_args)
    if rc != 0:
        return rc

    sys.stdout.write(
        "\n"
        + _demo_step(
            4,
            "Codex readback",
            "图鉴读回",
            lang,
        )
        + "\n"
    )
    progress = load_codex_progress()
    sys.stdout.write(f"Codex : {codex_path()}\n\n")
    sys.stdout.write(
        render_codex_summary(bundle, codex_progress=progress, language=lang)
        + "\n"
    )
    sys.stdout.write(
        "\n"
        + _demo_step(
            5,
            "Continue from here",
            "从这里继续",
            lang,
        )
        + "\n"
    )
    sys.stdout.write(_demo_next_commands(lang) + "\n")
    return 0


def _demo_heading(en: str, zh: str, lang: str) -> str:
    title = zh if lang == "zh" else en
    line = "=" * min(100, max(40, len(title)))
    return f"{line}\n{title}\n{line}\n"


def _demo_step(index: int, en: str, zh: str, lang: str) -> str:
    text = zh if lang == "zh" else en
    label_text = "STEP" if lang == "en" else "步骤"
    return f"{label_text} {index}: {text}"


def _demo_next_commands(lang: str) -> str:
    if lang == "zh":
        commands = (
            ("完整运行", "ouro run --mock"),
            ("状态总览", "ouro status --lang zh"),
            ("运行报告", "ouro run-report --lang zh"),
            ("查看图鉴", "ouro codex --lang zh"),
            ("查看归档", "ouro runs --lang zh --limit 5"),
            ("安装诊断", "ouro doctor --lang zh"),
        )
        title = "下一步命令"
    else:
        commands = (
            ("Full run", "ouro run --mock"),
            ("Status", "ouro status --lang en"),
            ("Run Report", "ouro run-report --lang en"),
            ("Review Codex", "ouro codex --lang en"),
            ("Review runs", "ouro runs --lang en --limit 5"),
            ("Doctor", "ouro doctor --lang en"),
        )
        title = "Next commands"
    lines = [title]
    lines.extend(f"- {name:<13} {command}" for name, command in commands)
    return "\n".join(lines)


def _cmd_replay(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    try:
        output = render_trace_replay(
            args.trace_path,
            language=lang,
            limit=args.limit or None,
        )
    except TraceReplayError as err:
        sys.stderr.write(f"error: {err}\n")
        return 2
    sys.stdout.write(output + "\n")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    content_dir = resolve_content_dir(args.content_dir)
    bundle = load_content_bundle(content_dir)
    progress = load_codex_progress()
    archives = load_run_archives()
    deaths = load_death_history()
    term_width = shutil.get_terminal_size((100, 24)).columns
    sys.stdout.write(
        render_progress_status(
            config,
            bundle,
            progress,
            archives,
            deaths,
            config_path=str(config_path()),
            codex_save_path=str(codex_path()),
            run_archive_path=str(run_archive_dir()),
            death_history_save_path=str(death_history_path()),
            language=lang,
            width=term_width,
        )
        + "\n"
    )
    return 0


def _latest_trace_label() -> str | None:
    base = Path(os.environ.get("OURO_AGENT_HOME", str(Path.home() / ".ouro_agent")))
    trace_dir = base / "traces"
    if not trace_dir.exists():
        return None
    traces = sorted(trace_dir.glob("*.trace.jsonl"), key=lambda p: p.stat().st_mtime)
    return str(traces[-1]) if traces else None


def _cmd_config_show(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    redacted = redacted_view(config, language=lang)
    sys.stdout.write(
        render_config_screen(
            redacted, config_path=str(config_path()), language=lang
        )
        + "\n"
    )
    return 0


def _cmd_config_set(args: argparse.Namespace) -> int:
    config = set_field(args.field, args.value)
    lang = _resolve_lang(args, config)
    redacted = redacted_view(config, language=lang)
    sys.stdout.write(
        render_config_screen(
            redacted, config_path=str(config_path()), language=lang
        )
        + "\n"
    )
    return 0


def _cmd_config_setup(args: argparse.Namespace) -> int:
    current = load_config()
    lang = _resolve_lang(args, current)
    provider = _prompt_provider(current.provider, lang)
    config = current.with_field("provider", provider)

    if provider == "mock":
        config = config.with_field("model", "mock-smart")
        config = config.with_field("api_key_env", "")
        config = config.with_field("base_url", "")
    else:
        default_model = _default_model(provider, current)
        model = _prompt_text(
            _setup_text("model_prompt", lang),
            default=default_model,
        )
        api_key_env = _prompt_text(
            _setup_text("api_key_env_prompt", lang),
            default=DEFAULT_API_KEY_ENV[provider],
        )
        config = config.with_field("model", model)
        config = config.with_field("api_key_env", api_key_env)

        if provider == "openai-compatible":
            base_url = _prompt_text(
                _setup_text("base_url_prompt", lang),
                default=current.base_url or "https://your-host.example.com/v1",
            )
            config = config.with_field("base_url", base_url)
        elif provider == "openai":
            base_url = _prompt_text(
                _setup_text("openai_base_url_prompt", lang),
                default=current.base_url,
            )
            config = config.with_field("base_url", base_url)
        else:
            config = config.with_field("base_url", "")

    language = _prompt_text(
        _setup_text("language_prompt", lang),
        default=config.language,
    )
    config = config.with_field("language", language)
    save_config(config)

    sys.stdout.write("\n" + _setup_text("saved", lang) + "\n")
    sys.stdout.write(
        render_config_screen(
            redacted_view(config, language=lang),
            config_path=str(config_path()),
            language=lang,
        )
        + "\n"
    )
    if config.provider != "mock":
        _print_env_status(config.api_key_env, lang)
    return 0


def _cmd_config_preflight(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    report = provider_preflight(config)
    sys.stdout.write(_render_provider_preflight(report, lang) + "\n")
    return 0 if report.ready else 3


def _render_provider_preflight(report, lang: str) -> str:
    title = "PROVIDER PREFLIGHT" if lang == "en" else "PROVIDER PREFLIGHT :: 供应商预检"
    ready_label = "READY" if report.ready else "NOT READY"
    if lang == "zh":
        ready_label = "READY" if report.ready else "NOT READY / 未就绪"

    lines = [
        title,
        f"provider     : {report.provider}",
        f"model        : {report.model or '-'}",
        f"base_url     : {report.base_url or '-'}",
        f"api_version  : {report.api_version or '-'}",
        f"timeout      : {report.timeout_seconds}s",
        f"retries      : {report.max_retries}",
    ]
    if report.api_key_env:
        env_state = "set (hidden)" if report.env_present else "MISSING"
        lines.append(f"api_key_env  : {report.api_key_env}")
        lines.append(f"env value    : {env_state}")
    else:
        lines.append("api_key_env  : not required")
        lines.append("env value    : not read")
    lines.extend(
        [
            "network      : not called",
            f"status       : {ready_label}",
        ]
    )
    if report.issues:
        lines.append("issues       :")
        lines.extend(f"- {issue}" for issue in report.issues)
    else:
        if report.provider == "mock":
            note = "mock provider is playable offline; no API key required"
        else:
            note = "offline checks passed; the first live turn may still fail on network/auth"
        lines.append(f"note         : {note}")
    return "\n".join(lines)


def _prompt_provider(current: str, lang: str) -> str:
    choices = list(SUPPORTED_PROVIDERS)
    sys.stdout.write(_setup_text("provider_title", lang) + "\n")
    for idx, provider in enumerate(choices, start=1):
        sys.stdout.write(f"[{idx}] {provider}\n")

    while True:
        raw = _prompt_text(
            _setup_text("provider_prompt", lang),
            default=current,
        )
        if raw in choices:
            return raw
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(choices):
                return choices[idx - 1]
        sys.stdout.write(_setup_text("provider_invalid", lang) + "\n")


def _prompt_text(prompt: str, *, default: str) -> str:
    suffix = f" [{default}]" if default else ""
    raw = _read_input(f"{prompt}{suffix}: ")
    return raw or default


def _default_model(provider: str, current: OuroConfig) -> str:
    if current.provider == provider and current.model:
        return current.model
    return {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-sonnet-4-5",
        "openai-compatible": "your-model-name",
    }.get(provider, "mock-smart")


def _print_env_status(api_key_env: str, lang: str) -> None:
    if not api_key_env:
        return
    if os.environ.get(api_key_env):
        sys.stdout.write(_setup_text("env_present", lang).format(env=api_key_env) + "\n")
        return
    sys.stdout.write(_setup_text("env_missing", lang).format(env=api_key_env) + "\n")


def _setup_text(key: str, lang: str) -> str:
    text = {
        "provider_title": {
            "en": "Choose provider",
            "zh": "选择模型供应商",
        },
        "provider_prompt": {
            "en": "Provider number or name",
            "zh": "供应商编号或名称",
        },
        "provider_invalid": {
            "en": "Invalid provider, please try again.",
            "zh": "供应商无效，请重新输入。",
        },
        "model_prompt": {"en": "Model name", "zh": "模型名称"},
        "api_key_env_prompt": {
            "en": "API key environment variable name",
            "zh": "API key 环境变量名",
        },
        "base_url_prompt": {
            "en": "OpenAI-compatible base URL",
            "zh": "OpenAI 兼容接口 base_url",
        },
        "openai_base_url_prompt": {
            "en": "OpenAI base URL override, leave blank for default",
            "zh": "OpenAI base_url 覆盖；留空使用官方默认",
        },
        "language_prompt": {"en": "UI language (zh/en)", "zh": "界面语言 (zh/en)"},
        "saved": {"en": "Configuration saved.", "zh": "配置已保存。"},
        "env_present": {
            "en": "Environment variable {env} is set for this shell.",
            "zh": "当前 shell 已设置环境变量 {env}。",
        },
        "env_missing": {
            "en": "Environment variable {env} is not set yet. Set it before real LLM play.",
            "zh": "环境变量 {env} 还没设置。真实 LLM 开局前需要先设置它。",
        },
    }
    return text[key].get(lang) or text[key]["en"]


def _cmd_list_heroes(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    bundle = load_content_bundle(resolve_content_dir(args.content_dir))
    sys.stdout.write(render_hero_list(bundle, language=lang) + "\n")
    return 0


def _cmd_hero_card(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    unicode_mode = bool(args.unicode) or config.unicode_mode
    bundle = load_content_bundle(resolve_content_dir(args.content_dir))
    hero = bundle.get_hero(args.hero_id)
    build = resolve_build(hero, bundle)
    sys.stdout.write(
        render_hero_card(
            hero,
            bundle,
            build,
            language=lang,
            prompt_style=args.prompt_style,
            unicode_mode=unicode_mode,
        )
        + "\n"
    )
    return 0


def _cmd_prompt_templates(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    sys.stdout.write(render_prompt_templates(language=lang) + "\n")
    return 0


def _cmd_codex(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    bundle = load_content_bundle(resolve_content_dir(args.content_dir))
    progress = load_codex_progress()

    sys.stdout.write(f"Codex : {codex_path()}\n\n")
    if args.enemy_id:
        sys.stdout.write(
            render_codex_card(
                args.enemy_id,
                bundle,
                codex_progress=progress,
                language=lang,
            )
            + "\n"
        )
    else:
        sys.stdout.write(
            render_codex_summary(bundle, codex_progress=progress, language=lang)
            + "\n"
        )
    return 0


def _cmd_runs(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    bundle = load_content_bundle(resolve_content_dir(args.content_dir))
    archives = load_run_archives()

    sys.stdout.write(f"Run Archives: {run_archive_dir()}\n\n")
    sys.stdout.write(
        render_run_archives(
            archives,
            bundle,
            language=lang,
            limit=max(0, args.limit),
        )
        + "\n"
    )
    return 0


def _cmd_run_report(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    bundle = load_content_bundle(resolve_content_dir(args.content_dir))

    entry = None
    if args.archive_path:
        entry = load_run_archive(Path(args.archive_path).expanduser())
        sys.stdout.write(f"Run Archive: {entry.get('_archive_path', args.archive_path)}\n\n")
    else:
        archives = load_run_archives()
        entry = archives[0] if archives else None
        sys.stdout.write(f"Run Archives: {run_archive_dir()}\n\n")

    sys.stdout.write(
        render_run_report(
            entry,
            bundle,
            language=lang,
            width=shutil.get_terminal_size((100, 24)).columns,
        )
        + "\n"
    )
    return 0


def _cmd_history(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    bundle = load_content_bundle(resolve_content_dir(args.content_dir))
    deaths = load_death_history()

    sys.stdout.write(f"Death History: {death_history_path()}\n\n")
    sys.stdout.write(
        render_death_history(
            deaths,
            bundle,
            language=lang,
            limit=max(0, args.limit),
        )
        + "\n"
    )
    return 0


def _cmd_validate_content(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    report = validate_content_dir(resolve_content_dir(args.content_dir))
    sys.stdout.write(report.render(language=lang) + "\n")
    return 0 if report.ok else 3


def _cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    content_dir = resolve_content_dir(args.content_dir)
    report = validate_content_dir(content_dir)
    provider_report = provider_preflight(config)
    status = "OK" if report.ok else "FAIL"
    provider_status = "READY" if provider_report.ready else "NOT READY"
    sys.stdout.write(f"ouro version : {__version__}\n")
    sys.stdout.write(f"config path  : {config_path()}\n")
    sys.stdout.write(f"provider     : {config.provider}\n")
    sys.stdout.write(f"model        : {config.model}\n")
    sys.stdout.write(f"language     : {lang}\n")
    if provider_report.api_key_env:
        sys.stdout.write(
            f"env var      : {provider_report.api_key_env} = "
            + ("set (hidden)" if provider_report.env_present else "MISSING")
            + "\n"
        )
    else:
        sys.stdout.write("env var      : (not configured; mock works without it)\n")
    sys.stdout.write(f"provider chk : {provider_status}\n")
    for issue in provider_report.issues:
        sys.stdout.write(f"provider err : {issue}\n")
    sys.stdout.write("supported    : " + ", ".join(SUPPORTED_PROVIDERS) + "\n")
    sys.stdout.write(f"content dir  : {content_dir}\n")
    sys.stdout.write(
        "content      : "
        f"{status} "
        f"heroes={report.heroes} skills={report.skills} enemies={report.enemies} "
        f"items={report.items} affixes={report.affixes} "
        f"resonances={report.resonances}\n"
    )
    if report.error:
        sys.stdout.write(f"content err  : {report.error}\n")
    sys.stdout.write("mock play    : ready (no API key required)\n")
    return 0 if report.ok and provider_report.ready else 3


def _prompt_hero_choice(bundle, lang: str) -> str:
    heroes = list(bundle.heroes.values())
    prompt = "Choose hero number or id" if lang == "en" else "选择英雄编号或 ID"
    while True:
        raw = _read_input(f"\n{prompt}: ")
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(heroes):
                return heroes[idx].id
        if raw in bundle.heroes:
            return raw
        sys.stderr.write(
            ("Invalid hero. Try again.\n" if lang == "en" else "英雄无效，请重新输入。\n")
        )


def _prompt_prompt_style(lang: str) -> str | None:
    choices = list(supported_prompt_styles())
    prompt = (
        "Prompt style number/name, or blank for hero default"
        if lang == "en"
        else "Prompt 预设编号/名称；留空使用英雄默认"
    )
    while True:
        raw = _read_input(f"\n{prompt}: ")
        if not raw:
            return None
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        if raw in choices:
            return raw
        sys.stderr.write(
            ("Invalid prompt style. Try again.\n" if lang == "en" else "Prompt 预设无效，请重新输入。\n")
        )


def _cmd_batch(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    bundle = load_content_bundle(resolve_content_dir(args.content_dir))

    hero_id = args.hero or DEFAULT_HERO_ID
    enemy_ids = list(args.enemies) or DEFAULT_ENEMY_IDS
    hero_name = bundle.get_hero(hero_id).display_name.get(lang)
    enemy_names = [
        bundle.get_enemy(enemy_id).display_name.get(lang)
        for enemy_id in enemy_ids
    ]

    def _progress(current: int, total: int) -> None:
        if not args.quiet:
            progress = int(current / total * 40)
            bar = "[" + "#" * progress + "-" * (40 - progress) + "]"
            sys.stdout.write(f"\rProgress: {bar} {current}/{total}")
            sys.stdout.flush()
            if current == total:
                sys.stdout.write("\n")

    if not args.quiet:
        sys.stdout.write(
            f"Running {args.count} battles with {hero_name} vs {', '.join(enemy_names)}\n"
        )
        sys.stdout.write(f"Base seed: {args.seed}\n\n")
        if args.prompt_style:
            sys.stdout.write(f"Prompt style: {args.prompt_style}\n\n")

    result = run_batch(
        bundle,
        hero_id=hero_id,
        enemy_ids=enemy_ids,
        count=args.count,
        base_seed=args.seed,
        max_ticks=args.max_ticks,
        language=lang,
        prompt_style=args.prompt_style,
        progress_callback=_progress if not args.quiet else None,
    )

    if not args.quiet:
        sys.stdout.write("\n")

    summary_lines = result.summary(language=lang)
    sys.stdout.write("\n".join(summary_lines) + "\n")

    return 0


def _cmd_play(args: argparse.Namespace) -> int:
    saved_config = load_config()
    config = _effective_game_config(args, saved_config)
    color_mode = _effective_color_mode(args)
    lang = config.language

    bundle = load_content_bundle(resolve_content_dir(args.content_dir))
    codex_progress = load_codex_progress()
    hero_id = args.hero or DEFAULT_HERO_ID
    hero_data = bundle.get_hero(hero_id)
    build = resolve_build(hero_data, bundle)
    prompt_override = apply_prompt_style(
        hero_data.default_prompt.get(lang),
        args.prompt_style,
        lang,
    )
    primary = build_provider(config, seed=args.seed, force_mock=args.mock, language=lang)
    if args.mock or config.provider == "mock":
        provider = primary
    else:
        provider = FallbackOnErrorProvider(
            primary,
            MockProvider(model="mock-smart", seed=args.seed, language=lang),
        )

    run_id = new_run_id()
    battle_id = new_battle_id(run_id, 1)

    trace_dir = Path(args.trace_dir) if args.trace_dir else None
    trace_cfg = TraceConfig(
        enabled=not args.no_trace,
        directory=trace_dir,  # type: ignore[arg-type]
    )

    loop = BattleLoop(
        bundle,
        provider,
        seed=args.seed,
        language=lang,
        battle_session_id=new_battle_llm_session_id(battle_id),
        hero_prompt_override=prompt_override,
        prompt_style=args.prompt_style,
        codex_progress=codex_progress,
    )
    state = loop.setup(hero_id, DEFAULT_ENEMY_IDS)

    frame_delay = 0.0 if args.no_animation else max(0.0, args.delay)
    use_refresh = not args.no_animation
    term_width = shutil.get_terminal_size((100, 24)).columns

    default_scene = None
    if "dungeon_ember_crypt" in bundle.dungeons:
        default_scene = bundle.dungeons["dungeon_ember_crypt"].scene_text.get(lang)

    with get_terminal(
        refresh=use_refresh,
        clear_screen=use_refresh and sys.stdout.isatty(),
        hide_cursor=use_refresh,
        save_screen=use_refresh,
    ) as term:
        start_screen = render_start_screen(
            config,
            provider_label=provider.name,
            seed=args.seed,
            language=lang,
            width=term_width,
        )
        setup_screen = render_run_setup_screen(
            hero_data,
            bundle,
            build,
            provider_label=provider.name,
            prompt_style=args.prompt_style,
            language=lang,
        )
        briefing_screen = render_encounter_briefing(
            state,
            bundle,
            build,
            language=lang,
            width=term_width,
        )
        if use_refresh:
            term.render(start_screen)
            time.sleep(max(0.35, frame_delay))
            term.render(setup_screen)
            time.sleep(max(0.35, frame_delay))
            term.render(briefing_screen)
            time.sleep(max(0.25, frame_delay))
        else:
            sys.stdout.write(start_screen + "\n\n")
            sys.stdout.write(setup_screen + "\n")
            sys.stdout.write("\n" + briefing_screen + "\n")

        def print_frame(state: BattleState, record: TurnRecord) -> None:
            screen = render_battle_screen(
                state,
                record,
                provider_label=provider.name,
                seed=args.seed,
                unicode_mode=config.unicode_mode,
                language=lang,
                width=term_width,
                enhanced_bars=use_refresh,
                bundle=bundle,
                build=build,
                scene_text=default_scene,
                color_mode=color_mode,
            )

            if use_refresh:
                presented = present_battle_frame(
                    screen,
                    turn_index=len(loop.records) + 1,
                    tick=record.tick,
                    language=lang,
                )
                term.render(presented.text)
            else:
                presented = present_battle_frame(
                    screen,
                    turn_index=len(loop.records) + 1,
                    tick=record.tick,
                    language=lang,
                )
                sys.stdout.write("\n" + presented.text + "\n")

            if frame_delay > 0:
                time.sleep(frame_delay)
                if record.side == "hero":
                    time.sleep(frame_delay)

        def print_thinking_frame(state: BattleState) -> None:
            screen = render_battle_screen(
                state,
                None,
                provider_label=provider.name,
                seed=args.seed,
                unicode_mode=config.unicode_mode,
                language=lang,
                width=term_width,
                enhanced_bars=use_refresh,
                bundle=bundle,
                build=build,
                scene_text=default_scene,
                color_mode=color_mode,
            )
            presented = present_battle_frame(
                screen,
                turn_index=len(loop.records) + 1,
                tick=state.tick,
                thinking=True,
                language=lang,
            )
            if use_refresh:
                term.render(presented.text)
                time.sleep(max(0.25, frame_delay))
            else:
                sys.stdout.write("\n" + presented.text + "\n")

        with TraceWriter(
            run_id=run_id,
            battle_id=battle_id,
            seed=args.seed,
            provider=provider.name,
            model=getattr(provider, "model", config.model),
            battle_session_id=(
                loop.battle_llm_session.battle_session_id
                if loop.battle_llm_session
                else None
            ),
            static_context_hash=(
                loop.battle_llm_session.static_context_hash
                if loop.battle_llm_session
                else None
            ),
            config=trace_cfg,
        ) as trace:

            def on_hero(state: BattleState, record: TurnRecord) -> None:
                trace.write(
                    "hero_turn",
                    tick=record.tick,
                    turn_id=f"{battle_id}_t{record.tick:04d}",
                    battle_session_id=record.battle_session_id,
                    static_context_hash=record.static_context_hash,
                    delta_context_id=record.delta_context_id,
                    delta_context=record.delta_context,
                    prompt_style=args.prompt_style,
                    prompt_template=(
                        prompt_style_text(args.prompt_style, lang)
                        if args.prompt_style
                        else None
                    ),
                    raw_text=record.raw_text,
                    model_narration=(
                        record.validation.narration
                        if record.validation
                        else ""
                    ),
                    model_analysis=(
                        record.validation.analysis
                        if record.validation
                        else ""
                    ),
                    action=record.action.to_dict() if record.action else None,
                    judge={
                        "valid": record.judge.valid if record.judge else False,
                        "reason": record.judge.reason if record.judge else "",
                        "summary": record.judge.summary if record.judge else "",
                        "damage": record.judge.damage if record.judge else 0,
                        "skill_id": record.judge.skill_id if record.judge else None,
                        "target_ids": list(record.judge.target_ids) if record.judge else [],
                    },
                    fallback_reason=(
                        record.validation.fallback_reason.value
                        if record.validation
                        else None
                    ),
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=record.usage_total_tokens,
                    latency_ms=record.usage_latency_ms,
                )
                print_frame(state, record)

            def on_enemy(state: BattleState, record: TurnRecord) -> None:
                trace.write(
                    "enemy_turn",
                    tick=record.tick,
                    actor_id=record.actor_id,
                    action=record.enemy_action,
                )
                print_frame(state, record)
                if frame_delay > 0:
                    time.sleep(1.0)

            loop.run(
                state,
                on_hero_turn=on_hero,
                on_enemy_turn=on_enemy,
                on_hero_thinking=print_thinking_frame,
            )
            trace.write(
                "battle_end",
                result=state.result,
                tick=state.tick,
                hero_hp=state.hero.hp,
                enemy_hp=[e.hp for e in state.enemies],
            )

    record_battle_codex(
        codex_progress,
        bundle,
        DEFAULT_ENEMY_IDS,
        {enemy.id for enemy in state.enemies if not enemy.is_alive},
    )
    codex_save_path = _try_save_codex_progress(codex_progress, lang)

    sys.stdout.write("\n" + label("battle_complete", lang) + "\n")
    result_label_key = {
        "victory": "result_victory",
        "defeat": "result_defeat",
        "timeout": "result_timeout",
        "ongoing": "result_ongoing",
    }.get(state.result, "result_ongoing")
    sys.stdout.write(
        f"{label('result', lang)} : {label(result_label_key, lang)}\n"
    )
    sys.stdout.write(
        "\n" + render_battle_report(state, loop.records, language=lang) + "\n"
    )
    if trace.path is not None:
        sys.stdout.write(f"{label('trace_label', lang)} : {trace.path}\n")
    if codex_save_path is not None:
        sys.stdout.write(f"Codex : {codex_save_path}\n")
    if isinstance(provider, FallbackOnErrorProvider) and provider.error:
        sys.stdout.write(
            f"\nNote: provider '{primary.name}' failed mid-battle and the\n"
            f"      battle finished on the local mock. Reason: {provider.error}\n"
        )
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    """Play a full roguelike run with dungeon traversal.

    This is the main game loop:
    1. Start at dungeon entrance
    2. Choose route (nodes on current floor)
    3. For each node:
       - Combat: fight, get rewards, choose reward
       - Shop: buy items
       - Event/Rest: special interactions
    4. Advance to next floor
    5. Repeat until boss defeated or hero dies
    """
    saved_config = load_config()
    config = _effective_game_config(args, saved_config)
    color_mode = _effective_color_mode(args)
    lang = config.language

    bundle = load_content_bundle(resolve_content_dir(args.content_dir))
    codex_progress = load_codex_progress()
    hero_id = args.hero or DEFAULT_HERO_ID
    dungeon_id = args.dungeon or "dungeon_ember_crypt"

    # Validate dungeon exists
    if dungeon_id not in bundle.dungeons:
        sys.stderr.write(f"error: unknown dungeon '{dungeon_id}'\n")
        sys.stderr.write(f"available dungeons: {', '.join(bundle.dungeons.keys())}\n")
        return 2

    if args.hero is None and not args.auto:
        sys.stdout.write(render_hero_list(bundle, language=lang) + "\n")
        hero_id = _prompt_hero_choice(bundle, lang)

    if args.prompt_style is None and not args.auto:
        sys.stdout.write("\n" + render_prompt_templates(language=lang) + "\n")
        args.prompt_style = _prompt_prompt_style(lang)

    hero_data = bundle.get_hero(hero_id)
    primary = build_provider(config, seed=args.seed, force_mock=args.mock, language=lang)
    if args.mock or config.provider == "mock":
        provider = primary
    else:
        provider = FallbackOnErrorProvider(
            primary,
            MockProvider(model="mock-smart", seed=args.seed, language=lang),
        )

    # Create run state
    run_id = new_run_id()
    battle_counter = 0

    run_state = create_run_state(
        run_id,
        args.seed,
        hero_id,
        dungeon_id,
        bundle,
        codex_progress=codex_progress,
    )
    run_state.strategy_style = args.prompt_style

    trace_dir = Path(args.trace_dir) if args.trace_dir else None
    frame_delay = 0.0 if args.no_animation else max(0.0, args.delay)
    term_width = shutil.get_terminal_size((100, 24)).columns
    use_refresh = not args.no_animation
    storage_warnings: set[str] = set()

    def _prompt_choice(prompt_text: str, max_choice: int, auto: bool = False) -> int:
        """Prompt user for a choice, or auto-select first option."""
        if auto:
            return 0
        while True:
            raw = _read_input(f"\n{prompt_text}: ")
            if raw.isdigit():
                choice = int(raw) - 1
                if 0 <= choice < max_choice:
                    return choice
            sys.stderr.write(f"Invalid choice. Please enter a number between 1 and {max_choice}.\n")

    with get_terminal(
        refresh=use_refresh,
        clear_screen=use_refresh and sys.stdout.isatty(),
        hide_cursor=use_refresh,
        save_screen=use_refresh,
    ) as term:

        def _print_to_term(content: str, clear_previous: bool = True) -> None:
            """Print content using terminal refresh or scrolling."""
            if use_refresh:
                term.render(content, clear_previous=clear_previous)
            else:
                sys.stdout.write(content)
                if not content.endswith("\n"):
                    sys.stdout.write("\n")
                sys.stdout.flush()

        def _run_battle(
            enemy_ids: tuple[str, ...],
            hero_hp: int,
            hero_mp: int,
            scene_text: str | None = None,
        ) -> tuple[str, int, int, list]:
            """Run a single battle.

            Returns:
                (result, final_hp, final_mp, records)
            """
            nonlocal battle_counter
            battle_counter += 1
            battle_id = new_battle_id(run_id, battle_counter)
            current_style = run_state.strategy_style or args.prompt_style
            prompt_override = apply_prompt_style(
                hero_data.default_prompt.get(lang),
                current_style,
                lang,
            )

            trace_cfg = TraceConfig(
                enabled=not args.no_trace,
                directory=trace_dir,
            )

            loop = BattleLoop(
                bundle,
                provider,
                seed=args.seed + battle_counter,
                language=lang,
                battle_session_id=new_battle_llm_session_id(battle_id),
                hero_prompt_override=prompt_override,
                prompt_style=current_style,
                codex_progress=run_state.codex_progress,
            )

            # Setup battle with current hero state
            battle_state = loop.setup(
                hero_id,
                list(enemy_ids),
                item_ids=tuple(run_state.item_ids),
                affix_ids=tuple(run_state.affix_ids),
            )
            # Override HP/MP to carry over from previous battles
            battle_state.hero.hp = hero_hp
            battle_state.hero.max_hp = run_state.max_hp
            battle_state.hero.mp = hero_mp
            battle_state.hero.max_mp = run_state.max_mp
            if run_state.next_battle_shield > 0:
                battle_state.hero.add_status(
                    StatusEffect(
                        id="status_shield",
                        stacks=run_state.next_battle_shield,
                        duration=2,
                    )
                )
                battle_state.emit(
                    "rest_focus_applied",
                    target_id=battle_state.hero.id,
                    shield=run_state.next_battle_shield,
                )
                run_state.next_battle_shield = 0

            # Get current build for battle screen
            current_build = run_state.resolved_build(bundle)
            floor_label = _run_battle_floor_label(run_state, bundle, lang)

            def print_frame(state: BattleState, record: TurnRecord) -> None:
                screen = render_battle_screen(
                    state,
                    record,
                    provider_label=provider.name,
                    seed=args.seed,
                    unicode_mode=config.unicode_mode,
                    language=lang,
                    width=term_width,
                    enhanced_bars=use_refresh,
                    bundle=bundle,
                    build=current_build,
                    scene_text=scene_text,
                    floor_label=floor_label,
                    color_mode=color_mode,
                )

                if use_refresh:
                    presented = present_battle_frame(
                        screen,
                        turn_index=len(loop.records) + 1,
                        tick=record.tick,
                        language=lang,
                    )
                    term.render(presented.text)
                else:
                    presented = present_battle_frame(
                        screen,
                        turn_index=len(loop.records) + 1,
                        tick=record.tick,
                        language=lang,
                    )
                    sys.stdout.write("\n" + presented.text + "\n")

                if frame_delay > 0:
                    time.sleep(frame_delay)
                    if record.side == "hero":
                        time.sleep(frame_delay)

            def print_thinking_frame(state: BattleState) -> None:
                screen = render_battle_screen(
                    state,
                    None,
                    provider_label=provider.name,
                    seed=args.seed,
                    unicode_mode=config.unicode_mode,
                    language=lang,
                    width=term_width,
                    enhanced_bars=use_refresh,
                    bundle=bundle,
                    build=current_build,
                    scene_text=scene_text,
                    floor_label=floor_label,
                    color_mode=color_mode,
                )
                presented = present_battle_frame(
                    screen,
                    turn_index=len(loop.records) + 1,
                    tick=state.tick,
                    thinking=True,
                    language=lang,
                )
                if use_refresh:
                    term.render(presented.text)
                    time.sleep(max(0.25, frame_delay))
                else:
                    sys.stdout.write("\n" + presented.text + "\n")

            with TraceWriter(
                run_id=run_id,
                battle_id=battle_id,
                seed=args.seed + battle_counter,
                provider=provider.name,
                model=getattr(provider, "model", config.model),
                battle_session_id=(
                    loop.battle_llm_session.battle_session_id
                    if loop.battle_llm_session
                    else None
                ),
                static_context_hash=(
                    loop.battle_llm_session.static_context_hash
                    if loop.battle_llm_session
                    else None
                ),
                config=trace_cfg,
            ) as trace:

                def on_hero(state: BattleState, record: TurnRecord) -> None:
                    trace.write(
                        "hero_turn",
                        tick=record.tick,
                        turn_id=f"{battle_id}_t{record.tick:04d}",
                        battle_session_id=record.battle_session_id,
                        static_context_hash=record.static_context_hash,
                        delta_context_id=record.delta_context_id,
                        delta_context=record.delta_context,
                        prompt_style=current_style,
                        prompt_template=(
                            prompt_style_text(current_style, lang)
                            if current_style
                            else None
                        ),
                        raw_text=record.raw_text,
                        model_narration=(
                            record.validation.narration
                            if record.validation
                            else ""
                        ),
                        model_analysis=(
                            record.validation.analysis
                            if record.validation
                            else ""
                        ),
                        action=record.action.to_dict() if record.action else None,
                        judge={
                            "valid": record.judge.valid if record.judge else False,
                            "reason": record.judge.reason if record.judge else "",
                            "summary": record.judge.summary if record.judge else "",
                            "damage": record.judge.damage if record.judge else 0,
                            "skill_id": record.judge.skill_id if record.judge else None,
                            "target_ids": list(record.judge.target_ids) if record.judge else [],
                        },
                        fallback_reason=(
                            record.validation.fallback_reason.value
                            if record.validation
                            else None
                        ),
                        input_tokens=0,
                        output_tokens=0,
                        total_tokens=record.usage_total_tokens,
                        latency_ms=record.usage_latency_ms,
                    )
                    print_frame(state, record)

                def on_enemy(state: BattleState, record: TurnRecord) -> None:
                    trace.write(
                        "enemy_turn",
                        tick=record.tick,
                        actor_id=record.actor_id,
                        action=record.enemy_action,
                    )
                    print_frame(state, record)
                    if frame_delay > 0:
                        time.sleep(1.0)

                loop.run(
                    battle_state,
                    on_hero_turn=on_hero,
                    on_enemy_turn=on_enemy,
                    on_hero_thinking=print_thinking_frame,
                )
                trace.write(
                    "battle_end",
                    result=battle_state.result,
                    tick=battle_state.tick,
                    hero_hp=battle_state.hero.hp,
                    enemy_hp=[e.hp for e in battle_state.enemies],
                )

            # Battle complete
            run_state.record_codex_battle(
                bundle,
                list(enemy_ids),
                {enemy.id for enemy in battle_state.enemies if not enemy.is_alive},
            )
            _try_save_codex_progress(
                run_state.codex_progress,
                lang,
                _print_to_term,
                storage_warnings,
            )
            battle_report = render_battle_report(battle_state, loop.records, language=lang)
            result_label_key = {
                "victory": "result_victory",
                "defeat": "result_defeat",
                "timeout": "result_timeout",
                "ongoing": "result_ongoing",
            }.get(battle_state.result, "result_ongoing")

            battle_complete_content = (
                f"\n{label('battle_complete', lang)}\n"
                f"{label('result', lang)} : {label(result_label_key, lang)}\n"
                f"\n{battle_report}\n"
            )
            if trace.path is not None:
                battle_complete_content += f"{label('trace_label', lang)} : {trace.path}\n"

            _print_to_term(battle_complete_content)

            return battle_state.result, battle_state.hero.hp, battle_state.hero.mp, loop.records

        dungeon = bundle.dungeons[dungeon_id]
        start_screen = render_start_screen(
            config,
            provider_label=provider.name,
            seed=args.seed,
            language=lang,
            width=term_width,
        )
        setup_screen = render_run_setup_screen(
            hero_data,
            bundle,
            run_state.resolved_build(bundle),
            provider_label=provider.name,
            prompt_style=args.prompt_style,
            language=lang,
        )
        run_title = (
            f"\n{label('run_title', lang)}\n"
            f"Run ID: {run_id}\n"
            f"Seed: {args.seed}\n"
            f"Dungeon: {dungeon.display_name.get(lang)}\n"
        )
        if use_refresh:
            _print_to_term(start_screen)
            time.sleep(max(0.4, frame_delay))
            _print_to_term(setup_screen)
            time.sleep(max(0.4, frame_delay))
            _print_to_term(run_title)
        else:
            _print_to_term(start_screen + "\n\n" + setup_screen + "\n" + run_title)

        while run_state.phase not in (RunPhase.COMPLETE, RunPhase.DEAD):
            # Route choice phase
            if run_state.phase == RunPhase.ROUTE_CHOICE:
                route_content = "\n" + "-" * term_width + "\n"
                screen = render_route_choice(run_state, bundle, language=lang, width=term_width)
                route_content += screen + "\n"

                _print_to_term(route_content)

                available = run_state.get_available_nodes(bundle)
                if not available:
                    # No more nodes on this floor, advance
                    if run_state.has_next_floor(bundle):
                        run_state.advance_to_next_floor(bundle)
                        _print_to_term(f"\nAdvancing to Floor {run_state.current_floor_index + 1}...\n")
                    else:
                        run_state.phase = RunPhase.COMPLETE
                    continue

                # Prompt for choice (not using refresh mode for input)
                choice_idx = _prompt_choice(
                    label("route_choice_prompt", lang),
                    len(available),
                    auto=args.auto,
                )
                node_index, node = available[choice_idx]
                run_state.select_node(node_index)

            # Node action phase
            elif run_state.phase == RunPhase.NODE_ACTION:
                node = run_state.current_node(bundle)
                _print_to_term(f"\nEntering: {node.display_name.get(lang)}\n")

                if node.node_type in ("normal_combat", "elite_combat", "boss", "mimic_chest"):
                    # Combat node
                    _print_to_term(f"Node type: {_node_type_label_cli(node.node_type, lang)}\n")
                    if node.risk_level:
                        _print_to_term(f"Risk: {_risk_level_label_cli(node.risk_level, lang)}\n")

                    # Get narrative text
                    dungeon = bundle.dungeons[dungeon_id]
                    scene_text = dungeon.scene_text.get(lang)
                    encounter_intro = node.encounter_intro.get(lang)
                    boss_intro = node.boss_intro.get(lang)

                    # Show narrative
                    if node.is_boss and boss_intro:
                        _print_to_term(
                            _narrative_block(
                                label("narrative_boss", lang),
                                boss_intro,
                                width=term_width,
                            )
                        )
                    elif encounter_intro:
                        _print_to_term(
                            _narrative_block(
                                label("narrative_encounter", lang),
                                encounter_intro,
                                width=term_width,
                            )
                        )

                    # Run battle
                    result, final_hp, final_mp, records = _run_battle(
                        node.enemy_ids,
                        run_state.current_hp,
                        run_state.current_mp,
                        scene_text=scene_text,
                    )

                    # Update run state
                    run_state.end_battle(result, final_hp, final_mp)

                    if result == "victory":
                        # Add rewards
                        if node.rewards:
                            run_state.add_rewards(node.rewards.gold or 0, node.rewards.xp or 0)
                            _print_to_term(f"\nEarned: {node.rewards.gold or 0}g, {node.rewards.xp or 0}xp\n")

                            # Set reward choices if available
                            if node.rewards.reward_choices:
                                run_state.set_reward_choices(node.rewards.reward_choices)
                            else:
                                # No reward choices, just mark node as complete
                                floor = run_state.current_floor(bundle)
                                node_id = floor.nodes[run_state.current_node_index]
                                run_state.visited_node_ids.add(node_id)
                                run_state.completed_node_ids.append(node_id)

                                # Check for next floor
                                available = run_state.get_available_nodes(bundle)
                                if available:
                                    run_state.phase = RunPhase.ROUTE_CHOICE
                                elif run_state.has_next_floor(bundle):
                                    run_state.advance_to_next_floor(bundle)
                                else:
                                    run_state.phase = RunPhase.COMPLETE
                    else:
                        # Defeat or timeout
                        run_state.phase = RunPhase.DEAD

                elif node.node_type == "shop":
                    # Shop node
                    if node.shop_items:
                        run_state.set_shop_items(node.shop_items)
                    else:
                        # No items, just leave
                        run_state.leave_shop(bundle)

                elif node.node_type == "rest":
                    # Rest node
                    run_state.set_rest_phase()

                elif node.node_type == "event":
                    # Event node
                    if node.rewards and node.rewards.reward_choices:
                        run_state.set_event_choices(list(node.rewards.reward_choices))
                    else:
                        # No choices, just mark as complete
                        floor = run_state.current_floor(bundle)
                        node_id = floor.nodes[run_state.current_node_index]
                        run_state.visited_node_ids.add(node_id)
                        run_state.completed_node_ids.append(node_id)

                        available = run_state.get_available_nodes(bundle)
                        if available:
                            run_state.phase = RunPhase.ROUTE_CHOICE
                        elif run_state.has_next_floor(bundle):
                            run_state.advance_to_next_floor(bundle)
                        else:
                            run_state.phase = RunPhase.COMPLETE

                else:
                    # Unknown node type
                    _print_to_term(f"Node type '{node.node_type}' not yet implemented.\n")
                    # Mark as complete
                    floor = run_state.current_floor(bundle)
                    node_id = floor.nodes[run_state.current_node_index]
                    run_state.visited_node_ids.add(node_id)
                    run_state.completed_node_ids.append(node_id)

                    available = run_state.get_available_nodes(bundle)
                    if available:
                        run_state.phase = RunPhase.ROUTE_CHOICE
                    elif run_state.has_next_floor(bundle):
                        run_state.advance_to_next_floor(bundle)
                    else:
                        run_state.phase = RunPhase.COMPLETE

            # Reward choice phase
            elif run_state.phase == RunPhase.REWARD_CHOICE:
                reward_content = "\n" + "-" * term_width + "\n"
                screen = render_reward_choice(run_state, bundle, language=lang, width=term_width)
                reward_content += screen + "\n"

                _print_to_term(reward_content)

                choices = run_state.current_choices
                choice_idx = _prompt_choice(
                    label("reward_choice_prompt", lang),
                    len(choices),
                    auto=args.auto,
                )
                run_state.choose_reward(choice_idx, bundle)
                _try_save_codex_progress(
                    run_state.codex_progress,
                    lang,
                    _print_to_term,
                    storage_warnings,
                )
                _print_to_term(f"\nReward chosen!\n")

            # Shop phase
            elif run_state.phase == RunPhase.SHOP:
                def _render_shop_screen() -> str:
                    return (
                        "\n" + "-" * term_width + "\n"
                        + render_shop(run_state, bundle, language=lang, width=term_width)
                        + "\n"
                    )

                _print_to_term(_render_shop_screen())

                while True:
                    choices = run_state.current_choices
                    prompt = f"{label('shop_prompt', lang)} (1-{len(choices)} or 'l')"

                    if args.auto:
                        # Auto mode: just leave shop
                        _print_to_term(f"\n{label('shop_leave', lang)}\n")
                        run_state.leave_shop(bundle)
                        break

                    raw = _read_input(f"\n{prompt}: ").lower()

                    if raw == "l" or raw == "leave":
                        _print_to_term(f"\n{label('shop_leave', lang)}\n")
                        run_state.leave_shop(bundle)
                        break

                    if raw.isdigit():
                        choice_idx = int(raw) - 1
                        if 0 <= choice_idx < len(choices):
                            item = choices[choice_idx]
                            if run_state.can_afford(item):
                                success = run_state.buy_shop_item(choice_idx, bundle)
                                if success:
                                    _print_to_term(f"\n{label('shop_item_bought', lang)}\n")
                                    # Re-render shop
                                    _print_to_term(_render_shop_screen())
                            else:
                                _print_to_term(f"\n{label('shop_cannot_afford', lang)}\n")
                        else:
                            sys.stderr.write(f"Invalid choice. Please enter a number between 1 and {len(choices)}.\n")
                    else:
                        sys.stderr.write(f"Invalid input. Enter a number or 'l' to leave.\n")

            # Rest phase
            elif run_state.phase == RunPhase.REST:
                def _render_rest_screen() -> str:
                    return (
                        "\n" + "-" * term_width + "\n"
                        + render_rest(run_state, bundle, language=lang, width=term_width)
                        + "\n"
                    )

                _print_to_term(_render_rest_screen())

                if args.auto:
                    # Auto mode: rest and leave
                    _print_to_term(f"\n{label('rest_confirmed', lang)}\n")
                    run_state.apply_rest(option="recover")
                    run_state.leave_rest(bundle)
                    continue

                while True:
                    raw = _read_input(f"\n{label('rest_prompt', lang)}: ").lower()

                    option_map = {
                        "1": "recover",
                        "recover": "recover",
                        "r": "recover",
                        "yes": "recover",
                        "y": "recover",
                        "2": "focus",
                        "focus": "focus",
                        "f": "focus",
                        "3": "study",
                        "study": "study",
                        "s": "study",
                    }
                    if raw in option_map:
                        _print_to_term(f"\n{label('rest_confirmed', lang)}\n")
                        run_state.apply_rest(option=option_map[raw])
                        run_state.leave_rest(bundle)
                        break
                    elif raw == "n" or raw == "no":
                        _print_to_term(f"\n{label('rest_skipped', lang)}\n")
                        run_state.leave_rest(bundle)
                        break
                    else:
                        sys.stderr.write("Invalid input. Enter 1/2/3, or 'n' to skip.\n")

            # Event phase
            elif run_state.phase == RunPhase.EVENT:
                def _render_event_screen() -> str:
                    return (
                        "\n" + "-" * term_width + "\n"
                        + render_event(run_state, bundle, language=lang, width=term_width)
                        + "\n"
                    )

                _print_to_term(_render_event_screen())

                choices = run_state.current_choices
                if not choices:
                    # No choices, just leave
                    run_state.choose_event(0, bundle)
                    continue

                if args.auto:
                    # Auto mode: choose first option
                    _print_to_term(f"\n{label('event_choice_confirmed', lang)}\n")
                    run_state.choose_event(0, bundle)
                    _try_save_codex_progress(
                        run_state.codex_progress,
                        lang,
                        _print_to_term,
                        storage_warnings,
                    )
                    continue

                while True:
                    raw = _read_input(f"\n{label('event_prompt', lang)}: ")

                    if raw.isdigit():
                        choice_idx = int(raw) - 1
                        if 0 <= choice_idx < len(choices):
                            _print_to_term(f"\n{label('event_choice_confirmed', lang)}\n")
                            run_state.choose_event(choice_idx, bundle)
                            _try_save_codex_progress(
                                run_state.codex_progress,
                                lang,
                                _print_to_term,
                                storage_warnings,
                            )
                            break
                        else:
                            sys.stderr.write(f"Invalid choice. Please enter a number between 1 and {len(choices)}.\n")
                    else:
                        sys.stderr.write(f"Invalid input. Enter a number.\n")

            else:
                # Unknown phase
                sys.stderr.write(f"error: unknown phase {run_state.phase}\n")
                return 1

        # Run complete or dead
        run_summary = (
            "\n" + "=" * term_width + "\n"
            + render_run_summary(run_state, bundle, language=lang, width=term_width)
            + "\n"
            + "=" * term_width + "\n"
        )

        _print_to_term(run_summary)
        archive_path, death_path = _try_save_run_records(
            run_state,
            bundle,
            lang,
            _print_to_term,
            storage_warnings,
        )
        if archive_path is not None:
            _print_to_term(f"Run Archive: {archive_path}\n")
        if death_path is not None:
            _print_to_term(f"Death History: {death_path}\n")

        if isinstance(provider, FallbackOnErrorProvider) and provider.error:
            _print_to_term(
                f"\nNote: provider '{primary.name}' failed mid-run and the\n"
                f"      run finished on the local mock. Reason: {provider.error}\n"
            )

        return _run_exit_code(
            run_state,
            strict_result_exit_code=args.strict_result_exit_code,
        )


def _node_type_label_cli(node_type: str, lang: str) -> str:
    """Get a localized label for a node type (for CLI output)."""
    labels = {
        "normal_combat": "route_node_normal",
        "elite_combat": "route_node_elite",
        "boss": "route_node_boss",
        "shop": "route_node_shop",
        "event": "route_node_event",
        "rest": "route_node_rest",
        "mimic_chest": "route_node_elite",
    }
    key = labels.get(node_type, "route_node_normal")
    from ouro_agent.i18n import label
    return label(key, lang)


def _narrative_block(title: str, text: str, *, width: int) -> str:
    body_width = max(40, width - 4)
    wrapped = textwrap.wrap(
        text,
        width=body_width,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [text]
    lines = ["", f"== {title} =="]
    lines.extend(f"\"{line}\"" for line in wrapped)
    return "\n".join(lines) + "\n"


def _risk_level_label_cli(risk_level: str, lang: str) -> str:
    """Get a localized label for a risk level (for CLI output)."""
    from ouro_agent.i18n import label
    labels = {
        "low": "route_risk_low",
        "medium": "route_risk_medium",
        "high": "route_risk_high",
        "safe": "route_risk_safe",
    }
    key = labels.get(risk_level, "route_risk_low")
    return label(key, lang)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
