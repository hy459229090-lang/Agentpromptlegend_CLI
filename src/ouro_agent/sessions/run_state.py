"""Run state management for roguelike progression.

This module implements the core roguelike loop:
- Dungeon traversal
- Node selection (route choice)
- Battle execution
- Reward selection
- Shop interaction
- Build progression

Key classes:
- RunPhase: Current phase of the run
- RunState: Complete state of a run
- RunEngine: Orchestrates the entire run loop
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Optional

from ouro_agent.content.schema import (
    ContentBundle,
    DungeonData,
    NodeData,
    RewardChoice,
    ShopItem,
)
from ouro_agent.engine.build import ResolvedBuild, resolve_build


class RunPhase(Enum):
    """Current phase of the run.
    
    The run progresses through these phases in order:
    START → ROUTE_CHOICE → [NODE_ACTION] → [REWARD_CHOICE or SHOP] → ROUTE_CHOICE → ... → COMPLETE
    """
    START = auto()
    ROUTE_CHOICE = auto()
    NODE_ACTION = auto()
    REWARD_CHOICE = auto()
    SHOP = auto()
    REST = auto()
    EVENT = auto()
    COMPLETE = auto()
    DEAD = auto()


@dataclass
class RunState:
    """Complete state of a roguelike run.
    
    This class tracks everything needed to resume or replay a run:
    - Current dungeon, floor, and node
    - Hero state (HP, MP, build)
    - Resources (gold, xp)
    - Progression history
    """
    # Required fields (no defaults)
    run_id: str
    seed: int
    dungeon_id: str
    hero_id: str
    
    # Optional fields (with defaults)
    # Dungeon state
    current_floor_index: int = 0
    current_node_index: int = 0
    visited_node_ids: set[str] = field(default_factory=set)
    
    # Hero state
    item_ids: list[str] = field(default_factory=list)
    affix_ids: list[str] = field(default_factory=list)
    current_hp: int = 0
    current_mp: int = 0
    max_hp: int = 0
    max_mp: int = 0
    
    # Resources
    gold: int = 0
    xp: int = 0
    
    # Phase
    phase: RunPhase = RunPhase.START
    available_node_indices: list[int] = field(default_factory=list)
    current_choices: list[Any] = field(default_factory=list)
    chosen_choice_index: Optional[int] = None
    
    # Battle state (only valid during NODE_ACTION)
    battle_in_progress: bool = False
    battle_result: Optional[str] = None
    
    # History
    completed_node_ids: list[str] = field(default_factory=list)
    earned_gold_total: int = 0
    earned_xp_total: int = 0
    battles_won: int = 0
    battles_lost: int = 0
    
    def resolved_build(self, bundle: ContentBundle) -> ResolvedBuild:
        """Get the current resolved build for the hero."""
        hero = bundle.get_hero(self.hero_id)
        return resolve_build(
            hero,
            bundle,
            item_ids=tuple(self.item_ids) if self.item_ids else None,
            affix_ids=tuple(self.affix_ids) if self.affix_ids else None,
        )
    
    def current_dungeon(self, bundle: ContentBundle) -> DungeonData:
        """Get the current dungeon data."""
        return bundle.dungeons[self.dungeon_id]
    
    def current_floor(self, bundle: ContentBundle) -> Any:
        """Get the current floor data."""
        dungeon = self.current_dungeon(bundle)
        return dungeon.floors[self.current_floor_index]
    
    def current_node(self, bundle: ContentBundle) -> NodeData:
        """Get the current node data."""
        floor = self.current_floor(bundle)
        node_id = floor.nodes[self.current_node_index]
        return bundle.nodes[node_id]
    
    def get_available_nodes(self, bundle: ContentBundle) -> list[tuple[int, NodeData]]:
        """Get available nodes for route choice.
        
        Returns:
            List of (node_index, node_data) tuples for available nodes.
        """
        floor = self.current_floor(bundle)
        available = []
        for idx, node_id in enumerate(floor.nodes):
            if node_id not in self.visited_node_ids:
                node = bundle.nodes[node_id]
                available.append((idx, node))
        return available
    
    def is_floor_complete(self) -> bool:
        """Check if all nodes on the current floor are completed."""
        return False  # TODO: Implement based on floor type
    
    def has_next_floor(self, bundle: ContentBundle) -> bool:
        """Check if there is a next floor."""
        dungeon = self.current_dungeon(bundle)
        return self.current_floor_index < len(dungeon.floors) - 1
    
    def advance_to_next_floor(self, bundle: ContentBundle) -> bool:
        """Advance to the next floor.
        
        Returns:
            True if advanced, False if already on the last floor.
        """
        if not self.has_next_floor(bundle):
            return False
        self.current_floor_index += 1
        self.current_node_index = 0
        self.phase = RunPhase.ROUTE_CHOICE
        return True
    
    def select_node(self, node_index: int) -> None:
        """Select a node for the current floor (during ROUTE_CHOICE phase)."""
        if self.phase != RunPhase.ROUTE_CHOICE:
            raise RuntimeError(f"Cannot select node in phase: {self.phase}")
        self.current_node_index = node_index
        self.phase = RunPhase.NODE_ACTION
    
    def start_battle(self) -> None:
        """Mark battle as started."""
        self.battle_in_progress = True
    
    def end_battle(self, result: str, hp_remaining: int, mp_remaining: int) -> None:
        """End the battle and update state.
        
        Args:
            result: 'victory', 'defeat', or 'timeout'
            hp_remaining: Hero's remaining HP
            mp_remaining: Hero's remaining MP
        """
        self.battle_in_progress = False
        self.battle_result = result
        self.current_hp = hp_remaining
        self.current_mp = mp_remaining
        
        node_id = None  # Will be set from bundle
        
        if result == "victory":
            self.battles_won += 1
            # Node will be marked as visited when reward is chosen
        elif result == "defeat":
            self.battles_lost += 1
            self.phase = RunPhase.DEAD
        else:  # timeout
            self.battles_lost += 1
            self.phase = RunPhase.DEAD
    
    def add_rewards(self, gold: int, xp: int) -> None:
        """Add rewards from a battle."""
        self.gold += gold
        self.xp += xp
        self.earned_gold_total += gold
        self.earned_xp_total += xp
    
    def set_reward_choices(self, choices: list[RewardChoice]) -> None:
        """Set the available reward choices after a victory."""
        self.current_choices = choices
        self.phase = RunPhase.REWARD_CHOICE
    
    def choose_reward(self, choice_index: int, bundle: ContentBundle) -> None:
        """Choose a reward and apply it.
        
        Args:
            choice_index: Index of the chosen reward
            bundle: Content bundle for validation
        """
        if self.phase != RunPhase.REWARD_CHOICE:
            raise RuntimeError(f"Cannot choose reward in phase: {self.phase}")
        
        choice = self.current_choices[choice_index]
        self.chosen_choice_index = choice_index
        
        # Apply the reward
        if choice.type == "item":
            if choice.item_id:
                self.item_ids.append(choice.item_id)
        elif choice.type == "affix":
            if choice.affix_id:
                self.affix_ids.append(choice.affix_id)
        elif choice.type == "codex":
            # Codex progress - TODO: Implement codex tracking
            pass
        elif choice.type == "gold":
            self.gold += choice.gold or 0
        elif choice.type == "heal":
            heal_amount = choice.heal_percent or 0
            if heal_amount > 0:
                actual_heal = int(self.max_hp * heal_amount / 100)
                self.current_hp = min(self.max_hp, self.current_hp + actual_heal)
        
        # Mark current node as visited
        floor = self.current_floor(bundle)
        node_id = floor.nodes[self.current_node_index]
        self.visited_node_ids.add(node_id)
        self.completed_node_ids.append(node_id)
        
        # Check if there are more nodes on this floor
        available = self.get_available_nodes(bundle)
        if available:
            # More nodes available - go back to route choice
            self.phase = RunPhase.ROUTE_CHOICE
        elif self.has_next_floor(bundle):
            # No more nodes, but has next floor
            self.advance_to_next_floor(bundle)
        else:
            # No more floors - run complete
            self.phase = RunPhase.COMPLETE
    
    def set_shop_items(self, items: list[ShopItem]) -> None:
        """Set the available shop items."""
        self.current_choices = items
        self.phase = RunPhase.SHOP
    
    def can_afford(self, item: ShopItem) -> bool:
        """Check if hero can afford a shop item."""
        return self.gold >= (item.price or 0)
    
    def buy_shop_item(self, choice_index: int, bundle: ContentBundle) -> bool:
        """Buy a shop item.
        
        Args:
            choice_index: Index of the item to buy
            bundle: Content bundle for validation
        
        Returns:
            True if purchased successfully, False if cannot afford.
        """
        if self.phase != RunPhase.SHOP:
            raise RuntimeError(f"Cannot buy shop item in phase: {self.phase}")
        
        item = self.current_choices[choice_index]
        price = item.price or 0
        
        if not self.can_afford(item):
            return False
        
        # Deduct gold
        self.gold -= price
        
        # Apply the item
        if item.type == "item":
            if item.item_id:
                self.item_ids.append(item.item_id)
        elif item.type == "affix":
            if item.affix_id:
                self.affix_ids.append(item.affix_id)
        elif item.type == "strategy":
            # Strategy style - TODO: Implement strategy tracking
            pass
        elif item.type == "heal":
            heal_percent = item.heal_percent or 0
            if heal_percent > 0:
                actual_heal = int(self.max_hp * heal_percent / 100)
                self.current_hp = min(self.max_hp, self.current_hp + actual_heal)
        
        return True
    
    def leave_shop(self, bundle: ContentBundle) -> None:
        """Leave the shop and proceed to next phase."""
        # Mark current node as visited
        floor = self.current_floor(bundle)
        node_id = floor.nodes[self.current_node_index]
        self.visited_node_ids.add(node_id)
        self.completed_node_ids.append(node_id)
        
        # Check if there are more nodes on this floor
        available = self.get_available_nodes(bundle)
        if available:
            # More nodes available - go back to route choice
            self.phase = RunPhase.ROUTE_CHOICE
        elif self.has_next_floor(bundle):
            # No more nodes, but has next floor
            self.advance_to_next_floor(bundle)
        else:
            # No more floors - run complete
            self.phase = RunPhase.COMPLETE
    
    def set_rest_phase(self) -> None:
        """Enter rest phase."""
        self.phase = RunPhase.REST
    
    def apply_rest(self, heal_percent: int = 30, restore_full_mp: bool = True) -> None:
        """Apply rest benefits.
        
        Args:
            heal_percent: Percentage of max HP to heal (0-100)
            restore_full_mp: Whether to restore MP to full
        """
        if self.phase != RunPhase.REST:
            raise RuntimeError(f"Cannot apply rest in phase: {self.phase}")
        
        if heal_percent > 0:
            heal_amount = int(self.max_hp * heal_percent / 100)
            self.current_hp = min(self.max_hp, self.current_hp + heal_amount)
        
        if restore_full_mp:
            self.current_mp = self.max_mp
    
    def leave_rest(self, bundle: ContentBundle) -> None:
        """Leave the rest site and proceed to next phase."""
        # Mark current node as visited
        floor = self.current_floor(bundle)
        node_id = floor.nodes[self.current_node_index]
        self.visited_node_ids.add(node_id)
        self.completed_node_ids.append(node_id)
        
        # Check if there are more nodes on this floor
        available = self.get_available_nodes(bundle)
        if available:
            # More nodes available - go back to route choice
            self.phase = RunPhase.ROUTE_CHOICE
        elif self.has_next_floor(bundle):
            # No more nodes, but has next floor
            self.advance_to_next_floor(bundle)
        else:
            # No more floors - run complete
            self.phase = RunPhase.COMPLETE
    
    def set_event_choices(self, choices: list[Any]) -> None:
        """Set the available event choices."""
        self.current_choices = choices
        self.phase = RunPhase.EVENT
    
    def choose_event(self, choice_index: int, bundle: ContentBundle) -> None:
        """Choose an event option and apply its effects.
        
        Args:
            choice_index: Index of the chosen option
            bundle: Content bundle for validation
        """
        if self.phase != RunPhase.EVENT:
            raise RuntimeError(f"Cannot choose event in phase: {self.phase}")
        
        choice = self.current_choices[choice_index]
        self.chosen_choice_index = choice_index
        
        # Apply the event choice effects
        # Event choices can have similar structure to RewardChoice
        if hasattr(choice, "type"):
            if choice.type == "item" and hasattr(choice, "item_id") and choice.item_id:
                self.item_ids.append(choice.item_id)
            elif choice.type == "affix" and hasattr(choice, "affix_id") and choice.affix_id:
                self.affix_ids.append(choice.affix_id)
            elif choice.type == "gold" and hasattr(choice, "gold") and choice.gold:
                self.gold += choice.gold or 0
            elif choice.type == "heal" and hasattr(choice, "heal_percent") and choice.heal_percent:
                heal_percent = choice.heal_percent or 0
                if heal_percent > 0:
                    actual_heal = int(self.max_hp * heal_percent / 100)
                    self.current_hp = min(self.max_hp, self.current_hp + actual_heal)
        
        # Mark current node as visited
        floor = self.current_floor(bundle)
        node_id = floor.nodes[self.current_node_index]
        self.visited_node_ids.add(node_id)
        self.completed_node_ids.append(node_id)
        
        # Check if there are more nodes on this floor
        available = self.get_available_nodes(bundle)
        if available:
            # More nodes available - go back to route choice
            self.phase = RunPhase.ROUTE_CHOICE
        elif self.has_next_floor(bundle):
            # No more nodes, but has next floor
            self.advance_to_next_floor(bundle)
        else:
            # No more floors - run complete
            self.phase = RunPhase.COMPLETE


def create_run_state(
    run_id: str,
    seed: int,
    hero_id: str,
    dungeon_id: str,
    bundle: ContentBundle,
) -> RunState:
    """Create a new run state.
    
    Args:
        run_id: Unique run identifier
        seed: Random seed
        hero_id: Hero to play
        dungeon_id: Dungeon to explore
        bundle: Content bundle
    
    Returns:
        Initialized RunState
    """
    hero = bundle.get_hero(hero_id)
    dungeon = bundle.dungeons[dungeon_id]
    
    # Get initial build to determine max HP/MP
    build = resolve_build(hero, bundle)
    
    state = RunState(
        run_id=run_id,
        seed=seed,
        dungeon_id=dungeon_id,
        current_floor_index=0,
        current_node_index=0,
        hero_id=hero_id,
        item_ids=list(hero.default_build.items),
        affix_ids=list(hero.default_build.affixes),
        current_hp=build.hp,
        current_mp=build.mp,
        max_hp=build.hp,
        max_mp=build.mp,
        gold=0,
        xp=0,
        phase=RunPhase.ROUTE_CHOICE,
    )
    
    return state
