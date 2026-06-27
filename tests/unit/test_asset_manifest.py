"""REQ-ASSETGEN-001 asset manifest coverage and QA gates."""
from __future__ import annotations

import binascii
import subprocess
import sys
import json
import shutil
import struct
import zlib
from pathlib import Path

import pytest
import yaml

from ouro_agent.content import (
    ContentError,
    build_asset_pipeline_report,
    build_asset_qa_template,
    build_asset_work_orders,
    load_asset_brief_catalog,
    load_asset_manifest,
    load_content_bundle,
    validate_asset_qa_records,
    validate_asset_manifest,
)


ROOT = Path(__file__).resolve().parents[2]


def test_asset_manifest_covers_current_mvp_content(content_root: Path):
    bundle = load_content_bundle(content_root)
    report = validate_asset_manifest(content_root, bundle)

    assert report.ok
    assert report.total_assets == 82
    assert report.counts_by_type == {
        "affix": 12,
        "dungeon": 1,
        "enemy": 9,
        "hero": 6,
        "item": 15,
        "node_type": 5,
        "resonance": 5,
        "skill": 18,
        "ui_state": 11,
    }
    assert all(not values for values in report.missing_by_type.values())
    assert all(not values for values in report.unexpected_by_type.values())

    manifest = report.manifest
    brief_catalog = report.brief_catalog
    assert manifest.runtime_policy["image_generation"] == "development_only"
    assert manifest.runtime_policy["runtime_network"] == "disabled"
    assert manifest.runtime_policy["qa_required_for_runtime"] is True
    assert manifest.runtime_policy["fallback_required"] is True
    assert len(brief_catalog.families) == 10
    assert len(brief_catalog.aliases) == report.total_assets
    assert set(brief_catalog.aliases) == {asset.source_brief for asset in manifest.assets}
    assert all(family.negative_prompt for family in brief_catalog.families.values())
    assert all("logo" in family.negative_prompt for family in brief_catalog.families.values())
    assert all(family.qa_checks for family in brief_catalog.families.values())
    assert all(asset.source_brief for asset in manifest.assets)
    assert all(asset.frames for asset in manifest.assets)
    assert all(frame.fallback_cell_id for asset in manifest.assets for frame in asset.frames)
    manifest_asset_ids = [asset.asset_id for asset in manifest.assets]
    runtime_assets = [asset for asset in manifest.assets if asset.runtime_enabled]
    assert [asset.asset_id for asset in runtime_assets] == manifest_asset_ids
    assert all(asset.qa_status == "qa_passed" for asset in runtime_assets)
    assert all(asset.path.endswith("/cut_metadata.yaml") for asset in runtime_assets)


def test_asset_brief_catalog_maps_aliases_to_manifest(content_root: Path):
    manifest = load_asset_manifest(content_root)
    catalog = load_asset_brief_catalog(content_root)

    for asset in manifest.assets:
        alias = catalog.aliases[asset.source_brief]
        assert alias.source_type == asset.source_type
        assert alias.source_content_id == asset.source_content_id
        family = catalog.families[alias.family]
        assert asset.source_type in family.source_types
        assert "terminal" in family.prompt.lower() or "terminal" in family.terminal_target.lower()
        assert "brand replica" in family.negative_prompt


def test_asset_manifest_rejects_runtime_assets_before_qa(tmp_path: Path):
    _write_manifest(
        tmp_path,
        qa_status="planned",
        runtime_enabled="true",
        path="sprites/hero.png",
    )

    with pytest.raises(ContentError, match="qa_status 'qa_passed'"):
        load_asset_manifest(tmp_path)


def test_asset_manifest_rejects_missing_frame_metadata(tmp_path: Path):
    _write_manifest(
        tmp_path,
        frame="frame_id: idle\n        anchor: [1, 1]\n        duration_ms: 80",
    )

    with pytest.raises(ContentError, match="fallback_cell_id"):
        load_asset_manifest(tmp_path)


