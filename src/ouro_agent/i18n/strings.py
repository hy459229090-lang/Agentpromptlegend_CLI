"""Localized strings for UI labels, engine log lines, and mock narration.

* ``label(key, lang)``       — short UI labels (e.g. HERO, ENEMIES).
* ``log_text(key, lang, **)`` — combat log templates resolved at push time.
* ``narration_text(key, lang, **)`` — mock provider narration templates.
* ``visual_width(s)``        — east-asian-width-aware text width in columns.
* ``pad_right(s, width)``    — right-pad to a visual column width.

Falling back across languages keeps render code defensive: missing zh entries
fall back to en. Missing en entries fall back to the key itself so coding
errors are visible but never crash the run.
"""
from __future__ import annotations

import unicodedata
from typing import Any

SUPPORTED_LANGUAGES: tuple[str, ...] = ("en", "zh")
DEFAULT_LANGUAGE: str = "zh"


_LABELS: dict[str, dict[str, str]] = {
    "title": {"en": "OURO AGENT", "zh": "暗影代理 Ouro Agent"},
    "hero": {"en": "HERO", "zh": "英雄"},
    "enemies": {"en": "ENEMIES", "zh": "敌人"},
    "model_turn": {"en": "MODEL TURN", "zh": "模型行动"},
    "log": {"en": "LOG", "zh": "战斗日志"},
    "battle_complete": {"en": "BATTLE COMPLETE", "zh": "战斗结束"},
    "result": {"en": "Result", "zh": "结果"},
    "trace_label": {"en": "Trace", "zh": "Trace"},
    "echo_cost": {"en": "Echo Cost", "zh": "回响代价"},
    "ritual_time": {"en": "Ritual Time", "zh": "仪式耗时"},
    "tokens_unit": {"en": "tokens", "zh": "tokens"},
    "trace_local": {"en": "Trace: local", "zh": "Trace: 本地"},
    "speed": {"en": "Speed", "zh": "速率"},
    "seed": {"en": "Seed", "zh": "种子"},
    "provider_label": {"en": "Provider", "zh": "供应商"},
    "down": {"en": "(down)", "zh": "(倒下)"},
    "judge_valid": {"en": "valid", "zh": "通过"},
    "judge_fallback": {"en": "fallback", "zh": "降级"},
    "no_judge": {"en": "(no judge result)", "zh": "(无裁判结果)"},
    "fallback_label": {"en": "fallback", "zh": "降级原因"},
    "status_none": {"en": "-", "zh": "-"},
    "status_label": {"en": "Status", "zh": "状态"},
    "action_label": {"en": "Action", "zh": "行动"},
    "judge_label": {"en": "Judge", "zh": "裁判"},
    "no_events": {"en": "(no events yet)", "zh": "(暂无事件)"},
    "no_enemies": {"en": "  (none)", "zh": "  (无)"},
    "awaiting": {"en": "(awaiting first action)", "zh": "(等待第一次行动)"},
    "result_victory": {"en": "victory", "zh": "胜利"},
    "result_defeat": {"en": "defeat", "zh": "失败"},
    "result_timeout": {"en": "timeout", "zh": "超时"},
    "result_ongoing": {"en": "ongoing", "zh": "进行中"},
    "config_title": {"en": "MODEL PROVIDER", "zh": "模型供应商配置"},
    "config_current": {"en": "Current", "zh": "当前配置"},
    "config_path": {"en": "Config file", "zh": "配置文件"},
    "config_field_provider": {"en": "provider", "zh": "供应商"},
    "config_field_model": {"en": "model", "zh": "模型"},
    "config_field_api_key_env": {"en": "api_key_env", "zh": "API key 环境变量名"},
    "config_field_api_key_value": {"en": "api_key_value", "zh": "API key 值"},
    "config_field_base_url": {"en": "base_url", "zh": "API 地址"},
    "config_field_api_version": {"en": "api_version", "zh": "API 版本"},
    "config_field_timeout": {"en": "timeout (s)", "zh": "超时 (秒)"},
    "config_field_retries": {"en": "retries", "zh": "重试次数"},
    "config_field_trace_level": {"en": "trace_level", "zh": "trace 级别"},
    "config_field_unicode_mode": {"en": "unicode_mode", "zh": "Unicode 模式"},
    "config_field_language": {"en": "language", "zh": "语言"},
    "config_api_key_value_note": {
        "en": "(not stored; read from env at runtime)",
        "zh": "(不保存，运行时从环境变量读取)",
    },
    "config_api_key_env_unset": {"en": "(unset)", "zh": "(未设置)"},
    "provider_line_mock": {
        "en": "[1] mock                  no API key required",
        "zh": "[1] mock                  无需 API key",
    },
    "provider_line_openai": {
        "en": "[2] openai                env: OPENAI_API_KEY",
        "zh": "[2] openai                环境变量: OPENAI_API_KEY",
    },
    "provider_line_anthropic": {
        "en": "[3] anthropic             env: ANTHROPIC_API_KEY",
        "zh": "[3] anthropic             环境变量: ANTHROPIC_API_KEY",
    },
    "provider_line_compatible": {
        "en": "[4] openai-compatible     env + base_url required",
        "zh": "[4] openai-compatible     需要环境变量 + base_url",
    },
    "content_validation_title": {
        "en": "CONTENT VALIDATION",
        "zh": "内容数据校验",
    },
    "content_heroes": {"en": "heroes", "zh": "英雄"},
    "content_skills": {"en": "skills", "zh": "技能"},
    "content_enemies": {"en": "enemies", "zh": "敌人"},
    "content_status": {"en": "status", "zh": "状态"},
    "content_status_ok": {"en": "OK", "zh": "OK"},
    "content_status_fail": {"en": "FAIL", "zh": "失败"},
    "content_error": {"en": "error", "zh": "错误"},
    "floor_label_default": {
        "en": "EMBER CRYPT :: FLOOR 1",
        "zh": "灰烬墓室 :: 第 1 层",
    },
    "enemy_actor_acts": {
        "en": "Enemy {actor_id} acts: {kind}",
        "zh": "敌人 {actor_id} 行动: {kind}",
    },
    "hero_list_title": {"en": "CHOOSE HERO", "zh": "选择英雄"},
    "hero_card_title": {"en": "HERO CARD", "zh": "英雄详情"},
    "hero_card_class": {"en": "Class", "zh": "职业"},
    "hero_card_tags": {"en": "Tags", "zh": "标签"},
    "hero_card_stats": {"en": "Stats", "zh": "属性"},
    "hero_card_skills": {"en": "Skills", "zh": "技能"},
    "hero_card_items": {"en": "Items", "zh": "装备"},
    "hero_card_affixes": {"en": "Affixes", "zh": "词条"},
    "hero_card_resonances": {"en": "Resonances", "zh": "羁绊"},
    "hero_card_prompt": {"en": "Default Prompt", "zh": "默认 Prompt"},
    "hero_card_none": {"en": "(none)", "zh": "(无)"},
    "content_items": {"en": "items", "zh": "装备"},
    "content_affixes": {"en": "affixes", "zh": "词条"},
    "content_resonances": {"en": "resonances", "zh": "羁绊"},
    "battle_report_title": {"en": "BATTLE REPORT", "zh": "战斗报告"},
    "battle_report_duration": {"en": "Duration", "zh": "持续时间"},
    "battle_report_actions": {"en": "Hero action mix", "zh": "英雄行动构成"},
    "battle_report_skills": {"en": "Skill usage", "zh": "技能使用"},
    "battle_report_basic_skill_ratio": {
        "en": "Basic:Skill ratio",
        "zh": "普攻:技能比例",
    },
    "battle_report_damage_dealt": {"en": "Damage dealt", "zh": "造成伤害"},
    "battle_report_damage_taken": {"en": "Damage taken", "zh": "承受伤害"},
    "battle_report_fallbacks": {"en": "Fallbacks", "zh": "降级次数"},
    "battle_report_death_reason": {"en": "Death reason", "zh": "失败原因"},
    "battle_report_build_note": {"en": "Build note", "zh": "Build 备注"},
    "battle_report_build_note_value": {
        "en": "MVP build resolver active; rewards and codex notes are not unlocked yet.",
        "zh": "MVP 构筑结算已启用；奖励与图鉴记录尚未解锁。",
    },
    "battle_report_none": {"en": "(none)", "zh": "(无)"},
    "battle_report_unknown": {"en": "(unknown)", "zh": "(未知)"},
    # Run / Dungeon
    "run_title": {"en": "ROGUE RUN", "zh": "肉鸽运行"},
    "run_dungeon": {"en": "Dungeon", "zh": "副本"},
    "run_floor": {"en": "Floor", "zh": "楼层"},
    "run_gold": {"en": "Gold", "zh": "金币"},
    "run_xp": {"en": "XP", "zh": "经验"},
    "run_battles_won": {"en": "Battles Won", "zh": "胜利场次"},
    "run_battles_lost": {"en": "Battles Lost", "zh": "失败场次"},
    # Route Choice
    "route_choice_title": {"en": "CHOOSE YOUR PATH", "zh": "选择你的道路"},
    "route_choice_prompt": {"en": "Select a node (enter number)", "zh": "选择一个节点（输入编号）"},
    "route_node_normal": {"en": "Combat", "zh": "战斗"},
    "route_node_elite": {"en": "Elite Combat", "zh": "精英战斗"},
    "route_node_boss": {"en": "Boss", "zh": "Boss"},
    "route_node_shop": {"en": "Shop", "zh": "商店"},
    "route_node_event": {"en": "Event", "zh": "事件"},
    "route_node_rest": {"en": "Rest", "zh": "休息"},
    "route_risk_low": {"en": "Risk: Low", "zh": "风险：低"},
    "route_risk_medium": {"en": "Risk: Medium", "zh": "风险：中"},
    "route_risk_high": {"en": "Risk: High", "zh": "风险：高"},
    "route_risk_safe": {"en": "Risk: Safe", "zh": "风险：安全"},
    # Reward Choice
    "reward_choice_title": {"en": "CHOOSE YOUR REWARD", "zh": "选择你的奖励"},
    "reward_choice_prompt": {"en": "Select a reward (enter number)", "zh": "选择一个奖励（输入编号）"},
    "reward_type_item": {"en": "Item", "zh": "装备"},
    "reward_type_affix": {"en": "Affix", "zh": "词条"},
    "reward_type_codex": {"en": "Codex Progress", "zh": "图鉴进度"},
    "reward_type_gold": {"en": "Gold", "zh": "金币"},
    "reward_type_heal": {"en": "Heal", "zh": "治疗"},
    # Shop
    "shop_title": {"en": "SHOP", "zh": "商店"},
    "shop_prompt": {"en": "Select an item to buy, or 'l' to leave", "zh": "选择物品购买，或输入 'l' 离开"},
    "shop_cannot_afford": {"en": "Cannot afford this item!", "zh": "金币不足！"},
    "shop_item_bought": {"en": "Purchased!", "zh": "已购买！"},
    "shop_leave": {"en": "Leaving shop...", "zh": "离开商店..."},
    # Rest
    "rest_title": {"en": "REST", "zh": "休息"},
    "rest_prompt": {"en": "Rest here? (y/n)", "zh": "在此休息？(y/n)"},
    "rest_heal_amount": {"en": "Heal {percent}% HP", "zh": "恢复 {percent}% 生命值"},
    "rest_mp_restore": {"en": "Restore full MP", "zh": "完全恢复魔力"},
    "rest_confirmed": {"en": "Resting...", "zh": "休息中..."},
    "rest_skipped": {"en": "Skipping rest...", "zh": "跳过休息..."},
    # Event
    "event_title": {"en": "EVENT", "zh": "事件"},
    "event_prompt": {"en": "Make a choice (enter number)", "zh": "做出选择（输入编号）"},
    "event_choice_confirmed": {"en": "Choice made!", "zh": "已做出选择！"},
    # Run Complete / Dead
    "run_complete_title": {"en": "RUN COMPLETE", "zh": "运行完成"},
    "run_dead_title": {"en": "YOU DIED", "zh": "你倒下了"},
    "run_summary": {"en": "Run Summary", "zh": "运行总结"},
}


