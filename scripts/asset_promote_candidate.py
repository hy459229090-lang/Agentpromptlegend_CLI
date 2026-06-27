#!/usr/bin/env python3
"""Promote a QA-approved cut candidate into repo-local runtime assets."""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ouro_agent.art.sprite_atlas import (  # noqa: E402
    CandidateCutFrame,
    CandidateCutMetadata,
    load_candidate_cut_metadata,
)
from ouro_agent.content import (  # noqa: E402
    AssetEntry,
    AssetWorkOrder,
    ContentError,
    build_asset_work_orders,
    load_content_bundle,
    validate_asset_manifest,
    validate_asset_qa_records,
)


SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a reviewed generated cut candidate into content/assets/runtime "
            "and write a qa_passed record. This does not edit manifest.yaml."
        )
    )
    parser.add_argument("--content-dir", default="content")
    parser.add_argument("--cut-metadata", required=True)
    parser.add_argument(
        "--runtime-dir",
        help="Runtime asset root. Defaults to content/assets/runtime.",
    )
    parser.add_argument(
        "--qa-output",
        help="QA record path. Defaults to content/assets/qa/<asset_id>.yaml.",
    )
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reviewed-at", default=_utc_now())
    parser.add_argument(
        "--candidate-ref",
        help="Portable candidate reference for the QA record.",
    )
    parser.add_argument(
        "--approve-all-checks",
        action="store_true",
        help="Mark every required QA check true for this reviewed candidate.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace an existing runtime target directory and QA output file.",
    )
    args = parser.parse_args(argv)

    try:
        content_dir = Path(args.content_dir)
        assets_root = (content_dir / "assets").resolve()
        bundle = load_content_bundle(content_dir)
        manifest_report = validate_asset_manifest(content_dir, bundle)
        cut = load_candidate_cut_metadata(Path(args.cut_metadata))
        assets_by_id = {asset.asset_id: asset for asset in manifest_report.manifest.assets}
        work_orders_by_asset = {
            order.asset_id: order for order in build_asset_work_orders(manifest_report)
        }
        asset = assets_by_id.get(cut.asset_id)
        work_order = work_orders_by_asset.get(cut.asset_id)
        if asset is None or work_order is None:
            raise ValueError(f"unknown asset_id '{cut.asset_id}'")
        _validate_promotable_cut(cut, asset, work_order)
        if not args.approve_all_checks:
            raise ValueError("--approve-all-checks is required for qa_passed promotion")

        runtime_root = (
            Path(args.runtime_dir)
            if args.runtime_dir
            else content_dir / "assets" / "runtime"
        )
        runtime_root = runtime_root.resolve()
        if not runtime_root.is_relative_to(assets_root):
            raise ValueError("runtime target must stay under content/assets")

        target_dir = runtime_root / cut.asset_id / _safe_name(cut.candidate_id)
        metadata_path = target_dir / "cut_metadata.yaml"
        qa_output = (
            Path(args.qa_output)
            if args.qa_output
            else content_dir / "assets" / "qa" / f"{cut.asset_id}.yaml"
        )
        qa_root = (content_dir / "assets" / "qa").resolve()
        if not qa_output.resolve().is_relative_to(qa_root):
            raise ValueError("QA output must stay under content/assets/qa")
        _prepare_output(target_dir, qa_output, replace=args.replace)
        _write_runtime_scaffold(target_dir, asset, cut)

        frames_by_id = {frame.frame_id: frame for frame in cut.frames}
        runtime_frames = []
        for frame_id in asset.required_frames:
            source_frame = frames_by_id[frame_id]
            frame_name = f"{_safe_name(frame_id)}.png"
            target_frame = target_dir / frame_name
            target_frame.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_frame.path, target_frame)
            runtime_frames.append(_runtime_frame(source_frame, frame_name))

        metadata = {
            "schema_version": "0.1",
            "asset_id": cut.asset_id,
            "candidate_id": cut.candidate_id,
            "work_order_id": cut.work_order_id,
            "source_brief": work_order.source_brief,
            "runtime_promoted": True,
            "frames": runtime_frames,
        }
        metadata_path.write_text(
            yaml.safe_dump(metadata, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )

        runtime_target_path = metadata_path.resolve().relative_to(assets_root).as_posix()
        candidate_ref = args.candidate_ref or f"generated-cache://{cut.candidate_id}"
        _validate_candidate_ref(candidate_ref)
        qa_output.parent.mkdir(parents=True, exist_ok=True)
        qa_output.write_text(
            yaml.safe_dump(
                _qa_record(
                    cut=cut,
                    asset=asset,
                    work_order=work_order,
                    candidate_ref=candidate_ref,
                    reviewer=args.reviewer,
                    reviewed_at=args.reviewed_at,
                    runtime_target_path=runtime_target_path,
                ),
                sort_keys=False,
                allow_unicode=False,
            ),
            encoding="utf-8",
        )
        validate_asset_qa_records(content_dir, manifest_report, qa_output.parent)
    except (ContentError, OSError, ValueError) as err:
        print("asset candidate promotion: FAIL", file=sys.stderr)
        print(f"error: {err}", file=sys.stderr)
        return 2

    print("asset candidate promotion: OK")
    print(f"asset_id: {cut.asset_id}")
    print(f"candidate_id: {cut.candidate_id}")
    print(f"frames_promoted: {len(runtime_frames)}")
    print(f"runtime_metadata: {metadata_path}")
    print(f"qa_record: {qa_output}")
    print(
        "manifest_update: "
        f"qa_status=qa_passed runtime_enabled=true path={runtime_target_path}"
    )
    return 0


def _validate_promotable_cut(
    cut: CandidateCutMetadata, asset: AssetEntry, work_order: AssetWorkOrder
) -> None:
    if cut.runtime_promoted:
        raise ValueError("cut metadata is already runtime_promoted")
    if cut.work_order_id != work_order.work_order_id:
        raise ValueError(
            f"cut work_order_id '{cut.work_order_id}' does not match "
            f"'{work_order.work_order_id}'"
        )
    frames_by_id = {frame.frame_id: frame for frame in cut.frames}
    required = set(asset.required_frames)
    found = set(frames_by_id)
    missing = sorted(required - found)
    extra = sorted(found - required)
    if missing:
        raise ValueError(f"cut metadata is missing required frames: {missing}")
    if extra:
        raise ValueError(f"cut metadata contains undeclared frames: {extra}")
    for frame in cut.frames:
        if frame.path.suffix.lower() != ".png":
            raise ValueError(f"{frame.frame_id}: runtime frame must be a PNG")
        if frame.visible_pixels <= 0:
            raise ValueError(f"{frame.frame_id}: runtime frame has no visible pixels")
        if frame.frame_size[0] <= 0 or frame.frame_size[1] <= 0:
            raise ValueError(f"{frame.frame_id}: runtime frame size must be positive")


def _prepare_output(target_dir: Path, qa_output: Path, *, replace: bool) -> None:
    if target_dir.exists():
        if not replace:
            raise ValueError(f"runtime target already exists: {target_dir}")
        shutil.rmtree(target_dir)
    if qa_output.exists():
        if not replace:
            raise ValueError(f"QA output already exists: {qa_output}")
        qa_output.unlink()
    target_dir.mkdir(parents=True, exist_ok=True)


def _write_runtime_scaffold(
    target_dir: Path, asset: AssetEntry, cut: CandidateCutMetadata
) -> None:
    asset_dir = target_dir.parent
    _write_if_missing(
        asset_dir / "README.md",
        "\n".join(
            [
                f"# {asset.asset_id}",
                "",
                f"Runtime assets for `{asset.source_type}:{asset.source_content_id}`.",
                "",
                "Only QA-promoted candidates should live in this directory.",
                "",
            ]
        ),
    )
    _write_if_missing(
        asset_dir / "_rules.md",
        "\n".join(
            [
                f"# {asset.asset_id} Rules",
                "",
                "1. Store only QA-promoted runtime candidates for this asset.",
                "2. Keep each candidate in its own directory with `cut_metadata.yaml`.",
                "3. Do not add generated source sheets, private paths, or rejected cuts.",
                "",
            ]
        ),
    )
    _write_if_missing(
        target_dir / "README.md",
        "\n".join(
            [
                f"# {cut.candidate_id}",
                "",
                f"QA-promoted runtime cut for `{asset.asset_id}`.",
                "",
                "`cut_metadata.yaml` is the runtime entry point. Frame paths are",
                "relative so installed packages and other machines can load this asset.",
                "",
            ]
        ),
    )
    _write_if_missing(
        target_dir / "_rules.md",
        "\n".join(
            [
                f"# {cut.candidate_id} Rules",
                "",
                "1. Keep frame PNG names stable unless metadata, QA records, tests,",
                "   and evidence are updated together.",
                "2. Do not add source sheet PNGs or generated-cache references here.",
                "3. Runtime metadata must stay portable and free of local absolute paths.",
                "",
            ]
        ),
    )


def _write_if_missing(path: Path, text: str) -> None:
    if path.exists():
        return
    path.write_text(text, encoding="utf-8")


def _runtime_frame(frame: CandidateCutFrame, frame_name: str) -> Mapping[str, object]:
    return {
        "frame_id": frame.frame_id,
        "path": frame_name,
        "frame_size": list(frame.frame_size),
        "visible_bbox": list(frame.visible_bbox),
        "visible_pixels": frame.visible_pixels,
        "anchor": list(frame.anchor),
        "duration_ms": frame.duration_ms,
        "fallback_cell_id": frame.fallback_cell_id,
    }


def _qa_record(
    *,
    cut: CandidateCutMetadata,
    asset: AssetEntry,
    work_order: AssetWorkOrder,
    candidate_ref: str,
    reviewer: str,
    reviewed_at: str,
    runtime_target_path: str,
) -> Mapping[str, object]:
    frames_by_id = {frame.frame_id: frame for frame in cut.frames}
    return {
        "schema_version": "0.1",
        "records": [
            {
                "asset_id": cut.asset_id,
                "candidate_id": cut.candidate_id,
                "work_order_id": cut.work_order_id,
                "source_brief": work_order.source_brief,
                "qa_status": "qa_passed",
                "candidate_ref": candidate_ref,
                "reviewer": reviewer,
                "reviewed_at": reviewed_at,
                "runtime_target_path": runtime_target_path,
                "checks": {check: True for check in work_order.qa_checks},
                "frame_metadata": [
                    {
                        "frame_id": frame_id,
                        "anchor": list(frames_by_id[frame_id].anchor),
                        "duration_ms": frames_by_id[frame_id].duration_ms,
                        "fallback_cell_id": frames_by_id[frame_id].fallback_cell_id,
                    }
                    for frame_id in asset.required_frames
                ],
            }
        ],
    }


def _validate_candidate_ref(value: str) -> None:
    if Path(value).is_absolute() or value.startswith("file:"):
        raise ValueError("candidate_ref must be portable and not a local file path")
    private_markers = ("/private/", "/Users/", "\\Users\\")
    if any(marker in value for marker in private_markers):
        raise ValueError("candidate_ref must not include private absolute paths")


def _safe_name(value: str) -> str:
    cleaned = SAFE_NAME.sub("_", value.strip())
    return cleaned.strip("._") or "asset"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
