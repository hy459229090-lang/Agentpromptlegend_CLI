"""Tests for context window progression."""
import pytest

from ouro_agent.sessions import ContextProgress, context_level_label, context_slot_label
from ouro_agent.tui.screens import render_context_window
from ouro_agent.i18n import visual_width


class TestContextProgress:
    """Tests for ContextProgress data class."""
    
    def test_initial_context(self):
        """Test initial context state."""
        context = ContextProgress()
        assert context.level == 1
        assert context.xp == 0
        assert context.strategy_slots == 1
        assert context.codex_slots == 1
        assert context.memory_echo == 340
        assert context.prompt_edit_budget == 1
        assert context.build_hint_slots == 1
        assert context.unlocked_levels == {1}
    
    def test_xp_for_next_level(self):
        """Test XP needed for next level."""
        context = ContextProgress()
        assert context.xp_for_next_level == 20
        assert context.next_level == 2
        assert not context.is_max_level
    
    def test_xp_for_next_level_at_max(self):
        """Test XP at max level."""
        context = ContextProgress(level=6, xp=200)
        assert context.xp_for_next_level == 0
        assert context.next_level is None
        assert context.is_max_level
    
    def test_next_level_reward(self):
        """Test next level reward description."""
        context = ContextProgress()
        assert "Strategy Slot" in context.next_level_reward
        
        context2 = ContextProgress(level=2, xp=20)
        assert "Codex Slot" in context2.next_level_reward
    
    def test_add_xp_no_level_up(self):
        """Test adding XP without level up."""
        context = ContextProgress()
        new_levels = context.add_xp(10)
        assert context.xp == 10
        assert context.level == 1
        assert new_levels == []
    
    def test_add_xp_level_up_once(self):
        """Test adding XP to level up once."""
        context = ContextProgress()
        new_levels = context.add_xp(20)
        assert context.xp == 20
        assert context.level == 2
        assert new_levels == [2]
        assert context.strategy_slots == 2
    
    def test_add_xp_level_up_multiple(self):
        """Test adding XP to level up multiple times."""
        context = ContextProgress()
        new_levels = context.add_xp(45)
        assert context.xp == 45
        assert context.level == 3
        assert new_levels == [2, 3]
        assert context.strategy_slots == 2
        assert context.codex_slots == 2
    
    def test_add_xp_up_to_level_4(self):
        """Test adding XP up to level 4."""
        context = ContextProgress()
        new_levels = context.add_xp(75)
        assert context.xp == 75
        assert context.level == 4
        assert new_levels == [2, 3, 4]
        assert context.strategy_slots == 2
        assert context.codex_slots == 2
        assert context.memory_echo == 460
    
    def test_add_xp_up_to_level_5(self):
        """Test adding XP up to level 5."""
        context = ContextProgress()
        new_levels = context.add_xp(110)
        assert context.xp == 110
        assert context.level == 5
        assert new_levels == [2, 3, 4, 5]
        assert context.prompt_edit_budget == 2
    
    def test_add_xp_up_to_level_6(self):
        """Test adding XP up to level 6."""
        context = ContextProgress()
        new_levels = context.add_xp(150)
        assert context.xp == 150
        assert context.level == 6
        assert new_levels == [2, 3, 4, 5, 6]
        assert context.build_hint_slots == 2
    
    def test_add_xp_past_max_level(self):
        """Test adding XP past max level."""
        context = ContextProgress(level=6, xp=150)
        new_levels = context.add_xp(100)
        assert context.xp == 250
        assert context.level == 6
        assert new_levels == []
    
    def test_to_dict(self):
        """Test serialization."""
        context = ContextProgress(level=3, xp=50)
        data = context.to_dict()
        assert data["level"] == 3
        assert data["xp"] == 50
        assert data["strategy_slots"] == 2
        assert data["codex_slots"] == 2
        assert 1 in data["unlocked_levels"]
        assert 2 in data["unlocked_levels"]
        assert 3 in data["unlocked_levels"]
    
    def test_from_dict(self):
        """Test deserialization."""
        raw = {
            "level": 4,
            "xp": 80,
            "strategy_slots": 2,
            "codex_slots": 2,
            "memory_echo": 460,
            "prompt_edit_budget": 1,
            "build_hint_slots": 1,
            "unlocked_levels": [1, 2, 3, 4],
        }
        context = ContextProgress.from_dict(raw)
        assert context.level == 4
        assert context.xp == 80
        assert context.strategy_slots == 2
        assert context.codex_slots == 2
        assert context.memory_echo == 460
        assert context.unlocked_levels == {1, 2, 3, 4}


