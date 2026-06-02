# Changeset Manifest - v0.1.0 Release Candidate

> Date: 2026-06-01  
> Purpose: document the intended commit boundary before tagging `v0.1.0`.

## Include In Release Candidate

These groups are part of the product/release changeset:

- Runtime code under `src/ouro_agent/`, including engine, provider, session, trace, TUI, art, content-loader, and packaging marker changes.
- Structured content under `content/`, including heroes, skills, enemies, dungeons, affixes, and resonances.
- Tests under `tests/`, including unit, integration, visual-width, release, QA, archive, replay, Codex, and requirement-matrix coverage.
- Developer helpers under `scripts/`, including the repo-root release gate runner.
  - `scripts/release_scope.py` audits changed paths against this release boundary without staging or committing.
  - `scripts/release_scope.py --stage-plan` prints grouped, shell-quoted `git add -- ...` commands for release-bound paths only.
- Product and engineering evidence under `docs/`, especially:
  - `docs/product/06_需求追踪矩阵_20260503.md`
  - `docs/product/23_QA证据与固定Seed试玩记录_20260601.md`
  - `docs/product/24_最终产品验收审计_20260601.md`
  - `docs/product/25_人工试玩记录_20260601.md`
  - `docs/engineering/RELEASE_HANDOFF_20260601.md`
- Public release files:
  - `README.md`
  - `README.zh.md`
  - `CHANGELOG.md`
  - `pyproject.toml`
  - `.gitignore`

## Exclude From Release Candidate

These are local-only or generated and should not be staged:

- `.obsidian/`
- `.pytest_cache/`
- `.venv/`, `venv/`, `venv312/`, and other `venv*/` directories
- `build/`, `dist/`, and `*.egg-info/`
- Root runtime outputs: `/traces/`, `/runs/`, `/logs/`
- Local secrets or machine config: `.env`, `.env.*`, `*.local`, `config.local.*`, `secrets.*`

## Pre-Tag Boundary Check

Before staging or tagging:

```bash
git status --short
venv312/bin/python scripts/release_scope.py
venv312/bin/python scripts/release_scope.py --stage-plan
venv312/bin/python scripts/release_check.py
git diff --check
venv312/bin/python -m pytest
venv312/bin/ouro validate-content
```

Expected release-candidate state:

- No local virtualenv/editor folders appear in `git status --short`.
- All intended source, content, test, docs, and release files are reviewed before staging.
- `scripts/release_scope.py` reports `Scope OK`, with zero local-only or unknown paths.
- `scripts/release_scope.py --stage-plan` reports `RELEASE STAGE PLAN`, prints grouped `git add -- ...` commands, and states that it did not stage files.
- `README.md`, `README.zh.md`, `CHANGELOG.md`, `docs/product/23_QA证据与固定Seed试玩记录_20260601.md`, `docs/product/24_最终产品验收审计_20260601.md`, and `docs/engineering/RELEASE_HANDOFF_20260601.md` agree on the latest test count.
- `scripts/release_check.py` reports `PASS: doctor` from an isolated temporary `OURO_AGENT_HOME`, with `provider chk : READY`, content OK, and mock play ready.
- `scripts/release_check.py` reports `PASS: version-consistency`, and `--version-only` reports `Version consistency OK: 0.1.0 / v0.1.0`.
- `venv312/bin/python scripts/release_check.py --install-smoke-only` passes before tagging when clean install smoke evidence must be refreshed; it verifies installed `play`, `codex`, `run`, `runs`, and `history` readback from outside the source checkout. `--install-smoke` can add the same gate to the full release check.
- `scripts/release_check.py` reports `PASS: privacy-scan` and does not find likely plaintext provider keys, bearer tokens, or secret assignments in release-bound text files.
- User satisfaction and License decision remain explicit release sign-off items, not silent assumptions.
