#!/usr/bin/env python3
"""Validate generated asset candidate QA records."""
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
    load_content_bundle,
    validate_asset_manifest,
    validate_asset_qa_records,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate terminal graphics generated-candidate QA records."
    )
    parser.add_argument(
        "--content-dir",
        default="content",
        help="Content directory to validate. Defaults to ./content.",
    )
    parser.add_argument(
        "--records-dir",
        help="Optional QA record directory. Defaults to content/assets/qa.",
    )
    args = parser.parse_args(argv)

    content_dir = Path(args.content_dir)
    records_dir = Path(args.records_dir) if args.records_dir else None
    try:
        bundle = load_content_bundle(content_dir)
        manifest_report = validate_asset_manifest(content_dir, bundle)
        qa_report = validate_asset_qa_records(content_dir, manifest_report, records_dir)
    except ContentError as err:
        print("asset QA records: FAIL")
        print(f"error: {err}")
        return 2

    print("asset QA records: OK")
    print(f"records: {qa_report.total_records}")
    for status, count in qa_report.counts_by_status.items():
        print(f"{status}: {count}")
    print("runtime gate: qa_passed records require checks, frame metadata, and safe target paths")
    print("candidate storage: no generated images are stored in runtime assets before QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
