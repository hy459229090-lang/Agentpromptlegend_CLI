# 暗影代理：祷文传说 / Ouro Agent: Prompt Legend

<p align="center">
  <strong>中文介绍</strong>
  ·
  <a href="README.md#english-store-page"><strong>English</strong></a>
  ·
  <a href="README.md"><strong>双语首页 / Bilingual README</strong></a>
  ·
  <code>ouro --lang zh</code> / <code>ouro --lang en</code>
</p>

<p align="center">
  <img alt="暗影代理祷文传说游戏介绍图" src="examples/ouro-readme-storefront.svg" width="100%">
</p>

<p align="center">
  <img alt="tests badge" src="https://img.shields.io/badge/tests-354%20passing-brightgreen">
  <img alt="python badge" src="https://img.shields.io/badge/python-3.11%2B-blue">
  <img alt="providers badge" src="https://img.shields.io/badge/providers-mock%20%7C%20openai%20%7C%20anthropic%20%7C%20openai--compatible-orange">
</p>

---

## 这是什么

### 训练一个会自己下副本的黑暗英雄 Agent

**暗影代理：祷文传说** 是一款黑暗终端风格的 AI 肉鸽。你不在战斗中手动点技能，
而是在战前配置英雄、装备、词条、Build、Prompt 和战术风格，然后观看这个 Agent
自动战斗、犯错、打断吟唱、抢节奏或死在自己的判断里。

模型只负责选择结构化行动；本地引擎负责校验行动、结算伤害、状态、胜负、奖励和长期存档。
**模型永远不决定伤害、掉落、胜负。**

它的重点不是让模型“讲故事”，而是让模型成为一名可训练、可观察、可复盘的战斗 Agent：

1. 玩家选择英雄、装备、词条、Prompt 模板和 Build 方向。
2. 战斗中模型只输出结构化行动，例如施放技能、选择目标、观察或防御。
3. 本地裁判验证行动是否合法，并结算伤害、状态、资源、胜负和奖励。
4. 每场战斗都会留下本地 trace、战报、图鉴进度和 run archive，方便复盘下一局。

因此它更接近“AI 驾驶的终端肉鸽”，而不是普通聊天机器人或日志生成器。

| 类型 | 当前状态 | 试玩门槛 |
|------|----------|----------|
| CLI roguelike / auto-battler / prompt-building game | MVP release candidate | 默认 mock，无需网络，无需 API key |

## 游戏画面

这些媒体图来自当前 CLI 输出的视觉整理；对应命令可用
`ouro --lang en play --mock --seed 2 --unicode --no-animation --no-trace --content-dir content`
复现。SVG 资产保存在 `examples/`，README 可以直接展示游戏画面，而不是只放文本日志。

<table>
  <tr>
    <td width="50%">
      <img alt="图形化 TUI 战斗舞台" src="examples/ouro-battle-canvas.svg">
      <br><strong>图形化战斗舞台</strong><br>
      左英雄、右怪物、中间弹道和裁判结果同屏，显示 HP、MP、ATB、意图、风险、Prompt 命中和 Build 状态。
    </td>
    <td width="50%">
      <img alt="战后复盘与图鉴进度" src="examples/ouro-after-action.svg">
      <br><strong>战后复盘与长期成长</strong><br>
      不是只告诉你赢了，而是把回合节奏、反制窗口、下一局建议和 Codex 研究目标一起留下。
    </td>
  </tr>
</table>

**开局配置：Prompt、Build、羁绊和下一步选择在进副本前就能看懂。**

```text
RUN READY BOARD
  [PROMPT] control / open by denying chant windows
  [BUILD] [ONLINE] Online / Black Candle Interrupt
  [CORE] shadow / control
  [NEXT PICK] guard, armor, poison
  [FIRST RULE] model chooses action, local judge resolves
```

**战斗帧：低分辨率 Canvas、像素角色、弹道、数值、英雄台词和本地裁判同时出现。**

```text
THE ECHO ALTAR / COUNTER WINDOW
HERO [CNDL] Astia     | SELECT > WINDOW > JUDGE | ENEMY [k] Acolyte
VOX seal the chant    | SEAL -16 HP             | ENM armor cracking
HP 100/100 MP 54/72   | ACTION HEX -> k         | HP 34/70 FX SLN1
```

