# content/assets

QA-approved runtime assets for terminal graphics live here.

This directory is not a demo asset bucket. `manifest.yaml` is the full MVP
asset production ledger and must cover every current hero, enemy, skill, item,
affix, resonance, dungeon/node stage, and UI state.
`source_briefs/` contains the development-time ImageGen prompt families and
per-asset aliases referenced by `source_brief`.

Current status: entries may be `planned`, but planned entries are not
runtime-enabled until generated candidates pass art QA, have frame metadata,
and have Unicode/ASCII fallback mappings.

The full current MVP asset set is QA-promoted into runtime assets: heroes,
enemies, skills, items, affixes, resonances, dungeon/node stage plates, and UI
state sprites. This proves the path from generated candidate to repo-local
runtime metadata for every manifest entry. Live battle/reward/shop/build UI may
still need explicit timeline or screen integration before every bitmap appears
in ordinary play.

Validate coverage from the repository root:

```bash
venv312/bin/python scripts/asset_manifest_check.py --content-dir content
```

Emit development-time ImageGen work orders without calling ImageGen:

```bash
venv312/bin/python scripts/asset_work_orders.py --content-dir content --format summary
venv312/bin/python scripts/asset_work_orders.py --content-dir content --output /private/tmp/ouro_asset_work_orders.jsonl
```

Validate generated-candidate QA records:

```bash
venv312/bin/python scripts/asset_qa_check.py --content-dir content
```

Create a generated-candidate QA template with frame metadata dry-run:

```bash
venv312/bin/python scripts/asset_candidate_intake.py \
  --content-dir content \
  --work-order-id wo_skill_hex_seal_effect_sheet \
  --candidate-id cand_hex_seal_001 \
  --candidate-ref generated-cache://hex_seal_001 \
  --output /private/tmp/ouro_hex_seal_candidate_qa.yaml
```

Cut a generated sprite-sheet candidate into scratch frame PNGs and cut metadata
without promoting runtime assets:

```bash
venv312/bin/python scripts/asset_sheet_cut.py \
  --content-dir content \
  --work-order-id wo_hero_shadow_apprentice_battle_sheet \
  --candidate-id cand_hero_shadow_apprentice_001 \
  --candidate-png /private/tmp/ouro_asset_candidates/hero_shadow_apprentice_001.png \
  --output-dir /private/tmp/ouro_asset_candidates/cut_frames
```

Promote a reviewed candidate into runtime assets and write a QA record:

```bash
venv312/bin/python scripts/asset_promote_candidate.py \
  --content-dir content \
  --cut-metadata /private/tmp/ouro_asset_candidates/cut_frames/hero_shadow_apprentice_battle_sheet/cand_hero_shadow_apprentice_001/cut_metadata.yaml \
  --reviewer codex-art-pipeline-smoke \
  --reviewed-at 2026-06-18T00:00:00Z \
  --candidate-ref generated-cache://cand_hero_shadow_apprentice_001 \
  --approve-all-checks
```
