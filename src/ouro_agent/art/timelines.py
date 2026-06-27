"""Animation timeline models for terminal-native combat staging."""
from __future__ import annotations

from dataclasses import dataclass

from ouro_agent.art.sprite_atlas import SpriteAsset, SpriteAtlas
from ouro_agent.content.loader import ContentError


@dataclass(frozen=True)
class TimelineBeat:
    frame_id: str
    duration_ms: int
    hero_asset_id: str
    hero_frame: str
    enemy_asset_id: str
    enemy_frame: str
    effect_asset_id: str
    effect_frame: str
    effect_offset: tuple[int, int] = (0, 0)
    damage_pop: str = ""
    hud_delta: str = ""
    hit_stop: bool = False

    def differs_from(self, other: "TimelineBeat") -> bool:
        return any(
            (
                self.hero_frame != other.hero_frame,
                self.enemy_frame != other.enemy_frame,
                self.effect_frame != other.effect_frame,
                self.effect_offset != other.effect_offset,
                self.damage_pop != other.damage_pop,
                self.hud_delta != other.hud_delta,
                self.hit_stop != other.hit_stop,
            )
        )


@dataclass(frozen=True)
class AnimationTimeline:
    timeline_id: str
    beats: tuple[TimelineBeat, ...]

    @property
    def total_duration_ms(self) -> int:
        return sum(beat.duration_ms for beat in self.beats)

    def validate_against(self, atlas: SpriteAtlas) -> None:
        if not self.beats:
            raise ContentError(f"{self.timeline_id}: timeline has no beats")
        previous: TimelineBeat | None = None
        for beat in self.beats:
            atlas.sprite(beat.hero_asset_id).frame(beat.hero_frame)
            atlas.sprite(beat.enemy_asset_id).frame(beat.enemy_frame)
            atlas.sprite(beat.effect_asset_id).frame(beat.effect_frame)
            if beat.duration_ms <= 0:
                raise ContentError(
                    f"{self.timeline_id}.{beat.frame_id}: duration_ms must be positive"
                )
            if previous is not None and not beat.differs_from(previous):
                raise ContentError(
                    f"{self.timeline_id}.{beat.frame_id}: adjacent beat has no "
                    "pose/effect/damage/HUD delta"
                )
            previous = beat


@dataclass(frozen=True)
class SignatureTimelineSpec:
    skill_id: str
    beat_ids: tuple[str, ...]
    effect_frames: tuple[str, ...]
    hud_deltas: tuple[str, ...]
    effect_offsets: tuple[tuple[int, int], ...]
    status_tag: str
    hit_stop_index: int = 5
    status_pop_index: int = 6


SIGNATURE_SKILL_IDS: tuple[str, ...] = (
    "skill_hex_seal",
    "skill_tower_brace",
    "skill_pierce_string",
    "skill_omen_vial",
    "skill_burial_engine",
    "skill_silent_hymn",
)

_SIGNATURE_EFFECT_OFFSETS: tuple[tuple[int, int], ...] = (
    (0, 0),
    (6, 0),
    (14, 0),
    (26, 0),
    (40, 0),
    (56, 0),
    (60, -1),
    (52, 0),
    (42, 0),
    (30, 0),
    (16, 0),
    (0, 0),
)

