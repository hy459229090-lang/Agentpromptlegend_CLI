#!/usr/bin/env python3
"""Emit development-time ImageGen work orders for the full asset manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ouro_agent.content import (  # noqa: E402
    ContentError,
    build_asset_work_orders,
    load_content_bundle,
    validate_asset_manifest,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic ImageGen work orders from the full "
            "terminal graphics asset manifest. This does not call ImageGen."
        )
    )
    parser.add_argument(
        "--content-dir",
        default="content",
        help="Content directory to validate. Defaults to ./content.",
    )
    parser.add_argument(
        "--format",
        choices=("jsonl", "summary"),
        default="jsonl",
        help="Output JSONL work orders or a compact summary.",
    )
    parser.add_argument(
        "--output",
        help="Optional output file. Defaults to stdout.",
    )
    args = parser.parse_args(argv)

    try:
        bundle = load_content_bundle(Path(args.content_dir))
        report = validate_asset_manifest(Path(args.content_dir), bundle)
        work_orders = build_asset_work_orders(report)
    except ContentError as err:
        print("asset work orders: FAIL", file=sys.stderr)
        print(f"error: {err}", file=sys.stderr)
        return 2

    if args.format == "summary":
        text = _summary(work_orders)
    else:
        text = "\n".join(json.dumps(order.to_dict(), sort_keys=True) for order in work_orders)
        if text:
            text += "\n"

    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"asset work orders: wrote {len(work_orders)} to {output}")
    else:
        print(text, end="")
    return 0


def _summary(work_orders) -> str:
    counts: dict[str, int] = {}
    for order in work_orders:
        counts[order.family] = counts.get(order.family, 0) + 1
    lines = [
        "asset work orders: OK",
        f"work orders: {len(work_orders)}",
        "runtime: no ImageGen call, no network, scratch-only candidates",
    ]
    for family in sorted(counts):
        lines.append(f"{family}: {counts[family]}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
