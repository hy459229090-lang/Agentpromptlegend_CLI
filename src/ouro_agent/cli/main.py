"""Ouro Agent CLI entrypoint.

Subcommands:
* ``ouro --version``
* ``ouro config show``
* ``ouro config set <field> <value>``
* ``ouro play --mock [--seed N] [--no-trace] [--unicode]``
* ``ouro validate-content``
* ``ouro doctor`` (placeholder)

The CLI never resolves combat or stores keys. It composes pieces from the
other modules.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from ouro_agent import __version__
from ouro_agent.config import (
    OuroConfig,
    config_path,
    load_config,
    redacted_view,
    save_config,
    set_field,
)
from ouro_agent.config.model import ConfigError, SUPPORTED_PROVIDERS
from ouro_agent.content import ContentError, load_content_bundle
from ouro_agent.engine.battle import BattleLoop, TurnRecord
from ouro_agent.engine.models import BattleState
from ouro_agent.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, label
from ouro_agent.providers import (
    FallbackOnErrorProvider,
    MockProvider,
    build_provider,
)
from ouro_agent.providers.base import ProviderError
from ouro_agent.sessions import new_battle_id, new_run_id
from ouro_agent.trace import TraceConfig, TraceWriter
from ouro_agent.tui import render_battle_screen, render_config_screen
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

from ouro_agent.engine import resolve_build
from ouro_agent.tui.screens import render_hero_card, render_hero_list

DEFAULT_CONTENT_DIR = "content"
DEFAULT_HERO_ID = "hero_shadow_apprentice"
DEFAULT_ENEMY_IDS = ["enemy_hungry_cultist", "enemy_black_candle_acolyte"]


def main(argv: list[str] | None = None) -> int:
    _ensure_utf8_stdout()
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command is None:
            parser.print_help()
            return 0
        return args.handler(args)
    except (ConfigError, ContentError, ProviderError) as err:
        sys.stderr.write(f"error: {err}\n")
        return 2


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

    # config
    config = sub.add_parser("config", help="View or change configuration")
    config_sub = config.add_subparsers(dest="config_command")
    cfg_show = config_sub.add_parser("show", help="Show current configuration")
    cfg_show.set_defaults(handler=_cmd_config_show)
    cfg_set = config_sub.add_parser("set", help="Set a configuration field")
    cfg_set.add_argument("field")
    cfg_set.add_argument("value")
    cfg_set.set_defaults(handler=_cmd_config_set)
    config.set_defaults(handler=_cmd_config_show)

    # play
    play = sub.add_parser("play", help="Play a battle")
    play.add_argument("--mock", action="store_true", help="Force the mock provider")
    play.add_argument("--seed", type=int, default=1)
    play.add_argument("--no-trace", action="store_true")
    play.add_argument("--unicode", action="store_true")
    play.add_argument(
        "--hero",
        default=DEFAULT_HERO_ID,
        help="Hero id to use (see 'ouro list-heroes')",
    )
    play.add_argument(
        "--content-dir",
        default=DEFAULT_CONTENT_DIR,
        help="Path to content/ root (defaults to ./content)",
    )
    play.add_argument(
        "--trace-dir",
        default=None,
        help="Override trace output directory (defaults to ~/.ouro_agent/traces)",
    )
    play.set_defaults(handler=_cmd_play)

    # list-heroes
    listh = sub.add_parser("list-heroes", help="List all heroes")
    listh.add_argument("--content-dir", default=DEFAULT_CONTENT_DIR)
    listh.set_defaults(handler=_cmd_list_heroes)

    # hero-card
    card = sub.add_parser("hero-card", help="Show a single hero detail card")
    card.add_argument("hero_id")
    card.add_argument("--content-dir", default=DEFAULT_CONTENT_DIR)
    card.set_defaults(handler=_cmd_hero_card)

    # validate-content
    validate = sub.add_parser("validate-content", help="Validate content/ directory")
    validate.add_argument("--content-dir", default=DEFAULT_CONTENT_DIR)
    validate.set_defaults(handler=_cmd_validate_content)

    # doctor
    doctor = sub.add_parser("doctor", help="Run install + config sanity checks")
    doctor.set_defaults(handler=_cmd_doctor)

    return parser


def _resolve_lang(args: argparse.Namespace, config: OuroConfig) -> str:
    return getattr(args, "lang", None) or config.language or DEFAULT_LANGUAGE


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


def _cmd_list_heroes(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    bundle = load_content_bundle(Path(args.content_dir))
    sys.stdout.write(render_hero_list(bundle, language=lang) + "\n")
    return 0


def _cmd_hero_card(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    bundle = load_content_bundle(Path(args.content_dir))
    hero = bundle.get_hero(args.hero_id)
    build = resolve_build(hero, bundle)
    sys.stdout.write(render_hero_card(hero, bundle, build, language=lang) + "\n")
    return 0


def _cmd_validate_content(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    report = validate_content_dir(Path(args.content_dir))
    sys.stdout.write(report.render(language=lang) + "\n")
    return 0 if report.ok else 3


def _cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config()
    sys.stdout.write(f"ouro version : {__version__}\n")
    sys.stdout.write(f"config path  : {config_path()}\n")
    sys.stdout.write(f"provider     : {config.provider}\n")
    sys.stdout.write(f"model        : {config.model}\n")
    sys.stdout.write(f"language     : {config.language}\n")
    if config.api_key_env:
        present = bool(os.environ.get(config.api_key_env))
        sys.stdout.write(
            f"env var      : {config.api_key_env} = "
            + ("set" if present else "MISSING")
            + "\n"
        )
    else:
        sys.stdout.write("env var      : (not configured; mock works without it)\n")
    sys.stdout.write("supported    : " + ", ".join(SUPPORTED_PROVIDERS) + "\n")
    return 0


def _cmd_play(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    if args.mock:
        config = OuroConfig(
            provider="mock",
            model=config.model or "mock-smart",
            api_key_env="",
            base_url="",
            api_version="",
            timeout_seconds=config.timeout_seconds,
            max_retries=config.max_retries,
            trace_level=config.trace_level,
            unicode_mode=args.unicode or config.unicode_mode,
            language=lang,
        )

    bundle = load_content_bundle(Path(args.content_dir))
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

    loop = BattleLoop(bundle, provider, seed=args.seed, language=lang)
    hero_id = args.hero or DEFAULT_HERO_ID
    state = loop.setup(hero_id, DEFAULT_ENEMY_IDS)

    last_record_holder: dict[str, TurnRecord | None] = {"v": None}
    with TraceWriter(
        run_id=run_id,
        battle_id=battle_id,
        seed=args.seed,
        provider=provider.name,
        model=getattr(provider, "model", config.model),
        config=trace_cfg,
    ) as trace:

        def on_hero(state: BattleState, record: TurnRecord) -> None:
            last_record_holder["v"] = record
            trace.write(
                "hero_turn",
                tick=record.tick,
                turn_id=f"{battle_id}_t{record.tick:04d}",
                raw_text=record.raw_text,
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

        def on_enemy(state: BattleState, record: TurnRecord) -> None:
            last_record_holder["v"] = record
            trace.write(
                "enemy_turn",
                tick=record.tick,
                actor_id=record.actor_id,
                action=record.enemy_action,
            )

        loop.run(state, on_hero_turn=on_hero, on_enemy_turn=on_enemy)
        trace.write(
            "battle_end",
            result=state.result,
            tick=state.tick,
            hero_hp=state.hero.hp,
            enemy_hp=[e.hp for e in state.enemies],
        )

    screen = render_battle_screen(
        state,
        last_record_holder["v"],
        provider_label=provider.name,
        seed=args.seed,
        unicode_mode=config.unicode_mode,
        language=lang,
    )
    sys.stdout.write(screen + "\n")
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
    if trace.path is not None:
        sys.stdout.write(f"{label('trace_label', lang)} : {trace.path}\n")
    if isinstance(provider, FallbackOnErrorProvider) and provider.error:
        sys.stdout.write(
            f"\nNote: provider '{primary.name}' failed mid-battle and the\n"
            f"      battle finished on the local mock. Reason: {provider.error}\n"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
