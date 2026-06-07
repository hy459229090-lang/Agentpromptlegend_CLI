"""Slice C-GameUI: Codex (图鉴) functionality tests.

Tests for:
- CodexStage enum
- CodexEntry and CodexProgress tracking
- Codex card rendering with fog/mist for locked information
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.cli.main import main
from ouro_agent.content import CodexStage, load_content_bundle
from ouro_agent.sessions import (
    CodexStoreError,
    CodexEntry,
    CodexProgress,
    codex_stage_badge,
    codex_stage_label,
    codex_path,
    load_codex_progress,
    record_battle_codex,
    save_codex_progress,
)
from ouro_agent.i18n import visual_width


@pytest.fixture()
def bundle(content_root: Path):
    return load_content_bundle(content_root)


def test_codex_stage_from_encounters():
    """Codex stage should be calculated from encounter and defeat counts."""
    assert CodexStage.from_encounters(0, 0) == CodexStage.UNKNOWN
    assert CodexStage.from_encounters(1, 0) == CodexStage.OBSERVED
    assert CodexStage.from_encounters(5, 1) == CodexStage.OBSERVED
    assert CodexStage.from_encounters(5, 2) == CodexStage.FAMILIAR
    assert CodexStage.from_encounters(10, 4) == CodexStage.FAMILIAR
    assert CodexStage.from_encounters(10, 5) == CodexStage.MASTERED
    assert CodexStage.from_encounters(20, 9) == CodexStage.MASTERED
    assert CodexStage.from_encounters(20, 10) == CodexStage.HUNTED


def test_codex_entry_tracking():
    """CodexEntry should track encounters and defeats."""
    entry = CodexEntry(family_id="family_black_candle")
    assert entry.encounters == 0
    assert entry.defeats == 0
    assert entry.stage == CodexStage.UNKNOWN

    entry.record_encounter()
    assert entry.encounters == 1
    assert entry.stage == CodexStage.OBSERVED

    entry.record_defeat()
    assert entry.defeats == 1
    assert entry.stage == CodexStage.OBSERVED

    entry.record_defeat()
    assert entry.defeats == 2
    assert entry.stage == CodexStage.FAMILIAR


def test_codex_progress_tracking():
    """CodexProgress should track multiple families."""
    progress = CodexProgress()

    progress.record_encounter("family_black_candle")
    progress.record_defeat("family_black_candle")
    progress.record_defeat("family_black_candle")

    entry = progress.get_entry("family_black_candle")
    assert entry.encounters == 1
    assert entry.defeats == 2
    assert entry.stage == CodexStage.FAMILIAR

    progress.record_encounter("family_hungry_cultist")
    entry2 = progress.get_entry("family_hungry_cultist")
    assert entry2.stage == CodexStage.OBSERVED


def test_codex_progress_tracks_family_tier_independently():
    """REQ-CODEX-001: Codex knowledge is scoped by family+tier."""
    progress = CodexProgress()

    progress.record_encounter("family_black_candle", "trace")

    assert progress.get_stage("family_black_candle", "trace") == CodexStage.OBSERVED
    assert progress.get_stage("family_black_candle", "ritebound") == CodexStage.UNKNOWN

    data = progress.to_dict()
    assert "family_black_candle:trace" in data["entries"]
    assert data["entries"]["family_black_candle:trace"]["tier"] == "trace"

    restored = CodexProgress.from_dict(data)
    assert restored.get_stage("family_black_candle", "trace") == CodexStage.OBSERVED
    assert restored.get_stage("family_black_candle", "ritebound") == CodexStage.UNKNOWN


def test_codex_entry_serialization():
    """CodexEntry should be serializable to dict and back."""
    entry = CodexEntry(family_id="family_black_candle", encounters=3, defeats=2)
    data = entry.to_dict()
    assert data["family_id"] == "family_black_candle"
    assert data["encounters"] == 3
    assert data["defeats"] == 2

    restored = CodexEntry.from_dict(data)
    assert restored.family_id == "family_black_candle"
    assert restored.encounters == 3
    assert restored.defeats == 2
    assert restored.stage == CodexStage.FAMILIAR


def test_codex_progress_serialization():
    """CodexProgress should be serializable to dict and back."""
    progress = CodexProgress()
    progress.record_encounter("family_black_candle")
    progress.record_defeat("family_black_candle")
    progress.record_defeat("family_black_candle")
    progress.record_encounter("family_hungry_cultist")

    data = progress.to_dict()
    restored = CodexProgress.from_dict(data)

    assert restored.get_stage("family_black_candle") == CodexStage.FAMILIAR
    assert restored.get_stage("family_hungry_cultist") == CodexStage.OBSERVED


def test_codex_progress_store_round_trip(isolated_home):
    """REQ-CODEX-002: codex progress persists locally without secrets."""
    progress = CodexProgress()
    progress.record_encounter("family_black_candle", "trace")
    progress.record_defeat("family_black_candle", "trace")

    path = save_codex_progress(progress)
    restored = load_codex_progress()
    text = path.read_text(encoding="utf-8")

    assert path == codex_path()
    assert restored.get_stage("family_black_candle", "trace") == CodexStage.OBSERVED
    assert "family_black_candle" in text
    assert "sk-" not in text


def test_codex_store_rejects_invalid_json(tmp_path: Path):
    bad = tmp_path / "codex.json"
    bad.write_text("{not-json}", encoding="utf-8")

    with pytest.raises(CodexStoreError):
        load_codex_progress(bad)


def test_codex_store_wraps_write_failures(tmp_path: Path):
    """REQ-CODEX-002: persistence failures become readable domain errors."""
    blocked = tmp_path / "codex-as-directory"
    blocked.mkdir()

    with pytest.raises(CodexStoreError, match="cannot write codex save"):
        save_codex_progress(CodexProgress(), blocked)


def test_record_battle_codex_tracks_encounter_and_defeat(bundle):
    """REQ-CODEX-002: battle results feed reusable family+tier progress."""
    progress = CodexProgress()

    record_battle_codex(
        progress,
        bundle,
        ["enemy_hungry_cultist", "enemy_black_candle_acolyte"],
        {"enemy_hungry_cultist"},
    )

    hungry = progress.find_entry("family_hungry_cultist", "trace")
    candle = progress.find_entry("family_black_candle", "trace")
    assert hungry is not None
    assert hungry.encounters == 1
    assert hungry.defeats == 1
    assert candle is not None
    assert candle.encounters == 1
    assert candle.defeats == 0


def test_saved_codex_progress_enters_next_battle_prompt(bundle, isolated_home):
    """REQ-CODEX-002: persisted codex stages are visible to the next prompt."""
    from ouro_agent.engine.battle import BattleLoop
    from ouro_agent.llm.prompt import compose_prompt
    from ouro_agent.providers.mock import MockProvider

    progress = CodexProgress()
    progress.record_encounter("family_black_candle", "trace")
    save_codex_progress(progress)

    restored = load_codex_progress()
    loop = BattleLoop(
        bundle,
        MockProvider(seed=1, language="en"),
        seed=1,
        language="en",
        codex_progress=restored,
    )
    state = loop.setup("hero_shadow_apprentice", ["enemy_black_candle_acolyte"])
    prompt = compose_prompt(
        state,
        bundle,
        battle_session=loop.battle_llm_session,
    )

    system_text = prompt.system_text()
    assert "Interrupt works" in system_text
    assert "Resist: shadow 10%" not in system_text


def test_cli_codex_shows_persisted_summary(bundle, content_root, isolated_home, capsys):
    """REQ-LONGVIEW-001: players can inspect durable Codex progress."""
    progress = CodexProgress()
    progress.record_encounter("family_black_candle", "trace")
    save_codex_progress(progress)

    rc = main(["codex", "--lang", "en", "--content-dir", str(content_root)])
    out = capsys.readouterr().out

    assert rc == 0
    assert f"Codex : {codex_path()}" in out
    assert "CODEX :: MONSTER ARCHIVE" in out
    assert "Observed: 1/9" in out
    assert "[OB] [k] Black Candle Acolyte [I: Trace]" in out
    assert "[??] [K] ???? [II: Ritebound]" in out


def test_cli_codex_shows_persisted_detail(content_root, isolated_home, capsys):
    """REQ-LONGVIEW-001: players can open a specific monster card."""
    progress = CodexProgress()
    progress.record_encounter("family_black_candle", "trace")
    save_codex_progress(progress)

    rc = main(
        [
            "codex",
            "enemy_black_candle_acolyte",
            "--lang",
            "en",
            "--content-dir",
            str(content_root),
        ]
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert f"Codex : {codex_path()}" in out
    assert "EVENT: CODEX REVEAL [OB]" in out
    assert "Black Candle Acolyte" in out
    assert "Family: Black Candle" in out
    assert "Encounters: 1" in out
    assert "family_" not in out


def test_cli_codex_accepts_public_card_code(content_root, isolated_home, capsys):
    """REQ-CODEXATLAS-001: monster cards can be opened without internal IDs."""
    progress = CodexProgress()
    progress.record_encounter("family_black_candle", "trace")
    save_codex_progress(progress)

    rc = main(
        [
            "codex",
            "k",
            "--lang",
            "en",
            "--content-dir",
            str(content_root),
        ]
    )
    out = capsys.readouterr().out

    assert rc == 0
    assert f"Codex : {codex_path()}" in out
    assert "EVENT: CODEX REVEAL [OB]" in out
    assert "Black Candle Acolyte" in out
    assert "Family: Black Candle" in out
    assert "Encounters: 1" in out
    assert "family_" not in out


def test_prompt_codex_visibility_is_stage_and_tier_limited(bundle):
    """REQ-CODEX-001: Hidden codex stages must not enter model prompts."""
    from ouro_agent.engine.battle import BattleLoop
    from ouro_agent.llm.prompt import compose_prompt
    from ouro_agent.providers.mock import MockProvider

    def progress_for(encounters: int, defeats: int) -> CodexProgress:
        progress = CodexProgress()
        for _ in range(encounters):
            progress.record_encounter("family_black_candle", "trace")
        for _ in range(defeats):
            progress.record_defeat("family_black_candle", "trace")
        return progress

    def prompt_system(enemy_id: str, progress: CodexProgress | None) -> str:
        loop = BattleLoop(
            bundle,
            MockProvider(seed=1, language="en"),
            seed=1,
            language="en",
            codex_progress=progress,
        )
        state = loop.setup("hero_shadow_apprentice", [enemy_id])
        prompt = compose_prompt(
            state,
            bundle,
            battle_session=loop.battle_llm_session,
        )
        return prompt.system_text()

    unknown = prompt_system("enemy_black_candle_acolyte", None)
    assert "A robed acolyte mid-chant" in unknown
    assert "Interrupt works" not in unknown
    assert "Resist: shadow 10%" not in unknown
    assert "Build hint: control/interrupt" not in unknown

    observed = prompt_system("enemy_black_candle_acolyte", progress_for(1, 0))
    assert "Interrupt works" in observed
    assert "Resist: shadow 10%" not in observed
    assert "Build hint: control/interrupt" not in observed

    familiar = prompt_system("enemy_black_candle_acolyte", progress_for(5, 2))
    assert "Resist: shadow 10%" in familiar
    assert "Build hint: control/interrupt" not in familiar

    mastered = prompt_system("enemy_black_candle_acolyte", progress_for(10, 5))
    assert "Build hint: control/interrupt" in mastered

    ritebound = prompt_system("enemy_black_candle_priest_rite", progress_for(10, 5))
    assert "A taller figure with multiple black candles" in ritebound
    assert "Priests cast longer" not in ritebound


def test_codex_stage_label():
    """Codex stage labels should be available in English and Chinese."""
    assert codex_stage_label(CodexStage.UNKNOWN, "en") == "Unknown"
    assert codex_stage_label(CodexStage.UNKNOWN, "zh") == "未知"
    assert codex_stage_label(CodexStage.OBSERVED, "en") == "Observed"
    assert codex_stage_label(CodexStage.OBSERVED, "zh") == "观察"
    assert codex_stage_label(CodexStage.MASTERED, "en") == "Mastered"
    assert codex_stage_label(CodexStage.MASTERED, "zh") == "掌握"


def test_codex_stage_badge():
    """Codex stage badges should be short codes."""
    assert codex_stage_badge(CodexStage.UNKNOWN) == "[??]"
    assert codex_stage_badge(CodexStage.OBSERVED) == "[OB]"
    assert codex_stage_badge(CodexStage.FAMILIAR) == "[FM]"
    assert codex_stage_badge(CodexStage.MASTERED) == "[MS]"
    assert codex_stage_badge(CodexStage.HUNTED) == "[HT]"


def test_codex_card_unknown(bundle):
    """REQ-GAMEUI-003: Unknown monsters should show only silhouette."""
    from ouro_agent.tui.screens import render_codex_card

    card = render_codex_card(
        "enemy_black_candle_acolyte",
        bundle,
        codex_progress=None,
        language="en",
    )

    assert "[??]" in card
    assert "UNKNOWN FAMILY" in card
    assert "FOG SILHOUETTE" in card
    assert "COUNTER PLAN BOARD" in card
    assert "[THREAT] ????? / encounter to reveal" in card
    assert "[BUILD] ????? / keep flexible" in card
    assert "░░░" in card
    assert "never encountered" in card


def test_codex_card_observed(bundle):
    """REQ-GAMEUI-003: Observed monsters should show name and basic info."""
    from ouro_agent.tui.screens import render_codex_card

    progress = CodexProgress()
    progress.record_encounter("family_black_candle")

    card = render_codex_card(
        "enemy_black_candle_acolyte",
        bundle,
        codex_progress=progress,
        language="en",
    )

    assert "[OB]" in card
    assert "EVENT: CODEX REVEAL [OB]" in card
    assert "BLOCK SILHOUETTE" in card
    assert "BLOCK SILHOUETTE / CODEX REVEAL" in card
    assert "▐▓k▓▌" in card
    assert "▐CDX▌" in card
    assert "Black Candle Acolyte" in card
    assert "Observed" in card
    assert "COUNTER PLAN BOARD" in card
    assert "[THREAT] chant burst / 14 damage" in card
    assert "[WINDOW] fogged / survive one more read" in card
    assert "[BUILD] locked / reach MASTERED" in card
    assert "[BUILD] control + silence + holy" not in card
    assert "Encounters: 1" in card
    assert "Defeats: 0" in card
    assert "Next: defeat 2 more" in card
    assert all(visual_width(line) <= 60 for line in card.splitlines())


def test_codex_card_familiar(bundle):
    """REQ-GAMEUI-003: Familiar monsters should show behavior."""
    from ouro_agent.tui.screens import render_codex_card

    progress = CodexProgress()
    progress.record_encounter("family_black_candle")
    progress.record_defeat("family_black_candle")
    progress.record_defeat("family_black_candle")

    card = render_codex_card(
        "enemy_black_candle_acolyte",
        bundle,
        codex_progress=progress,
        language="en",
    )

    assert "[FM]" in card
    assert "Familiar" in card
    assert "Behavior:" in card
    assert "MECHANIC READ: telegraph / break / punish" in card
    assert "[WINDOW] chant 1 turn(s) / interrupt or silence" in card
    assert "[BUILD] locked / reach MASTERED" in card
    assert "Defeats: 2" in card
    assert "Next: defeat 3 more" in card


def test_codex_card_mastered(bundle):
    """REQ-GAMEUI-003: Mastered monsters should show full stats."""
    from ouro_agent.tui.screens import render_codex_card

    progress = CodexProgress()
    for _ in range(5):
        progress.record_encounter("family_black_candle")
        progress.record_defeat("family_black_candle")

    card = render_codex_card(
        "enemy_black_candle_acolyte",
        bundle,
        codex_progress=progress,
        language="en",
    )

    assert "[MS]" in card
    assert "Mastered" in card
    assert "ATK:" in card
    assert "DEF:" in card
    assert "POW:" in card
    assert "WEAKNESS MAP: interrupt windows and build tags known" in card
    assert "[BUILD] control + silence + holy" in card
    assert "Defeats: 5" in card
    assert "Next: defeat 5 more" in card


def test_codex_card_hunted(bundle):
    """REQ-GAMEUI-003: Hunted monsters should show MAX STAGE."""
    from ouro_agent.tui.screens import render_codex_card

    progress = CodexProgress()
    for _ in range(10):
        progress.record_encounter("family_black_candle")
        progress.record_defeat("family_black_candle")

    card = render_codex_card(
        "enemy_black_candle_acolyte",
        bundle,
        codex_progress=progress,
        language="en",
    )

    assert "[HT]" in card
    assert "Hunted" in card
    assert "[LOOP] reserve counter every 2 beats" in card
    assert "MAX STAGE" in card


def test_codex_summary(bundle):
    """Codex summary should list all monsters with badges."""
    from ouro_agent.tui.screens import render_codex_summary

    progress = CodexProgress()
    progress.record_encounter("family_black_candle")

    summary = render_codex_summary(
        bundle,
        codex_progress=progress,
        language="en",
    )

    assert "CODEX" in summary
    assert "Total: 9 monsters" in summary
    assert "Observed: 3/9" in summary
    assert "CODEX HUNT BOARD" in summary
    assert "Gaps: unknown 6 / familiar 9 / mastered 9" in summary
    assert "Threat pool: chant 3 / fast 3 / brawler 3" in summary
    assert "Priority target: [??] Hungry Cultist" in summary
    assert "Card c" in summary
    assert "Next: ouro codex <card> for counter plan" in summary
    assert "MONSTER GALLERY BOARD" in summary
    assert "[??] [c] ???? [I: Trace]" in summary
    assert "  Family:" in summary
    assert "  Behavior:" in summary
    assert "  Silhouette:" in summary
    assert "  Card: c | -> encounter once" in summary
    assert "[OB] [k] Black Candle Acolyte [I: Trace]" in summary
    assert "Silhouette: ~(k)~" in summary
    assert "Card: k | -> defeat to familiar" in summary
    assert "Next: ouro codex <card> for counter plan" in summary
    assert "Hungry Cultist" in summary
    assert "Black Candle Acolyte" in summary
    assert "enemy_" not in summary
    assert all(visual_width(line) <= 80 for line in summary.splitlines())


def test_codex_summary_counts_family_tier_progress(bundle):
    """REQ-CODEX-001: Summary counts concrete family+tier unlocks."""
    from ouro_agent.tui.screens import render_codex_summary

    progress = CodexProgress()
    progress.record_encounter("family_black_candle", "trace")

    summary = render_codex_summary(
        bundle,
        codex_progress=progress,
        language="en",
    )

    assert "Observed: 1/9" in summary
    assert "Gaps: unknown 8 / familiar 9 / mastered 9" in summary
    assert "Priority target: [??] Hungry Cultist" in summary
    assert "Card c" in summary
    assert "MONSTER GALLERY BOARD" in summary
    assert "[OB] [k] Black Candle Acolyte [I: Trace]" in summary
    assert "Card: k | -> defeat to familiar" in summary
    assert "[??] [K] ???? [II: Ritebound]" in summary
    assert "[??] [B] ???? [III: Archive-Bound]" in summary
    assert "enemy_" not in summary


def test_codex_summary_no_progress(bundle):
    """Codex summary without progress should show all unknown."""
    from ouro_agent.tui.screens import render_codex_summary

    summary = render_codex_summary(
        bundle,
        codex_progress=None,
        language="en",
    )

    assert "CODEX" in summary
    assert "Total: 9 monsters" in summary
    assert "Observed: 0/9" in summary
    assert "CODEX HUNT BOARD" in summary
    assert "MONSTER GALLERY BOARD" in summary
    assert "Gaps: unknown 9 / familiar 9 / mastered 9" in summary
    assert "Threat pool: chant 3 / fast 3 / brawler 3" in summary
    assert "[??] [c] ???? [I: Trace]" in summary
    assert "[??]" in summary
    assert "Next: ouro codex <card> for counter plan" in summary
    assert "Monsters:" not in summary
    assert "enemy_" not in summary


def test_codex_summary_zh_gallery_board(bundle):
    """Chinese codex summary should keep the gallery board readable and command hints."""
    from ouro_agent.tui.screens import render_codex_summary

    progress = CodexProgress()
    progress.record_encounter("family_black_candle", "trace")

    summary = render_codex_summary(
        bundle,
        codex_progress=progress,
        language="zh",
    )

    assert "CODEX :: MONSTER ARCHIVE" in summary or "图鉴 :: 怪物档案" in summary
    assert "图鉴 :: 怪物档案" in summary
    assert "CODEX HUNT BOARD :: 图鉴狩猎板" in summary
    assert "怪物图鉴画廊" in summary
    assert "优先目标:" in summary
    assert "卡片 c" in summary
    assert "下一步: ouro codex <卡片> 查看反制计划" in summary
    assert "  家系: 黑烛教团" in summary
    assert "  行为: 吟唱" in summary
    assert "  剪影: ~(k)~" in summary
    assert "  卡片: k | -> 击败至熟悉" in summary
    assert "  Family:" not in summary
    assert "  Behavior:" not in summary
    assert "  Silhouette:" not in summary
    assert "enemy_" not in summary