**战后复盘：先给玩家读得懂的结果板，再进入细节。**

```text
BATTLE RESULT BOARD
  [RESULT] victory | HP 85/100 | MP 0/72
  [TEMPO] hero 6 / enemy 6 / tick 50
  [DAMAGE] dealt 173 / taken 15 / pressure controlled

BATTLE TURN MAP
  [FIRST HERO] Hex Seal
  [READ] one hero hit created the swing
```

## 为什么值得看

- **AI 决策是核心玩法。** Prompt 不只是说明文字，而会影响 Agent 是否打断吟唱、是否保留 MP、是否优先处理高 ATB 敌人和 Boss 窗口。
- **TUI 有游戏画面感。** 当前战斗屏已经包含低分辨率 Canvas、左右对战舞台、角色与怪物像素形象、武器小卡、弹道、命中浮字、`VOX` 英雄台词和 `ENM` 敌方回应。
- **战斗不是黑盒。** `ENCOUNTER BRIEFING`、`MOMENTUM BOARD`、`BATTLE TURN MAP`、`BATTLE RESULT BOARD` 会解释威胁、势能、行动轨道和战后结论。
- **可离线试玩。** 默认 mock provider 无需网络、无需 API key，也能跑完整 demo、单场战斗、完整副本、图鉴、死亡历史和状态页。
- **可接真实模型但不泄露密钥。** 支持 OpenAI、Anthropic、OpenAI-compatible；配置只保存环境变量名，实际 key 只从当前 shell 读取，并显示为 `set (hidden)`。
- **有策划和数值工具。** `batch` 可批量试跑，输出胜率、节奏异常、MP 枯竭、反制错失、样本热力图和调参建议。

## 一分钟试玩

```bash
pip install -e .
ouro doctor --lang zh --content-dir content
ouro demo --lang zh --seed 1
ouro run --mock
```

想看更强画面感：

```bash
ouro --lang en play --mock --seed 2 --unicode --color always --no-animation --no-trace --content-dir content
```

想看复盘和长期成长：

```bash
ouro status --lang zh
ouro codex --lang zh
ouro run-report --lang zh
ouro history --lang zh --limit 5
```

---

## 当前进度

| Slice | 内容 | 状态 |
|-------|------|------|
| 0 | 可安装 CLI、Provider 配置、ASCII-safe 主屏 | done |
| A | 确定性 ATB 战斗、action schema、mock model、本地 trace | done |
| i18n | UI / 内容 / Mock 旁白中英双语（中文默认，--lang en 切英文） | done |
| Provider | `openai` / `anthropic` / `openai-compatible` 真实 adapter + 自动降级 | done |
| B | 6 英雄 / 18 技能 / 15 装备 / 12 词条 / 5 羁绊 / 构筑结算 | done |
| C-Experience | 主菜单、英雄/Prompt/Build 配置、实时动作帧、战报、批量试跑 | done |
| D | 副本 / 路线 / 商店 / 奖励（完整肉鸽循环） | done |
| F | 批量试跑 + 基础平衡统计 | done |
| C-GameUI | 卡片 UI、角色动作、Build 快感、图鉴、Context 成长 | done |
| C0 | BattleLLMSession、静态上下文、turn delta、session trace | done |
| C1 | Build 面板、Buff/Debuff UI、怪物档次、图鉴阶段 | done |
| C2 | 怪物家族、三档图鉴与内容 schema | done |
| E | 图鉴持久化、Run 归档、死亡历史 | done |

`354 测试通过`。任何测试都不联网。

---

## 近期开发（2026-05-07）

<details>
<summary>开发日志和实现细节</summary>

### Slice C-Experience & F - 批量试跑（已完成）

**实现内容：**

1. **批量战斗引擎** (`src/ouro_agent/engine/battle.py`)
   - `BatchResult` 数据类：多场战斗聚合统计
   - `run_batch()` 函数：支持批量运行和进度回调
   - 统计指标：胜率、普攻占比、技能使用率、平均回合数、伤害统计

