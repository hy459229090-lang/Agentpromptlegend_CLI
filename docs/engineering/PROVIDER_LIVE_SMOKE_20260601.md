# Provider Live Smoke - Ouro Agent v0.1.0

> Status: pending live-provider review.
> This file is intentionally not passed yet.

The release candidate is mock-first and can be reviewed without network
access. A real-provider smoke is optional, but if it is used as final release
evidence it must be run with a user-provided environment variable and without
recording the key value.

## Safe Preflight

These commands do not call the network and must not print the secret value:

```bash
venv312/bin/python scripts/provider_smoke.py --provider openai --model gpt-test --api-key-env OPENAI_API_KEY
env OURO_API_KEY=redacted-test-key venv312/bin/python scripts/provider_smoke.py --provider openai-compatible --model smoke-test --api-key-env OURO_API_KEY --base-url https://example.invalid
```

Expected preflight properties:

- missing env returns `NOT READY`,
- present env displays `set (hidden)`,
- output includes `network : not called`,
- no API key value is printed or written.

## Safe Preflight Record

2026-06-18 agent-side preflight was rerun without marking live-provider
sign-off:

| Command | Return | Evidence |
| --- | ---: | --- |
| `venv312/bin/python scripts/provider_smoke.py --provider openai --model gpt-test --api-key-env OPENAI_API_KEY` | `3` | `env value : MISSING`, `network : not called`, `status : NOT READY`; no API key value printed |
| `env OURO_API_KEY=redacted-test-key venv312/bin/python scripts/provider_smoke.py --provider openai-compatible --model smoke-test --api-key-env OURO_API_KEY --base-url https://example.invalid` | `0` | `env value : set (hidden)`, `network : not called`, `status : READY`; redacted placeholder only |

This proves the preflight helper avoids network calls and hides configured env
values. It does not satisfy the live-provider sign-off below.

## Live Smoke Command

After setting the real provider key in the shell, run a command like:

```bash
export OURO_API_KEY="<set outside this file>"
venv312/bin/python scripts/provider_smoke.py --live --provider openai-compatible --model "<model>" --api-key-env OURO_API_KEY --base-url "<base-url>"
```

Use the provider/model/base URL that the user actually wants to validate.
Do not paste the key into this file, README, config, trace, or terminal logs.

## Result Record

- Date:
- Provider:
- Model:
- API key env var:
- Command:
- Result:
- Evidence summary:
- Follow-up issues:

## Sign-Off

Leave the following line as `pending` until live smoke completes without mock
fallback and without leaking the key. To mark this item ready, change it
exactly to: `SIGN-OFF: passed`.

SIGN-OFF: pending
