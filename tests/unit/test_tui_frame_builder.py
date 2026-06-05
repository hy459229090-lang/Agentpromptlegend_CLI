from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.content import load_content_bundle
from ouro_agent.engine.battle import BattleLoop, TurnRecord
from ouro_agent.engine.judge import JudgeOutcome
from ouro_agent.i18n import visual_width
from ouro_agent.llm.actions import HeroAction
from ouro_agent.llm.validator import ValidationResult
from ouro_agent.providers.mock import MockProvider
from ouro_agent.tui.frame_builder import build_battle_frame, format_status_detail, format_status_short
from ouro_agent.engine.models import StatusEffect


@pytest.fixture()
def bundle(content_root: Path):
    return load_content_bundle(content_root)


def _hex_record() -> TurnRecord:
    return TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text="analysis: interrupt the caster before release",
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_hex_seal",
            targets=("enemy_hungry_cultist",),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary="cast_skill skill_hex_seal -> enemy_hungry_cultist | 16 dmg",
            damage=16,
            target_ids=("enemy_hungry_cultist",),
            skill_id="skill_hex_seal",
            action_kind="cast_skill",
        ),
        battle_session_id="be_test",
        static_context_hash="ctx_test",
        delta_context_id="be_test_d0001",
        usage_latency_ms=12,
    )


def test_battle_frame_exposes_director_fields(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    record = _hex_record()

    frame = build_battle_frame(state, record)

    assert frame.phase == "hero_action"
    assert frame.action_label == "Hex Seal -> Hungry Cultist"
    assert frame.judge_label == "VALID | -16 HP"
    assert frame.impact_line is not None
    assert "-16 HP" in frame.impact_line
    assert frame.intent == "control the fastest threat"
    assert "Control" in frame.align
    assert frame.effect_glyph == "--x seal --"
    assert frame.event_banner in {"CHARGE BROKEN", "SEAL PLACED"}
    assert frame.session_usage is not None
    assert frame.session_usage.ritual_time_ms == 12


def test_pixel_skin_panels_are_ascii_and_fixed_width():
    from ouro_agent.tui.pixel_skin import pixel_panel, pixel_rule

    panel = pixel_panel("ACTION", ["Hex Seal", "IMPACT -16 HP"], 60, tone="counter")
    assert all(line.isascii() for line in panel.lines)
    assert all(len(line) == 60 for line in panel.lines)
    zh_panel = pixel_panel("行动选择", ["Recover", "SHD 12"], 40, tone="hero")
    assert all(visual_width(line) == 40 for line in zh_panel.lines)
    rule = pixel_rule("THE ECHO ALTAR", 80, tone="climax")
    assert rule.startswith("#")
    assert len(rule) == 80


def test_canvas_surface_draws_block_art_without_width_drift():
    from ouro_agent.tui.canvas import Surface
    from ouro_agent.tui.glyphs import get_glyph_set

    glyphs = get_glyph_set("unicode")
    surface = Surface(32, 8)
    surface.draw_box(0, 0, 32, 8, glyphs)
    surface.draw_sprite(3, 2, [" ▄██▄ ", " ▐▓c▓▌", "  ▟██▙"])
    surface.draw_bar(3, 6, 10, 0.6, glyphs)
    rendered = surface.render()

    assert any("▄██▄" in line for line in rendered)
    assert any("██████" in line or "█████" in line for line in rendered)
    assert all(visual_width(line) == 32 for line in rendered)


def test_tui_glyph_sets_are_single_width():
    from ouro_agent.tui.glyphs import ASCII_GLYPHS, UNICODE_BLOCK_GLYPHS

    for glyph_set in (ASCII_GLYPHS, UNICODE_BLOCK_GLYPHS):
        for glyph in (
            glyph_set.empty,
            glyph_set.light,
            glyph_set.mid,
            glyph_set.solid,
            glyph_set.upper,
            glyph_set.lower,
            glyph_set.left,
            glyph_set.right,
            glyph_set.h,
            glyph_set.v,
            glyph_set.corner,
        ):
            assert visual_width(glyph) == 1


def test_status_short_name_keeps_combat_screen_readable():
    assert format_status_short(StatusEffect("status_silence", stacks=2, duration=1)) == "SLN silence(2)"
    assert format_status_short(StatusEffect("status_corruption", stacks=1, duration=1)) == "CRP corrupt(1)"
    assert (
        format_status_detail(StatusEffect("status_silence", stacks=2, duration=1))
        == "SLN silence(2) id=status_silence dur=1"
    )


def test_layout_width_uses_visual_width(bundle):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="zh"), seed=1, language="zh")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    screen = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="zh",
        width=80,
    )

    for line in screen.splitlines():
        assert visual_width(line) <= 80


def test_unicode_battle_screen_uses_canvas_block_stage(bundle):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    screen = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
        unicode_mode=True,
    )

    assert "THE ECHO ALTAR" in screen
    assert "GRAPHICAL TUI" in screen
    assert "▄██▄" in screen
    assert "SELECT" in screen
    assert "IMPACT" in screen
    assert "JUDGE" in screen
    assert "[W:STF]" in screen
    assert "[ONLINE]" in screen
    assert "░░▓▓██>" in screen or "▓▓ SLN ▓▓" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= 100


