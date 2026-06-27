# User Acceptance - Ouro Agent v0.1.0

> Status: pending user review.
> This file is intentionally not accepted yet.

This document is the user-facing acceptance marker for the broader goal:
the game should feel like a mature CLI roguelike while preserving the one-hero
auto-battle core loop.

## Review Commands

Run these from the repository root:

```bash
venv312/bin/python scripts/acceptance_check.py
venv312/bin/python scripts/release_check.py --acceptance-only
venv312/bin/python scripts/release_check.py --doctor-only
venv312/bin/python scripts/release_check.py --combat-stage-only
venv312/bin/python scripts/release_check.py
venv312/bin/python scripts/release_check.py --install-smoke-only
venv312/bin/ouro try --lang en --seed 1 --content-dir content
venv312/bin/ouro demo --lang en --seed 1 --content-dir content
venv312/bin/ouro doctor graphics --lang en --content-dir content
venv312/bin/ouro doctor graphics --lang en --graphics bitmap --probe-image --content-dir content
venv312/bin/ouro --lang en play --mock --seed 2 --graphics auto --color always --no-animation --no-trace --content-dir content
env OURO_AGENT_HOME=/private/tmp/ouro_user_acceptance_seed7_20260601 venv312/bin/ouro --lang en run --mock --seed 7 --no-animation --auto --no-trace --content-dir content
env OURO_AGENT_HOME=/private/tmp/ouro_user_acceptance_seed7_20260601 venv312/bin/ouro run-report --lang en --content-dir content
venv312/bin/ouro status --lang en --content-dir content
venv312/bin/python scripts/completion_audit.py --json
```

Optional Chinese surface:

```bash
venv312/bin/ouro try --lang zh --seed 1 --content-dir content
venv312/bin/ouro demo --lang zh --seed 1 --content-dir content
venv312/bin/ouro list-heroes --lang zh --content-dir content
venv312/bin/ouro weapons --lang zh --content-dir content
venv312/bin/ouro status --lang zh --content-dir content
venv312/bin/ouro codex --lang zh --content-dir content
venv312/bin/ouro run-report --lang zh --content-dir content
```

## Acceptance Checklist

- Core loop remains one configured hero, model-chosen actions, and local deterministic combat resolution.
- Battle output shows turn-by-turn frames, HP/MP/ATB, action intent, judge result, effects, and logs.
- `release_check.py --acceptance-only` passes without writing `SIGN-OFF: accepted`.
- `release_check.py --doctor-only` reports `provider chk : READY`, content OK, and mock play ready.
- `release_check.py --combat-stage-only` reports `Combat stage evidence OK: bitmap, Unicode, and ASCII filmstrips verified.`
- The `completion-audit` step reports `asset_hard_gates.ready` before it stops on pending external sign-offs.
- `doctor graphics` explains the selected graphics backend, fallback chain, and why runtime image generation remains disabled; `--probe-image` renders one local QA-passed runtime PNG in bitmap-capable terminals.
- `play --graphics auto --no-animation` still preserves combat frames, actor/effect anchors, result art, and battle logs for deterministic review.
- The fixed-seed run can be reviewed immediately through `run-report`, including `RUN REPORT :: LAST ECHO`, `VISUAL ANCHORS`, and next-run loadout.
- CLI/TUI feels game-like: hero/enemy silhouettes, cards, build badges, route/reward/shop/rest surfaces, and readable status panels.
- World, character, enemy, Codex, and failure-review text feel coherent enough for a first release candidate.
- Chinese first-run/build/review surfaces are playable without confusing English report chrome.
- Mock mode is playable without network or API keys.
- Install smoke proves the game works outside the source checkout.
- Trace, config, Codex, run archives, and death history do not store API key values.
- Remaining release decisions are understood: user acceptance, optional live-provider smoke, and git boundary. MIT license readiness is already recorded by `LICENSE` and `pyproject.toml`.

## Latest Automated Evidence Refresh

2026-06-18 agent-side evidence refresh, without marking user acceptance:

| Command | Return | Evidence |
| --- | ---: | --- |
| `venv312/bin/ouro try --lang en --seed 1 --content-dir content` | `0` | `OURO DEMO :: FIRST ECHO`, `BATTLE COMPLETE`, `Result : victory`, `CODEX :: MONSTER ARCHIVE`, `STEP 5: Continue from here` |
| `venv312/bin/ouro doctor graphics --lang en --content-dir content` | `0` | selected `ascii` because stdout is a pipe; fallback chain `iterm2 -> kitty -> sixel -> unicode -> ascii`; runtime image generation disabled |
| `venv312/bin/python scripts/acceptance_check.py --json` | `0` | 7/7 automated review steps pass; `completion-audit` confirms `asset_hard_gates.ready: true` and still leaves external sign-offs pending |

## Notes

- User reviewer:
- Date:
- Verdict:
- Required changes before acceptance:

## Sign-Off

Leave the following line as `pending` until the user explicitly accepts the
current build. To mark this item ready, change it exactly to:
`SIGN-OFF: accepted`.

SIGN-OFF: pending
