"""REQ-TERMGRAPHICS-002/003 timeline renderer and evidence gates."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from ouro_agent.art.sprite_atlas import SpriteAtlas
from ouro_agent.art.timelines import build_hex_seal_smoke_timeline, signature_skill_ids
from ouro_agent.content import load_content_bundle, validate_asset_manifest
from ouro_agent.engine.battle import BattleLoop
from ouro_agent.i18n import visual_width
from ouro_agent.providers.mock import MockProvider
from ouro_agent.tui.animation import build_sprite_battle_animation_frames
from ouro_agent.tui.bitmap_renderer import (
    BitmapTimelineRenderer,
    render_bitmap_timeline_filmstrip,
)
from ouro_agent.tui.stage_model import (
    build_catalog_skill_timelines,
    build_combat_stage_timeline,
)
from ouro_agent.tui.timeline_renderer import (
    render_timeline_filmstrip,
    render_timeline_frames,
)


ROOT = Path(__file__).resolve().parents[2]


def test_timeline_renderer_outputs_unicode_and_ascii_filmstrips(content_root: Path):
    atlas = _atlas(content_root)
    timeline = build_hex_seal_smoke_timeline()

    unicode_frames = render_timeline_frames(timeline, atlas, mode="unicode", width=96)
    zh_frames = render_timeline_frames(
        timeline,
        atlas,
        mode="unicode",
        width=96,
        language="zh",
    )
    ascii_strip = render_timeline_filmstrip(timeline, atlas, mode="ascii", width=96)
    bitmap_strip = render_bitmap_timeline_filmstrip(
        timeline,
        atlas,
        backend="iterm2",
        width=112,
        max_frames=2,
        embed_images=False,
    )
    sixel_strip = render_bitmap_timeline_filmstrip(
        timeline,
        atlas,
        backend="sixel",
        width=112,
        max_frames=2,
        embed_images=False,
    )

    assert len(unicode_frames) == 12
    assert unicode_frames[0].frame_id == "idle"
    assert unicode_frames[5].frame_id == "hit_stop"
    assert "OURO STAGE smoke.hex_seal.black_candle :: hit_stop" in unicode_frames[5].text
    assert "HERO" in unicode_frames[5].text
    assert "ENEMY" in unicode_frames[5].text
    assert "EFFECT LANE" in unicode_frames[5].text
    assert "-16 HP" in unicode_frames[5].text
    assert "HIT STOP" in unicode_frames[5].text
    assert "local engine still owns damage/state/victory" in unicode_frames[5].text
    assert all(visual_width(line) <= 96 for frame in unicode_frames for line in frame.text.splitlines())
    assert "OURO 舞台 smoke.hex_seal.black_candle :: hit_stop" in zh_frames[5].text
    assert "英雄" in zh_frames[5].text
    assert "敌方" in zh_frames[5].text
    assert "效果轨" in zh_frames[5].text
    assert "行动" in zh_frames[5].text
    assert "伤害 -16 HP" in zh_frames[5].text
    assert "命中停顿" in zh_frames[5].text
    assert "事实 展示层渲染；伤害/状态/胜负仍由本地引擎结算" in zh_frames[5].text
    assert "EFFECT LANE" not in zh_frames[5].text
    assert "ACTION " not in zh_frames[5].text
    assert all(visual_width(line) <= 96 for frame in zh_frames for line in frame.text.splitlines())
    assert "▓▓XX▓▓-16" not in unicode_frames[5].text
    assert "░▒▓██-16" not in unicode_frames[6].text
    assert "SLNK" not in unicode_frames[6].text

    assert ascii_strip.isascii()
    assert "FRAME 06/12 hit_stop 90ms" in ascii_strip
    assert "DAMAGE -16 HP" in ascii_strip
    assert "runtime" not in ascii_strip.lower()
    assert all(visual_width(line) <= 96 for line in ascii_strip.splitlines())

    assert bitmap_strip.isascii()
    assert "BITMAP FRAME 01/12 idle 70ms" in bitmap_strip
    assert "OURO BITMAP STAGE smoke.hex_seal.black_candle :: idle" in bitmap_strip
    assert "[BITMAP iterm2 role=hero" in bitmap_strip
    assert "sha256=" in bitmap_strip
    assert "runtime bitmap" not in bitmap_strip.lower()
    assert all(visual_width(line) <= 112 for line in bitmap_strip.splitlines())
    assert sixel_strip.isascii()
    assert "BITMAP FRAME 01/12 idle 70ms" in sixel_strip
    assert "[BITMAP sixel role=hero" in sixel_strip
    assert "sha256=" in sixel_strip

    iterm2_frame = BitmapTimelineRenderer(
        backend="iterm2",
        embed_images=True,
    ).render_frame(timeline, timeline.beats[0], atlas)
    kitty_frame = BitmapTimelineRenderer(
        backend="kitty",
        embed_images=True,
    ).render_frame(timeline, timeline.beats[0], atlas)
    sixel_frame = BitmapTimelineRenderer(
        backend="sixel",
        embed_images=True,
    ).render_frame(timeline, timeline.beats[0], atlas)
    zh_bitmap_frame = BitmapTimelineRenderer(
        backend="iterm2",
        embed_images=False,
        language="zh",
    ).render_frame(timeline, timeline.beats[5], atlas)
    assert "\x1b]1337;File=" in iterm2_frame.text
    assert "\x1b_Ga=T,f=100,t=d" in kitty_frame.text
    assert "q=2" in kitty_frame.text
    assert "\x1bPq" in sixel_frame.text
    assert len(kitty_frame.text.splitlines()) >= 26
    assert sixel_frame.text.endswith(
        "FACTS display-only bitmap renderer; local engine owns combat facts"
    )
    assert "OURO BITMAP 舞台 smoke.hex_seal.black_candle :: hit_stop" in zh_bitmap_frame.text
    assert "英雄" in zh_bitmap_frame.text
    assert "敌方" in zh_bitmap_frame.text
    assert "行动" in zh_bitmap_frame.text
    assert "伤害 -16 HP" in zh_bitmap_frame.text
    assert "命中停顿" in zh_bitmap_frame.text
    assert "事实 bitmap 展示层渲染；战斗事实仍由本地引擎结算" in zh_bitmap_frame.text
    assert "OURO BITMAP STAGE" not in zh_bitmap_frame.text


def test_record_combat_stage_writes_evidence_files(tmp_path: Path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/record_combat_stage.py",
            "--content-dir",
            "content",
            "--output-dir",
            str(tmp_path),
            "--width",
            "96",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "combat stage record: OK" in result.stdout
    assert "beats: 12" in result.stdout
    assert "bitmap_frames: 408" in result.stdout
    assert "bitmap_iterm2_filmstrip: hex_seal_bitmap_iterm2_filmstrip.txt" in result.stdout
    assert "bitmap_kitty_filmstrip: hex_seal_bitmap_kitty_filmstrip.txt" in result.stdout
    assert "bitmap_sixel_filmstrip: hex_seal_bitmap_sixel_filmstrip.txt" in result.stdout

    summary = (tmp_path / "summary.txt").read_text(encoding="utf-8")
    unicode_strip = (tmp_path / "hex_seal_unicode_filmstrip.txt").read_text(encoding="utf-8")
    ascii_strip = (tmp_path / "hex_seal_ascii_filmstrip.txt").read_text(encoding="utf-8")
    bitmap_iterm2 = (tmp_path / "hex_seal_bitmap_iterm2_filmstrip.txt").read_text(encoding="utf-8")
    bitmap_kitty = (tmp_path / "hex_seal_bitmap_kitty_filmstrip.txt").read_text(encoding="utf-8")
    bitmap_sixel = (tmp_path / "hex_seal_bitmap_sixel_filmstrip.txt").read_text(encoding="utf-8")

    assert "COMBAT STAGE EVIDENCE" in summary
    assert "atlas_assets: 82" in summary
    assert "bitmap_frames: 408" in summary
    assert "bitmap_filmstrip_iterm2: hex_seal_bitmap_iterm2_filmstrip.txt" in summary
    assert "bitmap_filmstrip_kitty: hex_seal_bitmap_kitty_filmstrip.txt" in summary
    assert "bitmap_filmstrip_sixel: hex_seal_bitmap_sixel_filmstrip.txt" in summary
    assert "Runtime image generation: disabled" in summary
    assert "FRAME 06/12 hit_stop 90ms" in unicode_strip
    assert "░▒▓██>" in unicode_strip
    assert "FRAME 06/12 hit_stop 90ms" in ascii_strip
    assert ascii_strip.isascii()
    assert "BITMAP FRAME 06/12 hit_stop 90ms" in bitmap_iterm2
    assert "[BITMAP iterm2 role=effect" in bitmap_iterm2
    assert "sha256=" in bitmap_iterm2
    assert "BITMAP FRAME 06/12 hit_stop 90ms" in bitmap_kitty
    assert "[BITMAP kitty role=enemy" in bitmap_kitty
    assert "BITMAP FRAME 06/12 hit_stop 90ms" in bitmap_sixel
    assert "[BITMAP sixel role=hero" in bitmap_sixel
    assert bitmap_iterm2.isascii()
    assert bitmap_kitty.isascii()
    assert bitmap_sixel.isascii()


def test_resolved_hex_seal_turn_builds_live_sprite_timeline(content_root: Path):
    bundle = load_content_bundle(content_root)
    atlas = _atlas(content_root)
    loop = BattleLoop(
        bundle,
        MockProvider(seed=2, language="en"),
        seed=2,
        language="en",
    )
    state = loop.setup(
        "hero_shadow_apprentice",
        ("enemy_hungry_cultist", "enemy_black_candle_acolyte"),
    )
    records = []
    loop.run(state, on_hero_turn=lambda _state, record: records.append(record))
    record = next(
        item for item in records
        if item.judge is not None and item.judge.skill_id == "skill_hex_seal"
    )

    timeline = build_combat_stage_timeline(state, record, atlas)
    assert timeline is not None
    assert timeline.timeline_id == "battle.skill_hex_seal.enemy_hungry_cultist"
    assert len(timeline.beats) == 12
    assert timeline.beats[5].hit_stop
    assert timeline.beats[5].damage_pop == f"-{record.judge.damage} HP"
    timeline.validate_against(atlas)

    frames = build_sprite_battle_animation_frames(
        state,
        record,
        atlas=atlas,
        mode="unicode",
        width=96,
    )
    zh_frames = build_sprite_battle_animation_frames(
        state,
        record,
        atlas=atlas,
        mode="unicode",
        width=96,
        language="zh",
    )
    assert len(frames) == 12
    assert frames[0].phase == "idle"
    assert frames[5].phase == "hit_stop"
    assert "OURO STAGE battle.skill_hex_seal.enemy_hungry_cultist" in frames[5].text
    assert "LOG   action resolved by local judge; sprite stage is display-only" in frames[5].text
    assert "local engine still owns damage/state/victory" not in frames[5].text
    assert all(visual_width(line) <= 96 for frame in frames for line in frame.text.splitlines())
    assert "OURO 舞台 battle.skill_hex_seal.enemy_hungry_cultist" in zh_frames[5].text
    assert "日志 行动已由本地裁判结算；sprite 舞台只负责展示" in zh_frames[5].text
    assert "LOG   action resolved" not in zh_frames[5].text


def test_catalog_skill_timelines_cover_all_mvp_skills(content_root: Path):
    bundle = load_content_bundle(content_root)
    atlas = _atlas(content_root)

    timelines = build_catalog_skill_timelines(bundle, atlas)
    by_skill = {timeline.timeline_id.split(".")[1]: timeline for timeline in timelines}
    signature_ids = set(signature_skill_ids())

    assert len(timelines) == len(bundle.skills) == 18
    assert set(by_skill) == set(bundle.skills)
    assert signature_ids <= set(by_skill)
    for skill_id, timeline in by_skill.items():
        timeline.validate_against(atlas)
        minimum = 12 if skill_id in signature_ids else 8
        assert len(timeline.beats) >= minimum
        assert any(beat.hit_stop for beat in timeline.beats)
        assert len({beat.effect_frame for beat in timeline.beats}) >= 4
        assert all(
            atlas.sprite(beat.effect_asset_id).frame(beat.effect_frame).has_bitmap
            for beat in timeline.beats
        )
        assert all(
            atlas.sprite(beat.effect_asset_id).frame(beat.effect_frame).runtime_promoted
            for beat in timeline.beats
        )
        if skill_id in signature_ids:
            assert len(timeline.beats) == 12
            assert any(beat.hero_frame == "signature" for beat in timeline.beats)
            assert "release" not in {beat.frame_id for beat in timeline.beats}

    result = subprocess.run(
        [
            sys.executable,
            "scripts/timeline_coverage_report.py",
            "--content-dir",
            "content",
            "--require-all-skills",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "timeline coverage: OK" in result.stdout
    assert "skills: 18/18" in result.stdout
    assert "- skill_hex_seal: beats=12" in result.stdout
    assert "- skill_tower_brace: beats=12" in result.stdout
    assert "- skill_pierce_string: beats=12" in result.stdout
    assert "- skill_omen_vial: beats=12" in result.stdout
    assert "- skill_burial_engine: beats=12" in result.stdout
    assert "- skill_silent_hymn: beats=12" in result.stdout


def _atlas(content_root: Path) -> SpriteAtlas:
    bundle = load_content_bundle(content_root)
    report = validate_asset_manifest(content_root, bundle)
    return SpriteAtlas.from_manifest_report(report)