def test_unicode_battle_screen_optional_color_keeps_canvas_width(bundle, monkeypatch):
    from ouro_agent.tui.ansi import strip_ansi
    from ouro_agent.tui.screens import render_battle_screen

    monkeypatch.delenv("NO_COLOR", raising=False)
    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    plain = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
        unicode_mode=True,
    )
    colored = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
        unicode_mode=True,
        color_mode="always",
    )

    stripped = strip_ansi(colored)
    assert "\x1b[" not in plain
    assert "\x1b[" in colored
    assert "GRAPHICAL TUI" in stripped
    assert "SELECT" in stripped
    assert "HIT -16 HP SLN" in stripped
    for line in stripped.splitlines():
        assert visual_width(line) <= 100

    monkeypatch.setenv("NO_COLOR", "1")
    no_color = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
        unicode_mode=True,
        color_mode="always",
    )
    assert "\x1b[" not in no_color


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_canvas_width_matrix(bundle, width):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    screen = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )

    assert "GRAPHICAL TUI" in screen
    assert "SELECT" in screen
    assert "IMPACT" in screen
    assert "HIT -16 HP SLN" in screen
    assert "ACTION HEX -> c" in screen
    assert "ACTION Hex Seal" not in screen
    assert "Hex Seal -> Hungry Cultist" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= width


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_draws_plan_ribbon_inside_canvas(bundle, width):
    """REQ-HEROPLAN-001: Canvas stage should show the compact tactical plan."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])

    waiting = render_battle_screen(
        state,
        None,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "PLAN READ | PENDING" in waiting

    action = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "PLAN CONTROL | PROMPT HIT" in action
    assert "ACTION HEX -> c" in action
    assert "Hex Seal -> Hungry Cultist" in action
    assert "JUDGE  VALID | -16 HP" in action

    enemy = state.enemies[0]
    enemy.chant_charge_turns = 1
    enemy.chant_progress = 1
    enemy_record = TurnRecord(
        tick=10,
        actor_id=enemy.id,
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "chant_charge"},
        battle_session_id="be_plan",
        static_context_hash="ctx_plan",
    )
    counter = render_battle_screen(
        state,
        enemy_record,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "PLAN ANSWER | COUNTER" in counter
    assert "ACTION ENEMY CHARGE" in counter
    assert "Hungry Cultist chant_charge" in counter
    assert "JUDGE  LOCAL" in counter

    for screen in (waiting, action, counter):
        for line in screen.splitlines():
            assert visual_width(line) <= width


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_draws_beat_badge_inside_canvas(bundle, width):
    """REQ-CANVASBEAT-001: Canvas title should show tick and active side."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.tick = 9

    waiting = render_battle_screen(
        state,
        None,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "THE ECHO ALTAR" in waiting
    assert "BEAT T009 WAIT" in waiting

    action = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "BEAT T009 HERO" in action
    assert "ACTION HEX -> c" in action
    assert "Hex Seal -> Hungry Cultist" in action
    assert "JUDGE  VALID | -16 HP" in action

    enemy = state.enemies[0]
    enemy_record = TurnRecord(
        tick=10,
        actor_id=enemy.id,
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "attack", "damage": 9},
        battle_session_id="be_beat",
        static_context_hash="ctx_beat",
    )
    enemy_turn = render_battle_screen(
        state,
        enemy_record,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "BEAT T010 ENEMY" in enemy_turn
    assert "ACTION ENEMY STRIKE" in enemy_turn
    assert "Hungry Cultist attack" in enemy_turn
    assert "JUDGE  LOCAL" in enemy_turn

    for screen in (waiting, action, enemy_turn):
        for line in screen.splitlines():
            assert visual_width(line) <= width


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_draws_cast_meter_inside_canvas(bundle, width):
    """REQ-CASTMETER-001: Canvas stage should show chant progress as a meter."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_acolyte"])
    target = state.enemies[0]
    target.chant_charge_turns = 2
    target.chant_progress = 1
    record = TurnRecord(
        tick=10,
        actor_id=target.id,
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "chant_charge"},
        battle_session_id="be_cast_meter",
        static_context_hash="ctx_cast_meter",
    )

    charging = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "CAST " in charging
    assert "1/2" in charging
    assert "INTENT CHANT 1/2" in charging
    assert "RETICLE [WINDOW]" in charging

    target.add_status(StatusEffect("status_silence", stacks=1, duration=1))
    cut = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "CAST CUT" in cut
    assert "INTENT SILENCED" in cut

    for screen in (charging, cut):
        for line in screen.splitlines():
            assert visual_width(line) <= width


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_draws_wound_rail_inside_canvas(bundle, width):
    """REQ-WOUNDRAIL-001: Canvas stage should show target HP breakpoints."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    target = state.enemies[0]
    target.max_hp = 60
    target.hp = 44

    def hit_record(damage: int) -> TurnRecord:
        return TurnRecord(
            tick=9,
            actor_id=state.hero.id,
            side="hero",
            raw_text="analysis: press damage into the kill window",
            validation=None,
            action=HeroAction(
                type="cast_skill",
                skill_id="skill_hex_seal",
                targets=(target.id,),
            ),
            judge=JudgeOutcome(
                valid=True,
                reason="cast_skill resolved",
                summary=f"cast_skill skill_hex_seal -> {target.id} | {damage} dmg",
                damage=damage,
                target_ids=(target.id,),
                skill_id="skill_hex_seal",
                action_kind="cast_skill",
            ),
            battle_session_id="be_wound_rail",
            static_context_hash="ctx_wound_rail",
        )

    hold = render_battle_screen(
        state,
        hit_record(16),
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "WOUND" in hold
    assert "-16" in hold
    assert "44/60" in hold
    assert "HOLD" in hold
    assert "HIT -16 HP SLN" in hold

    target.hp = 12
    execute = render_battle_screen(
        state,
        hit_record(18),
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "12/60" in execute
    assert "EXE" in execute

    target.hp = 0
    down = render_battle_screen(
        state,
        hit_record(12),
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "0/60" in down
    assert "DOWN" in down

    for screen in (hold, execute, down):
        assert "PLAN" in screen
        assert "ACTION" in screen
        assert "JUDGE" in screen
        for line in screen.splitlines():
            assert visual_width(line) <= width


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_draws_pain_rail_on_enemy_damage(bundle, width):
    """REQ-PAINRAIL-001: Enemy damage frames should focus the hero HP rail."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])

    def enemy_hit(damage: int) -> TurnRecord:
        return TurnRecord(
            tick=12,
            actor_id="enemy_hungry_cultist",
            side="enemy",
            raw_text=None,
            validation=None,
            action=None,
            judge=None,
            enemy_action={"type": "attack", "damage": damage},
            battle_session_id="be_pain_rail",
            static_context_hash="ctx_pain_rail",
        )

    state.hero.max_hp = 50
    state.hero.hp = 41
    safe = render_battle_screen(
        state,
        enemy_hit(9),
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "PAIN" in safe
    assert "-9" in safe
    assert "41/50" in safe
    assert "SAFE" in safe
    assert "HIT -9 HP" in safe
    assert "WOUND" not in safe

    state.hero.hp = 12
    crit = render_battle_screen(
        state,
        enemy_hit(18),
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "12/50" in crit
    assert "CRIT" in crit

    state.hero.hp = 0
    fall = render_battle_screen(
        state,
        enemy_hit(12),
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "0/50" in fall
    assert "FALL" in fall

    for screen in (safe, crit, fall):
        assert "PLAN" in screen
        assert "ACTION" in screen
        assert "JUDGE" in screen
        for line in screen.splitlines():
            assert visual_width(line) <= width


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_marks_counter_window_in_canvas(bundle, width):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_acolyte"])
    target = state.enemies[0]
    target.chant_charge_turns = 1
    target.chant_progress = 1
    target.atb = 96
    hex_seal = state.hero.find_skill("skill_hex_seal")
    assert hex_seal is not None
    hex_seal.cooldown_remaining = 3
    record = TurnRecord(
        tick=10,
        actor_id="enemy_black_candle_acolyte",
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "chant_charge"},
        battle_session_id="be_test",
        static_context_hash="ctx_test",
    )
    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )

    assert "WINDOW" in screen
    assert "CUT " in screen
    assert "FULL" in screen
    assert "CD3" in screen
    assert "ACTION ENEMY CHARGE" in screen
    assert "ACTION Black Candle Acolyte cha..." not in screen
    assert "DELTA ATB:k96 CD:HEX3" in screen
    assert "DELTA ATB Black Candle" not in screen
    assert "COUNTER CLOCK" in screen
    assert screen.count("COUNTER CLOCK") == 1
    assert "THE ECHO ALTAR / COUNTER WINDOW" in screen
    assert "COUNTER CLOCK [#####] FULL | NE..." not in screen

    hex_seal.cooldown_remaining = 0
    state.hero.mp = 12
    mp_blocked = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "CUT " in mp_blocked
    assert "MP12/18" in mp_blocked

    state.hero.mp = 54
    ready = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "CUT " in ready
    assert "READY" in ready

    for candidate in (screen, mp_blocked, ready):
        for line in candidate.splitlines():
            assert visual_width(line) <= width


def test_unicode_battle_screen_uses_directed_effect_lane_and_hit_pose(bundle):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    record = TurnRecord(
        tick=12,
        actor_id="enemy_hungry_cultist",
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "attack", "damage": 9},
        battle_session_id="be_test",
        static_context_hash="ctx_test",
    )

    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
        unicode_mode=True,
    )

    assert "<██▓▓░" in screen
    assert "STRIKE -9 HP" in screen
    assert "▐▓x" in screen
    assert "HIT -9 HP" in screen
    assert "[HIT -9 HPhadow" not in screen
    assert "HIT -9 HPNLINE" not in screen
    assert "[ONLINE] shadow" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= 100


def test_unicode_battle_screen_embeds_scene_and_hero_voice_in_canvas(bundle):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    screen = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
        unicode_mode=True,
        scene_text="ash candles flicker under a broken arch",
    )

    assert "VOX There. The wick forg..." in screen
    assert "ENM armor cracking" in screen
    assert "candle" in screen
    assert "broken arch" in screen
    assert "SEAL -16 HP" in screen
    assert "▓██>h" not in screen
    for line in screen.splitlines():
        assert visual_width(line) <= 100


def test_unicode_battle_screen_embeds_resource_thresholds_in_canvas(bundle):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.hero.hp = 25
    state.hero.mp = 2
    state.hero.atb = 100
    screen = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
        unicode_mode=True,
    )

    assert "HP CRIT" in screen
    assert "MP LOW" in screen
    assert "ATB READY" in screen
    assert "DELTA MP20>2 I:N HP25/100!" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= 100


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_draws_status_chips_inside_canvas(bundle, width):
    """REQ-CANVASSTATUS-001: Canvas stage should show compact buff/debuff chips."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.hero.add_status(StatusEffect("status_shield", stacks=7, duration=2))
    target = state.enemies[0]
    target.add_status(StatusEffect("status_silence", stacks=1, duration=1))
    target.add_status(StatusEffect("status_corruption", stacks=2, duration=3))

    screen = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )

    assert "FX SHD7" in screen
    assert "FX SLN1 CRP2" in screen
    assert "TEMPO RAIL" in screen or "RAIL" in screen
    assert "STACK" in screen
    assert "ACTION HEX -> c" in screen
    assert "JUDGE  VALID | -16 HP" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= width


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_draws_skill_rail_inside_canvas(bundle, width):
    """REQ-SKILLRAIL-001: Canvas stage should show compact skill readiness chips."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.hero.mp = state.hero.max_mp
    hex_seal = state.hero.find_skill("skill_hex_seal")
    assert hex_seal is not None
    hex_seal.cooldown_remaining = 4

    screen = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )

    assert "SKILL STG* HEX4" in screen
    if width >= 100:
        assert "FOC*" in screen
    assert "ACTION HEX -> c" in screen
    assert "JUDGE  VALID | -16 HP" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= width


def test_unicode_battle_screen_adds_stagecraft_focus_markers(bundle):
    """REQ-STAGECRAFT-001: Canvas stage should visually mark actor, target, weapon, and threat."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_acolyte"])
    target = state.enemies[0]
    target.atb = 96
    target.chant_progress = 1
    record = TurnRecord(
        tick=12,
        actor_id=state.hero.id,
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_hex_seal",
            targets=(target.id,),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary=f"cast_skill skill_hex_seal -> {target.id} | 16 dmg",
            damage=16,
            target_ids=(target.id,),
            skill_id="skill_hex_seal",
            action_kind="cast_skill",
        ),
        battle_session_id="be_stagecraft",
        static_context_hash="ctx_stagecraft",
        delta_context_id="be_stagecraft_d0001",
    )

    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
        unicode_mode=True,
    )

    assert "ACT>" in screen
    assert "<TGT" in screen
    assert "RETICLE [WINDOW]" in screen
    assert "THREAT WINDOW" in screen
    assert "[W:STF] c==*" in screen
    assert "[ONLINE] shadow" in screen
    assert "░▓███░" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= 100


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_draws_enemy_intent_inside_canvas(bundle, width):
    """REQ-ENEMYINTENT-001/REQ-INTENTCLEAN-001: Canvas stage should show clean intent."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_acolyte"])
    target = state.enemies[0]
    target.atb = 88
    target.chant_charge_turns = 2
    target.chant_progress = 1
    record = TurnRecord(
        tick=12,
        actor_id=state.hero.id,
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_hex_seal",
            targets=(target.id,),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary=f"cast_skill skill_hex_seal -> {target.id} | 16 dmg",
            damage=16,
            target_ids=(target.id,),
            skill_id="skill_hex_seal",
            action_kind="cast_skill",
        ),
        battle_session_id="be_enemy_intent",
        static_context_hash="ctx_enemy_intent",
        delta_context_id="be_enemy_intent_d0001",
    )

    chanting = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "INTENT CHANT 1/2" in chanting
    assert "THREAT WINDOW 1/2" in chanting
    assert "RETICLE [WINDOW]" in chanting
    assert "ACTION HEX -> k" in chanting
    assert "JUDGE  VALID | -16 HP" in chanting

    target.atb = 100
    target.add_status(StatusEffect("status_silence", stacks=1, duration=1))
    silenced = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "INTENT SILENCED" in silenced
    assert "INTENT SILENCEDDY" not in silenced

    target.statuses.clear()
    target.chant_charge_turns = 0
    target.chant_progress = 0
    target.atb = 100
    ready_record = TurnRecord(
        tick=16,
        actor_id=state.hero.id,
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="basic_attack",
            targets=(target.id,),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="basic_attack resolved",
            summary=f"basic_attack -> {target.id} | 8 dmg",
            damage=8,
            target_ids=(target.id,),
            action_kind="basic_attack",
        ),
        battle_session_id="be_enemy_intent",
        static_context_hash="ctx_enemy_intent",
        delta_context_id="be_enemy_intent_d0002",
    )
    ready = render_battle_screen(
        state,
        ready_record,
        provider_label="mock",
        seed=1,
        language="en",
        width=width,
        unicode_mode=True,
    )
    assert "INTENT STRIKE RDY" in ready

    for screen in (chanting, silenced, ready):
        for line in screen.splitlines():
            assert visual_width(line) <= width


@pytest.mark.parametrize("language", ["en", "zh"])
@pytest.mark.parametrize("width", [80, 100, 120])
def test_battle_screen_embeds_director_strip_for_current_beat(bundle, language, width):
    """REQ-BATTLEDIR-001: battle frames expose threat, tempo, and tactical focus."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=7, language=language), seed=7, language=language)
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_priest_rite"])
    state.hero.atb = 100
    target = state.enemies[0]
    target.atb = 96
    target.chant_progress = 1
    record = TurnRecord(
        tick=137,
        actor_id=state.hero.id,
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_hex_seal",
            targets=(target.id,),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary=f"cast_skill skill_hex_seal -> {target.id} | 19 dmg",
            damage=19,
            target_ids=(target.id,),
            skill_id="skill_hex_seal",
            action_kind="cast_skill",
        ),
        battle_session_id="be_seed7_b003",
        static_context_hash="ctx_seed7",
        delta_context_id="be_seed7_b003_d0001",
    )

    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=7,
        language=language,
        width=width,
        unicode_mode=width > 88,
    )

    assert "DIRECTOR" in screen or "导演" in screen
    assert "THREAT" in screen or "威胁" in screen or "T:WIN" in screen
    assert "TEMPO" in screen or "节奏" in screen or "P:RDY" in screen
    assert "FOCUS" in screen or "焦点" in screen or "F:INT" in screen
    assert "HERO READY" in screen or "HERO_RDY" in screen or "P:RDY" in screen
    assert "interrupt chant" in screen or "打断咏唱" in screen or "INTERRUPT" in screen or "F:INT" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= width


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_draws_tempo_rail_inside_canvas(bundle, width):
    """REQ-TEMPORAIL-001: Canvas stage should draw ATB pressure as a visual rail."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=7, language="en"), seed=7, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_priest_rite"])
    state.hero.atb = 100
    target = state.enemies[0]
    target.atb = 96
    target.chant_progress = 1
    record = TurnRecord(
        tick=137,
        actor_id=state.hero.id,
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_hex_seal",
            targets=(target.id,),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary=f"cast_skill skill_hex_seal -> {target.id} | 19 dmg",
            damage=19,
            target_ids=(target.id,),
            skill_id="skill_hex_seal",
            action_kind="cast_skill",
        ),
        battle_session_id="be_temporail",
        static_context_hash="ctx_temporail",
        delta_context_id="be_temporail_d0001",
    )

    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=7,
        language="en",
        width=width,
        unicode_mode=True,
    )

    assert "RAIL" in screen
    if width > 88:
        assert "TEMPO RAIL" in screen
    assert "H100" in screen
    assert "E096" in screen
    assert "WIN" in screen
    assert "██" in screen
    assert "SEAL -19 HP" in screen
    assert "ACTION HEX -> K" in screen
    assert "JUDGE  VALID | -19 HP" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= width


@pytest.mark.parametrize("width", [80, 100, 120])
def test_unicode_battle_screen_draws_enemy_stack_inside_canvas(bundle, width):
    """REQ-ENEMYSTACK-001: Canvas stage should show the enemy pack without relying on roster text."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=2, language="en"), seed=2, language="en")
    state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    cultist = state.enemies[0]
    acolyte = state.enemies[1]
    cultist.hp = 34
    cultist.atb = 81
    acolyte.hp = 70
    acolyte.atb = 100
    record = TurnRecord(
        tick=10,
        actor_id=acolyte.id,
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "chant_charge"},
        battle_session_id="be_stack",
        static_context_hash="ctx_stack",
    )

    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=2,
        language="en",
        width=width,
        unicode_mode=True,
    )

    assert "STACK" in screen
    assert "ATB" in screen
    assert "-c" in screen
    assert ">k" in screen
    assert "RETICLE [WINDOW]" in screen
    assert "THREAT WINDOW" in screen
    assert "ENEMY ROSTER" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= width


