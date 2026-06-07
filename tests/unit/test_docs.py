from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_readme_covers_install_mock_provider_and_privacy():
    """REQ-DIST-003: README keeps install, mock play, provider, and privacy paths."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    zh_text = (ROOT / "README.zh.md").read_text(encoding="utf-8")
    examples_readme = (ROOT / "examples/README.md").read_text(encoding="utf-8")
    media_files = (
        "examples/ouro-readme-storefront-showcase.svg",
        "examples/ouro-readme-storefront.svg",
        "examples/ouro-readme-screenshot-wall.svg",
        "examples/ouro-weapon-gallery.svg",
        "examples/ouro-battle-canvas.svg",
        "examples/ouro-after-action.svg",
    )
    battle_media = (ROOT / "examples/ouro-battle-canvas.svg").read_text(encoding="utf-8")
    storefront_showcase = (
        ROOT / "examples/ouro-readme-storefront-showcase.svg"
    ).read_text(encoding="utf-8")
    storefront_media = (ROOT / "examples/ouro-readme-storefront.svg").read_text(
        encoding="utf-8"
    )
    after_action_media = (ROOT / "examples/ouro-after-action.svg").read_text(
        encoding="utf-8"
    )
    screenshot_wall = (ROOT / "examples/ouro-readme-screenshot-wall.svg").read_text(
        encoding="utf-8"
    )
    english_intro = text.split("## Quickstart", 1)[0]
    zh_intro = zh_text.split("## 快速开始", 1)[0]

    assert "Storefront Hero / 商店页封面" in text
    assert "商店页封面 / Storefront Hero" in zh_text
    assert "Player Start Panel / 玩家入口面板" in text
    assert "玩家入口面板 / Player Start Panel" in zh_text
    assert "Language Switch / 语言切换" in text
    assert "语言切换 / Language" in zh_text
    assert "English (current)" in text
    assert "Store page first, engineering later" in text
    assert "先像游戏页，再像工程文档" in zh_text
    assert "ENTER THE RUN" in text
    assert "WATCH THE GAME" in text
    assert "进入地牢" in zh_text
    assert "先看画面" in zh_text
    assert "Steam-style promise:" in text
    assert "Steam 式玩家承诺：" in zh_text
    assert "Gameplay Screens / 先看游戏画面" in text
    assert "先看游戏画面 / Gameplay Screens" in zh_text
    assert "Play Now / 立即试玩" in text
    assert "立即试玩 / Play Now" in zh_text
    assert "30-Second Demo" in text
    assert "30 秒试玩" in zh_text
    assert "中文 / English" in text
    assert "中文 / English" in zh_text
    assert "切到中文介绍" in text
    assert "当前中文介绍页" in zh_text
    assert "Ouro Agent storefront showcase with language switch" in text
    assert "暗影代理首屏主视觉：语言切换、试玩入口和图形化 TUI 战斗" in zh_text
    assert "PLAY DEMO" in text
    assert "WATCH BATTLE" in text
    assert "BROWSE BUILD" in text
    assert "查看构筑" in zh_text
    assert "观看战斗" in zh_text
    assert "The terminal is not a log. It is the arena." in text
    assert "终端不是日志，而是竞技场。" in zh_text
    assert "The AI can choose, but it cannot cheat." in text
    assert "AI 能选择，但不能作弊。" in zh_text
    assert "Game tags:" in text
    assert "游戏标签：" in zh_text
    assert "What you see first" in text
    assert "第一眼会看到什么" in zh_text
    assert "Store Page Capsule:" in text
    assert "商店页胶囊：" in zh_text
    assert "Store Page Pitch" in text
    assert "Steam 商店页式卖点" in zh_text
    assert "Watch the run before reading the docs." in text
    assert "先看画面，再看工程说明。" in zh_text
    assert "Steam-Style Front Page / Steam 风格首页" in text
    assert "Steam 风格首页 / Steam-Style Front Page" in zh_text
    assert "Playable now in mock mode: no network, no API key, deterministic seeds." in text
    assert "现在可离线试玩：无需网络、无需 API key，固定 seed 可复现。" in zh_text
    assert "Media first. Rules second. Engineering third." in text
    assert "Media first. Rules second. Engineering third." in zh_text
    assert "You do not pilot the hero turn by turn. You design the mind it carries into the dungeon." in text
    assert "你不是逐回合操控英雄的人。你是在设计它带进地牢的那颗脑子。" in zh_text
    assert "CLI Language Toggle" in text
    assert "CLI 语言切换" in zh_text
    assert "Best First Screen" in text
    assert "先看最佳画面" in zh_text
    assert "A dark terminal roguelike: build one Agent, then watch it survive by decision + rules, not by button-mashing." in text
    assert "暗黑 Roguelike。先搭建，一局看生死。你是构筑师，不是放技能的人。" in zh_text
    assert "Model chooses. Local Judge decides." in text
    assert "Model chooses. Local Judge decides." in zh_text
    assert "Play in 30 seconds" in text
    assert "中文 30 秒开局" in text
    assert "中文 30 秒开局" in zh_text
    assert "English 30-second start" in zh_text
    assert "Media Gallery / 先看游戏画面" in text
    assert "Media Gallery / 先看游戏画面" in zh_text
    assert "HP / MP / ATB / risk rail" in text
    assert "HP / MP / ATB / 风险条" in zh_text
    assert "Echo Cost / Read Echo / Spoken Echo / Ritual Time" in text
    assert "Echo Cost / Read Echo / Spoken Echo / Ritual Time" in zh_text
    assert text.count('src="examples/ouro-readme-storefront-showcase.svg"') == 1
    assert zh_text.count('src="examples/ouro-readme-storefront-showcase.svg"') == 1
    assert text.count('src="examples/ouro-readme-storefront.svg"') == 1
    assert zh_text.count('src="examples/ouro-readme-storefront.svg"') == 1
    assert text.count('src="examples/ouro-readme-screenshot-wall.svg"') == 1
    assert zh_text.count('src="examples/ouro-readme-screenshot-wall.svg"') == 1
    assert text.index("Train one AI hero. Watch it survive your Prompt.") < text.index("Storefront Hero / 商店页封面")
    assert zh_text.index("训练一个 AI 英雄，让它带着你的 Prompt 下地牢。") < zh_text.index("商店页封面 / Storefront Hero")
    assert text.index("Player Start Panel / 玩家入口面板") < text.index("Storefront Hero / 商店页封面")
    assert zh_text.index("玩家入口面板 / Player Start Panel") < zh_text.index("商店页封面 / Storefront Hero")
    assert text.index("ENTER THE RUN") < text.index('src="examples/ouro-readme-storefront.svg"')
    assert zh_text.index("进入地牢") < zh_text.index('src="examples/ouro-readme-storefront.svg"')
    assert text.index("WATCH THE GAME") < text.index('src="examples/ouro-readme-storefront.svg"')
    assert zh_text.index("先看画面") < zh_text.index('src="examples/ouro-readme-storefront.svg"')
    assert text.index('src="examples/ouro-readme-storefront.svg"') < text.index("Steam-Style Front Page / Steam 风格首页")
    assert zh_text.index('src="examples/ouro-readme-storefront.svg"') < zh_text.index("Steam 风格首页 / Steam-Style Front Page")
    assert text.index("Play in 30 seconds") < text.index('src="examples/ouro-readme-screenshot-wall.svg"')
    assert zh_text.index("中文 30 秒开局") < zh_text.index('src="examples/ouro-readme-screenshot-wall.svg"')
    assert text.index("<details>") < text.index("What a Steam page would show first")
    assert zh_text.index("<details>") < zh_text.index("好的 Steam 页面会先展示什么")
    assert text.index("What a Steam page would show first") < text.index("</details>")
    assert zh_text.index("好的 Steam 页面会先展示什么") < zh_text.index("</details>")
    assert text.index("Storefront Hero / 商店页封面") < text.index("Screenshots: Build, Fight, Learn")
    assert text.index("Screenshots: Build, Fight, Learn") < text.index("## Core Loop")
    assert text.index("## Core Loop") < text.index("## Play Now")
    assert text.index("## Play Now") < text.index("## Current Playable Content")
    assert text.index("## Current Playable Content") < text.index("## Languages")
    assert zh_text.index("商店页封面 / Storefront Hero") < zh_text.index(
        "## 先看游戏画面"
    )
    assert zh_text.index("## 先看游戏画面") < zh_text.index("## 每局你会做什么")
    assert zh_text.index("## 每局你会做什么") < zh_text.index("## 立即试玩")
    assert zh_text.index("## 立即试玩") < zh_text.index("## 当前可玩内容")
    assert zh_text.index("## 当前可玩内容") < zh_text.index("## 双语机制")
    assert "完整中文文档 / Full Chinese README" in text
    assert "English Store Page" in text
    assert "game first, docs later" in text
    assert "双语首页 / Bilingual README" in zh_text
    assert "Choose Your Page / 选择介绍页" in text
    assert "选择介绍页 / Choose Your Page" in zh_text
    assert "Hero Capsule" in text
    assert "首屏胶囊图" in zh_text
    assert "Steam-style screenshot wall" in text
    assert "商店式截图墙" in zh_text
    assert "Game Capsule / 游戏胶囊" in text
    assert "游戏胶囊 / Game Capsule" in zh_text
    assert "A CLI AI roguelike with a real local judge." in text
    assert "一款命令行 AI 肉鸽，胜负由本地裁判结算。" in zh_text
    assert "Why one more run" in text
    assert "为什么再开一局" in zh_text
    assert "MAIN MENU CONSOLE -> ENCOUNTER BRIEFING -> THE ECHO ALTAR -> DECISION FOCUS -> AFTER-ACTION REPORT" in text
    assert "MAIN MENU CONSOLE -> ENCOUNTER BRIEFING -> THE ECHO ALTAR -> DECISION FOCUS -> AFTER-ACTION REPORT" in zh_text
    assert "What a Steam page would show first" in text
    assert "好的 Steam 页面会先展示什么" in zh_text
    assert "Feature proof, not promises" in text
    assert "用画面证明，不只写承诺" in zh_text
    assert "Build / Weapon Gallery / 武器图鉴" in text
    assert "Build / 武器图鉴 / Weapon Gallery" in zh_text
    assert 'src="examples/ouro-weapon-gallery.svg"' in text
    assert 'src="examples/ouro-weapon-gallery.svg"' in zh_text
    assert "Storefront Snapshot / 游戏速览" in text
    assert "游戏速览 / Storefront Snapshot" in zh_text
    assert "Language / 语言" in text
    assert "语言切换 / Language" in zh_text
    assert "CLI 语言切换" in text
    assert "CLI 语言切换" in zh_text
    assert "Train one AI hero. Watch it survive your Prompt." in text
    assert "训练一个 AI 英雄，让它带着你的 Prompt 下地牢。" in zh_text
    assert "You are the builder behind the Agent." in text
    assert "About This Game" in text
    assert "关于这个游戏" in zh_text
    assert "商店页速览" in zh_text
    assert "See the fight, not a scroll of logs." in text
    assert "CLI is treated as a low-resolution game screen" in text
    assert "CLI 被当作低分辨率游戏画面使用" in zh_text
    assert "Visual Target" in text
    assert "Playable State" in text
    assert "试玩状态" in zh_text
    assert "Core Loop / 每局你会做什么" in text
    assert "每局你会做什么" in zh_text
    assert "Why It Plays / Key Features / 为什么它值得试玩" in text
    assert "关键特色" in zh_text
    assert "Mock, offline, no API key" in text
    assert "Play Now: No Network, No API Key" in text
    assert "立即试玩：无网络，无 API key" in zh_text
    assert "Current Playable Content / 当前可玩内容" in text
    assert "当前可玩内容" in zh_text
    assert "Guided first run" in text
    assert "Journey console and command map" in text
    assert "玩家旅程控制台与命令地图" in zh_text
    assert "ouro menu --lang en" in text
    assert "ouro menu --lang zh" in zh_text
    assert "Hero cards, weapon gallery, and Build planning" in text
    assert "英雄卡、武器图鉴和 Build 配置" in zh_text
    assert "ouro weapons --unicode" in text
    assert "ouro weapons --unicode" in zh_text
    assert "完整副本：路线、商店、休息、奖励和 Boss" in zh_text
    assert "Recent Development" not in english_intro
    assert "近期开发" not in zh_intro
    assert "模型永远不决定伤害、掉落、胜负。" in zh_text
    assert "像 Steam 页面一样先说清楚" not in text
    assert "像 Steam 页面一样先说清楚" not in zh_text
    assert "Player Promise" in text
    assert "玩家期待" in zh_text
    assert "Screenshots below are captured from reproducible CLI output" in text
    assert "下面的画面来自可复现的 CLI 输出" in zh_text
    assert "Screenshots: Build, Fight, Learn / 画面：构筑、战斗、复盘" in text
    assert "画面：构筑、战斗、复盘" in zh_text
    assert "Reproducible CLI Capture" in text
    assert "可复现终端片段" in zh_text
    assert "Real TUI Captures" in text
    assert "Graphical Battle Stage" in text
    assert "After-Action Report" in text
    assert "战后复盘屏" in zh_text
    assert "Play Now" in text
    assert "One command gets you from install to a guided first run" in text
    assert "一条命令从安装进入引导式首局" in zh_text
    for media_file in media_files:
        assert media_file in text
        assert media_file in zh_text
        assert (ROOT / media_file).is_file()
        assert "<svg" in (ROOT / media_file).read_text(encoding="utf-8")
    assert "CINEMATIC BEAT" in battle_media
    assert "FLOAT -16 HP | SLN" in battle_media
    assert "░▒▓▓██==&gt;" in battle_media
    assert "░░▓▓XX▓▓░" in battle_media
    assert "▓▓ SLN ▓▓" not in battle_media
    assert "MAIN MENU CONSOLE" in screenshot_wall
    assert "ENCOUNTER BRIEFING" in screenshot_wall
    assert "MINI STAGE" in screenshot_wall
    assert "THREAT RAIL" in screenshot_wall
    assert "WINDOW RAIL" in screenshot_wall
    assert "THE ECHO ALTAR" in screenshot_wall
    assert "DECISION FOCUS" in screenshot_wall
    assert "WINDOW PRESSURE" in screenshot_wall
    assert "AFTER-ACTION REPORT" in screenshot_wall
    assert "Model chooses. Local Judge decides." in screenshot_wall
    assert "Reproduce: ouro demo --lang en --seed 1." in screenshot_wall
    assert "PLAY NOW  ouro demo --lang en" in storefront_media
    assert "VOX [INTERRUPT]" in storefront_media
    assert "ENM [HIT]" in storefront_media
    assert "VOX [INTERRUPT]" in screenshot_wall
    assert "ENM [HIT]" in screenshot_wall
    assert "Build, Fight, Learn before the engineering notes begin" in screenshot_wall
    assert "HERO SHOWCASE" not in storefront_showcase
    assert "PLAYER FANTASY" in storefront_showcase
    assert "LANGUAGE  ENGLISH / 中文" in storefront_showcase
    assert "PLAY DEMO  ouro demo --lang en" in storefront_showcase
    assert "BUILD &gt; FIGHT &gt; LEARN" in storefront_showcase
    assert "No network. No API key." in storefront_showcase
    assert "Model chooses." in storefront_showcase
    assert "Local Judge decides damage" in storefront_showcase
    assert "DECISION FOCUS" in battle_media
    assert "WINDOW answered | JUDGE VALID | Echo Cost 0" in battle_media
    assert "STRIP [WIND]" in text
    assert "STRIP [WIND]" in zh_text
    assert "STRIP [WIND]" in battle_media
    assert "#====[ BATTLE RESULT BOARD ]====#" in after_action_media
    assert "+....[ BATTLE TURN MAP ]....+" in after_action_media
    assert "&gt;==[ PLAY NEXT BOARD ]==&lt;" in after_action_media
    assert "STRIP windup" not in text
    assert "STRIP windup" not in zh_text
    assert "STRIP windup" not in battle_media
    assert "windup ->" not in text
    assert "windup ->" not in zh_text
    assert "windup -&gt;" not in battle_media
    assert "README media captures" in examples_readme
    assert "storefront showcase" in examples_readme
    assert "screenshot wall" in examples_readme
    assert "decision focus HUD" in examples_readme
    assert "storefront-friendly" in examples_readme
    assert "RUN READY BOARD" in text
    assert "THE ECHO ALTAR / COUNTER WINDOW" in text
    assert "BATTLE RESULT BOARD" in text
    assert "[FIRST HERO] Hex Seal" in text
    assert "skill_hex_seal" not in text
    assert "skill_hex_seal" not in zh_text
    assert "游戏画面" in zh_text
    assert "pip install -e ." in text
    assert "pipx install git+https://github.com" in text
    assert "ouro --version" in text
    assert "ouro demo --lang en --seed 1" in text
    assert "ouro play --mock" in text
    assert "The first play does not need a real model." in text
    assert "第一次试玩不需要真实模型。" in zh_text
    assert "ouro config set provider openai" in text
    assert "ouro config set api_key_env OURO_API_KEY" in text
    assert "API keys are" in text
    assert "**never** stored" in text
    assert "ouro config preflight" in text
    assert "set (hidden)" in text
    assert "Mock requires no network and no API key" in text
    assert "Trace files never contain a key" in text


def test_required_layout_directories_have_readmes_and_rules():
    """REQ-DIST-004: product-owned directories declare ownership and local rules."""
    required_roots = (
        ROOT / "src",
        ROOT / "src/ouro_agent",
        ROOT / "content",
        ROOT / "tests",
        ROOT / "docs",
        ROOT / "examples",
        ROOT / "scripts",
    )

    missing: list[str] = []
    for root in required_roots:
        for directory in (root, *root.rglob("*")):
            if not directory.is_dir() or _is_generated_or_hidden(directory):
                continue
            for name in ("README.md", "_rules.md"):
                if not (directory / name).exists():
                    missing.append(f"{directory.relative_to(ROOT)}/{name}")

    assert missing == []


def test_release_handoff_covers_tag_install_smoke_and_privacy():
    """REQ-REL-001: release handoff is concrete enough for a GitHub tag."""
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    handoff = (
        ROOT / "docs/engineering/RELEASE_HANDOFF_20260601.md"
    ).read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "## 0.1.0 - 2026-06-01" in changelog
    assert "venv312/bin/python -m pytest" in changelog
    assert "400 passed" in changelog
    assert "share/ouro-agent/content" in changelog
    assert "API keys are never stored" in changelog
    assert "scripts/acceptance_check.py" in changelog

    assert "Recommended tag: `v0.1.0`" in handoff
    assert "pipx install \"git+https://github.com/<owner>/<repo>.git@v0.1.0\"" in handoff
    assert "venv312/bin/python scripts/acceptance_check.py" in handoff
    assert "ouro doctor --lang en" in handoff
    assert "ouro demo --lang en --seed 1" in handoff
    assert "ouro run --mock --auto --seed 7" in handoff
    assert "ouro codex --lang en" in handoff
    assert "ouro runs --lang en --limit 5" in handoff
    assert "git tag -a v0.1.0" in handoff
    assert "api_key_env" in handoff
    assert "plaintext API key" in handoff
    assert "scripts/acceptance_check.py" in readme
    assert "CHANGELOG.md" in readme
    assert "RELEASE_HANDOFF_20260601.md" in readme


def test_pyproject_packaging_file_references_exist():
    """REQ-DIST-006: release metadata should not point at missing files."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    setuptools = data["tool"]["setuptools"]

    package_data = setuptools.get("package-data", {})
    for package_name, files in package_data.items():
        package_root = ROOT / "src" / package_name.replace(".", "/")
        for relative in files:
            assert (package_root / relative).is_file(), f"{package_name}: {relative}"

    data_files = setuptools.get("data-files", {})
    for target, files in data_files.items():
        assert target.startswith("share/ouro-agent/content")
        for relative in files:
            assert (ROOT / relative).is_file(), relative


