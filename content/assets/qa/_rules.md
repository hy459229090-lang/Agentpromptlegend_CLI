# qa Rules

1. Store QA records only; do not store generated candidate images here.
2. A `qa_passed` record must include reviewer, review time, all required QA checks, and frame metadata.
3. `runtime_target_path` is allowed only for `qa_passed` records and must stay under `content/assets/`.
4. Rejected or generated candidates must not enable runtime manifest assets.
5. Do not include secrets, local player data, private absolute paths, or third-party brand replicas.
