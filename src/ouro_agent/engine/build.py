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

    def equipment_summary(self, language: str = "en") -> str:
        items = ", ".join(item.display_name.get(language) for item in self.items) or "-"
        affixes = ", ".join(affix.display_name.get(language) for affix in self.affixes) or "-"
        res = (
            ", ".join(r.display_name.get(language) for r in self.resonances)
            or "-"
        )
        return f"items: {items} | affixes: {affixes} | resonance: {res}"


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
