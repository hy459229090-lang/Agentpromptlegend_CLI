# G14 命令行美术与 TUI 设计策划案

> 状态：v0.1 草案  
> 依赖：G06、G13、G15  
> 目的：建立适合命令行阅读的暗黑画风、角色样式和界面布局，让游戏不是普通日志打印。

---

## 1. 模块目标

Ouro Agent 的视觉目标是“暗黑终端仪式感 + 高可读战斗面板”。命令行界面必须让玩家持续看懂：

1. 我是谁。
2. 敌人是谁。
3. 读条到哪里。
4. AI 正在做什么。
5. 行动造成什么结果。
6. 我下一步可以在哪里做选择。

---

## 2. 视觉原则

| 原则 | 要求 |
|------|------|
| 可读优先 | 数值、状态、目标必须清楚 |
| 美观克制 | 通过留白、分区、符号和少量颜色建立质感，不靠密集装饰 |
| 高性能 | 主屏局部刷新，避免逐字动画和高频全屏重绘 |
| 暗黑克制 | 使用黑、灰、暗红、金色，不做花哨彩虹 |
| 终端友好 | 默认 ASCII-safe，Unicode 增强可选 |
| 低刷屏 | 战斗主屏刷新，关键日志保留 |
| 可测试 | 动画可关闭，固定输出可用于快照测试 |

---

## 3. 颜色与样式基线

| 用途 | 颜色建议 | ANSI 方向 |
|------|----------|-----------|
| 背景 | 黑 / 深灰 | default / bright black |
| 英雄 | 暗金 / 白 | yellow / bright white |
| 敌人 | 暗红 | red |
| 腐化 / 毒 | 绿色或紫灰 | green / magenta |
| 护盾 | 蓝灰 | cyan |
| 警告 | 红色高亮 | bright red |
| 奖励 | 金色 | bright yellow |

实现时必须支持 `--no-color`。

---

## 4. 性能与刷新规则

| 规则 | 要求 |
|------|------|
| 刷新频率 | 常规读条不超过 4-8 FPS，模型等待状态可降到 1-2 FPS |
| 局部刷新 | 优先更新数值、读条、日志区域，不无意义重绘整个屏幕 |
| 日志限制 | 主屏只保留最近 5-8 行，完整日志写入 trace |
| 动画开关 | 支持 `--no-animation` 或配置项 |
| 测试输出 | 支持 deterministic text snapshot，不依赖实时动画 |
| 低配终端 | ASCII-safe + no-color + no-animation 必须可用 |

高性能不是第一版做复杂渲染优化，而是避免把终端输出做成不可测试、不可复盘的动画流。

---

## 5. 字符集策略

| 模式 | 用途 | 示例 |
|------|------|------|
| ASCII-safe | 默认兼容模式 | `HP [####----]` |
| Unicode-enhanced | 现代终端增强 | `HP ████░░░░` |

Windows 终端、旧 shell 或 CI 测试默认使用 ASCII-safe。玩家可在配置中启用 Unicode-enhanced。

---

## 6. 界面清单

| 界面 | MVP 优先级 | 说明 |
|------|------------|------|
| 主菜单 | P1 | 开始、配置、退出 |
| Provider 配置 | P0 | mock/openai/anthropic/openai-compatible |
| 英雄选择 | P1 | 展示角色、定位、默认 Prompt |
| 路线选择 | P1 | 展示下一层节点选择 |
| 战斗主屏 | P0 | HP/MP/ATB/敌人/日志 |
| 战后结算 | P1 | 奖励、经验、图鉴进度 |
| 商店 | P1 | 购买、替换、改 Prompt |
| 设置 | P0 | API key env、base_url、model、速度、颜色 |

---

## 7. 战斗主屏草案

```text
OURO AGENT :: EMBER CRYPT :: FLOOR 2
Seed: mvp_a-001        Mode: mock        Speed: x2

HERO
Astia / Shadow Apprentice
HP [########--] 82/100   MP [#####---] 31/48   ATB [#######---]
Status: shield(6), corruption_focus

ENEMIES
1. Hungry Cultist      HP [###-----] 24/50   ATB [####------] poison(1)
2. Black Candle Acolyte HP [######--] 41/70   ATB [######----]

MODEL TURN
Astia studies the acolyte's near-complete chant.
Action: cast_skill skill_shadow_sting -> enemy_black_candle_acolyte
Judge: valid | Damage: 27 shadow | Status: corruption +1
Model: mock-smart | Echo Cost: 0 tokens | Latency: 12ms

LOG
> Enemy 1 suffers 4 poison damage.
> Astia spends 12 MP. skill_shadow_sting cooldown: 2.
```

---

## 8. Token / 成本文案设计

借鉴 Claude Code 每轮 token 消耗展示，但文案必须游戏化。底层字段仍然保留真实统计，界面展示可包装成世界观语言。

| 技术字段 | 游戏化展示 | 说明 |
|----------|------------|------|
| input_tokens | Read Echo | 本轮模型读取的上下文 |
| output_tokens | Spoken Echo | 本轮模型输出 |
| total_tokens | Echo Cost | 本轮总消耗 |
| cached_tokens | Sealed Echo | 缓存命中或复用上下文 |
| latency_ms | Ritual Time | 模型响应延迟 |
| estimated_cost | Candle Debt | 后续可选，涉及价格时必须可关闭 |

主屏展示建议：

```text
MODEL
Provider: openai   Model: gpt-5.4
Echo Cost: 1,284 tokens   Ritual Time: 1.7s   Trace: local
```

原则：

1. 技术 trace 中保留原始 token 字段。
2. 玩家界面默认展示游戏化字段。
3. mock provider 显示 `Echo Cost: 0 tokens`。
4. 成本金额默认不展示，除非玩家开启。
5. Token 展示不能抢占战斗信息优先级。

---

## 9. 角色样式规范

每个英雄至少要有：

1. 1 个 ASCII-safe 头像。
2. 1 个短称号。
3. 1 行角色定位。
4. 3 个状态关键词。
5. 1 段默认 Prompt 摘要。

示例：

```text
  /\
 /##\   ASTIA
 |[]|   Shadow Apprentice
 /||\   tags: shadow / control / risk
```

---

## 10. Provider 配置界面草案

```text
MODEL PROVIDER

[1] Mock                  no API key required
[2] OpenAI                OPENAI_API_KEY
[3] Anthropic             ANTHROPIC_API_KEY
[4] OpenAI-compatible     custom base_url + api_key_env

Current:
provider = mock
model    = mock-smart
base_url = -
```

配置界面必须明确显示：是否会联网、使用哪个环境变量、不显示 key 明文。

---

## 11. 不可做

1. 不做复杂全屏动画阻塞测试。
2. 不把界面做成彩色噪音。
3. 不让 ASCII 图影响战斗数值可读性。
4. 不在 MVP 依赖图片、字体或 GUI。
5. 不为了展示 token 消耗牺牲战斗信息层级。

---

## 12. 验收标准

1. 战斗主屏能显示 HP、MP、ATB、状态、模型行动、裁判结果。
2. Provider 配置界面不泄露 API key。
3. ASCII-safe 模式在 Windows PowerShell 可读。
4. Unicode-enhanced 模式可选。
5. 至少 1 个英雄有命令行头像和角色面板。
6. 模型行动后可展示 Echo Cost / Ritual Time，mock 模式为 0 token。
7. 动画可关闭，输出可用于快照测试。