def test_final_product_audit_tracks_evidence_and_remaining_risks():
    """REQ-AUDIT-001 / REQ-DOCSYNC-001: audit and roadmap stay aligned."""
    audit = (
        ROOT / "docs/product/24_最终产品验收审计_20260601.md"
    ).read_text(encoding="utf-8")
    roadmap = (
        ROOT / "docs/planning/OuroAgent_分步实现路线图_20260503.md"
    ).read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "当前结论：MVP release candidate 证据充足；完整目标仍保持 active" in audit
    assert "核心玩法不变" in audit
    assert "美术与 TUI" in audit
    assert "数值与战斗节奏" in audit
    assert "剧情、文案、世界观" in audit
    assert "架构边界" in audit
    assert "Provider 与隐私" in audit
    assert "安装与发布" in audit
    assert "venv312/bin/python -m pytest" in audit
    assert "400 passed" in audit
    assert "用户满意度确认仍未完成" in audit
    assert "25_人工试玩记录_20260601.md" in audit
    assert "License 仍待决策" in audit
    assert "真实 Provider 联通 smoke" in audit
    assert "24_最终产品验收审计_20260601.md" in readme
    assert "v0.4 release candidate" in roadmap
    assert "| S6 | CLI / TUI 观战体验基础 | done |" in roadmap
    assert "| S6.1 | BattleLLMSession 改版 | done |" in roadmap
    assert "| S6.2 | Build / Buff / 图鉴 UI 改版 | done |" in roadmap
    assert "| S6.3 | 英雄与怪物内容扩展 | done |" in roadmap
    assert "| S7 | 节点型副本与商店 | done |" in roadmap
    assert "| S8 | 图鉴、成长、失败机制 | done |" in roadmap
    assert "| S9 | MVP 打磨与验证 | done |" in roadmap
    assert "REQ-LONGVIEW-*" in roadmap
    assert "scripts/signoff_check.py --strict" in roadmap
    assert "USER_ACCEPTANCE_20260601.md" in roadmap
    assert "PROVIDER_LIVE_SMOKE_20260601.md" in roadmap
    assert "不能把无限模式、排行榜或模型对战混进 v0.1.0 release candidate" in roadmap


