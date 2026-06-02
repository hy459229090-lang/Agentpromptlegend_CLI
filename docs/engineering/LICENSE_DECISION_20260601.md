# License Decision - Ouro Agent v0.1.0

> Status: pending user decision.
> This file is intentionally not selected yet.

The release candidate is technically ready for mock-first review, but public
distribution still needs an explicit License or private/internal distribution
policy. This decision must come from the project owner; implementation work
must not silently choose a License.

## Options To Choose From

Common public options:

- MIT: short permissive license, easy for examples and small tools.
- Apache-2.0: permissive license with explicit patent language.

Private/internal options:

- Private distribution only: document that the repository/package is not for
  public redistribution.
- Internal-only distribution: document who may install and share the package.

## Files To Update After Decision

For a public open-source License:

1. Add a root `LICENSE` file with the selected License text.
2. Update `pyproject.toml` `[project].license`.
3. Replace the README and README.zh pending License text.
4. Update `docs/engineering/RELEASE_HANDOFF_20260601.md`.
5. Run `venv312/bin/python scripts/signoff_check.py --json`.

For private/internal distribution:

1. Keep or set `pyproject.toml` to an explicit private policy text.
2. Replace the README and README.zh pending License text with the policy.
3. Update `docs/engineering/RELEASE_HANDOFF_20260601.md`.
4. Run `venv312/bin/python scripts/signoff_check.py --json`.

## Decision Record

- Decision owner:
- Date:
- Selected License or policy:
- Rationale:
- Files updated:
- Follow-up issues:

## Sign-Off

Leave the following line as `pending` until the project owner chooses a License
or private/internal distribution policy and updates the files above. This
template alone is not enough for `signoff_check.py` to mark License ready.

SIGN-OFF: pending
