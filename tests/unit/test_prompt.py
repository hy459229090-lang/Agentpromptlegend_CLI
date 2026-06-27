from __future__ import annotations

from pathlib import Path

from ouro_agent.content import load_content_bundle
from ouro_agent.engine.battle import BattleLoop
from ouro_agent.llm.prompt import compose_prompt
from ouro_agent.providers.mock import MockProvider


def test_prompt_injects_visible_identity_build_battle_and_player_prompt(content_root: Path):
    """REQ-LLM-003: prompt context exposes only model-visible tactical data."""
    bundle = load_content_bundle(content_root)
    loop = BattleLoop(
        bundle,
        MockProvider(seed=1, language="en"),
        seed=1,
        language="en",
        hero_prompt_override="Player plan: deny chants before spending damage.",
        prompt_style="control",
    )
    state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_black_candle_acolyte"],
        item_ids=("item_iron_bracer",),
        affix_ids=("affix_iron_will",),
    )

    prompt = compose_prompt(
        state,
        bundle,
        hero_prompt_override="Player plan: deny chants before spending damage.",
        battle_session=loop.battle_llm_session,
        prompt_style="control",
    )
    static = prompt.static_context
    system_text = prompt.system_text()
    user_text = prompt.user_text()

    assert static["hero"]["id"] == "hero_shadow_apprentice"
    assert "deny chants" in static["hero"]["prompt"]
    assert static["build"]["archetype"] == "Black Candle Interrupt"
    assert static["build"]["items"][0]["id"] == "item_iron_bracer"
    assert static["build"]["affixes"][0]["id"] == "affix_iron_will"
    assert static["build"]["stage_badge"].startswith("[")
    assert any(skill["id"] == "skill_hex_seal" for skill in static["skills"])
    assert static["enemies"][0]["id"] == "enemy_black_candle_acolyte"
    assert "A robed acolyte mid-chant" in system_text
    assert "Output schema" in system_text
    assert "Hero prompt:" in user_text
    assert "Battle snapshot / turn delta" in user_text
    assert prompt.delta_context["hero_delta"]["hp"] == state.hero.hp

    assert "Build hint: control/interrupt" not in system_text
    assert "attack_chance" not in system_text
    assert "chant_damage" not in system_text

