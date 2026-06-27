"""Deterministic timeline renderer for terminal graphics evidence."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ouro_agent.art.sprite_atlas import SpriteAtlas, SpriteFrame
from ouro_agent.art.timelines import AnimationTimeline, TimelineBeat
from ouro_agent.i18n import pad_right, visual_width
from ouro_agent.tui.canvas import Surface
from ouro_agent.tui.glyphs import GlyphSet, get_glyph_set
from ouro_agent.tui.layout import assert_width, fit_text


@dataclass(frozen=True)
class StageRenderFrame:
    frame_id: str
    duration_ms: int
    text: str


@dataclass(frozen=True)
class TimelineRenderLabels:
    stage_prefix: str
    hero: str
    enemy: str
    effect_lane: str
    action: str
    damage: str
    hud: str
    hit_stop: str
    facts_footer: str
    log_footer: str


class RendererBackend(Protocol):
    name: str

    def render_frame(
        self,
        timeline: AnimationTimeline,
        beat: TimelineBeat,
        atlas: SpriteAtlas,
    ) -> StageRenderFrame:
        """Render a single timeline beat."""


@dataclass(frozen=True)
class CellTimelineRenderer:
    """Render timeline beats to a stable Unicode/ASCII cell stage."""

    mode: str = "unicode"
    width: int = 96
    height: int = 16
    contract_line: bool = True
    language: str = "en"

    @property
    def name(self) -> str:
        return "unicode-cell" if self.mode != "ascii" else "ascii-cell"

    def render_frame(
        self,
        timeline: AnimationTimeline,
        beat: TimelineBeat,
        atlas: SpriteAtlas,
    ) -> StageRenderFrame:
        safe_width = max(72, self.width)
        safe_height = max(14, self.height)
        glyphs = get_glyph_set("unicode" if self.mode != "ascii" else "ascii")
        labels = timeline_render_labels(self.language)
        surface = Surface(safe_width, safe_height)
        _draw_stage_frame(
            surface,
            timeline,
            beat,
            atlas,
            glyphs=glyphs,
            contract_line=self.contract_line,
            labels=labels,
        )
        lines = surface.render()
        text = "\n".join(fit_text(line.rstrip(), safe_width) for line in lines)
        assert_width(text, safe_width)
        return StageRenderFrame(
            frame_id=beat.frame_id,
            duration_ms=beat.duration_ms,
            text=text,
        )


def render_timeline_frames(
    timeline: AnimationTimeline,
    atlas: SpriteAtlas,
    *,
    mode: str = "unicode",
    width: int = 96,
    contract_line: bool = True,
    language: str = "en",
) -> tuple[StageRenderFrame, ...]:
    timeline.validate_against(atlas)
    renderer = CellTimelineRenderer(
        mode=mode,
        width=width,
        contract_line=contract_line,
        language=language,
    )
    return tuple(renderer.render_frame(timeline, beat, atlas) for beat in timeline.beats)


def render_timeline_filmstrip(
    timeline: AnimationTimeline,
    atlas: SpriteAtlas,
    *,
    mode: str = "unicode",
    width: int = 96,
    max_frames: int | None = None,
    contract_line: bool = True,
    language: str = "en",
) -> str:
    frames = render_timeline_frames(
        timeline,
        atlas,
        mode=mode,
        width=width,
        contract_line=contract_line,
        language=language,
    )
    selected = frames if max_frames is None else frames[:max(0, max_frames)]
    divider = ("█" if mode != "ascii" else "#") * max(72, width)
    chunks: list[str] = []
    for index, frame in enumerate(selected, start=1):
        header = f"FRAME {index:02d}/{len(frames):02d} {frame.frame_id} {frame.duration_ms}ms"
        chunks.append(f"{header}\n{frame.text}")
    filmstrip = f"\n{divider}\n".join(chunks)
    assert_width(filmstrip, max(72, width))
    return filmstrip


def _draw_stage_frame(
    surface: Surface,
    timeline: AnimationTimeline,
    beat: TimelineBeat,
    atlas: SpriteAtlas,
    *,
    glyphs: GlyphSet,
    contract_line: bool,
    labels: TimelineRenderLabels,
) -> None:
    width = surface.width
    height = surface.height
    surface.draw_box(0, 0, width, height, glyphs)
    surface.draw_text(
        2,
        1,
        fit_text(
            f"{labels.stage_prefix} {timeline.timeline_id} :: {beat.frame_id} {beat.duration_ms}ms",
            width - 4,
        ),
    )
    surface.draw_text(3, 3, labels.hero)
    surface.draw_text(max(3, width - 16), 3, labels.enemy)
    lane_label = labels.effect_lane
    surface.draw_text(max(0, (width - visual_width(lane_label)) // 2), 3, lane_label)

    hero_frame = atlas.sprite(beat.hero_asset_id).frame(beat.hero_frame)
    enemy_frame = atlas.sprite(beat.enemy_asset_id).frame(beat.enemy_frame)
    effect_frame = atlas.sprite(beat.effect_asset_id).frame(beat.effect_frame)
    _draw_sprite_card(surface, 3, 5, hero_frame, beat.hero_frame, glyphs=glyphs)
    _draw_sprite_card(surface, width - 23, 5, enemy_frame, beat.enemy_frame, glyphs=glyphs)
    _draw_effect_lane(surface, beat, effect_frame, glyphs=glyphs)

    action = " -> ".join(
        [
            beat.hero_frame,
            beat.effect_frame,
            labels.hit_stop if beat.hit_stop else beat.enemy_frame,
        ]
    )
    surface.draw_text(3, height - 4, fit_text(f"{labels.action} {action}", width - 6))
    status = f"{labels.damage} " + (beat.damage_pop or "-")
    status += f" | {labels.hud} " + (beat.hud_delta or "-")
    if beat.hit_stop:
        status += f" | {labels.hit_stop}"
    surface.draw_text(3, height - 3, fit_text(status, width - 6))
    footer = labels.facts_footer if contract_line else labels.log_footer
    surface.draw_text(3, height - 2, fit_text(footer, width - 6))


def timeline_render_labels(language: str = "en") -> TimelineRenderLabels:
    if language == "zh":
        return TimelineRenderLabels(
            stage_prefix="OURO 舞台",
            hero="英雄",
            enemy="敌方",
            effect_lane="效果轨",
            action="行动",
            damage="伤害",
            hud="HUD",
            hit_stop="命中停顿",
            facts_footer="事实 展示层渲染；伤害/状态/胜负仍由本地引擎结算",
            log_footer="日志 行动已由本地裁判结算；sprite 舞台只负责展示",
        )
    return TimelineRenderLabels(
        stage_prefix="OURO STAGE",
        hero="HERO",
        enemy="ENEMY",
        effect_lane="EFFECT LANE",
        action="ACTION",
        damage="DAMAGE",
        hud="HUD",
        hit_stop="HIT STOP",
        facts_footer="FACTS display-only renderer; local engine still owns damage/state/victory",
        log_footer="LOG   action resolved by local judge; sprite stage is display-only",
    )


def _draw_sprite_card(
    surface: Surface,
    x: int,
    y: int,
    frame: SpriteFrame,
    label: str,
    *,
    glyphs: GlyphSet,
) -> None:
    card_w = 19
    card_h = 6
    surface.draw_box(x, y, card_w, card_h, glyphs)
    visual = _sprite_visual(frame, glyphs=glyphs)
    surface.draw_text(x + 2, y + 1, fit_text(label.upper(), card_w - 4))
    for row_index, row in enumerate(visual[:3], start=2):
        surface.draw_text(x + 2, y + row_index, fit_text(row, card_w - 4))
    tag = "BMP" if frame.has_bitmap else "CELL"
    if not frame.runtime_promoted and frame.has_bitmap:
        tag = "CAND"
    surface.draw_text(x + 2, y + card_h - 1, fit_text(f"{tag} {frame.fallback_cell_id}", card_w - 4))


def _draw_effect_lane(
    surface: Surface,
    beat: TimelineBeat,
    frame: SpriteFrame,
    *,
    glyphs: GlyphSet,
) -> None:
    lane_y = 7
    center = surface.width // 2
    lane_start = max(24, center - 16)
    lane_width = min(35, surface.width - lane_start - 24)
    for offset in range(lane_width):
        glyph = glyphs.mid if offset % 4 in {1, 2} else glyphs.light
        surface.put(lane_start + offset, lane_y, glyph)
    effect_x = max(lane_start, min(lane_start + lane_width - 5, lane_start + beat.effect_offset[0] // 2))
    effect = _effect_visual(frame, beat, glyphs=glyphs)
    for row_index, row in enumerate(effect):
        surface.draw_text(effect_x, lane_y - 1 + row_index, fit_text(row, 12))
    if beat.damage_pop:
        enemy_x = surface.width - 23
        damage_x = max(lane_start + 1, enemy_x - 13)
        surface.draw_text(damage_x, lane_y - 2, fit_text(beat.damage_pop, 12))


def _sprite_visual(frame: SpriteFrame, *, glyphs: GlyphSet) -> tuple[str, ...]:
    if frame.has_bitmap:
        width = max(1, (frame.visible_bbox or (0, 0, 8, 8))[2] - (frame.visible_bbox or (0, 0, 8, 8))[0])
        height = max(1, (frame.visible_bbox or (0, 0, 8, 8))[3] - (frame.visible_bbox or (0, 0, 8, 8))[1])
        scale = max(1, min(12, width // max(1, height // 2)))
        return (
            glyphs.upper + glyphs.solid * min(9, scale + 2) + glyphs.upper,
            glyphs.left + glyphs.mid * min(9, scale + 3) + glyphs.right,
            glyphs.lower + glyphs.solid * min(9, scale + 1) + glyphs.lower,
        )
    seed = frame.fallback_cell_id.rsplit(".", 1)[-1][:8].upper()
    return (
        glyphs.upper + glyphs.solid * 3 + glyphs.upper,
        glyphs.left + pad_right(seed, 8)[:8] + glyphs.right,
        glyphs.lower + glyphs.mid * 3 + glyphs.lower,
    )


def _effect_visual(
    frame: SpriteFrame, beat: TimelineBeat, *, glyphs: GlyphSet
) -> tuple[str, ...]:
    if beat.hit_stop:
        core = "XX" if glyphs.name == "ascii" else "▓▓XX▓▓"
        return (core, glyphs.solid * min(8, len(core) + 2))
    token = frame.frame_id.upper()[:6]
    arrow = "-->" if glyphs.name == "ascii" else "░▒▓██>"
    return (arrow, token)