2. **CLI Batch 命令** (`src/ouro_agent/cli/main.py`)
   - `batch` 子命令用于数值平衡测试
   - 参数：`--count`、`--seed`、`--hero`、`--enemies`、`--quiet`
   - ASCII 进度条和详细汇总报告

3. **测试** (`tests/unit/test_battle.py`)
   - `test_batch_run_produces_reproducible_results()`
   - `test_batch_run_is_reproducible_with_same_seed()`

**使用方法：**

```bash
# 运行 50 场战斗（默认英雄/敌人）
ouro --lang zh batch --count 50 --seed 1

# 静默模式（无进度条）
ouro --lang zh batch --count 100 --quiet

# 自定义英雄和敌人
ouro --lang zh batch --count 20 --hero hero_shadow_apprentice --enemies enemy_hungry_cultist
```

**示例输出：**
```
=== 批量运行报告 ===

英雄: 阿斯缇娅
敌人: 饥饿邪教徒, 黑烛侍祭

总体统计:
  总运行数: 50
  胜利: 50 (100.0%)
  战败: 0
  超时: 0

行动模式:
  平均英雄回合: 6.0
  平均普攻占比: 0.0%
  平均技能使用率: 100.0%

技能使用详情:
  Shadow Sting：150
  Hex Seal：100
  Corrupted Focus：50
```

### Slice D - 完整肉鸽循环（已完成）

这一阶段实现了可从开局走到 Boss 的单局流程：路线选择、战斗节点、
奖励三选一、商店、休息、事件、结算、run archive 与下一局建议。
详细实现以 `docs/product/06_需求追踪矩阵_20260503.md` 的证据记录为准。

</details>

---

## 快速开始

需要 Python 3.11+。

```bash
pip install -e .

ouro --version
ouro doctor --lang zh --content-dir content
ouro demo --lang zh --seed 1                              # 引导式首局试玩
ouro run --mock                                           # 从 demo 继续进入完整运行
ouro list-heroes
ouro hero-card hero_ash_guardian
ouro play --mock --seed 1                                  # 单场战斗（默认中文 / 阿斯缇娅）
ouro play --mock --seed 1 --hero hero_broken_string_hunter # 单场战斗（薇拉）
ouro --lang en play --mock --seed 1                        # 单场战斗（英文 ASCII-safe）
ouro replay examples/traces/mvp_a_seed7_mock.trace.jsonl   # 回放本地战斗 trace
ouro status --lang zh                                      # 查看档案、进度、下一局计划与命令
ouro codex --lang en                                       # 查看持久化怪物图鉴进度
ouro runs --lang en --limit 5                              # 查看运行归档
ouro run-report --lang en                                  # 查看最近一局紧凑报告
ouro history --lang en --limit 5                           # 查看陨落记录
ouro run --mock --auto                                     # 完整副本（自动选择）
ouro batch --count 50 --seed 1                             # 批量试跑（数值平衡测试）
```

GitHub 安装路径（未来）：

```bash
pipx install git+https://github.com/hy459229090-lang/Agentpromptlegend_CLI.git
ouro play --mock
```

安装后的 wheel 内置 MVP 内容包，因此离开源码目录也可以直接运行
`ouro doctor` 和 `ouro play --mock`。只有测试自定义内容时才需要
`--content-dir`。

---

## 双语机制

ID（`hero_shadow_apprentice`、`skill_shadow_sting` 等）始终英文，
玩家可见文本中英双语。

| 模式 | 用法 |
|------|------|
| 中文（默认） | `ouro play --mock` |
| 英文（ASCII-safe） | `ouro --lang en play --mock` 或 `ouro config set language en` |

* 中文界面需要 UTF-8 终端。Windows 下推荐 Windows Terminal，
  或 PowerShell 中执行 `chcp 65001` + `$env:PYTHONIOENCODING="utf-8"`。
* 英文界面**严格 ASCII-safe**，可在传统 PowerShell 与 CI 中无障碍运行。
* `ouro run` 在一局正常结束时返回 `0`，即使英雄死亡也不是程序失败。
  如脚本需要死亡或超时返回非零，可使用 `--strict-result-exit-code`。

