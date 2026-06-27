"""Bitmap timeline renderer for terminal inline image protocols.

The renderer is display-only. It reads QA-promoted runtime PNG frames from the
sprite atlas and emits terminal image escape sequences for backends that can
carry PNG payloads directly. Evidence mode writes deterministic fingerprints
instead of full image payloads.
"""
from __future__ import annotations

import base64
import hashlib
import struct
import zlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from ouro_agent.art.sprite_atlas import SpriteAtlas, SpriteFrame
from ouro_agent.art.timelines import AnimationTimeline, TimelineBeat
from ouro_agent.content.loader import ContentError
from ouro_agent.i18n import visual_width
from ouro_agent.tui.layout import assert_width, fit_text
from ouro_agent.tui.timeline_renderer import (
    StageRenderFrame,
    TimelineRenderLabels,
    timeline_render_labels,
)


BITMAP_RENDER_BACKENDS: tuple[str, ...] = ("iterm2", "kitty", "sixel")
SIXEL_PALETTE: tuple[tuple[int, int, int], ...] = (
    (0, 0, 0),
    (32, 28, 24),
    (74, 61, 48),
    (126, 91, 54),
    (189, 123, 58),
    (238, 178, 86),
    (71, 78, 88),
    (112, 123, 129),
    (168, 178, 174),
    (228, 220, 190),
    (73, 32, 39),
    (129, 45, 45),
    (197, 68, 52),
    (52, 71, 95),
    (80, 104, 132),
    (136, 155, 168),
)


@dataclass(frozen=True)
class BitmapTimelineRenderer:
    """Render timeline beats as iTerm2/Kitty inline PNG frames."""

    backend: str = "iterm2"
    width: int = 96
    contract_line: bool = True
    embed_images: bool = True
    language: str = "en"

    @property
    def name(self) -> str:
        return f"{self.backend}-bitmap"

    def render_frame(
        self,
        timeline: AnimationTimeline,
        beat: TimelineBeat,
        atlas: SpriteAtlas,
    ) -> StageRenderFrame:
        backend = _normalize_bitmap_backend(self.backend)
        safe_width = max(72, self.width)
        labels = timeline_render_labels(self.language)
        hero_frame = atlas.sprite(beat.hero_asset_id).frame(beat.hero_frame)
        enemy_frame = atlas.sprite(beat.enemy_asset_id).frame(beat.enemy_frame)
        effect_frame = atlas.sprite(beat.effect_asset_id).frame(beat.effect_frame)

        lines = [
            fit_text(
                f"{_bitmap_stage_prefix(labels)} {timeline.timeline_id} :: "
                f"{beat.frame_id} {beat.duration_ms}ms [{backend}]",
                safe_width,
            ),
            fit_text(f"{labels.hero}   {beat.hero_asset_id}/{beat.hero_frame}", safe_width),
            _render_png_frame(
                backend,
                hero_frame,
                role="hero",
                asset_id=beat.hero_asset_id,
                frame_id=beat.hero_frame,
                cells=(18, 7),
                embed_images=self.embed_images,
                width=safe_width,
            ),
            fit_text(
                f"{_effect_label(labels)} {beat.effect_asset_id}/{beat.effect_frame} "
                f"offset={beat.effect_offset}",
                safe_width,
            ),
            _render_png_frame(
                backend,
                effect_frame,
                role="effect",
                asset_id=beat.effect_asset_id,
                frame_id=beat.effect_frame,
                cells=(20, 5),
                embed_images=self.embed_images,
                width=safe_width,
            ),
            fit_text(f"{labels.enemy}  {beat.enemy_asset_id}/{beat.enemy_frame}", safe_width),
            _render_png_frame(
                backend,
                enemy_frame,
                role="enemy",
                asset_id=beat.enemy_asset_id,
                frame_id=beat.enemy_frame,
                cells=(18, 7),
                embed_images=self.embed_images,
                width=safe_width,
            ),
            fit_text(_action_line(beat, labels=labels), safe_width),
            fit_text(_status_line(beat, labels=labels), safe_width),
            fit_text(_footer(contract_line=self.contract_line, labels=labels), safe_width),
        ]
        text = "\n".join(lines)
        if not self.embed_images:
            assert_width(text, safe_width)
        return StageRenderFrame(
            frame_id=beat.frame_id,
            duration_ms=beat.duration_ms,
            text=text,
        )


