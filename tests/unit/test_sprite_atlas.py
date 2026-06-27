"""REQ-TERMGRAPHICS-002 sprite atlas and timeline contracts."""
from __future__ import annotations

from pathlib import Path

import pytest

from ouro_agent.art.sprite_atlas import (
    ActorSprite,
    EffectSprite,
    SpriteAtlas,
    load_candidate_cut_metadata,
)
from ouro_agent.art.timelines import build_hex_seal_smoke_timeline
from ouro_agent.content import load_content_bundle, validate_asset_manifest
from ouro_agent.content.loader import ContentError


def test_sprite_atlas_builds_full_manifest_fallback(content_root: Path):
    bundle = load_content_bundle(content_root)
    report = validate_asset_manifest(content_root, bundle)
    atlas = SpriteAtlas.from_manifest_report(report)

    assert atlas.total_assets == 82
    assert atlas.bitmap_frame_count == 408

    hero = atlas.sprite("hero_shadow_apprentice_battle_sheet")
    assert isinstance(hero, ActorSprite)
    assert hero.runtime_enabled
    assert hero.source_content_id == "hero_shadow_apprentice"
    assert hero.frame_ids == (
        "portrait",
        "idle",
        "ready",
        "attack",
        "skill",
        "guard",
        "hit",
        "low_hp",
        "victory",
        "defeat",
        "signature",
    )
    assert hero.frame("idle").fallback_cell_id == "cell.hero_shadow_apprentice.idle"
    assert hero.frame("idle").duration_ms == 80
    assert hero.frame("idle").visual_source == "runtime_cut"
    assert hero.frame("idle").has_bitmap
    assert hero.frame("skill").runtime_promoted is True

    enemy = atlas.sprite("enemy_black_candle_acolyte_actor_sheet")
    assert isinstance(enemy, ActorSprite)
    assert enemy.runtime_enabled
    assert enemy.frame("telegraph").visual_source == "runtime_cut"
    assert enemy.frame("hit").has_bitmap

    hex_seal = atlas.sprite("skill_hex_seal_effect_sheet")
    assert isinstance(hex_seal, EffectSprite)
    assert hex_seal.runtime_enabled
    assert hex_seal.frame("hit_stop").has_bitmap
    assert hex_seal.frame("hit_stop").visual_source == "runtime_cut"
    assert hex_seal.frame("hit_stop").runtime_promoted is True
    assert hex_seal.frame("hit_stop").fallback_cell_id == "cell.skill_hex_seal.hit_stop"
    assert hex_seal.frame("damage_pop").anchor == (80, 32)


def test_sprite_atlas_overlays_candidate_cut_metadata(
    content_root: Path, tmp_path: Path
):
    bundle = load_content_bundle(content_root)
    report = validate_asset_manifest(content_root, bundle)
    atlas = SpriteAtlas.from_manifest_report(report)
    cut_metadata_path = _write_cut_metadata(tmp_path)

    cut = load_candidate_cut_metadata(cut_metadata_path)
    atlas = atlas.with_candidate_cuts((cut,))

    hero = atlas.sprite("hero_shadow_apprentice_battle_sheet")
    assert atlas.bitmap_frame_count == 408
    assert hero.frame("portrait").visual_source == "candidate_cut"
    assert hero.frame("portrait").bitmap_path == tmp_path / "portrait.png"
    assert hero.frame("portrait").visible_bbox == (2, 3, 20, 30)
    assert hero.frame("portrait").visible_pixels == 100
    assert hero.frame("portrait").runtime_promoted is False
    assert hero.frame("idle").bitmap_path == tmp_path / "idle.png"
    assert hero.frame("ready").visual_source == "runtime_cut"
    assert hero.runtime_enabled


def test_candidate_cut_metadata_rejects_unknown_frame(content_root: Path, tmp_path: Path):
    bundle = load_content_bundle(content_root)
    report = validate_asset_manifest(content_root, bundle)
    atlas = SpriteAtlas.from_manifest_report(report)
    cut_metadata_path = _write_cut_metadata(tmp_path, frame_id="not_in_manifest")

    cut = load_candidate_cut_metadata(cut_metadata_path)
    with pytest.raises(ContentError, match="not declared"):
        atlas.with_candidate_cuts((cut,))


def test_candidate_cut_metadata_resolves_relative_frame_paths(tmp_path: Path):
    cut_metadata_path = _write_cut_metadata(tmp_path, relative_paths=True)

    cut = load_candidate_cut_metadata(cut_metadata_path)

    assert cut.frames[0].path == tmp_path / "portrait.png"
    assert cut.frames[1].path == tmp_path / "idle.png"


def test_hex_seal_smoke_timeline_validates_against_atlas(content_root: Path):
    bundle = load_content_bundle(content_root)
    report = validate_asset_manifest(content_root, bundle)
    atlas = SpriteAtlas.from_manifest_report(report)
    timeline = build_hex_seal_smoke_timeline()

    timeline.validate_against(atlas)

    assert timeline.timeline_id == "smoke.hex_seal.black_candle"
    assert len(timeline.beats) == 12
    assert timeline.total_duration_ms == 810
    assert [beat.frame_id for beat in timeline.beats[:6]] == [
        "idle",
        "windup",
        "seal_spawn",
        "travel_mid",
        "travel_near",
        "hit_stop",
    ]
    assert any(beat.hit_stop for beat in timeline.beats)
    assert any(beat.damage_pop == "-16 HP" for beat in timeline.beats)
    assert any(beat.damage_pop == "-16 HP | SLN" for beat in timeline.beats)
    assert all(
        later.differs_from(earlier)
        for earlier, later in zip(timeline.beats, timeline.beats[1:])
    )


def _write_cut_metadata(
    tmp_path: Path,
    *,
    frame_id: str = "portrait",
    relative_paths: bool = False,
) -> Path:
    portrait = tmp_path / "portrait.png"
    idle = tmp_path / "idle.png"
    portrait.write_bytes(b"png placeholder")
    idle.write_bytes(b"png placeholder")
    portrait_ref = "portrait.png" if relative_paths else str(portrait)
    idle_ref = "idle.png" if relative_paths else str(idle)
    path = tmp_path / "cut_metadata.yaml"
    path.write_text(
        "\n".join(
            [
                "schema_version: '0.1'",
                "asset_id: hero_shadow_apprentice_battle_sheet",
                "candidate_id: cand_hero_shadow_apprentice_001",
                "work_order_id: wo_hero_shadow_apprentice_battle_sheet",
                "source_brief: astia_black_candle_shadow_apprentice",
                "runtime_promoted: false",
                "frames:",
                f"  - frame_id: {frame_id}",
                f"    path: {portrait_ref}",
                "    anchor: [64, 96]",
                "    duration_ms: 80",
                "    fallback_cell_id: cell.hero_shadow_apprentice.portrait",
                "    frame_size: [96, 96]",
                "    visible_bbox: [2, 3, 20, 30]",
                "    visible_pixels: 100",
                "  - frame_id: idle",
                f"    path: {idle_ref}",
                "    anchor: [64, 96]",
                "    duration_ms: 80",
                "    fallback_cell_id: cell.hero_shadow_apprentice.idle",
                "    frame_size: [96, 96]",
                "    visible_bbox: [4, 5, 22, 32]",
                "    visible_pixels: 120",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path
