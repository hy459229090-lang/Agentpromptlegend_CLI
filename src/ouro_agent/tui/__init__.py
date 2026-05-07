"""Terminal presentation. ASCII-safe by default."""
from ouro_agent.tui.screens import (
    render_battle_report,
    render_battle_screen,
    render_config_screen,
    render_event,
    render_hero_card,
    render_hero_list,
    render_main_menu,
    render_prompt_templates,
    render_rest,
    render_route_choice,
    render_reward_choice,
    render_shop,
    render_run_summary,
)
from ouro_agent.tui.terminal import Terminal, get_terminal

__all__ = [
    "render_battle_report",
    "render_battle_screen",
    "render_config_screen",
    "render_event",
    "render_hero_card",
    "render_hero_list",
    "render_main_menu",
    "render_prompt_templates",
    "render_rest",
    "render_route_choice",
    "render_reward_choice",
    "render_shop",
    "render_run_summary",
    "Terminal",
    "get_terminal",
]
