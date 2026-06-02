"""Combat-time data structures.

These dataclasses describe in-fight state. Content schema (`HeroData`,
`SkillData`, `EnemyData`) describes data on disk; the battle copies values
from there into mutable dataclasses below so the engine never mutates loaded
content.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ouro_agent.i18n import DEFAULT_LANGUAGE, log_text


@dataclass
class StatusEffect:
    id: str
    stacks: int
    duration: int

    def tick(self) -> bool:
        """Return True when the effect should be removed."""
        self.duration -= 1
        return self.duration <= 0


@dataclass
class SkillState:
    id: str
    display_name: str
    mp_cost: int
    cooldown: int
    target_rule: str
    cooldown_remaining: int = 0

    def is_ready(self, current_mp: int) -> bool:
        return self.cooldown_remaining == 0 and self.mp_cost <= current_mp


Side = Literal["hero", "enemy"]


@dataclass
class Unit:
    id: str
    name: str
    side: Side
    max_hp: int
    hp: int
    max_mp: int
    mp: int
    attack: int
    defense: int
    power: int
    speed: int
    atb: int = 0
    statuses: list[StatusEffect] = field(default_factory=list)

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def find_status(self, status_id: str) -> StatusEffect | None:
        for s in self.statuses:
            if s.id == status_id:
                return s
        return None

    def add_status(self, effect: StatusEffect) -> None:
        existing = self.find_status(effect.id)
        if existing is not None:
            existing.stacks += effect.stacks
            existing.duration = max(existing.duration, effect.duration)
            return
        self.statuses.append(effect)


@dataclass
class Hero(Unit):
    skills: list[SkillState] = field(default_factory=list)
    short_tag: str = "[----]"
    class_name: str = ""

    def find_skill(self, skill_id: str) -> SkillState | None:
        for s in self.skills:
            if s.id == skill_id:
                return s
        return None

    def tick_cooldowns(self) -> None:
        for s in self.skills:
            if s.cooldown_remaining > 0:
                s.cooldown_remaining -= 1


@dataclass
class Enemy(Unit):
    behavior_kind: str = "rule_basic"
    attack_chance: float = 1.0
    chant_damage: int = 0
    chant_charge_turns: int = 0
    chant_progress: int = 0
    short_glyph: str = "?"
    family_id: str = ""
    tier: str = "trace"


@dataclass
class BattleEvent:
    """A single observable event for trace and TUI consumption."""
    kind: str
    payload: dict


BattleResult = Literal["ongoing", "victory", "defeat", "timeout"]


@dataclass
class BattleState:
    seed: int
    tick: int
    hero: Hero
    enemies: list[Enemy]
    language: str = DEFAULT_LANGUAGE
    log: list[str] = field(default_factory=list)
    events: list[BattleEvent] = field(default_factory=list)
    result: BattleResult = "ongoing"

    def alive_enemies(self) -> list[Enemy]:
        return [e for e in self.enemies if e.is_alive]

    def all_units(self) -> list[Unit]:
        return [self.hero, *self.enemies]

    def push_log(self, key: str, *, max_lines: int = 8, **kwargs: object) -> None:
        text = log_text(key, self.language, **kwargs)
        self.log.append(text)
        if len(self.log) > max_lines:
            del self.log[: len(self.log) - max_lines]

    def emit(self, event_kind: str, **payload: object) -> None:
        self.events.append(BattleEvent(kind=event_kind, payload=dict(payload)))