_SIGNATURE_TIMELINE_SPECS: dict[str, SignatureTimelineSpec] = {
    "skill_tower_brace": SignatureTimelineSpec(
        skill_id="skill_tower_brace",
        beat_ids=(
            "idle",
            "plant",
            "tower_lock",
            "shield_bloom",
            "impact_absorb",
            "hit_stop",
            "counter_spark",
            "brace_settle",
            "ash_fall",
            "recover",
            "hold_line",
            "ready",
        ),
        effect_frames=(
            "idle",
            "brace",
            "shield_flare",
            "impact_stop",
            "counter_spark",
            "impact_stop",
            "counter_spark",
            "shield_flare",
            "settle",
            "brace",
            "settle",
            "idle",
        ),
        hud_deltas=(
            "tower_idle",
            "shield_planted",
            "tower_lock",
            "ash_bloom",
            "impact_absorb",
            "hit_stop_guard",
            "counter_ready",
            "shield_settle",
            "ash_fall",
            "recover",
            "hold_line",
            "complete",
        ),
        effect_offsets=_SIGNATURE_EFFECT_OFFSETS,
        status_tag="SHD",
    ),
    "skill_pierce_string": SignatureTimelineSpec(
        skill_id="skill_pierce_string",
        beat_ids=(
            "idle",
            "aim",
            "string_snap",
            "bolt_release",
            "bolt_travel",
            "hit_stop",
            "bleed_pop",
            "recoil",
            "thread_pull",
            "recover",
            "string_echo",
            "settle",
        ),
        effect_frames=(
            "aim",
            "string_snap",
            "bolt_travel",
            "string_snap",
            "bolt_travel",
            "impact",
            "bleed_pop",
            "recover",
            "bleed_pop",
            "recover",
            "string_snap",
            "recover",
        ),
        hud_deltas=(
            "prey_mark",
            "aim_lock",
            "string_snap",
            "bolt_release",
            "bolt_travel",
            "impact",
            "bleed_set",
            "recoil",
            "thread_pull",
            "recover",
            "string_echo",
            "complete",
        ),
        effect_offsets=_SIGNATURE_EFFECT_OFFSETS,
        status_tag="BLD",
    ),
    "skill_omen_vial": SignatureTimelineSpec(
        skill_id="skill_omen_vial",
        beat_ids=(
            "idle",
            "raise",
            "omen_read",
            "throw",
            "arc",
            "hit_stop",
            "shatter",
            "omen_cloud",
            "mute_settle",
            "glass_fall",
            "recover",
            "settle",
        ),
        effect_frames=(
            "raise",
            "throw",
            "arc",
            "throw",
            "arc",
            "shatter",
            "omen_cloud",
            "shatter",
            "omen_cloud",
            "settle",
            "raise",
            "settle",
        ),
        hud_deltas=(
            "omen_idle",
            "vial_raised",
            "omen_read",
            "throw",
            "vial_arc",
            "impact",
            "mute_applied",
            "cloud_spread",
            "mute_settle",
            "glass_fall",
            "recover",
            "complete",
        ),
        effect_offsets=_SIGNATURE_EFFECT_OFFSETS,
        status_tag="SLN",
    ),
    "skill_burial_engine": SignatureTimelineSpec(
        skill_id="skill_burial_engine",
        beat_ids=(
            "idle",
            "deploy",
            "crank",
            "ignite",
            "engine_travel",
            "hit_stop",
            "blast",
            "gear_rattle",
            "smoke_settle",
            "recover",
            "engine_sleep",
            "settle",
        ),
        effect_frames=(
            "deploy",
            "ignite",
            "deploy",
            "ignite",
            "travel",
            "impact",
            "blast",
            "impact",
            "blast",
            "recover",
            "deploy",
            "recover",
        ),
        hud_deltas=(
            "engine_idle",
            "deploy",
            "crank",
            "ignite",
            "travel",
            "impact",
            "blast",
            "gear_rattle",
            "smoke_settle",
            "recover",
            "engine_sleep",
            "complete",
        ),
        effect_offsets=_SIGNATURE_EFFECT_OFFSETS,
        status_tag="BLAST",
    ),
    "skill_silent_hymn": SignatureTimelineSpec(
        skill_id="skill_silent_hymn",
        beat_ids=(
            "idle",
            "inhale",
            "hymn_rise",
            "hymn_wave",
            "quiet_travel",
            "hit_stop",
            "silence_mark",
            "holy_pop",
            "echo_settle",
            "recover",
            "last_note",
            "settle",
        ),
        effect_frames=(
            "inhale",
            "hymn_wave",
            "travel",
            "hymn_wave",
            "travel",
            "silence_mark",
            "holy_pop",
            "silence_mark",
            "holy_pop",
            "recover",
            "hymn_wave",
            "recover",
        ),
        hud_deltas=(
            "breathless",
            "inhale",
            "hymn_rise",
            "hymn_wave",
            "quiet_travel",
            "impact",
            "silence_set",
            "holy_pop",
            "echo_settle",
            "recover",
            "last_note",
            "complete",
        ),
        effect_offsets=_SIGNATURE_EFFECT_OFFSETS,
        status_tag="SLN",
    ),
}


