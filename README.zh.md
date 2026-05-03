# 暗影代理：祷文传说 / Agent Prompt Legend CLI

> 命令行 AI 肉鸽。玩家配置一名英雄 Agent（技能、装备、词条、战斗 Prompt），
> 战斗由模型挑选结构化行动 + 本地确定性裁判结算自动进行。
> **模型永远不决定伤害、掉落、胜负。**

English: **[README.md](README.md)**.

[![tests](https://img.shields.io/badge/tests-65%20passing-brightgreen)]() [![python](https://img.shields.io/badge/python-3.11%2B-blue)]() [![providers](https://img.shields.io/badge/providers-mock%20%7C%20openai%20%7C%20anthropic%20%7C%20openai--compatible-orange)]()

---

## 当前进度

| Slice | 内容 | 状态 |
|-------|------|------|
| 0 | 可安装 CLI、Provider 配置、ASCII-safe 主屏 | done |
| A | 确定性 ATB 战斗、action schema、mock model、本地 trace | done |
| i18n | UI / 内容 / Mock 旁白中英双语（中文默认，--lang en 切英文） | done |
| Provider | `openai` / `anthropic` / `openai-compatible` 真实 adapter + 自动降级 | done |
| B | 3 英雄 / 9 技能 / 6 装备 / 6 词条 / 2 羁绊 / 构筑结算 | done |
| C0 | BattleLLMSession、静态上下文、turn delta、session trace | next |
| C1 | Build 面板、Buff/Debuff UI、怪物档次、图鉴阶段 | next |
| C2 | 6 英雄、怪物家族、三档图鉴与内容 schema | planned |
| D | 副本 / 路线 / 商店 / 奖励 | planned |
| E | 图鉴 / 存档 / 死亡保留 | planned |
| F | 批量试跑 + 基础平衡 | planned |

`65 测试通过`。任何测试都不联网。

---

## 快速开始

需要 Python 3.11+。

```bash
pip install -e .

ouro --version
ouro list-heroes
ouro hero-card hero_ash_guardian
ouro play --mock --seed 1                                  # 默认中文 / 阿斯缇娅
ouro play --mock --seed 1 --hero hero_broken_string_hunter # 薇拉
ouro --lang en play --mock --seed 1                        # 英文 ASCII-safe
```

GitHub 安装路径（未来）：

```bash
pipx install git+https://github.com/hy459229090-lang/Agentpromptlegend_CLI.git
ouro play --mock
```

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
ouro play --seed 1
```

### Anthropic

```bash
setx ANTHROPIC_API_KEY "sk-ant-..."
ouro config set provider anthropic
ouro config set model claude-sonnet-4-5
ouro play --seed 1
```

### OpenAI 兼容（自定义 base URL）

```bash
setx OURO_API_KEY "..."
ouro config set provider openai-compatible
ouro config set base_url https://your-host.example.com/v1
ouro config set api_key_env OURO_API_KEY
ouro config set model your-model-name
ouro play --seed 1
```

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
| `tests/unit/test_config.py` | 配置安全（拒绝明文 key、拒绝旧明文字段） |
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
examples/                     示例配置 + 示例 trace
docs/                         产品 / 规划 / 工程 / AI 协作文档
scripts/                      开发辅助脚本
```

每个目录下都有本地 `README.md` 和 `_rules.md`。
代理改文件前应读最近的 `_rules.md`。

---

## 后续路线

按推荐优先级：

1. **Slice C0** — `BattleLLMSession`、static context / turn delta、
   session trace、上下文复用指标。
2. **Slice C1** — Build 面板、Buff/Debuff 分组、怪物档次、图鉴阶段、
   no-color 快照稳定性。
3. **Slice C2** — 六英雄内容规划、怪物家族、三档怪物变体、图鉴 schema。
4. **Slice D** — 副本 / 路线 / 节点 / 商店 / 奖励（让"一整局"成立）。
5. **Slice E** — 图鉴进度、死亡保留、Run / Codex 存档。
6. **Slice F** — `ouro batch` 批量试跑、平衡统计。

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
