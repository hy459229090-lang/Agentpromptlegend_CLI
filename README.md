# Agent Prompt Legend CLI

**Agent Prompt Legend CLI** is a planned command-line AI roguelike. The player configures one hero Agent with skills, equipment, traits, and a battle prompt; combat then runs automatically through model-chosen actions and deterministic local rules.

Current status: **design-ready / implementation handoff**. The repository now contains the product design, implementation gates, AI coding guides, and first-slice requirement matrix. Runtime code is the next step.

## Product Direction

- Single-player CLI roguelike.
- One configurable hero, not a party.
- Player acts between fights: choose route, shop, equipment, prompt changes.
- Combat is automatic: the model chooses structured actions.
- Local engine validates actions and resolves damage, cooldowns, rewards, and victory.
- Mock mode must run without API keys.
- OpenAI, Anthropic, and OpenAI-compatible providers are planned through a provider adapter.

## First Implementation Target

The first milestone is **Slice 0 + Slice A**:

- installable CLI skeleton,
- `ouro --version`,
- `ouro config show`,
- `ouro play --mock`,
- provider configuration for `mock`, `openai`, `anthropic`, and `openai-compatible`,
- ASCII-safe combat screen shell,
- deterministic ATB battle loop,
- model action schema,
- mock model,
- local battle trace.

See [Implementation Handoff](docs/IMPLEMENTATION_HANDOFF.md) and [Requirement Matrix](docs/product/06_需求追踪矩阵_20260503.md).

## Target Install Flow

These commands describe the intended player experience after Slice 0 is implemented:

```bash
pipx install git+https://github.com/hy459229090-lang/Agentpromptlegend_CLI.git
ouro --version
ouro play --mock
```

Provider configuration target:

```bash
ouro config set provider openai
ouro config set model <model-name>
ouro play
```

```bash
ouro config set provider anthropic
ouro config set model <model-name>
ouro play
```

```bash
ouro config set provider openai-compatible
ouro config set api_key_env OURO_API_KEY
ouro config set base_url https://example.com/v1
ouro config set model <model-name>
ouro play
```

API keys must be provided through environment variables. The game should store environment variable names, not plaintext keys.

## Visual Direction

The terminal UI should be dark, readable, and fast:

- ASCII-safe by default,
- optional Unicode enhancement,
- optional color,
- no-color mode for compatibility,
- low redraw frequency,
- animation can be disabled,
- game-flavored model usage display:
  - `Echo Cost` for total tokens,
  - `Read Echo` for input tokens,
  - `Spoken Echo` for output tokens,
  - `Ritual Time` for latency.

## Repository Map

```text
AGENTS.md                     AI implementation rules
CLAUDE.md                     Claude Code entry guide
docs/IMPLEMENTATION_HANDOFF.md First implementation package
docs/ai-guides/               Cursor and Claude Code guides
docs/product/                 Product design and requirement docs
docs/planning/                Planning and collaboration rules
```

## For Cursor / Claude Code

Start here:

- [AGENTS.md](AGENTS.md)
- [CLAUDE.md](CLAUDE.md)
- [Cursor Guide](docs/ai-guides/CURSOR.md)
- [Claude Code Guide](docs/ai-guides/CLAUDE_CODE.md)

Do not implement features outside ready `REQ-*` items in the requirement matrix.

## Provider References

- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses/create?api-mode=responses)
- [OpenAI authentication](https://platform.openai.com/docs/api-reference/authentication?api-mode=responses)
- [Anthropic Messages API](https://docs.anthropic.com/en/api/messages)
- [Anthropic Messages examples](https://docs.anthropic.com/en/api/messages-examples)

## License

License is not selected yet.