---

## 真实 Provider 接入

API key **永远不**保存进配置文件。配置只存环境变量名（如
`OPENAI_API_KEY`），实际值在调用时从 `os.environ` 读取。

如果真实 provider 在战斗中失败（网络 / 鉴权 / 超时），引擎会
自动用本地 mock 完成本场剩余回合，并在结尾打印一行提示。
裁判（伤害与胜负）始终由本地引擎控制。

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

### OpenAI 兼容（自定义 base URL）

```bash
setx OURO_API_KEY "..."
ouro config set provider openai-compatible
ouro config set base_url https://your-host.example.com/v1
ouro config set api_key_env OURO_API_KEY
ouro config set model your-model-name
ouro config preflight
ouro play --seed 1
```

`ouro config preflight` 不发起网络请求。它只检查 provider、model、
base URL、`api_key_env` 和当前 shell 中对应环境变量是否存在；若存在，
只显示 `set (hidden)`，不会回显密钥值。
`ouro doctor` 也会执行这项离线 Provider 检查；如果真实 Provider
已配置但未就绪，会返回非零。

---

## 测试

```bash
pip install -e ".[dev]"
pytest -q
```

| 测试文件 | 覆盖 |
|----------|------|
| `tests/unit/test_battle.py` | ATB / MP / 冷却 / 胜负 / 护盾 |
| `tests/unit/test_action_validator.py` | JSON 修复 / 未知行动 / 未知技能 / 兜底 |
| `tests/unit/test_config.py` | 配置安全、Provider preflight、拒绝明文 key / 旧明文字段 |
| `tests/unit/test_content_loader.py` | YAML schema + 双语回退 + ID 前缀校验 |
| `tests/unit/test_i18n.py` | 中文标签 / 英文 ASCII-safe / CJK 宽度 |
| `tests/unit/test_build.py` | 3 英雄 / 6 装备 / 6 词条 / 2 羁绊 / 构筑结算 |
| `tests/unit/test_providers.py` | OpenAI / Anthropic / 兼容 wire + 失败降级（HTTP 已 mock） |
| `tests/integration/test_mock_battle.py` | 固定 seed 复测 + trace + ASCII-safe 战斗屏 |

---

## 安全边界

| 规则 | 落地位置 |
|------|---------|
| 模型不决定伤害 / 掉落 / 胜负 | `engine/judge.py` 是唯一伤害来源 |
| Mock 不联网、无需 API key | `providers/mock.py` 不引用任何 SDK / http |
| 配置不允许出现明文 key | `config/store.py` 拦截 `api_key`、`secret` 字段，并对 `api_key_env` 拒绝 `sk-` 开头 |
| Provider 预检不泄露 key 值 | `ouro config preflight` 只显示环境变量是否 `set (hidden)` |
| Trace 文件永不写 key | `trace/writer.py` 仅记录 provider 名 + 模型名 |
| 真实 provider 失败不毁局 | `providers/registry.FallbackOnErrorProvider` 自动切 mock |
| 默认 UI 任意终端可读 | `--lang en` 输出 100% ASCII；`tests/test_i18n.py::test_battle_screen_en_remains_ascii_safe` 断言 `text.isascii()` |

---

## 架构 30 秒

```
                +---------------------+
ouro play --->  |  CLI (cli/main.py)  |
                +----------+----------+
                           |
                  +--------v---------+        +-----------------------+
                  | Provider 适配器  |<-----> | mock / openai /       |
                  | (Provider 接口)  |        | anthropic / 兼容       |
                  +--------+---------+        +-----------------------+
                           |
                           | ModelTurnResult (raw_text + token usage)
                           v
                  +----------------+
                  | llm.validator  |   解析 / 修复 / 降级
                  +-------+--------+
                          |
                          | HeroAction（已校验）
                          v
                  +----------------+        +------------------+
                  | engine.judge   |<------ | engine.battle    |
                  | (唯一伤害源)    |        | (ATB 主循环)     |
                  +-------+--------+        +---------+--------+
                          |                            |
                          v                            v
                  BattleState 变更               tui/screens（只读）
                                                trace/writer (jsonl)
```

