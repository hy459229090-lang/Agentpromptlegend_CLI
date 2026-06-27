"""Display-only asset card helpers for reward/build UI surfaces."""
from __future__ import annotations

from typing import Any

from ouro_agent.art.sprite_atlas import SpriteAsset, SpriteAtlas, SpriteFrame
from ouro_agent.tui.glyphs import GlyphSet, get_glyph_set


def render_reward_asset_art(
    choice: Any,
    atlas: SpriteAtlas | None,
    *,
    language: str = "en",
    unicode_mode: bool = False,
) -> list[str] | None:
    """Return asset-backed art lines for a reward choice.

    The helper reads already QA-promoted runtime atlas metadata. It never
    changes rewards, build state, choices, or content data.
    """
    return render_choice_asset_art(
        choice,
        atlas,
        language=language,
        unicode_mode=unicode_mode,
    )


def render_choice_asset_art(
    choice: Any,
    atlas: SpriteAtlas | None,
    *,
    language: str = "en",
    unicode_mode: bool = False,
    include_reward_card: bool = True,
) -> list[str] | None:
    """Return asset-backed art lines for run choice cards."""
    if atlas is None:
        return None

    lines: list[str] = []
    primary = _choice_primary_frame(choice, atlas)
    if primary is not None:
        source_type, frame = primary
        lines.append(_asset_line("asset", source_type, frame, language=language))
        lines.append(
            _asset_thumbnail_line(
                "asset",
                source_type,
                frame,
                language=language,
                unicode_mode=unicode_mode,
            )
        )

    reward_frame = _reward_card_frame(choice, atlas) if include_reward_card else None
    if reward_frame is not None:
        lines.append(_asset_line("card", "reward", reward_frame, language=language))
        lines.append(
            _asset_thumbnail_line(
                "card",
                "reward",
                reward_frame,
                language=language,
                unicode_mode=unicode_mode,
            )
        )

    return lines or None


def render_rest_asset_art(
    option: str,
    atlas: SpriteAtlas | None,
    *,
    language: str = "en",
    unicode_mode: bool = False,
) -> list[str] | None:
    """Return asset-backed art lines for rest options."""
    if atlas is None:
        return None
    frame = _rest_option_frame(option, atlas)
    if frame is None:
        return None
    source_type = {
        "recover": "heal",
        "focus": "focus",
        "study": "codex",
    }.get(option, "rest")
    return [
        _asset_line("asset", source_type, frame, language=language),
        _asset_thumbnail_line(
            "asset",
            source_type,
            frame,
            language=language,
            unicode_mode=unicode_mode,
        ),
    ]


def render_hero_asset_art(
    hero: Any,
    atlas: SpriteAtlas | None,
    *,
    language: str = "en",
    unicode_mode: bool = False,
) -> list[str] | None:
    """Return asset-backed art lines for a hero card or run setup surface."""
    if atlas is None:
        return None
    hero_id = getattr(hero, "id", str(hero))
    asset = _find_asset(
        atlas,
        source_type="hero",
        source_content_id=hero_id,
    )
    if asset is None:
        return None
    frame = _first_frame(asset, ("portrait", "ready", "idle"))
    return [
        _asset_line("asset", "hero", frame, language=language),
        _asset_thumbnail_line(
            "asset",
            "hero",
            frame,
            language=language,
            unicode_mode=unicode_mode,
        ),
    ]


def render_route_asset_art(
    dungeon_id: str,
    node_types: list[str] | tuple[str, ...],
    atlas: SpriteAtlas | None,
    *,
    language: str = "en",
    unicode_mode: bool = False,
) -> list[str] | None:
    """Return asset-backed stage lines for a route choice surface."""
    if atlas is None:
        return None

    lines: list[str] = []
    dungeon_asset = _find_asset(
        atlas,
        source_type="dungeon",
        source_content_id=dungeon_id,
    )
    if dungeon_asset is not None:
        frame = _first_frame(dungeon_asset, ("background", "floor_texture", "combat_intro"))
        lines.append(_asset_line("stage", "dungeon", frame, language=language))
        lines.append(
            _asset_thumbnail_line(
                "stage",
                "dungeon",
                frame,
                language=language,
                unicode_mode=unicode_mode,
            )
        )

    for node_type in _unique_node_asset_types(node_types):
        asset = _find_asset(
            atlas,
            source_type="node_type",
            source_content_id=node_type,
        )
        if asset is None:
            continue
        frame = _first_frame(
            asset,
            (
                "background",
                "intro_plate",
                "encounter_mood",
                "counter",
                "shrine_light",
                "recovery_glow",
                "altar_symbols",
                "choice_glow",
                "chapel_doors",
                "boss_intro",
            ),
        )
        lines.append(_asset_line("route", "node", frame, language=language))
        lines.append(
            _asset_thumbnail_line(
                "route",
                "node",
                frame,
                language=language,
                unicode_mode=unicode_mode,
            )
        )

    return lines or None


