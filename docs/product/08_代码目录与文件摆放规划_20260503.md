# Ouro Agent 代码目录与文件摆放规划

> 版本：v0.1  
> 日期：2026-05-03  
> 用途：指导 Cursor / Claude Code 创建代码时按目录边界放置文件，避免后续混乱。

---

## 1. 总原则

1. 代码、内容、文档、测试、运行输出分离。
2. 战斗引擎不依赖 Provider SDK。
3. Provider Adapter 不知道具体战斗规则。
4. TUI 只读取展示模型，不直接改战斗状态。
5. 内容数据不写死在代码里。
6. API key 不进入仓库和普通配置文件。
7. 每个目录都有 `README.md` 和 `_rules.md`。

---

## 2. 仓库目标结构

```text
.
|-- README.md
|-- AGENTS.md
|-- CLAUDE.md
|-- pyproject.toml
|-- src/
|   `-- ouro_agent/
|       |-- cli/
|       |-- config/
|       |-- providers/
|       |-- engine/
|       |-- llm/
|       |-- content/
|       |-- sessions/
|       |-- tui/
|       |-- art/
|       |-- trace/
|       `-- validation/
|-- content/
|   |-- heroes/
|   |-- enemies/
|   |-- skills/
|   |-- items/
|   |-- dungeons/
|   `-- ui/
|-- tests/
|   |-- unit/
|   |-- integration/
|   `-- fixtures/
|-- docs/
|-- examples/
|   |-- config/
|   `-- traces/
`-- scripts/
```

---

## 3. 目录职责

| 目录 | 职责 | 不放什么 |
|------|------|----------|
| `src/ouro_agent/cli/` | CLI 命令入口、参数解析、命令分发 | 战斗规则 |
| `src/ouro_agent/config/` | 配置读取、写入、环境变量名管理 | API key 明文 |
| `src/ouro_agent/providers/` | mock/openai/anthropic/openai-compatible adapter | 战斗结算 |
| `src/ouro_agent/engine/` | ATB、HP/MP、技能、状态、胜负、裁判 | Provider SDK |
| `src/ouro_agent/llm/` | Prompt Composer、action schema、validator、fallback | 具体 HTTP 调用 |
| `src/ouro_agent/content/` | 内容加载、schema 校验、引用校验 | 大量内容数据 |
| `src/ouro_agent/sessions/` | Run/Battle/Turn session 状态与持久化 | UI 绘制 |
| `src/ouro_agent/tui/` | 面板、布局、ASCII-safe 输出、no-color | 状态结算 |
| `src/ouro_agent/art/` | glyph、头像、符号映射 | 玩法规则 |
| `src/ouro_agent/trace/` | trace 结构、写入、脱敏摘要 | API key |
| `src/ouro_agent/validation/` | 内容校验、快照校验、doctor 检查 | 游戏运行主逻辑 |
| `content/` | 结构化游戏内容数据 | Python 逻辑 |
| `tests/` | 单元、集成、fixtures | 运行时输出 |
| `examples/` | 示例配置、示例 trace | 用户真实配置 |
| `scripts/` | 开发辅助脚本 | 核心产品逻辑 |

---

## 4. 第一轮文件建议

Slice 0 + Slice A 最小文件：

```text
pyproject.toml
src/ouro_agent/__init__.py
src/ouro_agent/cli/main.py
src/ouro_agent/config/model.py
src/ouro_agent/config/store.py
src/ouro_agent/providers/base.py
src/ouro_agent/providers/mock.py
src/ouro_agent/engine/models.py
src/ouro_agent/engine/battle.py
src/ouro_agent/engine/judge.py
src/ouro_agent/llm/actions.py
src/ouro_agent/llm/prompt.py
src/ouro_agent/llm/validator.py
src/ouro_agent/content/loader.py
src/ouro_agent/content/schema.py
src/ouro_agent/tui/screens.py
src/ouro_agent/art/glyphs.py
src/ouro_agent/trace/writer.py
content/heroes/mvp_heroes.yaml
content/enemies/mvp_enemies.yaml
content/skills/mvp_skills.yaml
tests/unit/test_battle.py
tests/unit/test_action_validator.py
tests/unit/test_config.py
tests/integration/test_mock_battle.py
```

---

## 5. 命名规则

| 类型 | 命名 |
|------|------|
| Python 文件 | snake_case |
| 类名 | PascalCase |
| 内容 ID | 设计基线前缀 + snake_case |
| 测试文件 | `test_<module>.py` |
| 示例 trace | `<scenario>.trace.jsonl` |
| 示例配置 | `<scenario>.config.example.toml` |

---

## 6. 禁止项

1. 不把战斗逻辑写进 CLI。
2. 不把 Provider HTTP 代码写进战斗引擎。
3. 不把 API key 写入 examples。
4. 不把 trace 输出提交为真实玩家数据。
5. 不在 `src/` 中硬编码大量英雄/敌人内容。
6. 不让 TUI 直接修改核心 BattleState。