def test_asset_manifest_script_reports_full_coverage():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/asset_manifest_check.py",
            "--content-dir",
            "content",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "asset manifest: OK" in result.stdout
    assert "assets: 82" in result.stdout
    assert "brief families: 10" in result.stdout
    assert "source briefs: 82" in result.stdout
    assert "hero: 6" in result.stdout
    assert "skill: 18" in result.stdout
    assert "ui_state: 11" in result.stdout
    assert "coverage: full current MVP content" in result.stdout
    assert "development-only ImageGen" in result.stdout


def test_asset_work_orders_cover_every_manifest_asset(content_root: Path):
    bundle = load_content_bundle(content_root)
    report = validate_asset_manifest(content_root, bundle)
    work_orders = build_asset_work_orders(report)

    assert len(work_orders) == report.total_assets == 82
    assert {order.asset_id for order in work_orders} == {
        asset.asset_id for asset in report.manifest.assets
    }
    assert all(order.runtime_policy == "development_only" for order in work_orders)
    assert all(order.candidate_storage == "scratch_only_until_qa" for order in work_orders)
    assert all("brand replica" in order.negative_prompt for order in work_orders)
    assert all(order.fallback_cell_ids for order in work_orders)

    hex_seal = next(order for order in work_orders if order.asset_id == "skill_hex_seal_effect_sheet")
    assert hex_seal.family == "skill_effect_sheet"
    assert hex_seal.source_content_id == "skill_hex_seal"
    assert "Required frames:" in hex_seal.prompt
    assert "hit_stop" in hex_seal.prompt