def render_bitmap_timeline_frames(
    timeline: AnimationTimeline,
    atlas: SpriteAtlas,
    *,
    backend: str = "iterm2",
    width: int = 96,
    contract_line: bool = True,
    embed_images: bool = True,
    language: str = "en",
) -> tuple[StageRenderFrame, ...]:
    """Render bitmap timeline frames for a PNG-capable backend."""
    timeline.validate_against(atlas)
    renderer = BitmapTimelineRenderer(
        backend=backend,
        width=width,
        contract_line=contract_line,
        embed_images=embed_images,
        language=language,
    )
    return tuple(renderer.render_frame(timeline, beat, atlas) for beat in timeline.beats)


def render_bitmap_timeline_filmstrip(
    timeline: AnimationTimeline,
    atlas: SpriteAtlas,
    *,
    backend: str = "iterm2",
    width: int = 96,
    max_frames: int | None = None,
    contract_line: bool = True,
    embed_images: bool = False,
    language: str = "en",
) -> str:
    """Render a bitmap filmstrip.

    Evidence callers should keep ``embed_images=False`` so the output stays
    compact, deterministic, and reviewable in text logs.
    """
    frames = render_bitmap_timeline_frames(
        timeline,
        atlas,
        backend=backend,
        width=width,
        contract_line=contract_line,
        embed_images=embed_images,
        language=language,
    )
    selected = frames if max_frames is None else frames[: max(0, max_frames)]
    divider = "#" * max(72, width)
    chunks: list[str] = []
    for index, frame in enumerate(selected, start=1):
        header = (
            f"BITMAP FRAME {index:02d}/{len(frames):02d} "
            f"{frame.frame_id} {frame.duration_ms}ms"
        )
        chunks.append(f"{header}\n{frame.text}")
    filmstrip = f"\n{divider}\n".join(chunks)
    if not embed_images:
        assert_width(filmstrip, max(72, width))
    return filmstrip


def render_bitmap_image_probe(
    bitmap_path: Path,
    *,
    backend: str,
    cells: tuple[int, int] = (24, 14),
) -> str:
    """Render one runtime PNG as an inline terminal image probe."""

    normalized = _normalize_bitmap_backend(backend)
    data = bitmap_path.read_bytes()
    _validate_png(bitmap_path, data)
    _width, height = cells
    return _image_escape(normalized, bitmap_path, data, cells=cells) + ("\n" * max(0, height - 1))


def _render_png_frame(
    backend: str,
    frame: SpriteFrame,
    *,
    role: str,
    asset_id: str,
    frame_id: str,
    cells: tuple[int, int],
    embed_images: bool,
    width: int,
) -> str:
    path = _bitmap_path(frame, role=role, asset_id=asset_id, frame_id=frame_id)
    data = path.read_bytes()
    _validate_png(path, data)
    if embed_images:
        _width, height = cells
        return _image_escape(backend, path, data, cells=cells) + ("\n" * max(0, height - 1))
    asset_label = asset_id.removesuffix("_battle_sheet")
    asset_label = asset_label.removesuffix("_effect_sheet")
    asset_label = asset_label.removesuffix("_actor_sheet")
    return fit_text(
        " ".join(
            [
                f"[BITMAP {backend}",
                f"role={role}",
                f"frame={frame_id}",
                f"sha256={hashlib.sha256(data).hexdigest()[:16]}",
                f"bytes={len(data)}",
                f"asset={asset_label}",
                f"png={path.name}",
                f"anchor={frame.anchor[0]},{frame.anchor[1]}",
                f"size={_size_label(frame)}]",
            ]
        ),
        width,
    )


