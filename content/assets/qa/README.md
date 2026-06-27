# content/assets/qa

Machine-readable QA records for generated asset candidates live here.

Do not store generated candidate images in this directory. Candidate images
stay in scratch/cache locations until an art review passes them; only QA-passed
runtime assets may be copied into `content/assets/` and enabled in
`manifest.yaml`.

Validate records from the repository root:

```bash
venv312/bin/python scripts/asset_qa_check.py --content-dir content
```