def test_asset_work_order_script_outputs_summary_and_jsonl(tmp_path: Path):
    summary = subprocess.run(
        [
            sys.executable,
            "scripts/asset_work_orders.py",
            "--content-dir",
            "content",
            "--format",
            "summary",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert summary.returncode == 0, summary.stdout + summary.stderr
    assert "asset work orders: OK" in summary.stdout
    assert "work orders: 82" in summary.stdout
    assert "scratch-only candidates" in summary.stdout
    assert "hero_actor_sheet: 6" in summary.stdout
    assert "skill_effect_sheet: 18" in summary.stdout

    output = tmp_path / "orders.jsonl"
    jsonl = subprocess.run(
        [
            sys.executable,
            "scripts/asset_work_orders.py",
            "--content-dir",
            "content",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert jsonl.returncode == 0, jsonl.stdout + jsonl.stderr
    assert "wrote 82" in jsonl.stdout
    rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 82
    assert rows[0]["runtime_policy"] == "development_only"
    assert rows[0]["candidate_storage"] == "scratch_only_until_qa"
    assert "negative_prompt" in rows[0]


def test_asset_candidate_intake_template_has_frame_metadata(content_root: Path):
    bundle = load_content_bundle(content_root)
    manifest_report = validate_asset_manifest(content_root, bundle)
    template = build_asset_qa_template(
        manifest_report,
        work_order_id="wo_skill_hex_seal_effect_sheet",
        candidate_id="cand_hex_seal_001",
        candidate_ref="generated-cache://hex_seal_001",
    )

    assert template.asset_id == "skill_hex_seal_effect_sheet"
    assert template.qa_status == "generated"
    assert template.candidate_ref == "generated-cache://hex_seal_001"
    frame_ids = [frame.frame_id for frame in template.frame_metadata]
    assert frame_ids == [
        "idle",
        "windup",
        "seal_spawn",
        "travel_mid",
        "travel_near",
        "hit_stop",
        "damage_pop",
        "settle",
        "recover",
        "dissolve",
        "trail",
        "impact",
    ]
    assert all(frame.anchor == (80, 32) for frame in template.frame_metadata)
    assert all(frame.duration_ms == 80 for frame in template.frame_metadata)
    assert template.frame_metadata[0].fallback_cell_id == "cell.skill_hex_seal.idle"
    assert template.frame_metadata[-1].fallback_cell_id == "cell.skill_hex_seal.impact"
    assert all(value is False for value in template.checks.values())


def test_asset_candidate_intake_script_outputs_valid_generated_record(tmp_path: Path):
    output = tmp_path / "hex_seal_candidate.yaml"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/asset_candidate_intake.py",
            "--content-dir",
            "content",
            "--work-order-id",
            "wo_skill_hex_seal_effect_sheet",
            "--candidate-id",
            "cand_hex_seal_001",
            "--candidate-ref",
            "generated-cache://hex_seal_001",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "wrote template" in result.stdout
    text = output.read_text(encoding="utf-8")
    assert "asset_id: skill_hex_seal_effect_sheet" in text
    assert "qa_status: generated" in text
    assert "frame_id: hit_stop" in text
    assert "fallback_cell_id: cell.skill_hex_seal.hit_stop" in text

    qa_result = subprocess.run(
        [
            sys.executable,
            "scripts/asset_qa_check.py",
            "--content-dir",
            "content",
            "--records-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert qa_result.returncode == 0, qa_result.stdout + qa_result.stderr
    assert "records: 1" in qa_result.stdout
    assert "generated: 1" in qa_result.stdout


def test_asset_sheet_cut_slices_candidate_to_scratch_frames(tmp_path: Path):
    sheet = tmp_path / "candidate_sheet.png"
    _write_test_sheet_png(sheet)
    output_dir = tmp_path / "cut"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/asset_sheet_cut.py",
            "--content-dir",
            "content",
            "--work-order-id",
            "wo_item_cracked_wand_icon_card",
            "--candidate-id",
            "cand_item_cracked_wand_sheet_001",
            "--candidate-png",
            str(sheet),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "asset sheet cut: OK" in result.stdout
    assert "frames_written: 3" in result.stdout
    assert "ignored_cells: 1" in result.stdout
    assert "runtime promotion: disabled until QA passes" in result.stdout

    metadata_path = (
        output_dir
        / "item_cracked_wand_icon_card"
        / "cand_item_cracked_wand_sheet_001"
        / "cut_metadata.yaml"
    )
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    assert metadata["asset_id"] == "item_cracked_wand_icon_card"
    assert metadata["runtime_promoted"] is False
    assert metadata["ignored_cells"] == 1
    assert [frame["frame_id"] for frame in metadata["frames"]] == [
        "icon",
        "card",
        "hud_mark",
    ]
    assert metadata["frames"][0]["visible_bbox"] == [4, 3, 10, 8]
    assert metadata["frames"][1]["visible_bbox"] == [5, 2, 13, 9]
    assert metadata["frames"][2]["visible_bbox"] == [6, 3, 16, 10]
    assert all(Path(frame["path"]).is_file() for frame in metadata["frames"])
    assert all(
        frame["fallback_cell_id"].startswith("cell.item_cracked_wand.")
        for frame in metadata["frames"]
    )


def test_asset_sheet_cut_can_select_noncontiguous_cells(tmp_path: Path):
    sheet = tmp_path / "candidate_sheet.png"
    _write_test_sheet_png(sheet)
    output_dir = tmp_path / "cut"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/asset_sheet_cut.py",
            "--content-dir",
            "content",
            "--work-order-id",
            "wo_item_cracked_wand_icon_card",
            "--candidate-id",
            "cand_item_cracked_wand_sheet_002",
            "--candidate-png",
            str(sheet),
            "--output-dir",
            str(output_dir),
            "--cols",
            "2",
            "--rows",
            "2",
            "--cell-indices",
            "0,1,3",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "frames_written: 3" in result.stdout
    assert "ignored_cells: 1" in result.stdout

    metadata_path = (
        output_dir
        / "item_cracked_wand_icon_card"
        / "cand_item_cracked_wand_sheet_002"
        / "cut_metadata.yaml"
    )
    metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
    assert metadata["selected_cell_indices"] == [0, 1, 3]
    assert [frame["grid_cell"] for frame in metadata["frames"]] == [
        [0, 0],
        [1, 0],
        [1, 1],
    ]
    assert metadata["frames"][2]["visible_bbox"] == [4, 4, 15, 9]


def test_asset_sheet_cut_refuses_content_assets_output(tmp_path: Path):
    sheet = tmp_path / "candidate_sheet.png"
    _write_test_sheet_png(sheet)
    forbidden = ROOT / "content" / "assets" / "generated_metadata" / "bad_candidate"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/asset_sheet_cut.py",
            "--content-dir",
            "content",
            "--work-order-id",
            "wo_item_cracked_wand_icon_card",
            "--candidate-id",
            "cand_bad_runtime_write",
            "--candidate-png",
            str(sheet),
            "--output-dir",
            str(forbidden),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "refusing to write generated frames under content/assets" in result.stderr
    assert not forbidden.exists()


def test_asset_promote_candidate_script_copies_runtime_and_writes_qa(
    content_root: Path, tmp_path: Path
):
    isolated_content = tmp_path / "content"
    shutil.copytree(content_root, isolated_content)
    bundle = load_content_bundle(isolated_content)
    manifest_report = validate_asset_manifest(isolated_content, bundle)
    asset = next(
        item for item in manifest_report.manifest.assets
        if item.asset_id == "item_cracked_wand_icon_card"
    )
    work_order = next(
        order for order in build_asset_work_orders(manifest_report)
        if order.asset_id == asset.asset_id
    )
    cut_metadata = _write_promotable_cut_metadata(
        tmp_path / "candidate_cut",
        asset,
        work_order,
        candidate_id="cand_item_cracked_wand_promote_001",
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/asset_promote_candidate.py",
            "--content-dir",
            str(isolated_content),
            "--cut-metadata",
            str(cut_metadata),
            "--reviewer",
            "art-pipeline-test",
            "--reviewed-at",
            "2026-06-17T00:00:00Z",
            "--approve-all-checks",
            "--replace",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "asset candidate promotion: OK" in result.stdout
    assert "frames_promoted: 3" in result.stdout
    runtime_metadata = (
        isolated_content
        / "assets"
        / "runtime"
        / asset.asset_id
        / "cand_item_cracked_wand_promote_001"
        / "cut_metadata.yaml"
    )
    metadata = yaml.safe_load(runtime_metadata.read_text(encoding="utf-8"))
    assert metadata["runtime_promoted"] is True
    assert [frame["path"] for frame in metadata["frames"]] == [
        "icon.png",
        "card.png",
        "hud_mark.png",
    ]
    assert all(not Path(frame["path"]).is_absolute() for frame in metadata["frames"])
    assert all((runtime_metadata.parent / frame["path"]).is_file() for frame in metadata["frames"])
    assert (runtime_metadata.parent.parent / "README.md").is_file()
    assert (runtime_metadata.parent.parent / "_rules.md").is_file()
    assert (runtime_metadata.parent / "README.md").is_file()
    assert (runtime_metadata.parent / "_rules.md").is_file()

    qa_report = validate_asset_qa_records(
        isolated_content,
        manifest_report,
        isolated_content / "assets" / "qa",
    )
    record = next(item for item in qa_report.records if item.asset_id == asset.asset_id)
    assert record.qa_status == "qa_passed"
    assert record.runtime_target_path == (
        "runtime/item_cracked_wand_icon_card/"
        "cand_item_cracked_wand_promote_001/cut_metadata.yaml"
    )
    assert all(record.checks[check] is True for check in work_order.qa_checks)


def test_asset_qa_check_accepts_repo_records():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/asset_qa_check.py",
            "--content-dir",
            "content",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "asset QA records: OK" in result.stdout
    assert "records: 82" in result.stdout
    assert "qa_passed: 82" in result.stdout
    assert "no generated images are stored" in result.stdout


def test_asset_qa_records_validate_passed_candidate(content_root: Path, tmp_path: Path):
    bundle = load_content_bundle(content_root)
    manifest_report = validate_asset_manifest(content_root, bundle)
    asset = next(
        item for item in manifest_report.manifest.assets
        if item.asset_id == "item_cracked_wand_icon_card"
    )
    work_order = next(
        order for order in build_asset_work_orders(manifest_report)
        if order.asset_id == asset.asset_id
    )
    records_dir = tmp_path / "qa"
    records_dir.mkdir()
    _write_qa_record(records_dir, asset, work_order)

    report = validate_asset_qa_records(content_root, manifest_report, records_dir)

    assert report.total_records == 1
    assert report.counts_by_status == {"qa_passed": 1}
    record = report.records[0]
    assert record.asset_id == asset.asset_id
    assert record.runtime_target_path == "sprites/items/item_cracked_wand.png"
    assert {frame.frame_id for frame in record.frame_metadata} == set(asset.required_frames)


def test_asset_qa_records_reject_missing_required_check(content_root: Path, tmp_path: Path):
    bundle = load_content_bundle(content_root)
    manifest_report = validate_asset_manifest(content_root, bundle)
    asset = next(
        item for item in manifest_report.manifest.assets
        if item.asset_id == "item_cracked_wand_icon_card"
    )
    work_order = next(
        order for order in build_asset_work_orders(manifest_report)
        if order.asset_id == asset.asset_id
    )
    records_dir = tmp_path / "qa"
    records_dir.mkdir()
    _write_qa_record(records_dir, asset, work_order, omit_check="mit_safe")

    with pytest.raises(ContentError, match="missing QA checks"):
        validate_asset_qa_records(content_root, manifest_report, records_dir)


def test_asset_qa_records_reject_runtime_target_escape(content_root: Path, tmp_path: Path):
    bundle = load_content_bundle(content_root)
    manifest_report = validate_asset_manifest(content_root, bundle)
    asset = next(
        item for item in manifest_report.manifest.assets
        if item.asset_id == "item_cracked_wand_icon_card"
    )
    work_order = next(
        order for order in build_asset_work_orders(manifest_report)
        if order.asset_id == asset.asset_id
    )
    records_dir = tmp_path / "qa"
    records_dir.mkdir()
    _write_qa_record(
        records_dir,
        asset,
        work_order,
        runtime_target_path="../escaped.png",
    )

    with pytest.raises(ContentError, match="escapes content/assets"):
        validate_asset_qa_records(content_root, manifest_report, records_dir)


def test_asset_pipeline_report_summarizes_candidate_cut_and_runtime_gaps(
    content_root: Path, tmp_path: Path
):
    bundle = load_content_bundle(content_root)
    manifest_report = validate_asset_manifest(content_root, bundle)
    asset = next(
        item for item in manifest_report.manifest.assets
        if item.asset_id == "item_cracked_wand_icon_card"
    )
    work_order = next(
        order for order in build_asset_work_orders(manifest_report)
        if order.asset_id == asset.asset_id
    )
    records_dir = tmp_path / "qa"
    records_dir.mkdir()
    _write_qa_record(records_dir, asset, work_order)
    cut_dir = tmp_path / "cut"
    _write_cut_metadata(cut_dir, asset.asset_id)

    qa_report = validate_asset_qa_records(content_root, manifest_report, records_dir)
    pipeline = build_asset_pipeline_report(
        manifest_report,
        qa_report,
        cut_metadata_dir=cut_dir,
    )

    assert pipeline.total_assets == 82
    assert pipeline.candidate_asset_ids == ("item_cracked_wand_icon_card",)
    assert pipeline.cut_metadata_asset_ids == ("item_cracked_wand_icon_card",)
    assert pipeline.qa_passed_asset_ids == ("item_cracked_wand_icon_card",)
    manifest_asset_ids = tuple(
        sorted(asset.asset_id for asset in manifest_report.manifest.assets)
    )
    assert pipeline.runtime_asset_ids == manifest_asset_ids
    assert len(pipeline.missing_candidate_asset_ids) == 81
    assert len(pipeline.missing_qa_passed_asset_ids) == 81
    assert len(pipeline.missing_runtime_asset_ids) == 0
    assert pipeline.counts_by_type["item"] == {
        "total": 15,
        "candidates": 1,
        "cut_metadata": 1,
        "qa_passed": 1,
        "runtime_enabled": 15,
    }


def test_asset_status_report_script_reports_and_strict_gate_passes(
    content_root: Path, tmp_path: Path
):
    bundle = load_content_bundle(content_root)
    manifest_report = validate_asset_manifest(content_root, bundle)
    asset = next(
        item for item in manifest_report.manifest.assets
        if item.asset_id == "item_cracked_wand_icon_card"
    )
    work_order = next(
        order for order in build_asset_work_orders(manifest_report)
        if order.asset_id == asset.asset_id
    )
    records_dir = tmp_path / "qa"
    records_dir.mkdir()
    _write_qa_record(records_dir, asset, work_order)
    cut_dir = tmp_path / "cut"
    _write_cut_metadata(cut_dir, asset.asset_id)

    report = subprocess.run(
        [
            sys.executable,
            "scripts/asset_status_report.py",
            "--content-dir",
            "content",
            "--records-dir",
            str(records_dir),
            "--cut-metadata-dir",
            str(cut_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert report.returncode == 0, report.stdout + report.stderr
    assert "asset pipeline status: OK" in report.stdout
    assert "candidate_assets: 1/82" in report.stdout
    assert "cut_metadata_assets: 1/82" in report.stdout
    assert "qa_passed_assets: 1/82" in report.stdout
    assert "runtime_enabled_assets: 82/82" in report.stdout
    assert "- item: total=15 candidate=1 cut=1 qa_passed=1 runtime=15" in report.stdout
    assert "asset pipeline strict gate: not requested" in report.stdout

    strict = subprocess.run(
        [
            sys.executable,
            "scripts/asset_status_report.py",
            "--content-dir",
            "content",
            "--records-dir",
            str(records_dir),
            "--cut-metadata-dir",
            str(cut_dir),
            "--require-all-runtime",
            "--gap-limit",
            "2",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert strict.returncode == 0
    assert "asset pipeline strict gate: OK" in strict.stdout
    assert "missing runtime asset:" not in strict.stdout


def _write_promotable_cut_metadata(
    root: Path,
    asset,
    work_order,
    *,
    candidate_id: str,
) -> Path:
    frames_dir = root / "frames"
    frames_dir.mkdir(parents=True)
    frame_rows: list[str] = []
    for frame_id in asset.required_frames:
        frame_path = frames_dir / f"{frame_id}.png"
        frame_path.write_bytes(b"png placeholder")
        frame_rows.append(
            "\n".join(
                [
                    f"  - frame_id: {frame_id}",
                    f"    path: {frame_path}",
                    "    frame_size: [8, 8]",
                    "    visible_bbox: [1, 1, 7, 7]",
                    "    visible_pixels: 12",
                    "    anchor: [32, 32]",
                    "    duration_ms: 80",
                    f"    fallback_cell_id: cell.item_cracked_wand.{frame_id}",
                ]
            )
        )
    metadata = root / "cut_metadata.yaml"
    metadata.write_text(
        "\n".join(
            [
                'schema_version: "0.1"',
                f"asset_id: {asset.asset_id}",
                f"candidate_id: {candidate_id}",
                f"work_order_id: {work_order.work_order_id}",
                f"source_brief: {asset.source_brief}",
                "runtime_promoted: false",
                "frames:",
                *frame_rows,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return metadata


def _write_manifest(
    root: Path,
    *,
    qa_status: str = "planned",
    runtime_enabled: str = "false",
    path: str = "",
    frame: str = (
        "frame_id: idle\n"
        "        anchor: [1, 1]\n"
        "        duration_ms: 80\n"
        "        fallback_cell_id: cell.hero_x.idle"
    ),
) -> None:
    assets = root / "assets"
    assets.mkdir()
    (assets / "manifest.yaml").write_text(
        f"""
schema_version: "0.1"
content_version: test
runtime_policy:
  image_generation: development_only
  runtime_network: disabled
  qa_required_for_runtime: true
  fallback_required: true
statuses: [planned, generated, qa_passed, integrated, fallback_ready, evidence_done]
assets:
  - asset_id: hero_x_sheet
    source_type: hero
    source_content_id: hero_x
    role: hero_actor_sheet
    qa_status: {qa_status}
    runtime_enabled: {runtime_enabled}
    source_brief: hero_x_brief
    path: "{path}"
    required_frames: [idle]
    frames:
      - {frame}
""".lstrip(),
        encoding="utf-8",
    )


def _write_qa_record(
    records_dir: Path,
    asset,
    work_order,
    *,
    omit_check: str = "",
    runtime_target_path: str = "sprites/items/item_cracked_wand.png",
) -> None:
    checks = [
        f"      {check}: true"
        for check in work_order.qa_checks
        if check != omit_check
    ]
    frames: list[str] = []
    for frame_id in asset.required_frames:
        frames.append(
            "      - frame_id: {frame_id}\n"
            "        anchor: [32, 32]\n"
            "        duration_ms: 80\n"
            "        fallback_cell_id: cell.item_cracked_wand.{frame_id}".format(
                frame_id=frame_id
            )
        )
    (records_dir / "item_cracked_wand_qa.yaml").write_text(
        "\n".join(
            [
                'schema_version: "0.1"',
                "records:",
                f"  - asset_id: {asset.asset_id}",
                "    candidate_id: cand_item_cracked_wand_001",
                f"    work_order_id: wo_{asset.asset_id}",
                f"    source_brief: {asset.source_brief}",
                "    qa_status: qa_passed",
                "    candidate_ref: generated-cache://item_cracked_wand_001",
                "    reviewer: art-pipeline",
                "    reviewed_at: 2026-06-17T00:00:00Z",
                f"    runtime_target_path: {runtime_target_path}",
                "    checks:",
                *checks,
                "    frame_metadata:",
                *frames,
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_cut_metadata(root: Path, asset_id: str) -> None:
    metadata_path = root / asset_id / "candidate_001" / "cut_metadata.yaml"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(
        "\n".join(
            [
                'schema_version: "0.1"',
                f"asset_id: {asset_id}",
                "candidate_id: candidate_001",
                "runtime_promoted: false",
                "frames: []",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_test_sheet_png(path: Path) -> None:
    width = 41
    height = 21
    pixels = [[0, 255, 0, 255] for _ in range(width * height)]

    def draw_rect(x0: int, y0: int, x1: int, y1: int, color: list[int]) -> None:
        for y in range(y0, y1):
            for x in range(x0, x1):
                pixels[y * width + x] = color

    draw_rect(4, 3, 10, 8, [210, 30, 24, 255])
    draw_rect(25, 2, 33, 9, [24, 50, 220, 255])
    draw_rect(6, 13, 16, 20, [230, 190, 32, 255])
    draw_rect(24, 14, 35, 19, [180, 20, 180, 255])
    rgba = bytes(value for pixel in pixels for value in pixel)
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw.extend(rgba[y * stride : (y + 1) * stride])
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(
        _png_chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0),
        )
    )
    png.extend(_png_chunk(b"IDAT", zlib.compress(bytes(raw), level=9)))
    png.extend(_png_chunk(b"IEND", b""))
    path.write_bytes(bytes(png))


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    crc = binascii.crc32(chunk_type)
    crc = binascii.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", crc)
