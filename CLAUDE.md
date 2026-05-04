# CLAUDE — Implementation Guide

Use this file when working with Claude Code in this repository.

## Mission

Implement **Agent Prompt Legend CLI / Ouro Agent** as an installable command-line AI roguelike. The current priority is to turn the working engine and flow skeleton into a player-visible CLI game experience: hero/Build/Prompt setup, turn-by-turn battle frames, readable logs, and battle reports.

## Required Reading

1. `AGENTS.md`
2. `docs/product/06_需求追踪矩阵_20260503.md`
3. `docs/product/04_策划完成度与实现前验收清单_20260503.md`
4. `docs/product/modules/14_命令行美术与TUI设计策划案.md`
5. `docs/product/16_玩家可感知体验整改规格_20260504.md`
6. `docs/product/17_CLI游戏化体验美术Build深化规格_20260504.md`
7. `docs/product/art/08_战斗界面图形与动作分镜_20260504.md`
8. `docs/product/modules/15_GitHub发布安装与Provider接入策划案.md`
9. `docs/product/art/00_美术设计板块索引_20260503.md`
10. `docs/engineering/CODE_LAYOUT.md`
11. `docs/IMPLEMENTATION_HANDOFF.md`

## Current Work Package

Slice 0/A/B and provider integration may already exist in some worktrees. Before adding more systems, implement the `C-Experience` requirements from `docs/product/06_需求追踪矩阵_20260503.md`:

1. `REQ-EXP-001`: main menu/status entry.
2. `REQ-EXP-002`: hero, weapon, Build, skill, Prompt display.
3. `REQ-EXP-003`: semi-auto Prompt strategy templates.
4. `REQ-EXP-004`: turn-by-turn Battle Frame.
5. `REQ-EXP-005`: battle report with skill usage, damage source, and death reason.

Then continue to route/reward/shop interaction and batch balance requirements.

For UI/game-feel work, also implement `C-GameUI` requirements:

1. `REQ-GAMEUI-001`: card/icon/scene-background CLI screens.
2. `REQ-GAMEUI-002`: hero and monster action states.
3. `REQ-GAMEUI-003`: Codex cards with locked/fog states.
4. `REQ-BUILDJOY-001`: Build stage and high-roll feedback.
5. `REQ-CONTEXT-001`: XP-driven context slots.
6. `REQ-GAMEUI-004`: left-hero vs right-enemy battle arena with center effect lane.
7. `REQ-ART-002`: 4-6 line hero/monster sprites, weapon icons, and Build badges.

## Do Not Do Yet

1. Real OpenAI or Anthropic API calls.
2. Full shops, route maps, or dungeon generation.
3. Leaderboards or uploads.
4. Multiplayer/model-vs-model.
5. Large content libraries.
6. GUI or image assets.
7. Final-snapshot-only battles; playable battle output must show turn frames.
8. Pure text-only UI for player-facing game screens; preserve ASCII-safe fallback but design card/icon/action states.
9. Single-column or top-bottom battle screens for the default player battle view.

## Directory Discipline

1. Before adding a file, read the nearest `README.md` and `_rules.md`.
2. Runtime code belongs in `src/ouro_agent/` according to `docs/engineering/CODE_LAYOUT.md`.
3. Game content belongs in `content/`, not hardcoded in package modules.
4. Tests belong in `tests/`; no test may require network or real API keys.
5. Update docs when a directory responsibility changes.

## Expected Validation

Provide commands and evidence for:

1. `ouro --version`
2. `ouro config show`
3. `ouro play --mock`
4. content validation
5. unit tests
6. generated local battle trace
7. fixed-seed player-visible battle output or screenshot showing turn frames and battle report