def render_codex_asset_art(
    enemy: Any,
    stage: Any,
    atlas: SpriteAtlas | None,
    *,
    language: str = "en",
    unicode_mode: bool = False,
) -> list[str] | None:
    """Return unlock-aware asset lines for a Codex card."""
    if atlas is None:
        return None

    stage_name = getattr(stage, "name", str(stage)).upper()
    is_unknown = stage_name == "UNKNOWN"
    lines: list[str] = []

    if not is_unknown:
        enemy_asset = _find_asset(
            atlas,
            source_type="enemy",
            source_content_id=getattr(enemy, "id", str(enemy)),
        )
        if enemy_asset is not None:
            enemy_frame = _first_frame(enemy_asset, ("codex_reveal", "idle", "telegraph"))
            lines.append(_asset_line("asset", "enemy", enemy_frame, language=language))
            lines.append(
                _asset_thumbnail_line(
                    "asset",
                    "enemy",
                    enemy_frame,
                    language=language,
                    unicode_mode=unicode_mode,
                )
            )

    codex_asset = _find_asset(
        atlas,
        source_type="ui_state",
        source_content_id="codex_reveal",
    )
    if codex_asset is not None:
        frame_names = ("locked", "fog") if is_unknown else ("reveal", "learned", "fog")
        codex_frame = _first_frame(codex_asset, frame_names)
        lines.append(_asset_line("codex", "codex", codex_frame, language=language))
        lines.append(
            _asset_thumbnail_line(
                "codex",
                "codex",
                codex_frame,
                language=language,
                unicode_mode=unicode_mode,
            )
        )

    return lines or None


def render_codex_gallery_asset_line(
    enemy: Any,
    stage: Any,
    atlas: SpriteAtlas | None,
    *,
    language: str = "en",
) -> str | None:
    """Return a compact, non-identifying Codex gallery asset status line."""
    if atlas is None:
        return None

    stage_name = getattr(stage, "name", str(stage)).upper()
    is_unknown = stage_name == "UNKNOWN"
    parts: list[str] = []

    if not is_unknown:
        enemy_asset = _find_asset(
            atlas,
            source_type="enemy",
            source_content_id=getattr(enemy, "id", str(enemy)),
        )
        if enemy_asset is not None:
            frame = _first_frame(enemy_asset, ("codex_reveal", "idle", "telegraph"))
            status = "BMP" if frame.has_bitmap and frame.runtime_promoted else "CELL"
            parts.append(f"{status} enemy {frame.frame_id}")

    codex_asset = _find_asset(
        atlas,
        source_type="ui_state",
        source_content_id="codex_reveal",
    )
    if codex_asset is not None:
        frame_names = ("locked", "fog") if is_unknown else ("reveal", "learned", "fog")
        frame = _first_frame(codex_asset, frame_names)
        status = "BMP" if frame.has_bitmap and frame.runtime_promoted else "CELL"
        parts.append(f"{status} codex {frame.frame_id}")

    if not parts:
        return None
    label = "资产" if language == "zh" else "Asset"
    return f"{label}: {' | '.join(parts)}"


def render_run_record_asset_art(
    *,
    hero_id: str,
    dungeon_id: str,
    result: str,
    atlas: SpriteAtlas | None,
    language: str = "en",
    unicode_mode: bool = False,
) -> list[str] | None:
    """Return asset-backed visual anchors for run result/report surfaces."""
    if atlas is None:
        return None

    lines: list[str] = []
    hero_asset = _find_asset(atlas, source_type="hero", source_content_id=hero_id)
    if hero_asset is not None:
        frame_name = "victory" if result == "complete" else "defeat"
        frame = _first_frame(hero_asset, (frame_name, "portrait", "idle"))
        lines.append(_asset_line("result", "hero", frame, language=language))
        lines.append(
            _asset_thumbnail_line(
                "result",
                "hero",
                frame,
                language=language,
                unicode_mode=unicode_mode,
            )
        )

    dungeon_asset = _find_asset(atlas, source_type="dungeon", source_content_id=dungeon_id)
    if dungeon_asset is not None:
        frame = _first_frame(dungeon_asset, ("background", "floor_texture", "combat_intro"))
        lines.append(_asset_line("stage", "dungeon", frame, language=language))
        lines.append(
            _asset_thumbnail_line(
                "stage",
                "dungeon",
                frame,
                language=language,
                unicode_mode=unicode_mode,
            )
        )

    card_asset = _find_asset(atlas, source_type="ui_state", source_content_id="reward_card")
    if card_asset is not None:
        frame_names = ("high", "online", "seed") if result == "complete" else ("lock", "seed")
        frame = _first_frame(card_asset, frame_names)
        lines.append(_asset_line("result", "reward", frame, language=language))
        lines.append(
            _asset_thumbnail_line(
                "result",
                "reward",
                frame,
                language=language,
                unicode_mode=unicode_mode,
            )
        )

    return lines or None