def _bitmap_path(frame: SpriteFrame, *, role: str, asset_id: str, frame_id: str) -> Path:
    if frame.bitmap_path is None:
        raise ContentError(
            f"{asset_id}/{frame_id}: {role} frame has no runtime bitmap path"
        )
    if not frame.runtime_promoted:
        raise ContentError(
            f"{asset_id}/{frame_id}: {role} frame is not QA-promoted runtime"
        )
    if not frame.bitmap_path.is_file():
        raise ContentError(
            f"{asset_id}/{frame_id}: bitmap file is missing: {frame.bitmap_path}"
        )
    return frame.bitmap_path


def _validate_png(path: Path, data: bytes) -> None:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ContentError(f"{path}: runtime bitmap is not a PNG")


def _image_escape(
    backend: str,
    path: Path,
    data: bytes,
    *,
    cells: tuple[int, int],
) -> str:
    if backend == "iterm2":
        return _iterm2_escape(path, data, cells=cells)
    if backend == "kitty":
        return _kitty_escape(data, cells=cells)
    if backend == "sixel":
        return _sixel_escape(data, cells=cells)
    raise ValueError(f"unsupported bitmap backend: {backend}")


def _iterm2_escape(path: Path, data: bytes, *, cells: tuple[int, int]) -> str:
    name = base64.b64encode(path.name.encode("utf-8")).decode("ascii")
    payload = base64.b64encode(data).decode("ascii")
    width, height = cells
    return (
        "\x1b]1337;File="
        f"name={name};inline=1;width={width};height={height};"
        f"preserveAspectRatio=1:{payload}\x07"
    )


def _kitty_escape(data: bytes, *, cells: tuple[int, int]) -> str:
    payload = base64.b64encode(data).decode("ascii")
    width, height = cells
    chunks = [payload[index : index + 4096] for index in range(0, len(payload), 4096)]
    if not chunks:
        chunks = [""]
    parts: list[str] = []
    for index, chunk in enumerate(chunks):
        more = 1 if index < len(chunks) - 1 else 0
        if index == 0:
            control = f"a=T,f=100,t=d,c={width},r={height},q=2,m={more}"
        else:
            control = f"m={more}"
        parts.append(f"\x1b_G{control};{chunk}\x1b\\")
    return "".join(parts)


def _sixel_escape(data: bytes, *, cells: tuple[int, int]) -> str:
    width, height = cells
    pixel_width = max(1, width * 6)
    pixel_height = max(1, height * 12)
    return _sixel_escape_cached(data, pixel_width, pixel_height)


@lru_cache(maxsize=256)
def _sixel_escape_cached(data: bytes, pixel_width: int, pixel_height: int) -> str:
    source_width, source_height, pixels = _decode_png_rgba(data)
    target_width, target_height, indexed = _scale_and_quantize_rgba(
        source_width,
        source_height,
        pixels,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
    )
    palette = _sixel_palette_definitions()
    body = _indexed_pixels_to_sixel(indexed, width=target_width, height=target_height)
    return f"\x1bPq\"1;1;{target_width};{target_height}{palette}{body}\x1b\\"


