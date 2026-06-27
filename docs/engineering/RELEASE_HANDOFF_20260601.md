# Release Handoff - v0.1.0

> Date: 2026-06-01  
> Scope: GitHub tag-ready handoff for Ouro Agent: Prompt Legend CLI.

## Release Target

- Package name: `ouro-agent`
- CLI entrypoint: `ouro`
- Version: `0.1.0`
- Recommended tag: `v0.1.0`
- Python: `>=3.11`
- Offline demo path: mock provider

## Install Notes

Editable local install:

```bash
pip install -e .
ouro --version
ouro doctor --lang en
ouro try --lang en --seed 1
ouro play --mock --seed 1 --no-animation --no-trace
```

GitHub tag install:

```bash
pipx install "git+https://github.com/<owner>/<repo>.git@v0.1.0"
ouro --version
ouro doctor --lang en
ouro try --lang en --seed 1
ouro run --mock --auto --seed 7 --no-animation --no-trace
```

Clean virtual environment smoke:

```bash
python -m venv /private/tmp/ouro_install_smoke_20260601
/private/tmp/ouro_install_smoke_20260601/bin/python -m pip install .
cd /private/tmp
/private/tmp/ouro_install_smoke_20260601/bin/ouro --version
OURO_AGENT_HOME=/private/tmp/ouro_release_home /private/tmp/ouro_install_smoke_20260601/bin/ouro --lang en doctor
OURO_AGENT_HOME=/private/tmp/ouro_release_home /private/tmp/ouro_install_smoke_20260601/bin/ouro --lang en try --seed 1
OURO_AGENT_HOME=/private/tmp/ouro_release_home /private/tmp/ouro_install_smoke_20260601/bin/ouro --lang en play --mock --seed 1 --no-animation --no-trace
OURO_AGENT_HOME=/private/tmp/ouro_release_home /private/tmp/ouro_install_smoke_20260601/bin/ouro codex --lang en
```

The installed package must find bundled content under `share/ouro-agent/content` when `./content` is absent.
`ouro demo` remains a compatibility alias for release reviewers, but `ouro try`
is the recommended player-facing first command.

## Required Gates

Run these before tagging:

```bash
venv312/bin/python scripts/release_check.py
venv312/bin/python -m pytest
venv312/bin/ouro validate-content
venv312/bin/python scripts/asset_status_report.py --content-dir content --require-all-runtime
venv312/bin/python scripts/asset_qa_check.py --content-dir content
venv312/bin/python scripts/asset_manifest_check.py --content-dir content
git diff --check
```

Use `venv312/bin/python scripts/release_check.py --dry-run` to preview the
exact gate commands without executing them.
Use `venv312/bin/python scripts/release_check.py --install-smoke-only` before
tagging when you want to re-run the clean virtualenv install smoke without
the full test suite.
Use `venv312/bin/python scripts/release_check.py --version-only` to verify
`pyproject.toml`, package `__version__`, `CHANGELOG.md`, and this handoff all
agree on `0.1.0` / `v0.1.0`.
Use `venv312/bin/python scripts/release_check.py --evidence-only` to verify
the current pytest collection count and release-bound privacy scan count still
match README, CHANGELOG, QA, audit, and requirement-matrix evidence.
Use `venv312/bin/python scripts/release_check.py --combat-stage-only` to verify
the terminal graphics evidence bundle: simulated iTerm2/Kitty/SIXEL bitmap filmstrips,
Unicode fallback filmstrip, and ASCII fallback filmstrip for the Hex Seal smoke
timeline.
Use `venv312/bin/python scripts/release_check.py --timeline-coverage-only` to
verify all 18 MVP skills still build display-only sprite timelines from
QA-promoted runtime atlas frames, including 12-beat authored timelines for all
six hero signature skills.
Use `venv312/bin/python scripts/asset_status_report.py --content-dir content --require-all-runtime`
as the strict runtime asset gate. It must report 82/82 candidate, cut metadata,
QA-passed, and runtime-enabled assets, plus `asset pipeline strict gate: OK`.
Use `venv312/bin/python scripts/asset_qa_check.py --content-dir content` and
`venv312/bin/python scripts/asset_manifest_check.py --content-dir content` to
verify QA records, safe target paths, manifest coverage, and the runtime policy
of development-only ImageGen plus local QA-passed assets.
Use `venv312/bin/python scripts/release_check.py --privacy-scan-only` to run
only the release-bound secret scan.
Use `venv312/bin/python scripts/provider_smoke.py` for an offline real-provider
preflight, or add `--live` after setting the configured API-key environment
variable to run one real-provider battle. The helper uses a temporary
`OURO_AGENT_HOME`, stores only `api_key_env`, and fails live smoke if the CLI
falls back to mock.
Use `venv312/bin/python scripts/signoff_check.py` to display human/external
sign-offs that are outside the mock-first automated gate. Add `--json` for a
machine-readable report, or `--strict` when you want the command to fail until
user satisfaction, live provider, and git-boundary sign-offs are
explicitly handled.

