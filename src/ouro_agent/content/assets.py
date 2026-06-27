"""Asset manifest loading and coverage validation for terminal graphics."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Any

import yaml

from ouro_agent.content.loader import ContentError
from ouro_agent.content.schema import ContentBundle, VALID_STATUS_IDS


VALID_ASSET_STATUSES = {
    "planned",
    "generated",
    "qa_passed",
    "integrated",
    "fallback_ready",
    "evidence_done",
}

VALID_ASSET_SOURCE_TYPES = {
    "hero",
    "enemy",
    "skill",
    "item",
    "affix",
    "resonance",
    "dungeon",
    "node_type",
    "ui_state",
}

VALID_QA_RECORD_STATUSES = {"generated", "rejected", "qa_passed"}

REQUIRED_UI_STATES = frozenset(
    {
        "hp_bar",
        "mp_bar",
        "atb_bar",
        "damage_pop",
        "codex_reveal",
        "reward_card",
        *VALID_STATUS_IDS,
    }
)


@dataclass(frozen=True)
class AssetFrame:
    frame_id: str
    anchor: tuple[int, int]
    duration_ms: int
    fallback_cell_id: str


@dataclass(frozen=True)
class AssetEntry:
    asset_id: str
    source_type: str
    source_content_id: str
    role: str
    qa_status: str
    runtime_enabled: bool
    source_brief: str
    path: str
    required_frames: tuple[str, ...]
    frames: tuple[AssetFrame, ...]


@dataclass(frozen=True)
class AssetManifest:
    path: Path
    schema_version: str
    content_version: str
    runtime_policy: Mapping[str, object]
    statuses: tuple[str, ...]
    assets: tuple[AssetEntry, ...]


@dataclass(frozen=True)
class SourceBriefFamily:
    id: str
    source_types: tuple[str, ...]
    output: str
    prompt: str
    negative_prompt: str
    terminal_target: str
    qa_checks: tuple[str, ...]


@dataclass(frozen=True)
class SourceBriefAlias:
    id: str
    family: str
    source_type: str
    source_content_id: str


@dataclass(frozen=True)
class AssetBriefCatalog:
    paths: tuple[Path, ...]
    families: Mapping[str, SourceBriefFamily]
    aliases: Mapping[str, SourceBriefAlias]


@dataclass(frozen=True)
class AssetManifestReport:
    manifest: AssetManifest
    brief_catalog: AssetBriefCatalog
    missing_by_type: Mapping[str, tuple[str, ...]]
    unexpected_by_type: Mapping[str, tuple[str, ...]]
    missing_briefs: tuple[str, ...]
    brief_mismatches: tuple[str, ...]
    counts_by_type: Mapping[str, int]

    @property
    def ok(self) -> bool:
        return (
            not any(self.missing_by_type.values())
            and not any(self.unexpected_by_type.values())
            and not self.missing_briefs
            and not self.brief_mismatches
        )

    @property
    def total_assets(self) -> int:
        return len(self.manifest.assets)


@dataclass(frozen=True)
class AssetWorkOrder:
    work_order_id: str
    asset_id: str
    source_brief: str
    family: str
    source_type: str
    source_content_id: str
    role: str
    output: str
    prompt: str
    negative_prompt: str
    terminal_target: str
    qa_checks: tuple[str, ...]
    required_frames: tuple[str, ...]
    fallback_cell_ids: tuple[str, ...]
    runtime_policy: str = "development_only"
    candidate_storage: str = "scratch_only_until_qa"

    def to_dict(self) -> dict[str, Any]:
        return {
            "work_order_id": self.work_order_id,
            "asset_id": self.asset_id,
            "source_brief": self.source_brief,
            "family": self.family,
            "source_type": self.source_type,
            "source_content_id": self.source_content_id,
            "role": self.role,
            "output": self.output,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "terminal_target": self.terminal_target,
            "qa_checks": list(self.qa_checks),
            "required_frames": list(self.required_frames),
            "fallback_cell_ids": list(self.fallback_cell_ids),
            "runtime_policy": self.runtime_policy,
            "candidate_storage": self.candidate_storage,
        }


@dataclass(frozen=True)
class AssetQARecord:
    asset_id: str
    candidate_id: str
    work_order_id: str
    source_brief: str
    qa_status: str
    candidate_ref: str
    reviewer: str
    reviewed_at: str
    checks: Mapping[str, bool]
    frame_metadata: tuple[AssetFrame, ...]
    runtime_target_path: str = ""


@dataclass(frozen=True)
class AssetQAReport:
    paths: tuple[Path, ...]
    records: tuple[AssetQARecord, ...]
    counts_by_status: Mapping[str, int]

    @property
    def total_records(self) -> int:
        return len(self.records)


@dataclass(frozen=True)
class AssetPipelineReport:
    total_assets: int
    qa_report: AssetQAReport
    cut_metadata_paths: tuple[Path, ...]
    counts_by_type: Mapping[str, Mapping[str, int]]
    candidate_asset_ids: tuple[str, ...]
    cut_metadata_asset_ids: tuple[str, ...]
    qa_passed_asset_ids: tuple[str, ...]
    runtime_asset_ids: tuple[str, ...]
    missing_candidate_asset_ids: tuple[str, ...]
    missing_cut_metadata_asset_ids: tuple[str, ...]
    missing_qa_passed_asset_ids: tuple[str, ...]
    missing_runtime_asset_ids: tuple[str, ...]


@dataclass(frozen=True)
class AssetQATemplate:
    asset_id: str
    candidate_id: str
    work_order_id: str
    source_brief: str
    qa_status: str
    candidate_ref: str
    checks: Mapping[str, bool]
    frame_metadata: tuple[AssetFrame, ...]

    def to_record_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "candidate_id": self.candidate_id,
            "work_order_id": self.work_order_id,
            "source_brief": self.source_brief,
            "qa_status": self.qa_status,
            "candidate_ref": self.candidate_ref,
            "reviewer": "",
            "reviewed_at": "",
            "runtime_target_path": "",
            "checks": dict(self.checks),
            "frame_metadata": [
                {
                    "frame_id": frame.frame_id,
                    "anchor": list(frame.anchor),
                    "duration_ms": frame.duration_ms,
                    "fallback_cell_id": frame.fallback_cell_id,
                }
                for frame in self.frame_metadata
            ],
        }


def load_asset_manifest(content_root: Path) -> AssetManifest:
    """Load and validate ``content/assets/manifest.yaml``."""
    manifest_path = content_root / "assets" / "manifest.yaml"
    if not manifest_path.exists():
        raise ContentError(f"missing asset manifest: {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as fp:
        try:
            raw = yaml.safe_load(fp)
        except yaml.YAMLError as err:
            raise ContentError(f"yaml parse error in {manifest_path}: {err}") from err

    if not isinstance(raw, Mapping):
        raise ContentError(f"{manifest_path}: top level must be a mapping")

    schema_version = _required_str(raw, "schema_version", str(manifest_path))
    content_version = _required_str(raw, "content_version", str(manifest_path))
    runtime_policy = raw.get("runtime_policy", {})
    if not isinstance(runtime_policy, Mapping):
        raise ContentError(f"{manifest_path}: runtime_policy must be a mapping")
    _validate_runtime_policy(runtime_policy, manifest_path)

    statuses_raw = raw.get("statuses", [])
    if not isinstance(statuses_raw, list) or not statuses_raw:
        raise ContentError(f"{manifest_path}: statuses must be a non-empty list")
    statuses = tuple(str(item) for item in statuses_raw)
    unknown_statuses = sorted(set(statuses) - VALID_ASSET_STATUSES)
    if unknown_statuses:
        raise ContentError(
            f"{manifest_path}: unsupported asset statuses {unknown_statuses}"
        )

    assets_raw = raw.get("assets", [])
    if not isinstance(assets_raw, list) or not assets_raw:
        raise ContentError(f"{manifest_path}: assets must be a non-empty list")

    assets_root = (content_root / "assets").resolve()
    seen: set[str] = set()
    assets: list[AssetEntry] = []
    for index, item in enumerate(assets_raw):
        where = f"{manifest_path}#assets[{index}]"
        if not isinstance(item, Mapping):
            raise ContentError(f"{where}: asset entry must be a mapping")
        entry = _asset_entry_from_mapping(item, where, assets_root)
        if entry.asset_id in seen:
            raise ContentError(f"{where}: duplicate asset_id '{entry.asset_id}'")
        seen.add(entry.asset_id)
        assets.append(entry)

    return AssetManifest(
        path=manifest_path,
        schema_version=schema_version,
        content_version=content_version,
        runtime_policy=runtime_policy,
        statuses=statuses,
        assets=tuple(assets),
    )


def load_asset_brief_catalog(content_root: Path) -> AssetBriefCatalog:
    """Load development-time ImageGen source brief families and aliases."""
    briefs_dir = content_root / "assets" / "source_briefs"
    if not briefs_dir.exists():
        raise ContentError(f"missing asset source brief directory: {briefs_dir}")
    paths = tuple(sorted(briefs_dir.glob("*.yaml"))) + tuple(
        sorted(briefs_dir.glob("*.yml"))
    )
    if not paths:
        raise ContentError(f"missing asset source brief yaml files: {briefs_dir}")

    families: dict[str, SourceBriefFamily] = {}
    aliases: dict[str, SourceBriefAlias] = {}
    pending_aliases: list[tuple[SourceBriefAlias, str]] = []

    for path in paths:
        raw = _read_yaml_mapping(path)
        families_raw = raw.get("brief_families", []) or []
        if not isinstance(families_raw, list):
            raise ContentError(f"{path}: brief_families must be a list")
        for index, item in enumerate(families_raw):
            where = f"{path}#brief_families[{index}]"
            family = _brief_family_from_mapping(item, where)
            if family.id in families:
                raise ContentError(f"{where}: duplicate brief family '{family.id}'")
            families[family.id] = family

        aliases_raw = raw.get("brief_aliases", []) or []
        if not isinstance(aliases_raw, list):
            raise ContentError(f"{path}: brief_aliases must be a list")
        for index, item in enumerate(aliases_raw):
            where = f"{path}#brief_aliases[{index}]"
            alias = _brief_alias_from_mapping(item, where)
            if alias.id in aliases:
                raise ContentError(f"{where}: duplicate brief alias '{alias.id}'")
            aliases[alias.id] = alias
            pending_aliases.append((alias, where))

    if not families:
        raise ContentError(f"{briefs_dir}: no brief families loaded")
    if not aliases:
        raise ContentError(f"{briefs_dir}: no brief aliases loaded")

    for alias, where in pending_aliases:
        family = families.get(alias.family)
        if family is None:
            raise ContentError(
                f"{where}: brief alias references unknown family '{alias.family}'"
            )
        if alias.source_type not in family.source_types:
            raise ContentError(
                f"{where}: source_type '{alias.source_type}' is not allowed by "
                f"brief family '{alias.family}'"
            )

    return AssetBriefCatalog(
        paths=paths,
        families=families,
        aliases=aliases,
    )


def validate_asset_manifest(
    content_root: Path, bundle: ContentBundle
) -> AssetManifestReport:
    """Return full-MVP asset coverage results for the current content bundle."""
    manifest = load_asset_manifest(content_root)
    brief_catalog = load_asset_brief_catalog(content_root)
    expected = _expected_content_ids(bundle)

    seen_by_type: dict[str, set[str]] = defaultdict(set)
    missing_briefs: list[str] = []
    brief_mismatches: list[str] = []
    for asset in manifest.assets:
        seen_by_type[asset.source_type].add(asset.source_content_id)
        alias = brief_catalog.aliases.get(asset.source_brief)
        if alias is None:
            missing_briefs.append(asset.source_brief)
            continue
        if (
            alias.source_type != asset.source_type
            or alias.source_content_id != asset.source_content_id
        ):
            brief_mismatches.append(
                f"{asset.asset_id}: {asset.source_brief} maps to "
                f"{alias.source_type}:{alias.source_content_id}"
            )

    missing_by_type: dict[str, tuple[str, ...]] = {}
    unexpected_by_type: dict[str, tuple[str, ...]] = {}
    for source_type in sorted(expected):
        expected_ids = expected[source_type]
        seen_ids = seen_by_type.get(source_type, set())
        missing_by_type[source_type] = tuple(sorted(expected_ids - seen_ids))
        unexpected_by_type[source_type] = tuple(sorted(seen_ids - expected_ids))

    counts = Counter(asset.source_type for asset in manifest.assets)
    return AssetManifestReport(
        manifest=manifest,
        brief_catalog=brief_catalog,
        missing_by_type=missing_by_type,
        unexpected_by_type=unexpected_by_type,
        missing_briefs=tuple(sorted(set(missing_briefs))),
        brief_mismatches=tuple(sorted(brief_mismatches)),
        counts_by_type=dict(sorted(counts.items())),
    )


def iter_missing_asset_coverage(report: AssetManifestReport) -> Iterable[str]:
    for source_type, missing in report.missing_by_type.items():
        for content_id in missing:
            yield f"{source_type}:{content_id}"
    for source_type, unexpected in report.unexpected_by_type.items():
        for content_id in unexpected:
            yield f"unexpected {source_type}:{content_id}"
    for brief_id in report.missing_briefs:
        yield f"missing source_brief:{brief_id}"
    for mismatch in report.brief_mismatches:
        yield f"brief mismatch {mismatch}"


def build_asset_work_orders(report: AssetManifestReport) -> tuple[AssetWorkOrder, ...]:
    """Build deterministic ImageGen work orders for every manifest asset."""
    if not report.ok:
        missing = ", ".join(iter_missing_asset_coverage(report))
        raise ContentError(f"cannot build asset work orders while manifest has gaps: {missing}")

    work_orders: list[AssetWorkOrder] = []
    for asset in report.manifest.assets:
        alias = report.brief_catalog.aliases[asset.source_brief]
        family = report.brief_catalog.families[alias.family]
        prompt = (
            f"{family.prompt} Asset source: {asset.source_type}:{asset.source_content_id}. "
            f"Asset role: {asset.role}. Source brief: {asset.source_brief}. "
            f"Required frames: {', '.join(asset.required_frames)}. "
            "Keep transparent background where applicable, stable anchor, no text UI."
        )
        fallback_ids = tuple(frame.fallback_cell_id for frame in asset.frames)
        work_orders.append(
            AssetWorkOrder(
                work_order_id=f"wo_{asset.asset_id}",
                asset_id=asset.asset_id,
                source_brief=asset.source_brief,
                family=family.id,
                source_type=asset.source_type,
                source_content_id=asset.source_content_id,
                role=asset.role,
                output=family.output,
                prompt=prompt,
                negative_prompt=family.negative_prompt,
                terminal_target=family.terminal_target,
                qa_checks=family.qa_checks,
                required_frames=asset.required_frames,
                fallback_cell_ids=fallback_ids,
            )
        )
    return tuple(work_orders)


def validate_asset_qa_records(
    content_root: Path,
    manifest_report: AssetManifestReport,
    records_dir: Path | None = None,
) -> AssetQAReport:
    """Validate candidate QA records without promoting unreviewed assets."""
    qa_dir = records_dir if records_dir is not None else content_root / "assets" / "qa"
    if not qa_dir.exists():
        return AssetQAReport(paths=(), records=(), counts_by_status={})

    paths = tuple(sorted(qa_dir.glob("*.yaml"))) + tuple(sorted(qa_dir.glob("*.yml")))
    paths = tuple(path for path in paths if not path.name.startswith("_"))
    if not paths:
        return AssetQAReport(paths=(), records=(), counts_by_status={})

    assets_by_id = {asset.asset_id: asset for asset in manifest_report.manifest.assets}
    work_orders_by_id = {
        order.work_order_id: order for order in build_asset_work_orders(manifest_report)
    }
    records: list[AssetQARecord] = []
    seen_candidates: set[str] = set()
    for path in paths:
        raw = _read_yaml_mapping(path)
        records_raw = raw.get("records", []) or []
        if not isinstance(records_raw, list):
            raise ContentError(f"{path}: records must be a list")
        for index, item in enumerate(records_raw):
            where = f"{path}#records[{index}]"
            record = _qa_record_from_mapping(
                item,
                where,
                assets_by_id,
                work_orders_by_id,
                (content_root / "assets").resolve(),
            )
            if record.candidate_id in seen_candidates:
                raise ContentError(
                    f"{where}: duplicate candidate_id '{record.candidate_id}'"
                )
            seen_candidates.add(record.candidate_id)
            records.append(record)

    counts = Counter(record.qa_status for record in records)
    return AssetQAReport(
        paths=paths,
        records=tuple(records),
        counts_by_status=dict(sorted(counts.items())),
    )


def build_asset_pipeline_report(
    manifest_report: AssetManifestReport,
    qa_report: AssetQAReport,
    *,
    cut_metadata_dir: Path | None = None,
) -> AssetPipelineReport:
    """Summarize candidate/QA/cut/runtime readiness for every manifest asset."""
    asset_ids = {asset.asset_id for asset in manifest_report.manifest.assets}
    candidate_asset_ids = {record.asset_id for record in qa_report.records}
    qa_passed_asset_ids = {
        record.asset_id for record in qa_report.records if record.qa_status == "qa_passed"
    }
    runtime_asset_ids = {
        asset.asset_id
        for asset in manifest_report.manifest.assets
        if asset.runtime_enabled
    }
    cut_metadata_paths, cut_metadata_asset_ids = _load_cut_metadata_assets(
        cut_metadata_dir
    )
    unknown_cut_assets = sorted(cut_metadata_asset_ids - asset_ids)
    if unknown_cut_assets:
        raise ContentError(
            "cut metadata references unknown assets: "
            + ", ".join(unknown_cut_assets)
        )

    counts_by_type: dict[str, dict[str, int]] = {}
    for source_type in sorted(manifest_report.counts_by_type):
        typed_assets = {
            asset.asset_id
            for asset in manifest_report.manifest.assets
            if asset.source_type == source_type
        }
        counts_by_type[source_type] = {
            "total": len(typed_assets),
            "candidates": len(typed_assets & candidate_asset_ids),
            "cut_metadata": len(typed_assets & cut_metadata_asset_ids),
            "qa_passed": len(typed_assets & qa_passed_asset_ids),
            "runtime_enabled": len(typed_assets & runtime_asset_ids),
        }

    return AssetPipelineReport(
        total_assets=len(asset_ids),
        qa_report=qa_report,
        cut_metadata_paths=cut_metadata_paths,
        counts_by_type=counts_by_type,
        candidate_asset_ids=tuple(sorted(candidate_asset_ids)),
        cut_metadata_asset_ids=tuple(sorted(cut_metadata_asset_ids)),
        qa_passed_asset_ids=tuple(sorted(qa_passed_asset_ids)),
        runtime_asset_ids=tuple(sorted(runtime_asset_ids)),
        missing_candidate_asset_ids=tuple(sorted(asset_ids - candidate_asset_ids)),
        missing_cut_metadata_asset_ids=tuple(sorted(asset_ids - cut_metadata_asset_ids)),
        missing_qa_passed_asset_ids=tuple(sorted(asset_ids - qa_passed_asset_ids)),
        missing_runtime_asset_ids=tuple(sorted(asset_ids - runtime_asset_ids)),
    )


def iter_asset_pipeline_gaps(
    report: AssetPipelineReport,
    *,
    require_all_candidates: bool = False,
    require_all_cut_metadata: bool = False,
    require_all_qa_passed: bool = False,
    require_all_runtime: bool = False,
) -> Iterable[str]:
    if require_all_candidates:
        for asset_id in report.missing_candidate_asset_ids:
            yield f"missing candidate: {asset_id}"
    if require_all_cut_metadata:
        for asset_id in report.missing_cut_metadata_asset_ids:
            yield f"missing cut metadata: {asset_id}"
    if require_all_qa_passed:
        for asset_id in report.missing_qa_passed_asset_ids:
            yield f"missing qa_passed: {asset_id}"
    if require_all_runtime:
        for asset_id in report.missing_runtime_asset_ids:
            yield f"missing runtime asset: {asset_id}"


def build_asset_qa_template(
    manifest_report: AssetManifestReport,
    *,
    work_order_id: str,
    candidate_id: str,
    candidate_ref: str,
    qa_status: str = "generated",
) -> AssetQATemplate:
    """Build a QA record template with frame metadata for one candidate."""
    if qa_status not in VALID_QA_RECORD_STATUSES:
        raise ContentError(f"unsupported qa_status '{qa_status}'")
    work_orders = {
        order.work_order_id: order for order in build_asset_work_orders(manifest_report)
    }
    work_order = work_orders.get(work_order_id)
    if work_order is None:
        raise ContentError(f"unknown work_order_id '{work_order_id}'")
    assets = {asset.asset_id: asset for asset in manifest_report.manifest.assets}
    asset = assets[work_order.asset_id]
    frame_metadata = _frame_metadata_template(asset)
    return AssetQATemplate(
        asset_id=asset.asset_id,
        candidate_id=candidate_id,
        work_order_id=work_order_id,
        source_brief=asset.source_brief,
        qa_status=qa_status,
        candidate_ref=candidate_ref,
        checks={check: False for check in work_order.qa_checks},
        frame_metadata=frame_metadata,
    )


def _expected_content_ids(bundle: ContentBundle) -> dict[str, set[str]]:
    node_types = {node.node_type for node in bundle.nodes.values()}
    return {
        "hero": set(bundle.heroes),
        "enemy": set(bundle.enemies),
        "skill": set(bundle.skills),
        "item": set(bundle.items),
        "affix": set(bundle.affixes),
        "resonance": set(bundle.resonances),
        "dungeon": set(bundle.dungeons),
        "node_type": node_types,
        "ui_state": set(REQUIRED_UI_STATES),
    }


def _frame_metadata_template(asset: AssetEntry) -> tuple[AssetFrame, ...]:
    existing_by_id = {frame.frame_id: frame for frame in asset.frames}
    fallback = asset.frames[0]
    frames: list[AssetFrame] = []
    for frame_id in asset.required_frames:
        existing = existing_by_id.get(frame_id)
        if existing is not None:
            frames.append(existing)
            continue
        frames.append(
            AssetFrame(
                frame_id=frame_id,
                anchor=fallback.anchor,
                duration_ms=fallback.duration_ms or 80,
                fallback_cell_id=_fallback_cell_id_for_frame(
                    fallback.fallback_cell_id, frame_id
                ),
            )
        )
    return tuple(frames)


def _fallback_cell_id_for_frame(seed: str, frame_id: str) -> str:
    if seed.endswith(".planned"):
        return f"{seed.removesuffix('.planned')}.{frame_id}"
    return f"{seed}.{frame_id}"


def _asset_entry_from_mapping(
    raw: Mapping[str, object], where: str, assets_root: Path
) -> AssetEntry:
    asset_id = _required_str(raw, "asset_id", where)
    source_type = _required_str(raw, "source_type", where)
    if source_type not in VALID_ASSET_SOURCE_TYPES:
        raise ContentError(f"{where}: unsupported source_type '{source_type}'")
    source_content_id = _required_str(raw, "source_content_id", where)
    role = _required_str(raw, "role", where)
    qa_status = _required_str(raw, "qa_status", where)
    if qa_status not in VALID_ASSET_STATUSES:
        raise ContentError(f"{where}: unsupported qa_status '{qa_status}'")
    runtime_enabled = raw.get("runtime_enabled")
    if not isinstance(runtime_enabled, bool):
        raise ContentError(f"{where}: runtime_enabled must be bool")
    source_brief = _required_str(raw, "source_brief", where)
    asset_path = str(raw.get("path", "") or "")

    required_frames_raw = raw.get("required_frames")
    if not isinstance(required_frames_raw, list) or not required_frames_raw:
        raise ContentError(f"{where}: required_frames must be a non-empty list")
    required_frames = tuple(_non_empty_string(item, f"{where}.required_frames") for item in required_frames_raw)

    frames_raw = raw.get("frames")
    if not isinstance(frames_raw, list) or not frames_raw:
        raise ContentError(f"{where}: frames must be a non-empty list")
    frames = tuple(
        _asset_frame_from_mapping(frame, f"{where}.frames[{idx}]")
        for idx, frame in enumerate(frames_raw)
    )

    if runtime_enabled:
        if qa_status != "qa_passed":
            raise ContentError(
                f"{where}: runtime_enabled asset must have qa_status 'qa_passed'"
            )
        if not asset_path:
            raise ContentError(f"{where}: runtime_enabled asset requires path")
        path = Path(asset_path)
        if path.is_absolute():
            raise ContentError(f"{where}: asset path must be relative to content/assets")
        resolved = (assets_root / path).resolve()
        if not resolved.is_relative_to(assets_root):
            raise ContentError(f"{where}: asset path escapes content/assets")
        if not resolved.is_file():
            raise ContentError(f"{where}: runtime asset file is missing: {asset_path}")

    return AssetEntry(
        asset_id=asset_id,
        source_type=source_type,
        source_content_id=source_content_id,
        role=role,
        qa_status=qa_status,
        runtime_enabled=runtime_enabled,
        source_brief=source_brief,
        path=asset_path,
        required_frames=required_frames,
        frames=frames,
    )


def _asset_frame_from_mapping(raw: object, where: str) -> AssetFrame:
    if not isinstance(raw, Mapping):
        raise ContentError(f"{where}: frame entry must be a mapping")
    frame_id = _required_str(raw, "frame_id", where)
    anchor_raw = raw.get("anchor")
    if not (
        isinstance(anchor_raw, list)
        and len(anchor_raw) == 2
        and all(isinstance(value, int) and value >= 0 for value in anchor_raw)
    ):
        raise ContentError(f"{where}: anchor must be [x, y] non-negative ints")
    duration_raw = raw.get("duration_ms")
    if not isinstance(duration_raw, int) or duration_raw < 0:
        raise ContentError(f"{where}: duration_ms must be a non-negative int")
    fallback_cell_id = _required_str(raw, "fallback_cell_id", where)
    return AssetFrame(
        frame_id=frame_id,
        anchor=(int(anchor_raw[0]), int(anchor_raw[1])),
        duration_ms=int(duration_raw),
        fallback_cell_id=fallback_cell_id,
    )


def _brief_family_from_mapping(raw: object, where: str) -> SourceBriefFamily:
    if not isinstance(raw, Mapping):
        raise ContentError(f"{where}: brief family must be a mapping")
    family_id = _required_str(raw, "id", where)
    source_types_raw = raw.get("source_types")
    if not isinstance(source_types_raw, list) or not source_types_raw:
        raise ContentError(f"{where}: source_types must be a non-empty list")
    source_types = tuple(
        _non_empty_string(item, f"{where}.source_types") for item in source_types_raw
    )
    for source_type in source_types:
        if source_type not in VALID_ASSET_SOURCE_TYPES:
            raise ContentError(f"{where}: unsupported source_type '{source_type}'")
    qa_checks_raw = raw.get("qa_checks")
    if not isinstance(qa_checks_raw, list) or not qa_checks_raw:
        raise ContentError(f"{where}: qa_checks must be a non-empty list")
    return SourceBriefFamily(
        id=family_id,
        source_types=source_types,
        output=_required_str(raw, "output", where),
        prompt=_required_str(raw, "prompt", where),
        negative_prompt=_required_str(raw, "negative_prompt", where),
        terminal_target=_required_str(raw, "terminal_target", where),
        qa_checks=tuple(
            _non_empty_string(item, f"{where}.qa_checks") for item in qa_checks_raw
        ),
    )


def _brief_alias_from_mapping(raw: object, where: str) -> SourceBriefAlias:
    if not isinstance(raw, Mapping):
        raise ContentError(f"{where}: brief alias must be a mapping")
    source_type = _required_str(raw, "source_type", where)
    if source_type not in VALID_ASSET_SOURCE_TYPES:
        raise ContentError(f"{where}: unsupported source_type '{source_type}'")
    return SourceBriefAlias(
        id=_required_str(raw, "id", where),
        family=_required_str(raw, "family", where),
        source_type=source_type,
        source_content_id=_required_str(raw, "source_content_id", where),
    )


def _qa_record_from_mapping(
    raw: object,
    where: str,
    assets_by_id: Mapping[str, AssetEntry],
    work_orders_by_id: Mapping[str, AssetWorkOrder],
    assets_root: Path,
) -> AssetQARecord:
    if not isinstance(raw, Mapping):
        raise ContentError(f"{where}: QA record must be a mapping")
    asset_id = _required_str(raw, "asset_id", where)
    asset = assets_by_id.get(asset_id)
    if asset is None:
        raise ContentError(f"{where}: unknown asset_id '{asset_id}'")
    candidate_id = _required_str(raw, "candidate_id", where)
    work_order_id = _required_str(raw, "work_order_id", where)
    work_order = work_orders_by_id.get(work_order_id)
    if work_order is None:
        raise ContentError(f"{where}: unknown work_order_id '{work_order_id}'")
    if work_order.asset_id != asset_id:
        raise ContentError(
            f"{where}: work_order_id '{work_order_id}' belongs to '{work_order.asset_id}'"
        )
    source_brief = _required_str(raw, "source_brief", where)
    if source_brief != asset.source_brief:
        raise ContentError(
            f"{where}: source_brief '{source_brief}' does not match manifest"
        )
    qa_status = _required_str(raw, "qa_status", where)
    if qa_status not in VALID_QA_RECORD_STATUSES:
        raise ContentError(f"{where}: unsupported qa_status '{qa_status}'")
    candidate_ref = _required_str(raw, "candidate_ref", where)
    reviewer = str(raw.get("reviewer", "") or "").strip()
    reviewed_at = str(raw.get("reviewed_at", "") or "").strip()
    if qa_status in {"qa_passed", "rejected"} and (not reviewer or not reviewed_at):
        raise ContentError(f"{where}: reviewed QA records require reviewer/reviewed_at")

    checks_raw = raw.get("checks", {}) or {}
    if not isinstance(checks_raw, Mapping):
        raise ContentError(f"{where}: checks must be a mapping")
    checks = {str(key): bool(value) for key, value in checks_raw.items()}
    if qa_status == "qa_passed":
        missing_checks = sorted(set(work_order.qa_checks) - set(checks))
        failed_checks = sorted(key for key in work_order.qa_checks if checks.get(key) is not True)
        if missing_checks:
            raise ContentError(f"{where}: missing QA checks {missing_checks}")
        if failed_checks:
            raise ContentError(f"{where}: failed QA checks {failed_checks}")

    frames_raw = raw.get("frame_metadata", []) or []
    if not isinstance(frames_raw, list):
        raise ContentError(f"{where}: frame_metadata must be a list")
    frame_metadata = tuple(
        _asset_frame_from_mapping(frame, f"{where}.frame_metadata[{idx}]")
        for idx, frame in enumerate(frames_raw)
    )
    if qa_status == "qa_passed":
        frame_ids = {frame.frame_id for frame in frame_metadata}
        missing_frames = sorted(set(asset.required_frames) - frame_ids)
        if missing_frames:
            raise ContentError(f"{where}: missing frame_metadata {missing_frames}")

    runtime_target_path = str(raw.get("runtime_target_path", "") or "")
    if runtime_target_path:
        if qa_status != "qa_passed":
            raise ContentError(
                f"{where}: runtime_target_path requires qa_status 'qa_passed'"
            )
        target = Path(runtime_target_path)
        if target.is_absolute():
            raise ContentError(f"{where}: runtime_target_path must be relative")
        resolved = (assets_root / target).resolve()
        if not resolved.is_relative_to(assets_root):
            raise ContentError(f"{where}: runtime_target_path escapes content/assets")

    return AssetQARecord(
        asset_id=asset_id,
        candidate_id=candidate_id,
        work_order_id=work_order_id,
        source_brief=source_brief,
        qa_status=qa_status,
        candidate_ref=candidate_ref,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        checks=checks,
        frame_metadata=frame_metadata,
        runtime_target_path=runtime_target_path,
    )


def _validate_runtime_policy(policy: Mapping[str, object], path: Path) -> None:
    expected = {
        "image_generation": "development_only",
        "runtime_network": "disabled",
        "qa_required_for_runtime": True,
        "fallback_required": True,
    }
    for key, value in expected.items():
        if policy.get(key) != value:
            raise ContentError(f"{path}: runtime_policy.{key} must be {value!r}")


def _read_yaml_mapping(path: Path) -> Mapping[str, object]:
    with path.open("r", encoding="utf-8") as fp:
        try:
            raw = yaml.safe_load(fp)
        except yaml.YAMLError as err:
            raise ContentError(f"yaml parse error in {path}: {err}") from err
    if not isinstance(raw, Mapping):
        raise ContentError(f"{path}: top level must be a mapping")
    return raw


def _load_cut_metadata_assets(
    cut_metadata_dir: Path | None,
) -> tuple[tuple[Path, ...], set[str]]:
    if cut_metadata_dir is None or not cut_metadata_dir.exists():
        return (), set()
    paths = tuple(sorted(cut_metadata_dir.rglob("cut_metadata.yaml"))) + tuple(
        sorted(cut_metadata_dir.rglob("cut_metadata.yml"))
    )
    asset_ids: set[str] = set()
    for path in paths:
        raw = _read_yaml_mapping(path)
        asset_ids.add(_required_str(raw, "asset_id", str(path)))
    return paths, asset_ids


def _required_str(raw: Mapping[str, object], key: str, where: str) -> str:
    return _non_empty_string(raw.get(key), f"{where}.{key}")


def _non_empty_string(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContentError(f"{where}: must be a non-empty string")
    return value.strip()
