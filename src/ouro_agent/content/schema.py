"""Strict dataclass schema for game content.

Loaders translate raw yaml dicts into these dataclasses and reject any file
whose IDs, references, or required fields are missing or malformed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import Iterable, Mapping

from ouro_agent.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


class CodexStage(IntEnum):
    """Codex unlock stage for a monster family/tier.

    Order matters: higher stages include information from lower stages.
    Values are ordered for comparison operations.
    """
    UNKNOWN = 0
    OBSERVED = 1
    FAMILIAR = 2
    MASTERED = 3
    HUNTED = 4

    @classmethod
    def from_encounters(cls, encounters: int, defeats: int) -> "CodexStage":
        """Calculate codex stage from encounter and defeat counts.

        Based on G07:
        - OBSERVED: 1+ encounters
        - FAMILIAR: 2+ defeats
        - MASTERED: 5+ defeats
        - HUNTED: 10+ defeats
        """
        if defeats >= 10:
            return cls.HUNTED
        if defeats >= 5:
            return cls.MASTERED
        if defeats >= 2:
            return cls.FAMILIAR
        if encounters >= 1:
            return cls.OBSERVED
        return cls.UNKNOWN


VALID_CODEX_STAGES = {stage.name.lower() for stage in CodexStage}
VALID_MONSTER_TIERS = {"trace", "ritebound", "archive_bound"}
VALID_TIERS = {"common", "heroic", "legendary"}
VALID_STAT_FIELDS = {"hp", "mp", "speed", "attack", "defense", "power"}
VALID_FIXED_EFFECT_KINDS = {"battle_start_status", "passive_tag"}
VALID_ALLOWED_EFFECT_KINDS = {
    "bleed_on_hit",
    "double_strike",
    "shadow_bonus",
    "shield_on_low_hp",
}
VALID_ACTION_TYPES = {
    "basic_attack",
    "cast_skill",
    "use_item",
    "defend",
    "observe",
    "change_stance",
}
VALID_TARGET_RULES = {"self", "single_enemy", "all_enemies", "single_ally", "all_allies"}
VALID_DAMAGE_TYPES = {"physical", "shadow", "fire", "ice", "holy", "none"}
VALID_STATUS_IDS = {
    "status_poison",
    "status_bleed",
    "status_shield",
    "status_corruption",
    "status_silence",
}
VALID_BEHAVIOR_KINDS = {"rule_basic", "rule_chant"}

ID_PREFIXES = {
    "hero": "hero_",
    "skill": "skill_",
    "enemy": "enemy_",
    "status": "status_",
    "dungeon": "dungeon_",
    "node": "node_",
}

VALID_NODE_TYPES = {
    "normal_combat",
    "elite_combat",
    "mimic_chest",
    "shop",
    "event",
    "rest",
    "boss",
}

VALID_REWARD_TYPES = {
    "item",
    "affix",
    "codex",
    "gold",
    "xp",
    "strategy",
    "heal",
}


@dataclass(frozen=True)
class LocalizedText:
    """A piece of text available in every supported language.

    On disk, accept either a plain string (used as the value for every
    language) or a mapping ``{ "en": ..., "zh": ... }``. At least one of
    ``en`` / ``zh`` must be non-empty.
    """
    en: str
    zh: str

    def get(self, lang: str = DEFAULT_LANGUAGE) -> str:
        if lang == "zh":
            return self.zh or self.en
        return self.en or self.zh

    @classmethod
    def from_value(cls, value: object, where: str) -> "LocalizedText":
        if isinstance(value, str):
            return cls(en=value, zh=value)
        if isinstance(value, Mapping):
            extra = set(value) - set(SUPPORTED_LANGUAGES)
            if extra:
                raise SchemaError(
                    f"{where}: localized text has unsupported languages: {sorted(extra)}"
                )
            en = str(value.get("en", "") or "").strip()
            zh = str(value.get("zh", "") or "").strip()
            if not en and not zh:
                raise SchemaError(
                    f"{where}: localized text requires at least one of en/zh"
                )
            return cls(en=en or zh, zh=zh or en)
        raise SchemaError(
            f"{where}: localized text must be a string or {{en, zh}} mapping"
        )


@dataclass(frozen=True)
class BaseStats:
    hp: int
    mp: int
    speed: int
    attack: int
    defense: int
    power: int

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "BaseStats":
        required = ("hp", "mp", "speed", "attack", "defense", "power")
        for key in required:
            if key not in raw:
                raise SchemaError(f"{where}: missing base stat '{key}'")
            if not isinstance(raw[key], int):
                raise SchemaError(f"{where}: stat '{key}' must be int")
        return cls(**{k: int(raw[k]) for k in required})  # type: ignore[arg-type]


@dataclass(frozen=True)
class StatusApplication:
    status_id: str
    stacks: int
    duration: int

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "StatusApplication":
        sid = raw.get("id")
        if not isinstance(sid, str) or sid not in VALID_STATUS_IDS:
            raise SchemaError(f"{where}: invalid apply_status.id '{sid}'")
        stacks = raw.get("stacks", 1)
        duration = raw.get("duration", 1)
        if not isinstance(stacks, int) or not isinstance(duration, int):
            raise SchemaError(f"{where}: stacks/duration must be int")
        return cls(status_id=sid, stacks=int(stacks), duration=int(duration))


@dataclass(frozen=True)
class SkillEffect:
    kind: str
    base: int
    power_scale: float
    damage_type: str
    apply_status: StatusApplication | None

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "SkillEffect":
        kind = raw.get("kind")
        if kind not in {"damage", "status"}:
            raise SchemaError(f"{where}: skill effect.kind must be damage or status")
        base = int(raw.get("base", 0))
        power_scale = float(raw.get("power_scale", 0.0))
        damage_type = raw.get("damage_type", "none")
        if damage_type not in VALID_DAMAGE_TYPES:
            raise SchemaError(f"{where}: invalid damage_type '{damage_type}'")
        status_raw = raw.get("apply_status")
        apply_status = (
            StatusApplication.from_dict(status_raw, f"{where}.apply_status")  # type: ignore[arg-type]
            if isinstance(status_raw, Mapping)
            else None
        )
        return cls(
            kind=str(kind),
            base=base,
            power_scale=power_scale,
            damage_type=str(damage_type),
            apply_status=apply_status,
        )


@dataclass(frozen=True)
class SkillData:
    id: str
    display_name: LocalizedText
    mp_cost: int
    cooldown: int
    target_rule: str
    tags: tuple[str, ...]
    effect: SkillEffect
    visible_description: LocalizedText

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "SkillData":
        sid = raw.get("id")
        if not isinstance(sid, str) or not sid.startswith(ID_PREFIXES["skill"]):
            raise SchemaError(f"{where}: skill id must start with 'skill_', got {sid!r}")
        target_rule = raw.get("target_rule")
        if target_rule not in VALID_TARGET_RULES:
            raise SchemaError(f"{where}: invalid target_rule '{target_rule}'")
        effect_raw = raw.get("effect")
        if not isinstance(effect_raw, Mapping):
            raise SchemaError(f"{where}: missing skill effect block")
        return cls(
            id=str(sid),
            display_name=LocalizedText.from_value(
                raw.get("display_name", sid), f"{where}.display_name"
            ),
            mp_cost=int(raw.get("mp_cost", 0)),
            cooldown=int(raw.get("cooldown", 0)),
            target_rule=str(target_rule),
            tags=tuple(str(t) for t in raw.get("tags", ()) or ()),
            effect=SkillEffect.from_dict(effect_raw, f"{where}.effect"),
            visible_description=LocalizedText.from_value(
                raw.get("visible_description", ""),
                f"{where}.visible_description",
            ),
        )


@dataclass(frozen=True)
class HeroBuild:
    items: tuple[str, ...] = ()
    affixes: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: object, where: str) -> "HeroBuild":
        if raw is None:
            return cls()
        if not isinstance(raw, Mapping):
            raise SchemaError(f"{where}: default_build must be a mapping")
        return cls(
            items=tuple(str(i) for i in raw.get("items", ()) or ()),
            affixes=tuple(str(a) for a in raw.get("affixes", ()) or ()),
        )


@dataclass(frozen=True)
class HeroData:
    id: str
    display_name: LocalizedText
    class_name: LocalizedText
    short_tag: str
    tags: tuple[str, ...]
    avatar_ascii: tuple[str, ...]
    base_stats: BaseStats
    skills: tuple[str, ...]
    default_prompt: LocalizedText
    description: LocalizedText
    default_build: HeroBuild = HeroBuild()

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "HeroData":
        hid = raw.get("id")
        if not isinstance(hid, str) or not hid.startswith(ID_PREFIXES["hero"]):
            raise SchemaError(f"{where}: hero id must start with 'hero_', got {hid!r}")
        stats_raw = raw.get("base_stats")
        if not isinstance(stats_raw, Mapping):
            raise SchemaError(f"{where}: missing base_stats")
        skills = raw.get("skills", ())
        if not isinstance(skills, Iterable) or not skills:
            raise SchemaError(f"{where}: hero must list at least one skill")
        avatar = raw.get("avatar_ascii", ())
        if not isinstance(avatar, Iterable):
            raise SchemaError(f"{where}: avatar_ascii must be a list")
        return cls(
            id=str(hid),
            display_name=LocalizedText.from_value(
                raw.get("display_name", hid), f"{where}.display_name"
            ),
            class_name=LocalizedText.from_value(
                raw.get("class_name", ""), f"{where}.class_name"
            ),
            short_tag=str(raw.get("short_tag", "[----]")),
            tags=tuple(str(t) for t in raw.get("tags", ()) or ()),
            avatar_ascii=tuple(str(line) for line in avatar),
            base_stats=BaseStats.from_dict(stats_raw, f"{where}.base_stats"),
            skills=tuple(str(s) for s in skills),
            default_prompt=LocalizedText.from_value(
                raw.get("default_prompt", ""), f"{where}.default_prompt"
            ),
            description=LocalizedText.from_value(
                raw.get("description", ""), f"{where}.description"
            ),
            default_build=HeroBuild.from_dict(
                raw.get("default_build"), f"{where}.default_build"
            ),
        )


@dataclass(frozen=True)
class EnemyBehavior:
    kind: str
    attack_chance: float
    chant_damage: int
    chant_charge_turns: int

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "EnemyBehavior":
        kind = raw.get("kind")
        if kind not in VALID_BEHAVIOR_KINDS:
            raise SchemaError(f"{where}: invalid enemy behavior kind '{kind}'")
        return cls(
            kind=str(kind),
            attack_chance=float(raw.get("attack_chance", 1.0)),
            chant_damage=int(raw.get("chant_damage", 0)),
            chant_charge_turns=int(raw.get("chant_charge_turns", 0)),
        )


@dataclass(frozen=True)
class EnemyData:
    id: str
    display_name: LocalizedText
    short_glyph: str
    base_stats: BaseStats
    behavior: EnemyBehavior
    family_id: str = ""
    tier: str = "trace"
    codex_stage_unknown: LocalizedText = field(
        default_factory=lambda: LocalizedText(en="", zh="")
    )
    codex_stage_observed: LocalizedText = field(
        default_factory=lambda: LocalizedText(en="", zh="")
    )
    codex_stage_familiar: LocalizedText = field(
        default_factory=lambda: LocalizedText(en="", zh="")
    )
    codex_stage_mastered: LocalizedText = field(
        default_factory=lambda: LocalizedText(en="", zh="")
    )
    codex_stage_hunted: LocalizedText = field(
        default_factory=lambda: LocalizedText(en="", zh="")
    )

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "EnemyData":
        eid = raw.get("id")
        if not isinstance(eid, str) or not eid.startswith(ID_PREFIXES["enemy"]):
            raise SchemaError(f"{where}: enemy id must start with 'enemy_', got {eid!r}")
        stats_raw = raw.get("base_stats")
        if not isinstance(stats_raw, Mapping):
            raise SchemaError(f"{where}: missing base_stats")
        behavior_raw = raw.get("behavior")
        if not isinstance(behavior_raw, Mapping):
            raise SchemaError(f"{where}: missing behavior block")

        family_id = raw.get("family_id", "")
        if not isinstance(family_id, str):
            raise SchemaError(f"{where}: family_id must be string")

        tier = raw.get("tier", "trace")
        if tier and tier not in VALID_MONSTER_TIERS:
            raise SchemaError(
                f"{where}: invalid tier '{tier}', must be one of {sorted(VALID_MONSTER_TIERS)}"
            )

        return cls(
            id=str(eid),
            display_name=LocalizedText.from_value(
                raw.get("display_name", eid), f"{where}.display_name"
            ),
            short_glyph=str(raw.get("short_glyph", "?")),
            base_stats=BaseStats.from_dict(stats_raw, f"{where}.base_stats"),
            behavior=EnemyBehavior.from_dict(behavior_raw, f"{where}.behavior"),
            family_id=str(family_id),
            tier=str(tier or "trace"),
            codex_stage_unknown=LocalizedText.from_value(
                raw.get("codex_stage_unknown", ""),
                f"{where}.codex_stage_unknown",
            ),
            codex_stage_observed=LocalizedText.from_value(
                raw.get("codex_stage_observed", ""),
                f"{where}.codex_stage_observed",
            ),
            codex_stage_familiar=LocalizedText.from_value(
                raw.get("codex_stage_familiar", ""),
                f"{where}.codex_stage_familiar",
            ),
            codex_stage_mastered=LocalizedText.from_value(
                raw.get("codex_stage_mastered", ""),
                f"{where}.codex_stage_mastered",
            ),
            codex_stage_hunted=LocalizedText.from_value(
                raw.get("codex_stage_hunted", ""),
                f"{where}.codex_stage_hunted",
            ),
        )

    def codex_text_for_stage(self, stage: CodexStage, lang: str = DEFAULT_LANGUAGE) -> str:
        """Get the codex description for a given stage.

        Returns the highest available stage description that is <= the given stage.
        """
        if stage == CodexStage.HUNTED and self.codex_stage_hunted.get(lang):
            return self.codex_stage_hunted.get(lang)
        if stage == CodexStage.MASTERED and self.codex_stage_mastered.get(lang):
            return self.codex_stage_mastered.get(lang)
        if stage == CodexStage.FAMILIAR and self.codex_stage_familiar.get(lang):
            return self.codex_stage_familiar.get(lang)
        if stage == CodexStage.OBSERVED and self.codex_stage_observed.get(lang):
            return self.codex_stage_observed.get(lang)
        return self.codex_stage_unknown.get(lang)

    def tier_display(self, lang: str = DEFAULT_LANGUAGE) -> str:
        """Get display name for monster tier."""
        tier_names = {
            "trace": {"en": "I: Trace", "zh": "I: 碎影"},
            "ritebound": {"en": "II: Ritebound", "zh": "II: 仪式"},
            "archive_bound": {"en": "III: Archive-Bound", "zh": "III: 档案化"},
        }
        return tier_names.get(self.tier, {}).get(lang, self.tier)


@dataclass(frozen=True)
class StatMods:
    """Additive modifiers to a unit's six base stats."""
    hp: int = 0
    mp: int = 0
    speed: int = 0
    attack: int = 0
    defense: int = 0
    power: int = 0

    @classmethod
    def from_dict(cls, raw: object, where: str) -> "StatMods":
        if raw is None:
            return cls()
        if not isinstance(raw, Mapping):
            raise SchemaError(f"{where}: stat_mods must be a mapping")
        extra = set(raw) - VALID_STAT_FIELDS
        if extra:
            raise SchemaError(
                f"{where}: stat_mods has unknown fields: {sorted(extra)}"
            )
        return cls(**{k: int(v) for k, v in raw.items()})

    def is_zero(self) -> bool:
        return not any(
            (self.hp, self.mp, self.speed, self.attack, self.defense, self.power)
        )

    def summary_parts(self) -> list[str]:
        out = []
        for name, value in (
            ("hp", self.hp),
            ("mp", self.mp),
            ("speed", self.speed),
            ("attack", self.attack),
            ("defense", self.defense),
            ("power", self.power),
        ):
            if value:
                sign = "+" if value > 0 else ""
                out.append(f"{name}{sign}{value}")
        return out


