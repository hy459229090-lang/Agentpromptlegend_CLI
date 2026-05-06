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
import shutil
import sys
import time
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
from ouro_agent.content import ContentError, load_content_bundle
from ouro_agent.engine.battle import BattleLoop, TurnRecord
from ouro_agent.engine.models import BattleState
from ouro_agent.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, label
from ouro_agent.llm.prompt import apply_prompt_style, supported_prompt_styles
from ouro_agent.llm.prompt import prompt_style_text
from ouro_agent.providers import (
    FallbackOnErrorProvider,
    MockProvider,
    build_provider,
)
from ouro_agent.providers.base import ProviderError
from ouro_agent.sessions import new_battle_id, new_battle_llm_session_id, new_run_id
from ouro_agent.trace import TraceConfig, TraceWriter
from ouro_agent.tui import (
    render_battle_report,
    render_battle_screen,
    render_config_screen,
    render_main_menu,
    render_prompt_templates,
)
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
            return _cmd_menu(args)
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

    # menu
    menu = sub.add_parser("menu", help="Show game status and entry commands")
    menu.set_defaults(handler=_cmd_menu)

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
        default=0.0,
        help="Seconds to wait after each turn frame (default: 0).",
    )
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
    play.add_argument(
        "--prompt-style",
        choices=supported_prompt_styles(),
        default=None,
        help="Apply a strategy template to this battle.",
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
    card.add_argument("--prompt-style", choices=supported_prompt_styles(), default=None)
    card.set_defaults(handler=_cmd_hero_card)

    templates = sub.add_parser(
        "prompt-templates", help="List strategy templates for hero prompts"
    )
    templates.set_defaults(handler=_cmd_prompt_templates)

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
    raw = input(f"{prompt}{suffix}: ").strip()
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
    bundle = load_content_bundle(Path(args.content_dir))
    sys.stdout.write(render_hero_list(bundle, language=lang) + "\n")
    return 0


def _cmd_hero_card(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    bundle = load_content_bundle(Path(args.content_dir))
    hero = bundle.get_hero(args.hero_id)
    build = resolve_build(hero, bundle)
    sys.stdout.write(
        render_hero_card(
            hero,
            bundle,
            build,
            language=lang,
            prompt_style=args.prompt_style,
        )
        + "\n"
    )
    return 0


def _cmd_prompt_templates(args: argparse.Namespace) -> int:
    config = load_config()
    lang = _resolve_lang(args, config)
    sys.stdout.write(render_prompt_templates(language=lang) + "\n")
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
    hero_id = args.hero or DEFAULT_HERO_ID
    hero_data = bundle.get_hero(hero_id)
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
    )
    state = loop.setup(hero_id, DEFAULT_ENEMY_IDS)

    frame_delay = 0.0 if args.no_animation else max(0.0, args.delay)

    def print_frame(state: BattleState, record: TurnRecord) -> None:
        screen = render_battle_screen(
            state,
            record,
            provider_label=provider.name,
            seed=args.seed,
            unicode_mode=config.unicode_mode,
            language=lang,
            width=shutil.get_terminal_size((100, 24)).columns,
        )
        sys.stdout.write(
            f"\n--- turn {len(loop.records) + 1} / tick {record.tick} ---\n"
        )
        sys.stdout.write(screen + "\n")
        if frame_delay > 0:
            time.sleep(frame_delay)

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

        loop.run(state, on_hero_turn=on_hero, on_enemy_turn=on_enemy)
        trace.write(
            "battle_end",
            result=state.result,
            tick=state.tick,
            hero_hp=state.hero.hp,
            enemy_hp=[e.hp for e in state.enemies],
        )

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
    if isinstance(provider, FallbackOnErrorProvider) and provider.error:
        sys.stdout.write(
            f"\nNote: provider '{primary.name}' failed mid-battle and the\n"
            f"      battle finished on the local mock. Reason: {provider.error}\n"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
