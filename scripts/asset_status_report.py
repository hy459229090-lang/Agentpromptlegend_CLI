#!/usr/bin/env python3
"""Report generated-candidate, QA, cut, and runtime asset readiness."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ouro_agent.content import (  # noqa: E402
    ContentError,
    build_asset_pipeline_report,
    iter_asset_pipeline_gaps,
    load_content_bundle,
    validate_asset_manifest,
    validate_asset_qa_records,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report terminal graphics asset pipeline readiness. Default mode is "
            "informational; strict flags turn missing work into a failing gate."
        )
    )
    parser.add_argument("--content-dir", default="content")
    parser.add_argument(
        "--records-dir",
        help="Optional QA record directory. Defaults to content/assets/qa.",
    )
    parser.add_argument(
        "--cut-metadata-dir",
        help=(
            "Optional scratch/runtime directory containing cut_metadata.yaml "
            "files. Defaults to content/assets/runtime."
        ),
    )
    parser.add_argument("--require-all-candidates", action="store_true")
    parser.add_argument("--require-all-cut-metadata", action="store_true")
    parser.add_argument("--require-all-qa-passed", action="store_true")
    parser.add_argument("--require-all-runtime", action="store_true")
    parser.add_argument(
        "--gap-limit",
        type=int,
        default=12,
        help="Maximum missing asset lines to print per failing run.",
    )
    args = parser.parse_args(argv)

    content_dir = Path(args.content_dir)
    records_dir = Path(args.records_dir) if args.records_dir else None
    cut_metadata_dir = (
        Path(args.cut_metadata_dir)
        if args.cut_metadata_dir
        else content_dir / "assets" / "runtime"
    )

    try:
        bundle = load_content_bundle(content_dir)
        manifest_report = validate_asset_manifest(content_dir, bundle)
        qa_report = validate_asset_qa_records(content_dir, manifest_report, records_dir)
        report = build_asset_pipeline_report(
            manifest_report,
            qa_report,
            cut_metadata_dir=cut_metadata_dir,
        )
    except ContentError as err:
        print("asset pipeline status: FAIL")
        print(f"error: {err}")
        return 2

    print("asset pipeline status: OK")
    print(f"assets: {report.total_assets}")
    print(f"candidate_assets: {len(report.candidate_asset_ids)}/{report.total_assets}")
    print(f"cut_metadata_assets: {len(report.cut_metadata_asset_ids)}/{report.total_assets}")
    print(f"qa_passed_assets: {len(report.qa_passed_asset_ids)}/{report.total_assets}")
    print(f"runtime_enabled_assets: {len(report.runtime_asset_ids)}/{report.total_assets}")
    print(f"qa_records: {report.qa_report.total_records}")
    for status, count in report.qa_report.counts_by_status.items():
        print(f"qa_{status}: {count}")
    print(f"cut_metadata_files: {len(report.cut_metadata_paths)}")
    print("by_type:")
    for source_type, counts in report.counts_by_type.items():
        print(
            f"- {source_type}: total={counts['total']} "
            f"candidate={counts['candidates']} "
            f"cut={counts['cut_metadata']} "
            f"qa_passed={counts['qa_passed']} "
            f"runtime={counts['runtime_enabled']}"
        )

    gaps = tuple(
        iter_asset_pipeline_gaps(
            report,
            require_all_candidates=args.require_all_candidates,
            require_all_cut_metadata=args.require_all_cut_metadata,
            require_all_qa_passed=args.require_all_qa_passed,
            require_all_runtime=args.require_all_runtime,
        )
    )
    if gaps:
        print("asset pipeline strict gate: MISSING")
        limit = max(args.gap_limit, 0)
        for item in gaps[:limit]:
            print(f"- {item}")
        if len(gaps) > limit:
            print(f"- ... {len(gaps) - limit} more")
        return 3

    if any(
        (
            args.require_all_candidates,
            args.require_all_cut_metadata,
            args.require_all_qa_passed,
            args.require_all_runtime,
        )
    ):
        print("asset pipeline strict gate: OK")
    else:
        print("asset pipeline strict gate: not requested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