@dataclass(frozen=True)
class FixedEffect:
    """A fixed (deterministic) effect granted by an item or affix."""
    kind: str
    status_id: str = ""
    stacks: int = 0
    duration: int = 0
    tag: str = ""

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "FixedEffect":
        kind = raw.get("kind")
        if kind not in VALID_FIXED_EFFECT_KINDS:
            raise SchemaError(
                f"{where}: fixed effect kind must be one of "
                f"{sorted(VALID_FIXED_EFFECT_KINDS)}; got {kind!r}"
            )
        if kind == "battle_start_status":
            sid = raw.get("status_id")
            if not isinstance(sid, str) or sid not in VALID_STATUS_IDS:
                raise SchemaError(f"{where}: invalid status_id '{sid}'")
            return cls(
                kind=str(kind),
                status_id=str(sid),
                stacks=int(raw.get("stacks", 1)),
                duration=int(raw.get("duration", 1)),
            )
        if kind == "passive_tag":
            tag = raw.get("tag")
            if not isinstance(tag, str) or not tag:
                raise SchemaError(f"{where}: passive_tag requires non-empty 'tag'")
            return cls(kind=str(kind), tag=str(tag))
        raise SchemaError(f"{where}: unsupported fixed effect kind '{kind}'")


@dataclass(frozen=True)
class AllowedEffect:
    """A restricted set of optional effects a legendary item may pick from."""
    kind: str

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "AllowedEffect":
        kind = raw.get("kind")
        if kind not in VALID_ALLOWED_EFFECT_KINDS:
            raise SchemaError(
                f"{where}: allowed_effect kind must be one of "
                f"{sorted(VALID_ALLOWED_EFFECT_KINDS)}; got {kind!r}"
            )
        return cls(kind=str(kind))


