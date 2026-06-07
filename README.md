# Ouro Agent: Prompt Legend / 暗影代理：祷文传说

<p align="center">
  <strong>Train one AI hero. Watch it survive your Prompt.</strong><br>
  <strong>训练一个 AI 英雄，让它带着你的 Prompt 下地牢。</strong><br>
  <sub>CLI AI Roguelike · Prompt-Building Auto Battler · Offline Mock Playable</sub>
</p>

<p align="center">
  <strong>Language Switch / 语言切换: 中文 / English</strong><br>
  <a href="README.zh.md"><strong>中文介绍页 / Full Chinese README</strong></a>
  &nbsp;|&nbsp;
  <a href="#english-store-page"><strong>English Store Page</strong></a>
  &nbsp;|&nbsp;
  <strong>CLI Language Toggle / CLI 语言切换:</strong>
  <code>ouro --lang zh</code> / <code>ouro --lang en</code>
</p>

<a id="storefront-hero"></a>

## Storefront Hero / 商店页封面

<p align="center">
  <img alt="Ouro Agent Prompt Legend storefront capture" src="examples/ouro-readme-storefront.svg" width="100%">
  <br><strong>You do not pilot the hero turn by turn. You design the mind it carries into the dungeon.</strong><br>
  <strong>A dark terminal roguelike: build one Agent, then watch it survive by decision + rules, not by button-mashing.</strong><br>
  <strong>暗黑 Roguelike。先搭建，一局看生死。你是构筑师，不是放技能的人。</strong><br>
  <sub>Model chooses. Local Judge decides. 模型只选招式，裁判负责结算。</sub>
</p>

<table>
  <tr>
    <th colspan="4">Steam-Style Front Page / Steam 风格首页 · Choose Your Page / 选择介绍页</th>
  </tr>
  <tr>
    <td align="center"><a href="README.zh.md"><strong>中文 / Chinese</strong><br><sub>完整中文文档 / Full Chinese README</sub></a></td>
    <td align="center"><a href="#english-store-page"><strong>English Store Page</strong><br><sub>game first, docs later</sub></a></td>
    <td align="center"><a href="#screenshots-build-fight-learn"><strong>Best First Screen</strong><br><sub>Media Gallery / 先看游戏画面</sub></a></td>
    <td align="center"><a href="#play-now"><strong>Play Now</strong><br><sub>Mock, offline, no API key</sub></a></td>
  </tr>
</table>

<p align="center">
  <strong>Playable now in mock mode: no network, no API key, deterministic seeds.</strong><br>
  <strong>现在可离线试玩：无需网络、无需 API key，固定 seed 可复现。</strong><br>
  <sub>Watch the run before reading the docs. Media first. Rules second. Engineering third.</sub>
</p>

| Play in 30 seconds | 中文 30 秒开局 | Watch the battle canvas |
|--------------------|----------------|-------------------------|
| `pip install -e .`<br>`ouro demo --lang en --seed 1` | `pip install -e .`<br>`ouro demo --lang zh --seed 1` | `ouro --lang en play --mock --seed 2 --unicode --color always --no-animation --no-trace --content-dir content` |

<p align="center">
  <strong>Hero Capsule / 首屏胶囊图</strong><br>
  <sub>One trained Agent, one local judge, and a dungeon that answers the Prompt.</sub>
</p>

<p align="center">
  <img alt="Steam-style screenshot wall for Ouro Agent TUI gameplay" src="examples/ouro-readme-screenshot-wall.svg" width="100%">
  <br><strong>Steam-style screenshot wall / 商店式截图墙</strong><br>
  <sub>MAIN MENU CONSOLE -> ENCOUNTER BRIEFING -> THE ECHO ALTAR -> DECISION FOCUS -> AFTER-ACTION REPORT. Real TUI Captures before the engineering notes begin.</sub>
</p>

<details>
<summary>What a Steam page would show first / 好的 Steam 页面会先展示什么</summary>

