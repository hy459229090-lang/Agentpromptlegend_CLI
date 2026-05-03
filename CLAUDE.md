# CLAUDE — Implementation Guide

Use this file when working with Claude Code in this repository.

## Mission

Implement **Agent Prompt Legend CLI / Ouro Agent** as an installable command-line AI roguelike. The first useful milestone is not a full game; it is a trustworthy CLI skeleton plus a mock-model battle loop.

## Required Reading

1. `AGENTS.md`
2. `docs/product/06_需求追踪矩阵_20260503.md`
3. `docs/product/04_策划完成度与实现前验收清单_20260503.md`
4. `docs/product/modules/14_命令行美术与TUI设计策划案.md`
5. `docs/product/modules/15_GitHub发布安装与Provider接入策划案.md`
6. `docs/IMPLEMENTATION_HANDOFF.md`

## First Work Package

Implement only:

1. `REQ-DIST-*`
2. `REQ-PROV-*`
3. `REQ-ART-001`
4. `REQ-CONTENT-001`
5. then `REQ-BTL-*`, `REQ-LLM-*`, `REQ-DATA-*`, `REQ-TRC-*`, `REQ-VAL-001`

## Do Not Do Yet

1. Real OpenAI or Anthropic API calls.
2. Full shops, route maps, or dungeon generation.
3. Leaderboards or uploads.
4. Multiplayer/model-vs-model.
5. Large content libraries.
6. GUI or image assets.

## Expected Validation

Provide commands and evidence for:

1. `ouro --version`
2. `ouro config show`
3. `ouro play --mock`
4. content validation
5. unit tests
6. generated local battle trace

