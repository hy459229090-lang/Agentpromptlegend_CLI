"""Map resolved combat turns to display-only combat stage timelines."""
from __future__ import annotations

from ouro_agent.art.sprite_atlas import SpriteAtlas, SpriteAsset
from ouro_agent.art.timelines import (
    AnimationTimeline,
    TimelineBeat,
    build_signature_skill_timeline,
)
from ouro_agent.content.schema import ContentBundle
from ouro_agent.engine.battle import TurnRecord
from ouro_agent.engine.models import BattleState


def build_combat_stage_timeline(
    state: BattleState,
    record: TurnRecord,
    atlas: SpriteAtlas,
) -> AnimationTimeline | None:
    """Build a sprite timeline for a resolved hero skill turn.

    The timeline is derived only from already-resolved local combat facts. It
    never changes damage, target selection, statuses, victory, trace, or reward.
    """
    if record.side != "hero" or record.judge is None:
        return None
    skill_id = record.judge.skill_id or (record.action.skill_id if record.action else None)
    if not skill_id:
        return None

    hero_asset = _find_asset(
        atlas,
        source_type="hero",
        source_content_id=state.hero.id,
    )
    skill_asset = _find_asset(
        atlas,
        source_type="skill",
        source_content_id=skill_id,
    )
    target_id = _target_enemy_id(state, record)
    if hero_asset is None or skill_asset is None or target_id is None:
        return None
    enemy_asset = _find_asset(
        atlas,
        source_type="enemy",
        source_content_id=target_id,
    )
    if enemy_asset is None:
        return None

    damage_pop = _damage_pop(record)
    signature_timeline = build_signature_skill_timeline(
        hero_asset=hero_asset,
        enemy_asset=enemy_asset,
        effect_asset=skill_asset,
        skill_id=skill_id,
        damage_pop=damage_pop,
        timeline_id=f"battle.{skill_id}.{target_id}",
    )
    if signature_timeline is not None:
        return signature_timeline

    return _build_generic_skill_timeline(
        hero_asset=hero_asset,
        enemy_asset=enemy_asset,
        skill_asset=skill_asset,
        skill_id=skill_id,
        target_id=target_id,
        damage_pop=damage_pop,
    )


def build_catalog_skill_timelines(
    bundle: ContentBundle,
    atlas: SpriteAtlas,
    *,
    enemy_id: str | None = None,
) -> tuple[AnimationTimeline, ...]:
    """Build display-only coverage timelines for every content skill.

    This is an art/QA coverage helper, not a combat simulator. It proves that
    each skill has a playable runtime effect timeline against QA-promoted atlas
    frames while keeping real battle facts owned by the local engine.
    """
    target_id = enemy_id or _default_enemy_id(bundle)
    timelines: list[AnimationTimeline] = []
    for skill_id, skill in bundle.skills.items():
        hero_id = _hero_id_for_skill(bundle, skill_id)
        if hero_id is None:
            continue
        damage_pop = f"-{max(1, skill.effect.base)} HP" if skill.effect.base > 0 else "STATUS"
        timeline = build_catalog_skill_timeline(
            atlas,
            hero_id=hero_id,
            skill_id=skill_id,
            enemy_id=target_id,
            damage_pop=damage_pop,
        )
        if timeline is not None:
            timelines.append(timeline)
    return tuple(timelines)


def build_catalog_skill_timeline(
    atlas: SpriteAtlas,
    *,
    hero_id: str,
    skill_id: str,
    enemy_id: str,
    damage_pop: str = "-12 HP",
) -> AnimationTimeline | None:
    """Build a display-only catalog timeline for a specific skill asset."""
    hero_asset = _find_asset(atlas, source_type="hero", source_content_id=hero_id)
    skill_asset = _find_asset(atlas, source_type="skill", source_content_id=skill_id)
    enemy_asset = _find_asset(atlas, source_type="enemy", source_content_id=enemy_id)
    if hero_asset is None or skill_asset is None or enemy_asset is None:
        return None
    signature_timeline = build_signature_skill_timeline(
        hero_asset=hero_asset,
        enemy_asset=enemy_asset,
        effect_asset=skill_asset,
        skill_id=skill_id,
        damage_pop=damage_pop,
        timeline_id=f"catalog.{skill_id}.{enemy_id}",
    )
    if signature_timeline is not None:
        return signature_timeline

    return _build_generic_skill_timeline(
        hero_asset=hero_asset,
        enemy_asset=enemy_asset,
        skill_asset=skill_asset,
        skill_id=skill_id,
        target_id=enemy_id,
        damage_pop=damage_pop,
        timeline_prefix="catalog",
    )