_LOG_TEMPLATES: dict[str, dict[str, str]] = {
    "hero.basic_attack": {
        "en": "{hero} strikes {target} for {dmg}.",
        "zh": "{hero} 一记普攻命中 {target}，造成 {dmg} 点伤害。",
    },
    "hero.basic_attack_miss_target": {
        "en": "{hero} swings at nothing.",
        "zh": "{hero} 一记空挥。",
    },
    "hero.cast_skill": {
        "en": "{hero} casts {skill}. -MP {mp}, cd {cd}.",
        "zh": "{hero} 施展 {skill}。-MP {mp}，冷却 {cd}。",
    },
    "hero.defend": {
        "en": "{hero} braces. shield(+4)",
        "zh": "{hero} 收紧蜡烛烟雾，护盾 +4。",
    },
    "hero.observe": {
        "en": "{hero} studies the foes.",
        "zh": "{hero} 凝视敌人，记忆其轮廓。",
    },
    "hero.stance": {
        "en": "{hero} shifts stance.",
        "zh": "{hero} 切换姿态。",
    },
    "hero.fall": {
        "en": "{hero} falls.",
        "zh": "{hero} 倒下。",
    },
    "hero.routed": {
        "en": "Enemies routed.",
        "zh": "敌人尽数倒下。",
    },
    "enemy.basic_attack": {
        "en": "{enemy} hits {hero} for {dmg}.",
        "zh": "{enemy} 击中 {hero}，造成 {dmg} 点伤害。",
    },
    "enemy.chant_charge": {
        "en": "{enemy} continues a low chant.",
        "zh": "{enemy} 继续低声吟唱。",
    },
    "enemy.chant_release": {
        "en": "{enemy} releases a shadow chant for {dmg}.",
        "zh": "{enemy} 释放暗影吟唱，造成 {dmg} 点伤害。",
    },
    "enemy.defend": {
        "en": "{enemy} braces.",
        "zh": "{enemy} 守住身位。",
    },
    "shield.absorb": {
        "en": "  shield absorbs {n}.",
        "zh": "  护盾抵消 {n} 点伤害。",
    },
    "poison.tick": {
        "en": "{name} suffers {dmg} poison.",
        "zh": "{name} 受到 {dmg} 点中毒伤害。",
    },
    "bleed.tick": {
        "en": "{name} bleeds for {dmg}.",
        "zh": "{name} 受到 {dmg} 点流血伤害。",
    },
}