Expected results:

- `464 passed` or higher, matching README and QA note badges.
- Content validation shows heroes 6, skills 18, enemies 9, items 15, affixes 12, resonances 5.
- The isolated doctor gate reports `provider chk : READY`, content OK, and mock play ready from a temporary `OURO_AGENT_HOME`.
- Version consistency reports `Version consistency OK: 0.1.0 / v0.1.0`.
- Evidence count consistency reports `Evidence counts OK: 464 tests collected; 777 release-bound text files.`
- Scope boundary reports `Scope OK` from `venv312/bin/python scripts/release_scope.py` and is included in the default release check.
- Staging review can use `venv312/bin/python scripts/release_scope.py --stage-plan`, which prints `RELEASE STAGE PLAN`, grouped `git add -- ...` commands, and `This script did not stage files.`
- User acceptance review can use `venv312/bin/python scripts/acceptance_check.py` or the release-gate wrapper `venv312/bin/python scripts/release_check.py --acceptance-only`, while `venv312/bin/python scripts/signoff_check.py` also lists optional Chinese try/demo/status/Codex/run-report review commands; these reports do not write `SIGN-OFF: accepted`.
- Completion audit `venv312/bin/python scripts/completion_audit.py --json --skip-release-check` still runs strict asset hard gates and reports `goal_complete_ready: false` until all external sign-offs are ready; it includes `asset_hard_gates.ready` plus `signoff.pending_items` with each pending item's evidence and action. Run without `--skip-release-check` for the full final audit.
- License decision is MIT: `LICENSE` exists, `pyproject.toml` reports `MIT`, README/README.zh link the license, and `signoff_check.py --json` reports `license: READY`.
- Clean install smoke creates a temporary virtualenv, runs `pip install .`, then verifies installed `ouro --version`, `ouro doctor`, `ouro try`, `ouro play --mock`, `ouro codex`, full `ouro run`, `ouro runs`, `ouro run-report`, `ouro history`, and `ouro status` from outside the source checkout.
- Strict runtime asset status reports `assets: 82`, `candidate_assets: 82/82`, `cut_metadata_assets: 82/82`, `qa_passed_assets: 82/82`, `runtime_enabled_assets: 82/82`, all MVP type counts, and `asset pipeline strict gate: OK`.
- Asset QA reports `asset QA records: OK`, `records: 82`, `qa_passed: 82`, safe target paths, and no generated images stored in runtime assets before QA.
- Asset manifest reports `asset manifest: OK`, `assets: 82`, full current MVP content coverage across 6 heroes, 9 enemies, 18 skills, 15 items, 12 affixes, 5 resonances, Ember Crypt, node types, and UI states, with development-only ImageGen and local QA-passed runtime policy.
- Roadmap sync shows `docs/planning/OuroAgent_分步实现路线图_20260503.md` at `v0.4 release candidate`, with S6-S9 done and the remaining work expressed as external sign-offs rather than stale implementation phases.
- Real-provider smoke is optional for public mock-first release review: `scripts/provider_smoke.py` must report `network : not called` in preflight, `set (hidden)` when the env var is present, and `Live provider smoke OK.` only when `--live` completes without mock fallback.
- TUI shell spike is optional and non-invasive: `venv312/bin/python scripts/tui_shell_spike.py` reports `OURO TUI SHELL SPIKE`, keeps `current-ansi-renderer` as default, marks `rich-live` as the first optional adapter candidate, defers `textual-app-shell`, and adds no base dependency.
- Sign-off check reports pending user satisfaction, live-provider smoke, and git-boundary items instead of silently treating them as automated test failures; License is already ready.
- `git diff --check` has no output.
- Privacy scan reports no likely plaintext provider keys, bearer tokens, or secret assignments in release-bound text files.

