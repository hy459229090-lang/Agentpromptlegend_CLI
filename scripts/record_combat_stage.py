#!/usr/bin/env python3
"""Record deterministic combat-stage filmstrip evidence."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ouro_agent.art.sprite_atlas import (  # noqa: E402
    SpriteAtlas,
    load_candidate_cut_metadata,
)
from ouro_agent.art.timelines import build_hex_seal_smoke_timeline  # noqa: E402
from ouro_agent.content import (  # noqa: E402
    ContentError,
    load_content_bundle,
    validate_asset_manifest,
)
from ouro_agent.tui.graphics import render_graphics_doctor, select_graphics_backend  # noqa: E402
from ouro_agent.tui.bitmap_renderer import render_bitmap_timeline_filmstrip  # noqa: E402
from ouro_agent.tui.timeline_renderer import render_timeline_filmstrip  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Write terminal graphics evidence filmstrips for the Hex Seal smoke "
            "timeline. This script is display-only and does not run combat."
        )
    )
    parser.add_argument("--content-dir", default="content")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--candidate-cut-metadata",
        action="append",
        default=[],
        help="Optional cut_metadata.yaml path to overlay generated candidate frames.",
    )
    parser.add_argument("--width", type=int, default=96)
    parser.add_argument("--max-frames", type=int)
    args = parser.parse_args(argv)

    try:
        content_dir = Path(args.content_dir)
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        bundle = load_content_bundle(content_dir)
        manifest_report = validate_asset_manifest(content_dir, bundle)
        atlas = SpriteAtlas.from_manifest_report(manifest_report)
        cuts = tuple(
            load_candidate_cut_metadata(Path(path))
            for path in args.candidate_cut_metadata
        )
        if cuts:
            atlas = atlas.with_candidate_cuts(cuts)
        timeline = build_hex_seal_smoke_timeline()
        timeline.validate_against(atlas)

        unicode_filmstrip = render_timeline_filmstrip(
            timeline,
            atlas,
            mode="unicode",
            width=args.width,
            max_frames=args.max_frames,
        )
        ascii_filmstrip = render_timeline_filmstrip(
            timeline,
            atlas,
            mode="ascii",
            width=args.width,
            max_frames=args.max_frames,
        )
        bitmap_iterm2_filmstrip = render_bitmap_timeline_filmstrip(
            timeline,
            atlas,
            backend="iterm2",
            width=args.width,
            max_frames=args.max_frames,
            embed_images=False,
        )
        bitmap_kitty_filmstrip = render_bitmap_timeline_filmstrip(
            timeline,
            atlas,
            backend="kitty",
            width=args.width,
            max_frames=args.max_frames,
            embed_images=False,
        )
        bitmap_sixel_filmstrip = render_bitmap_timeline_filmstrip(
            timeline,
            atlas,
            backend="sixel",
            width=args.width,
            max_frames=args.max_frames,
            embed_images=False,
        )
        capability = select_graphics_backend(
            requested_mode="auto",
            stdout_is_tty=False,
            no_animation=True,
        )
        summary = "\n".join(
            [
                "COMBAT STAGE EVIDENCE",
                f"timeline: {timeline.timeline_id}",
                f"beats: {len(timeline.beats)}",
                f"duration_ms: {timeline.total_duration_ms}",
                f"atlas_assets: {atlas.total_assets}",
                f"bitmap_frames: {atlas.bitmap_frame_count}",
                "bitmap_filmstrip_iterm2: hex_seal_bitmap_iterm2_filmstrip.txt",
                "bitmap_filmstrip_kitty: hex_seal_bitmap_kitty_filmstrip.txt",
                "bitmap_filmstrip_sixel: hex_seal_bitmap_sixel_filmstrip.txt",
                f"candidate_cuts: {len(cuts)}",
                "runtime: display-only evidence; local engine owns combat facts",
                "",
                render_graphics_doctor(capability),
                "",
            ]
        )
        (output_dir / "summary.txt").write_text(summary, encoding="utf-8")
        (output_dir / "hex_seal_unicode_filmstrip.txt").write_text(
            unicode_filmstrip + "\n",
            encoding="utf-8",
        )
        (output_dir / "hex_seal_ascii_filmstrip.txt").write_text(
            ascii_filmstrip + "\n",
            encoding="utf-8",
        )
        (output_dir / "hex_seal_bitmap_iterm2_filmstrip.txt").write_text(
            bitmap_iterm2_filmstrip + "\n",
            encoding="utf-8",
        )
        (output_dir / "hex_seal_bitmap_kitty_filmstrip.txt").write_text(
            bitmap_kitty_filmstrip + "\n",
            encoding="utf-8",
        )
        (output_dir / "hex_seal_bitmap_sixel_filmstrip.txt").write_text(
            bitmap_sixel_filmstrip + "\n",
            encoding="utf-8",
        )
    except (ContentError, OSError, ValueError) as err:
        print("combat stage record: FAIL", file=sys.stderr)
        print(f"error: {err}", file=sys.stderr)
        return 2

    print("combat stage record: OK")
    print(f"output_dir: {output_dir}")
    print(f"timeline: {timeline.timeline_id}")
    print(f"beats: {len(timeline.beats)}")
    print(f"bitmap_frames: {atlas.bitmap_frame_count}")
    print("bitmap_iterm2_filmstrip: hex_seal_bitmap_iterm2_filmstrip.txt")
    print("bitmap_kitty_filmstrip: hex_seal_bitmap_kitty_filmstrip.txt")
    print("bitmap_sixel_filmstrip: hex_seal_bitmap_sixel_filmstrip.txt")
    print("unicode_filmstrip: hex_seal_unicode_filmstrip.txt")
    print("ascii_filmstrip: hex_seal_ascii_filmstrip.txt")
    print("summary: summary.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
