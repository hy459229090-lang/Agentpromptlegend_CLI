"""YAML content loader and reference validator."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from ouro_agent.content.schema import (
    AffixData,
    ContentBundle,
    DungeonData,
    DungeonFloor,
    EnemyData,
    HeroData,
    ItemData,
    NodeData,
    ResonanceData,
    SchemaError,
    SkillData,
)


class ContentError(SchemaError):
    """Raised when a content directory fails to load or cross-validate."""


def _wrap(err: SchemaError) -> "ContentError":
    if isinstance(err, ContentError):
        return err
    return ContentError(str(err))


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        raise ContentError(f"missing content file: {path}")
    with path.open("r", encoding="utf-8") as fp:
        try:
            data = yaml.safe_load(fp)
        except yaml.YAMLError as err:
            raise ContentError(f"yaml parse error in {path}: {err}") from err
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ContentError(f"top level of {path} must be a mapping")
    return data


def _iter_yaml_files(directory: Path) -> Iterable[Path]:
    if not directory.exists():
        return ()
    return sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))


def load_content_bundle(content_root: Path) -> ContentBundle:
    """Load heroes / skills / enemies and cross-validate references."""
    bundle = ContentBundle()

    try:
        for path in _iter_yaml_files(content_root / "skills"):
            raw = _read_yaml(path)
            for idx, item in enumerate(raw.get("skills", []) or []):
                where = f"{path.name}#skills[{idx}]"
                skill = SkillData.from_dict(item, where)
                if skill.id in bundle.skills:
                    raise ContentError(f"{where}: duplicate skill id '{skill.id}'")
                bundle.skills[skill.id] = skill

        for path in _iter_yaml_files(content_root / "enemies"):
            raw = _read_yaml(path)
            for idx, item in enumerate(raw.get("enemies", []) or []):
                where = f"{path.name}#enemies[{idx}]"
                enemy = EnemyData.from_dict(item, where)
                if enemy.id in bundle.enemies:
                    raise ContentError(f"{where}: duplicate enemy id '{enemy.id}'")
                bundle.enemies[enemy.id] = enemy

        for path in _iter_yaml_files(content_root / "items"):
            raw = _read_yaml(path)
            for idx, item in enumerate(raw.get("items", []) or []):
                where = f"{path.name}#items[{idx}]"
                item_data = ItemData.from_dict(item, where)
                if item_data.id in bundle.items:
                    raise ContentError(f"{where}: duplicate item id '{item_data.id}'")
                bundle.items[item_data.id] = item_data

        for path in _iter_yaml_files(content_root / "affixes"):
            raw = _read_yaml(path)
            for idx, item in enumerate(raw.get("affixes", []) or []):
                where = f"{path.name}#affixes[{idx}]"
                affix = AffixData.from_dict(item, where)
                if affix.id in bundle.affixes:
                    raise ContentError(f"{where}: duplicate affix id '{affix.id}'")
                bundle.affixes[affix.id] = affix

        for path in _iter_yaml_files(content_root / "resonances"):
            raw = _read_yaml(path)
            for idx, item in enumerate(raw.get("resonances", []) or []):
                where = f"{path.name}#resonances[{idx}]"
                res = ResonanceData.from_dict(item, where)
                if res.id in bundle.resonances:
                    raise ContentError(f"{where}: duplicate resonance id '{res.id}'")
                bundle.resonances[res.id] = res

        for path in _iter_yaml_files(content_root / "heroes"):
            raw = _read_yaml(path)
            for idx, item in enumerate(raw.get("heroes", []) or []):
                where = f"{path.name}#heroes[{idx}]"
                hero = HeroData.from_dict(item, where)
                if hero.id in bundle.heroes:
                    raise ContentError(f"{where}: duplicate hero id '{hero.id}'")
                for sid in hero.skills:
                    if sid not in bundle.skills:
                        raise ContentError(
                            f"{where}: hero '{hero.id}' references unknown skill '{sid}'"
                        )
                for iid in hero.default_build.items:
                    if iid not in bundle.items:
                        raise ContentError(
                            f"{where}: hero '{hero.id}' references unknown item '{iid}'"
                        )
                for aid in hero.default_build.affixes:
                    if aid not in bundle.affixes:
                        raise ContentError(
                            f"{where}: hero '{hero.id}' references unknown affix '{aid}'"
                        )
                bundle.heroes[hero.id] = hero

        for path in _iter_yaml_files(content_root / "dungeons"):
            raw = _read_yaml(path)
            for idx, item in enumerate(raw.get("nodes", []) or []):
                where = f"{path.name}#nodes[{idx}]"
                node = NodeData.from_dict(item, where)
                if node.id in bundle.nodes:
                    raise ContentError(f"{where}: duplicate node id '{node.id}'")
                for eid in node.enemy_ids:
                    if eid and eid not in bundle.enemies:
                        raise ContentError(
                            f"{where}: node '{node.id}' references unknown enemy '{eid}'"
                        )
                if node.shop_items:
                    for shop_item in node.shop_items:
                        if shop_item.item_id and shop_item.item_id not in bundle.items:
                            raise ContentError(
                                f"{where}: node '{node.id}' references unknown item '{shop_item.item_id}'"
                            )
                        if shop_item.affix_id and shop_item.affix_id not in bundle.affixes:
                            raise ContentError(
                                f"{where}: node '{node.id}' references unknown affix '{shop_item.affix_id}'"
                            )
                if node.rewards and node.rewards.reward_choices:
                    for choice in node.rewards.reward_choices:
                        if choice.item_id and choice.item_id not in bundle.items:
                            raise ContentError(
                                f"{where}: node '{node.id}' references unknown item '{choice.item_id}'"
                            )
                        if choice.affix_id and choice.affix_id not in bundle.affixes:
                            raise ContentError(
                                f"{where}: node '{node.id}' references unknown affix '{choice.affix_id}'"
                            )
                bundle.nodes[node.id] = node

            for idx, item in enumerate(raw.get("dungeons", []) or []):
                where = f"{path.name}#dungeons[{idx}]"
                dungeon = DungeonData.from_dict(item, where)
                if dungeon.id in bundle.dungeons:
                    raise ContentError(f"{where}: duplicate dungeon id '{dungeon.id}'")
                for floor in dungeon.floors:
                    for nid in floor.nodes:
                        if nid not in bundle.nodes:
                            raise ContentError(
                                f"{where}: dungeon '{dungeon.id}' references unknown node '{nid}'"
                            )
                bundle.dungeons[dungeon.id] = dungeon
    except SchemaError as err:
        raise _wrap(err) from err

    if not bundle.heroes:
        raise ContentError(f"no heroes loaded from {content_root}")
    if not bundle.skills:
        raise ContentError(f"no skills loaded from {content_root}")
    if not bundle.enemies:
        raise ContentError(f"no enemies loaded from {content_root}")

    return bundle
