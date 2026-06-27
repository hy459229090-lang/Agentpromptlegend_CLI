"""Sprite atlas models for bitmap/cell terminal graphics assets."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

import yaml

from ouro_agent.content.assets import AssetFrame, AssetManifestReport
from ouro_agent.content.loader import ContentError


@dataclass(frozen=True)
class SpriteFrame:
    frame_id: str
    anchor: tuple[int, int]
    duration_ms: int
    fallback_cell_id: str
    bitmap_path: Path | None = None
    visual_source: str = "fallback_cell"
    frame_size: tuple[int, int] | None = None
    visible_bbox: tuple[int, int, int, int] | None = None
    visible_pixels: int = 0
    runtime_promoted: bool = False

    @property
    def has_bitmap(self) -> bool:
        return self.bitmap_path is not None


@dataclass(frozen=True)
class SpriteAsset:
    asset_id: str
    source_type: str
    source_content_id: str
    role: str
    frames: Mapping[str, SpriteFrame]
    runtime_enabled: bool = False
    qa_status: str = "planned"

    def frame(self, frame_id: str) -> SpriteFrame:
        frame = self.frames.get(frame_id)
        if frame is None:
            raise ContentError(f"{self.asset_id}: missing sprite frame '{frame_id}'")
        return frame

    @property
    def frame_ids(self) -> tuple[str, ...]:
        return tuple(self.frames)


@dataclass(frozen=True)
class ActorSprite(SpriteAsset):
    """Actor sprite asset for heroes and enemies."""


@dataclass(frozen=True)
class EffectSprite(SpriteAsset):
    """Effect sprite asset for skills, status pops, and HUD effects."""


@dataclass(frozen=True)
class CandidateCutFrame:
    frame_id: str
    path: Path
    anchor: tuple[int, int]
    duration_ms: int
    fallback_cell_id: str
    frame_size: tuple[int, int]
    visible_bbox: tuple[int, int, int, int]
    visible_pixels: int


@dataclass(frozen=True)
class CandidateCutMetadata:
    path: Path
    asset_id: str
    candidate_id: str
    work_order_id: str
    runtime_promoted: bool
    frames: tuple[CandidateCutFrame, ...]


@dataclass(frozen=True)
class SpriteAtlas:
    assets: Mapping[str, SpriteAsset]

    @classmethod
    def from_manifest_report(cls, report: AssetManifestReport) -> "SpriteAtlas":
        assets: dict[str, SpriteAsset] = {}
        runtime_cuts: list[CandidateCutMetadata] = []
        assets_root = report.manifest.path.parent
        for entry in report.manifest.assets:
            frame_templates = _frame_templates(entry.required_frames, entry.frames)
            frames = {
                frame.frame_id: SpriteFrame(
                    frame_id=frame.frame_id,
                    anchor=frame.anchor,
                    duration_ms=frame.duration_ms or 80,
                    fallback_cell_id=frame.fallback_cell_id,
                    runtime_promoted=entry.runtime_enabled,
                )
                for frame in frame_templates
            }
            asset_cls = _asset_class_for_role(entry.role)
            assets[entry.asset_id] = asset_cls(
                asset_id=entry.asset_id,
                source_type=entry.source_type,
                source_content_id=entry.source_content_id,
                role=entry.role,
                frames=frames,
                runtime_enabled=entry.runtime_enabled,
                qa_status=entry.qa_status,
            )
            if entry.runtime_enabled:
                cut = load_candidate_cut_metadata(assets_root / entry.path)
                if not cut.runtime_promoted:
                    raise ContentError(
                        f"{entry.asset_id}: runtime asset metadata must be promoted"
                    )
                runtime_cuts.append(cut)
        atlas = cls(assets=assets)
        if runtime_cuts:
            atlas = atlas.with_candidate_cuts(tuple(runtime_cuts))
        return atlas

    def sprite(self, asset_id: str) -> SpriteAsset:
        asset = self.assets.get(asset_id)
        if asset is None:
            raise ContentError(f"unknown sprite asset '{asset_id}'")
        return asset

    def with_candidate_cuts(
        self, cuts: tuple[CandidateCutMetadata, ...]
    ) -> "SpriteAtlas":
        assets = dict(self.assets)
        for cut in cuts:
            asset = assets.get(cut.asset_id)
            if asset is None:
                raise ContentError(
                    f"{cut.path}: cut metadata references unknown asset_id "
                    f"'{cut.asset_id}'"
                )
            frames = dict(asset.frames)
            for cut_frame in cut.frames:
                existing = frames.get(cut_frame.frame_id)
                if existing is None:
                    raise ContentError(
                        f"{cut.path}: cut frame '{cut_frame.frame_id}' is not "
                        f"declared by asset '{cut.asset_id}'"
                    )
                frames[cut_frame.frame_id] = replace(
                    existing,
                    bitmap_path=cut_frame.path,
                    visual_source=(
                        "runtime_cut" if cut.runtime_promoted else "candidate_cut"
                    ),
                    frame_size=cut_frame.frame_size,
                    visible_bbox=cut_frame.visible_bbox,
                    visible_pixels=cut_frame.visible_pixels,
                    runtime_promoted=cut.runtime_promoted,
                )
            assets[cut.asset_id] = replace(asset, frames=frames)
        return SpriteAtlas(assets=assets)

    @property
    def total_assets(self) -> int:
        return len(self.assets)

    @property
    def bitmap_frame_count(self) -> int:
        return sum(
            1
            for asset in self.assets.values()
            for frame in asset.frames.values()
            if frame.has_bitmap
        )


def load_candidate_cut_metadata(path: Path) -> CandidateCutMetadata:
    raw = _read_yaml_mapping(path)
    runtime_promoted = raw.get("runtime_promoted")
    if not isinstance(runtime_promoted, bool):
        raise ContentError(f"{path}: runtime_promoted must be bool")
    frames_raw = raw.get("frames")
    if not isinstance(frames_raw, list) or not frames_raw:
        raise ContentError(f"{path}: frames must be a non-empty list")
    frames = tuple(
        _cut_frame_from_mapping(
            frame,
            f"{path}#frames[{index}]",
            base_dir=path.parent,
        )
        for index, frame in enumerate(frames_raw)
    )
    return CandidateCutMetadata(
        path=path,
        asset_id=_required_str(raw, "asset_id", str(path)),
        candidate_id=_required_str(raw, "candidate_id", str(path)),
        work_order_id=_required_str(raw, "work_order_id", str(path)),
        runtime_promoted=runtime_promoted,
        frames=frames,
    )


def _frame_templates(
    required_frames: tuple[str, ...], frames: tuple[AssetFrame, ...]
) -> tuple[AssetFrame, ...]:
    existing = {frame.frame_id: frame for frame in frames}
    fallback = frames[0]
    templates: list[AssetFrame] = []
    for frame_id in required_frames:
        frame = existing.get(frame_id)
        if frame is not None:
            templates.append(frame)
            continue
        templates.append(
            AssetFrame(
                frame_id=frame_id,
                anchor=fallback.anchor,
                duration_ms=fallback.duration_ms or 80,
                fallback_cell_id=_fallback_cell_id_for_frame(
                    fallback.fallback_cell_id, frame_id
                ),
            )
        )
    return tuple(templates)


def _fallback_cell_id_for_frame(seed: str, frame_id: str) -> str:
    if seed.endswith(".planned"):
        return f"{seed.removesuffix('.planned')}.{frame_id}"
    return f"{seed}.{frame_id}"


def _asset_class_for_role(role: str) -> type[SpriteAsset]:
    if "actor" in role or "boss" in role:
        return ActorSprite
    if "effect" in role or "status" in role or "hud" in role:
        return EffectSprite
    return SpriteAsset


def _cut_frame_from_mapping(
    raw: object, where: str, *, base_dir: Path
) -> CandidateCutFrame:
    if not isinstance(raw, Mapping):
        raise ContentError(f"{where}: frame must be a mapping")
    path = Path(_required_str(raw, "path", where))
    if not path.is_absolute():
        path = base_dir / path
    if not path.is_file():
        raise ContentError(f"{where}.path: frame PNG is missing: {path}")
    return CandidateCutFrame(
        frame_id=_required_str(raw, "frame_id", where),
        path=path,
        anchor=_pair(raw.get("anchor"), f"{where}.anchor"),
        duration_ms=_non_negative_int(raw.get("duration_ms"), f"{where}.duration_ms"),
        fallback_cell_id=_required_str(raw, "fallback_cell_id", where),
        frame_size=_pair(raw.get("frame_size"), f"{where}.frame_size"),
        visible_bbox=_quad(raw.get("visible_bbox"), f"{where}.visible_bbox"),
        visible_pixels=_non_negative_int(
            raw.get("visible_pixels"), f"{where}.visible_pixels"
        ),
    )


def _read_yaml_mapping(path: Path) -> Mapping[str, object]:
    with path.open("r", encoding="utf-8") as fp:
        try:
            raw = yaml.safe_load(fp)
        except yaml.YAMLError as err:
            raise ContentError(f"yaml parse error in {path}: {err}") from err
    if not isinstance(raw, Mapping):
        raise ContentError(f"{path}: top level must be a mapping")
    return raw


def _required_str(raw: Mapping[str, object], key: str, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContentError(f"{where}.{key}: must be a non-empty string")
    return value.strip()


def _pair(value: object, where: str) -> tuple[int, int]:
    if not (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, int) and item >= 0 for item in value)
    ):
        raise ContentError(f"{where}: must be two non-negative ints")
    return int(value[0]), int(value[1])


def _quad(value: object, where: str) -> tuple[int, int, int, int]:
    if not (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(item, int) and item >= 0 for item in value)
    ):
        raise ContentError(f"{where}: must be four non-negative ints")
    return int(value[0]), int(value[1]), int(value[2]), int(value[3])


def _non_negative_int(value: object, where: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise ContentError(f"{where}: must be a non-negative int")
    return int(value)