| What a Steam page would show first | How this README now handles it |
|------------------------------------|--------------------------------|
| **Capsule art and screenshots** | Hero capsule, screenshot wall, and Build/Fight/Learn gallery appear before architecture and provider docs. |
| **A one-sentence fantasy** | Build one Agent, release it, and watch whether your Prompt survives pressure. |
| **Playable status and CTA** | `ouro demo --lang en --seed 1` and `ouro demo --lang zh --seed 1` are above the engineering sections. |
| **Feature proof, not promises** | Every media panel names a reproducible CLI command and uses mock-friendly game screens. |

</details>

## Game Capsule / 游戏胶囊

| What this is | What you do | What you watch | Why one more run |
|--------------|-------------|----------------|------------------|
| **A CLI AI roguelike with a real local judge.** | Build one Agent: hero, weapon, affixes, Prompt style, and tactical bias. | A low-pixel TUI stage with hero/enemy silhouettes, HP/MP/ATB, effect lanes, VOX/ENM barks, and judge readouts. | The report tells you where the Prompt failed, which Codex clue unlocked, and what Build to try next. |

| 这是什么 | 你做什么 | 你会看到什么 | 为什么再开一局 |
|----------|----------|--------------|----------------|
| **一款命令行 AI 肉鸽，胜负由本地裁判结算。** | 战前构筑一个 Agent：英雄、武器、词条、Prompt 风格和战术偏好。 | 低像素 TUI 舞台：英雄/敌人剪影、HP/MP/ATB、弹道、VOX/ENM 台词、浮字和裁判结果同屏。 | 战报会告诉你 Prompt 哪里失手、图鉴解锁了什么、下一局该怎么改 Build。 |

**Playable offline now.** The mock provider runs a full guided demo with no
network, no API key, and deterministic seeds. Build once, release the Agent,
then read how the local judge explains every hit.

<a id="screenshots-build-fight-learn"></a>

## Screenshots: Build, Fight, Learn / 画面：构筑、战斗、复盘

Media Gallery / 先看游戏画面. Screenshots below are captured from reproducible CLI output, not concept art. Run
`ouro --lang en play --mock --seed 2 --unicode --no-animation --no-trace --content-dir content`
to reproduce the battle style. The SVG media lives in `examples/`.

<table>
  <tr>
    <td width="33%">
      <img alt="Weapon gallery and Build arsenal" src="examples/ouro-weapon-gallery.svg">
      <br><strong>Build / Weapon Gallery / 武器图鉴</strong><br>
      Six weapons show silhouettes, Build tags, owner roles, AI behavior, and the next hero-card or run command before you commit to a run.<br>
      <sub>Reproduce: <code>ouro weapons --unicode</code></sub>
    </td>
    <td width="33%">
      <img alt="Graphical TUI battle canvas" src="examples/ouro-battle-canvas.svg">
      <br><strong>Fight / Graphical Battle Stage / 图形化战斗舞台</strong><br>
      Left hero vs right enemy, projectile lane, HP / MP / ATB / risk rail, floating FX, Prompt hit, Build state, and local judge in one terminal frame.<br>
      <sub>Reproduce: <code>ouro --lang en play --mock --seed 2 --unicode --no-animation --no-trace --content-dir content</code></sub>
    </td>
    <td width="33%">
      <img alt="After action report and Codex preview" src="examples/ouro-after-action.svg">
      <br><strong>Learn / After-Action Report / 战后复盘屏</strong><br>
      Victory is not one final line. The run remembers turn flow, counter windows, Codex research, death history, and the next build to try.<br>
      <sub>Reproduce: <code>ouro run-report --lang en</code> and <code>ouro codex --lang en</code></sub>
    </td>
  </tr>
</table>

The first playable loop is meant to read like a compact game journey:

1. **RUN READY BOARD** - your Agent's Prompt, Build stage, tags, next pick, and first rule.
2. **THE ECHO ALTAR / COUNTER WINDOW** - the model chooses an action; the local judge resolves the impact.
3. **BATTLE RESULT BOARD** - tempo, mistakes, Codex progress, and next-run commands stay visible.

<details>
<summary>Reproducible CLI Capture / 可复现终端片段</summary>