@pytest.mark.parametrize("language", ["en", "zh"])
@pytest.mark.parametrize("width", [80, 100, 120])
def test_battle_readout_uses_beat_film_instead_of_loose_log_dump(bundle, language, width):
    """REQ-BEATFILM-001: evidence readout should present action, judge, and log as a film strip."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language=language), seed=1, language=language)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.log.extend(["Astia casts Hex Seal for 16 damage.", "Hungry Cultist is silenced."])

    screen = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language=language,
        width=width,
    )

    assert "MODEL TURN" in screen or "模型行动" in screen
    assert "BEAT FILM" in screen or "战斗分镜" in screen
    assert "[01 MODEL]" in screen or "[01 模型]" in screen
    assert "[02 JUDGE]" in screen or "[02 裁判]" in screen
    assert "[03 LOG]" in screen or "[03 战斗日志]" in screen
    assert "Hex Seal -> Hungry Cultist" in screen or "禁咒封印 -> 饥饿邪教徒" in screen
    assert "VALID | -16 HP" in screen or "有效 | -16 HP" in screen
    assert "Hungry Cultist is sil" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= width


@pytest.mark.parametrize("language", ["en", "zh"])
@pytest.mark.parametrize("width", [80, 100, 120])
def test_battle_screen_width_matrix(bundle, language, width):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language=language), seed=1, language=language)
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.enemies[0].add_status(StatusEffect("status_silence", stacks=1, duration=1))
    screen = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language=language,
        width=width,
    )

    for line in screen.splitlines():
        assert visual_width(line) <= width
    assert "status_silence" not in screen
    assert "SLN silence(1)" in screen
    if width > 88:
        assert "THE ECHO ALTAR" in screen or "回声祭坛" in screen
    assert "BATTLE THESIS" in screen or "战斗命题" in screen
    assert "ECHO READOUT" in screen or "回声读数" in screen
    assert screen.count("INTENT") <= 1
    if language == "en":
        assert "GOAL" in screen
        assert "CLOCK" in screen
        assert "NEXT" in screen
    else:
        assert "目标" in screen
        assert "威胁" in screen
        assert "下一步" in screen


@pytest.mark.parametrize("language", ["en", "zh"])
@pytest.mark.parametrize("width", [80, 100, 120])
def test_no_animation_seed7_frame_sequence_is_stable(bundle, language, width):
    """REQ-TUIQA-002: fixed seed turn frames stay deterministic and width-safe."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(
        bundle,
        MockProvider(seed=7, language=language),
        seed=7,
        language=language,
        battle_session_id="be_seed7_tuiqa",
    )
    state = loop.setup(
        "hero_shadow_apprentice",
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
    )
    captured: list[tuple[TurnRecord, str]] = []

    def capture(frame_state, record):
        if len(captured) >= 6:
            return
        captured.append(
            (
                record,
                render_battle_screen(
                    frame_state,
                    record,
                    provider_label="mock",
                    seed=7,
                    language=language,
                    width=width,
                ),
            )
        )

    loop.run(state, on_hero_turn=capture, on_enemy_turn=capture)

    signature = [
        (
            record.tick,
            record.side,
            record.actor_id,
            record.action.type if record.action else (record.enemy_action or {}).get("type"),
        )
        for record, _screen in captured
    ]
    assert signature == [
        (9, "hero", "hero_shadow_apprentice", "cast_skill"),
        (10, "enemy", "enemy_black_candle_acolyte", "chant_charge"),
        (12, "enemy", "enemy_hungry_cultist", "basic_attack"),
        (17, "hero", "hero_shadow_apprentice", "cast_skill"),
        (19, "enemy", "enemy_black_candle_acolyte", "chant_release"),
        (25, "hero", "hero_shadow_apprentice", "cast_skill"),
    ]
    for record, screen in captured:
        assert "ACTION" in screen or "行动" in screen
        if record.side == "hero":
            assert "Judge:" in screen or "裁判:" in screen
        for line in screen.splitlines():
            assert visual_width(line) <= width


