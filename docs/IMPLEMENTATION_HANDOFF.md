# Implementation Handoff

> Current state: Slice 0/A/B may exist in implementation worktrees; next approved planning target is player-visible C-Experience.

## Goal

Build an installable command-line AI roguelike that feels playable in a terminal: the player can choose a hero, understand weapon/Build/skills/Prompt strategy, watch turn-by-turn automatic combat, and read a useful battle report.

## Historical First Milestone

Complete **Slice 0 + Slice A** from `docs/product/06_需求追踪矩阵_20260503.md`.

### Slice 0

1. `REQ-DIST-001`: installable CLI package skeleton.
2. `REQ-DIST-002`: mock mode requires no API key.
3. `REQ-DIST-003`: README supports install and mock play.
4. `REQ-PROV-001`: provider config accepts mock/openai/anthropic/openai-compatible.
5. `REQ-PROV-002`: config supports model and base_url.
6. `REQ-PROV-003`: config stores env var names, not key values.
7. `REQ-ART-001`: ASCII-safe combat screen shell.
8. `REQ-CONTENT-001`: at least one hero card with ASCII avatar.

### Slice A

1. `REQ-BTL-001..005`: deterministic ATB combat loop.
2. `REQ-LLM-001..004`: action schema, fallback handling, prompt composer, mock model.
3. `REQ-DATA-001..002`: structured content and validation.
4. `REQ-TRC-001..002`: local battle trace and privacy-safe config.
5. `REQ-VAL-001`: repeatable fixed-seed mock battle.

## Suggested Tech Stack

Planning recommendation:

1. Python package with `pyproject.toml`.
2. `typer` for CLI.
3. `rich` for terminal panels.
4. `pydantic` or dataclasses plus explicit validation for data/schema.
5. `pytest` for tests.

This is a recommendation, not a permanent lock. If changed, update docs and explain why.

## Directory Layout

The repository already contains the intended directory skeleton. Follow `docs/engineering/CODE_LAYOUT.md` and the nearest `README.md` / `_rules.md` before adding files.

Key placement rules:

1. `src/ouro_agent/engine/` owns deterministic combat rules.
2. `src/ouro_agent/providers/` owns provider adapters and must not resolve combat.
3. `src/ouro_agent/tui/` owns terminal presentation and must not mutate battle state.
4. `content/` owns structured game data.
5. `tests/` owns repeatable evidence; tests must not call real model APIs.
6. `examples/` owns safe sample config and trace files only.

## Target Commands

```bash
ouro --version
ouro config show
ouro config set provider mock
ouro play --mock
ouro validate-content
```

## Next Milestone: C-Experience

Before expanding more systems, implement:

1. `REQ-EXP-001`: main menu/status screen.
2. `REQ-EXP-002`: hero/weapon/Build/skill/Prompt configuration display.
3. `REQ-EXP-003`: semi-auto Prompt strategy templates.
4. `REQ-EXP-004`: turn-by-turn Battle Frame.
5. `REQ-EXP-005`: battle report with action mix, skill usage, damage source, and death reason.

## Next Milestone: C-GameUI

After or alongside C-Experience, implement the player-facing game UI layer:

1. `REQ-GAMEUI-001`: CLI cards, icons, and low-density scene backgrounds.
2. `REQ-GAMEUI-002`: hero and monster action states.
3. `REQ-GAMEUI-003`: Codex cards with locked/fog/observed/mastered states.
4. `REQ-BUILDJOY-001`: Build completion stages, resonance events, and best-next-pick hints.
5. `REQ-CONTEXT-001`: XP-driven Strategy/Codex/Memory/Prompt edit slots.
6. `REQ-GAMEUI-004`: left-hero vs right-enemy arena with center projectile/impact lane.
7. `REQ-ART-002`: 4-6 line hero/monster sprites, weapon icons, and Build stage badges.

This milestone is still CLI-first. Do not add GUI/image dependencies; use ASCII-safe and Unicode-enhanced terminal assets.

Target evidence commands:

```bash
ouro play --mock --seed 1 --delay 0.1
ouro play --mock --seed 1 --no-animation
ouro hero-card hero_shadow_apprentice
```

`--no-animation` must still output turn frames; it only removes delay and micro-animation.

Default player battle output must follow `docs/product/art/08_战斗界面图形与动作分镜_20260504.md`: left hero, right enemy, actor sprites, center effects, HUD, Build badges, and short logs.

## Evidence Required

Implementation is not complete until the repo contains evidence for:

1. command output,
2. tests,
3. local trace sample, or
4. documented playtest log,
5. player-visible battle output showing turn frames and battle report.