* `src/ouro_agent/engine/` — 确定性战斗。不引入任何 provider SDK，
  也不依赖任何 TUI 模块。
* `src/ouro_agent/providers/` — wire 适配器。不引入战斗内部。
* `src/ouro_agent/llm/` — Prompt 组合、action schema、validator。
  把 provider 的原始文本与引擎隔离。
* `src/ouro_agent/i18n/` — 中英 UI 标签、战斗日志模板、CJK 宽度辅助。
* `content/` — 所有游戏数据为 YAML，双语 `display_name` 等。

完整布局：[docs/engineering/CODE_LAYOUT.md](docs/engineering/CODE_LAYOUT.md)。

---

## 仓库速览

```text
README.md / README.zh.md      中英双语首页
AGENTS.md / CLAUDE.md         coding agent 规则（改代码前必读）
pyproject.toml                可安装包，命令入口 `ouro`
src/ouro_agent/               运行时代码（按职责拆分）
content/                      游戏数据（英雄 / 技能 / 敌人 / 装备 / 词条 / 羁绊）
tests/                        单元 + 集成测试
examples/                     示例配置 + 示例 trace + README 媒体图
docs/                         产品 / 规划 / 工程 / AI 协作文档
scripts/                      开发辅助脚本
```

每个目录下都有本地 `README.md` 和 `_rules.md`。
代理改文件前应读最近的 `_rules.md`。

---

## 后续路线

当前推荐优先级：

1. **最终产品审计 QA** — 保持
   [docs/product/24_最终产品验收审计_20260601.md](docs/product/24_最终产品验收审计_20260601.md)
   与 [docs/product/25_人工试玩记录_20260601.md](docs/product/25_人工试玩记录_20260601.md)
   一致后，再考虑标记大目标完成。
2. **发布交接 QA** — 保持 [CHANGELOG.md](CHANGELOG.md) 与
   [docs/engineering/RELEASE_HANDOFF_20260601.md](docs/engineering/RELEASE_HANDOFF_20260601.md)
   以及 [docs/engineering/CHANGESET_MANIFEST_20260601.md](docs/engineering/CHANGESET_MANIFEST_20260601.md)
   同最新 `venv312/bin/python scripts/release_check.py` 输出一致，包括 privacy scan，再打 tag。

需求矩阵：[docs/product/06_需求追踪矩阵_20260503.md](docs/product/06_需求追踪矩阵_20260503.md)。

---

## Provider 文档参考

- [OpenAI Chat Completions](https://platform.openai.com/docs/api-reference/chat/create)
- [OpenAI 鉴权](https://platform.openai.com/docs/api-reference/authentication)
- [Anthropic Messages API](https://docs.anthropic.com/en/api/messages)
- [Anthropic Messages 示例](https://docs.anthropic.com/en/api/messages-examples)

---

## License

License 待定。

## 完成前签收

自动门禁通过不等于完整目标已经可以标记完成。正式 complete 前运行：

```bash
venv312/bin/python scripts/signoff_check.py
venv312/bin/python scripts/signoff_check.py --json
venv312/bin/python scripts/signoff_check.py --strict
```

它会动态报告用户满意度、License、真实 Provider live smoke 与 Git
提交边界这些需要人工或外部证据的签收项；用户满意度项会列出可复制的
acceptance commands；`--json` 可给 CI/发布记录复用。
`venv312/bin/python scripts/acceptance_check.py` 可一条命令跑完 mock-first
验收路径，但不会写入签收标记。
正式 staging 前可先运行 `venv312/bin/python scripts/release_scope.py --stage-plan`，
获取只读的分组 `git add -- ...` 命令清单。
待填写模板位于
`docs/engineering/USER_ACCEPTANCE_20260601.md` 和
`docs/engineering/LICENSE_DECISION_20260601.md` 和
`docs/engineering/PROVIDER_LIVE_SMOKE_20260601.md`；只有真实验收完成后才改
`SIGN-OFF` 行。
如需一个总览入口，可运行 `venv312/bin/python scripts/completion_audit.py`。
