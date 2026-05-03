# AGENTS — Agent Prompt Legend CLI

This repository is for implementing **Ouro Agent: Prompt Legend**, a command-line AI roguelike where the player configures one hero Agent, then watches it fight automatically through model-driven decisions and deterministic local combat rules.

## Read First

Before coding, read these files in order:

1. `docs/product/00_策划案索引_20260503.md`
2. `docs/product/01_游戏策划总纲_20260503.md`
3. `docs/product/02_设计基线与术语表_20260503.md`
4. `docs/product/03_功能模块拆分与策划清单_20260503.md`
5. `docs/product/04_策划完成度与实现前验收清单_20260503.md`
6. `docs/product/05_策划与研发标准对齐_20260503.md`
7. `docs/product/06_需求追踪矩阵_20260503.md`
8. `docs/product/modules/13_角色世界观与内容圣经策划案.md`
9. `docs/product/modules/14_命令行美术与TUI设计策划案.md`
10. `docs/product/modules/15_GitHub发布安装与Provider接入策划案.md`
11. `docs/planning/OuroAgent_AI协作规则_20260503.md`
12. `docs/planning/OuroAgent_分步实现路线图_20260503.md`

## Current Build Scope

Only implement ready requirements from `docs/product/06_需求追踪矩阵_20260503.md`.

The first approved implementation track is:

1. **Slice 0**: installable CLI skeleton, README, provider config, ASCII-safe screen shell.
2. **Slice A**: deterministic combat engine, model action schema, mock model, local trace.

Do not start shops, route maps, real provider calls, leaderboards, multiplayer, or large content packs until Slice 0 and Slice A are validated.

## Product Rules

1. MVP is a single-player CLI game.
2. MVP uses one configured hero, not a party.
3. During combat the player cannot select skills or targets.
4. The model chooses an action; the local engine validates and resolves it.
5. The model must never decide damage, rewards, drops, or victory.
6. Mock provider must always work without network or API keys.
7. GitHub installability, mock play, provider config, and ASCII-safe UI are product requirements.
8. API keys must not be stored in plaintext; save environment variable names only.
9. Default output must be ASCII-safe; Unicode and color are optional enhancements.

## Provider Rules

Supported provider names:

1. `mock`
2. `openai`
3. `anthropic`
4. `openai-compatible`

The combat engine must depend on an internal provider adapter result, not provider-specific SDK responses.

Configuration fields:

1. `provider`
2. `model`
3. `api_key_env`
4. `base_url`
5. `api_version`
6. `timeout_seconds`
7. `max_retries`
8. `trace_level`
9. `unicode_mode`

## Visual Rules

1. Favor readable panels over decorative output.
2. Use game-flavored token display names:
   - `Echo Cost` for total tokens
   - `Read Echo` for input tokens
   - `Spoken Echo` for output tokens
   - `Ritual Time` for latency
3. Main combat screen must show HP, MP, ATB, statuses, model action, judge result, token/latency summary, and recent log.
4. Animations must be optional and test output must be deterministic.

## Evidence Rules

Each completed `REQ-*` must include evidence:

1. tests,
2. trace file,
3. command output,
4. screenshot/log, or
5. documented manual playtest note.

Do not mark a requirement done without evidence.