def _unique_node_asset_types(node_types: list[str] | tuple[str, ...]) -> list[str]:
    mapped: list[str] = []
    for node_type in node_types:
        asset_type = {
            "elite_combat": "normal_combat",
            "mimic_chest": "normal_combat",
        }.get(node_type, node_type)
        if asset_type not in mapped:
            mapped.append(asset_type)
    return mapped


def _choice_primary_frame(
    choice: Any,
    atlas: SpriteAtlas,
) -> tuple[str, SpriteFrame] | None:
    choice_type = getattr(choice, "type", "")
    if choice_type == "item" and getattr(choice, "item_id", None):
        asset = _find_asset(
            atlas,
            source_type="item",
            source_content_id=choice.item_id,
        )
        return (
            ("item", _first_frame(asset, ("card", "icon", "hud_mark")))
            if asset
            else None
        )
    if choice_type == "affix" and getattr(choice, "affix_id", None):
        asset = _find_asset(
            atlas,
            source_type="affix",
            source_content_id=choice.affix_id,
        )
        return (
            ("affix", _first_frame(asset, ("reward_motif", "badge", "build_online")))
            if asset
            else None
        )
    if choice_type == "codex":
        asset = _find_asset(
            atlas,
            source_type="ui_state",
            source_content_id="codex_reveal",
        )
        return ("codex", _first_frame(asset, ("reveal", "learned", "fog"))) if asset else None
    if choice_type == "heal":
        asset = _find_asset(
            atlas,
            source_type="ui_state",
            source_content_id="hp_bar",
        )
        return ("heal", _first_frame(asset, ("recover", "fill", "delta"))) if asset else None
    if choice_type == "scout":
        asset = _find_asset(
            atlas,
            source_type="ui_state",
            source_content_id="codex_reveal",
        )
        return ("codex", _first_frame(asset, ("reveal", "fog", "learned"))) if asset else None
    if choice_type == "strategy":
        asset = _find_asset(
            atlas,
            source_type="ui_state",
            source_content_id="atb_bar",
        )
        return ("strategy", _first_frame(asset, ("ready", "charge", "spent"))) if asset else None
    return None


def _reward_card_frame(choice: Any, atlas: SpriteAtlas) -> SpriteFrame | None:
    asset = _find_asset(
        atlas,
        source_type="ui_state",
        source_content_id="reward_card",
    )
    if asset is None:
        return None
    frame_by_type = {
        "item": "online",
        "affix": "pair",
        "codex": "lock",
        "gold": "seed",
        "heal": "high",
    }
    frame_id = frame_by_type.get(getattr(choice, "type", ""), "seed")
    return _first_frame(asset, (frame_id, "seed", "online", "card"))


def _rest_option_frame(option: str, atlas: SpriteAtlas) -> SpriteFrame | None:
    if option == "recover":
        asset = _find_asset(
            atlas,
            source_type="ui_state",
            source_content_id="hp_bar",
        )
        return _first_frame(asset, ("fill", "delta", "danger")) if asset else None
    if option == "focus":
        asset = _find_asset(
            atlas,
            source_type="ui_state",
            source_content_id="status_shield",
        )
        return _first_frame(asset, ("applied", "badge", "ticking")) if asset else None
    if option == "study":
        asset = _find_asset(
            atlas,
            source_type="ui_state",
            source_content_id="codex_reveal",
        )
        return _first_frame(asset, ("reveal", "fog", "learned")) if asset else None
    return None


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


def _first_frame(asset: SpriteAsset, names: tuple[str, ...]) -> SpriteFrame:
    for name in names:
        if name in asset.frames:
            return asset.frames[name]
    return next(iter(asset.frames.values()))