_NARRATION: dict[str, dict[str, str]] = {
    "basic_attack": {
        "en": "{hero} steadies a basic strike.",
        "zh": "{hero} 稳住手中的攻势。",
    },
    "cast_skill": {
        "en": "{hero} channels {skill}.",
        "zh": "{hero} 引动 {skill}。",
    },
    "defend": {
        "en": "{hero} braces behind cracked candle smoke.",
        "zh": "{hero} 缩入裂痕中的烛烟之后。",
    },
    "hesitate": {
        "en": "{hero} hesitates.",
        "zh": "{hero} 微微迟疑。",
    },
}


def _resolve_lang(lang: str) -> str:
    if lang in SUPPORTED_LANGUAGES:
        return lang
    return DEFAULT_LANGUAGE


def label(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    """Return a UI label, falling back en -> key on misses."""
    table = _LABELS.get(key)
    if not table:
        return key
    lang = _resolve_lang(lang)
    return table.get(lang) or table.get("en") or key


def log_text(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
    """Return a localized combat log line."""
    table = _LOG_TEMPLATES.get(key)
    if not table:
        return key
    lang = _resolve_lang(lang)
    template = table.get(lang) or table.get("en") or key
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def narration_text(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
    """Return a localized mock narration line."""
    table = _NARRATION.get(key)
    if not table:
        return key
    lang = _resolve_lang(lang)
    template = table.get(lang) or table.get("en") or key
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def visual_width(text: str) -> int:
    """Visual column width with east-asian width awareness."""
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def pad_right(text: str, width: int) -> str:
    """Pad ``text`` to at least ``width`` visual columns."""
    extra = max(0, width - visual_width(text))
    return text + (" " * extra)