@dataclass(frozen=True)
class ItemData:
    id: str
    display_name: LocalizedText
    tier: str
    tags: tuple[str, ...]
    stat_mods: StatMods
    fixed_effects: tuple[FixedEffect, ...]
    allowed_effects: tuple[AllowedEffect, ...]
    description: LocalizedText

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "ItemData":
        iid = raw.get("id")
        if not isinstance(iid, str) or not iid.startswith("item_"):
            raise SchemaError(f"{where}: item id must start with 'item_', got {iid!r}")
        tier = raw.get("tier")
        if tier not in VALID_TIERS:
            raise SchemaError(
                f"{where}: tier must be one of {sorted(VALID_TIERS)}; got {tier!r}"
            )
        fixed_raw = raw.get("fixed_effects")
        if fixed_raw is None:
            fixed_raw = []
        if not isinstance(fixed_raw, list):
            raise SchemaError(f"{where}: fixed_effects must be a list")
        allowed_raw = raw.get("allowed_effects")
        if allowed_raw is None:
            allowed_raw = []
        if not isinstance(allowed_raw, list):
            raise SchemaError(f"{where}: allowed_effects must be a list")
        if tier == "legendary" and not allowed_raw:
            raise SchemaError(
                f"{where}: legendary items must declare allowed_effects"
            )
        return cls(
            id=str(iid),
            display_name=LocalizedText.from_value(
                raw.get("display_name", iid), f"{where}.display_name"
            ),
            tier=str(tier),
            tags=tuple(str(t) for t in raw.get("tags", ()) or ()),
            stat_mods=StatMods.from_dict(raw.get("stat_mods"), f"{where}.stat_mods"),
            fixed_effects=tuple(
                FixedEffect.from_dict(item, f"{where}.fixed_effects[{i}]")
                for i, item in enumerate(fixed_raw)
            ),
            allowed_effects=tuple(
                AllowedEffect.from_dict(item, f"{where}.allowed_effects[{i}]")
                for i, item in enumerate(allowed_raw)
            ),
            description=LocalizedText.from_value(
                raw.get("description", ""), f"{where}.description"
            ),
        )