## Manual Smoke Checklist

- `ouro menu --lang en` shows `MAIN MENU CONSOLE`, a recommended `ouro try --seed 1` next command, `Mock Path : mock-ready`, `PLAYER JOURNEY BOARD`, grouped entry commands, New Run, Try / Demo, Quick Battle, Codex, Runs, Death History, Replay, Doctor, and Configure.
- `ouro try --lang en --seed 1` shows menu status, hero card, deterministic mock battle, and Codex readback without trace or network; `ouro demo --lang en --seed 1` remains a compatibility alias.
- `ouro status --lang en` shows the profile, Codex progress, run/death totals, latest run, next-run plan, and next commands.
- `ouro list-heroes --lang en` shows 6 heroes with Build badges and risk labels.
- `ouro hero-card hero_shadow_apprentice --lang en` shows weapon, Build strategy, skills, tags, prompt contract, and risk.
- `ouro play --mock --seed 1 --no-animation --no-trace --lang en` prints turn-by-turn frames and a battle report.
- `ouro codex --lang en` displays saved monster knowledge after a mock battle, including `CODEX :: MONSTER ARCHIVE` and observed entries.
- `ouro run --mock --auto --seed 7 --no-animation --no-trace --lang en` prints route/reward/shop/rest context, floor labels, battle frames, run summary, run archive path, and death history path when dead.
- `ouro runs --lang en --limit 5` displays saved `.run.json` archives.
- `ouro history --lang en --limit 5` displays empty or populated death history without network access.
- `ouro replay examples/traces/mvp_a_seed7_mock.trace.jsonl --limit 6 --lang en` displays timeline, judge result, Echo Cost, and Result.
- `ouro batch --lang en --count 50 --seed 100 --quiet` displays budget and tempo metric keys.

## Privacy And Data Notes

- The config file stores `api_key_env`, never a plaintext API key.
- Run `ouro config preflight` after configuring a real provider; `ouro doctor` also runs this offline provider check. Both check env presence and base settings without network calls or key-value output.
- Traces, Codex progress, run archives, and death history must not contain `sk-`, bearer tokens, or raw provider secrets.
- `scripts/release_check.py` runs a release-bound privacy scan before tagging; placeholder docs such as `sk-...` are allowed, but realistic long tokens fail the gate.
- Mock mode must remain playable without API keys or network access.
- Real providers must be optional and may fail over to readable errors or configured fallback behavior.

## Tag Procedure

```bash
git status --short
git tag -a v0.1.0 -m "Ouro Agent v0.1.0"
git push origin v0.1.0
```

Before publishing the tag, confirm `CHANGELOG.md`, `README.md`, `README.zh.md`, `docs/product/06_需求追踪矩阵_20260503.md`, and `docs/product/23_QA证据与固定Seed试玩记录_20260601.md` all reference the same test count and release evidence.
Use `docs/engineering/CHANGESET_MANIFEST_20260601.md` to decide what belongs in the release commit and what must remain local-only.
Use `docs/engineering/RELEASE_SIGNOFF_20260601.md` and `scripts/signoff_check.py --strict` for the human/external sign-off audit.
The one-command gate is `venv312/bin/python scripts/release_check.py`.
