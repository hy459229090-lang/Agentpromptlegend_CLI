# runtime Rules

1. Store only QA-approved runtime assets referenced by `manifest.yaml`.
2. Every asset here must have a `qa_passed` record under `content/assets/qa/`.
3. Keep frame paths portable; do not store `/private/tmp`, `/Users`, `file://`,
   cache paths, or secrets in runtime metadata.
4. Preserve ASCII/Unicode fallback IDs for every bitmap frame.
5. Do not store rejected or generated-only candidates in this directory.