def _build_generic_skill_timeline(
    *,
    hero_asset: SpriteAsset,
    enemy_asset: SpriteAsset,
    skill_asset: SpriteAsset,
    skill_id: str,
    target_id: str,
    damage_pop: str,
    timeline_prefix: str = "battle",
) -> AnimationTimeline:
    hero_idle = _first_frame(hero_asset, ("idle", "portrait"))
    hero_ready = _first_frame(hero_asset, ("ready", hero_idle))
    hero_skill = _first_frame(hero_asset, ("skill", "attack", hero_ready))
    hero_attack = _first_frame(hero_asset, ("attack", hero_skill))
    enemy_idle = _first_frame(enemy_asset, ("idle", "codex_reveal"))
    enemy_telegraph = _first_frame(enemy_asset, ("telegraph", "cast", "attack", enemy_idle))
    enemy_hit = _first_frame(enemy_asset, ("hit", enemy_idle))
    enemy_break = _first_frame(enemy_asset, ("break", "death", enemy_hit))

    spawn = _first_frame(
        skill_asset,
        (
            "spawn",
            "windup",
            "draw",
            "focus",
            "ring",
            "load",
            "deploy",
            "raise",
            "crank",
            "veil_rise",
        ),
        fallback_index=0,
    )
    travel_a = _first_frame(
        skill_asset,
        (
            "brace",
            "flare",
            "glare",
            "travel",
            "travel_mid",
            "bolt_travel",
            "string_snap",
            "hook_launch",
            "throw",
            "arc",
            "echo_arc",
            "hymn_wave",
            "shadow_step",
            "shield_build",
            "echo_wave",
            "ignite",
            "wrap",
            "spark",
        ),
        fallback_index=1,
    )
    travel_b = _first_frame(
        skill_asset,
        (
            "near_hit",
            "travel_near",
            "pull",
            "pin",
            "gear_spin",
            "shield_flash",
            "shield_flare",
            "pulse",
            "sink",
            "shield_pop",
            "silence_mark",
            "holy_pop",
            "omen_cloud",
        ),
        fallback_index=2,
    )
    impact = _first_frame(
        skill_asset,
        (
            "impact",
            "hit_stop",
            "impact_stop",
            "shatter",
            "mute",
            "poison_pop",
            "bleed_pop",
            "shield_flash",
            "shield_flare",
            "counter_spark",
            "blast",
            "mark_pop",
            "return_wave",
            "execute_pop",
        ),
        fallback_index=3,
    )
    settle = _first_frame(
        skill_asset,
        (
            "dissolve",
            "settle",
            "recover",
            "ember_pop",
            "mark_pop",
            "return_wave",
            "omen_cloud",
        ),
        fallback_index=-2,
    )
    recover = _first_frame(skill_asset, ("recover",), fallback_index=-1)

    return AnimationTimeline(
        timeline_id=f"{timeline_prefix}.{skill_id}.{target_id}",
        beats=(
            TimelineBeat("idle", 70, hero_asset.asset_id, hero_idle, enemy_asset.asset_id, enemy_idle, skill_asset.asset_id, spawn),
            TimelineBeat("windup", 70, hero_asset.asset_id, hero_ready, enemy_asset.asset_id, enemy_telegraph, skill_asset.asset_id, spawn, effect_offset=(6, 0), hud_delta="target_reticle"),
            TimelineBeat("release", 60, hero_asset.asset_id, hero_skill, enemy_asset.asset_id, enemy_telegraph, skill_asset.asset_id, travel_a, effect_offset=(18, 0), hud_delta="release"),
            TimelineBeat("travel", 55, hero_asset.asset_id, hero_attack, enemy_asset.asset_id, enemy_telegraph, skill_asset.asset_id, travel_b, effect_offset=(38, 0), hud_delta="travel"),
            TimelineBeat("hit_stop", 90, hero_asset.asset_id, hero_attack, enemy_asset.asset_id, enemy_hit, skill_asset.asset_id, impact, effect_offset=(58, 0), damage_pop=damage_pop, hud_delta="impact", hit_stop=True),
            TimelineBeat("damage_pop", 70, hero_asset.asset_id, hero_skill, enemy_asset.asset_id, enemy_break, skill_asset.asset_id, impact, effect_offset=(60, -1), damage_pop=damage_pop, hud_delta="damage_pop"),
            TimelineBeat("settle", 70, hero_asset.asset_id, hero_idle, enemy_asset.asset_id, enemy_break, skill_asset.asset_id, settle, effect_offset=(48, 0), hud_delta="status_settle"),
            TimelineBeat("recover", 80, hero_asset.asset_id, hero_idle, enemy_asset.asset_id, enemy_idle, skill_asset.asset_id, recover, effect_offset=(24, 0), hud_delta="recover"),
        ),
    )


def _find_asset(
    atlas: SpriteAtlas,
    *,
    source_type: str,
    source_content_id: str,
) -> SpriteAsset | None:
    for asset in atlas.assets.values():
        if asset.source_type == source_type and asset.source_content_id == source_content_id:
            return asset
    return None


def _target_enemy_id(state: BattleState, record: TurnRecord) -> str | None:
    target_ids = record.judge.target_ids if record.judge else ()
    if not target_ids and record.action is not None:
        target_ids = tuple(record.action.targets)
    enemy_ids = {enemy.id for enemy in state.enemies}
    for target_id in target_ids:
        if target_id in enemy_ids:
            return target_id
    living = next((enemy.id for enemy in state.enemies if enemy.is_alive), None)
    return living or (state.enemies[0].id if state.enemies else None)


def _damage_pop(record: TurnRecord) -> str:
    damage = record.judge.damage if record.judge else 0
    if damage > 0:
        return f"-{damage} HP"
    if record.judge and record.judge.valid:
        return "STATUS"
    return "MISS"


def _default_enemy_id(bundle: ContentBundle) -> str:
    if "enemy_black_candle_acolyte" in bundle.enemies:
        return "enemy_black_candle_acolyte"
    return next(iter(bundle.enemies))


def _hero_id_for_skill(bundle: ContentBundle, skill_id: str) -> str | None:
    for hero in bundle.heroes.values():
        if skill_id in hero.skills:
            return hero.id
    return None


def _first_frame(
    asset: SpriteAsset,
    names: tuple[str, ...],
    *,
    fallback_index: int = 0,
) -> str:
    available = set(asset.frame_ids)
    for name in names:
        if name in available:
            return name
    if not asset.frame_ids:
        return ""
    index = fallback_index
    if index < 0:
        index = len(asset.frame_ids) + index
    bounded = max(0, min(index, len(asset.frame_ids) - 1))
    return asset.frame_ids[bounded]
