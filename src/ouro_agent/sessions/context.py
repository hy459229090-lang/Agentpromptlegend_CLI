"""Context window progression for AI agent growth.

This module implements the context growth system from G07:
- Level/XP system
- Strategy, Codex, Memory, and Prompt edit slots
- Level up choices
- Context window UI display
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


LEVEL_XP_THRESHOLDS = {
    1: 0,
    2: 20,
    3: 45,
    4: 75,
    5: 110,
    6: 150,
}

LEVEL_REWARDS = {
    1: {"description": "Starting context"},
    2: {"reward": "strategy_slot", "amount": 1, "description": "Strategy Slot +1"},
    3: {"reward": "codex_slot", "amount": 1, "description": "Codex Slot +1"},
    4: {"reward": "memory_echo", "amount": 120, "description": "Memory Echo +120"},
    5: {"reward": "prompt_edit", "amount": 1, "description": "Prompt Edit Budget +1"},
    6: {"reward": "build_hint", "amount": 1, "description": "Build Hint Slot +1"},
}

DEFAULT_CONTEXT_CONFIG = {
    "max_level": 6,
    "strategy_slots_max": 3,
    "codex_slots_max": 2,
    "memory_echo_max": 500,
    "prompt_edit_budget_max": 2,
    "build_hint_slots_max": 2,
}


@dataclass
class ContextProgress:
    """Context window progression tracking.
    
    Tracks the player's AI agent context growth across a run.
    """
    level: int = 1
    xp: int = 0
    strategy_slots: int = 1
    codex_slots: int = 1
    memory_echo: int = 340
    prompt_edit_budget: int = 1
    build_hint_slots: int = 1
    unlocked_levels: set[int] = field(default_factory=lambda: {1})
    
    def __post_init__(self) -> None:
        """Ensure unlocked levels have their rewards applied.
        
        When creating a ContextProgress from a saved state, ensure
        all unlocked level rewards are applied.
        """
        for lv in range(1, self.level + 1):
            self.unlocked_levels.add(lv)
        
        object.__setattr__(self, "strategy_slots", 1)
        object.__setattr__(self, "codex_slots", 1)
        object.__setattr__(self, "memory_echo", 340)
        object.__setattr__(self, "prompt_edit_budget", 1)
        object.__setattr__(self, "build_hint_slots", 1)
        
        for lv in sorted(self.unlocked_levels):
            if lv > 1:
                self._apply_level_reward(lv)
    
    @property
    def xp_for_next_level(self) -> int:
        """XP needed for next level."""
        if self.level >= 6:
            return 0
        return LEVEL_XP_THRESHOLDS[self.level + 1] - self.xp
    
    @property
    def next_level(self) -> int | None:
        """Next level number, or None if max level."""
        if self.level >= 6:
            return None
        return self.level + 1
    
    @property
    def next_level_reward(self) -> str:
        """Description of reward for next level."""
        if self.level >= 6:
            return "MAX LEVEL"
        next_lv = self.level + 1
        return LEVEL_REWARDS.get(next_lv, {}).get("description", "Unknown reward")
    
    @property
    def is_max_level(self) -> bool:
        """Whether at max level."""
        return self.level >= 6
    
    def add_xp(self, amount: int) -> list[int]:
        """Add XP and return any new levels unlocked.
        
        Args:
            amount: XP to add
            
        Returns:
            List of level numbers that were newly unlocked
        """
        self.xp += amount
        new_levels = []
        
        while True:
            next_lv = self.level + 1
            if next_lv > 6:
                break
            if next_lv in self.unlocked_levels:
                self.level = next_lv
                continue
            if self.xp >= LEVEL_XP_THRESHOLDS.get(next_lv, 999999):
                self.level = next_lv
                self.unlocked_levels.add(next_lv)
                self._apply_level_reward(next_lv)
                new_levels.append(next_lv)
            else:
                break
        
        return new_levels
    
    def _apply_level_reward(self, level: int) -> None:
        """Apply the reward for reaching a level."""
        reward = LEVEL_REWARDS.get(level, {})
        reward_type = reward.get("reward")
        amount = reward.get("amount", 0)
        
        if reward_type == "strategy_slot":
            self.strategy_slots += amount
        elif reward_type == "codex_slot":
            self.codex_slots += amount
        elif reward_type == "memory_echo":
            self.memory_echo += amount
        elif reward_type == "prompt_edit":
            self.prompt_edit_budget += amount
        elif reward_type == "build_hint":
            self.build_hint_slots += amount
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "level": self.level,
            "xp": self.xp,
            "strategy_slots": self.strategy_slots,
            "codex_slots": self.codex_slots,
            "memory_echo": self.memory_echo,
            "prompt_edit_budget": self.prompt_edit_budget,
            "build_hint_slots": self.build_hint_slots,
            "unlocked_levels": list(self.unlocked_levels),
        }
    
    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "ContextProgress":
        """Deserialize from dict."""
        return cls(
            level=int(raw.get("level", 1)),
            xp=int(raw.get("xp", 0)),
            strategy_slots=int(raw.get("strategy_slots", 1)),
            codex_slots=int(raw.get("codex_slots", 1)),
            memory_echo=int(raw.get("memory_echo", 340)),
            prompt_edit_budget=int(raw.get("prompt_edit_budget", 1)),
            build_hint_slots=int(raw.get("build_hint_slots", 1)),
            unlocked_levels=set(raw.get("unlocked_levels", [1])),
        )


def context_level_label(level: int, lang: str = "zh") -> str:
    """Get display label for a context level."""
    labels = {
        1: {"en": "Lv.1 Novice", "zh": "Lv.1 新手"},
        2: {"en": "Lv.2 Apprentice", "zh": "Lv.2 学徒"},
        3: {"en": "Lv.3 Adept", "zh": "Lv.3 熟手"},
        4: {"en": "Lv.4 Expert", "zh": "Lv.4 专家"},
        5: {"en": "Lv.5 Master", "zh": "Lv.5 大师"},
        6: {"en": "Lv.6 Legend", "zh": "Lv.6 传奇"},
    }
    return labels.get(level, {}).get(lang, f"Lv.{level}")


def context_slot_label(slot_type: str, lang: str = "zh") -> str:
    """Get display label for a context slot type."""
    labels = {
        "strategy": {"en": "Strategy", "zh": "策略"},
        "codex": {"en": "Codex", "zh": "图鉴"},
        "memory": {"en": "Memory", "zh": "记忆"},
        "prompt_edit": {"en": "Prompt Edit", "zh": "Prompt 编辑"},
        "build_hint": {"en": "Build Hint", "zh": "Build 提示"},
    }
    return labels.get(slot_type, {}).get(lang, slot_type)
