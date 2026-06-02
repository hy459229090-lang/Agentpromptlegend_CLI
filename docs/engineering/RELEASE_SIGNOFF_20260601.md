# Release Sign-Off Checklist - v0.1.0

> Date: 2026-06-01  
> Purpose: keep external decisions separate from automated release gates.

The build can pass automated gates while still needing human or external
sign-off before the larger user goal is marked complete. Run:

```bash
venv312/bin/python scripts/signoff_check.py
venv312/bin/python scripts/signoff_check.py --strict
venv312/bin/python scripts/signoff_check.py --json
```

Default mode reports the current sign-off state without failing. `--strict`
returns nonzero while any sign-off remains pending. `--json` emits the same
state as a machine-readable report for CI or release notes.

The checker is dynamic: it reads the current License metadata, README license
language, git working-tree state, and explicit sign-off marker files. It still
keeps unverifiable human/external approvals pending unless those marker files
exist with the exact accepted/passed line.
For user satisfaction review, it includes `acceptance command` details for the
guided demo, isolated fixed-seed full run, and completion audit.
`venv312/bin/python scripts/acceptance_check.py` runs that mock-first review
path as one concise report and still leaves `SIGN-OFF: pending`.
For git-boundary review, it also echoes the current release scope summary and
points to `venv312/bin/python scripts/release_scope.py --stage-plan` so staging
can be reviewed from a generated, read-only command plan.

## Pending Sign-Offs

| Item | Current State | Ready Evidence | Required Action |
| --- | --- | --- | --- |
| User satisfaction | Agent playtest is recorded and `docs/engineering/USER_ACCEPTANCE_20260601.md` exists as a pending template, but user acceptance is not yet provided; `signoff_check.py` prints acceptance commands for the review path. | `docs/engineering/USER_ACCEPTANCE_20260601.md` contains `SIGN-OFF: accepted`. | Run the acceptance commands, play or explicitly accept the current build, then update the template sign-off line. |
| License | `pyproject.toml`, README, and README.zh still state that License is pending; `docs/engineering/LICENSE_DECISION_20260601.md` exists as a pending decision template. | Pending language removed, plus either a `LICENSE` file or documented private/internal distribution policy. | Choose a license or private/internal distribution policy, then update the template and release metadata. |
| Live provider smoke | Provider preflight, optional live-smoke helper, and `docs/engineering/PROVIDER_LIVE_SMOKE_20260601.md` pending template exist; no user key is available here. | `docs/engineering/PROVIDER_LIVE_SMOKE_20260601.md` contains `SIGN-OFF: passed`. | Run `scripts/provider_smoke.py --live` after setting the configured API-key env var, then update the template sign-off line. |
| Git boundary | Changeset manifest defines intended release scope; `scripts/release_scope.py --stage-plan` prints a read-only grouped staging plan; current `git status --short` still reports changed paths. | `git status --short --untracked-files=all` is clean after intentional staging/commit. | Review `git status --short`, run `venv312/bin/python scripts/release_scope.py --stage-plan`, stage release files, commit, then tag. |

These items should not be hidden inside the automated mock-first release gate.
They are product/release sign-offs, not code failures.
