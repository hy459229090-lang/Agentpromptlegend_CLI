"""Build resolver: combine hero base + items + affixes + resonances.

Inputs are pure content data; output is a ``ResolvedBuild`` describing
* final stats,
* tag multiset,
* triggered resonances,
* battle-start statuses to apply.

The combat engine reads ``ResolvedBuild`` once at battle setup; nothing here
runs per-turn.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

from ouro_agent.content.schema import (
    AffixData,
    ContentBundle,
    FixedEffect,
    HeroData,
    ItemData,
    ResonanceData,
    StatMods,
)
from ouro_agent.engine.models import StatusEffect


class BuildStage(Enum):
    SEED = "seed"
    PAIR = "pair"
    ONLINE = "online"
    HIGH_ROLL = "high_roll"
    LOCKED_IN = "locked_in"

    @property
    def badge(self) -> str:
        return {
            BuildStage.SEED: "[SEED]",
            BuildStage.PAIR: "[PAIR]",
            BuildStage.ONLINE: "[ONLINE]",
            BuildStage.HIGH_ROLL: "[HIGH]",
            BuildStage.LOCKED_IN: "[LOCK]",
        }[self]

    @property
    def display_name(self) -> str:
        return {
            BuildStage.SEED: "Seed",
            BuildStage.PAIR: "Pair",
            BuildStage.ONLINE: "Online",
            BuildStage.HIGH_ROLL: "High Roll",
            BuildStage.LOCKED_IN: "Locked In",
        }[self]


@dataclass
class BuildProgress:
    stage: BuildStage
    stage_name: str
    core_tags: dict[str, int]
    active_resonances: list[str]
    near_resonances: list[dict]
    best_next_picks: list[dict]

    def badge_line(self, language: str = "en") -> str:
        parts = [self.stage.badge]
        if self.active_resonances:
            parts.append(f"active: {', '.join(self.active_resonances)}")
        return " ".join(parts)


HERO_CORE_TAGS: dict[str, list[str]] = {
    "hero_shadow_apprentice": ["shadow", "control"],
    "hero_ash_guardian": ["guard", "armor"],
    "hero_broken_string_hunter": ["bleed", "hunter"],
    "hero_mire_oracle": ["poison", "omen"],
    "hero_gravewright": ["gear", "trap"],
    "hero_echo_exile": ["echo", "holy"],
}

HERO_BUILD_ARCHETYPES: dict[str, dict[str, str]] = {
    "hero_shadow_apprentice": {
        "en": "Black Candle Interrupt",
        "zh": "黑烛打断",
    },
    "hero_ash_guardian": {
        "en": "Iron Wall Counter",
        "zh": "铁壁反击",
    },
    "hero_broken_string_hunter": {
        "en": "Bleed Execution",
        "zh": "流血处决",
    },
    "hero_mire_oracle": {
        "en": "Poison Attrition",
        "zh": "毒沼消耗",
    },
    "hero_gravewright": {
        "en": "Gear Trap Setup",
        "zh": "机关陷阱",
    },
    "hero_echo_exile": {
        "en": "Echo Ward Control",
        "zh": "回声护壁",
    },
}

HERO_RISK_LEVELS: dict[str, str] = {
    "hero_shadow_apprentice": "normal",
    "hero_ash_guardian": "easy",
    "hero_broken_string_hunter": "hard",
    "hero_mire_oracle": "normal",
    "hero_gravewright": "normal",
    "hero_echo_exile": "easy",
}

HERO_STRATEGIES: dict[str, dict[str, list[str]]] = {
    "hero_shadow_apprentice": {
        "en": [
            "Interrupt high-ATB casters.",
            "Spend MP for tempo, not vanity.",
            "Use shield before HP drops too far.",
        ],
        "zh": [
            "优先打断高 ATB 施法者。",
            "用 MP 换节奏，不为炫技乱放。",
            "血线危险前先补护盾。",
        ],
    },
    "hero_ash_guardian": {
        "en": [
            "Keep HP above the safe line.",
            "Brace before enemy telegraphs.",
            "Punish casters after they commit.",
        ],
        "zh": [
            "保持 HP 在安全线以上。",
            "敌人预兆前先架盾。",
            "等施法者露出破绽再反击。",
        ],
    },
    "hero_broken_string_hunter": {
        "en": [
            "Stack bleed on durable targets.",
            "Execute weakened enemies quickly.",
            "Use speed to create action gaps.",
        ],
        "zh": [
            "给高耐久目标叠流血。",
            "快速处决残血敌人。",
            "用速度制造行动差。",
        ],
    },
    "hero_mire_oracle": {
        "en": [
            "Poison durable targets early.",
            "Mute high-ATB casters with Omen Vial.",
            "Use Sinking Veil before the attrition race turns.",
        ],
        "zh": [
            "开局给耐久目标铺毒。",
            "用预兆毒瓶压制高 ATB 施法者。",
            "消耗战失控前使用沉沼纱幕。",
        ],
    },
    "hero_gravewright": {
        "en": [
            "Mark targets with Grave Nail.",
            "Brace with Crank Charge under pressure.",
            "Release Burial Engine into weakened or chanting enemies.",
        ],
        "zh": [
            "用坟钉标记目标。",
            "压力上升时用曲柄充能稳住。",
            "把葬仪机关打向虚弱或正在吟唱的敌人。",
        ],
    },
    "hero_echo_exile": {
        "en": [
            "Keep Bell Echo ready before heavy turns.",
            "Silence chants with Silent Hymn.",
            "Use Returning Chime to end fights cleanly.",
        ],
        "zh": [
            "敌人大回合前保留铃声回响。",
            "用静默圣歌封住吟唱。",
            "用回返钟声干净结束战斗。",
        ],
    },
}


@dataclass
class ResolvedBuild:
    hp: int
    mp: int
    speed: int
    attack: int
    defense: int
    power: int
    tags: tuple[str, ...]
    items: tuple[ItemData, ...]
    affixes: tuple[AffixData, ...]
    resonances: tuple[ResonanceData, ...]
    battle_start_statuses: list[StatusEffect] = field(default_factory=list)
    passive_tags: tuple[str, ...] = ()
    hero_id: str = ""

    def equipment_summary(self, language: str = "en") -> str:
        items = ", ".join(item.display_name.get(language) for item in self.items) or "-"
        affixes = ", ".join(affix.display_name.get(language) for affix in self.affixes) or "-"
        res = (
            ", ".join(r.display_name.get(language) for r in self.resonances)
            or "-"
        )
        return f"items: {items} | affixes: {affixes} | resonance: {res}"

    def tag_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for tag in self.tags:
            counts[tag] = counts.get(tag, 0) + 1
        return counts

    def core_tag_counts(self, hero_id: str | None = None) -> dict[str, int]:
        hid = hero_id or self.hero_id
        core_tags = HERO_CORE_TAGS.get(hid, [])
        counts = self.tag_counts()
        return {tag: counts.get(tag, 0) for tag in core_tags}

    def archetype(self, language: str = "en") -> str:
        archetypes = HERO_BUILD_ARCHETYPES.get(self.hero_id, {})
        return archetypes.get(language) or archetypes.get("en", "Unknown Build")

    def risk_level(self) -> str:
        return HERO_RISK_LEVELS.get(self.hero_id, "normal")

    def strategy_lines(self, language: str = "en") -> list[str]:
        strategies = HERO_STRATEGIES.get(self.hero_id, {})
        return strategies.get(language) or strategies.get("en", [])

    def calculate_progress(self, bundle: ContentBundle) -> BuildProgress:
        tag_counts = self.tag_counts()
        core_counts = self.core_tag_counts()
        
        active_res_ids = [r.id for r in self.resonances]
        
        near_resonances: list[dict] = []
        for res in bundle.resonances.values():
            if res.id in active_res_ids:
                continue
            missing: list[dict] = []
            for tag, need in res.required_tag_counts.items():
                have = tag_counts.get(tag, 0)
                if have < need:
                    missing.append({"tag": tag, "have": have, "need": need})
            if missing:
                near_resonances.append({
                    "id": res.id,
                    "display_name": res.display_name,
                    "missing": missing,
                })
        
        best_next_picks: list[dict] = []
        for near in near_resonances:
            for miss in near["missing"]:
                need_more = miss["need"] - miss["have"]
                best_next_picks.append({
                    "resonance_id": near["id"],
                    "resonance_name": near["display_name"],
                    "tag": miss["tag"],
                    "need": need_more,
                })
        
        stage = self._determine_stage(tag_counts, active_res_ids)
        
        return BuildProgress(
            stage=stage,
            stage_name=stage.display_name,
            core_tags=core_counts,
            active_resonances=active_res_ids,
            near_resonances=near_resonances,
            best_next_picks=best_next_picks,
        )

    def _determine_stage(self, tag_counts: dict[str, int], active_res_ids: list[str]) -> BuildStage:
        core_tags = HERO_CORE_TAGS.get(self.hero_id, [])
        
        if len(active_res_ids) >= 2:
            return BuildStage.LOCKED_IN
        
        has_legendary = any(item.tier == "legendary" for item in self.items)
        if active_res_ids and has_legendary and len(self.affixes) >= 2:
            return BuildStage.HIGH_ROLL
        
        if active_res_ids:
            return BuildStage.ONLINE
        
        core_pairs = sum(1 for tag in core_tags if tag_counts.get(tag, 0) >= 2)
        if core_pairs >= 1:
            return BuildStage.PAIR
        
        any_core = any(tag_counts.get(tag, 0) >= 1 for tag in core_tags)
        if any_core:
            return BuildStage.SEED
        
        return BuildStage.SEED


def resolve_build(
    hero: HeroData,
    bundle: ContentBundle,
    *,
    item_ids: tuple[str, ...] | None = None,
    affix_ids: tuple[str, ...] | None = None,
) -> ResolvedBuild:
    items_ids = item_ids if item_ids is not None else hero.default_build.items
    affixes_ids = affix_ids if affix_ids is not None else hero.default_build.affixes

    items = tuple(bundle.get_item(i) for i in items_ids)
    affixes = tuple(bundle.get_affix(a) for a in affixes_ids)

    base_mods = StatMods(
        hp=hero.base_stats.hp,
        mp=hero.base_stats.mp,
        speed=hero.base_stats.speed,
        attack=hero.base_stats.attack,
        defense=hero.base_stats.defense,
        power=hero.base_stats.power,
    )

    sources_mods: list[StatMods] = [base_mods]
    sources_mods.extend(item.stat_mods for item in items)
    sources_mods.extend(affix.stat_mods for affix in affixes)

    tags: list[str] = list(hero.tags)
    for item in items:
        tags.extend(item.tags)
    for affix in affixes:
        tags.extend(affix.tags)

    resonances = _matched_resonances(tags, bundle)
    sources_mods.extend(r.stat_mods for r in resonances)

    final = _sum_mods(sources_mods)

    fixed_effects: list[FixedEffect] = []
    for item in items:
        fixed_effects.extend(item.fixed_effects)
    for affix in affixes:
        fixed_effects.extend(affix.fixed_effects)
    for res in resonances:
        fixed_effects.extend(res.fixed_effects)

    battle_start_statuses: list[StatusEffect] = []
    passive_tags: list[str] = []
    for fx in fixed_effects:
        if fx.kind == "battle_start_status":
            battle_start_statuses.append(
                StatusEffect(
                    id=fx.status_id, stacks=fx.stacks, duration=fx.duration
                )
            )
        elif fx.kind == "passive_tag":
            passive_tags.append(fx.tag)
            tags.append(fx.tag)

    return ResolvedBuild(
        hp=max(1, final.hp),
        mp=max(0, final.mp),
        speed=max(1, final.speed),
        attack=max(0, final.attack),
        defense=max(0, final.defense),
        power=max(0, final.power),
        tags=tuple(tags),
        items=items,
        affixes=affixes,
        resonances=resonances,
        battle_start_statuses=battle_start_statuses,
        passive_tags=tuple(passive_tags),
        hero_id=hero.id,
    )


def _matched_resonances(
    tag_list: list[str], bundle: ContentBundle
) -> tuple[ResonanceData, ...]:
    counts: dict[str, int] = {}
    for tag in tag_list:
        counts[tag] = counts.get(tag, 0) + 1
    matched: list[ResonanceData] = []
    for res in bundle.resonances.values():
        ok = all(counts.get(tag, 0) >= need for tag, need in res.required_tag_counts.items())
        if ok:
            matched.append(res)
    return tuple(matched)


def _sum_mods(mods: list[StatMods]) -> StatMods:
    return StatMods(
        hp=sum(m.hp for m in mods),
        mp=sum(m.mp for m in mods),
        speed=sum(m.speed for m in mods),
        attack=sum(m.attack for m in mods),
        defense=sum(m.defense for m in mods),
        power=sum(m.power for m in mods),
    )
