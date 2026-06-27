from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.art.sprite_atlas import SpriteAtlas
from ouro_agent.cli.main import main
from ouro_agent.config import OuroConfig
from ouro_agent.content import load_content_bundle, validate_asset_manifest
from ouro_agent.sessions import (
    CodexProgress,
    RunArchiveError,
    RunPhase,
    append_death_history,
    build_run_archive,
    death_history_path,
    load_death_history,
    load_run_archives,
    run_archive_dir,
    save_codex_progress,
    save_run_archive,
)
from ouro_agent.sessions.run_state import create_run_state
from ouro_agent.tui.screens import render_progress_status


@pytest.fixture()
def bundle(content_root: Path):
    return load_content_bundle(content_root)


def _atlas(content_root: Path, bundle) -> SpriteAtlas:
    report = validate_asset_manifest(content_root, bundle)
    return SpriteAtlas.from_manifest_report(report)


def test_run_archive_captures_result_build_resources_and_codex(bundle, isolated_home):
    """REQ-RUNSAVE-001: completed runs write a local, replayable summary."""
    state = create_run_state(
        "run_archive",
        11,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    state.phase = RunPhase.COMPLETE
    state.battle_result = "victory"
    state.gold = 25
    state.xp = 10
    state.completed_node_ids.append("node_ember_crypt_f1_n1")
    state.record_codex_battle(
        bundle,
        ["enemy_hungry_cultist"],
        {"enemy_hungry_cultist"},
    )

    path = save_run_archive(state, bundle)
    archive = build_run_archive(state, bundle)
    text = path.read_text(encoding="utf-8")

    assert path == run_archive_dir() / "run_archive.run.json"
    assert archive["result"] == "complete"
    assert archive["build"]["stage_badge"].startswith("[")
    assert archive["gold"] == 25
    assert archive["completed_node_ids"] == ["node_ember_crypt_f1_n1"]
    assert "family_hungry_cultist" in text
    assert "sk-" not in text


def test_cli_runs_shows_persisted_archives(bundle, content_root, isolated_home, capsys):
    """REQ-LONGVIEW-002: players can review all saved run archives from the CLI."""
    complete = create_run_state(
        "run_complete",
        21,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    complete.phase = RunPhase.COMPLETE
    complete.battle_result = "victory"
    complete.battles_won = 3
    complete.gold = 40
    complete.xp = 12
    complete.completed_node_ids.append("node_ember_crypt_f1_n1")

    dead = create_run_state(
        "run_dead",
        22,
        "hero_ash_guardian",
        "dungeon_ember_crypt",
        bundle,
    )
    dead.phase = RunPhase.DEAD
    dead.battle_result = "defeat"
    dead.battles_won = 1
    dead.battles_lost = 1
    dead.current_hp = 0

    complete_path = save_run_archive(complete, bundle)
    save_run_archive(dead, bundle)

    archives = load_run_archives()
    rc = main(["runs", "--lang", "en", "--limit", "5", "--content-dir", str(content_root)])
    out = capsys.readouterr().out

    assert rc == 0
    assert len(archives) == 2
    assert f"Run Archives: {run_archive_dir()}" in out
    assert "RUN ARCHIVE :: ALL RUNS" in out
    assert "Total: 2" in out
    assert "RUN ARCHIVE BOARD" in out
    assert "[RESULTS] complete 1 / dead 1" in out
    assert "[BEST] seed 21 / 3W/0L" in out
    assert "[LATEST] seed 22 / dead" in out
    assert "[REPORT] ouro run-report" in out
    assert "run_complete" in out
    assert "Result: complete" in out
    assert "run_dead" in out
    assert "Result: dead" in out
    assert "Hero: Astia" in out
    assert "Hero: Norn" in out
    assert "Resources: HP 0/" in out
    assert ".run.json" in out

    rc_runs_zh = main(["runs", "--lang", "zh", "--limit", "5", "--content-dir", str(content_root)])
    zh_runs = capsys.readouterr().out

    assert rc_runs_zh == 0
    assert f"运行归档: {run_archive_dir()}" in zh_runs
    assert "运行归档 :: 全部记录" in zh_runs
    assert "总计: 2" in zh_runs
    assert "显示: 2" in zh_runs
    assert "运行归档面板" in zh_runs
    assert "[结果] 通关 1 / 陨落 1" in zh_runs
    assert "[最佳] seed 21 / 3胜/0负" in zh_runs
    assert "[最近] seed 22 / 陨落" in zh_runs
    assert "[报告] ouro run-report" in zh_runs
    assert "种子: 22  结果: 陨落  阶段: 陨落" in zh_runs
    assert "英雄: 诺恩" in zh_runs
    assert "副本: 灰烬墓室" in zh_runs
    assert "战斗: 1胜/1负" in zh_runs
    assert "资源: HP 0/" in zh_runs
    assert "构筑: 铁壁反击" in zh_runs
    assert "归档:" in zh_runs
    assert "Run Archives:" not in zh_runs
    assert "RUN ARCHIVE BOARD" not in zh_runs
    assert "[RESULTS]" not in zh_runs
    assert "[BEST]" not in zh_runs
    assert "[LATEST]" not in zh_runs
    assert "[REPORT]" not in zh_runs
    assert "Seed:" not in zh_runs
    assert "Result:" not in zh_runs
    assert "Phase:" not in zh_runs
    assert "Hero:" not in zh_runs
    assert "Dungeon:" not in zh_runs
    assert "Battles:" not in zh_runs
    assert "Nodes:" not in zh_runs
    assert "Gold:" not in zh_runs
    assert "Resources:" not in zh_runs
    assert "Build:" not in zh_runs
    assert "Archive:" not in zh_runs

    rc_report = main(["run-report", "--lang", "en", "--content-dir", str(content_root)])
    report = capsys.readouterr().out

    assert rc_report == 0
    assert f"Run Archives: {run_archive_dir()}" in report
    assert "RUN REPORT :: LAST ECHO" in report
    assert "VISUAL ANCHORS" in report
    assert "[RESULT] BMP hero defeat | fallback cell.hero_ash_guardian.defeat" in report
    assert "[STAGE] BMP dungeon background | fallback cell.dungeon_ember_crypt.background" in report
    assert "[RESULT] BMP reward lock | fallback cell.ui.reward_card.lock" in report
    assert "SUMMARY" in report
    assert "run_dead" in report
    assert "Seed: 22  Result: dead  Phase: dead" in report
    assert "Hero: Norn" in report
    assert "Floor reached:" in report
    assert "BUILD" in report
    assert "PROGRESSION" in report
    assert "Codex: Observed" in report
    assert "NEXT RUN LOADOUT" in report
    assert "[PROMPT] control / reduce boss tempo risk" in report
    assert "[SEED] 23 / fixed retry sample" in report
    assert "[CODEX] patch" in report
    assert "[ROUTE] rest/shop before boss pressure" in report
    assert "NEXT RUN" in report
    assert "Takeaway: fell after 1 wins" in report
    assert "Retry: ouro run --mock --prompt-style control --seed 23" in report
    assert "sk-" not in report

    rc_path_report = main(
        [
            "run-report",
            str(complete_path),
            "--lang",
            "en",
            "--content-dir",
            str(content_root),
        ]
    )
    path_report = capsys.readouterr().out

    assert rc_path_report == 0
    assert f"Run Archive: {complete_path}" in path_report
    assert "VISUAL ANCHORS" in path_report
    assert "[RESULT] BMP hero victory | fallback cell.hero_shadow_apprentice.victory" in path_report
    assert "[RESULT] BMP reward high | fallback cell.ui.reward_card.high" in path_report
    assert "run_complete" in path_report
    assert "Seed: 21  Result: complete  Phase: complete" in path_report
    assert "[PROMPT] guarded / validate under higher pressure" in path_report
    assert "[ROUTE] try elite or event greed line" in path_report
    assert "Pressure: ouro run --mock --prompt-style guarded --seed 22" in path_report

    rc_report_zh = main(["run-report", "--lang", "zh", "--content-dir", str(content_root)])
    zh_report = capsys.readouterr().out

    assert rc_report_zh == 0
    assert f"运行归档: {run_archive_dir()}" in zh_report
    assert "运行报告 :: 最近回响" in zh_report
    assert "视觉锚点" in zh_report
    assert "[结算] BMP 英雄 defeat | fallback cell.hero_ash_guardian.defeat" in zh_report
    assert "[场景] BMP 地牢 background | fallback cell.dungeon_ember_crypt.background" in zh_report
    assert "[结算] BMP 奖励 lock | fallback cell.ui.reward_card.lock" in zh_report
    assert "运行: run_dead" in zh_report
    assert "种子: 22  结果: 陨落  阶段: 陨落" in zh_report
    assert "英雄: 诺恩" in zh_report
    assert "资源: HP 0/" in zh_report
    assert "金币" in zh_report
    assert "原型: 铁壁反击" in zh_report
    assert "阶段:" in zh_report
    assert "提示词:" in zh_report
    assert "标签:" in zh_report
    assert "共鸣:" in zh_report
    assert "路径:" in zh_report
    assert "归档:" in zh_report
    assert "图鉴: 已观察" in zh_report
    assert "获得: 金币" in zh_report
    assert "[提示词] control / 降低首领前节奏风险" in zh_report
    assert "[种子] 23 / 固定样本复验" in zh_report
    assert "[图鉴] 补" in zh_report
    assert "[路线] 首领前优先休整/商店" in zh_report
    assert "重试: ouro run --mock --prompt-style control --seed 23" in zh_report
    assert "复盘: ouro history --lang zh --limit 3" in zh_report
    assert "Run Archives:" not in zh_report
    assert "Run:" not in zh_report
    assert "Seed:" not in zh_report
    assert "Result:" not in zh_report
    assert "Phase:" not in zh_report
    assert "Gold" not in zh_report
    assert "Prompt:" not in zh_report
    assert "Path:" not in zh_report
    assert "Archive:" not in zh_report
    assert "Codex: Observed" not in zh_report
    assert "Earned:" not in zh_report
    assert "[PROMPT]" not in zh_report
    assert "[SEED]" not in zh_report
    assert "[CODEX]" not in zh_report
    assert "[ROUTE]" not in zh_report
    assert "Retry:" not in zh_report
    assert "Review:" not in zh_report


def test_cli_runs_shows_empty_state(content_root, isolated_home, capsys):
    """REQ-LONGVIEW-002: empty run archive has a readable state."""
    rc = main(["runs", "--lang", "en", "--content-dir", str(content_root)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "RUN ARCHIVE :: ALL RUNS" in out
    assert "Total: 0" in out
    assert "No run archives recorded yet." in out

    rc_report = main(["run-report", "--lang", "en", "--content-dir", str(content_root)])
    report = capsys.readouterr().out

    assert rc_report == 0
    assert "RUN REPORT :: LAST ECHO" in report
    assert "No saved run archive yet." in report
    assert "Start: ouro run --mock --seed 7" in report


def test_run_report_next_loadout_width_matrix(bundle, content_root: Path):
    from ouro_agent.i18n import visual_width
    from ouro_agent.sessions import build_run_archive
    from ouro_agent.tui.screens import render_run_report

    state = create_run_state(
        "run_report_loadout",
        31,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    state.phase = RunPhase.DEAD
    state.battle_result = "defeat"
    state.battles_won = 2
    state.battles_lost = 1
    state.current_hp = 0
    entry = build_run_archive(state, bundle)
    atlas = _atlas(content_root, bundle)

    for width in (80, 100, 120):
        report = render_run_report(entry, bundle, language="en", width=width)
        assert "NEXT RUN LOADOUT" in report
        assert "[PROMPT] control" in report
        assert all(visual_width(line) <= width for line in report.splitlines())

    report_with_assets = render_run_report(
        entry,
        bundle,
        language="en",
        width=120,
        asset_atlas=atlas,
        unicode_mode=True,
    )
    assert "VISUAL ANCHORS" in report_with_assets
    assert "[RESULT] BMP hero defeat | fallback cell.hero_shadow_apprentice.defeat" in report_with_assets
    assert "[STAGE] BMP dungeon background | fallback cell.dungeon_ember_crypt.background" in report_with_assets
    assert "[RESULT] BMP reward lock | fallback cell.ui.reward_card.lock" in report_with_assets
    assert all(visual_width(line) <= 120 for line in report_with_assets.splitlines())

    zh_report = render_run_report(entry, bundle, language="zh", width=80)
    assert "下一局配置" in zh_report
    assert "[提示词] control" in zh_report
    assert "[种子] 32" in zh_report
    assert "[图鉴] 补" in zh_report
    assert "[路线] 首领前优先休整/商店" in zh_report
    assert "重试: ouro run --mock --prompt-style control --seed 32" in zh_report
    assert "[PROMPT]" not in zh_report
    assert "[SEED]" not in zh_report
    assert "[CODEX]" not in zh_report
    assert "[ROUTE]" not in zh_report
    assert all(visual_width(line) <= 80 for line in zh_report.splitlines())


def test_run_archive_wraps_write_failures(bundle, tmp_path: Path):
    """REQ-RUNSAVE-001: archive write failures stay user-readable."""
    state = create_run_state(
        "run_archive_blocked",
        14,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("blocked", encoding="utf-8")

    with pytest.raises(RunArchiveError, match="cannot write run archive"):
        save_run_archive(state, bundle, blocked)


def test_death_history_appends_dead_runs_only(bundle, isolated_home):
    """REQ-RUNSAVE-001: deaths and timeouts leave a durable history entry."""
    dead = create_run_state(
        "run_dead",
        12,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    dead.phase = RunPhase.DEAD
    dead.battle_result = "defeat"
    dead.battles_lost = 1

    complete = create_run_state(
        "run_complete",
        13,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    complete.phase = RunPhase.COMPLETE

    path = append_death_history(dead, bundle)
    skipped = append_death_history(complete, bundle)
    history = load_death_history()

    assert path == death_history_path()
    assert skipped is None
    assert len(history) == 1
    assert history[0]["run_id"] == "run_dead"
    assert history[0]["battle_result"] == "defeat"
    assert history[0]["battles_lost"] == 1


def test_cli_history_shows_persisted_deaths(bundle, content_root, isolated_home, capsys):
    """REQ-LONGVIEW-001: players can review fallen runs from the CLI."""
    dead = create_run_state(
        "run_dead",
        12,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    dead.phase = RunPhase.DEAD
    dead.battle_result = "defeat"
    dead.battles_lost = 1
    dead.completed_node_ids.append("node_ember_crypt_f1_n1")
    append_death_history(dead, bundle)

    rc = main(["history", "--lang", "en", "--content-dir", str(content_root)])
    out = capsys.readouterr().out

    assert rc == 0
    assert f"Death History: {death_history_path()}" in out
    assert "DEATH HISTORY :: FALLEN RUNS" in out
    assert "DEATH REVIEW BOARD" in out
    assert "[SAMPLES] 1 fallen runs" in out
    assert "[LATEST] seed 12 / 0W" in out
    assert "[DEEPEST] seed 12 / 0W" in out
    assert "[RETRY] ouro run --mock --prompt-style control --seed 13" in out
    assert "[1] run_dead" in out
    assert "Seed: 12  Result: defeat" in out
    assert "Hero: Astia" in out
    assert "Dungeon: Ember Crypt" in out
    assert "Battles: 0W/1L  Nodes: 1" in out
    assert "Path: Hungry Followers" in out

    rc_zh = main(["history", "--lang", "zh", "--content-dir", str(content_root)])
    zh_out = capsys.readouterr().out

    assert rc_zh == 0
    assert f"陨落历史: {death_history_path()}" in zh_out
    assert "死亡历史 :: 陨落记录" in zh_out
    assert "总计: 1" in zh_out
    assert "显示: 1" in zh_out
    assert "陨落复盘板" in zh_out
    assert "[样本] 1 次陨落" in zh_out
    assert "[最近] seed 12 / 0胜" in zh_out
    assert "[最深] seed 12 / 0胜" in zh_out
    assert "[重试] ouro run --mock --prompt-style control --seed 13" in zh_out
    assert "[1] run_dead" in zh_out
    assert "种子: 12  结果: 失败" in zh_out
    assert "英雄: 阿斯缇娅" in zh_out
    assert "副本: 灰烬墓室" in zh_out
    assert "战斗: 0胜/1负  节点: 1" in zh_out
    assert "构筑: 黑烛打断" in zh_out
    assert "路径: 饥饿信徒" in zh_out
    assert "Death History:" not in zh_out
    assert "DEATH REVIEW BOARD" not in zh_out
    assert "[SAMPLES]" not in zh_out
    assert "[LATEST]" not in zh_out
    assert "[DEEPEST]" not in zh_out
    assert "[RETRY]" not in zh_out
    assert "Seed:" not in zh_out
    assert "Result:" not in zh_out
    assert "Hero:" not in zh_out
    assert "Dungeon:" not in zh_out
    assert "Battles:" not in zh_out
    assert "Nodes:" not in zh_out
    assert "Build:" not in zh_out
    assert "Path:" not in zh_out


def test_cli_history_shows_empty_state(content_root, isolated_home, capsys):
    """REQ-LONGVIEW-001: empty death history has a readable state."""
    rc = main(["history", "--lang", "en", "--content-dir", str(content_root)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "DEATH HISTORY :: FALLEN RUNS" in out
    assert "Total: 0" in out
    assert "No fallen runs recorded yet." in out


def test_cli_status_summarizes_progress_and_next_commands(
    bundle,
    content_root,
    isolated_home,
    capsys,
):
    """REQ-LONGVIEW-003: returning players get one progress overview."""
    config = OuroConfig(provider="mock", model="mock-smart", language="en")
    empty_status = render_progress_status(
        config,
        bundle,
        CodexProgress(),
        [],
        [],
        config_path="/tmp/ouro/status/config.toml",
        codex_save_path="/tmp/ouro/status/codex.json",
        run_archive_path="/tmp/ouro/status/runs",
        death_history_save_path="/tmp/ouro/status/death_history.json",
        language="en",
        width=100,
    )
    assert "LEGEND PROGRESS MAP" in empty_status
    assert "[CODEX] [----------] mastered 0/9" in empty_status
    assert "[RUNS]  [----------] complete 0/0 / dead 0" in empty_status
    assert "[READY] [----------] next-run signals 0/3" in empty_status
    assert "NEXT RUN PLAN" in empty_status
    assert "NEXT RUN CONTROL" in empty_status
    assert "Start fast: ouro try --seed 1" in empty_status
    assert "First run: ouro run --mock --seed 7" in empty_status
    assert "[PROMPT] default / establish first baseline" in empty_status
    assert "[RUN] ouro run --mock --seed 7" in empty_status

    complete = create_run_state(
        "run_status_complete",
        41,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    complete.phase = RunPhase.COMPLETE
    complete.battle_result = "victory"
    complete_status = render_progress_status(
        config,
        bundle,
        CodexProgress(),
        [build_run_archive(complete, bundle)],
        [],
        config_path="/tmp/ouro/status/config.toml",
        codex_save_path="/tmp/ouro/status/codex.json",
        run_archive_path="/tmp/ouro/status/runs",
        death_history_save_path="/tmp/ouro/status/death_history.json",
        language="en",
        width=100,
    )
    assert "Compare winning builds: ouro runs --lang en --limit 5" in complete_status
    assert "[PROMPT] guarded / pressure validation" in complete_status
    assert "[ROUTE] elite/event greed line" in complete_status
    assert "New pressure seed: ouro run --mock --prompt-style guarded --seed 42" in (
        complete_status
    )

    dead = create_run_state(
        "run_status_dead",
        31,
        "hero_shadow_apprentice",
        "dungeon_ember_crypt",
        bundle,
    )
    dead.phase = RunPhase.DEAD
    dead.battle_result = "defeat"
    dead.battles_won = 2
    dead.battles_lost = 1
    dead.current_hp = 0
    dead.completed_node_ids.append("node_ember_crypt_f1_n1")
    dead.record_codex_battle(
        bundle,
        ["enemy_hungry_cultist"],
        {"enemy_hungry_cultist"},
    )
    save_codex_progress(dead.codex_progress)
    save_run_archive(dead, bundle)
    append_death_history(dead, bundle)

    rc = main(["status", "--lang", "en", "--content-dir", str(content_root)])
    out = capsys.readouterr().out

    assert rc == 0
    assert "OURO STATUS :: ECHO LEDGER" in out
    assert "PROFILE" in out
    assert "Provider: mock" in out
    assert "LOCAL FILES" in out
    assert "PROGRESS" in out
    assert "LEGEND PROGRESS MAP" in out
    assert "Observed 1/9" in out
    assert "[RISK]  [##########] fall pressure 1/1" in out
    assert "[READY] [##########] next-run signals 3/3" in out
    assert "Runs: 1 total  0 complete  1 dead" in out
    assert "Fallen Runs: 1" in out
    assert "LAST RUN" in out
    assert "run_status_dead" in out
    assert "Seed: 31  Result: dead  Phase: dead" in out
    assert "Hero: Astia" in out
    assert "Resources: HP 0/" in out
    assert "NEXT RUN PLAN" in out
    assert "NEXT RUN CONTROL" in out
    assert "Review fall #1" in out
    assert "ouro history --lang en --limit 3" in out
    assert "ouro run --mock --prompt-style control --seed 32" in out
    assert "Patch 8 Codex gaps" in out
    assert "[PROMPT] control / reduce enemy tempo" in out
    assert "[SEED] 32 / fixed retry sample" in out
    assert "[ROUTE] rest/shop before boss pressure" in out
    assert "rest/shop before boss" in out
    assert "NEXT COMMANDS" in out
    assert "ouro run --mock" in out
    assert "ouro codex --lang en" in out
    assert "sk-" not in out

    rc = main(["status", "--lang", "zh", "--content-dir", str(content_root)])
    zh_out = capsys.readouterr().out

    assert rc == 0
    assert "OURO :: 回响总览" in zh_out
    assert "档案" in zh_out
    assert "供应商: mock" in zh_out
    assert "模型: mock-smart" in zh_out
    assert "密钥: mock-ready" in zh_out
    assert "本地文件" in zh_out
    assert "配置:" in zh_out
    assert "运行归档:" in zh_out
    assert "陨落历史:" in zh_out
    assert "进度" in zh_out
    assert "已观察 1/9" in zh_out
    assert "运行: 1 次  通关 0  陨落 1" in zh_out
    assert "陨落记录: 1" in zh_out
    assert "传奇进度地图" in zh_out
    assert "[图鉴] [----------] 已掌握 0/9 / 已追猎 0/9" in zh_out
    assert "[风险] [##########] 陨落压力 1/1" in zh_out
    assert "[准备] [##########] 下局信号 3/3" in zh_out
    assert "最近运行" in zh_out
    assert "种子: 31  结果: 陨落  阶段: 陨落" in zh_out
    assert "英雄: 阿斯缇娅" in zh_out
    assert "战斗: 2胜/1负" in zh_out
    assert "资源: HP 0/" in zh_out
    assert "构筑: 黑烛打断" in zh_out
    assert "下一局计划" in zh_out
    assert "首领前优先休整/商店" in zh_out
    assert "下一局控制台" in zh_out
    assert "[提示词] control / 降低敌方节奏" in zh_out
    assert "[种子] 32 / 固定重试样本" in zh_out
    assert "[路线] 首领前找休整/商店" in zh_out
    assert "下一步命令" in zh_out
    assert "Provider:" not in zh_out
    assert "Model:" not in zh_out
    assert "Key:" not in zh_out
    assert "Language:" not in zh_out
    assert "Visual:" not in zh_out
    assert "Config:" not in zh_out
    assert "Run Archives:" not in zh_out
    assert "Death History:" not in zh_out
    assert "Observed" not in zh_out
    assert "Familiar" not in zh_out
    assert "Mastered" not in zh_out
    assert "Runs:" not in zh_out
    assert "Fallen Runs:" not in zh_out
    assert "LEGEND PROGRESS MAP" not in zh_out
    assert "mastered" not in zh_out
    assert "hunted" not in zh_out
    assert "complete" not in zh_out
    assert "Result: dead" not in zh_out
    assert "Phase: dead" not in zh_out
    assert "fall pressure" not in zh_out
    assert "next-run signals" not in zh_out
    assert "Seed:" not in zh_out
    assert "Result:" not in zh_out
    assert "Phase:" not in zh_out
    assert "Hero:" not in zh_out
    assert "Dungeon:" not in zh_out
    assert "Battles:" not in zh_out
    assert "Nodes:" not in zh_out
    assert "Gold:" not in zh_out
    assert "Resources:" not in zh_out
    assert "Build:" not in zh_out
    assert "[PROMPT]" not in zh_out
    assert "[SEED]" not in zh_out
    assert "[CODEX]" not in zh_out
    assert "[ROUTE]" not in zh_out


def test_death_history_rejects_invalid_json(tmp_path: Path):
    bad = tmp_path / "death_history.json"
    bad.write_text("{not-json}", encoding="utf-8")

    with pytest.raises(RunArchiveError):
        load_death_history(bad)


def test_run_archives_reject_invalid_json(tmp_path: Path):
    bad_dir = tmp_path / "runs"
    bad_dir.mkdir()
    (bad_dir / "run_bad.run.json").write_text("{not-json}", encoding="utf-8")

    with pytest.raises(RunArchiveError):
        load_run_archives(bad_dir)
