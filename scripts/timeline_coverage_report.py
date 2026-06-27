#!/usr/bin/env python3
"""Report terminal combat-stage timeline coverage across MVP skills."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ouro_agent.art.sprite_atlas import SpriteAtlas  # noqa: E402
from ouro_agent.art.timelines import signature_skill_ids  # noqa: E402
from ouro_agent.content import (  # noqa: E402
    ContentError,
    load_content_bundle,
    validate_asset_manifest,
)
from ouro_agent.tui.stage_model import build_catalog_skill_timelines  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that every MVP skill has a display-only sprite timeline "
            "against QA-promoted runtime assets."
        )
    )
    parser.add_argument("--content-dir", default="content")
    parser.add_argument("--enemy-id", default="enemy_black_candle_acolyte")
    parser.add_argument(
        "--require-all-skills",
        action="store_true",
        help="Fail unless every content skill has a valid timeline.",
    )
    args = parser.parse_args(argv)

    try:
        content_dir = Path(args.content_dir)
        bundle = load_content_bundle(content_dir)
        report = validate_asset_manifest(content_dir, bundle)
        atlas = SpriteAtlas.from_manifest_report(report)
        timelines = build_catalog_skill_timelines(
            bundle,
            atlas,
            enemy_id=args.enemy_id,
        )
        issues = _timeline_issues(bundle, atlas, timelines)
    except (ContentError, OSError, ValueError) as err:
        print("timeline coverage: FAIL", file=sys.stderr)
        print(f"error: {err}", file=sys.stderr)
        return 2

    if args.require_all_skills and issues:
        print("timeline coverage: FAIL")
        for issue in issues:
            print(f"- {issue}")
        return 2

    print("timeline coverage: OK" if not issues else "timeline coverage: WARN")
    print(f"skills: {len(timelines)}/{len(bundle.skills)}")
    print(f"atlas_assets: {atlas.total_assets}")
    print(f"bitmap_frames: {atlas.bitmap_frame_count}")
    print("runtime: display-only coverage; local engine owns combat facts")
    for timeline in timelines:
        skill_id = timeline.timeline_id.split(".")[1]
        effect_frames = {beat.effect_frame for beat in timeline.beats}
        hit_stop = "yes" if any(beat.hit_stop for beat in timeline.beats) else "no"
        print(
            f"- {skill_id}: beats={len(timeline.beats)} "
            f"unique_effect_frames={len(effect_frames)} hit_stop={hit_stop} "
            f"duration_ms={timeline.total_duration_ms}"
        )
    for issue in issues:
        print(f"! {issue}")
    return 0


def _timeline_issues(bundle, atlas: SpriteAtlas, timelines) -> list[str]:
    issues: list[str] = []
    by_skill = {timeline.timeline_id.split(".")[1]: timeline for timeline in timelines}
    missing = sorted(set(bundle.skills) - set(by_skill))
    for skill_id in missing:
        issues.append(f"{skill_id}: missing catalog timeline")
    for skill_id, timeline in by_skill.items():
        try:
            timeline.validate_against(atlas)
        except ContentError as err:
            issues.append(str(err))
            continue
        minimum = 12 if skill_id in signature_skill_ids() else 8
        if len(timeline.beats) < minimum:
            issues.append(f"{skill_id}: expected at least {minimum} beats")
        effect_frames = {beat.effect_frame for beat in timeline.beats}
        if len(effect_frames) < 4:
            issues.append(f"{skill_id}: expected at least 4 unique effect frames")
        if not any(beat.hit_stop for beat in timeline.beats):
            issues.append(f"{skill_id}: missing hit_stop beat")
        for beat in timeline.beats:
            frame = atlas.sprite(beat.effect_asset_id).frame(beat.effect_frame)
            if not frame.has_bitmap or not frame.runtime_promoted:
                issues.append(
                    f"{skill_id}.{beat.frame_id}: effect frame is not runtime bitmap"
                )
    return issues


if __name__ == "__main__":
    raise SystemExit(main())
