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
venv312/bin/python scripts/release_check.py
venv312/bin/python scripts/release_check.py --install-smoke-only
venv312/bin/ouro demo --lang en --seed 1 --content-dir content
env OURO_AGENT_HOME=/private/tmp/ouro_user_acceptance_seed7_20260601 venv312/bin/ouro --lang en run --mock --seed 7 --no-animation --auto --no-trace --content-dir content
venv312/bin/ouro status --lang en --content-dir content
venv312/bin/python scripts/completion_audit.py --json
```

Optional Chinese surface:

```bash
venv312/bin/ouro demo --lang zh --seed 1 --content-dir content
venv312/bin/ouro status --lang zh --content-dir content
```

## Acceptance Checklist

- Core loop remains one configured hero, model-chosen actions, and local deterministic combat resolution.
- Battle output shows turn-by-turn frames, HP/MP/ATB, action intent, judge result, effects, and logs.
- CLI/TUI feels game-like: hero/enemy silhouettes, cards, build badges, route/reward/shop/rest surfaces, and readable status panels.
- World, character, enemy, Codex, and failure-review text feel coherent enough for a first release candidate.
- Mock mode is playable without network or API keys.
- Install smoke proves the game works outside the source checkout.
- Trace, config, Codex, run archives, and death history do not store API key values.
- Remaining release decisions are understood: License, optional live-provider smoke, and git boundary.

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