@dataclass(frozen=True)
class AffixData:
    id: str
    display_name: LocalizedText
    tags: tuple[str, ...]
    stat_mods: StatMods
    fixed_effects: tuple[FixedEffect, ...]
    description: LocalizedText

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "AffixData":
        aid = raw.get("id")
        if not isinstance(aid, str) or not aid.startswith("affix_"):
            raise SchemaError(
                f"{where}: affix id must start with 'affix_', got {aid!r}"
            )
        fixed_raw = raw.get("fixed_effects")
        if fixed_raw is None:
            fixed_raw = []
        if not isinstance(fixed_raw, list):
            raise SchemaError(f"{where}: fixed_effects must be a list")
        return cls(
            id=str(aid),
            display_name=LocalizedText.from_value(
                raw.get("display_name", aid), f"{where}.display_name"
            ),
            tags=tuple(str(t) for t in raw.get("tags", ()) or ()),
            stat_mods=StatMods.from_dict(raw.get("stat_mods"), f"{where}.stat_mods"),
            fixed_effects=tuple(
                FixedEffect.from_dict(item, f"{where}.fixed_effects[{i}]")
                for i, item in enumerate(fixed_raw)
            ),
            description=LocalizedText.from_value(
                raw.get("description", ""), f"{where}.description"
            ),
        )


