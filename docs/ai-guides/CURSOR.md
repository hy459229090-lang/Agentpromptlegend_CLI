# Cursor Guide — Agent Prompt Legend CLI

## Objective

Use Cursor to implement the repo from the documented requirements, not from inferred behavior. The product is an installable CLI roguelike with model-provider configuration and a mock-model combat loop.

## Read Before Editing

1. `AGENTS.md`
2. `docs/product/00_策划案索引_20260503.md`
3. `docs/product/02_设计基线与术语表_20260503.md`
4. `docs/product/06_需求追踪矩阵_20260503.md`
5. `docs/IMPLEMENTATION_HANDOFF.md`

## Cursor Working Rules

1. Work requirement-by-requirement using `REQ-*` IDs.
2. Keep code changes tied to Slice 0 and Slice A until those pass.
3. Use relative project paths in docs and code.
4. Never store API keys in config files.
5. Mock mode must work without network.
6. Default UI must be ASCII-safe.
7. Add tests or command-output evidence with each finished requirement.

## Recommended First Prompt For Cursor

```text
Read AGENTS.md, docs/product/06_需求追踪矩阵_20260503.md, and docs/IMPLEMENTATION_HANDOFF.md.
Implement only Slice 0 requirements first: REQ-DIST-001..003, REQ-PROV-001..003, REQ-ART-001, REQ-CONTENT-001.
Do not implement real provider calls yet. Keep mock provider working without API keys.
After implementation, show commands and evidence for ouro --version, ouro config show, and ouro play --mock.
```