def test_manual_playtest_note_records_full_run_observations():
    """REQ-MANUAL-001: fixed-seed manual playtest records complete-run evidence."""
    note = (
        ROOT / "docs/product/25_人工试玩记录_20260601.md"
    ).read_text(encoding="utf-8")

    assert "REQ-MANUAL-001" in note
    assert "venv312/bin/ouro --lang en run --mock --seed 7" in note
    assert "/private/tmp/ouro_manual_playtest_seed7_20260601.log" in note
    assert "seed | `7`" in note
    assert "Decision:" in note
    assert "Build before/after" in note
    assert "SHOP" in note
    assert "REST" in note
    assert "BOSS PHASE II" in note
    assert "BOSS PHASE III" in note
    assert "Counter windows: 0/10 answered, 5 missed" in note
    assert "Floor reached: 4" in note
    assert "Run Archive:" in note
    assert "Death History:" in note
    assert "结论：pass" in note
    assert "用户满意度确认仍未完成" in note


def test_changeset_manifest_defines_release_boundary_and_local_excludes():
    """REQ-REL-002: release candidate staging boundary is documented."""
    manifest = (
        ROOT / "docs/engineering/CHANGESET_MANIFEST_20260601.md"
    ).read_text(encoding="utf-8")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "v0.1.0 Release Candidate" in manifest
    assert "Include In Release Candidate" in manifest
    assert "Exclude From Release Candidate" in manifest
    assert "src/ouro_agent/" in manifest
    assert "content/" in manifest
    assert "tests/" in manifest
    assert "docs/product/25_人工试玩记录_20260601.md" in manifest
    assert "CHANGELOG.md" in manifest
    assert "git status --short" in manifest
    assert "scripts/release_scope.py --stage-plan" in manifest
    assert "User satisfaction and License decision remain explicit release sign-off items" in manifest
    assert ".obsidian/" in manifest
    assert "venv312/" in manifest
    assert "venv*/" in gitignore
    assert ".obsidian/" in gitignore


