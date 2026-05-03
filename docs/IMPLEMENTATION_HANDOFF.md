# Implementation Handoff

> Current state: design-ready, implementation pending.

## Goal

Build an installable command-line AI roguelike skeleton that can run a mock-provider battle without API keys.

## First Milestone

Complete **Slice 0 + Slice A** from `docs/product/06_需求追踪矩阵_20260503.md`.

### Slice 0

1. `REQ-DIST-001`: installable CLI package skeleton.
2. `REQ-DIST-002`: mock mode requires no API key.
3. `REQ-DIST-003`: README supports install and mock play.
4. `REQ-PROV-001`: provider config accepts mock/openai/anthropic/openai-compatible.
5. `REQ-PROV-002`: config supports model and base_url.
6. `REQ-PROV-003`: config stores env var names, not key values.
7. `REQ-ART-001`: ASCII-safe combat screen shell.
8. `REQ-CONTENT-001`: at least one hero card with ASCII avatar.

### Slice A

1. `REQ-BTL-001..005`: deterministic ATB combat loop.
2. `REQ-LLM-001..004`: action schema, fallback handling, prompt composer, mock model.
3. `REQ-DATA-001..002`: structured content and validation.
4. `REQ-TRC-001..002`: local battle trace and privacy-safe config.
5. `REQ-VAL-001`: repeatable fixed-seed mock battle.

## Suggested Tech Stack

Planning recommendation:

1. Python package with `pyproject.toml`.
2. `typer` for CLI.
3. `rich` for terminal panels.
4. `pydantic` or dataclasses plus explicit validation for data/schema.
5. `pytest` for tests.

This is a recommendation, not a permanent lock. If changed, update docs and explain why.

## Target Commands

```bash
ouro --version
ouro config show
ouro config set provider mock
ouro play --mock
ouro validate-content
```

## Evidence Required

Implementation is not complete until the repo contains evidence for:

1. command output,
2. tests,
3. local trace sample, or
4. documented playtest log.