def signature_skill_ids() -> tuple[str, ...]:
    """Return skills that have authored 12-beat hero signature timelines."""
    return SIGNATURE_SKILL_IDS


def is_signature_skill(skill_id: str) -> bool:
    return skill_id in SIGNATURE_SKILL_IDS


def build_signature_skill_timeline(
    *,
    hero_asset: SpriteAsset,
    enemy_asset: SpriteAsset,
    effect_asset: SpriteAsset,
    skill_id: str,
    damage_pop: str,
    timeline_id: str,
) -> AnimationTimeline | None:
    """Return an authored 12-beat signature timeline when one exists.

    Signature timelines reuse the same QA-promoted bitmap/cell assets as the
    generic timeline, but they give each hero's signature skill its own action
    grammar instead of sharing one template.
    """
    if skill_id == "skill_hex_seal":
        return build_hex_seal_smoke_timeline(
            hero_asset_id=hero_asset.asset_id,
            enemy_asset_id=enemy_asset.asset_id,
            effect_asset_id=effect_asset.asset_id,
            damage_pop=damage_pop,
            timeline_id=timeline_id,
        )
    spec = _SIGNATURE_TIMELINE_SPECS.get(skill_id)
    if spec is None:
        return None

    hero_sequence = _signature_hero_frames(hero_asset)
    enemy_sequence = _signature_enemy_frames(enemy_asset)
    beats = tuple(
        TimelineBeat(
            spec.beat_ids[index],
            _signature_duration(index),
            hero_asset.asset_id,
            hero_sequence[index],
            enemy_asset.asset_id,
            enemy_sequence[index],
            effect_asset.asset_id,
            _frame_or_fallback(effect_asset, frame_id, fallback_index=index),
            effect_offset=spec.effect_offsets[index],
            damage_pop=_signature_damage_pop(index, spec, damage_pop),
            hud_delta=spec.hud_deltas[index],
            hit_stop=index == spec.hit_stop_index,
        )
        for index, frame_id in enumerate(spec.effect_frames)
    )
    return AnimationTimeline(timeline_id=timeline_id, beats=beats)