def _decode_png_rgba(data: bytes) -> tuple[int, int, tuple[tuple[int, int, int, int], ...]]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ContentError("runtime bitmap is not a PNG")
    width = height = bit_depth = color_type = interlace = 0
    palette: list[tuple[int, int, int]] = []
    transparency: bytes = b""
    idat_parts: list[bytes] = []
    pos = 8
    while pos + 12 <= len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if chunk_type == b"IHDR":
            (
                width,
                height,
                bit_depth,
                color_type,
                _compression,
                _filter,
                interlace,
            ) = struct.unpack(">IIBBBBB", chunk_data)
        elif chunk_type == b"PLTE":
            palette = [
                tuple(chunk_data[index : index + 3])  # type: ignore[arg-type]
                for index in range(0, len(chunk_data), 3)
            ]
        elif chunk_type == b"tRNS":
            transparency = chunk_data
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width <= 0 or height <= 0:
        raise ContentError("PNG is missing IHDR dimensions")
    if bit_depth != 8:
        raise ContentError(f"PNG bit depth {bit_depth} is not supported for SIXEL")
    if interlace != 0:
        raise ContentError("interlaced PNG is not supported for SIXEL")
    channels_by_type = {0: 1, 2: 3, 3: 1, 6: 4}
    if color_type not in channels_by_type:
        raise ContentError(f"PNG color type {color_type} is not supported for SIXEL")

    channels = channels_by_type[color_type]
    stride = width * channels
    raw = zlib.decompress(b"".join(idat_parts))
    expected = height * (1 + stride)
    if len(raw) < expected:
        raise ContentError("PNG pixel data is shorter than expected")

    rows: list[bytes] = []
    offset = 0
    previous = bytes(stride)
    for _row in range(height):
        filter_type = raw[offset]
        offset += 1
        scanline = raw[offset : offset + stride]
        offset += stride
        row = _unfilter_png_scanline(
            filter_type,
            scanline,
            previous,
            bytes_per_pixel=channels,
        )
        rows.append(row)
        previous = row

    pixels: list[tuple[int, int, int, int]] = []
    for row in rows:
        for x in range(width):
            start = x * channels
            if color_type == 0:
                gray = row[start]
                pixels.append((gray, gray, gray, 255))
            elif color_type == 2:
                pixels.append((row[start], row[start + 1], row[start + 2], 255))
            elif color_type == 3:
                index = row[start]
                if index >= len(palette):
                    rgba = (0, 0, 0, 0)
                else:
                    red, green, blue = palette[index]
                    alpha = transparency[index] if index < len(transparency) else 255
                    rgba = (red, green, blue, alpha)
                pixels.append(rgba)
            else:
                pixels.append((row[start], row[start + 1], row[start + 2], row[start + 3]))
    return width, height, tuple(pixels)


