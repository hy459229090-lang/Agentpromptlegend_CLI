# License Decision - Ouro Agent v0.1.0

> Status: selected.
> Decision: MIT License.

The project owner selected MIT on 2026-06-11. This record keeps the release
policy explicit so packaging metadata, README copy, release handoff, and
`signoff_check.py` all agree.

## Decision

- Decision owner: project owner / RicHe
- Date: 2026-06-11
- Selected License or policy: MIT License
- Rationale: short permissive open-source license, straightforward for a CLI
  game, examples, packaging, and downstream experiments.
- Files updated:
  - `LICENSE`
  - `pyproject.toml`
  - `README.md`
  - `README.zh.md`
  - `docs/engineering/RELEASE_HANDOFF_20260601.md`
  - `docs/engineering/RELEASE_SIGNOFF_20260601.md`
  - `docs/product/24_最终产品验收审计_20260601.md`
  - `scripts/release_check.py`
  - `scripts/release_scope.py`
- Follow-up issues: none for License. User satisfaction, live-provider smoke,
  and git-boundary sign-offs remain separate release items.

## Sign-Off

`signoff_check.py` marks License ready when pending License language is removed
from release metadata and either a root `LICENSE` file or a documented private
distribution policy exists.

SIGN-OFF: selected
