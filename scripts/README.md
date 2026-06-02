# scripts

Development helper scripts.

- `release_check.py`: run the repo-root release gates (`pytest`,
  `ouro validate-content`, isolated doctor gate, version consistency,
  evidence count consistency, scope boundary, acceptance path, `git diff --check`,
  and privacy scan) with `--dry-run`, `--doctor-only`, `--version-only`,
  `--evidence-only`, `--scope-only`, `--acceptance-only`,
  `--privacy-scan-only`, and optional clean install smoke via
  `--install-smoke-only` or `--install-smoke`. The evidence count gate checks
  that pytest collection and release-bound privacy scan counts match the
  release docs. The install smoke also covers the guided demo, Codex readback,
  run archive readback, compact run-report readback, death-history readback,
  status overview, and the next-run plan from the installed CLI.
- `release_scope.py`: audit `git status` paths against the release-candidate
  scope boundary. It classifies paths as release-bound, local-only, or unknown,
  returns nonzero for local-only or unknown paths, and never stages or commits.
  Add `--stage-plan` to print grouped, shell-quoted `git add -- ...` commands
  for release-bound paths only; the plan is read-only and does not mutate the
  git index.
- `completion_audit.py`: aggregate the release gates, scope boundary, and
  external sign-off state into one final-goal readiness report. It returns
  nonzero while any required evidence remains pending, includes pending sign-off
  evidence/actions in `pending_items`, and does not replace
  user/license/live-provider/git sign-offs.
- `acceptance_check.py`: run the mock-first user acceptance command path as a
  concise report. It covers guided demo, isolated fixed-seed full run, and
  completion audit; it never writes `SIGN-OFF: accepted`.
- `docs/engineering/LICENSE_DECISION_20260601.md`: pending template for the
  project owner to choose a public License or private/internal distribution
  policy; it is guidance only until release metadata is updated.
- `provider_smoke.py`: optional real-provider preflight/live smoke helper.
  Default mode checks provider/model/base URL/env readiness without network
  calls or key-value output. `--live` runs one real-provider battle from a
  temporary `OURO_AGENT_HOME` and fails if the CLI falls back to mock.
- `signoff_check.py`: report human/external sign-offs still required before
  marking the larger goal complete. It dynamically checks License metadata,
  README policy text, explicit user/live-provider sign-off marker files, and
  git working-tree state. The satisfaction item includes acceptance commands
  for guided demo, fixed-seed full run, and completion audit. The git-boundary
  item includes the release scope count summary and points to
  `release_scope.py --stage-plan` for a read-only staging command plan. Default
  mode is informational; `--strict` returns nonzero while sign-offs remain
  pending, and `--json` emits a machine-readable report. Pending marker
  templates live at
  `docs/engineering/USER_ACCEPTANCE_20260601.md` and
  `docs/engineering/LICENSE_DECISION_20260601.md` and
  `docs/engineering/PROVIDER_LIVE_SMOKE_20260601.md`.
- `play-real.sh`: configure the DashScope Anthropic bridge from environment
  variables and start a real-provider battle. It never stores the API key;
  it only saves the `OURO_API_KEY` environment variable name.
