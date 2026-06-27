#!/usr/bin/env python3
"""Create a QA record template for one generated asset candidate."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ouro_agent.content import (  # noqa: E402
    ContentError,
    build_asset_qa_template,
    load_content_bundle,
    validate_asset_manifest,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a generated-candidate QA record template with frame "
            "metadata dry-run. This does not promote runtime assets."
        )
    )
    parser.add_argument("--content-dir", default="content")
    parser.add_argument("--work-order-id", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument(
        "--candidate-ref",
        required=True,
        help="Scratch/cache reference to the generated candidate, not a runtime path.",
    )
    parser.add_argument("--output", help="Optional YAML output path. Defaults to stdout.")
    args = parser.parse_args(argv)

    try:
        content_dir = Path(args.content_dir)
        bundle = load_content_bundle(content_dir)
        manifest_report = validate_asset_manifest(content_dir, bundle)
        template = build_asset_qa_template(
            manifest_report,
            work_order_id=args.work_order_id,
            candidate_id=args.candidate_id,
            candidate_ref=args.candidate_ref,
        )
    except ContentError as err:
        print("asset candidate intake: FAIL", file=sys.stderr)
        print(f"error: {err}", file=sys.stderr)
        return 2

    data = {
        "schema_version": "0.1",
        "records": [template.to_record_dict()],
    }
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=False)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
        print(f"asset candidate intake: wrote template to {output}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