def test_signoff_check_reports_external_pending_items():
    """REQ-REL-011: external sign-offs are explicit and machine-checkable."""
    script = ROOT / "scripts/signoff_check.py"
    signoff = (
        ROOT / "docs/engineering/RELEASE_SIGNOFF_20260601.md"
    ).read_text(encoding="utf-8")
    scripts_readme = (ROOT / "scripts/README.md").read_text(encoding="utf-8")
    audit = (
        ROOT / "docs/product/24_最终产品验收审计_20260601.md"
    ).read_text(encoding="utf-8")

    assert script.is_file()
    script_text = script.read_text(encoding="utf-8")
    assert "OURO RELEASE SIGN-OFF" in script_text
    assert "--json" in script_text
    assert "git status" in script_text
    assert "SIGN-OFF: accepted" in script_text
    assert "SIGN-OFF: passed" in script_text
    assert "scripts/release_scope.py --stage-plan" in script_text
    assert "ACCEPTANCE_COMMANDS" in script_text
    assert "ouro_user_acceptance_seed7_20260601" in script_text
    assert "signoff_check.py --strict" in signoff
    assert "signoff_check.py --json" in signoff
    assert "release scope summary" in signoff
    assert "acceptance command" in signoff
    assert "scripts/release_scope.py --stage-plan" in signoff
    assert "USER_ACCEPTANCE_20260601.md" in signoff
    assert "LICENSE_DECISION_20260601.md" in signoff
    assert "PROVIDER_LIVE_SMOKE_20260601.md" in signoff
    assert "pending template" in signoff
    assert "User satisfaction" in signoff
    assert "License" in signoff
    assert "Live provider smoke" in signoff
    assert "Git boundary" in signoff
    assert "signoff_check.py" in scripts_readme
    assert "--json" in scripts_readme
    assert "release_scope.py --stage-plan" in scripts_readme
    assert "USER_ACCEPTANCE_20260601.md" in scripts_readme
    assert "LICENSE_DECISION_20260601.md" in scripts_readme
    assert "PROVIDER_LIVE_SMOKE_20260601.md" in scripts_readme
    assert "signoff_check.py --strict" in audit
    assert "scripts/release_scope.py --stage-plan" in audit

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "OURO RELEASE SIGN-OFF" in result.stdout
    assert "[PENDING] satisfaction" in result.stdout
    assert "[PENDING] license" in result.stdout
    assert "[PENDING] live-provider" in result.stdout
    assert "[PENDING] git-boundary" in result.stdout
    assert "acceptance command: venv312/bin/ouro demo --lang en --seed 1 --content-dir content" in (
        result.stdout
    )
    assert "ouro_user_acceptance_seed7_20260601" in result.stdout
    assert "acceptance command: venv312/bin/python scripts/completion_audit.py --json" in (
        result.stdout
    )
    assert "scope boundary: release-bound=" in result.stdout
    assert "staging plan: venv312/bin/python scripts/release_scope.py --stage-plan" in result.stdout
    assert "Pending sign-offs: 4/4" in result.stdout

    strict = subprocess.run(
        [sys.executable, str(script), "--strict"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert strict.returncode == 3, strict.stderr
    assert "Pending sign-offs: 4/4" in strict.stdout

    json_result = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert json_result.returncode == 0, json_result.stderr
    report = json.loads(json_result.stdout)
    assert report["pending_count"] == 4
    assert report["total"] == 4
    assert report["all_ready"] is False
    statuses = {item["key"]: item["status"] for item in report["items"]}
    assert statuses == {
        "satisfaction": "PENDING",
        "license": "PENDING",
        "live-provider": "PENDING",
        "git-boundary": "PENDING",
    }
    satisfaction = next(item for item in report["items"] if item["key"] == "satisfaction")
    assert any("ouro demo --lang en --seed 1 --content-dir content" in detail for detail in satisfaction["details"])
    assert any("ouro_user_acceptance_seed7_20260601" in detail for detail in satisfaction["details"])
    assert any("scripts/completion_audit.py --json" in detail for detail in satisfaction["details"])
    git_boundary = next(item for item in report["items"] if item["key"] == "git-boundary")
    assert "scripts/release_scope.py --stage-plan" in git_boundary["action"]
    assert any("scope boundary: release-bound=" in detail for detail in git_boundary["details"])


def test_acceptance_check_runs_review_commands_without_signing_off():
    """REQ-REL-019: user acceptance commands have a one-shot review runner."""
    script = ROOT / "scripts/acceptance_check.py"
    signoff_file = ROOT / "docs/engineering/USER_ACCEPTANCE_20260601.md"
    script_text = script.read_text(encoding="utf-8")

    assert script.is_file()
    assert "OURO USER ACCEPTANCE CHECK" in script_text
    assert "SIGN-OFF: accepted" in script_text
    assert "marks_signoff" in script_text
    assert "completion_audit.py" in script_text
    assert "expected_returncodes=(3,)" in script_text

    dry_run = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert dry_run.returncode == 0, dry_run.stderr
    assert "OURO USER ACCEPTANCE CHECK - DRY RUN" in dry_run.stdout
    assert "[DRY-RUN] guided-demo:" in dry_run.stdout
    assert "[DRY-RUN] fixed-seed-run:" in dry_run.stdout
    assert "[DRY-RUN] completion-audit:" in dry_run.stdout

    before = signoff_file.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    after = signoff_file.read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert before == after
    assert "SIGN-OFF: pending" in after
    report = json.loads(result.stdout)
    assert report["ok"] is True
    assert report["marks_signoff"] is False
    steps = {step["key"]: step for step in report["steps"]}
    assert set(steps) == {"guided-demo", "fixed-seed-run", "completion-audit"}
    assert steps["guided-demo"]["missing_markers"] == []
    assert "OURO DEMO :: FIRST ECHO" in steps["guided-demo"]["summary"]
    assert "YOU DIED" in steps["fixed-seed-run"]["summary"]
    assert steps["completion-audit"]["returncode"] == 3
    assert any("goal_complete_ready" in line for line in steps["completion-audit"]["summary"])


def test_signoff_templates_exist_but_do_not_fake_ready():
    """REQ-REL-013: pending templates guide sign-off without passing it."""
    user_acceptance = ROOT / "docs/engineering/USER_ACCEPTANCE_20260601.md"
    provider_live = ROOT / "docs/engineering/PROVIDER_LIVE_SMOKE_20260601.md"
    script = ROOT / "scripts/signoff_check.py"

    acceptance_text = user_acceptance.read_text(encoding="utf-8")
    provider_text = provider_live.read_text(encoding="utf-8")

    assert "SIGN-OFF: pending" in acceptance_text
    assert "SIGN-OFF: accepted" in acceptance_text
    assert "venv312/bin/python scripts/release_check.py" in acceptance_text
    assert "venv312/bin/ouro demo --lang en --seed 1" in acceptance_text
    assert "Mock mode is playable without network or API keys." in acceptance_text
    assert "SIGN-OFF: pending" in provider_text
    assert "SIGN-OFF: passed" in provider_text
    assert "scripts/provider_smoke.py --live" in provider_text
    assert "Do not paste the key into this file" in provider_text

    result = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    statuses = {item["key"]: item["status"] for item in report["items"]}
    assert statuses["satisfaction"] == "PENDING"
    assert statuses["live-provider"] == "PENDING"


def test_license_decision_template_guides_policy_without_marking_ready():
    """REQ-REL-015: License template guides the decision without making it."""
    template = ROOT / "docs/engineering/LICENSE_DECISION_20260601.md"
    script = ROOT / "scripts/signoff_check.py"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh.md").read_text(encoding="utf-8")

    text = template.read_text(encoding="utf-8")

    assert "SIGN-OFF: pending" in text
    assert "MIT" in text
    assert "Apache-2.0" in text
    assert "Private distribution only" in text
    assert "pyproject.toml" in text
    assert "README.zh" in text
    assert "template alone is not enough" in text
    assert "LICENSE_DECISION_20260601.md" in readme
    assert "LICENSE_DECISION_20260601.md" in readme_zh

    result = subprocess.run(
        [sys.executable, str(script), "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    license_item = next(item for item in report["items"] if item["key"] == "license")
    assert license_item["status"] == "PENDING"
    assert "LICENSE_DECISION_20260601.md" in license_item["action"]


def test_signoff_check_detects_ready_markers_and_license_policy(tmp_path):
    """REQ-REL-011: ready states are based on explicit evidence."""
    signoff = _load_signoff_check_module()
    docs_engineering = tmp_path / "docs/engineering"
    docs_engineering.mkdir(parents=True)
    (docs_engineering / "USER_ACCEPTANCE_20260601.md").write_text(
        "# User acceptance\n\nSIGN-OFF: accepted\n", encoding="utf-8"
    )
    (docs_engineering / "PROVIDER_LIVE_SMOKE_20260601.md").write_text(
        "# Provider live smoke\n\nSIGN-OFF: passed\n", encoding="utf-8"
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nlicense = { text = "MIT" }\n', encoding="utf-8"
    )
    (tmp_path / "README.md").write_text(
        "# Ouro\n\n## License\nPrivate distribution policy is selected.\n",
        encoding="utf-8",
    )
    (tmp_path / "README.zh.md").write_text(
        "# Ouro\n\n## License\nPrivate distribution policy is selected.\n",
        encoding="utf-8",
    )

    items = {item.key: item for item in signoff._signoff_items(tmp_path)}

    assert items["satisfaction"].ready
    assert items["license"].ready
    assert items["live-provider"].ready
    assert not items["git-boundary"].ready


def test_release_check_script_documents_and_dry_runs_repo_root_gates():
    """REQ-REL-003: release gates are executable and documented."""
    script = ROOT / "scripts/release_check.py"
    script_text = script.read_text(encoding="utf-8")
    scripts_readme = (ROOT / "scripts/README.md").read_text(encoding="utf-8")
    handoff = (
        ROOT / "docs/engineering/RELEASE_HANDOFF_20260601.md"
    ).read_text(encoding="utf-8")
    manifest = (
        ROOT / "docs/engineering/CHANGESET_MANIFEST_20260601.md"
    ).read_text(encoding="utf-8")
    provider_smoke = ROOT / "scripts/provider_smoke.py"
    provider_smoke_text = provider_smoke.read_text(encoding="utf-8")
    release_scope = ROOT / "scripts/release_scope.py"
    release_scope_text = release_scope.read_text(encoding="utf-8")

    assert script.is_file()
    assert provider_smoke.is_file()
    assert release_scope.is_file()
    assert "subprocess.run" in script_text
    assert "PYTHONPATH" in script_text
    assert '("git", "diff", "--check")' in script_text
    assert "--version-only" in script_text
    assert "version-consistency" in script_text
    assert "Version consistency OK" in script_text
    assert "--evidence-only" in script_text
    assert "evidence-count" in script_text
    assert "Evidence counts OK" in script_text
    assert "--scope-only" in script_text
    assert "scope-boundary" in script_text
    assert "--acceptance-only" in script_text
    assert "acceptance-path" in script_text
    assert "acceptance_check.py" in script_text
    assert "release_scope.py" in script_text
    assert "RELEASE SCOPE CHECK" in release_scope_text
    assert "RELEASE STAGE PLAN" in release_scope_text
    assert "--stage-plan" in release_scope_text
    assert "--collect-only" in script_text
    assert '"demo"' in script_text
    assert "OURO DEMO :: FIRST ECHO" in script_text
    assert "guided demo did not finish battle" in script_text
    assert "REAL PROVIDER SMOKE PREFLIGHT" in provider_smoke_text
    assert "--live" in provider_smoke_text
    assert "provider fell back to mock" in provider_smoke_text
    assert "temporary OURO_AGENT_HOME" in provider_smoke_text
    assert '"run"' in script_text
    assert '"--auto"' in script_text
    assert "Run Summary" in script_text
    assert '"codex"' in script_text
    assert '"status"' in script_text
    assert "OURO STATUS :: ECHO LEDGER" in script_text
    assert "CODEX :: MONSTER ARCHIVE" in script_text
    assert "Observed:" in script_text
    assert "[OB]" in script_text
    assert '"runs"' in script_text
    assert '"history"' in script_text
    assert "RUN ARCHIVE :: ALL RUNS" in script_text
    assert "DEATH HISTORY :: FALLEN RUNS" in script_text
    assert "Runs: 1 total" in script_text
    assert "Fallen Runs: 1" in script_text
    assert "NEXT RUN PLAN" in script_text
    assert "ouro run --mock --prompt-style control" in script_text
    assert "curl" not in script_text
    assert "requests" not in script_text
    assert "release_check.py" in scripts_readme
    assert "pytest" in scripts_readme
    assert "ouro validate-content" in scripts_readme
    assert "git diff --check" in scripts_readme
    assert "privacy scan" in scripts_readme
    assert "doctor gate" in scripts_readme
    assert "version consistency" in scripts_readme
    assert "evidence count" in scripts_readme
    assert "release_scope.py" in scripts_readme
    assert "scope boundary" in scripts_readme
    assert "--stage-plan" in scripts_readme
    assert "acceptance path" in scripts_readme
    assert "--acceptance-only" in scripts_readme
    assert "provider_smoke.py" in scripts_readme
    assert "fails if the CLI falls back to mock" in scripts_readme
    assert "install smoke" in scripts_readme
    assert "Codex readback" in scripts_readme
    assert "status overview" in scripts_readme
    assert "next-run plan" in scripts_readme
    assert "venv312/bin/python scripts/release_check.py" in handoff
    assert "venv312/bin/python scripts/release_check.py --dry-run" in handoff
    assert "venv312/bin/python scripts/release_check.py --install-smoke-only" in handoff
    assert "venv312/bin/python scripts/release_check.py --evidence-only" in handoff
    assert "venv312/bin/python scripts/release_check.py --acceptance-only" in handoff
    assert "venv312/bin/python scripts/release_scope.py" in handoff
    assert "venv312/bin/python scripts/release_scope.py --stage-plan" in handoff
    assert "venv312/bin/python scripts/provider_smoke.py" in handoff
    assert "Live provider smoke OK." in handoff
    assert "repo-root release gate runner" in manifest
    assert "scripts/release_scope.py" in manifest
    assert "scripts/release_scope.py --stage-plan" in manifest
    assert "Scope OK" in manifest
    assert "privacy-scan" in manifest
    assert "PASS: doctor" in manifest
    assert "install smoke" in manifest

    result = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "[DRY-RUN] pytest:" in result.stdout
    assert "-m pytest" in result.stdout
    assert "--doctor-only" in result.stdout
    assert "--version-only" in result.stdout
    assert "--evidence-only" in result.stdout
    assert "[DRY-RUN] evidence-count:" in result.stdout
    assert "--scope-only" in result.stdout
    assert "[DRY-RUN] scope-boundary:" in result.stdout
    assert "--acceptance-only" in result.stdout
    assert "[DRY-RUN] acceptance-path:" in result.stdout
    assert "-m ouro_agent.cli.main validate-content" in result.stdout
    assert "git diff --check" in result.stdout
    assert "--privacy-scan-only" in result.stdout

    install_dry_run = subprocess.run(
        [sys.executable, str(script), "--dry-run", "--install-smoke"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert install_dry_run.returncode == 0, install_dry_run.stderr
    assert "[DRY-RUN] install-smoke:" in install_dry_run.stdout
    assert "--install-smoke-only" in install_dry_run.stdout

    doctor_result = subprocess.run(
        [sys.executable, str(script), "--doctor-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert doctor_result.returncode == 0, doctor_result.stderr
    assert "provider     : mock" in doctor_result.stdout
    assert "provider chk : READY" in doctor_result.stdout
    assert "content      : OK heroes=6 skills=18 enemies=9" in doctor_result.stdout
    assert "mock play    : ready (no API key required)" in doctor_result.stdout
    assert ".ouro_agent" not in doctor_result.stdout

    version_result = subprocess.run(
        [sys.executable, str(script), "--version-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert version_result.returncode == 0, version_result.stderr
    assert "Version consistency OK: 0.1.0 / v0.1.0" in version_result.stdout

    scope_result = subprocess.run(
        [sys.executable, str(script), "--scope-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert scope_result.returncode == 0, scope_result.stderr
    assert "RELEASE SCOPE CHECK" in scope_result.stdout
    assert "Scope OK" in scope_result.stdout

    acceptance_result = subprocess.run(
        [sys.executable, str(script), "--acceptance-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert acceptance_result.returncode == 0, acceptance_result.stderr
    assert "OURO USER ACCEPTANCE CHECK" in acceptance_result.stdout
    assert "[PASS] guided-demo" in acceptance_result.stdout
    assert "[PASS] fixed-seed-run" in acceptance_result.stdout
    assert "[PASS] completion-audit" in acceptance_result.stdout
    assert "User satisfaction sign-off remains manual." in acceptance_result.stdout

    evidence_result = subprocess.run(
        [sys.executable, str(script), "--evidence-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert evidence_result.returncode == 0, evidence_result.stderr
    assert "Evidence counts OK: 400 tests collected; 247 release-bound text files." in (
        evidence_result.stdout
    )

    missing_env = os.environ.copy()
    missing_env.pop("OPENAI_API_KEY", None)
    missing_env.pop("PYTHONPATH", None)
    provider_missing = subprocess.run(
        [
            sys.executable,
            str(provider_smoke),
            "--provider",
            "openai",
            "--model",
            "gpt-test",
            "--api-key-env",
            "OPENAI_API_KEY",
        ],
        cwd=ROOT,
        env=missing_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert provider_missing.returncode == 3, provider_missing.stderr
    assert "REAL PROVIDER SMOKE PREFLIGHT" in provider_missing.stdout
    assert "network      : not called" in provider_missing.stdout
    assert "status       : NOT READY" in provider_missing.stdout
    assert "environment variable OPENAI_API_KEY is not set" in provider_missing.stdout

    ready_env = os.environ.copy()
    ready_env.pop("PYTHONPATH", None)
    ready_env["OURO_API_KEY"] = "redacted-test-key"
    provider_ready = subprocess.run(
        [
            sys.executable,
            str(provider_smoke),
            "--provider",
            "openai-compatible",
            "--model",
            "smoke-test",
            "--api-key-env",
            "OURO_API_KEY",
            "--base-url",
            "https://example.invalid",
        ],
        cwd=ROOT,
        env=ready_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert provider_ready.returncode == 0, provider_ready.stderr
    assert "env value    : set (hidden)" in provider_ready.stdout
    assert "network      : not called" in provider_ready.stdout
    assert "status       : READY" in provider_ready.stdout
    assert "redacted-test-key" not in provider_ready.stdout

    provider_dry_run = subprocess.run(
        [
            sys.executable,
            str(provider_smoke),
            "--dry-run",
            "--live",
            "--provider",
            "openai",
            "--model",
            "gpt-test",
            "--api-key-env",
            "OPENAI_API_KEY",
        ],
        cwd=ROOT,
        env=missing_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert provider_dry_run.returncode == 0, provider_dry_run.stderr
    assert "DRY RUN" in provider_dry_run.stdout
    assert "would run" in provider_dry_run.stdout
    assert "network           : not called" in provider_dry_run.stdout

    scan_result = subprocess.run(
        [sys.executable, str(script), "--privacy-scan-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert scan_result.returncode == 0, scan_result.stderr
    assert "Privacy scan OK" in scan_result.stdout

    release_check = _load_release_check_module()
    placeholder_text = 'setx OPENAI_API_KEY "sk-..."\nBearer token\n'
    real_secret_text = (
        'OPENAI_API_KEY = "sk-' + ("a" * 24) + '"\n'
        "Authorization: Bearer " + ("b" * 32) + "\n"
    )

    assert release_check._find_secret_markers(script, placeholder_text) == []
    findings = release_check._find_secret_markers(script, real_secret_text)
    assert [finding.label for finding in findings] == ["provider key", "bearer token"]


def test_release_scope_classifies_manifest_paths_and_rejects_local_noise(tmp_path):
    """REQ-REL-014: changed paths are audited against the release boundary."""
    scope = _load_release_scope_module()
    script = ROOT / "scripts/release_scope.py"

    assert scope.classify_path("src/ouro_agent/cli/main.py") == "release-bound"
    assert scope.classify_path("content/enemies/mvp_enemies.yaml") == "release-bound"
    assert scope.classify_path("docs/product/23_QA证据与固定Seed试玩记录_20260601.md") == "release-bound"
    assert scope.classify_path("scripts/release_check.py") == "release-bound"
    assert scope.classify_path(".gitignore") == "release-bound"
    assert scope.classify_path(".obsidian/workspace.json") == "local-only"
    assert scope.classify_path("venv312/bin/python") == "local-only"
    assert scope.classify_path(".env") == "local-only"
    assert scope.classify_path("scratchpad/output.txt") == "unknown"

    repo_ok = tmp_path / "release-ok"
    repo_ok.mkdir()
    subprocess.run(["git", "init"], cwd=repo_ok, check=True, stdout=subprocess.PIPE)
    (repo_ok / "README.md").write_text("# release\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(script), "--json", "--root", str(repo_ok)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["ok"] is True
    assert report["release_bound_count"] == 1
    assert report["local_only_count"] == 0
    assert report["unknown_count"] == 0

    repo_blocked = tmp_path / "release-blocked"
    repo_blocked.mkdir()
    subprocess.run(["git", "init"], cwd=repo_blocked, check=True, stdout=subprocess.PIPE)
    (repo_blocked / "README.md").write_text("# release\n", encoding="utf-8")
    (repo_blocked / ".env").write_text("OURO_API_KEY=placeholder\n", encoding="utf-8")
    (repo_blocked / "scratchpad").mkdir()
    (repo_blocked / "scratchpad/output.txt").write_text("local\n", encoding="utf-8")

    blocked = subprocess.run(
        [sys.executable, str(script), "--json", "--root", str(repo_blocked)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert blocked.returncode == 1
    blocked_report = json.loads(blocked.stdout)
    assert blocked_report["ok"] is False
    assert blocked_report["release_bound_count"] == 1
    assert blocked_report["local_only"] == [".env"]
    assert blocked_report["unknown"] == ["scratchpad/output.txt"]


def test_release_scope_prints_read_only_stage_plan_without_mutating_index(tmp_path):
    """REQ-REL-016: release-bound staging has a reviewable read-only plan."""
    scope = _load_release_scope_module()
    script = ROOT / "scripts/release_scope.py"

    commands = scope.stage_plan_commands(
        (
            "README.md",
            "docs/product/stage plan note.md",
            "src/ouro_agent/cli/main.py",
        ),
        chunk_size=1,
    )

    assert commands[0] == "git add -- README.md"
    assert "git add -- 'docs/product/stage plan note.md'" in commands
    assert "git add -- src/ouro_agent/cli/main.py" in commands

    repo = tmp_path / "stage-plan"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE)
    (repo / "README.md").write_text("# release\n", encoding="utf-8")
    src_file = repo / "src/ouro_agent/cli/main.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text("def main():\n    return 0\n", encoding="utf-8")

    before = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result = subprocess.run(
        [sys.executable, str(script), "--stage-plan", "--root", str(repo)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    after = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert before.returncode == 0, before.stderr
    assert result.returncode == 0, result.stderr
    assert after.returncode == 0, after.stderr
    assert before.stdout == after.stdout
    assert "RELEASE STAGE PLAN" in result.stdout
    assert "This script did not stage files." in result.stdout
    assert "release-bound changes :" in result.stdout
    assert "local-only changes    : 0" in result.stdout
    assert "unknown changes       : 0" in result.stdout
    assert "# runtime package" in result.stdout
    assert "git add --" in result.stdout


def test_completion_audit_reports_release_scope_and_signoff_without_marking_complete():
    """REQ-AUDIT-002: final readiness is explicit and sign-off aware."""
    script = ROOT / "scripts/completion_audit.py"
    script_text = script.read_text(encoding="utf-8")
    scripts_readme = (ROOT / "scripts/README.md").read_text(encoding="utf-8")
    handoff = (
        ROOT / "docs/engineering/RELEASE_HANDOFF_20260601.md"
    ).read_text(encoding="utf-8")
    audit = (
        ROOT / "docs/product/24_最终产品验收审计_20260601.md"
    ).read_text(encoding="utf-8")

    assert script.is_file()
    assert "OURO COMPLETION AUDIT" in script_text
    assert "goal_complete_ready" in script_text
    assert "release_check.py" in script_text
    assert "release_scope.py" in script_text
    assert "signoff_check.py" in script_text
    assert "pending_items" in script_text
    assert "Required sign-offs" in script_text
    assert "completion_audit.py" in scripts_readme
    assert "completion_audit.py --json --skip-release-check" in handoff
    assert "pending_items" in handoff
    assert "completion_audit.py --json --skip-release-check" in audit
    assert "Required sign-offs" in audit

    dry_run = subprocess.run(
        [sys.executable, str(script), "--dry-run"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert dry_run.returncode == 0, dry_run.stderr
    assert "[DRY-RUN] release:" in dry_run.stdout
    assert "[DRY-RUN] scope:" in dry_run.stdout
    assert "[DRY-RUN] signoff:" in dry_run.stdout

    json_result = subprocess.run(
        [sys.executable, str(script), "--json", "--skip-release-check"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert json_result.returncode == 3, json_result.stderr
    report = json.loads(json_result.stdout)
    assert report["goal_complete_ready"] is False
    assert report["release_check"]["skipped"] is True
    assert report["release_check"]["ready"] is True
    assert report["scope"]["ready"] is True
    assert report["signoff"]["ready"] is False
    assert set(report["signoff"]["pending_keys"]) == {
        "satisfaction",
        "license",
        "live-provider",
        "git-boundary",
    }
    pending_items = {item["key"]: item for item in report["signoff"]["pending_items"]}
    assert set(pending_items) == {
        "satisfaction",
        "license",
        "live-provider",
        "git-boundary",
    }
    assert "USER_ACCEPTANCE_20260601.md" in pending_items["satisfaction"]["action"]
    assert any(
        "ouro demo --lang en --seed 1 --content-dir content" in detail
        for detail in pending_items["satisfaction"]["details"]
    )
    assert any(
        "ouro_user_acceptance_seed7_20260601" in detail
        for detail in pending_items["satisfaction"]["details"]
    )
    assert "LICENSE_DECISION_20260601.md" in pending_items["license"]["action"]
    assert "provider_smoke.py --live" in pending_items["live-provider"]["action"]
    assert "scripts/release_scope.py --stage-plan" in pending_items["git-boundary"]["action"]

    text_result = subprocess.run(
        [sys.executable, str(script), "--skip-release-check"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert text_result.returncode == 3, text_result.stderr
    assert "Required sign-offs:" in text_result.stdout
    assert "satisfaction: User plays" in text_result.stdout
    assert "git-boundary: Run venv312/bin/python scripts/release_scope.py --stage-plan" in (
        text_result.stdout
    )


def _is_generated_or_hidden(directory: Path) -> bool:
    generated_names = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "build",
        "dist",
    }
    return any(
        part in generated_names
        or part.startswith(".")
        or part.endswith(".egg-info")
        for part in directory.relative_to(ROOT).parts
    )


def _load_release_check_module():
    module_path = ROOT / "scripts/release_check.py"
    spec = importlib.util.spec_from_file_location("ouro_release_check", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_release_scope_module():
    module_path = ROOT / "scripts/release_scope.py"
    spec = importlib.util.spec_from_file_location("ouro_release_scope", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_signoff_check_module():
    module_path = ROOT / "scripts/signoff_check.py"
    spec = importlib.util.spec_from_file_location("ouro_signoff_check", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
