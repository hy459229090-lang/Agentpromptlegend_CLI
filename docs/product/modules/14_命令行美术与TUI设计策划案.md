# G14 命令行美术与 TUI 设计策划案

> 状态：v0.2 草案
> 依赖：G03、G05、G06、G07、G13、G15
> 目的：建立适合命令行阅读的暗黑画风、角色样式、Build 展示、怪物图鉴和 BattleLLMSession 可视化规则。

---

## 1. 模块目标

Ouro Agent 的视觉目标是“暗黑终端仪式感 + 高可读战斗面板”。命令行界面必须让玩家持续看懂：

1. 我是谁，我的 Build 是什么。
2. 敌人是谁，属于哪个怪物家族和档次。
3. Buff/Debuff 在影响什么。
4. 读条到哪里。
5. AI 这一场战斗的 Session 正在消耗什么上下文。
6. 行动造成什么结果。
7. 我下一步可以在哪里做选择。

---

## 2. 视觉原则

| 原则 | 要求 |
|------|------|
| 可读优先 | 数值、状态、目标必须清楚 |
| 构筑可见 | Build 类型、核心标签、羁绊必须出现在英雄详情和战斗主屏 |
| 怪物可识别 | 怪物家族、档次、图鉴阶段必须能无颜色识别 |
| 美观克制 | 通过留白、分区、符号和少量颜色建立质感 |
| 高性能 | 主屏局部刷新，避免逐字动画和高频全屏重绘 |
| 终端友好 | 默认 ASCII-safe，Unicode 增强可选 |
| 可测试 | 动画可关闭，固定输出可用于快照测试 |

---

## 3. 颜色与样式基线

| 用途 | 颜色建议 | no-color 替代 |
|------|----------|---------------|
| 英雄 | 暗金 / 白 | `[HERO]` |
| 敌人 I | 暗红 | `[I]` |
| 敌人 II | 亮红 / 橙 | `[II]` |
| 敌人 III | 紫红 / 金 | `[III]` |
| Buff | 蓝灰 / 金 | `BUFF:` |
| Debuff | 绿 / 紫灰 | `DEBUFF:` |
| 图鉴 | 青灰 | `Codex:` |
| Session | 灰 / 暗金 | `Echo:` |

实现时必须支持 `--no-color`。

---

## 4. 角色与 Build UI

英雄详情页必须同时展示：

1. ASCII 头像或短卡。
2. 职业定位。
3. Build 类型。
4. 核心标签。
5. 当前武器/装备。
6. 已触发羁绊。
7. 模型策略提示摘要。

示例：

```text
HERO CARD

[XBOW] VELA  Broken String Hunter
Build : Bleed Execution
Tags  : bleed(3), hunter(2), execute(1), speed(1)
Gear  : Severed String [legendary]  allowed: bleed_on_hit / shadow_bonus
Echo  : Hunting Rite active

MODEL PLAN
1. Keep bleed on the toughest target.
2. Interrupt enemies above 80% ATB.
3. Execute enemies below 35% HP.
```

---

## 5. 状态显示规则

状态显示必须区分 Buff 和 Debuff。

```text
BUFF   : SHD shield(8), FOC focus(1)
DEBUFF : BLD bleed(2), CRP corruption(1), STG stagger(1)
```

原则：

1. 状态缩写必须有文档映射。
2. 不只用颜色表达状态。
3. 状态超过 4 个时，主屏显示前 4 个，完整状态写入详情或 trace。

---

## 6. 怪物和图鉴 UI

怪物列表必须显示家族、档次和图鉴阶段。

```text
ENEMIES
1. [I:c] Hungry Cultist        HP [###-----] 24/50   Codex: observed
2. [II:k] Black Candle Firekeeper HP [#####---] 86/120 Codex: unknown
3. [III:A] Hollow Archivist    HP [########--] 210/260 Codex: familiar
```

图鉴页面示例：

```text
CODEX :: BLACK CANDLE FAMILY

Tier I  Hungry Cultist          mastered
Tier II Black Candle Firekeeper observed
Tier III Black Candle High Priest unknown

Known:
- Black Candle enemies prefer delayed chants.
- Interrupt effects are high value before chant release.

Hidden:
- Tier III phase behavior is still sealed.
```

---

## 7. BattleLLMSession 显示

模型 Session 展示要游戏化，但字段必须可追踪。

| 技术字段 | 游戏化展示 |
|----------|------------|
| battle_session_id | Battle Echo |
| static_context_hash | Sealed Echo |
| delta_tokens | Fresh Echo |
| cached_tokens | Remembered Echo |
| total_tokens | Echo Cost |
| latency_ms | Ritual Time |

战斗主屏建议：

```text
MODEL SESSION
Battle Echo: be_017       Provider: openai       Model: gpt-5.4
Sealed Echo: ctx_91af     Fresh Echo: 418 tokens
Echo Cost: 1,284 tokens   Ritual Time: 1.7s      Trace: local
```

mock 模式可显示：

```text
Battle Echo: mock-local   Echo Cost: 0 tokens   Ritual Time: 12ms
```

---

## 8. 战斗主屏 v0.2

```text
OURO AGENT :: ASH GATE :: FLOOR 2
Seed: run-017      Provider: mock      Speed: x2      Codex: local

HERO
[CNDL] ASTIA  Shadow Apprentice
Build : Black Candle Interrupt   Tags: shadow(3), control(2), risk(1)
HP [########--] 82/100   MP [#####---] 31/48   ATB [#######---]
BUFF: SHD shield(6)

ENEMIES
1. [I:c] Hungry Cultist          HP [###-----] 24/50   ATB [####------] Codex: familiar
2. [II:k] Black Candle Firekeeper HP [######--] 86/120  ATB [########--] Codex: observed
DEBUFF: enemy 2 CRP corruption(1), STG stagger(1)

MODEL SESSION
Battle Echo: mock-local   Echo Cost: 0 tokens   Ritual Time: 12ms

MODEL TURN
Astia sees the firekeeper's chant near release.
Action: cast_skill skill_hex_seal -> enemy_black_candle_firekeeper
Judge: valid | silence(1), 11 shadow damage

LOG
> Build priority matched: interrupt high-ATB caster.
> Codex hint used: Black Candle chants can be sealed.
```

---

## 9. 不可做

1. 不做复杂全屏动画阻塞测试。
2. 不把界面做成彩色噪音。
3. 不让 ASCII 图影响战斗数值可读性。
4. 不在 MVP 依赖图片、字体或 GUI。
5. 不为了展示 token 消耗牺牲战斗信息层级。
6. 不把 Build 和图鉴只藏在 trace 里，玩家界面必须可见。

---

## 10. 验收标准

1. 战斗主屏能显示 HP、MP、ATB、状态、模型行动、裁判结果。
2. 英雄详情能显示 Build 类型、装备、词条、羁绊和策略摘要。
3. 怪物列表能显示 family tier 和 codex stage。
4. BattleLLMSession 能显示 Battle Echo / Sealed Echo / Echo Cost。
5. Provider 配置界面不泄露 API key。
6. ASCII-safe 模式在 Windows PowerShell 可读。
7. 动画可关闭，输出可用于快照测试。