class TestContextLabels:
    """Tests for context labels."""
    
    @pytest.mark.parametrize("level,expected", [
        (1, "Lv.1 新手"),
        (2, "Lv.2 学徒"),
        (3, "Lv.3 熟手"),
        (4, "Lv.4 专家"),
        (5, "Lv.5 大师"),
        (6, "Lv.6 传奇"),
    ])
    def test_context_level_label_zh(self, level, expected):
        """Test context level labels in Chinese."""
        assert context_level_label(level, lang="zh") == expected
    
    @pytest.mark.parametrize("level,expected", [
        (1, "Lv.1 Novice"),
        (2, "Lv.2 Apprentice"),
        (3, "Lv.3 Adept"),
        (4, "Lv.4 Expert"),
        (5, "Lv.5 Master"),
        (6, "Lv.6 Legend"),
    ])
    def test_context_level_label_en(self, level, expected):
        """Test context level labels in English."""
        assert context_level_label(level, lang="en") == expected
    
    @pytest.mark.parametrize("slot_type,expected", [
        ("strategy", "策略"),
        ("codex", "图鉴"),
        ("memory", "记忆"),
        ("prompt_edit", "Prompt 编辑"),
    ])
    def test_context_slot_label_zh(self, slot_type, expected):
        """Test context slot labels in Chinese."""
        assert context_slot_label(slot_type, lang="zh") == expected
    
    @pytest.mark.parametrize("slot_type,expected", [
        ("strategy", "Strategy"),
        ("codex", "Codex"),
        ("memory", "Memory"),
        ("prompt_edit", "Prompt Edit"),
    ])
    def test_context_slot_label_en(self, slot_type, expected):
        """Test context slot labels in English."""
        assert context_slot_label(slot_type, lang="en") == expected


class TestRenderContextWindow:
    """Tests for render_context_window function."""
    
    def test_render_context_default(self):
        """Test rendering default context window."""
        output = render_context_window(lang="zh")
        assert "上下文窗口" in output
        assert "Lv.1 新手" in output
        assert "策略: 1/3" in output
        assert "图鉴: 1/2" in output
        assert "记忆: 340/500" in output
        assert "Prompt 编辑: 1/2" in output
        assert "Build 提示: 1/2" in output
        assert "CONTEXT GROWTH BOARD" in output
        assert "[LEVEL] Lv.1 新手 / 0/20 XP" in output
        assert "[STRATEGY] 1 槽 / 驾驶模式与路线策略" in output
        assert "[CODEX] 1 槽 / 怪物知识注入" in output
        assert "[MEMORY] 340 Echo / 长期战斗记忆" in output
        assert "[PROMPT] 1 次 / 局内 Prompt 修正" in output
        assert "[BUILD] 1 槽 / 构筑提示" in output
        assert "Strategy Slot" in output
        assert "+" in output
        assert "-" in output
        assert "|" in output
        assert all(visual_width(line) <= 56 for line in output.splitlines())
    
    def test_render_context_level_3(self):
        """Test rendering context window at level 3."""
        context = ContextProgress(level=3, xp=50)
        output = render_context_window(context, lang="zh")
        assert "Lv.3 熟手" in output
        assert "策略: 2/3" in output
        assert "图鉴: 2/2" in output
        assert "Memory Echo" in output
    
    def test_render_context_max_level(self):
        """Test rendering context window at max level."""
        context = ContextProgress(level=6, xp=200)
        output = render_context_window(context, lang="zh")
        assert "Lv.6 传奇" in output
        assert "已满级" in output
    
    def test_render_context_en(self):
        """Test rendering context window in English."""
        output = render_context_window(lang="en")
        assert "CONTEXT WINDOW" in output
        assert "Lv.1 Novice" in output
        assert "Strategy: 1/3" in output
        assert "Codex: 1/2" in output
        assert "Memory: 340/500" in output
        assert "Prompt Edit: 1/2" in output
        assert "Build Hint: 1/2" in output
        assert "CONTEXT GROWTH BOARD" in output
        assert "[STRATEGY] 1 slot(s) / pilot and route plans" in output
        assert "[CODEX] 1 slot(s) / monster intel injected" in output
        assert "[PROMPT] 1 edit(s) / mid-run prompt repair" in output
        assert "[BUILD] 1 slot(s) / build hint feed" in output
        assert "Next:" in output
        assert "XP" in output
        assert all(visual_width(line) <= 56 for line in output.splitlines())