def _unfilter_png_scanline(
    filter_type: int,
    scanline: bytes,
    previous: bytes,
    *,
    bytes_per_pixel: int,
) -> bytes:
    result = bytearray(scanline)
    for index, value in enumerate(scanline):
        left = result[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        up = previous[index] if index < len(previous) else 0
        up_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        if filter_type == 0:
            restored = value
        elif filter_type == 1:
            restored = value + left
        elif filter_type == 2:
            restored = value + up
        elif filter_type == 3:
            restored = value + ((left + up) // 2)
        elif filter_type == 4:
            restored = value + _paeth_predictor(left, up, up_left)
        else:
            raise ContentError(f"PNG filter type {filter_type} is not supported")
        result[index] = restored & 0xFF
    return bytes(result)


def _paeth_predictor(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    dist_left = abs(estimate - left)
    dist_up = abs(estimate - up)
    dist_up_left = abs(estimate - up_left)
    if dist_left <= dist_up and dist_left <= dist_up_left:
        return left
    if dist_up <= dist_up_left:
        return up
    return up_left


def _scale_and_quantize_rgba(
    source_width: int,
    source_height: int,
    pixels: tuple[tuple[int, int, int, int], ...],
    *,
    pixel_width: int,
    pixel_height: int,
) -> tuple[int, int, tuple[int, ...]]:
    scale = min(pixel_width / source_width, pixel_height / source_height)
    target_width = max(1, min(pixel_width, round(source_width * scale)))
    target_height = max(1, min(pixel_height, round(source_height * scale)))
    indexed: list[int] = []
    for y in range(target_height):
        source_y = min(source_height - 1, int(y * source_height / target_height))
        for x in range(target_width):
            source_x = min(source_width - 1, int(x * source_width / target_width))
            red, green, blue, alpha = pixels[source_y * source_width + source_x]
            if alpha < 32:
                indexed.append(-1)
            else:
                indexed.append(_nearest_sixel_palette_index(red, green, blue))
    return target_width, target_height, tuple(indexed)


def _nearest_sixel_palette_index(red: int, green: int, blue: int) -> int:
    best_index = 0
    best_distance = 1_000_000
    for index, (pal_red, pal_green, pal_blue) in enumerate(SIXEL_PALETTE):
        distance = (
            (red - pal_red) * (red - pal_red)
            + (green - pal_green) * (green - pal_green)
            + (blue - pal_blue) * (blue - pal_blue)
        )
        if distance < best_distance:
            best_index = index
            best_distance = distance
    return best_index


def _sixel_palette_definitions() -> str:
    chunks = []
    for index, (red, green, blue) in enumerate(SIXEL_PALETTE):
        chunks.append(
            f"#{index};2;{_to_sixel_percent(red)};"
            f"{_to_sixel_percent(green)};{_to_sixel_percent(blue)}"
        )
    return "".join(chunks)


def _to_sixel_percent(value: int) -> int:
    return max(0, min(100, round(value * 100 / 255)))


def _indexed_pixels_to_sixel(indexed: tuple[int, ...], *, width: int, height: int) -> str:
    used_colors = sorted({value for value in indexed if value >= 0})
    if not used_colors:
        return ""
    bands: list[str] = []
    for y in range(0, height, 6):
        color_chunks: list[str] = []
        for color_index in used_colors:
            chars = []
            has_pixels = False
            for x in range(width):
                bits = 0
                for dy in range(6):
                    yy = y + dy
                    if yy >= height:
                        continue
                    if indexed[yy * width + x] == color_index:
                        bits |= 1 << dy
                        has_pixels = True
                chars.append(chr(63 + bits))
            if has_pixels:
                color_chunks.append(f"#{color_index}{_sixel_rle(chars)}")
        if color_chunks:
            bands.append("$".join(color_chunks))
        if y + 6 < height:
            bands.append("-")
    return "".join(bands)


def _sixel_rle(chars: list[str]) -> str:
    if not chars:
        return ""
    chunks: list[str] = []
    run_char = chars[0]
    run_length = 1
    for char in chars[1:]:
        if char == run_char:
            run_length += 1
        else:
            chunks.append(_sixel_run(run_char, run_length))
            run_char = char
            run_length = 1
    chunks.append(_sixel_run(run_char, run_length))
    return "".join(chunks)


def _sixel_run(char: str, length: int) -> str:
    if length >= 4:
        return f"!{length}{char}"
    return char * length


def _normalize_bitmap_backend(backend: str) -> str:
    normalized = backend.strip().lower()
    if normalized not in BITMAP_RENDER_BACKENDS:
        supported = ", ".join(BITMAP_RENDER_BACKENDS)
        raise ValueError(f"bitmap backend must be one of {supported}; got {backend!r}")
    return normalized


def _bitmap_stage_prefix(labels: TimelineRenderLabels) -> str:
    return "OURO BITMAP 舞台" if labels.stage_prefix == "OURO 舞台" else "OURO BITMAP STAGE"


def _effect_label(labels: TimelineRenderLabels) -> str:
    return "效果" if labels.effect_lane == "效果轨" else "EFFECT"


def _action_line(beat: TimelineBeat, *, labels: TimelineRenderLabels) -> str:
    action = " -> ".join(
        [
            beat.hero_frame,
            beat.effect_frame,
            labels.hit_stop if beat.hit_stop else beat.enemy_frame,
        ]
    )
    return f"{labels.action} {action}"


def _status_line(beat: TimelineBeat, *, labels: TimelineRenderLabels) -> str:
    status = f"{labels.damage} " + (beat.damage_pop or "-")
    status += f" | {labels.hud} " + (beat.hud_delta or "-")
    if beat.hit_stop:
        status += f" | {labels.hit_stop}"
    return status


def _footer(*, contract_line: bool, labels: TimelineRenderLabels) -> str:
    if contract_line:
        if labels.stage_prefix == "OURO 舞台":
            return "事实 bitmap 展示层渲染；战斗事实仍由本地引擎结算"
        return "FACTS display-only bitmap renderer; local engine owns combat facts"
    if labels.stage_prefix == "OURO 舞台":
        return "日志 bitmap sprite 舞台只负责展示；裁判事实仍在本地"
    return "LOG   bitmap sprite stage is display-only; judge facts are local"


def _size_label(frame: SpriteFrame) -> str:
    if frame.frame_size is None:
        return "-"
    return f"{frame.frame_size[0]}x{frame.frame_size[1]}"
