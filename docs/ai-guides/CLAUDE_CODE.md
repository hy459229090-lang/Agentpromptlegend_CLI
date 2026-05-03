# Claude Code Guide — Agent Prompt Legend CLI

## Objective

Claude Code should implement the project as a disciplined product repo. The first milestone is a GitHub-installable CLI skeleton plus a mock-model battle loop.

## Required Context

Read:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/product/06_需求追踪矩阵_20260503.md`
4. `docs/product/07_产出文件逻辑一致性Review_20260503.md`
5. `docs/product/08_代码目录与文件摆放规划_20260503.md`
6. `docs/engineering/CODE_LAYOUT.md`
7. `docs/product/art/00_美术设计板块索引_20260503.md`
8. `docs/IMPLEMENTATION_HANDOFF.md`

## Implementation Order

1. Slice 0 packaging and CLI skeleton.
2. Provider configuration layer with mock/openai/anthropic/openai-compatible names.
3. ASCII-safe combat panel shell.
4. Deterministic battle engine.
5. Model action schema and mock model.
6. Local trace generation.

## Hard Constraints

1. No real API calls until mock battle passes.
2. No plaintext API key storage.
3. No leaderboard, uploads, or player-vs-player.
4. No GUI dependency.
5. No model-decided damage, drops, rewards, or victory.
6. No requirement is done without evidence.
7. No new file may ignore the nearest directory `README.md` and `_rules.md`.
8. No ad hoc top-level directory unless the code layout docs and repo README are updated in the same change.

## Completion Report Format

When finishing a task, report:

1. `REQ-*` IDs completed.
2. Files changed.
3. Commands run.
4. Evidence path or output summary.
5. Remaining blockers.