@dataclass(frozen=True)
class ResonanceData:
    """A trigger keyed on tag counts; effect is granted at battle start."""
    id: str
    display_name: LocalizedText
    required_tag_counts: dict[str, int]
    stat_mods: StatMods
    fixed_effects: tuple[FixedEffect, ...]
    description: LocalizedText

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "ResonanceData":
        rid = raw.get("id")
        if not isinstance(rid, str) or not rid.startswith("resonance_"):
            raise SchemaError(
                f"{where}: resonance id must start with 'resonance_', got {rid!r}"
            )
        req_raw = raw.get("required_tag_counts") or {}
        if not isinstance(req_raw, Mapping) or not req_raw:
            raise SchemaError(
                f"{where}: required_tag_counts must be a non-empty mapping"
            )
        req = {str(k): int(v) for k, v in req_raw.items()}
        for tag, count in req.items():
            if count <= 0:
                raise SchemaError(
                    f"{where}: tag count for {tag!r} must be > 0"
                )
        fixed_raw = raw.get("fixed_effects")
        if fixed_raw is None:
            fixed_raw = []
        if not isinstance(fixed_raw, list):
            raise SchemaError(f"{where}: fixed_effects must be a list")
        return cls(
            id=str(rid),
            display_name=LocalizedText.from_value(
                raw.get("display_name", rid), f"{where}.display_name"
            ),
            required_tag_counts=req,
            stat_mods=StatMods.from_dict(raw.get("stat_mods"), f"{where}.stat_mods"),
            fixed_effects=tuple(
                FixedEffect.from_dict(item, f"{where}.fixed_effects[{i}]")
                for i, item in enumerate(fixed_raw)
            ),
            description=LocalizedText.from_value(
                raw.get("description", ""), f"{where}.description"
            ),
        )


