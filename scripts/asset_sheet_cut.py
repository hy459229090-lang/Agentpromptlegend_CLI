#!/usr/bin/env python3
"""Cut a generated sprite-sheet candidate into frame PNGs and metadata."""
from __future__ import annotations

import argparse
import binascii
import re
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

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


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


class PngError(ValueError):
    """Raised when a candidate PNG cannot be decoded by the lightweight reader."""


@dataclass(frozen=True)
class RgbaImage:
    width: int
    height: int
    pixels: tuple[int, ...]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Cut a development-time generated sprite sheet into scratch frame "
            "PNGs and metadata. This does not promote runtime assets."
        )
    )
    parser.add_argument("--content-dir", default="content")
    parser.add_argument("--work-order-id", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--candidate-png", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--metadata-output")
    parser.add_argument("--cols", type=int)
    parser.add_argument("--rows", type=int)
    parser.add_argument(
        "--frame-ids",
        help="Optional comma-separated frame IDs. Defaults to manifest-required frames.",
    )
    parser.add_argument(
        "--cell-indices",
        help=(
            "Optional comma-separated zero-based grid cell indices to map to "
            "frame IDs. Use when a generated sheet has spacer or variant cells."
        ),
    )
    parser.add_argument("--chroma-key", default="#00ff00")
    parser.add_argument("--chroma-threshold", type=int, default=72)
    parser.add_argument("--green-floor", type=int, default=160)
    parser.add_argument("--green-dominance", type=int, default=48)
    parser.add_argument("--min-visible-pixels", type=int, default=8)
    parser.add_argument(
        "--allow-content-assets",
        action="store_true",
        help="Allow writing under content/assets. Use only after QA approval.",
    )
    args = parser.parse_args(argv)

    try:
        content_dir = Path(args.content_dir)
        output_dir = Path(args.output_dir)
        _reject_unreviewed_runtime_output(
            output_dir,
            content_dir=content_dir,
            allow_content_assets=args.allow_content_assets,
        )
        bundle = load_content_bundle(content_dir)
        manifest_report = validate_asset_manifest(content_dir, bundle)
        template = build_asset_qa_template(
            manifest_report,
            work_order_id=args.work_order_id,
            candidate_id=args.candidate_id,
            candidate_ref=f"scratch://{_safe_name(args.candidate_id)}",
        )
        manifest_frames = {frame.frame_id: frame for frame in template.frame_metadata}
        frame_ids = _parse_frame_ids(args.frame_ids) or [
            frame.frame_id for frame in template.frame_metadata
        ]
        if len(set(frame_ids)) != len(frame_ids):
            raise ValueError("frame IDs must be unique")
        unknown_frames = sorted(set(frame_ids) - set(manifest_frames))
        if unknown_frames:
            raise ValueError(f"frame IDs are not in the manifest: {unknown_frames}")
        cols, rows = _resolve_grid(args.cols, args.rows, len(frame_ids))
        if cols * rows < len(frame_ids):
            raise ValueError(
                f"grid {cols}x{rows} has fewer cells than {len(frame_ids)} frames"
            )
        selected_cell_indices = _parse_cell_indices(
            args.cell_indices,
            frame_count=len(frame_ids),
            cell_count=cols * rows,
        )

        source_path = Path(args.candidate_png)
        image = _read_png_rgba(source_path)
        chroma = _parse_hex_color(args.chroma_key)
        frame_root = output_dir / template.asset_id / _safe_name(args.candidate_id)
        frame_root.mkdir(parents=True, exist_ok=True)
        written_frames = []
        for index, frame_id in enumerate(frame_ids):
            cell_index = selected_cell_indices[index]
            col = cell_index % cols
            row = cell_index // cols
            bounds = _cell_bounds(image.width, image.height, cols, rows, col, row)
            cell = _crop_rgba(image, bounds)
            keyed_pixels = _apply_chroma_key(
                cell.pixels,
                chroma=chroma,
                threshold=args.chroma_threshold,
                green_floor=args.green_floor,
                green_dominance=args.green_dominance,
            )
            visible_bbox = _visible_bbox(cell.width, cell.height, keyed_pixels)
            if visible_bbox is None:
                raise ValueError(f"frame '{frame_id}' has no visible pixels after keying")
            visible_pixels = _visible_pixel_count(keyed_pixels)
            if visible_pixels < args.min_visible_pixels:
                raise ValueError(
                    f"frame '{frame_id}' has only {visible_pixels} visible pixels"
                )
            frame_path = frame_root / f"{_safe_name(frame_id)}.png"
            _write_png_rgba(frame_path, cell.width, cell.height, keyed_pixels)
            manifest_frame = manifest_frames[frame_id]
            written_frames.append(
                {
                    "frame_id": frame_id,
                    "path": str(frame_path),
                    "grid_cell": [col, row],
                    "source_bounds": list(bounds),
                    "frame_size": [cell.width, cell.height],
                    "visible_bbox": list(visible_bbox),
                    "visible_pixels": visible_pixels,
                    "anchor": list(manifest_frame.anchor),
                    "duration_ms": manifest_frame.duration_ms or 80,
                    "fallback_cell_id": manifest_frame.fallback_cell_id,
                }
            )

        metadata = {
            "schema_version": "0.1",
            "asset_id": template.asset_id,
            "candidate_id": args.candidate_id,
            "work_order_id": args.work_order_id,
            "source_brief": template.source_brief,
            "source_image": str(source_path),
            "grid": {"cols": cols, "rows": rows},
            "selected_cell_indices": selected_cell_indices,
            "chroma_key": args.chroma_key,
            "chroma_threshold": args.chroma_threshold,
            "ignored_cells": cols * rows - len(set(selected_cell_indices)),
            "runtime_promoted": False,
            "frames": written_frames,
        }
        metadata_path = (
            Path(args.metadata_output)
            if args.metadata_output
            else frame_root / "cut_metadata.yaml"
        )
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            yaml.safe_dump(metadata, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
    except (ContentError, OSError, PngError, ValueError) as err:
        print("asset sheet cut: FAIL", file=sys.stderr)
        print(f"error: {err}", file=sys.stderr)
        return 2

    print("asset sheet cut: OK")
    print(f"asset_id: {template.asset_id}")
    print(f"candidate_id: {args.candidate_id}")
    print(f"frames_written: {len(written_frames)}")
    print(f"grid: {cols}x{rows}")
    print(f"ignored_cells: {cols * rows - len(set(selected_cell_indices))}")
    print(f"output_dir: {frame_root}")
    print(f"metadata: {metadata_path}")
    print("runtime promotion: disabled until QA passes")
    return 0


def _reject_unreviewed_runtime_output(
    output_dir: Path, *, content_dir: Path, allow_content_assets: bool
) -> None:
    if allow_content_assets:
        return
    assets_root = (content_dir / "assets").resolve()
    target = output_dir.resolve()
    if target == assets_root or target.is_relative_to(assets_root):
        raise ValueError(
            "refusing to write generated frames under content/assets before QA"
        )


def _parse_frame_ids(value: str | None) -> list[str]:
    if not value:
        return []
    frame_ids = [item.strip() for item in value.split(",")]
    return [item for item in frame_ids if item]


def _parse_cell_indices(
    value: str | None, *, frame_count: int, cell_count: int
) -> list[int]:
    if not value:
        return list(range(frame_count))
    cells: list[int] = []
    for raw in value.split(","):
        text = raw.strip()
        if not text:
            continue
        try:
            cell_index = int(text)
        except ValueError as err:
            raise ValueError(f"invalid cell index '{text}'") from err
        if cell_index < 0 or cell_index >= cell_count:
            raise ValueError(
                f"cell index {cell_index} is outside grid cell range 0..{cell_count - 1}"
            )
        cells.append(cell_index)
    if len(cells) != frame_count:
        raise ValueError(
            f"--cell-indices must provide {frame_count} entries, got {len(cells)}"
        )
    if len(set(cells)) != len(cells):
        raise ValueError("cell indices must be unique")
    return cells


def _resolve_grid(cols: int | None, rows: int | None, frame_count: int) -> tuple[int, int]:
    if cols is not None and cols <= 0:
        raise ValueError("--cols must be positive")
    if rows is not None and rows <= 0:
        raise ValueError("--rows must be positive")
    if cols is None and rows is None:
        cols = 1
        while cols * cols < frame_count:
            cols += 1
        rows = (frame_count + cols - 1) // cols
    elif cols is None:
        assert rows is not None
        cols = (frame_count + rows - 1) // rows
    elif rows is None:
        rows = (frame_count + cols - 1) // cols
    return cols, rows


def _safe_name(value: str) -> str:
    cleaned = SAFE_NAME.sub("_", value.strip())
    return cleaned.strip("._") or "asset"


def _parse_hex_color(value: str) -> tuple[int, int, int]:
    text = value.strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) != 6:
        raise ValueError(f"invalid hex color '{value}'")
    try:
        return tuple(int(text[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as err:
        raise ValueError(f"invalid hex color '{value}'") from err


def _cell_bounds(
    width: int, height: int, cols: int, rows: int, col: int, row: int
) -> tuple[int, int, int, int]:
    x0 = col * width // cols
    x1 = (col + 1) * width // cols
    y0 = row * height // rows
    y1 = (row + 1) * height // rows
    return x0, y0, x1, y1


def _crop_rgba(image: RgbaImage, bounds: tuple[int, int, int, int]) -> RgbaImage:
    x0, y0, x1, y1 = bounds
    pixels: list[int] = []
    for y in range(y0, y1):
        start = (y * image.width + x0) * 4
        end = (y * image.width + x1) * 4
        pixels.extend(image.pixels[start:end])
    return RgbaImage(width=x1 - x0, height=y1 - y0, pixels=tuple(pixels))


def _apply_chroma_key(
    pixels: Iterable[int],
    *,
    chroma: tuple[int, int, int],
    threshold: int,
    green_floor: int,
    green_dominance: int,
) -> tuple[int, ...]:
    keyed = list(pixels)
    r_key, g_key, b_key = chroma
    threshold_sq = threshold * threshold
    for index in range(0, len(keyed), 4):
        red, green, blue, alpha = keyed[index : index + 4]
        dist_sq = (
            (red - r_key) * (red - r_key)
            + (green - g_key) * (green - g_key)
            + (blue - b_key) * (blue - b_key)
        )
        green_screen = (
            green >= green_floor
            and green - red >= green_dominance
            and green - blue >= green_dominance
        )
        if alpha and (dist_sq <= threshold_sq or green_screen):
            keyed[index + 3] = 0
    return tuple(keyed)


def _visible_bbox(
    width: int, height: int, pixels: tuple[int, ...]
) -> tuple[int, int, int, int] | None:
    min_x = width
    min_y = height
    max_x = -1
    max_y = -1
    for y in range(height):
        row = y * width * 4
        for x in range(width):
            if pixels[row + x * 4 + 3] == 0:
                continue
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
    if max_x < 0:
        return None
    return min_x, min_y, max_x + 1, max_y + 1


def _visible_pixel_count(pixels: tuple[int, ...]) -> int:
    return sum(1 for index in range(3, len(pixels), 4) if pixels[index] > 0)


def _read_png_rgba(path: Path) -> RgbaImage:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise PngError(f"{path}: not a PNG file")
    pos = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = None
    idat: list[bytes] = []
    while pos < len(data):
        if pos + 8 > len(data):
            raise PngError(f"{path}: truncated PNG chunk header")
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_start = pos + 8
        chunk_end = chunk_start + length
        crc_end = chunk_end + 4
        if crc_end > len(data):
            raise PngError(f"{path}: truncated PNG chunk {chunk_type!r}")
        chunk = data[chunk_start:chunk_end]
        expected_crc = struct.unpack(">I", data[chunk_end:crc_end])[0]
        actual_crc = binascii.crc32(chunk_type)
        actual_crc = binascii.crc32(chunk, actual_crc) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise PngError(f"{path}: CRC mismatch in PNG chunk {chunk_type!r}")
        pos = crc_end
        if chunk_type == b"IHDR":
            (
                width,
                height,
                bit_depth,
                color_type,
                compression,
                filter_method,
                interlace,
            ) = struct.unpack(">IIBBBBB", chunk)
            if compression != 0 or filter_method != 0 or interlace != 0:
                raise PngError(f"{path}: unsupported PNG compression/filter/interlace")
        elif chunk_type == b"IDAT":
            idat.append(chunk)
        elif chunk_type == b"IEND":
            break
    if width is None or height is None or bit_depth is None or color_type is None:
        raise PngError(f"{path}: missing IHDR")
    if bit_depth != 8 or color_type not in {0, 2, 6}:
        raise PngError(f"{path}: supports only 8-bit grayscale, RGB, or RGBA PNG")
    if not idat:
        raise PngError(f"{path}: missing IDAT")
    channels = {0: 1, 2: 3, 6: 4}[color_type]
    raw = zlib.decompress(b"".join(idat))
    stride = width * channels
    offset = 0
    previous = bytearray(stride)
    rows: list[bytearray] = []
    for _y in range(height):
        if offset + 1 + stride > len(raw):
            raise PngError(f"{path}: truncated decompressed pixel data")
        filter_type = raw[offset]
        offset += 1
        row = bytearray(raw[offset : offset + stride])
        offset += stride
        _unfilter_row(row, previous, channels, filter_type)
        rows.append(row)
        previous = row
    pixels: list[int] = []
    for row in rows:
        for index in range(0, len(row), channels):
            if color_type == 0:
                value = row[index]
                pixels.extend([value, value, value, 255])
            elif color_type == 2:
                pixels.extend([row[index], row[index + 1], row[index + 2], 255])
            else:
                pixels.extend(row[index : index + 4])
    return RgbaImage(width=width, height=height, pixels=tuple(pixels))


def _unfilter_row(
    row: bytearray, previous: bytearray, bytes_per_pixel: int, filter_type: int
) -> None:
    if filter_type == 0:
        return
    if filter_type == 1:
        for index in range(len(row)):
            left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            row[index] = (row[index] + left) & 0xFF
        return
    if filter_type == 2:
        for index in range(len(row)):
            row[index] = (row[index] + previous[index]) & 0xFF
        return
    if filter_type == 3:
        for index in range(len(row)):
            left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            up = previous[index]
            row[index] = (row[index] + ((left + up) // 2)) & 0xFF
        return
    if filter_type == 4:
        for index in range(len(row)):
            left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            up = previous[index]
            up_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            row[index] = (row[index] + _paeth(left, up, up_left)) & 0xFF
        return
    raise PngError(f"unsupported PNG filter type {filter_type}")


def _paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    dist_left = abs(estimate - left)
    dist_up = abs(estimate - up)
    dist_up_left = abs(estimate - up_left)
    if dist_left <= dist_up and dist_left <= dist_up_left:
        return left
    if dist_up <= dist_up_left:
        return up
    return up_left


def _write_png_rgba(path: Path, width: int, height: int, pixels: Iterable[int]) -> None:
    rgba = bytes(pixels)
    expected = width * height * 4
    if len(rgba) != expected:
        raise ValueError(f"RGBA pixel buffer has {len(rgba)} bytes, expected {expected}")
    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw.extend(rgba[y * stride : (y + 1) * stride])
    png = bytearray(PNG_SIGNATURE)
    png.extend(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)))
    png.extend(_png_chunk(b"IDAT", zlib.compress(bytes(raw), level=9)))
    png.extend(_png_chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(png))


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    crc = binascii.crc32(chunk_type)
    crc = binascii.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", crc)


if __name__ == "__main__":
    raise SystemExit(main())
