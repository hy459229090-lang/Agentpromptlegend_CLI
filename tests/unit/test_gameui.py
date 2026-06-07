"""Slice C-GameUI: character poses, sprites, and build joy."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.content import load_content_bundle
from ouro_agent.engine import resolve_build
from ouro_agent.engine.battle import BattleLoop, TurnRecord
from ouro_agent.engine.judge import JudgeOutcome
from ouro_agent.llm.actions import HeroAction
from ouro_agent.providers.mock import MockProvider
from ouro_agent.sessions.run_state import create_run_state


@pytest.fixture()
def bundle(content_root: Path):
    return load_content_bundle(content_root)


def test_actor_pose_idle():
    from ouro_agent.tui.screens import _actor_pose

    pose = _actor_pose("hero_shadow_apprentice", None)
    assert pose == "idle"


def test_actor_pose_attack(bundle):
    from ouro_agent.tui.screens import _actor_pose

    record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(type="basic_attack", targets=("enemy_hungry_cultist",)),
        judge=JudgeOutcome(
            valid=True,
            reason="basic_attack resolved",
            summary="basic_attack -> enemy_hungry_cultist | 10 dmg",
            damage=10,
            target_ids=("enemy_hungry_cultist",),
            action_kind="basic_attack",
        ),
        battle_session_id="test",
        static_context_hash="ctx_test",
        delta_context_id="test_d0001",
    )

    pose = _actor_pose("hero_shadow_apprentice", record)
    assert pose == "attack"


def test_actor_pose_skill_cast(bundle):
    from ouro_agent.tui.screens import _actor_pose

    record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(type="cast_skill", skill_id="skill_shadow_sting", targets=("enemy_hungry_cultist",)),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary="cast_skill skill_shadow_sting -> enemy_hungry_cultist | 12 dmg",
            damage=12,
            target_ids=("enemy_hungry_cultist",),
            skill_id="skill_shadow_sting",
            action_kind="cast_skill",
        ),
        battle_session_id="test",
        static_context_hash="ctx_test",
        delta_context_id="test_d0001",
    )

    pose = _actor_pose("hero_shadow_apprentice", record)
    assert pose == "skill_shadow"


def test_actor_pose_handles_enemy_director_states_and_self_target_guard():
    from ouro_agent.tui.screens import _actor_pose

    enemy_strike = TurnRecord(
        tick=12,
        actor_id="enemy_hungry_cultist",
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "attack", "damage": 9},
    )
    assert _actor_pose("hero_shadow_apprentice", enemy_strike) == "hit"
    assert _actor_pose("enemy_hungry_cultist", enemy_strike) == "attack"

    charge = TurnRecord(
        tick=14,
        actor_id="enemy_black_candle_acolyte",
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "chant_charge"},
    )
    assert _actor_pose("enemy_black_candle_acolyte", charge) == "skill"

    broken = TurnRecord(
        tick=16,
        actor_id="enemy_black_candle_acolyte",
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "silenced"},
    )
    assert _actor_pose("enemy_black_candle_acolyte", broken) == "break"

    self_guard = TurnRecord(
        tick=18,
        actor_id="hero_ash_guardian",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_tower_brace",
            targets=("hero_ash_guardian", "enemy_black_candle_high_priest_archive"),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary="cast_skill skill_tower_brace -> hero_ash_guardian,enemy_black_candle_high_priest_archive | 25 dmg",
            damage=25,
            target_ids=("hero_ash_guardian", "enemy_black_candle_high_priest_archive"),
            skill_id="skill_tower_brace",
            action_kind="cast_skill",
        ),
    )
    assert _actor_pose("hero_ash_guardian", self_guard) == "defend"


def test_hero_sprite_returns_lines(bundle):
    from ouro_agent.tui.screens import _hero_sprite

    loop = BattleLoop(bundle, MockProvider(seed=1), seed=1)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    hero = state.hero

    sprite = _hero_sprite(hero, None)
    assert isinstance(sprite, list)
    assert len(sprite) >= 3
    assert any(".^." in line or "candle" in line.lower() for line in sprite)


def test_enemy_sprite_returns_lines(bundle):
    from ouro_agent.tui.screens import _enemy_sprite

    loop = BattleLoop(bundle, MockProvider(seed=1), seed=1)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    enemy = state.enemies[0]

    sprite = _enemy_sprite(enemy, None)
    assert isinstance(sprite, list)
    assert len(sprite) >= 3
    assert any("(c)" in line or "hungry" in line.lower() for line in sprite)


def test_route_reward_shop_rest_screens_show_decision_context(bundle):
    from ouro_agent.tui.screens import (
        render_rest,
        render_reward_choice,
        render_route_choice,
        render_shop,
    )

    state = create_run_state(
        "run_ui",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )

    state.current_floor_index = 2
    route = render_route_choice(state, bundle, language="en", width=100)
    assert "[PATH]" in route
    assert "ROUTE MAP" in route
    assert "ROUTE DIRECTOR BOARD" in route
    assert "Branch pressure:" in route
    assert "##==>##" in route or "##XX##" in route
    assert "Decision:" in route
    assert "Cost:" in route
    assert "Reward:" in route
    assert "Build fit:" in route
    assert "chant threat" in route
    assert "[REC]" in route or "[DANGER]" in route or "[FLEX]" in route
    compact_route = render_route_choice(state, bundle, language="en", width=80)
    assert "ROUTE DIRECTOR BOARD" in compact_route
    assert max(len(line) for line in compact_route.splitlines()) <= 80

    state.current_floor_index = 0
    state.current_node_index = 0
    node = state.current_node(bundle)
    state.set_reward_choices(list(node.rewards.reward_choices))
    reward = render_reward_choice(state, bundle, language="en", width=100)
    assert "[REWARD]" in reward
    assert "[SEED] -> [PAIR] -> [ONLINE]" in reward
    assert "REWARD BUILD TRACK" in reward
    assert "PICK PRIORITY BOARD" in reward
    assert "Current: [ONLINE] Online" in reward
    assert "[1] [ONLINE] => [ONLINE] | tags shadow 5->6" in reward
    assert "[2] [ONLINE] => [ONLINE] | tags corruption 1->2, shadow 5->6" in reward
    assert "[3] [CODEX] => [+1 STUDY] | prompt intel" in reward
    assert "[1] CORE" in reward
    assert "[2] CORE" in reward
    assert "[3] INFO" in reward
    assert "Build before/after" in reward
    assert "Stat delta" in reward
    assert "Tag delta:" in reward
    assert "AI impact:" in reward
    assert "push HIGH ROLL" in reward
    assert "push resonance online" not in reward
    assert "[REST]  ##+##" not in reward

    state.current_floor_index = 1
    state.current_node_index = 0
    node = state.current_node(bundle)
    state.set_reward_choices(list(node.rewards.reward_choices))
    cross_reward = render_reward_choice(state, bundle, language="en", width=100)
    assert "Cross-build seed:" in cross_reward

    state.current_floor_index = 1
    state.current_node_index = 1
    state.set_shop_items(list(state.current_node(bundle).shop_items))
    state.gold = 25
    shop = render_shop(state, bundle, language="en", width=100)
    assert "[SHOP]" in shop
    assert "##[]##" in shop
    assert "SHOP FIX BOARD" in shop
    assert "BUDGET TACTICS BOARD" in shop
    assert "Lanes: RECOVER / BUILD / PROMPT / SCOUT" in shop
    assert "[1] RECOVER 12g READY => HP +35%, MP full" in shop
    assert "[3] BUILD 14g READY => Build tags control 2->3, shadow 5->6" in shop
    assert "[4] PROMPT 10g READY => Prompt style control" in shop
    assert "[5] SCOUT 8g READY => Boss clue / route intel" in shop
    assert "Wallet: 25g" in shop
    assert "[1] BUY   RECOVER 12g -> 13g" in shop
    assert "[5] BUY   SCOUT 8g -> 17g" in shop
    assert "Build before/after" in shop
    assert "AI impact:" in shop
    assert "Decision: changes model bias" in shop
    assert "Restore MP to full" in shop
    assert "Boss clue:" in shop

    state.current_node_index = 2
    state.current_hp = max(1, state.max_hp // 3)
    state.current_mp = 0
    state.set_rest_phase()
    rest = render_rest(state, bundle, language="en", width=100)
    assert "[REST]" in rest
    assert "recover / focus / study" in rest
    assert "Rest preview" in rest
    assert "Decision pressure: high" in rest
    assert "REST DECISION RING" in rest
    assert "REST PRIORITY BOARD" in rest
    assert "[1] PICK RECOVER | HP 33->63 / MP 0->72" in rest
    assert "[2] FLEX FOCUS" in rest
    assert "[3] LOW  STUDY" in rest
    assert "[1] RECOVER => HP/MP repair | stabilize the run" in rest
    assert "HP 33->63 / MP 0->72" in rest
    assert "[2] FOCUS   => SHD 12 next battle | absorb pressure" in rest
    assert "[3] STUDY   => scout note | reduce unknown risk" in rest
    assert "[1] Recover" in rest
    assert "[2] Focus" in rest
    assert "[3] Study" in rest


def test_route_choice_shows_pixel_route_map_with_visited_nodes(bundle):
    from ouro_agent.i18n import visual_width
    from ouro_agent.tui.screens import render_route_choice

    state = create_run_state(
        "run_route_map",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    state.current_floor_index = 1
    state.visited_node_ids.add("node_ember_crypt_f2_n1")

    route = render_route_choice(state, bundle, language="en", width=100)

    assert "ROUTE MAP" in route
    assert "ROUTE DIRECTOR BOARD" in route
    assert "Legend: C combat" in route
    assert "[X:C] [M] Rat Pack" in route
    assert "[1:$] [$] Black Candle Merchant" in route
    assert "[2:+] [+] Candle Shrine" in route
    assert "[1] FIX" in route
    assert "[2] FIX" in route
    assert "Branch pressure: 2 choices" in route
    assert "+-->" in route
    assert "|-->" in route
    for width in (80, 100):
        compact = render_route_choice(state, bundle, language="en", width=width)
        assert "ROUTE DIRECTOR BOARD" in compact
        assert all(visual_width(line) <= width for line in compact.splitlines())

    zh_route = render_route_choice(state, bundle, language="zh", width=80)
    assert "路线导演板" in zh_route
    assert all(visual_width(line) <= 80 for line in zh_route.splitlines())


def test_reward_choice_build_track_stays_width_stable(bundle):
    from ouro_agent.i18n import visual_width
    from ouro_agent.tui.screens import render_reward_choice

    state = create_run_state(
        "run_reward_track",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    state.current_floor_index = 0
    state.current_node_index = 0
    state.set_reward_choices(list(state.current_node(bundle).rewards.reward_choices))

    for width in (80, 100, 120):
        reward = render_reward_choice(state, bundle, language="en", width=width)
        assert "REWARD BUILD TRACK" in reward
        assert "PICK PRIORITY BOARD" in reward
        assert "CORE" in reward
        assert "INFO" in reward
        assert all(visual_width(line) <= width for line in reward.splitlines())

    zh_reward = render_reward_choice(state, bundle, language="zh", width=80)
    assert "奖励 Build 轨道" in zh_reward
    assert "选择优先级面板" in zh_reward
    assert "主标签" in zh_reward
    assert "提示词情报" in zh_reward
    assert all(visual_width(line) <= 80 for line in zh_reward.splitlines())


def test_shop_fix_board_tracks_affordability_and_lanes(bundle):
    from ouro_agent.i18n import visual_width
    from ouro_agent.tui.screens import render_shop

    state = create_run_state(
        "run_shop_fix",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    state.current_floor_index = 1
    state.current_node_index = 1
    state.set_shop_items(list(state.current_node(bundle).shop_items))
    state.gold = 9

    shop = render_shop(state, bundle, language="en", width=100)

    assert "SHOP FIX BOARD" in shop
    assert "BUDGET TACTICS BOARD" in shop
    assert "[1] RECOVER 12g LOCKED => HP +35%, MP full" in shop
    assert "[1] WAIT   RECOVER 12g | short 3g" in shop
    assert "[4] PROMPT 10g LOCKED => Prompt style control" in shop
    assert "[4] WAIT   PROMPT 10g | short 1g" in shop
    assert "[5] SCOUT 8g READY => Boss clue / route intel" in shop
    assert "[5] BUY   SCOUT 8g -> 1g" in shop
    for width in (80, 100, 120):
        compact = render_shop(state, bundle, language="en", width=width)
        assert "BUDGET TACTICS BOARD" in compact
        assert all(visual_width(line) <= width for line in compact.splitlines())

    zh_shop = render_shop(state, bundle, language="zh", width=80)
    assert "商店修正面板" in zh_shop
    assert "预算战术面板" in zh_shop
    assert "缺 3g" in zh_shop
    assert all(visual_width(line) <= 80 for line in zh_shop.splitlines())


def test_rest_decision_ring_shows_three_mutually_exclusive_outcomes(bundle):
    from ouro_agent.i18n import visual_width
    from ouro_agent.tui.screens import render_rest

    state = create_run_state(
        "run_rest_ring",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    state.current_floor_index = 1
    state.current_node_index = 2
    state.current_hp = max(1, state.max_hp // 3)
    state.current_mp = 0
    state.set_rest_phase()

    rest = render_rest(state, bundle, language="en", width=100)

    assert "REST DECISION RING" in rest
    assert "REST PRIORITY BOARD" in rest
    assert "[1] PICK RECOVER | HP 33->63 / MP 0->72" in rest
    assert "[1] RECOVER => HP/MP repair | stabilize the run" in rest
    assert "[2] FOCUS   => SHD 12 next battle | absorb pressure" in rest
    assert "[3] STUDY   => scout note | reduce unknown risk" in rest
    for width in (80, 100, 120):
        compact = render_rest(state, bundle, language="en", width=width)
        assert "REST PRIORITY BOARD" in compact
        assert all(visual_width(line) <= width for line in compact.splitlines())

    zh_rest = render_rest(state, bundle, language="zh", width=80)
    assert "休整决策环" in zh_rest
    assert "休整优先级面板" in zh_rest
    assert "[1] PICK RECOVER" in zh_rest
    assert all(visual_width(line) <= 80 for line in zh_rest.splitlines())


def test_event_fate_board_summarizes_event_outcomes(bundle):
    from ouro_agent.i18n import visual_width
    from ouro_agent.tui.screens import render_event

    state = create_run_state(
        "run_event_fate",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    state.current_floor_index = 2
    state.current_node_index = 1
    state.current_hp = state.max_hp // 2
    state.set_event_choices(list(state.current_node(bundle).rewards.reward_choices))

    event = render_event(state, bundle, language="en", width=100)

    assert "EVENT FATE BOARD" in event
    assert "EVENT RISK BOARD" in event
    assert "[1] BUILD => tags hunter 0->1" in event
    assert "[2] GOLD  => +50 shop power" in event
    assert "[3] HEAL  => HP 50->100" in event
    assert "[1] GREED => pivot tags hunter 0->1" in event
    assert "[2] GREED => funds shop fixes" in event
    assert "[3] SAFE  => HP line is stressed" in event
    assert "[REWARD] [SEED] -> [PAIR] -> [ONLINE]" in event
    assert "[PATH]  ##==>##" not in event
    for width in (80, 100, 120):
        compact = render_event(state, bundle, language="en", width=width)
        assert "EVENT RISK BOARD" in compact
        assert all(visual_width(line) <= width for line in compact.splitlines())

    zh_event = render_event(state, bundle, language="zh", width=80)
    assert "事件命运板" in zh_event
    assert "事件风险面板" in zh_event
    assert "血线有压力" in zh_event
    assert all(visual_width(line) <= 80 for line in zh_event.splitlines())


def test_run_summary_shows_result_board_for_retry_decision(bundle):
    from ouro_agent.i18n import visual_width
    from ouro_agent.sessions import RunPhase
    from ouro_agent.tui.screens import render_run_summary

    state = create_run_state(
        "run_result_board",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    state.phase = RunPhase.DEAD
    state.battles_won = 3
    state.battles_lost = 1
    state.current_hp = 0
    state.current_mp = 4
    state.completed_node_ids.extend(
        [
            "node_ember_crypt_f1_n1",
            "node_ember_crypt_f2_n1",
            "node_ember_crypt_f2_n2",
        ]
    )

    summary = render_run_summary(state, bundle, language="en", width=100)

    assert "RUN RESULT BOARD" in summary
    assert "RETRY LOADOUT BOARD" in summary
    assert "[FALL] Result: dead | Floor 1 | Nodes 3" in summary
    assert "Combat: 3W/1L | Resources HP 0/100 MP 4/72" in summary
    assert "Build: [ONLINE] Online | Black Candle Interrupt" in summary
    assert "Next: review route/rest timing and prompt style before retry" in summary
    assert "[PROMPT] control / slow enemy tempo" in summary
    assert "[SEED] 8 / fixed retry sample" in summary
    assert "[ROUTE] rest/shop before boss pressure" in summary
    for width in (80, 100, 120):
        compact = render_run_summary(state, bundle, language="en", width=width)
        assert "RETRY LOADOUT BOARD" in compact
        assert all(visual_width(line) <= width for line in compact.splitlines())

    state.phase = RunPhase.COMPLETE
    complete = render_run_summary(state, bundle, language="en", width=100)
    assert "[WIN] Result: complete" in complete
    assert "Next: raise risk, try a new hero, or chase HIGH ROLL" in complete
    assert "[PROMPT] guarded / validate" in complete
    assert "[ROUTE] elite/event greed line" in complete


def test_selectable_surfaces_share_card_rules_and_status_details(bundle):
    """REQ-ART-003: choice objects use one card grammar; status IDs stay in details."""
    from ouro_agent.engine.models import StatusEffect
    from ouro_agent.i18n import visual_width
    from ouro_agent.tui.screens import (
        render_battle_report,
        render_battle_screen,
        render_hero_list,
        render_rest,
        render_reward_choice,
        render_route_choice,
        render_shop,
    )

    state = create_run_state(
        "run_art003",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    state.current_floor_index = 2
    route = render_route_choice(state, bundle, language="en", width=100)

    state.current_floor_index = 0
    state.current_node_index = 0
    node = state.current_node(bundle)
    state.set_reward_choices(list(node.rewards.reward_choices))
    reward = render_reward_choice(state, bundle, language="en", width=100)

    state.current_floor_index = 1
    state.current_node_index = 1
    state.set_shop_items(list(state.current_node(bundle).shop_items))
    state.gold = 25
    shop = render_shop(state, bundle, language="en", width=100)

    state.current_node_index = 2
    state.current_hp = max(1, state.max_hp // 3)
    state.current_mp = 0
    state.set_rest_phase()
    rest = render_rest(state, bundle, language="en", width=100)

    selectable = {
        "hero_list": render_hero_list(bundle, language="en"),
        "route": route,
        "reward": reward,
        "shop": shop,
        "rest": rest,
    }
    for name, text in selectable.items():
        card_headers = [line for line in text.splitlines() if "[ [1]" in line]
        assert card_headers, f"{name} missing pixel choice card header"
        assert all(line[0] in "+!>#" for line in card_headers)
        assert all(line.rstrip()[-1] in "+!<#" for line in card_headers)
        assert all(visual_width(line) <= 100 for line in text.splitlines())
        assert "+-- [1]" not in text

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    battle_state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    battle_state.hero.add_status(StatusEffect(id="status_shield", stacks=2, duration=3))
    battle_state.enemies[0].add_status(StatusEffect(id="status_corruption", stacks=1, duration=2))
    record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(type="basic_attack", targets=("enemy_hungry_cultist",)),
        judge=JudgeOutcome(
            valid=True,
            reason="basic_attack resolved",
            summary="basic_attack -> enemy_hungry_cultist | 10 dmg",
            damage=10,
            target_ids=("enemy_hungry_cultist",),
            action_kind="basic_attack",
        ),
        battle_session_id="test",
        static_context_hash="ctx_test",
        delta_context_id="test_d0001",
    )

    screen = render_battle_screen(
        battle_state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
    )
    report = render_battle_report(battle_state, [record], language="en", width=100)

    assert "BUFF   : SHD shield(2)" in screen
    assert "DEBUFF : CRP corrupt(1)" in screen
    assert "status_shield" not in screen
    assert "status_corruption" not in screen
    assert "Status Details:" in report
    assert "HERO SHD shield x2 / 3t" in report
    assert "[c] CRP corrupt x1 / 2t" in report
    assert "id=status_shield" not in report
    assert "id=status_corruption" not in report


def test_core_screens_have_stable_width_and_required_fields(bundle):
    from ouro_agent.config import OuroConfig
    from ouro_agent.i18n import visual_width
    from ouro_agent.tui.screens import (
        render_battle_report,
        render_battle_screen,
        render_hero_card,
        render_main_menu,
        render_progress_status,
        render_rest,
        render_reward_choice,
        render_route_choice,
        render_shop,
        render_weapon_gallery,
    )

    from ouro_agent.sessions import CodexProgress

    hero = bundle.get_hero("hero_shadow_apprentice")
    build = resolve_build(hero, bundle)
    record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(type="basic_attack", targets=("enemy_hungry_cultist",)),
        judge=JudgeOutcome(
            valid=True,
            reason="basic_attack resolved",
            summary="basic_attack -> enemy_hungry_cultist | 10 dmg",
            damage=10,
            target_ids=("enemy_hungry_cultist",),
            action_kind="basic_attack",
        ),
        battle_session_id="test",
        static_context_hash="ctx_test",
        delta_context_id="test_d0001",
    )

    required = {
        "en": {
            "menu": (("MAIN MENU CONSOLE",), ("mock-smart",), ("ouro.toml",), ("Mock Path : mock-ready",), ("[NEXT] Recommended: ouro demo --seed 1",), ("PLAYER JOURNEY BOARD",), ("ENTRY COMMANDS",), ("[START]",), ("[BUILD]",), ("[RUN]",), ("[LEARN]",), ("[PLAY] New Run",), ("[BUILD] Hero/Weapon",), ("[LEARN] Run Report",), ("ouro run --mock",), ("Guided Demo",), ("ouro demo --seed 1",), ("Quick Battle",), ("ouro codex",), ("ouro runs",), ("ouro run-report",), ("ouro history",), ("ouro doctor",)),
            "hero": (("[W:",), ("BUILD STAGE:",), ("Core Tags:",)),
            "weapon": (("WEAPON GALLERY :: BUILD ARSENAL",), ("[W:STF] c==* Astia",), ("NEXT WEAPON ROUTE",)),
            "route": (("Cost:",), ("Reward:",), ("Build fit:",), ("Scout:",)),
            "reward": (("Build before/after:",), ("Tag delta:",), ("AI impact:",)),
            "shop": (("Restore MP to full",), ("Decision:",), ("Build before/after:",)),
            "rest": (("Rest preview:",), ("[1] Recover",), ("[2] Focus",)),
            "status": (("OURO STATUS :: ECHO LEDGER",), ("PROFILE",), ("Runs: 1 total",), ("LEGEND PROGRESS MAP",), ("NEXT RUN PLAN",), ("NEXT RUN CONTROL",), ("Patch 8 Codex gaps",), ("NEXT COMMANDS",), ("ouro status --lang en",)),
            "battle": (
                ("HP",),
                ("MP",),
                ("ATB",),
                ("ACTION",),
                ("CINEMATIC BEAT",),
                ("VOX",),
                ("ENM",),
                ("FLOAT",),
                ("STRIP",),
                ("LOG",),
            ),
            "report": (
                ("AFTER-ACTION STAGE",),
                ("RESULT RAIL",),
                ("DAMAGE RAIL",),
                ("Result:",),
                ("Tactical Diagnosis:",),
                ("Build note:",),
                ("PLAY NEXT BOARD",),
                ("ouro play --mock",),
            ),
        },
        "zh": {
            "menu": (("主菜单控制台",), ("mock-smart",), ("ouro.toml",), ("Mock Path : mock-ready",), ("[NEXT] 建议先跑: ouro demo --seed 1",), ("玩家旅程",), ("入口命令",), ("[START]",), ("[BUILD]",), ("[RUN]",), ("[LEARN]",), ("[PLAY] 新运行",), ("[BUILD] 英雄/武器",), ("[LEARN] 运行报告",), ("ouro run --mock",), ("引导试玩",), ("ouro demo --seed 1",), ("快速战斗",), ("ouro codex",), ("ouro runs",), ("ouro run-report",), ("ouro history",), ("ouro doctor",)),
            "hero": (("[W:",), ("构筑阶段:",), ("核心标签:",)),
            "weapon": (("武器图鉴 :: 构筑兵装",), ("[W:STF] c==* 阿斯缇娅",), ("下一步武器路线",)),
            "route": (("消耗:",), ("收益:",), ("Build 适配:",), ("侦察:",)),
            "reward": (("Build 前后:",), ("标签变化:",), ("AI 影响:",)),
            "shop": (("MP 恢复至满",), ("决策:",), ("Build 前后:",)),
            "rest": (("休整预览:",), ("[1] Recover",), ("[2] Focus",)),
            "status": (("OURO STATUS :: 回响总览",), ("档案",), ("Runs: 1 total",), ("传奇进度地图",), ("下一局计划",), ("下一局控制台",), ("补图鉴缺口 8 个",), ("下一步命令",), ("ouro status --lang zh",)),
            "battle": (
                ("HP",),
                ("MP",),
                ("ATB",),
                ("ACTION", "行动"),
                ("战斗分镜",),
                ("声",),
                ("敌",),
                ("浮字",),
                ("节奏",),
                ("日志",),
            ),
            "report": (
                ("战后结算镜头",),
                ("结果轨道",),
                ("伤害轨道",),
                ("结果:",),
                ("战术诊断:",),
                ("Build 备注:",),
                ("下一局闭环面板",),
                ("[重开]",),
            ),
        },
    }

    for language in ("en", "zh"):
        config = OuroConfig(
            provider="mock",
            model="mock-smart",
            language=language,
            unicode_mode=False,
        )
        for width in (80, 100, 120):
            run_state = create_run_state(
                "run_ui",
                7,
                "hero_shadow_apprentice",
                "dungeon_ember_crypt",
                bundle,
            )

            run_state.current_floor_index = 2
            route = render_route_choice(run_state, bundle, language=language, width=width)

            run_state.current_floor_index = 0
            run_state.current_node_index = 0
            node = run_state.current_node(bundle)
            run_state.set_reward_choices(list(node.rewards.reward_choices))
            reward = render_reward_choice(run_state, bundle, language=language, width=width)

            run_state.current_floor_index = 1
            run_state.current_node_index = 1
            run_state.set_shop_items(list(run_state.current_node(bundle).shop_items))
            run_state.gold = 25
            shop = render_shop(run_state, bundle, language=language, width=width)

            run_state.current_node_index = 2
            run_state.current_hp = max(1, run_state.max_hp // 3)
            run_state.current_mp = 0
            run_state.set_rest_phase()
            rest = render_rest(run_state, bundle, language=language, width=width)

            loop = BattleLoop(
                bundle,
                MockProvider(seed=1, language=language),
                seed=1,
                language=language,
            )
            battle_state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
            battle_state.log.append("Test")
            progress = CodexProgress()
            progress.record_encounter("family_hungry_cultist", "trace")
            archive = {
                "run_id": "run_ui_status",
                "seed": 7,
                "result": "dead",
                "phase": "dead",
                "hero_id": "hero_shadow_apprentice",
                "dungeon_id": "dungeon_ember_crypt",
                "battles_won": 3,
                "battles_lost": 1,
                "gold": 25,
                "xp": 9,
                "current_hp": 0,
                "max_hp": 64,
                "current_mp": 2,
                "max_mp": 28,
                "completed_node_ids": ["node_ember_crypt_f1_n1"],
                "build": {
                    "archetype": "Black Candle Interrupt",
                    "stage_badge": "[ONLINE]",
                },
            }

            screens = {
                "menu": render_main_menu(
                    config,
                    config_path="ouro.toml",
                    language=language,
                    width=width,
                ),
                "hero": render_hero_card(
                    hero,
                    bundle,
                    build,
                    language=language,
                    prompt_style="control",
                    width=width,
                ),
                "weapon": render_weapon_gallery(bundle, language=language, width=width),
                "route": route,
                "reward": reward,
                "shop": shop,
                "rest": rest,
                "status": render_progress_status(
                    config,
                    bundle,
                    progress,
                    [archive],
                    [{"run_id": "run_ui_status"}],
                    config_path="/tmp/ouro/status/config.toml",
                    codex_save_path="/tmp/ouro/status/codex.json",
                    run_archive_path="/tmp/ouro/status/runs/with/a/very/long/path",
                    death_history_save_path="/tmp/ouro/status/death_history.json",
                    language=language,
                    width=width,
                ),
                "battle": render_battle_screen(
                    battle_state,
                    record,
                    provider_label="mock",
                    seed=1,
                    unicode_mode=False,
                    language=language,
                    width=width,
                    bundle=bundle,
                    build=build,
                ),
                "report": render_battle_report(
                    battle_state,
                    [record],
                    language=language,
                    width=width,
                ),
            }

            for name, text in screens.items():
                for marker_options in required[language][name]:
                    assert any(marker in text for marker in marker_options), (
                        f"{name}/{language}/{width} missing one of {marker_options}"
                    )
                overflow = [
                    (line_number, visual_width(line), line)
                    for line_number, line in enumerate(text.splitlines(), start=1)
                    if visual_width(line) > width
                ]
                assert not overflow, f"{name}/{language}/{width} overflow: {overflow[:3]}"


def test_hero_sprite_changes_with_pose(bundle):
    from ouro_agent.tui.screens import _hero_sprite

    loop = BattleLoop(bundle, MockProvider(seed=1), seed=1)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    hero = state.hero

    idle_sprite = _hero_sprite(hero, None)

    attack_record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(type="basic_attack", targets=("enemy_hungry_cultist",)),
        judge=JudgeOutcome(
            valid=True,
            reason="basic_attack resolved",
            summary="basic_attack -> enemy_hungry_cultist | 10 dmg",
            damage=10,
            target_ids=("enemy_hungry_cultist",),
            action_kind="basic_attack",
        ),
        battle_session_id="test",
        static_context_hash="ctx_test",
        delta_context_id="test_d0001",
    )
    attack_sprite = _hero_sprite(hero, attack_record)

    assert idle_sprite != attack_sprite


def test_weapon_icon_in_battle_screen(bundle):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.log.append("Test")
    record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(type="basic_attack", targets=("enemy_hungry_cultist",)),
        judge=JudgeOutcome(
            valid=True,
            reason="basic_attack resolved",
            summary="basic_attack -> enemy_hungry_cultist | 10 dmg",
            damage=10,
            target_ids=("enemy_hungry_cultist",),
            action_kind="basic_attack",
        ),
        battle_session_id="test",
        static_context_hash="ctx_test",
        delta_context_id="test_d0001",
    )

    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        unicode_mode=False,
        language="en",
    )

    assert "[W:STF]" in screen
    assert "ACTION LENS" in screen
    assert "SHOT" in screen
    assert "JUDGE" in screen


def test_build_badge_in_battle_screen(bundle):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.log.append("Test")
    record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(type="basic_attack", targets=("enemy_hungry_cultist",)),
        judge=JudgeOutcome(
            valid=True,
            reason="basic_attack resolved",
            summary="basic_attack -> enemy_hungry_cultist | 10 dmg",
            damage=10,
            target_ids=("enemy_hungry_cultist",),
            action_kind="basic_attack",
        ),
        battle_session_id="test",
        static_context_hash="ctx_test",
        delta_context_id="test_d0001",
    )

    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        unicode_mode=False,
        language="en",
    )

    assert "[ONLINE]" in screen
    assert "ACTION LENS" in screen


def test_dynamic_next_pick_in_battle_screen(bundle):
    """REQ-BUILDJOY-001: NEXT PICK should use real BuildProgress, not hardcoded."""
    from ouro_agent.tui.screens import render_battle_screen

    hero_data = bundle.get_hero("hero_shadow_apprentice")
    build = resolve_build(hero_data, bundle)

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.log.append("Test")
    record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(type="basic_attack", targets=("enemy_hungry_cultist",)),
        judge=JudgeOutcome(
            valid=True,
            reason="basic_attack resolved",
            summary="basic_attack -> enemy_hungry_cultist | 10 dmg",
            damage=10,
            target_ids=("enemy_hungry_cultist",),
            action_kind="basic_attack",
        ),
        battle_session_id="test",
        static_context_hash="ctx_test",
        delta_context_id="test_d0001",
    )

    screen_with_build = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        unicode_mode=False,
        language="en",
        bundle=bundle,
        build=build,
    )

    screen_without_build = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        unicode_mode=False,
        language="en",
    )

    assert "hardcoded" not in screen_with_build.lower()
    assert "control +1" not in screen_with_build or "HIGH ROLL" not in screen_with_build
    assert "NEXT PICK:" in screen_with_build
    assert "NEED:" in screen_with_build
    next_pick_lines = [line for line in screen_with_build.splitlines() if "NEXT PICK:" in line]
    assert next_pick_lines
    assert all("NEED:" not in line for line in next_pick_lines)
    assert "BUILD STAGE: pending" in screen_without_build

    screen_zh = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        unicode_mode=False,
        language="zh",
        bundle=bundle,
        build=build,
    )
    assert "武器" in screen_zh
    assert "裂痕短杖" in screen_zh
    assert "构筑 [ONLINE]" in screen_zh
    assert "暗影 3/3" in screen_zh
    assert "控制 2/3" in screen_zh
    assert "下次选择:" in screen_zh
    assert "词条" in screen_zh
    assert "遗物" in screen_zh
    assert "还需:" in screen_zh
    next_lines_zh = [line for line in screen_zh.splitlines() if "下次选择:" in line]
    assert next_lines_zh
    assert all(" relic" not in line for line in next_lines_zh)
    need_lines_zh = [line for line in screen_zh.splitlines() if "还需:" in line]
    assert need_lines_zh
    assert all(" for " not in line for line in need_lines_zh)
    assert any("推进" in line for line in need_lines_zh)
    assert "BLACK CANDLE STAFF" not in screen_zh.upper()
    assert "NEXT PICK:" not in screen_zh
    assert "NEED:" not in screen_zh

    screen_zh_canvas = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        unicode_mode=True,
        language="zh",
        bundle=bundle,
        build=build,
    )
    assert "裂痕短杖" in screen_zh_canvas
    assert "[ONLINE] 暗影" in screen_zh_canvas
    assert "暗影/控制" in screen_zh_canvas
    assert "[ONLINE] shadow" not in screen_zh_canvas
    assert "shadow/control" not in screen_zh_canvas


def test_start_and_setup_screens_show_playable_entry_context(bundle):
    from ouro_agent.tui.screens import (
        render_encounter_briefing,
        render_run_setup_screen,
        render_start_screen,
    )
    from ouro_agent.config import OuroConfig
    from ouro_agent.i18n import visual_width

    config = OuroConfig(provider="mock", model="mock-smart", language="en")
    hero = bundle.get_hero("hero_shadow_apprentice")
    build = resolve_build(hero, bundle)

    start = render_start_screen(config, provider_label="mock", seed=7, language="en")
    setup = render_run_setup_screen(
        hero,
        bundle,
        build,
        provider_label="mock",
        prompt_style="control",
        language="en",
    )
    start_zh = render_start_screen(
        config,
        provider_label="mock",
        seed=7,
        language="zh",
    )
    setup_zh = render_run_setup_screen(
        hero,
        bundle,
        build,
        provider_label="mock",
        prompt_style="control",
        language="zh",
    )

    loop = BattleLoop(bundle, MockProvider(seed=1, language="zh"), seed=1, language="zh")
    encounter_state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    encounter = render_encounter_briefing(
        encounter_state,
        bundle,
        build,
        language="zh",
        width=100,
    )
    loop_en = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    encounter_state_en = loop_en.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    encounter_en = render_encounter_briefing(
        encounter_state_en,
        bundle,
        build,
        language="en",
        width=100,
    )

    assert start.isascii()
    assert "OURO AGENT :: PROMPT LEGEND" in start
    assert "New Run: choose hero, prompt style" in start
    assert "RUN SETUP" in setup
    assert "Equipment Loadout" in setup
    assert "Prompt Contract" in setup
    assert "RUN READY BOARD" in setup
    assert "[PROMPT] control / open by denying chant windows" in setup
    assert "[BUILD] [ONLINE] Online / Black Candle Interrupt" in setup
    assert "[CORE] shadow / control" in setup
    assert "[NEXT PICK]" in setup
    assert "[FIRST RULE] model chooses action, local judge resolves" in setup
    assert "Active Resonances: Corruption School" in setup
    assert "resonance_corruption_school" not in setup
    assert "[W:*]" in setup

    assert "暗影代理 :: 祷文传说" in start_zh
    assert "供应商: mock" in start_zh
    assert "模型: mock-smart" in start_zh
    assert "种子: 7" in start_zh
    assert "|  英雄" in start_zh
    assert "|  提示词" in start_zh
    assert "|  本地裁判" in start_zh
    assert "属性/构筑" in start_zh
    assert "风格/意图" in start_zh
    assert "伤害/胜负" in start_zh
    assert "入局确认" in setup_zh
    assert "[提示词]" in setup_zh
    assert "[构筑]" in setup_zh
    assert "[ONLINE] 在线 / 黑烛打断" in setup_zh
    assert "[核心]" in setup_zh
    assert "[下次选择]" in setup_zh
    assert "标签:" in setup_zh
    assert "标签: 暗影" in setup_zh
    assert "标签: 暗影, 图鉴" in setup_zh
    assert "标签: 暗影, 腐化" in setup_zh
    assert "标签: 暗影, 控制" in setup_zh
    assert "[普通]" in setup_zh
    assert "[英雄]" in setup_zh
    assert "暗影" in setup_zh
    assert "图鉴" in setup_zh
    assert "腐化" in setup_zh
    assert "控制" in setup_zh
    assert "tags:" not in setup_zh
    assert "Online / 黑烛打断" not in setup_zh
    assert "[第一规则]" in setup_zh
    assert "遭遇简报" in encounter
    assert "入场镜头" in encounter
    assert "英雄 阿斯缇娅" in encounter
    assert "敌方 [" in encounter
    assert "威胁轨道" in encounter
    assert "窗口轨道" in encounter
    assert "简报字段:" in encounter
    assert "[敌人]" in encounter
    assert "[威胁]" in encounter
    assert "[构筑]" in encounter
    assert "下次 防守, 护甲" in encounter
    assert "下次 guard" not in encounter
    assert "[窗口]" in encounter
    assert "[计划]" in encounter
    assert encounter_en.isascii()
    assert "ENCOUNTER BRIEFING" in encounter_en
    assert "MINI STAGE" in encounter_en
    assert "HERO Astia" in encounter_en
    assert "ENEMY [" in encounter_en
    assert "THREAT RAIL" in encounter_en
    assert "WINDOW RAIL" in encounter_en
    assert "BRIEF FIELDS:" in encounter_en
    assert "[ENEMY]" in encounter_en
    assert "[THREAT]" in encounter_en
    assert "[BUILD]" in encounter_en
    assert "[WINDOW]" in encounter_en
    assert "[PLAN]" in encounter_en

    for language, state_for_width in (
        ("en", encounter_state_en),
        ("zh", encounter_state),
    ):
        for width in (80, 100, 120):
            compact = render_encounter_briefing(
                state_for_width,
                bundle,
                build,
                language=language,
                width=width,
            )
            overflow = [
                (line_number, visual_width(line), line)
                for line_number, line in enumerate(compact.splitlines(), start=1)
                if visual_width(line) > width
            ]
            assert not overflow, f"encounter/{language}/{width} overflow: {overflow[:3]}"

    for chrome in (
        "Provider:",
        "Model:",
        "Seed:",
        "HERO",
        "LOCAL JUDGE",
        "RUN READY BOARD",
        "[PROMPT]",
        "[NEXT PICK]",
        "ENCOUNTER BRIEFING",
        "[ENEMY]",
        "[THREAT]",
        "[WINDOW]",
        "[PLAN]",
    ):
        assert chrome not in start_zh
        assert chrome not in setup_zh
        assert chrome not in encounter

def test_story_surfaces_show_route_boss_battle_and_codex_fragments(bundle):
    """REQ-STORY-001: story text appears before fights, on routes, and in Codex."""
    from ouro_agent.sessions import CodexProgress
    from ouro_agent.tui.screens import render_battle_screen, render_codex_card, render_route_choice

    run_state = create_run_state(
        "run_story",
        7,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    run_state.current_floor_index = 2
    route = render_route_choice(run_state, bundle, language="en", width=100)
    assert "Omen: A low chant reverberates through the chamber." in route
    assert "These are not hungry scavengers" in route

    run_state.current_floor_index = 3
    boss_route = render_route_choice(run_state, bundle, language="en", width=100)
    assert "Boss omen:" in boss_route
    assert "predicted that too." in boss_route

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(type="basic_attack", targets=("enemy_hungry_cultist",)),
        judge=JudgeOutcome(
            valid=True,
            reason="basic_attack resolved",
            summary="basic_attack -> enemy_hungry_cultist | 10 dmg",
            damage=10,
            target_ids=("enemy_hungry_cultist",),
            action_kind="basic_attack",
        ),
    )
    battle = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=7,
        language="en",
        width=100,
        scene_text=bundle.dungeons["dungeon_ember_crypt"].scene_text.get("en"),
    )
    assert "ash candles flicker under a broken arch" in battle

    progress = CodexProgress()
    progress.record_encounter("family_black_candle")
    codex = render_codex_card(
        "enemy_black_candle_acolyte",
        bundle,
        codex_progress=progress,
        language="en",
    )
    assert "Acolytes channel a slow chant" in codex


def test_battle_screen_lists_all_enemies_in_roster(bundle):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(type="basic_attack", targets=("enemy_hungry_cultist",)),
        judge=JudgeOutcome(
            valid=True,
            reason="basic_attack resolved",
            summary="basic_attack -> enemy_hungry_cultist | 10 dmg",
            damage=10,
            target_ids=("enemy_hungry_cultist",),
            action_kind="basic_attack",
        ),
        battle_session_id="test",
        static_context_hash="ctx_test",
        delta_context_id="test_d0001",
    )

    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        unicode_mode=False,
        language="en",
        width=100,
    )

    assert "ENEMY ROSTER" in screen
    assert "Hungry Cultist" in screen
    assert "Black Candle Acolyte" in screen