def build_hex_seal_smoke_timeline(
    *,
    hero_asset_id: str = "hero_shadow_apprentice_battle_sheet",
    enemy_asset_id: str = "enemy_black_candle_acolyte_actor_sheet",
    effect_asset_id: str = "skill_hex_seal_effect_sheet",
    damage_pop: str = "-16 HP",
    timeline_id: str = "smoke.hex_seal.black_candle",
) -> AnimationTimeline:
    """Return the 12-beat Astia/Black Candle/Hex Seal smoke timeline contract."""
    hero = hero_asset_id
    enemy = enemy_asset_id
    effect = effect_asset_id
    return AnimationTimeline(
        timeline_id=timeline_id,
        beats=(
            TimelineBeat("idle", 70, hero, "idle", enemy, "idle", effect, "idle"),
            TimelineBeat(
                "windup",
                70,
                hero,
                "ready",
                enemy,
                "telegraph",
                effect,
                "windup",
                effect_offset=(4, 0),
                hud_delta="target_reticle",
            ),
            TimelineBeat(
                "seal_spawn",
                60,
                hero,
                "signature",
                enemy,
                "telegraph",
                effect,
                "seal_spawn",
                effect_offset=(12, 0),
                hud_delta="candle_flare",
            ),
            TimelineBeat(
                "travel_mid",
                50,
                hero,
                "skill",
                enemy,
                "telegraph",
                effect,
                "travel_mid",
                effect_offset=(30, 0),
                hud_delta="seal_travel",
            ),
            TimelineBeat(
                "travel_near",
                50,
                hero,
                "attack",
                enemy,
                "telegraph",
                effect,
                "travel_near",
                effect_offset=(48, 0),
                hud_delta="seal_near",
            ),
            TimelineBeat(
                "hit_stop",
                90,
                hero,
                "attack",
                enemy,
                "hit",
                effect,
                "hit_stop",
                effect_offset=(58, 0),
                damage_pop=damage_pop,
                hud_delta="impact",
                hit_stop=True,
            ),
            TimelineBeat(
                "damage_pop",
                70,
                hero,
                "signature",
                enemy,
                "break",
                effect,
                "damage_pop",
                effect_offset=(60, -1),
                damage_pop=f"{damage_pop} | SLN",
                hud_delta="chant_cut",
            ),
            TimelineBeat(
                "settle",
                70,
                hero,
                "idle",
                enemy,
                "break",
                effect,
                "settle",
                effect_offset=(54, 0),
                hud_delta="status_settle",
            ),
            TimelineBeat(
                "recover",
                80,
                hero,
                "idle",
                enemy,
                "idle",
                effect,
                "recover",
                effect_offset=(38, 0),
                hud_delta="recover",
            ),
            TimelineBeat(
                "dissolve",
                60,
                hero,
                "idle",
                enemy,
                "idle",
                effect,
                "dissolve",
                effect_offset=(28, 0),
                hud_delta="dissolve",
            ),
            TimelineBeat(
                "trail",
                60,
                hero,
                "ready",
                enemy,
                "idle",
                effect,
                "trail",
                effect_offset=(16, 0),
                hud_delta="afterimage",
            ),
            TimelineBeat(
                "impact",
                80,
                hero,
                "idle",
                enemy,
                "idle",
                effect,
                "impact",
                effect_offset=(0, 0),
                hud_delta="complete",
            ),
        ),
    )


def _signature_hero_frames(hero_asset: SpriteAsset) -> tuple[str, ...]:
    idle = _frame_or_fallback(hero_asset, "idle", fallback_index=0)
    ready = _frame_or_fallback(hero_asset, "ready", fallback_index=1)
    signature = _frame_or_fallback(hero_asset, "signature", fallback_index=-1)
    attack = _frame_or_fallback(hero_asset, "attack", fallback_index=3)
    skill = _frame_or_fallback(hero_asset, "skill", fallback_index=4)
    return (
        idle,
        ready,
        signature,
        signature,
        attack,
        attack,
        signature,
        skill,
        ready,
        idle,
        ready,
        idle,
    )


def _signature_enemy_frames(enemy_asset: SpriteAsset) -> tuple[str, ...]:
    idle = _frame_or_fallback(enemy_asset, "idle", fallback_index=0)
    telegraph = _frame_or_fallback(enemy_asset, "telegraph", fallback_index=1)
    hit = _frame_or_fallback(enemy_asset, "hit", fallback_index=3)
    broken = _frame_or_fallback(enemy_asset, "break", fallback_index=4)
    return (
        idle,
        telegraph,
        telegraph,
        telegraph,
        telegraph,
        hit,
        broken,
        broken,
        broken,
        hit,
        telegraph,
        idle,
    )


def _signature_duration(index: int) -> int:
    durations = (70, 70, 60, 55, 50, 90, 70, 70, 60, 60, 60, 80)
    return durations[index]


def _signature_damage_pop(
    index: int,
    spec: SignatureTimelineSpec,
    damage_pop: str,
) -> str:
    if index == spec.hit_stop_index:
        return damage_pop
    if index == spec.status_pop_index:
        return f"{damage_pop} | {spec.status_tag}"
    return ""


def _frame_or_fallback(
    asset: SpriteAsset,
    frame_id: str,
    *,
    fallback_index: int,
) -> str:
    if frame_id in asset.frames:
        return frame_id
    if not asset.frame_ids:
        return frame_id
    index = fallback_index
    if index < 0:
        index = len(asset.frame_ids) + index
    return asset.frame_ids[max(0, min(index, len(asset.frame_ids) - 1))]