```text
RUN READY BOARD
  [PROMPT] control / open by denying chant windows
  [BUILD] [ONLINE] Online / Black Candle Interrupt
  [CORE] shadow / control
  [NEXT PICK] guard, armor, poison
  [FIRST RULE] model chooses action, local judge resolves

THE ECHO ALTAR / COUNTER WINDOW
HERO [CNDL] Astia     | SELECT > WINDOW > JUDGE | ENEMY [k] Acolyte
VOX seal the chant    | SEAL -16 HP             | ENM armor cracking
HP 100/100 MP 54/72   | ACTION HEX -> k         | HP 34/70 FX SLN1

CINEMATIC BEAT
  VOX There. The wick forgets its prayer.
  FLOAT -16 HP | SLN
  STRIP [WIND] ░SEAL LANE░ ▓HIT -16▓ █VALID█

BATTLE RESULT BOARD
  [RESULT] victory | HP 85/100 | MP 0/72
  [TEMPO] hero 6 / enemy 6 / tick 50
  [DAMAGE] dealt 173 / taken 15 / pressure controlled

BATTLE TURN MAP
  [FIRST HERO] Hex Seal
  [READ] one hero hit created the swing
```
</details>

<a id="english-store-page"></a>

## English Store Page

### You are the builder behind the Agent.

**Ouro Agent: Prompt Legend** is a playable CLI AI roguelike about preparation,
pressure, and readable failure. You do not click skills during combat. You build
one hero Agent before the dungeon starts: hero, weapon, affixes, Build direction,
Prompt style, and tactical bias. Then the run begins, and you watch whether that
plan can survive the dungeon.

The model chooses structured actions. The local engine validates targets,
cooldowns, resources, damage, statuses, rewards, defeat, and victory. That
boundary is the fun: the Prompt can be clever, but the dungeon still has rules.

| Storefront Snapshot / 游戏速览 | Current Promise |
|--------------------------------|-----------------|
| **Genre** | CLI roguelike / auto-battler / prompt-building game |
| **Player Fantasy** | Build one Agent, release it, then watch it read pressure, miss windows, interrupt rituals, and grow through failure |
| **Language / 语言** | README has Chinese and English pages; CLI 语言切换 uses `ouro --lang zh` or `ouro --lang en` |
| **Playable State** | Mock provider is deterministic, offline, and ready without network or API keys |
| **Combat Rule** | Model chooses action; local judge resolves legality, damage, rewards, defeat, and victory |
| **Visual Target** | Graphical TUI with left hero vs right enemy, HP/MP/ATB, threat rails, projectile lane, floating FX, `Echo Cost / Read Echo / Spoken Echo / Ritual Time`, VOX/ENM barks, and Cinematic Beat |

| Player Promise | What You Actually Do | Why It Feels Different |
|----------------|----------------------|------------------------|
| Build before the fight. Watch the Agent answer under pressure. | Pick one hero, weapon, affixes, Build tags, Prompt style, and tactical bias before combat. | The run tests your preparation instead of your reaction speed. |
| See the fight, not a scroll of logs. | Watch a left-hero vs right-enemy battle canvas with HP/MP/ATB, intent, risk, model action, judge result, floating numbers, and battle barks. | CLI is treated as a low-resolution game screen, not a debug console. |
| Let failure teach the next build. | Read battle reports, Codex progress, death history, status boards, replays, and batch balance reports. | Every mistake leaves a trace you can actually use in the next run. |

## About This Game

This is not a chat wrapper with damage numbers. It is a local game loop where
Prompt design becomes a build choice, model output becomes intent, and a
deterministic judge keeps the dungeon honest.

| Why click into it? | What proves it now? |
|--------------------|---------------------|
| **The AI can be wrong in interesting ways.** | Every battle prints model action, judge result, resources, risk, and recent log. |
| **The TUI is treated as a game screen.** | Weapon gallery, battle canvas, Codex, status, run report, and death history render as card-like terminal boards. |
| **The first run is frictionless.** | Mock mode is offline, deterministic, and works without API keys. |

## Core Loop / 每局你会做什么