def test_battle_screen_shows_tactical_resource_thresholds(bundle):
    """REQ-NUMFEED-001: HP/MP/ATB/CD/shield thresholds should be visible."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    state.hero.hp = 25
    state.hero.mp = 2
    state.hero.atb = 100
    state.hero.add_status(StatusEffect("status_shield", stacks=7, duration=2))
    skill = state.hero.find_skill("skill_hex_seal")
    assert skill is not None
    skill.cooldown_remaining = 2

    frame = build_battle_frame(state, _hex_record())
    deltas = {delta.label: delta.text for delta in frame.resource_deltas}

    assert deltas["HP"] == "25/100 | critical"
    assert deltas["MP"] == "20 -> 2 | interrupt ready: no"
    assert deltas["ATB"] == "hero ready"
    assert deltas["CD"] == "Hex Seal locked 2t"
    assert deltas["SHD"] == "7 shield | absorbs next hit"

    screen = render_battle_screen(
        state,
        _hex_record(),
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
    )

    assert "DELTA" in screen
    assert "HP 25/100 | critical" in screen
    assert "MP 20 -> 2 | interrupt ready: no" in screen
    assert "ATB hero ready" in screen
    assert "CD Hex Seal locked 2t" in screen
    assert "SHD 7 shield | absorbs next hit" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= 100


@pytest.mark.parametrize("width", [80, 100])
def test_seed7_third_battle_action_result_is_readable(bundle, width):
    """REQ-BATTLEUI-001: action, target, judge, HP/MP/ATB stay visible."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(
        bundle,
        MockProvider(seed=7, language="en"),
        seed=7,
        language="en",
        battle_session_id="be_seed7_b003",
    )
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_priest_rite"])
    state.tick = 137
    state.hero.hp = 73
    state.hero.mp = 30
    state.hero.atb = 100
    priest = state.enemies[0]
    priest.hp = 88
    priest.atb = 96
    priest.chant_progress = 1
    record = TurnRecord(
        tick=137,
        actor_id=state.hero.id,
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_hex_seal",
            targets=(priest.id,),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary=f"cast_skill skill_hex_seal -> {priest.id} | 19 dmg",
            damage=19,
            target_ids=(priest.id,),
            skill_id="skill_hex_seal",
            action_kind="cast_skill",
        ),
        battle_session_id="be_seed7_b003",
        static_context_hash="ctx_seed7",
        delta_context_id="be_seed7_b003_d0001",
    )

    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=7,
        language="en",
        width=width,
    )

    assert "ACTION" in screen
    assert "MOMENTUM BOARD" in screen
    assert "[FLOW] WINDOW" in screen
    assert "[LANE] HERO" in screen
    assert "[SWING] hero hit -19 HP" in screen
    assert "[READ] answer the window" in screen
    assert "Hex Seal -> Black Candle Priest" in screen
    assert "VALID" in screen
    assert "-19 HP" in screen
    assert "Judge:" in screen
    assert "HP [######--] 73/100" in screen
    assert "MP [##----] 30/72" in screen
    assert "ATB" in screen
    assert "COUNTER [ANSWER]" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= width


