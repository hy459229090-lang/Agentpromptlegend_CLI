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
8. `docs/product/08_代码目录与文件摆放规划_20260503.md`
9. `docs/engineering/CODE_LAYOUT.md`
10. `docs/product/modules/13_角色世界观与内容圣经策划案.md`
11. `docs/product/modules/14_命令行美术与TUI设计策划案.md`
12. `docs/product/modules/15_GitHub发布安装与Provider接入策划案.md`
13. `docs/product/art/00_美术设计板块索引_20260503.md`
14. `docs/product/16_玩家可感知体验整改规格_20260504.md`
15. `docs/product/17_CLI游戏化体验美术Build深化规格_20260504.md`
16. `docs/product/art/08_战斗界面图形与动作分镜_20260504.md`
17. `docs/planning/OuroAgent_AI协作规则_20260503.md`
18. `docs/planning/OuroAgent_分步实现路线图_20260503.md`

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
10. Every directory must keep a local `README.md` and `_rules.md`; read the nearest `_rules.md` before adding files there.
11. Follow `docs/engineering/CODE_LAYOUT.md` when deciding where code, content, tests, examples, and scripts belong.

## Directory Rules

1. Put runtime package code under `src/ouro_agent/`.
2. Put structured game data under `content/`.
3. Put repeatable tests under `tests/`.
4. Put sample configs and sample traces under `examples/`.
5. Put developer helpers under `scripts/`.
6. Put product, planning, engineering, and AI handoff docs under `docs/`.
7. Do not create ad hoc top-level folders without updating `docs/engineering/CODE_LAYOUT.md`, `README.md`, and the relevant directory rules.

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
5. Playable battle output must show turn-by-turn action frames; a final snapshot alone is not acceptable.
6. `--no-animation` may remove delays and micro-animation, but must not remove turn frames or battle logs.
7. CLI style does not mean plain text only; use cards, icons, low-density scene backgrounds, and action states while preserving ASCII-safe fallback.
8. Codex, rewards, Build, and hero screens should be card-like, with locked/fog states where information is not unlocked.
9. Default battle screen must be left-hero vs right-enemy, with 4-6 line actor sprites and a center effect lane.
10. Weapons must use `[W:*]` icons and silhouettes; Build state must use `[SEED]`/`[PAIR]`/`[ONLINE]`/`[HIGH]`/`[LOCK]` badges.

## Evidence Rules

Each completed `REQ-*` must include evidence:

1. tests,
2. trace file,
3. command output,
4. screenshot/log, or
5. documented manual playtest note.

Do not mark a requirement done without evidence.
