#!/usr/bin/env python3
"""Validate terminal graphics asset manifest coverage."""
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
)
from ouro_agent.content.assets import iter_missing_asset_coverage  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate content/assets/manifest.yaml coverage and QA gates."
    )
    parser.add_argument(
        "--content-dir",
        default="content",
        help="Content directory to validate. Defaults to ./content.",
    )
    args = parser.parse_args(argv)

    content_dir = Path(args.content_dir)
    try:
        bundle = load_content_bundle(content_dir)
        report = validate_asset_manifest(content_dir, bundle)
    except ContentError as err:
        print(f"asset manifest: FAIL")
        print(f"error: {err}")
        return 2

    print("asset manifest: OK" if report.ok else "asset manifest: MISSING")
    print(f"path: {report.manifest.path}")
    print(f"assets: {report.total_assets}")
    print(f"brief families: {len(report.brief_catalog.families)}")
    print(f"source briefs: {len(report.brief_catalog.aliases)}")
    for source_type, count in report.counts_by_type.items():
        print(f"{source_type}: {count}")

    missing = tuple(iter_missing_asset_coverage(report))
    if missing:
        print("coverage gaps:")
        for item in missing:
            print(f"- {item}")
        return 3

    print("coverage: full current MVP content")
    print("runtime policy: development-only ImageGen, local QA-passed assets only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