@dataclass(frozen=True)
class ContentBundle:
    heroes: dict[str, HeroData] = field(default_factory=dict)
    skills: dict[str, SkillData] = field(default_factory=dict)
    enemies: dict[str, EnemyData] = field(default_factory=dict)
    items: dict[str, ItemData] = field(default_factory=dict)
    affixes: dict[str, AffixData] = field(default_factory=dict)
    resonances: dict[str, ResonanceData] = field(default_factory=dict)
    dungeons: dict[str, "DungeonData"] = field(default_factory=dict)
    nodes: dict[str, "NodeData"] = field(default_factory=dict)

    def get_hero(self, hero_id: str) -> HeroData:
        if hero_id not in self.heroes:
            raise SchemaError(f"unknown hero id '{hero_id}'")
        return self.heroes[hero_id]

    def get_enemy(self, enemy_id: str) -> EnemyData:
        if enemy_id not in self.enemies:
            raise SchemaError(f"unknown enemy id '{enemy_id}'")
        return self.enemies[enemy_id]

    def get_skill(self, skill_id: str) -> SkillData:
        if skill_id not in self.skills:
            raise SchemaError(f"unknown skill id '{skill_id}'")
        return self.skills[skill_id]

    def get_item(self, item_id: str) -> ItemData:
        if item_id not in self.items:
            raise SchemaError(f"unknown item id '{item_id}'")
        return self.items[item_id]

    def get_affix(self, affix_id: str) -> AffixData:
        if affix_id not in self.affixes:
            raise SchemaError(f"unknown affix id '{affix_id}'")
        return self.affixes[affix_id]

    def get_dungeon(self, dungeon_id: str) -> "DungeonData":
        if not hasattr(self, "dungeons") or dungeon_id not in self.dungeons:
            raise SchemaError(f"unknown dungeon id '{dungeon_id}'")
        return self.dungeons[dungeon_id]

    def get_node(self, node_id: str) -> "NodeData":
        if not hasattr(self, "nodes") or node_id not in self.nodes:
            raise SchemaError(f"unknown node id '{node_id}'")
        return self.nodes[node_id]