def test_battle_screen_keeps_raw_model_reasoning_out_of_main_surface(bundle):
    """REQ-MODEL-001: full model reasoning belongs in trace/replay, not the HUD."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    action = HeroAction(
        type="cast_skill",
        skill_id="skill_hex_seal",
        targets=("enemy_hungry_cultist",),
    )
    record = TurnRecord(
        tick=9,
        actor_id="hero_shadow_apprentice",
        side="hero",
        raw_text="RAW_SECRET_MODEL_CHAIN_SHOULD_STAY_IN_TRACE",
        validation=ValidationResult(
            action=action,
            narration="Astia raises the black candle.",
            analysis="RAW_SECRET_MODEL_CHAIN_SHOULD_STAY_IN_TRACE",
        ),
        action=action,
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary="cast_skill skill_hex_seal -> enemy_hungry_cultist | 16 dmg",
            damage=16,
            target_ids=("enemy_hungry_cultist",),
            skill_id="skill_hex_seal",
            action_kind="cast_skill",
        ),
        battle_session_id="be_test",
        static_context_hash="ctx_test",
        delta_context_id="be_test_d0001",
        usage_latency_ms=12,
    )

    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
    )

    assert "RAW_SECRET_MODEL_CHAIN_SHOULD_STAY_IN_TRACE" not in screen
    assert "Analysis:" not in screen
    assert "INTENT" in screen
    assert "RISK" in screen
    assert "ALIGN" in screen
    assert "Action:" in screen
    assert "Judge:" in screen


def test_battle_assets_registry_serves_pose_sprites():
    from ouro_agent.art.battle_assets import enemy_sprite, hero_sprite

    assert "candle" in " ".join(hero_sprite("hero_shadow_apprentice", "low"))
    assert "chant broken" in " ".join(enemy_sprite("k", "break"))


def test_presenter_builds_deterministic_headings():
    from ouro_agent.tui.presenter import present_battle_frame

    normal = present_battle_frame("BODY", turn_index=2, tick=17, language="en")
    thinking = present_battle_frame("BODY", turn_index=2, tick=17, thinking=True, language="zh")

    assert normal.text.startswith("--- turn 2 / tick 17 ---")
    assert "模型读取战场" in thinking.text


def test_battle_frame_flows_through_screen_model_layout_and_presenter(bundle):
    """REQ-TUIARCH-001: BattleFrame can render through model/layout/presenter."""
    from ouro_agent.tui.presenter import (
        BattleScreenModel,
        battle_screen_model_from_frame,
        present_battle_screen_model,
    )
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    record = _hex_record()
    frame = build_battle_frame(state, record)

    model = battle_screen_model_from_frame(frame, width=72)
    presented = present_battle_screen_model(model, turn_index=1, tick=frame.tick, language="en")
    compatible_screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
    )

    assert isinstance(model, BattleScreenModel)
    assert model.frame_id == frame.frame_id
    assert all(block.width == 72 for block in model.blocks)
    assert "BattleFrame ACTION" in model.text
    assert frame.action_label in model.text
    assert "Intent:" in model.text
    assert presented.text.startswith("--- turn 1 / tick 9 ---")
    assert frame.action_label in presented.text
    assert frame.action_label in compatible_screen
    for line in model.text.splitlines():
        assert visual_width(line) <= 72


def test_enemy_chant_opens_counter_window(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_acolyte"])
    record = TurnRecord(
        tick=10,
        actor_id="enemy_black_candle_acolyte",
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "chant_charge"},
        battle_session_id="be_test",
        static_context_hash="ctx_test",
    )

    frame = build_battle_frame(state, record)

    assert frame.intent == "enemy chant pressure"
    assert frame.align == "Counter window"
    assert frame.event_banner == "BREAK WINDOW OPEN"
    assert frame.counter_hint is not None
    assert frame.counter_clock is not None
    assert "COUNTER CLOCK" in frame.counter_clock
    assert "[WINDOW]" in frame.counter_hint
    assert "interrupt before release" in frame.counter_hint


def test_counter_window_sequence_shows_threat_window_and_result(bundle):
    """REQ-COUNTER-001: threat -> window -> result should be explicit."""
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_acolyte"])
    acolyte = state.enemies[0]
    acolyte.chant_progress = 1

    window_record = TurnRecord(
        tick=10,
        actor_id=acolyte.id,
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "chant_charge"},
        battle_session_id="be_counter",
        static_context_hash="ctx_counter",
    )
    answer_record = TurnRecord(
        tick=12,
        actor_id=state.hero.id,
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_hex_seal",
            targets=(acolyte.id,),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary=f"cast_skill skill_hex_seal -> {acolyte.id} | 12 dmg",
            damage=12,
            target_ids=(acolyte.id,),
            skill_id="skill_hex_seal",
            action_kind="cast_skill",
        ),
        battle_session_id="be_counter",
        static_context_hash="ctx_counter",
    )
    missed_record = TurnRecord(
        tick=14,
        actor_id=acolyte.id,
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "chant_release", "damage": 18},
        battle_session_id="be_counter",
        static_context_hash="ctx_counter",
    )

    window = build_battle_frame(state, window_record)
    answer = build_battle_frame(state, answer_record)
    missed = build_battle_frame(state, missed_record)

    assert window.event_banner == "BREAK WINDOW OPEN"
    assert window.counter_hint is not None and "[WINDOW]" in window.counter_hint
    assert answer.event_banner == "CHARGE BROKEN"
    assert answer.counter_hint is not None and "[ANSWER]" in answer.counter_hint
    assert missed.event_banner == "CHANT RELEASED"
    assert missed.counter_hint is not None and "[MISSED]" in missed.counter_hint

    screen = render_battle_screen(
        state,
        window_record,
        provider_label="mock",
        seed=1,
        language="en",
        width=100,
    )

    assert "COUNTER CLOCK" in screen
    assert "[WINDOW]" in screen
    assert "interrupt before release" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= 100


def test_boss_frame_exposes_phase_charge_break_enrage(bundle):
    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_high_priest_archive"])
    boss = state.enemies[0]
    boss.hp = boss.max_hp // 2
    boss.chant_progress = 1
    state.tick = 320
    record = TurnRecord(
        tick=320,
        actor_id=boss.id,
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "chant_charge"},
        battle_session_id="be_boss",
        static_context_hash="ctx_boss",
    )

    frame = build_battle_frame(state, record)

    assert frame.event_banner == "BOSS CHARGE"
    assert frame.boss_intel is not None
    assert "Phase II" in frame.boss_intel.phase
    assert "Charge 1/2" in frame.boss_intel.charge
    assert "Break OPEN" in frame.boss_intel.break_state
    assert "Enrage rising" in frame.boss_intel.enrage
    assert frame.counter_hint is not None
    assert "[WINDOW]" in frame.counter_hint


def test_boss_battle_screen_shows_special_intel_without_width_drift(bundle):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_high_priest_archive"])
    boss = state.enemies[0]
    boss.hp = boss.max_hp // 2
    boss.chant_progress = 1
    state.tick = 320
    record = TurnRecord(
        tick=320,
        actor_id=boss.id,
        side="enemy",
        raw_text=None,
        validation=None,
        action=None,
        judge=None,
        enemy_action={"type": "chant_charge"},
        battle_session_id="be_boss",
        static_context_hash="ctx_boss",
    )

    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=7,
        language="en",
        width=100,
    )

    assert "BOSS" in screen
    assert "Phase II" in screen
    assert "Charge 1/2" in screen
    assert "BREAK" in screen
    assert "ENRAGE" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= 100


def test_boss_phase_crossing_raises_climax_banner(bundle):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_high_priest_archive"])
    boss = state.enemies[0]
    boss.hp = 120
    state.tick = 240
    record = TurnRecord(
        tick=240,
        actor_id=state.hero.id,
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_shadow_sting",
            targets=(boss.id,),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary=f"cast_skill skill_shadow_sting -> {boss.id} | 30 dmg",
            damage=30,
            target_ids=(boss.id,),
            skill_id="skill_shadow_sting",
            action_kind="cast_skill",
        ),
    )

    frame = build_battle_frame(state, record)
    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=7,
        language="en",
        width=100,
    )

    assert frame.event_banner == "BOSS PHASE II"
    assert frame.counter_clock is None
    assert "BOSS PHASE II" in screen


def test_climax_banners_cover_kill_and_build_online(bundle):
    """REQ-CLIMAX-001/REQ-BUILDCLIMAX-001: Build and kill events keep distinct beats."""
    from ouro_agent.engine import resolve_build
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_hungry_cultist"])
    build = resolve_build(bundle.get_hero("hero_shadow_apprentice"), bundle)
    opening = render_battle_screen(
        state,
        None,
        provider_label="mock",
        seed=7,
        language="en",
        width=100,
        bundle=bundle,
        build=build,
    )
    assert "EVENT   BUILD ONLINE" in opening or "EVENT   HIGH ROLL" in opening

    state.log.append("Tick 9 Astia casts Hex Seal.")
    later_wait = render_battle_screen(
        state,
        None,
        provider_label="mock",
        seed=7,
        language="en",
        width=100,
        bundle=bundle,
        build=build,
    )
    assert "EVENT   BUILD ONLINE" not in later_wait
    assert "EVENT   HIGH ROLL" not in later_wait

    enemy = state.enemies[0]
    enemy.hp = 0
    record = TurnRecord(
        tick=36,
        actor_id=state.hero.id,
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="basic_attack",
            targets=(enemy.id,),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="basic_attack resolved",
            summary=f"basic_attack -> {enemy.id} | 10 dmg",
            damage=10,
            target_ids=(enemy.id,),
            action_kind="basic_attack",
        ),
    )

    frame = build_battle_frame(state, record)
    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=7,
        language="en",
        width=100,
        bundle=bundle,
        build=build,
    )

    assert frame.event_banner == "KILL CONFIRMED"
    assert "EVENT   KILL CONFIRMED" in screen
    assert "EVENT   BUILD ONLINE" not in screen
    assert "EVENT   HIGH ROLL" not in screen
    for line in (*opening.splitlines(), *later_wait.splitlines(), *screen.splitlines()):
        assert visual_width(line) <= 100


def test_tower_brace_counter_renders_boss_break(bundle):
    from ouro_agent.tui.screens import render_battle_screen

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_ash_guardian", ["enemy_black_candle_high_priest_archive"])
    boss = state.enemies[0]
    boss.hp = 170
    boss.chant_progress = 0
    boss.add_status(StatusEffect("status_silence", stacks=1, duration=2))
    record = TurnRecord(
        tick=180,
        actor_id=state.hero.id,
        side="hero",
        raw_text=None,
        validation=None,
        action=HeroAction(
            type="cast_skill",
            skill_id="skill_tower_brace",
            targets=(state.hero.id,),
        ),
        judge=JudgeOutcome(
            valid=True,
            reason="cast_skill resolved",
            summary=f"cast_skill skill_tower_brace -> {state.hero.id},{boss.id} | 25 dmg",
            damage=25,
            target_ids=(state.hero.id, boss.id),
            skill_id="skill_tower_brace",
            action_kind="cast_skill",
        ),
    )

    frame = build_battle_frame(state, record)
    screen = render_battle_screen(
        state,
        record,
        provider_label="mock",
        seed=7,
        language="en",
        width=100,
    )

    assert frame.event_banner == "BOSS BREAK"
    assert frame.counter_hint is not None
    assert "tower counter" in frame.counter_hint
    assert "BOSS BREAK" in screen
    assert "Break BROKEN" in screen
    for line in screen.splitlines():
        assert visual_width(line) <= 100


def test_tactical_diagnosis_counts_missed_counter_and_low_tempo(bundle):
    from ouro_agent.tui.report_analysis import analyze_battle_tactics, render_tactical_diagnosis

    loop = BattleLoop(bundle, MockProvider(seed=1, language="en"), seed=1, language="en")
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_acolyte"])
    records = [
        TurnRecord(
            tick=5,
            actor_id="enemy_black_candle_acolyte",
            side="enemy",
            raw_text=None,
            validation=None,
            action=None,
            judge=None,
            enemy_action={"type": "chant_charge"},
        ),
        TurnRecord(
            tick=8,
            actor_id="hero_shadow_apprentice",
            side="hero",
            raw_text=None,
            validation=None,
            action=HeroAction(type="defend"),
            judge=JudgeOutcome(
                valid=True,
                reason="defend stance",
                summary="defend | shield +4 (2 turns)",
                action_kind="defend",
            ),
        ),
        TurnRecord(
            tick=11,
            actor_id="hero_shadow_apprentice",
            side="hero",
            raw_text=None,
            validation=None,
            action=HeroAction(
                type="cast_skill",
                skill_id="skill_hex_seal",
                targets=("enemy_black_candle_acolyte",),
            ),
            judge=JudgeOutcome(
                valid=False,
                reason="insufficient MP (1/4)",
                summary="Mana too low.",
                damage=0,
                target_ids=("enemy_black_candle_acolyte",),
                skill_id="skill_hex_seal",
                action_kind="cast_skill",
            ),
        ),
        TurnRecord(
            tick=14,
            actor_id="enemy_black_candle_acolyte",
            side="enemy",
            raw_text=None,
            validation=None,
            action=None,
            judge=None,
            enemy_action={"type": "chant_release", "damage": 18},
        ),
    ]

    diagnosis = analyze_battle_tactics(state, records, language="en")
    rendered = "\n".join(render_tactical_diagnosis(diagnosis, language="en"))

    assert diagnosis.mp_dry_turns == 1
    assert diagnosis.low_impact_turns == 1
    assert diagnosis.counter_windows_opened == 1
    assert diagnosis.counter_windows_missed == 1
    assert "MP dry turns: 1" in rendered
    assert "1 missed" in rendered
    assert "Problem:" in rendered
    assert "Next Build Pick:" in rendered


def test_all_hero_core_poses_have_ascii_sprites():
    from ouro_agent.art.battle_assets import HERO_SPRITES, hero_sprite

    required = ("idle", "attack", "skill", "defend", "hit", "low", "victory", "defeat")
    for hero_id in HERO_SPRITES:
        for pose in required:
            sprite = hero_sprite(hero_id, pose)
            assert len(sprite) >= 4
            assert "\n".join(sprite).isascii()


def test_reusable_art_assets_cover_mvp_heroes_enemies_and_weapons(bundle):
    """REQ-TUICANVAS-002: sprites and weapon card art live in art registries."""
    from ouro_agent.art.battle_assets import ENEMY_SPRITES, HERO_SPRITES, enemy_sprite, hero_sprite
    from ouro_agent.art.block_sprites import (
        ENEMY_BLOCK_SPRITES,
        HERO_BLOCK_SPRITES,
        enemy_block_sprite,
        hero_block_sprite,
    )
    from ouro_agent.art.weapon_cards import HERO_WEAPON_CARDS, hero_weapon_card, hero_weapon_card_art

    required_poses = ("idle", "attack", "skill", "defend", "hit", "low", "victory", "defeat")
    for hero_id in bundle.heroes:
        assert hero_id in HERO_SPRITES
        assert hero_id in HERO_BLOCK_SPRITES
        assert hero_id in HERO_WEAPON_CARDS
        weapon, badge = hero_weapon_card(hero_id)
        card_art = hero_weapon_card_art(hero_id)
        assert weapon.startswith("[W:")
        assert badge.startswith("[")
        assert card_art.icon.startswith("[W:")
        assert card_art.badge.startswith("[")
        assert len(card_art.ascii_art) >= 3
        assert len(card_art.unicode_art) >= 3
        assert "\n".join(card_art.ascii_art).isascii()
        assert "AI " in card_art.ai_effect
        assert "[" in card_art.build_shift and "]" in card_art.build_shift
        for pose in required_poses:
            ascii_sprite = hero_sprite(hero_id, pose)
            block_sprite = hero_block_sprite(hero_id, pose)
            assert len(ascii_sprite) >= 4
            assert len(block_sprite) >= 4
            assert "\n".join(ascii_sprite).isascii()
            assert all(visual_width(line) <= 8 for line in block_sprite)

    for enemy in bundle.enemies.values():
        assert enemy.short_glyph in ENEMY_SPRITES
        assert enemy.short_glyph in ENEMY_BLOCK_SPRITES
        ascii_sprite = enemy_sprite(enemy.short_glyph, "idle")
        block_sprite = enemy_block_sprite(enemy.short_glyph, "idle")
        assert len(ascii_sprite) >= 4
        assert len(block_sprite) >= 4
        assert "\n".join(ascii_sprite).isascii()
        assert all(visual_width(line) <= 8 for line in block_sprite)
