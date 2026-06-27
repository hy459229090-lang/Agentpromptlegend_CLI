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
        "examples/ouro-animation-filmstrip.svg",
        "examples/ouro-motion-evidence.svg",
        "examples/ouro-after-action.svg",
    )
    battle_media = (ROOT / "examples/ouro-battle-canvas.svg").read_text(encoding="utf-8")
    animation_media = (
        ROOT / "examples/ouro-animation-filmstrip.svg"
    ).read_text(encoding="utf-8")
    motion_evidence_media = (
        ROOT / "examples/ouro-motion-evidence.svg"
    ).read_text(encoding="utf-8")
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

    assert "# Ouro Agent: Prompt Legend" in text
    assert "# 暗影代理：祷文传说" in zh_text
    assert "Chinese README" in text
    assert "英文版 README" in zh_text
    assert "## Start Here" in text
    assert "## 入口" in zh_text
    assert "## The Pitch" in text
    assert "## 一句话介绍" in zh_text
    assert "## First Look" in text
    assert "## 第一眼" in zh_text
    assert "Start Here / 玩家入口" not in text
    assert "入口 / Start Here" not in zh_text
    assert "The Pitch / 游戏一句话" not in text
    assert "一句话介绍 / The Pitch" not in zh_text
    assert "First Look / 第一眼" not in text
    assert "第一眼 / First Look" not in zh_text
    assert "Game Capsule / 游戏胶囊" not in text
    assert "游戏胶囊 / Game Capsule" not in zh_text
    assert "Screenshots: Build, Fight, Learn / 画面：构筑、战斗、复盘" not in text
    assert "先看游戏画面：构筑、战斗、复盘 / Screenshots" not in zh_text
    assert "Train one AI hero. Send it into a dark terminal dungeon." in text
    assert "训练一个 AI 英雄，把它放进黑暗终端地牢" in zh_text
    assert "Prompt is part of the build" in text
    assert "Prompt 是构筑的一部分" in zh_text
    assert "You do not play the hero turn by turn." in text
    assert "你不是逐回合操控英雄的人" in zh_text
    assert "Model chooses. Local Judge decides." in text
    assert "模型选择行动，本地裁判结算" in zh_text
    assert "Try it in 30 seconds" in text
    assert "中文 30 秒试玩" in zh_text
    assert "Gameplay wall" in text
    assert "玩法画面墙" in zh_text
    assert "Gameplay wall / 玩法画面墙" not in text
    assert "玩法画面墙 / Gameplay wall" not in zh_text
    assert "Player promise" in text
    assert "玩家承诺" in zh_text
    assert "The Prompt is your build." in text
    assert "Prompt 就是你的 Build。" in zh_text
    assert "The terminal is the arena." in text
    assert "终端就是竞技场。" in zh_text
    assert "The AI can choose, but it cannot cheat." in text
    assert "AI 能选择，但不能作弊。" in zh_text
    assert "Every failure becomes evidence." in text
    assert "每次失败都留下证据。" in zh_text
    assert "About This Game" in text
    assert "关于这个游戏" in zh_text
    assert "It cannot invent damage" in text
    assert "它不能虚构伤害" in zh_text
    assert "Recent Development" not in english_intro
    assert "近期开发" not in zh_intro
    assert "像 Steam 页面一样先说清楚" not in text
    assert "像 Steam 页面一样先说清楚" not in zh_text
    assert "Store page first, engineering later" not in text
    assert "先像游戏页，再像工程文档" not in zh_text

    assert "Screenshots below are captured from reproducible CLI output" in text
    assert "下面的画面来自可复现的 CLI 输出" in zh_text
    assert "Screenshots: Build, Fight, Learn" in text
    assert "先看游戏画面：构筑、战斗、复盘" in zh_text
    assert "Reproducible CLI Capture" in text
    assert "可复现终端片段" in zh_text
    assert "Graphical Battle Stage" in text
    assert "战后复盘屏" in zh_text
    assert "Motion Preview" in text
    assert "Motion Evidence" in text
    assert "动画节奏预览" in zh_text
    assert "动效证据墙" in zh_text
    assert "Motion Preview / 动画节奏预览" not in text
    assert "Motion Evidence / 动效证据墙" not in text
    assert "Motion Preview / 动画节奏预览" not in zh_text
    assert "Motion Evidence / 动效证据墙" not in zh_text
    for media_file in media_files:
        assert media_file in text
        assert media_file in zh_text
        assert (ROOT / media_file).is_file()
        assert "<svg" in (ROOT / media_file).read_text(encoding="utf-8")

    live_auto_command = (
        "ouro --lang en play --mock --seed 2 --graphics auto --color always --no-trace --content-dir content"
    )
    bitmap_command = (
        "ouro --lang en play --mock --seed 2 --graphics bitmap --color always --no-trace --content-dir content"
    )
    unicode_command = (
        "ouro --lang en play --mock --seed 2 --graphics unicode --color always --no-trace --content-dir content"
    )
    ascii_static_command = (
        "ouro --lang en play --mock --seed 2 --graphics ascii --no-animation --no-trace --content-dir content"
    )
    zh_live_auto_command = (
        "ouro --lang zh play --mock --seed 2 --graphics auto --color always --no-trace --content-dir content"
    )
    zh_bitmap_command = (
        "ouro --lang zh play --mock --seed 2 --graphics bitmap --color always --no-trace --content-dir content"
    )
    zh_unicode_command = (
        "ouro --lang zh play --mock --seed 2 --graphics unicode --color always --no-trace --content-dir content"
    )
    zh_ascii_static_command = (
        "ouro --lang zh play --mock --seed 2 --graphics ascii --no-animation --no-trace --content-dir content"
    )
    probe_command = "ouro doctor graphics --graphics bitmap --probe-image --content-dir content"
    for command in (
        live_auto_command,
        bitmap_command,
        unicode_command,
        ascii_static_command,
        probe_command,
    ):
        assert command in text
    for command in (
        zh_live_auto_command,
        zh_bitmap_command,
        zh_unicode_command,
        zh_ascii_static_command,
        probe_command,
    ):
        assert command in zh_text

    assert "THE ECHO ALTAR / IMPACT" in battle_media
    assert "SCENE CANDLE/ASH/BROKEN ARCH" in battle_media
    assert "HIT FLASH -16HP" in battle_media
    assert "PULSE ████▓░░ HIT hit" in battle_media
    assert "CAMERA █SHAKE█ hit stop" in battle_media
    assert "WINDOW PRESSURE ANSWERED" in battle_media
    assert "TTY PARTIAL REFRESH" in battle_media
    assert "CINEMATIC BEAT" in battle_media
    assert "OURO AGENT :: ANIMATION FILMSTRIP" in animation_media
    assert "OURO AGENT :: MOTION EVIDENCE WALL" in motion_evidence_media
    assert "MAIN MENU CONSOLE" in screenshot_wall
    assert "ENCOUNTER BRIEFING" in screenshot_wall
    assert "AFTER-ACTION REPORT" in screenshot_wall
    assert "PLAYER FANTASY" in storefront_showcase
    assert "LANGUAGE  ENGLISH / 中文" in storefront_showcase
    assert "PLAY DEMO  ouro demo --lang en" in storefront_showcase
    assert "#====[ BATTLE RESULT BOARD ]====#" in after_action_media
    assert "STRIP windup" not in text
    assert "STRIP windup" not in zh_text
    assert "skill_hex_seal" not in text
    assert "skill_hex_seal" not in zh_text

    assert "Current Playable Content" in text
    assert "Current Playable Content / 当前可玩内容" not in text
    assert "当前可玩内容" in zh_text
    assert "Guided first run" in text
    assert "引导式首局试玩" in zh_text
    assert "pip install -e ." in text
    assert "pipx install git+https://github.com" in text
    assert "ouro --version" in text
    assert "ouro try --lang en --seed 1" in text
    assert "ouro try --lang zh --seed 1" in zh_text
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
    assert "README media captures" in examples_readme
    assert "animation filmstrip" in examples_readme
    assert "motion evidence wall" in examples_readme

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
    assert "464 passed" in changelog
    assert "share/ouro-agent/content" in changelog
    assert "API keys are never stored" in changelog
    assert "scripts/acceptance_check.py" in changelog
    assert "graphics doctor, combat-stage parity" in changelog
    assert "asset_hard_gates.ready: true" in changelog
    assert "strict asset hard gates" in changelog

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
    assert "464 passed" in audit
    assert "七步 PASS" in audit
    assert "graphics doctor" in audit
    assert "combat-stage parity" in audit
    assert "VISUAL ANCHORS" in audit
    assert "release_check.py --combat-stage-only" in audit
    assert "asset_status_report.py --content-dir content --require-all-runtime" in audit
    assert "asset pipeline strict gate: OK" in audit
    assert "asset_manifest_check.py --content-dir content" in audit
    assert "runtime policy: development-only ImageGen, local QA-passed assets only" in audit
    assert "用户满意度确认仍未完成" in audit
    assert "25_人工试玩记录_20260601.md" in audit
    assert "License 已落地" in audit
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
    assert "scripts/release_check.py --combat-stage-only" in note
    assert "Combat stage evidence OK: bitmap, Unicode, and ASCII filmstrips verified." in note
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
    assert "License decision is recorded as MIT" in manifest
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
    assert "doctor graphics --lang en --content-dir content" in script_text
    assert "--graphics auto " in script_text
    assert "--color always --no-animation --no-trace --content-dir content" in script_text
    assert "scripts/release_check.py --combat-stage-only" in script_text
    assert "ouro run-report --lang zh --content-dir content" in script_text
    assert "post-run visual report" in signoff
    assert "release_check.py --combat-stage-only" in signoff
    assert "signoff_check.py --strict" in signoff
    assert "signoff_check.py --json" in signoff
    assert "release scope summary" in signoff
    assert "acceptance command" in signoff
    assert "optional Chinese" in signoff
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
    assert "[READY] license" in result.stdout
    assert "[PENDING] live-provider" in result.stdout
    assert "[PENDING] git-boundary" in result.stdout
    assert "acceptance command: venv312/bin/ouro try --lang en --seed 1 --content-dir content" in (
        result.stdout
    )
    assert "acceptance command: venv312/bin/ouro demo --lang en --seed 1 --content-dir content" in (
        result.stdout
    )
    assert "ouro_user_acceptance_seed7_20260601" in result.stdout
    assert "acceptance command: venv312/bin/ouro doctor graphics --lang en --content-dir content" in (
        result.stdout
    )
    assert (
        "acceptance command: venv312/bin/ouro doctor graphics --lang en --graphics bitmap "
        "--probe-image --content-dir content"
    ) in result.stdout
    assert "acceptance command: venv312/bin/ouro --lang en play --mock --seed 2 --graphics auto" in (
        result.stdout
    )
    assert "acceptance command: venv312/bin/python scripts/release_check.py --combat-stage-only" in (
        result.stdout
    )
    assert "acceptance command: env OURO_AGENT_HOME=/private/tmp/ouro_user_acceptance_seed7_20260601 venv312/bin/ouro run-report --lang en --content-dir content" in (
        result.stdout
    )
    assert "acceptance command: venv312/bin/ouro status --lang zh --content-dir content" in (
        result.stdout
    )
    assert "acceptance command: venv312/bin/ouro codex --lang zh --content-dir content" in (
        result.stdout
    )
    assert "acceptance command: venv312/bin/ouro run-report --lang zh --content-dir content" in (
        result.stdout
    )
    assert "acceptance command: venv312/bin/python scripts/completion_audit.py --json" in (
        result.stdout
    )
    assert "scope boundary: release-bound=" in result.stdout
    assert "staging plan: venv312/bin/python scripts/release_scope.py --stage-plan" in result.stdout
    assert "Pending sign-offs: 3/4" in result.stdout

    strict = subprocess.run(
        [sys.executable, str(script), "--strict"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert strict.returncode == 3, strict.stderr
    assert "Pending sign-offs: 3/4" in strict.stdout

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
    assert report["pending_count"] == 3
    assert report["total"] == 4
    assert report["all_ready"] is False
    statuses = {item["key"]: item["status"] for item in report["items"]}
    assert statuses == {
        "satisfaction": "PENDING",
        "license": "READY",
        "live-provider": "PENDING",
        "git-boundary": "PENDING",
    }
    satisfaction = next(item for item in report["items"] if item["key"] == "satisfaction")
    assert any("ouro try --lang en --seed 1 --content-dir content" in detail for detail in satisfaction["details"])
    assert any("ouro demo --lang en --seed 1 --content-dir content" in detail for detail in satisfaction["details"])
    assert any("doctor graphics --lang en --content-dir content" in detail for detail in satisfaction["details"])
    assert any("--probe-image --content-dir content" in detail for detail in satisfaction["details"])
    assert any("release_check.py --combat-stage-only" in detail for detail in satisfaction["details"])
    assert any("ouro_user_acceptance_seed7_20260601" in detail for detail in satisfaction["details"])
    assert any("ouro run-report --lang zh --content-dir content" in detail for detail in satisfaction["details"])
    assert any("scripts/completion_audit.py --json" in detail for detail in satisfaction["details"])
    git_boundary = next(item for item in report["items"] if item["key"] == "git-boundary")
    assert "scripts/release_scope.py --stage-plan" in git_boundary["action"]
    assert any("scope boundary: release-bound=" in detail for detail in git_boundary["details"])


def test_acceptance_check_runs_review_commands_without_signing_off():
    """REQ-REL-019: user acceptance commands have a one-shot review runner."""
    script = ROOT / "scripts/acceptance_check.py"
    signoff_file = ROOT / "docs/engineering/USER_ACCEPTANCE_20260601.md"
    script_text = script.read_text(encoding="utf-8")
    signoff_text = signoff_file.read_text(encoding="utf-8")

    assert script.is_file()
    assert "OURO USER ACCEPTANCE CHECK" in script_text
    assert "SIGN-OFF: accepted" in script_text
    assert "marks_signoff" in script_text
    assert "completion_audit.py" in script_text
    assert "_completion_audit_missing_json_markers" in script_text
    assert "asset_hard_gates.ready true" in script_text
    assert "asset_hard_gates.ready:" in script_text
    assert "expected_returncodes=(3,)" in script_text
    assert "ouro run-report --lang zh --content-dir content" in signoff_text
    assert "asset_hard_gates.ready" in signoff_text

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
    assert "--lang en try --seed 1 --content-dir content" in dry_run.stdout
    assert "[DRY-RUN] try-storage-fallback:" in dry_run.stdout
    assert "OURO_AGENT_HOME=<blocked-file>" in dry_run.stdout
    assert "[DRY-RUN] graphics-doctor:" in dry_run.stdout
    assert "doctor graphics --lang en --graphics bitmap --probe-image --content-dir content" in dry_run.stdout
    assert "[DRY-RUN] combat-stage-parity:" in dry_run.stdout
    assert "scripts/release_check.py' --combat-stage-only" in dry_run.stdout
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
    assert set(steps) == {
        "guided-demo",
        "try-storage-fallback",
        "graphics-doctor",
        "combat-stage-parity",
        "fixed-seed-run",
        "post-run-report",
        "completion-audit",
    }
    assert steps["guided-demo"]["title"] == "Guided try/demo"
    assert "try" in steps["guided-demo"]["command"]
    assert steps["guided-demo"]["missing_markers"] == []
    assert "OURO DEMO :: FIRST ECHO" in steps["guided-demo"]["summary"]
    assert steps["try-storage-fallback"]["title"] == "Try storage fallback"
    assert steps["try-storage-fallback"]["home_mode"] == "blocked-file"
    assert steps["try-storage-fallback"]["missing_markers"] == []
    assert "DEMO STORAGE" in steps["try-storage-fallback"]["summary"]
    assert any("[TEMP]" in line for line in steps["try-storage-fallback"]["summary"])
    assert any("[KEEP]" in line for line in steps["try-storage-fallback"]["summary"])
    assert steps["graphics-doctor"]["title"] == "Graphics preflight"
    assert steps["graphics-doctor"]["missing_markers"] == []
    assert any("GRAPHICS PREFLIGHT" in line for line in steps["graphics-doctor"]["summary"])
    assert any("IMAGE PROBE" in line for line in steps["graphics-doctor"]["summary"])
    assert any(
        "Runtime image generation: disabled" in line
        for line in steps["graphics-doctor"]["summary"]
    )
    assert steps["combat-stage-parity"]["title"] == "Combat stage parity"
    assert steps["combat-stage-parity"]["missing_markers"] == []
    assert any("Combat stage evidence OK" in line for line in steps["combat-stage-parity"]["summary"])
    assert "YOU DIED" in steps["fixed-seed-run"]["summary"]
    assert any("[RESULT] BMP hero defeat" in line for line in steps["fixed-seed-run"]["summary"])
    assert steps["post-run-report"]["title"] == "Post-run visual report"
    assert steps["post-run-report"]["missing_markers"] == []
    assert any("RUN REPORT :: LAST ECHO" in line for line in steps["post-run-report"]["summary"])
    assert any("VISUAL ANCHORS" in line for line in steps["post-run-report"]["summary"])
    assert steps["completion-audit"]["returncode"] == 3
    assert any("goal_complete_ready" in line for line in steps["completion-audit"]["summary"])
    assert any("asset_hard_gates" in line for line in steps["completion-audit"]["summary"])
    assert "asset_hard_gates.ready: true" in steps["completion-audit"]["summary"]
    assert "asset-status-strict.ready: true" in steps["completion-audit"]["summary"]
    assert "asset-qa.ready: true" in steps["completion-audit"]["summary"]
    assert "asset-manifest.ready: true" in steps["completion-audit"]["summary"]
    assert any("asset-status-strict" in line for line in steps["completion-audit"]["summary"])
    assert any("asset-qa" in line for line in steps["completion-audit"]["summary"])
    assert any("asset-manifest" in line for line in steps["completion-audit"]["summary"])


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
    assert "venv312/bin/ouro try --lang en --seed 1" in acceptance_text
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


def test_mit_license_decision_is_recorded_and_ready():
    """REQ-REL-015: MIT License decision is recorded and machine-checkable."""
    template = ROOT / "docs/engineering/LICENSE_DECISION_20260601.md"
    script = ROOT / "scripts/signoff_check.py"
    license_file = ROOT / "LICENSE"
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh.md").read_text(encoding="utf-8")

    text = template.read_text(encoding="utf-8")

    assert license_file.is_file()
    assert "MIT License" in license_file.read_text(encoding="utf-8")
    assert pyproject["project"]["license"]["text"] == "MIT"
    assert "SIGN-OFF: selected" in text
    assert "Selected License or policy: MIT License" in text
    assert "pyproject.toml" in text
    assert "README.zh" in text
    assert "`LICENSE` file" in text
    assert "MIT License. See [LICENSE](LICENSE)." in readme
    assert "本项目使用 MIT License，详见 [LICENSE](LICENSE)。" in readme_zh
    assert "License is not selected yet" not in readme
    assert "License 待定" not in readme_zh
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
    assert license_item["status"] == "READY"
    assert license_item["evidence"] == "LICENSE file exists"
    assert license_item["action"] == "No action required."
    assert any("license='MIT'" in detail for detail in license_item["details"])


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
    tui_shell_spike = ROOT / "scripts/tui_shell_spike.py"
    tui_shell_spike_text = tui_shell_spike.read_text(encoding="utf-8")
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert script.is_file()
    assert provider_smoke.is_file()
    assert release_scope.is_file()
    assert tui_shell_spike.is_file()
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
    assert "--asset-status-only" in script_text
    assert "--asset-status-strict" in script_text
    assert "--skip-asset-status" in script_text
    assert "asset-status" in script_text
    assert "asset_status_report.py" in script_text
    assert "--combat-stage-only" in script_text
    assert "--skip-combat-stage" in script_text
    assert "combat-stage-evidence" in script_text
    assert "record_combat_stage.py" in script_text
    assert "--timeline-coverage-only" in script_text
    assert "--skip-timeline-coverage" in script_text
    assert "timeline-coverage" in script_text
    assert "timeline_coverage_report.py" in script_text
    assert "release_scope.py" in script_text
    assert "RELEASE SCOPE CHECK" in release_scope_text
    assert "RELEASE STAGE PLAN" in release_scope_text
    assert "--stage-plan" in release_scope_text
    assert "--collect-only" in script_text
    assert '"try"' in script_text
    assert "OURO DEMO :: FIRST ECHO" in script_text
    assert "guided try did not finish battle" in script_text
    assert "REAL PROVIDER SMOKE PREFLIGHT" in provider_smoke_text
    assert "--live" in provider_smoke_text
    assert "provider fell back to mock" in provider_smoke_text
    assert "temporary OURO_AGENT_HOME" in provider_smoke_text
    assert "OURO TUI SHELL SPIKE" in tui_shell_spike_text
    assert "current-ansi-renderer" in tui_shell_spike_text
    assert "rich-live" in tui_shell_spike_text
    assert "textual-app-shell" in tui_shell_spike_text
    assert "importlib.util.find_spec" in tui_shell_spike_text
    assert "ShellAdapter.close() restores cursor/screen and never mutates RunState" in (
        tui_shell_spike_text
    )
    base_deps = [dependency.lower() for dependency in pyproject["project"]["dependencies"]]
    assert all(not dependency.startswith("rich") for dependency in base_deps)
    assert all(not dependency.startswith("textual") for dependency in base_deps)
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
    assert "graphics doctor, combat-stage parity" in scripts_readme
    assert "post-run visual report" in scripts_readme
    assert "asset_hard_gates.ready: true" in scripts_readme
    assert "asset status" in scripts_readme
    assert "--asset-status-only" in scripts_readme
    assert "--asset-status-strict" in scripts_readme
    assert "informational by default" in scripts_readme
    assert "combat-stage graphics evidence" in scripts_readme
    assert "--combat-stage-only" in scripts_readme
    assert "iTerm2/Kitty/SIXEL bitmap filmstrips" in scripts_readme
    assert "skill timeline coverage" in scripts_readme
    assert "--timeline-coverage-only" in scripts_readme
    assert "timeline_coverage_report.py" in scripts_readme
    assert "provider_smoke.py" in scripts_readme
    assert "fails if the CLI falls back to mock" in scripts_readme
    assert "tui_shell_spike.py" in scripts_readme
    assert "optional Rich/Textual shell evaluation helper" in scripts_readme
    assert "dependency-free ANSI renderer as the default" in scripts_readme
    assert "graphics auto play, combat-stage parity" in scripts_readme
    assert "install smoke" in scripts_readme
    assert "Codex readback" in scripts_readme
    assert "status overview" in scripts_readme
    assert "next-run plan" in scripts_readme
    assert "venv312/bin/python scripts/release_check.py" in handoff
    assert "venv312/bin/python scripts/release_check.py --dry-run" in handoff
    assert "venv312/bin/python scripts/release_check.py --install-smoke-only" in handoff
    assert "venv312/bin/python scripts/release_check.py --evidence-only" in handoff
    assert "venv312/bin/python scripts/release_check.py --combat-stage-only" in handoff
    assert "venv312/bin/python scripts/release_check.py --timeline-coverage-only" in handoff
    assert "venv312/bin/python scripts/release_check.py --acceptance-only" in handoff
    assert (
        "venv312/bin/python scripts/asset_status_report.py --content-dir content --require-all-runtime"
        in handoff
    )
    assert "venv312/bin/python scripts/asset_qa_check.py --content-dir content" in handoff
    assert "venv312/bin/python scripts/asset_manifest_check.py --content-dir content" in handoff
    assert "asset pipeline strict gate: OK" in handoff
    assert "development-only ImageGen plus local QA-passed assets" in handoff
    assert "venv312/bin/python scripts/release_scope.py" in handoff
    assert "venv312/bin/python scripts/release_scope.py --stage-plan" in handoff
    assert "venv312/bin/python scripts/provider_smoke.py" in handoff
    assert "venv312/bin/python scripts/tui_shell_spike.py" in handoff
    assert "TUI shell spike is optional and non-invasive" in handoff
    assert "rich-live" in handoff
    assert "textual-app-shell" in handoff
    assert "Live provider smoke OK." in handoff
    assert "repo-root release gate runner" in manifest
    assert "scripts/release_scope.py" in manifest
    assert "scripts/release_scope.py --stage-plan" in manifest
    assert "Scope OK" in manifest
    assert "privacy-scan" in manifest
    assert "combat-stage-evidence" in manifest
    assert "simulated iTerm2/Kitty/SIXEL bitmap filmstrips" in manifest
    assert "timeline-coverage" in manifest
    assert "all 18 MVP skills" in manifest
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
    assert "--asset-status-only" in result.stdout
    assert "[DRY-RUN] asset-status:" in result.stdout
    assert "--combat-stage-only" in result.stdout
    assert "[DRY-RUN] combat-stage-evidence:" in result.stdout
    assert "--timeline-coverage-only" in result.stdout
    assert "[DRY-RUN] timeline-coverage:" in result.stdout
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

    asset_status_result = subprocess.run(
        [sys.executable, str(script), "--asset-status-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert asset_status_result.returncode == 0, asset_status_result.stderr
    assert "asset pipeline status: OK" in asset_status_result.stdout
    assert "asset pipeline strict gate: not requested" in asset_status_result.stdout

    asset_status_strict_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/asset_status_report.py"),
            "--content-dir",
            "content",
            "--require-all-runtime",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert asset_status_strict_result.returncode == 0, asset_status_strict_result.stderr
    assert "assets: 82" in asset_status_strict_result.stdout
    assert "candidate_assets: 82/82" in asset_status_strict_result.stdout
    assert "cut_metadata_assets: 82/82" in asset_status_strict_result.stdout
    assert "qa_passed_assets: 82/82" in asset_status_strict_result.stdout
    assert "runtime_enabled_assets: 82/82" in asset_status_strict_result.stdout
    assert "asset pipeline strict gate: OK" in asset_status_strict_result.stdout

    asset_qa_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/asset_qa_check.py"),
            "--content-dir",
            "content",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert asset_qa_result.returncode == 0, asset_qa_result.stderr
    assert "asset QA records: OK" in asset_qa_result.stdout
    assert "records: 82" in asset_qa_result.stdout
    assert "qa_passed: 82" in asset_qa_result.stdout
    assert "candidate storage: no generated images are stored in runtime assets before QA" in (
        asset_qa_result.stdout
    )

    asset_manifest_result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/asset_manifest_check.py"),
            "--content-dir",
            "content",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert asset_manifest_result.returncode == 0, asset_manifest_result.stderr
    assert "asset manifest: OK" in asset_manifest_result.stdout
    assert "assets: 82" in asset_manifest_result.stdout
    assert "skill: 18" in asset_manifest_result.stdout
    assert "coverage: full current MVP content" in asset_manifest_result.stdout
    assert "runtime policy: development-only ImageGen, local QA-passed assets only" in (
        asset_manifest_result.stdout
    )

    combat_stage_result = subprocess.run(
        [sys.executable, str(script), "--combat-stage-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert combat_stage_result.returncode == 0, combat_stage_result.stderr
    assert "combat stage record: OK" in combat_stage_result.stdout
    assert "bitmap_iterm2_filmstrip" in combat_stage_result.stdout
    assert "Combat stage evidence OK" in combat_stage_result.stdout

    timeline_coverage_result = subprocess.run(
        [sys.executable, str(script), "--timeline-coverage-only"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert timeline_coverage_result.returncode == 0, timeline_coverage_result.stderr
    assert "timeline coverage: OK" in timeline_coverage_result.stdout
    assert "skills: 18/18" in timeline_coverage_result.stdout
    assert "- skill_hex_seal: beats=12" in timeline_coverage_result.stdout

    tui_spike_result = subprocess.run(
        [sys.executable, str(tui_shell_spike)],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert tui_spike_result.returncode == 0, tui_spike_result.stderr
    assert "OURO TUI SHELL SPIKE" in tui_spike_result.stdout
    assert "KEEP current-ansi-renderer as default" in tui_spike_result.stdout
    assert "DEFER textual-app-shell" in tui_spike_result.stdout
    assert "ShellAdapter.close() restores cursor/screen and never mutates RunState" in (
        tui_spike_result.stdout
    )

    tui_spike_json = subprocess.run(
        [sys.executable, str(tui_shell_spike), "--json"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert tui_spike_json.returncode == 0, tui_spike_json.stderr
    tui_spike_data = json.loads(tui_spike_json.stdout)
    assert tui_spike_data["ok"] is True
    probe_names = {probe["name"] for probe in tui_spike_data["probes"]}
    assert probe_names == {"current-ansi-renderer", "rich-live", "textual-app-shell"}
    decisions = {probe["name"]: probe["default_path"] for probe in tui_spike_data["probes"]}
    assert decisions["current-ansi-renderer"] == "keep"
    assert decisions["rich-live"] == "defer"
    assert decisions["textual-app-shell"] == "defer"

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
    assert "[PASS] try-storage-fallback" in acceptance_result.stdout
    assert "DEMO STORAGE" in acceptance_result.stdout
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
    assert "Evidence counts OK: 464 tests collected; 777 release-bound text files." in (
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
    assert scope.classify_path("LICENSE") == "release-bound"
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
    assert "asset_status_report.py" in script_text
    assert "--require-all-candidates" in script_text
    assert "--require-all-cut-metadata" in script_text
    assert "--require-all-qa-passed" in script_text
    assert "--require-all-runtime" in script_text
    assert "asset_qa_check.py" in script_text
    assert "asset_manifest_check.py" in script_text
    assert "asset_hard_gates" in script_text
    assert "release_scope.py" in script_text
    assert "signoff_check.py" in script_text
    assert "pending_items" in script_text
    assert "Required sign-offs" in script_text
    assert "completion_audit.py" in scripts_readme
    assert "strict asset hard gates" in scripts_readme
    assert "Even with `--skip-release-check`, it still runs asset status strict mode" in (
        scripts_readme
    )
    assert "completion_audit.py --json --skip-release-check" in handoff
    assert "asset_hard_gates.ready" in handoff
    assert "pending_items" in handoff
    assert "completion_audit.py --json --skip-release-check" in audit
    assert "asset_hard_gates.ready: true" in audit
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
    assert "[DRY-RUN] asset-status-strict:" in dry_run.stdout
    assert "--require-all-candidates --require-all-cut-metadata --require-all-qa-passed --require-all-runtime" in (
        dry_run.stdout
    )
    assert "[DRY-RUN] asset-qa:" in dry_run.stdout
    assert "[DRY-RUN] asset-manifest:" in dry_run.stdout
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
    assert report["asset_hard_gates"]["ready"] is True
    asset_commands = {
        command["key"]: command for command in report["asset_hard_gates"]["commands"]
    }
    assert asset_commands["asset-status-strict"]["ready"] is True
    assert asset_commands["asset-status-strict"]["marker"] == "asset pipeline strict gate: OK"
    assert asset_commands["asset-qa"]["ready"] is True
    assert asset_commands["asset-qa"]["marker"] == "asset QA records: OK"
    assert asset_commands["asset-manifest"]["ready"] is True
    assert asset_commands["asset-manifest"]["marker"] == "asset manifest: OK"
    assert report["scope"]["ready"] is True
    assert report["signoff"]["ready"] is False
    assert set(report["signoff"]["pending_keys"]) == {
        "satisfaction",
        "live-provider",
        "git-boundary",
    }
    pending_items = {item["key"]: item for item in report["signoff"]["pending_items"]}
    assert set(pending_items) == {
        "satisfaction",
        "live-provider",
        "git-boundary",
    }
    assert "USER_ACCEPTANCE_20260601.md" in pending_items["satisfaction"]["action"]
    assert any(
        "ouro try --lang en --seed 1 --content-dir content" in detail
        for detail in pending_items["satisfaction"]["details"]
    )
    assert any(
        "ouro demo --lang en --seed 1 --content-dir content" in detail
        for detail in pending_items["satisfaction"]["details"]
    )
    assert any(
        "ouro_user_acceptance_seed7_20260601" in detail
        for detail in pending_items["satisfaction"]["details"]
    )
    assert any(
        "ouro run-report --lang zh --content-dir content" in detail
        for detail in pending_items["satisfaction"]["details"]
    )
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
    assert "asset gates   : READY" in text_result.stdout
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
