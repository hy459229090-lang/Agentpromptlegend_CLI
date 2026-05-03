# traces

Synthetic trace examples produced by the mock provider.

| File | How to regenerate |
|------|-------------------|
| `mvp_a_seed7_mock.trace.jsonl` | `ouro --lang en play --mock --seed 7 --trace-dir examples/traces` |
| `mvp_a_seed7_zh_mock.trace.jsonl` | `ouro play --mock --seed 7 --trace-dir examples/traces` (default zh) |

Traces are JSON Lines. Every record carries `run_id`, `battle_id`, and either
`turn_id` (hero turns) or `tick` + `actor_id` (enemy turns). Trace files are
written with `ensure_ascii=true` so non-ASCII narration becomes `\uXXXX`
sequences — that keeps the file safe to read in any encoding.

No API key, raw prompt, or environment value is ever written.
