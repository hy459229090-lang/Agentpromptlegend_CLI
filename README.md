# Agent Prompt Legend CLI / 暗影代理：祷文传说

**Language / 语言**: [中文](#中文) | [English](#english) | [完整中文文档](README.zh.md)

[![tests](https://img.shields.io/badge/tests-345%20passing-brightgreen)]() [![python](https://img.shields.io/badge/python-3.11%2B-blue)]() [![providers](https://img.shields.io/badge/providers-mock%20%7C%20openai%20%7C%20anthropic%20%7C%20openai--compatible-orange)]()

---

## 中文

### AI 会自己下副本，你负责把它训练成英雄

**暗影代理：祷文传说** 是一款命令行 AI 肉鸽。你不在战斗中手动点技能，
而是在战前配置英雄、装备、词条、Prompt 和战术风格，然后观看这个 Agent
自动战斗。模型只负责选择结构化行动；本地引擎负责校验行动、结算伤害、
状态、胜负、奖励和长期存档。

这不是聊天机器人套壳。它的核心玩法是：**让 AI 决策变得可观看、可复盘、
可调教**。

| 类型 | 当前状态 | 试玩门槛 |
|------|----------|----------|
| CLI roguelike / auto-battler / prompt-building game | MVP release candidate | 默认 mock，无需网络，无需 API key |

### 游戏画面

真实 TUI 输出，来自 `ouro --lang en play --mock --seed 2 --unicode --no-trace`：

```text
█▀▀ THE ECHO ALTAR / COUNTER WINDOW ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀█
█ HERO [CNDL] Astia        █ ▓SELECT▓▓▓ █WINDOW███ ▓JUDGE▓▓▓▓ █ ENEMY [c] Hungry Cultist █
█ VOX There. The wick...   █        . candle .                    █ ENM armor cracking   █
█ ACT>▄██▄░                █ DIRECTOR T:WIN P:RDY F:INT           █     ▄▒▄        <TGT  █
█    ▐▓c▓██                █              ░▒▓▓██>                 █    ▐▒x▒              █
█  HP ████████████ 100/100 █            SEAL -16 HP               █ HP ███████░ 34/50    █
█  MP ████████░░░░ 54/72   █ ACTION Hex Seal -> Hungry Cultist    █ THREAT WINDOW 0/1    █
█  ATB READY               █ JUDGE  VALID | -16 HP                █ RETICLE [WINDOW]     █
█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█
```

```text
>==============================[ MOMENTUM BOARD ]==============================<
| [FLOW] WINDOW | enemy ATB 99                                                 |
| [LANE] HERO [########] 100/100 vs ENEMY [#######-] 104/120                   |
| [TARGET] Hungry Cultist                                                      |
| [SWING] hero hit -16 HP                                                      |
| [READ] answer the window before damage races ahead                           |
>==============================================================================<
```

```text
BATTLE TURN MAP
  [FLOW] H009-16 -> E010CHG -> E012 -> H017-48 -> E019 -> H025 -> E028-14 ->
  H034-47 -> E037CHG -> H042-15 -> E046BRK -> H050-47
  [FIRST HERO] skill_hex_seal
  [IMPACT] peak hit 48 / enemy damage 14
  [READ] one hero hit created the swing
```

### 你在游戏里做什么

1. **配置 Agent**：选英雄、Prompt 模板、装备、词条和 Build 方向。
2. **观看战斗**：AI 选择行动，本地裁判结算，TUI 展示意图、风险、伤害、窗口和节奏。
3. **复盘失败**：查看 `BATTLE TURN MAP`、死亡历史、图鉴进度和下一局建议。
4. **迭代构筑**：用新 Prompt、路线、奖励和 Codex 情报继续推进。

### 为什么这个项目有意思

- **AI 决策是玩法，不是背景文案。** 你调的是 Agent 的提示词、构筑和上下文；
  战斗中观察它是否会保留 MP、打断吟唱、处理 Boss 窗口。
- **TUI 是游戏界面，不是日志。** 战斗有低分辨率 Canvas、左右对战舞台、角色/怪物
  像素形象、武器小卡、弹道、命中浮字、英雄 `VOX` 与敌方 `ENM` 气泡。
- **战斗可以被解释。** `ENCOUNTER BRIEFING`、`MOMENTUM BOARD`、
  `BATTLE RESULT BOARD` 和本地 trace 会把模型行动、本地裁判、关键窗口和数值节奏串起来。
- **离线也能完整试玩。** 默认 mock provider 不联网、不需要 API key；真实 Provider
  支持 OpenAI、Anthropic 和 OpenAI-compatible。
- **有策划和数值工具。** `batch` 可批量试跑，输出胜率、节奏异常、MP 枯竭、
  反制错失、样本热力图和调参建议。

### 一分钟试玩

```bash
pip install -e .
ouro doctor --lang zh --content-dir content
ouro demo --lang zh --seed 1
ouro run --mock
```

想看更强画面感：

```bash
ouro --lang en play --mock --seed 2 --unicode --color always --no-trace
```

---

## English

**Agent Prompt Legend CLI** is a command-line AI roguelike where you configure
one hero Agent, then watch it fight automatically. The model chooses structured
actions; the local engine validates them and resolves damage, statuses, victory,
rewards, archives, and progression.

The design goal is not "chatbot writes a battle log." The goal is a playable
terminal roguelike where AI decisions are visible, debuggable, and tunable.

What you get:

- A deterministic mock mode that needs no network and no API key.
- A graphical TUI battle stage with actor sprites, projectile lanes, VOX/ENM
  battle lines, resource deltas, counter windows, and post-battle maps.
- Real provider adapters for OpenAI, Anthropic, and OpenAI-compatible APIs,
  with safe preflight and fallback behavior.
- Persistent Codex progress, run archives, death history, status dashboards,
  replay, and batch balance reports.

Quick start:

```bash
pip install -e .
ouro demo --lang en --seed 1
ouro run --mock
```

---

## Current Build

| Slice | What | State |
|-------|------|-------|
| 0 | Installable CLI, provider config, ASCII-safe screen | done |
| A | Deterministic ATB battle, action schema, mock model, trace | done |
| i18n | Bilingual UI / content / mock narration (zh default, --lang en) | done |
| Provider | Real `openai`, `anthropic`, `openai-compatible` adapters + auto fallback | done |
| B | 6 heroes, 18 skills, 15 items, 12 affixes, 5 resonances, build resolver | done |
| C-Experience | Main menu, hero prompt/build UI, battle frames, post-battle report, batch playtest | done |
| D | Dungeon, route, shop, rewards (full roguelike loop playable) | done |
| F | Batch playtest + balance stats | done |
| C-GameUI | Card UI, character poses, build joy, codex, context growth | done |
| C0 | BattleLLMSession, static context / turn delta, session trace | done |
| C1 | Build panel, Buff/Debuff UI, monster tier, codex stage | done |
| C2 | Monster families, tiered codex/content schema | done |
| E | Codex persistence, run archive, death history | done |

`345 tests passing`. No real network calls in any test.

---

## Recent Development (2026-05-06)

<details>
<summary>Development notes and implementation log</summary>

### Slice D - Full Roguelike Loop (Completed)

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

### Slice C-Experience & F - Batch Playtest (Completed 2026-05-07)

**What was implemented:**

1. **Batch Battle Engine** (`src/ouro_agent/engine/battle.py`)
   - `BatchResult` dataclass: aggregated stats across multiple battles
   - `run_batch()`: runs multiple battles with progress callback support
   - Metrics tracked: win rate, basic attack ratio, skill usage, turn count, damage dealt/taken

2. **CLI Batch Command** (`src/ouro_agent/cli/main.py`)
   - `batch` subcommand for balance testing
   - Arguments: `--count`, `--seed`, `--hero`, `--enemies`, `--quiet`
   - ASCII progress bar and detailed summary report

3. **Tests** (`tests/unit/test_battle.py`)
   - `test_batch_run_produces_reproducible_results()`
   - `test_batch_run_is_reproducible_with_same_seed()`

**How to Use:**

```bash
# Run 50 battles with default hero/enemies
ouro --lang en batch --count 50 --seed 1

# Quiet mode (no progress bar)
ouro --lang en batch --count 100 --quiet

# Custom hero and enemies
ouro --lang en batch --count 20 --hero hero_shadow_apprentice --enemies enemy_hungry_cultist
```

**Sample Output:**
```
=== BATCH RUN REPORT ===

Hero: hero_shadow_apprentice
Enemies: enemy_hungry_cultist, enemy_black_candle_acolyte

Overall Stats:
  Total runs: 50
  Victories: 50 (100.0%)
  Defeats: 0
  Timeouts: 0

Action Patterns:
  Avg hero turns: 6.0
  Avg basic attack ratio: 0.0%
  Avg skill usage ratio: 100.0%

Skill Usage Detail:
  skill_shadow_sting: 150
  skill_hex_seal: 100
  skill_corrupted_focus: 50
```

</details>

---

## Quickstart

Requires Python 3.11+.

```bash
pip install -e .

ouro --version
ouro doctor --lang en --content-dir content
ouro demo --lang en --seed 1                              # Guided first-player smoke
ouro run --mock                                           # Continue from demo into a full run
ouro list-heroes
ouro hero-card hero_ash_guardian
ouro play --mock --seed 1                                  # Single battle (Astia, Chinese default)
ouro play --mock --seed 1 --hero hero_broken_string_hunter # Single battle (Vela)
ouro --lang en play --mock --seed 1                        # Single battle (English, ASCII-safe)
ouro replay examples/traces/mvp_a_seed7_mock.trace.jsonl   # Replay a saved local battle trace
ouro status --lang en                                      # Review profile, progress, next-run plan, and commands
ouro codex --lang en                                       # Review persisted monster Codex progress
ouro runs --lang en --limit 5                              # Review saved run archives
ouro run-report --lang en                                  # Review the latest run as a compact report
ouro history --lang en --limit 5                           # Review fallen runs
ouro run --mock --auto                                     # Full dungeon run (auto-choose)
ouro batch --count 50 --seed 1                             # Batch playtest for balance testing
```

Eventual GitHub install:

```bash
pipx install git+https://github.com/hy459229090-lang/Agentpromptlegend_CLI.git
ouro play --mock
```

Installed wheels include the MVP content bundle, so `ouro doctor` and
`ouro play --mock` work outside the source checkout. Use `--content-dir`
only when testing a custom content directory.

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
* `ouro run` returns `0` when a playable session ends normally, even if the
  hero dies. Use `--strict-result-exit-code` when scripts should fail on
  death or timeout.

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
ouro config preflight
ouro play --seed 1
```

### Anthropic

```bash
setx ANTHROPIC_API_KEY "sk-ant-..."
ouro config set provider anthropic
ouro config set model claude-sonnet-4-5
ouro config preflight
ouro play --seed 1
```

### OpenAI-compatible (custom base URL)

```bash
setx OURO_API_KEY "..."
ouro config set provider openai-compatible
ouro config set base_url https://your-host.example.com/v1
ouro config set api_key_env OURO_API_KEY
ouro config set model your-model-name
ouro config preflight
ouro play --seed 1
```

`ouro config preflight` never calls the network. It checks provider, model,
base URL, `api_key_env`, and whether the named environment variable is present
in the current shell. If present, the value is shown only as `set (hidden)`.
`ouro doctor` also runs this offline provider check and returns nonzero if a
real provider is configured but not ready.

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
| `tests/unit/test_config.py` | Safe config, provider preflight, rejects plaintext key / legacy plaintext fields |
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
| Provider preflight must not leak key values | `ouro config preflight` prints env presence only as `set (hidden)` |
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

Next ready priorities:

1. **Final product audit QA** — keep
   [docs/product/24_最终产品验收审计_20260601.md](docs/product/24_最终产品验收审计_20260601.md)
   and [docs/product/25_人工试玩记录_20260601.md](docs/product/25_人工试玩记录_20260601.md)
   aligned before marking the larger goal complete.
2. **Release handoff QA** — keep [CHANGELOG.md](CHANGELOG.md) and
   [docs/engineering/RELEASE_HANDOFF_20260601.md](docs/engineering/RELEASE_HANDOFF_20260601.md)
   plus [docs/engineering/CHANGESET_MANIFEST_20260601.md](docs/engineering/CHANGESET_MANIFEST_20260601.md)
   aligned with the latest `venv312/bin/python scripts/release_check.py`
   output, including privacy scan, before tagging. Use
   `venv312/bin/python scripts/release_scope.py --stage-plan` for a read-only
   review of grouped `git add -- ...` commands.
3. **External sign-off** — run `venv312/bin/python scripts/signoff_check.py`,
   JSON mode `venv312/bin/python scripts/signoff_check.py --json`, or strict
   mode `venv312/bin/python scripts/signoff_check.py --strict` before marking
   the broader goal complete. This dynamically reports user satisfaction,
   License, live-provider smoke, and git-boundary sign-offs without replacing
   those human decisions; the user-satisfaction item includes copyable
   acceptance commands. `venv312/bin/python scripts/acceptance_check.py` runs
   the mock-first acceptance path without writing sign-off markers. Pending
   templates live at
   [docs/engineering/USER_ACCEPTANCE_20260601.md](docs/engineering/USER_ACCEPTANCE_20260601.md)
   [docs/engineering/LICENSE_DECISION_20260601.md](docs/engineering/LICENSE_DECISION_20260601.md),
   and [docs/engineering/PROVIDER_LIVE_SMOKE_20260601.md](docs/engineering/PROVIDER_LIVE_SMOKE_20260601.md);
   only change their `SIGN-OFF` lines after the real review is complete.
   For a single final readiness summary, run
   `venv312/bin/python scripts/completion_audit.py`.

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