@dataclass(frozen=True)
class RewardChoice:
    type: str
    item_id: str | None = None
    affix_id: str | None = None
    progress: int | None = None
    strategy_style: str | None = None
    gold: int | None = None
    heal_percent: int | None = None

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "RewardChoice":
        reward_type = raw.get("type")
        if not isinstance(reward_type, str) or reward_type not in VALID_REWARD_TYPES:
            raise SchemaError(f"{where}: invalid reward type '{reward_type}'")
        return cls(
            type=str(reward_type),
            item_id=str(raw.get("item_id")) if raw.get("item_id") else None,
            affix_id=str(raw.get("affix_id")) if raw.get("affix_id") else None,
            progress=int(raw.get("progress")) if raw.get("progress") is not None else None,
            strategy_style=str(raw.get("strategy_style")) if raw.get("strategy_style") else None,
            gold=int(raw.get("gold")) if raw.get("gold") is not None else None,
            heal_percent=int(raw.get("heal_percent")) if raw.get("heal_percent") is not None else None,
        )


@dataclass(frozen=True)
class ShopItem:
    type: str
    price: int
    item_id: str | None = None
    affix_id: str | None = None
    strategy_style: str | None = None
    heal_percent: int | None = None
    restore_mp: bool = False
    scout_hint: LocalizedText | None = None

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "ShopItem":
        item_type = raw.get("type")
        if not isinstance(item_type, str) or item_type not in {"item", "affix", "strategy", "heal", "scout"}:
            raise SchemaError(f"{where}: invalid shop item type '{item_type}'")
        price = raw.get("price", 0)
        if not isinstance(price, int) or price < 0:
            raise SchemaError(f"{where}: price must be a non-negative int")
        heal_percent = raw.get("heal_percent")
        if heal_percent is not None and (
            not isinstance(heal_percent, int) or heal_percent < 0
        ):
            raise SchemaError(f"{where}: heal_percent must be a non-negative int")
        restore_mp = raw.get("restore_mp", False)
        if not isinstance(restore_mp, bool):
            raise SchemaError(f"{where}: restore_mp must be bool")
        scout_hint = (
            LocalizedText.from_value(raw.get("scout_hint"), f"{where}.scout_hint")
            if raw.get("scout_hint") is not None
            else None
        )
        return cls(
            type=str(item_type),
            price=int(price),
            item_id=str(raw.get("item_id")) if raw.get("item_id") else None,
            affix_id=str(raw.get("affix_id")) if raw.get("affix_id") else None,
            strategy_style=str(raw.get("strategy_style")) if raw.get("strategy_style") else None,
            heal_percent=int(heal_percent) if heal_percent is not None else None,
            restore_mp=restore_mp,
            scout_hint=scout_hint,
        )


@dataclass(frozen=True)
class NodeRewards:
    gold: int = 0
    xp: int = 0
    reward_choices: tuple[RewardChoice, ...] = ()

    @classmethod
    def from_dict(cls, raw: Mapping[str, object] | None, where: str) -> "NodeRewards":
        if raw is None:
            return cls()
        gold = int(raw.get("gold", 0))
        xp = int(raw.get("xp", 0))
        choices_raw = raw.get("reward_choices", []) or []
        if not isinstance(choices_raw, list):
            raise SchemaError(f"{where}: reward_choices must be a list")
        choices = tuple(
            RewardChoice.from_dict(choice, f"{where}.reward_choices[{i}]")
            for i, choice in enumerate(choices_raw)
        )
        return cls(gold=gold, xp=xp, reward_choices=choices)


