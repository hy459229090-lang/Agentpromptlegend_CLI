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
    "analysis_label": {"en": "Reasoning", "zh": "思考"},
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
    "hero_card_build": {"en": "Build", "zh": "构筑"},
    "hero_card_weapon": {"en": "Weapon", "zh": "武器"},
    "hero_card_risk": {"en": "Risk", "zh": "风险"},
    "hero_card_id_label": {"en": "id", "zh": "编号"},
    "hero_card_mp": {"en": "MP", "zh": "蓝量"},
    "hero_card_cd": {"en": "cd", "zh": "冷却"},
    "hero_card_active_resonances": {"en": "Active Resonances", "zh": "已激活羁绊"},
    "hero_card_near_resonances": {"en": "Near Resonances", "zh": "接近羁绊"},
    "hero_card_codex": {"en": "Codex", "zh": "图鉴"},
    "hero_card_risk_normal": {"en": "normal", "zh": "普通"},
    "hero_card_risk_high": {"en": "high", "zh": "高风险"},
    "hero_card_risk_safe": {"en": "safe", "zh": "安全"},
    "hero_card_risk_gamble": {"en": "gamble", "zh": "赌徒"},
    "hero_card_risk_easy": {"en": "easy", "zh": "容易"},
    "hero_card_risk_hard": {"en": "hard", "zh": "困难"},
    "hero_card_status_online": {"en": "online", "zh": "已激活"},
    "hero_card_status_active": {"en": "active", "zh": "激活中"},
    "hero_card_status_need": {"en": "need", "zh": "还需"},
    "hero_card_best_next_picks": {"en": "Best Next Picks", "zh": "推荐选择"},
    "hero_card_need": {"en": "need", "zh": "还需"},
    "hero_card_action_kit": {"en": "ACTION KIT BOARD", "zh": "ACTION KIT BOARD :: 技能行动套件"},
    "hero_card_positioning": {"en": "Pos", "zh": "定位"},
    "hero_card_use": {"en": "Use", "zh": "用途"},
    "hero_card_build_relation": {"en": "Build", "zh": "Build 关系"},
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
        "en": "Build rewards and Codex knowledge now carry into later decisions.",
        "zh": "Build 奖励与图鉴知识会带入后续决策。",
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
    # Narrative / Story
    "narrative_encounter": {"en": "ENCOUNTER", "zh": "遭遇"},
    "narrative_boss": {"en": "BOSS", "zh": "BOSS"},
    # Shop
    "shop_cannot_afford": {"en": "[CANNOT AFFORD]", "zh": "[买不起]"},
    "shop_strategy": {"en": "Strategy", "zh": "策略"},
    "shop_heal_percent": {"en": "Heal {percent}% HP", "zh": "恢复 {percent}% 生命"},
    # Reward
    "reward_codex_progress": {"en": "+{amount} progress", "zh": "+{amount} 进度"},
    "reward_gold_suffix": {"en": "g", "zh": "金"},
    "reward_heal_percent": {"en": "Heal {percent}% HP", "zh": "恢复 {percent}% 生命"},
    # Run summary
    "run_id_label": {"en": "Run ID", "zh": "运行编号"},
    "seed_label": {"en": "Seed", "zh": "种子"},
    "run_nodes_completed": {"en": "Nodes completed", "zh": "已完成节点"},
    "run_final_build": {"en": "Final Build", "zh": "最终构筑"},
    "run_final_build_stage": {"en": "Stage", "zh": "阶段"},
    "run_final_build_items": {"en": "Items", "zh": "道具"},
    "run_final_build_affixes": {"en": "Affixes", "zh": "词缀"},
    "run_final_build_resonances": {"en": "Resonances", "zh": "羁绊"},
    "run_final_build_skill_limit": {"en": "Skill Limit", "zh": "技能上限"},
    "run_final_build_strategy": {"en": "Strategy", "zh": "策略"},
    "run_current_stats": {"en": "Current Stats", "zh": "当前属性"},
    "run_final_stats": {"en": "Final Stats", "zh": "最终属性"},
    "run_hero": {"en": "Hero", "zh": "英雄"},
    "run_seed_title": {"en": "Seed Title", "zh": "种子标题"},
    "run_level": {"en": "Level", "zh": "等级"},
    "run_build_name": {"en": "Build Name", "zh": "构筑名称"},
    "run_equipment": {"en": "Equipment", "zh": "装备"},
    "run_equip_weapon": {"en": "Weapon", "zh": "武器"},
    "run_equip_armor": {"en": "Armor", "zh": "护甲"},
    "run_equip_trinket": {"en": "Trinket", "zh": "饰品"},
    "run_skills": {"en": "Skills", "zh": "技能"},
    "run_codex": {"en": "Codex", "zh": "图鉴"},
    "run_route": {"en": "Route", "zh": "路线"},
    # Main menu
    "menu_title": {"en": "OURO AGENT :: PROMPT LEGEND", "zh": "暗影代理 Ouro Agent :: 传奇咒语"},
    "menu_status": {"en": "STATUS", "zh": "状态"},
    "menu_entries": {"en": "ENTRIES", "zh": "选项"},
    "menu_entry_play": {"en": "[1] New Run        ouro run --mock", "zh": "[1] 新运行          ouro run --mock"},
    "menu_entry_demo": {"en": "[2] Guided Demo    ouro demo --seed 1", "zh": "[2] 引导试玩        ouro demo --seed 1"},
    "menu_entry_quick_battle": {"en": "[3] Quick Battle   ouro play --mock --no-animation", "zh": "[3] 快速战斗        ouro play --mock --no-animation"},
    "menu_entry_heroes": {"en": "[4] Hero Card      ouro list-heroes / ouro hero-card <hero_id>", "zh": "[4] 英雄卡片        ouro list-heroes / ouro hero-card <英雄ID>"},
    "menu_entry_prompt": {"en": "[5] Prompt Style   ouro prompt-templates", "zh": "[5] 咒语风格        ouro prompt-templates"},
    "menu_entry_status": {"en": "[6] Status         ouro status", "zh": "[6] 状态总览        ouro status"},
    "menu_entry_codex": {"en": "[7] Codex          ouro codex", "zh": "[7] 图鉴            ouro codex"},
    "menu_entry_runs": {"en": "[8] Runs           ouro runs --limit 5", "zh": "[8] 运行归档        ouro runs --limit 5"},
    "menu_entry_report": {"en": "[9] Run Report     ouro run-report", "zh": "[9] 运行报告        ouro run-report"},
    "menu_entry_history": {"en": "[10] Death History ouro history --limit 5", "zh": "[10] 陨落历史       ouro history --limit 5"},
    "menu_entry_replay": {"en": "[11] Replay        ouro replay <trace>", "zh": "[11] 回放           ouro replay <追踪>"},
    "menu_entry_doctor": {"en": "[12] Doctor        ouro doctor", "zh": "[12] 诊断           ouro doctor"},
    "menu_entry_config": {"en": "[13] Configure     ouro config setup", "zh": "[13] 配置           ouro config setup"},
    "menu_entry_quit": {"en": "[q] Quit", "zh": "[q] 退出"},
    "menu_provider": {"en": "Provider", "zh": "供应商"},
    "menu_model": {"en": "Model", "zh": "模型"},
    "menu_key": {"en": "Key", "zh": "密钥"},
    "menu_language": {"en": "Language", "zh": "语言"},
    "menu_visual": {"en": "Visual", "zh": "视觉"},
    "menu_trace": {"en": "Trace", "zh": "追踪"},
    "menu_config": {"en": "Config", "zh": "配置"},
    "menu_key_set": {"en": "set", "zh": "已设置"},
    "menu_key_missing": {"en": "missing", "zh": "缺失"},
    "setup_title": {"en": "RUN SETUP", "zh": "开局整备"},
    "setup_prompt": {"en": "Prompt Contract", "zh": "Prompt 契约"},
    "setup_equipment": {"en": "Equipment Loadout", "zh": "装备界面"},
    "route_choice_note": {
        "en": "Scout the next node. Combat previews show who will enter the right-side enemy lane.",
        "zh": "侦察下一处节点；战斗预览会显示即将进入右侧敌阵的目标。",
    },
    # Battle UI
    "action_strip": {"en": "ACTION STRIP", "zh": "行动流程"},
    "auto_watch": {"en": "AUTO WATCH", "zh": "自动观战"},
    "default_scene": {
        "en": "ash candles flicker under a broken arch",
        "zh": "断裂拱门下，灰烬烛火摇曳",
    },
    "model_session": {"en": "MODEL SESSION", "zh": "模型会话"},
    "battle_echo": {"en": "Battle Echo", "zh": "战斗回响"},
    "sealed_echo": {"en": "Sealed Echo", "zh": "封印回响"},
    "fresh_echo": {"en": "Fresh Echo", "zh": "新鲜回响"},
    "next_pick": {"en": "NEXT PICK", "zh": "下次选择"},
    "need": {"en": "NEED", "zh": "还需"},
    "build_complete": {"en": "BUILD COMPLETE! ALL RESONANCES ONLINE", "zh": "构筑完成！所有羁绊已激活"},
    "build_pending": {"en": "BUILD STAGE: pending real build info", "zh": "构筑阶段：等待真实构筑信息"},
    "build_stage_seed": {"en": "PAIR", "zh": "配对"},
    "build_stage_pair": {"en": "ONLINE", "zh": "激活"},
    "build_stage_online": {"en": "HIGH ROLL", "zh": "高潮"},
    "build_stage_high": {"en": "LOCKED IN", "zh": "锁定"},
    "build_stage_locked": {"en": "PERFECT", "zh": "完美"},
    "build_stage_next": {"en": "NEXT", "zh": "下一阶段"},
    "hud_buff": {"en": "BUFF", "zh": "增益"},
    "hud_debuff": {"en": "DEBUFF", "zh": "减益"},
    "hud_weapon": {"en": "WEAPON", "zh": "武器"},
    "hud_build": {"en": "BUILD", "zh": "构筑"},
    "model_thinking": {"en": "MODEL THINKING", "zh": "模型思考"},
    "model_thinking_loading": {"en": "thinking...", "zh": "思考中..."},
    "enemy_roster": {"en": "ENEMY ROSTER", "zh": "敌方队列"},
    "hero_line": {"en": "HERO LINE", "zh": "英雄台词"},
    "hero_card_ai_bias": {"en": "AI Bias", "zh": "AI 倾向"},
    "hero_card_prompt_template": {"en": "Prompt Template", "zh": "提示词模板"},
    "reward_choice_note": {
        "en": "Pick one reward. The choice changes the next battle's build tags and prompt context.",
        "zh": "选择一项奖励。它会改变下一场战斗的构筑标签与 Prompt 上下文。",
    },
    "shop_note": {
        "en": "The caravan only sells choices that can matter to your build. Leave with 'l'.",
        "zh": "商队只摆出可能影响构筑的货物；输入 l 离开。",
    },
    "shop_ready": {"en": "[READY]", "zh": "[可购买]"},
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
    "hero.ash_counter": {
        "en": "{hero}'s tower shield breaks {enemy}'s chant for {dmg}.",
        "zh": "{hero} 以塔盾震碎 {enemy} 的吟唱，反击 {dmg} 点伤害。",
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
    "enemy.silenced": {
        "en": "{enemy}'s chant breaks under silence.",
        "zh": "{enemy} 的吟唱被沉默打断。",
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