def _asset_line(
    role: str,
    source_type: str,
    frame: SpriteFrame,
    *,
    language: str,
) -> str:
    role_label = _role_label(role, language)
    type_label = _source_type_label(source_type, language)
    status = "BMP" if frame.has_bitmap and frame.runtime_promoted else "CELL"
    fallback = "fallback" if language != "zh" else "fallback"
    return (
        f"[{role_label}] {status} {type_label} {frame.frame_id} | "
        f"{fallback} {frame.fallback_cell_id}"
    )


def _asset_thumbnail_line(
    role: str,
    source_type: str,
    frame: SpriteFrame,
    *,
    language: str,
    unicode_mode: bool,
) -> str:
    role_label = _thumbnail_label(role, language)
    type_label = _source_type_label(source_type, language)
    glyphs = get_glyph_set("unicode" if unicode_mode else "ascii")
    thumbnail = " ".join(_frame_thumbnail(frame, source_type, glyphs=glyphs))
    size = _size_label(frame)
    crop = _crop_label(frame)
    pixels = str(frame.visible_pixels)
    if language == "zh":
        return f"[{role_label}] {thumbnail} | {type_label} {size} 裁切 {crop} 像素 {pixels}"
    return f"[{role_label}] {thumbnail} | {type_label} {size} crop {crop} px {pixels}"


def _frame_thumbnail(
    frame: SpriteFrame,
    source_type: str,
    *,
    glyphs: GlyphSet,
) -> tuple[str, str, str]:
    token = _thumbnail_token(source_type)
    fill = _density_glyph(frame, glyphs)
    return (
        f"{glyphs.upper}{fill * 3}{glyphs.upper}",
        f"{glyphs.left}{token}{glyphs.right}",
        f"{glyphs.lower}{glyphs.mid * 3}{glyphs.lower}",
    )


def _thumbnail_token(source_type: str) -> str:
    return {
        "item": "ITM",
        "affix": "AFX",
        "codex": "CDX",
        "heal": "HP ",
        "focus": "SHD",
        "strategy": "ATB",
        "rest": "RST",
        "reward": "RWD",
        "hero": "HRO",
        "dungeon": "DNG",
        "node": "NOD",
        "enemy": "ENM",
    }.get(source_type, source_type[:3].upper().ljust(3)[:3])


def _density_glyph(frame: SpriteFrame, glyphs: GlyphSet) -> str:
    bbox = frame.visible_bbox
    if bbox is None:
        return glyphs.mid
    width = max(1, bbox[2] - bbox[0])
    height = max(1, bbox[3] - bbox[1])
    density = frame.visible_pixels / max(1, width * height)
    if density >= 0.62:
        return glyphs.solid
    if density >= 0.32:
        return glyphs.mid
    return glyphs.light


def _size_label(frame: SpriteFrame) -> str:
    if frame.frame_size is None:
        return "-"
    return f"{frame.frame_size[0]}x{frame.frame_size[1]}"


def _crop_label(frame: SpriteFrame) -> str:
    if frame.visible_bbox is None:
        return "-"
    width = max(0, frame.visible_bbox[2] - frame.visible_bbox[0])
    height = max(0, frame.visible_bbox[3] - frame.visible_bbox[1])
    return f"{width}x{height}"


def _thumbnail_label(role: str, language: str) -> str:
    if language == "zh":
        return {
            "asset": "缩略",
            "card": "卡缩",
            "stage": "场景缩略",
            "route": "路线缩略",
            "codex": "图鉴缩略",
            "result": "结算缩略",
        }.get(role, role)
    return {
        "asset": "THUMB",
        "card": "CARD THUMB",
        "stage": "STAGE THUMB",
        "route": "ROUTE THUMB",
        "codex": "CODEX THUMB",
        "result": "RESULT THUMB",
    }.get(role, role.upper())


def _role_label(role: str, language: str) -> str:
    if language == "zh":
        return {"asset": "资产", "card": "卡面", "stage": "场景", "route": "路线", "codex": "图鉴", "result": "结算"}.get(role, role)
    return {"asset": "ASSET", "card": "CARD", "stage": "STAGE", "route": "ROUTE", "codex": "CODEX", "result": "RESULT"}.get(role, role.upper())


def _source_type_label(source_type: str, language: str) -> str:
    if language == "zh":
        return {
            "item": "装备",
            "affix": "词条",
            "codex": "图鉴",
            "heal": "治疗",
            "focus": "专注",
            "strategy": "策略",
            "rest": "休整",
            "reward": "奖励",
            "hero": "英雄",
            "dungeon": "地牢",
            "node": "节点",
            "enemy": "敌人",
        }.get(source_type, source_type)
    return source_type
