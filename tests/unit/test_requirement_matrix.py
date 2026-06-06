from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "docs/product/06_需求追踪矩阵_20260503.md"
QA_NOTE = ROOT / "docs/product/23_QA证据与固定Seed试玩记录_20260601.md"


def _requirement_rows() -> list[list[str]]:
    rows: list[list[str]] = []
    for line in MATRIX.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| REQ-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 9:
            rows.append(cells)
    return rows


def test_done_requirements_have_replayable_evidence():
    """REQ-QA-001: done rows must point to tests, traces, commands, or notes."""
    evidence_markers = (
        "tests/",
        "pytest",
        "venv312/bin/ouro",
        "ouro ",
        "trace",
        ".trace.jsonl",
        "render_",
        "git diff --check",
        "输出",
        "快照",
        "人工试玩",
        "docs/product/23_",
        "examples/",
    )
    forbidden_placeholders = ("tbd", "todo", "待补", "占位")
    done_rows = [row for row in _requirement_rows() if row[-1] == "done"]

    assert done_rows
    for row in done_rows:
        req_id = row[0]
        evidence = row[5]
        assert any(marker in evidence for marker in evidence_markers), req_id
        assert not any(marker in evidence.lower() for marker in forbidden_placeholders), req_id


def test_qa_note_records_fixed_seed_evidence_and_manual_template():
    """REQ-QA-001: QA note keeps command evidence and human playtest structure."""
    text = QA_NOTE.read_text(encoding="utf-8")

    assert "venv312/bin/python -m pytest" in text
    assert "369 passed" in text
    assert "scripts/release_check.py --evidence-only" in text
    assert "Evidence counts OK: 369 tests collected; 247 release-bound text files." in text
    assert "scripts/release_scope.py --stage-plan" in text
    assert "test_release_scope_prints_read_only_stage_plan_without_mutating_index" in text
    assert "scripts/acceptance_check.py" in text
    assert "test_acceptance_check_runs_review_commands_without_signing_off" in text
    assert "venv312/bin/ouro validate-content" in text
    assert "git diff --check" in text
    assert "venv312/bin/ouro menu --lang en" in text
    assert "New Run        ouro run --mock" in text
    assert "/private/tmp/ouro_install_smoke_20260601/bin/ouro --version" in text
    assert "share/ouro-agent/content" in text
    assert "venv312/bin/ouro --lang en run --mock --seed 7 --no-animation --auto --no-trace" in text
    assert "test_interactive_run_abort_returns_code_without_system_exit" in text
    assert "test_content_dir_help_describes_installed_fallback" in text
    assert "test_cli_runs_shows_persisted_archives" in text
    assert "test_release_handoff_covers_tag_install_smoke_and_privacy" in text
    assert "test_pyproject_packaging_file_references_exist" in text
    assert "test_final_product_audit_tracks_evidence_and_remaining_risks" in text
    assert "test_manual_playtest_note_records_full_run_observations" in text
    assert "test_changeset_manifest_defines_release_boundary_and_local_excludes" in text
    assert "test_release_check_script_documents_and_dry_runs_repo_root_gates" in text
    assert "test_config_preflight_redacts_env_value_and_reports_ready" in text
    assert "test_provider_preflight_ready_for_configured_compatible_without_network" in text
    assert "test_doctor_reports_real_provider_preflight_without_leaking_env" in text
    assert "docs/product/25_人工试玩记录_20260601.md" in text
    assert "Warning: could not save Codex progress" in text
    assert "Metric keys: tempo_outlier=0, mp_dry_turns=0, defense_loop_turns=0, boss_break_missed=0" in text
    assert "boss_break_missed=10" in text
    assert "日期:" in text
    assert "结论: pass / fail" in text