1. **Prepare the Agent** - choose the hero, weapon, affixes, Prompt style, and tactical bias.
2. **Release it into battle** - combat is automatic; the model picks a structured action.
3. **Watch the local judge** - legality, damage, statuses, resources, drops, defeat, and victory are resolved locally.
4. **Read the scars, rebuild smarter** - Codex progress, death history, replay, and run reports tell you what to change next.

## Why It Plays / Key Features / 为什么它值得试玩

- **The Prompt is part of the build.** You are tuning an Agent's combat bias and watching whether that bias survives pressure.
- **The battle screen is a game surface.** The fight uses a left/right stage, actor silhouettes, weapon cards, effect lane, floating numbers, VOX/ENM barks, and a compact Cinematic Beat.
- **The model is powerful but not sovereign.** It can choose an action; it cannot invent damage, drops, victory, or hidden knowledge.
- **Mock mode is a complete first play.** The first demo needs no network and no API key, while real providers remain optional.
- **Failure feeds the roguelike loop.** Route choices, rewards, shop decisions, Codex unlocks, deaths, and reports all feed the next run.

<a id="play-now"></a>

## Play Now: No Network, No API Key / 立即试玩

One command gets you from install to a guided first run:

```bash
pip install -e .
ouro demo --lang en --seed 1
```

Want Chinese:

```bash
ouro demo --lang zh --seed 1
```

Want to jump straight into the game:

```bash
ouro play --mock
ouro run --mock
```

Want the journey console:

```bash
ouro menu --lang en
```

Want the current battle canvas directly:

```bash
ouro --lang en play --mock --seed 2 --unicode --color always --no-animation --no-trace --content-dir content
```

Want the post-run learning loop:

```bash
ouro status --lang en
ouro codex --lang en
ouro run-report --lang en
ouro history --lang en --limit 5
```

## 中文简介

**暗影代理：祷文传说** 是一款黑暗终端风格的 AI 肉鸽。你战前训练一个英雄
Agent，把 Prompt、武器、词条和 Build 方向交给它；战斗开始后你不能救场，
只能看它执行你的计划、暴露你的构筑缺陷，然后带着复盘回到下一局。

模型只负责选择结构化行动；本地引擎负责校验行动、结算伤害、状态、胜负、奖励和长期存档。
**模型永远不决定伤害、掉落、胜负。** 中文完整说明见 [README.zh.md](README.zh.md)。

---

## Current Playable Content / 当前可玩内容

| What You Can Play | Available Now | Recommended Command |
|-------------------|---------------|---------------------|
| Guided first run | yes | `ouro demo --lang en --seed 1` |
| Journey console and command map | yes | `ouro menu --lang en` |
| Single AI battle | yes | `ouro play --mock` |
| Full dungeon run with route, shop, rest, rewards, and boss | yes | `ouro run --mock` |
| Hero cards, weapon gallery, and Build planning | yes | `ouro list-heroes` / `ouro weapons --unicode` / `ouro hero-card hero_ash_guardian` |
| Codex, status, death history, and run archives | yes | `ouro status --lang en` / `ouro codex --lang en` |
| Local battle replay | yes | `ouro replay examples/traces/mvp_a_seed7_mock.trace.jsonl` |
| Balance and batch reports | yes | `ouro batch --count 50 --seed 1` |

<p align="center">
  <img alt="tests badge" src="https://img.shields.io/badge/tests-373%20passing-brightgreen">
  <img alt="python badge" src="https://img.shields.io/badge/python-3.11%2B-blue">
  <img alt="providers badge" src="https://img.shields.io/badge/providers-mock%20%7C%20openai%20%7C%20anthropic%20%7C%20openai--compatible-orange">
</p>

`373 tests passing`. No real network calls in any test.

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
ouro weapons --unicode
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

Language / 语言: CLI 语言切换 / CLI language switching uses `ouro --lang zh` or
`ouro --lang en`; the same options can be saved with `ouro config set language`.

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

## Optional: Use a Real Model

The first play does not need a real model. The mock provider is a complete
offline demo path. If you want to bring a real model later, API keys are
**never** stored in config files. The config holds the
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
examples/                     Example configs + traces + README media captures
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
