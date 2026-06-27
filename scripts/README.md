# scripts

Development helper scripts.

- `release_check.py`: run the repo-root release gates (`pytest`,
  `ouro validate-content`, isolated doctor gate, version consistency,
  evidence count consistency, scope boundary, acceptance path, terminal graphics
  asset status, combat-stage graphics evidence, skill timeline coverage,
  `git diff --check`, and privacy scan) with `--dry-run`,
  `--doctor-only`, `--version-only`,
  `--evidence-only`, `--scope-only`, `--acceptance-only`, `--asset-status-only`,
  `--combat-stage-only`, `--timeline-coverage-only`,
  `--privacy-scan-only`, and optional clean install smoke via
  `--install-smoke-only` or `--install-smoke`. The asset status gate is
  informational by default; pass `--asset-status-strict` to require all
  manifest assets to have candidates, cut metadata, QA pass records, and
  runtime-enabled files. The combat-stage evidence gate verifies simulated
  iTerm2/Kitty/SIXEL bitmap filmstrips plus Unicode/ASCII fallback parity for the
  Hex Seal smoke timeline. The timeline coverage gate verifies all 18 MVP
  skills have display-only sprite timelines against QA-promoted runtime frames,
  with all six hero signature skills held to 12-beat authored timelines.
  The evidence count gate checks that pytest collection and release-bound
  privacy scan counts match the release docs. The install
  smoke also covers the guided try/demo path, Codex readback,
  run archive readback, compact run-report readback, death-history readback,
  status overview, and the next-run plan from the installed CLI.
- `release_scope.py`: audit `git status` paths against the release-candidate
  scope boundary. It classifies paths as release-bound, local-only, or unknown,
  returns nonzero for local-only or unknown paths, and never stages or commits.
  Add `--stage-plan` to print grouped, shell-quoted `git add -- ...` commands
  for release-bound paths only; the plan is read-only and does not mutate the
  git index.
- `completion_audit.py`: aggregate the release gates, strict asset hard gates,
  scope boundary, and external sign-off state into one final-goal readiness
  report. It returns nonzero while any required evidence remains pending,
  includes pending sign-off evidence/actions in `pending_items`, and does not
  replace user/live-provider/git sign-offs; License is checked dynamically from
  release metadata and is ready once the selected policy is fully synchronized.
  Even with `--skip-release-check`, it still runs asset status strict mode,
  asset QA, and asset manifest checks.
- `acceptance_check.py`: run the mock-first user acceptance command path as a
  concise report. It covers guided try/demo, blocked-home try storage fallback,
  graphics doctor, combat-stage parity, isolated fixed-seed full run, post-run
  visual report, and completion audit; it never writes `SIGN-OFF: accepted`.
  The completion-audit step parses JSON and shows `asset_hard_gates.ready: true`
  before reporting the external sign-offs that remain pending.
- `docs/engineering/LICENSE_DECISION_20260601.md`: records the selected MIT
  License policy and the release metadata that must stay synchronized.
- `provider_smoke.py`: optional real-provider preflight/live smoke helper.
  Default mode checks provider/model/base URL/env readiness without network
  calls or key-value output. `--live` runs one real-provider battle from a
  temporary `OURO_AGENT_HOME` and fails if the CLI falls back to mock.
- `tui_shell_spike.py`: optional Rich/Textual shell evaluation helper. It does
  not import network clients or change gameplay; it probes whether `rich` and
  `textual` are installed, records the fallback contract, and keeps the
  dependency-free ANSI renderer as the default until optional adapters have
  install, CI/pipe, snapshot, and accessibility evidence.
- `asset_manifest_check.py`: validate `content/assets/manifest.yaml` coverage,
  source brief aliases, QA gating, frame metadata, fallback IDs, and local
  runtime-asset policy for the terminal graphics asset pipeline. It returns
  nonzero when the manifest misses current content, points at a missing or
  mismatched ImageGen brief, enables an asset before `qa_passed`, references a
  missing runtime file, or violates the development-only ImageGen policy.
- `asset_work_orders.py`: emit deterministic development-time ImageGen work
  orders from the validated manifest and source brief catalog. It outputs JSONL
  or a compact summary, never calls ImageGen, never uses network, and keeps
  generated candidates outside runtime assets until QA passes.
- `asset_candidate_intake.py`: create a QA record template for one generated
  candidate from a work order. The template includes frame metadata dry-run,
  fallback cell IDs, and required QA checks, but leaves reviewer, review time,
  and runtime target blank until a real art review happens.
- `asset_sheet_cut.py`: cut a generated sprite-sheet candidate into scratch
  frame PNGs and cut metadata using the manifest frame order. It removes
  chroma-key green backgrounds, records visible bounds, refuses to write under
  `content/assets/` by default, and does not promote runtime assets.
- `asset_promote_candidate.py`: after art QA approval, copy one cut candidate
  into `content/assets/runtime/`, rewrite frame paths to portable relative
  paths, and write a `qa_passed` record. It intentionally does not edit
  `manifest.yaml`; the manifest promotion is reviewed separately.
- `asset_qa_check.py`: validate machine-readable QA records for generated asset
  candidates. It accepts zero records, but any `qa_passed` record must include
  reviewer, review time, all family QA checks, complete frame metadata, and a
  safe runtime target path under `content/assets/`.
- `asset_status_report.py`: report current asset pipeline readiness across
  manifest entries, generated candidate QA records, cut metadata, QA-passed
  assets, and runtime-enabled assets. Default mode is informational; strict
  flags such as `--require-all-candidates`, `--require-all-qa-passed`, and
  `--require-all-runtime` turn missing work into a failing gate for release
  checks.
- `record_combat_stage.py`: write deterministic terminal graphics evidence for
  the Hex Seal smoke timeline. It emits a summary, simulated iTerm2/Kitty/SIXEL
  bitmap filmstrips with runtime PNG fingerprints, Unicode filmstrip, and
  ASCII filmstrip from `SpriteAtlas`/`AnimationTimeline`, optionally overlaying
  development-time cut metadata; QA-promoted runtime metadata is loaded from
  the manifest automatically.
- `timeline_coverage_report.py`: validate that every current MVP skill can
  build a catalog combat-stage timeline from QA-promoted runtime atlas frames.
  It requires the six hero signature skills to use 12-beat authored timelines
  while ordinary MVP skills keep the compact 8-beat fallback. Use
  `--require-all-skills` to fail on missing/invalid skill timelines.
- `signoff_check.py`: report human/external sign-offs still required before
  marking the larger goal complete. It dynamically checks License metadata,
  README policy text, explicit user/live-provider sign-off marker files, and
  git working-tree state. The satisfaction item includes acceptance commands
  for guided try/demo, graphics doctor, graphics auto play, combat-stage parity,
  fixed-seed full run, post-run visual report, optional Chinese
  status/Codex/run-report review, and completion audit. The git-boundary
  item includes the release scope count summary and points to
  `release_scope.py --stage-plan` for a read-only staging command plan. Default
  mode is informational; `--strict` returns nonzero while sign-offs remain
  pending, and `--json` emits a machine-readable report. Marker
  templates live at
  `docs/engineering/USER_ACCEPTANCE_20260601.md` and
  `docs/engineering/PROVIDER_LIVE_SMOKE_20260601.md`; the License record lives
  at `docs/engineering/LICENSE_DECISION_20260601.md`.
- `play-real.sh`: configure the DashScope Anthropic bridge from environment
  variables and start a real-provider battle. It never stores the API key;
  it only saves the `OURO_API_KEY` environment variable name.