@dataclass(frozen=True)
class NodeData:
    id: str
    node_type: str
    display_name: LocalizedText
    description: LocalizedText
    enemy_ids: tuple[str, ...] = ()
    shop_items: tuple[ShopItem, ...] = ()
    rewards: NodeRewards | None = None
    risk_level: str | None = None
    is_boss: bool = False
    encounter_intro: LocalizedText = field(
        default_factory=lambda: LocalizedText(en="", zh="")
    )
    boss_intro: LocalizedText = field(
        default_factory=lambda: LocalizedText(en="", zh="")
    )

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "NodeData":
        nid = raw.get("id")
        if not isinstance(nid, str) or not nid.startswith(ID_PREFIXES["node"]):
            raise SchemaError(f"{where}: node id must start with 'node_', got {nid!r}")
        node_type = raw.get("node_type")
        if not isinstance(node_type, str) or node_type not in VALID_NODE_TYPES:
            raise SchemaError(f"{where}: invalid node type '{node_type}'")
        enemy_ids = tuple(str(e) for e in raw.get("enemy_ids", ()) or ())
        shop_raw = raw.get("shop_items", []) or []
        if not isinstance(shop_raw, list):
            raise SchemaError(f"{where}: shop_items must be a list")
        shop_items = tuple(
            ShopItem.from_dict(item, f"{where}.shop_items[{i}]")
            for i, item in enumerate(shop_raw)
        )
        rewards_raw = raw.get("rewards")
        rewards = (
            NodeRewards.from_dict(rewards_raw, f"{where}.rewards")
            if rewards_raw is not None
            else None
        )
        return cls(
            id=str(nid),
            node_type=str(node_type),
            display_name=LocalizedText.from_value(
                raw.get("display_name", nid), f"{where}.display_name"
            ),
            description=LocalizedText.from_value(
                raw.get("description", ""), f"{where}.description"
            ),
            enemy_ids=enemy_ids,
            shop_items=shop_items,
            rewards=rewards,
            risk_level=str(raw.get("risk_level")) if raw.get("risk_level") else None,
            is_boss=bool(raw.get("is_boss", False)),
            encounter_intro=LocalizedText.from_value(
                raw.get("encounter_intro", ""),
                f"{where}.encounter_intro",
            ),
            boss_intro=LocalizedText.from_value(
                raw.get("boss_intro", ""),
                f"{where}.boss_intro",
            ),
        )


@dataclass(frozen=True)
class DungeonFloor:
    floor_number: int
    display_name: LocalizedText
    nodes: tuple[str, ...]
    is_start: bool = False
    is_boss_floor: bool = False
    route_choice: bool = False

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "DungeonFloor":
        floor_num = raw.get("floor_number")
        if not isinstance(floor_num, int) or floor_num < 1:
            raise SchemaError(f"{where}: floor_number must be a positive int")
        nodes_raw = raw.get("nodes", []) or []
        if not isinstance(nodes_raw, list) or not nodes_raw:
            raise SchemaError(f"{where}: floor must have at least one node")
        nodes = tuple(str(n) for n in nodes_raw)
        return cls(
            floor_number=int(floor_num),
            display_name=LocalizedText.from_value(
                raw.get("display_name", f"Floor {floor_num}"), f"{where}.display_name"
            ),
            nodes=nodes,
            is_start=bool(raw.get("is_start", False)),
            is_boss_floor=bool(raw.get("is_boss_floor", False)),
            route_choice=bool(raw.get("route_choice", False)),
        )


@dataclass(frozen=True)
class DungeonData:
    id: str
    display_name: LocalizedText
    description: LocalizedText
    scene_text: LocalizedText
    floors: tuple[DungeonFloor, ...]

    @classmethod
    def from_dict(cls, raw: Mapping[str, object], where: str) -> "DungeonData":
        did = raw.get("id")
        if not isinstance(did, str) or not did.startswith(ID_PREFIXES["dungeon"]):
            raise SchemaError(f"{where}: dungeon id must start with 'dungeon_', got {did!r}")
        floors_raw = raw.get("floors", []) or []
        if not isinstance(floors_raw, list) or not floors_raw:
            raise SchemaError(f"{where}: dungeon must have at least one floor")
        floors = tuple(
            DungeonFloor.from_dict(floor, f"{where}.floors[{i}]")
            for i, floor in enumerate(floors_raw)
        )
        return cls(
            id=str(did),
            display_name=LocalizedText.from_value(
                raw.get("display_name", did), f"{where}.display_name"
            ),
            description=LocalizedText.from_value(
                raw.get("description", ""), f"{where}.description"
            ),
            scene_text=LocalizedText.from_value(
                raw.get("scene_text", ""), f"{where}.scene_text"
            ),
            floors=floors,
        )


class SchemaError(ValueError):
    """Raised when content data violates the strict schema."""
