# Agent Prompt Legend CLI / 暗影代理：祷文传说

> A bilingual command-line AI roguelike. The player configures one hero
> Agent (skills, equipment, traits, battle prompt); combat then runs
> automatically through a model-chosen action plus a deterministic local
> judge. The model **never** decides damage, drops, or victory.

中文说明请见 **[README.zh.md](README.zh.md)**.

[![tests](https://img.shields.io/badge/tests-65%20passing-brightgreen)]() [![python](https://img.shields.io/badge/python-3.11%2B-blue)]() [![providers](https://img.shields.io/badge/providers-mock%20%7C%20openai%20%7C%20anthropic%20%7C%20openai--compatible-orange)]()

---

## Status

| Slice | What | State |
|-------|------|-------|
| 0 | Installable CLI, provider config, ASCII-safe screen | done |
| A | Deterministic ATB battle, action schema, mock model, trace | done |
| i18n | Bilingual UI / content / mock narration (zh default, --lang en) | done |
| Provider | Real `openai`, `anthropic`, `openai-compatible` adapters + auto fallback | done |
| B | 3 heroes, 9 skills, 6 items, 6 affixes, 2 resonances, build resolver | done |
| D | Dungeon, route, shop, rewards (full roguelike loop playable) | done |
| C0 | BattleLLMSession, static context / turn delta, session trace | next |
| C1 | Build panel, Buff/Debuff UI, monster tier, codex stage | next |
| C2 | 6 heroes, monster families, tiered codex/content schema | planned |
| E | Codex, run save, death persistence | planned |
| F | Batch playtest + balance stats | planned |

`76 tests passing`. No real network calls in any test.

---

## Recent Development (2026-05-06)

### Slice D - Full Roguelelike Loop (Completed)

**What was implemented:**

1. **Content Data** (`content/dungeons/mvp_dungeons.yaml`)
   - Created the first dungeon: "Ember Crypt" (灰烬墓室)
   - 3 floors with 5 nodes: normal combat, shop, boss
   - Reward choices and shop items defined

2. **Schema Extensions** (`src/ouro_agent/content/schema.py`)
   - Added `DungeonData`, `DungeonFloor`, `NodeData`, `NodeRewards`, `RewardChoice`, `ShopItem`
   - Added `ID_PREFIXES` for dungeon and node
   - Extended `ContentBundle` to include `dungeons` and `nodes`

3. **Content Loader** (`src/ouro_agent/content/loader.py`)
   - Added loading logic for dungeons and nodes
   - Added reference validation: enemy IDs, item IDs, affix IDs

4. **Run State Management** (`src/ouro_agent/sessions/run_state.py`)
   - `RunPhase` enum: START, ROUTE_CHOICE, NODE_ACTION, REWARD_CHOICE, SHOP, REST, EVENT, COMPLETE, DEAD
   - `RunState` class: tracks dungeon progress, hero state, resources, history
   - `create_run_state()`: factory function for initializing runs

5. **CLI Run Command** (`src/ouro_agent/cli/main.py`)
   - New `run` command for full roguelike gameplay
   - Arguments: `--mock`, `--seed`, `--hero`, `--dungeon`, `--auto`, `--no-animation`, `--delay`, `--no-trace`, `--prompt-style`
   - Integrated with existing battle loop

6. **TUI Screens** (`src/ouro_agent/tui/screens.py`)
   - `render_route_choice()`: displays available nodes to choose from
   - `render_reward_choice()`: displays rewards after victory
   - `render_shop()`: displays shop items for purchase
   - `render_run_summary()`: displays final run stats

7. **Enhanced Action System** (`src/ouro_agent/tui/screens.py`)
   - Extended `_actor_pose()`: supports attack, skill_shadow, skill_fire, skill_physical, skill_holy, skill_poison, defend, observe
   - Enhanced `_effect_lane()`: shows damage numbers, miss, status effects (SILENCE, CORRUPT, POISON, BLEED, FIRE, SHIELD)
   - Rewrote `_hero_sprite()`: 6 heroes × 12 poses each
   - Rewrote `_enemy_sprite()`: 2 enemies × 7 poses each

8. **Enhanced Bars** (`src/ouro_agent/art/glyphs.py`)
   - `hp_bar()`: state indicators (healthy/wounded/critical), different borders/shapes, percentage display
   - `mp_bar()`: low/empty indicators, different borders
   - `atb_bar()`: ready indicator, charging display
   - `shield_indicator()`: compact shield display
   - `status_indicator()`: compact status effect display

9. **Terminal Control** (`src/ouro_agent/tui/terminal.py`)
   - `Terminal` class: ANSI escape code helpers for clearing, cursor control, refresh mode
   - `get_terminal()`: factory function

**How to Play:**

```bash
# Auto-run with mock (for testing)
ouro --lang zh run --mock --auto

# Interactive run
ouro --lang zh run --mock

# Run with real LLM (requires provider config)
ouro --lang zh run --auto
```

---

## Quickstart

Requires Python 3.11+.

```bash
pip install -e .

ouro --version
ouro list-heroes
ouro hero-card hero_ash_guardian
ouro play --mock --seed 1                                  # Astia, Chinese (default)
ouro play --mock --seed 1 --hero hero_broken_string_hunter # Vela
ouro --lang en play --mock --seed 1                        # English, ASCII-safe
```

Eventual GitHub install:

```bash
pipx install git+https://github.com/hy459229090-lang/Agentpromptlegend_CLI.git
ouro play --mock
```

---

## Languages

The CLI ships in both Chinese and English. Stable IDs
(`hero_shadow_apprentice`, `skill_shadow_sting`, ...) are always English;
only player-visible text is bilingual.

| Mode | Use |
|------|-----|
| 中文 (default) | `ouro play --mock` |
| English (ASCII-safe) | `ouro --lang en play --mock` or `ouro config set language en` |

* The Chinese surface needs a UTF-8 capable terminal. On Windows: Windows
  Terminal, or `chcp 65001` + `$env:PYTHONIOENCODING="utf-8"`.
* The English surface stays strictly ASCII-safe — works in legacy
  PowerShell and CI.

---

## Real Provider Adapters

API keys are **never** stored in config files. The config holds the
**name** of an environment variable (e.g. `OPENAI_API_KEY`); the value is
read from `os.environ` at call time.

If a real provider fails mid-battle (network, auth, timeout), the engine
finishes the rest of the battle on the local mock and prints a single
note. The local judge keeps full control of damage and victory either way.

### OpenAI

```bash
setx OPENAI_API_KEY "sk-..."
ouro config set provider openai
ouro config set model gpt-4o-mini
ouro play --seed 1
```

### Anthropic

```bash
setx ANTHROPIC_API_KEY "sk-ant-..."
ouro config set provider anthropic
ouro config set model claude-sonnet-4-5
ouro play --seed 1
```

### OpenAI-compatible (custom base URL)

```bash
setx OURO_API_KEY "..."
ouro config set provider openai-compatible
ouro config set base_url https://your-host.example.com/v1
ouro config set api_key_env OURO_API_KEY
ouro config set model your-model-name
ouro play --seed 1
```

---

## Testing

```bash
pip install -e ".[dev]"
pytest -q
```

| Test file | Coverage |
|-----------|----------|
| `tests/unit/test_battle.py` | ATB / MP / cooldown / win-loss / shield |
| `tests/unit/test_action_validator.py` | JSON repair, unknown action / skill, empty fallback |
| `tests/unit/test_config.py` | Safe config (rejects plaintext key, rejects legacy plaintext fields) |
| `tests/unit/test_content_loader.py` | YAML schema + bilingual fallback + ID-prefix checks |
| `tests/unit/test_i18n.py` | Chinese labels / English ASCII-safe / CJK width padding |
| `tests/unit/test_build.py` | 3 heroes / 6 items / 6 affixes / 2 resonances / build resolver |
| `tests/unit/test_providers.py` | OpenAI / Anthropic / compatible wires + fallback (mocked HTTP) |
| `tests/integration/test_mock_battle.py` | Fixed-seed reproducibility + trace + ASCII-safe combat screen |

---

## How safety works

| Rule | Where it is enforced |
|------|---------------------|
| The model never decides damage, drops, or victory | `engine/judge.py` is the only damage source |
| Mock requires no network and no API key | `providers/mock.py` does not import any SDK or http |
| Config must not store a plaintext key | `config/store.py` blocks `api_key`, `secret`, etc. and rejects `sk-` style values for `api_key_env` |
| Trace files never contain a key | `trace/writer.py` writes provider name + model only |
| Real provider failure cannot crash a battle | `providers/registry.FallbackOnErrorProvider` switches to mock for the rest of the battle |
| Default UI must be readable in any terminal | `--lang en` keeps the screen 100% ASCII; `tests/test_i18n.py::test_battle_screen_en_remains_ascii_safe` asserts `text.isascii()` |

---

## Architecture in 30 seconds

```
                +---------------------+
ouro play --->  |  CLI (cli/main.py)  |
                +----------+----------+
                           |
                  +--------v---------+        +-----------------------+
                  | Provider adapter |<-----> | mock / openai /       |
                  | (Provider iface) |        | anthropic / compat    |
                  +--------+---------+        +-----------------------+
                           |
                           | ModelTurnResult (raw_text + token usage)
                           v
                  +----------------+
                  | llm.validator  |   parses + repairs + falls back
                  +-------+--------+
                          |
                          | HeroAction (validated)
                          v
                  +----------------+        +------------------+
                  | engine.judge   |<------ | engine.battle    |
                  | (only damage)  |        | (ATB loop)       |
                  +-------+--------+        +---------+--------+
                          |                            |
                          v                            v
                  BattleState mutation         tui/screens (read-only)
                                               trace/writer (jsonl)
```

* `src/ouro_agent/engine/` — deterministic combat. Never imports a
  provider SDK, never imports a TUI module.
* `src/ouro_agent/providers/` — wire-format adapters. Never imports
  combat internals.
* `src/ouro_agent/llm/` — prompt composition + action schema +
  validator. Hides the provider's raw text from the engine.
* `src/ouro_agent/i18n/` — bilingual UI labels, log templates, and CJK
  width helper.
* `content/` — all game data as YAML, bilingual `display_name` etc.

Full layout: [docs/engineering/CODE_LAYOUT.md](docs/engineering/CODE_LAYOUT.md).

---

## Repository Map

```text
README.md / README.zh.md      Bilingual front pages
AGENTS.md / CLAUDE.md         Coding-agent rules (must read before editing)
pyproject.toml                Installable package (entrypoint: `ouro`)
src/ouro_agent/               Runtime code, split by responsibility
content/                      Game data (heroes, skills, enemies, items, affixes, resonances)
tests/                        Unit + integration tests
examples/                     Example configs + sample trace files
docs/                         Product, planning, engineering, AI-handoff docs
scripts/                      Developer helper scripts
```

Every project directory has a local `README.md` and `_rules.md`. Coding
agents should read the nearest `_rules.md` before adding or moving files.

---

## Roadmap

Next ready slices (in order of recommended priority):

1. **Slice C0** — `BattleLLMSession`, static context / turn delta,
   session trace, context reuse metrics.
2. **Slice C1** — Build panel, Buff/Debuff groups, monster tier, codex
   stage, no-color snapshot stability.
3. **Slice C2** — six-hero content plan, monster families, three-tier
   monster variants, codex schema.
4. **Slice D** — dungeons, routes, shops, rewards (so a full run becomes
   playable).
5. **Slice E** — Codex progress, death handling, run/codex save files.
6. **Slice F** — `ouro batch` with seed sweeps and balance stats.

See the requirement matrix:
[docs/product/06_需求追踪矩阵_20260503.md](docs/product/06_需求追踪矩阵_20260503.md).

---

## Provider Reference Docs

- [OpenAI Chat Completions](https://platform.openai.com/docs/api-reference/chat/create)
- [OpenAI authentication](https://platform.openai.com/docs/api-reference/authentication)
- [Anthropic Messages API](https://docs.anthropic.com/en/api/messages)
- [Anthropic Messages examples](https://docs.anthropic.com/en/api/messages-examples)

---

## License

License is not selected yet.
