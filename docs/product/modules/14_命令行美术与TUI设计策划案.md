# G14 命令行美术与 TUI 设计策划案

> 状态：v0.3 草案
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

CLI 不是纯文本日志。视觉目标分三级：

| 等级 | 名称 | 能力 | 用途 |
|------|------|------|------|
| L0 | ASCII-safe | ASCII 面板、卡片框、短标识 | 兼容和 CI |
| L1 | ANSI/Unicode | 颜色、Unicode 图标、块状血条、局部清屏 | 默认推荐玩家体验 |
| L2 | Rich/TUI | 键盘导航、面板布局、卡片列表、轻量动画 | 后续正式体验 |

ASCII-safe 是兼容底线，不是最终审美上限。

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

### 4.1 武器、Build、技能组合展示

英雄选择和英雄详情必须把“构筑组合”展示成玩家能理解的关系，而不是孤立字段。

```text
BUILD MAP
Weapon : Severed String [legendary]  tags: bleed, hunter
Affix  : Blood-Marked Bolt            tags: bleed, execute
Link   : bleed(3) -> Resonance: Hunting Rite

Skill Plan
[1] Barbed Shot      MP 8  CD 1  keep bleed active
[2] Eclipse Step     MP 10 CD 3  dodge / reposition
[3] Final String     MP 18 CD 4  execute below 35% HP

AI Bias
Aggressive + Bleed Execution:
  keep bleed -> interrupt high ATB -> execute low HP
```

展示原则：

1. 装备、词条、技能、羁绊必须在同一页能看出组合关系。
2. 不只列 YAML ID，要显示玩家可读的收益。
3. 如果 Build 改变 Prompt 倾向，必须在 `AI Bias` 中展示。

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

### 6.1 图鉴卡片和迷雾

图鉴页面必须卡片化。未解锁内容使用迷雾/占位，而不是空白文字。

```text
+------------------------------+
| [??] UNKNOWN FAMILY          |
| tier: ?                      |
| silhouette: ░░░░░            |
| known: first seen in Ash Gate|
| unlock: encounter once       |
+------------------------------+
```

```text
+------------------------------+
| [I:k] BLACK CANDLE ACOLYTE   |
| Codex: observed              |
| HP: 50-70     threat: chant  |
| Known                         |
| - Uses delayed shadow chant. |
| Fog                           |
| - ░░░ weakness hidden ░░░    |
| - ░░░ drop table hidden ░░░  |
+------------------------------+
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

### 8.1 主屏状态机

TUI 不应只有一个静态战斗主屏，至少要有 5 种状态：

| 状态 | 触发 | 屏幕重点 |
|------|------|----------|
| `battle_intro` | 战斗开始 | 敌人、风险、Build 提醒 |
| `model_waiting` | 等待真实模型 | Provider、Ritual Time、上一轮状态，不刷屏 |
| `hero_action` | 英雄行动后 | 英雄动作、技能、目标、MP/CD、Judge |
| `enemy_action` | 敌人行动后 | 敌人动作、伤害、状态、威胁变化 |
| `battle_report` | 战斗结束 | 胜负原因、技能使用、承伤来源、图鉴/奖励 |

### 8.1.1 场景背景

战斗主屏必须有低密度背景层，体现当前副本。

| 场景 | ASCII 背景元素 | 用途 |
|------|----------------|------|
| Ember Crypt | `| candles | ash | arch |` | 新手、黑烛 |
| Ash Gate | `[gate] [shield fragments]` | 防守、灰烬 |
| Hollow Archive | `[index] [missing pages]` | 图鉴、遗忘 |
| Mire Vault | `~ mire ~ vials ~` | 毒、预兆 |
| Grave Engine | `[gear] [nails] [crank]` | 装置、爆破 |

背景只能增强氛围，不能挤占核心战斗数字。

### 8.2 动作帧样例

```text
TURN 07 :: HERO ACTION

[CNDL] Astia raises the black candle.
        shadow >>> [II:k] Black Candle Firekeeper

Action : Hex Seal -> Black Candle Firekeeper
Impact : 12 shadow damage, SLN silence(2)
Cost   : MP 54 -> 36, Hex Seal CD 4
Judge  : valid
```

```text
TURN 08 :: ENEMY ACTION

[I:c] Hungry Cultist claws at the candlelight.
Impact : Astia takes 7 physical damage
Shield : SHD 6 -> 0, overflow 1
Threat : Black Candle Firekeeper ATB 72 -> 84
```

### 8.3 战报样例

```text
BATTLE REPORT :: DEFEAT

Duration : 89 ticks / 34 hero turns
Killed by: Black Candle Acolyte - Chant Release

Hero Actions
Basic Attack        28   82%
Shadow Sting         1    3%
Hex Seal             3    9%
Corrupted Focus      2    6%

Main Damage Taken
Chant Release       70
Basic Attack        21

Build Note
Ready skills were ignored for 18 consecutive hero turns.
```

### 8.4 Build 胡牌 UI

```text
BUILD EVENT :: RESONANCE ONLINE

[R] Corruption School
shadow(3) + control(2)

Effect
Corrupted enemies take +4 shadow damage.

Astia's candle burns black.
```

```text
BUILD :: BLACK CANDLE INTERRUPT

Core tags
shadow  [###] 3/3  online
control [##-] 2/3  need 1
risk    [#--] 1/2  optional

Near
[ ] Candle Tribunal needs control +1

Best next picks
- Hexed Wick affix
- Black Sun Codex
```

### 8.5 Context 窗口 UI

```text
CONTEXT WINDOW
Strategy    : 2/3 slots
Codex       : 1/2 slots
Memory      : 340/500 echo
Prompt edit : 1/2

Upgrade next:
Level 3 -> Codex slot +1
```

---

## 9. 不可做

1. 不做复杂全屏动画阻塞测试。
2. 不把界面做成彩色噪音。
3. 不让 ASCII 图影响战斗数值可读性。
4. 不在 MVP 依赖图片、字体或 GUI。
5. 不为了展示 token 消耗牺牲战斗信息层级。
6. 不把 Build 和图鉴只藏在 trace 里，玩家界面必须可见。
7. 不让 `--no-animation` 变成“只显示最终结果”；它只能关闭延迟和微动画。
8. 不把副本路线、奖励、商店做成静默自动流程，除非显式处于 batch/auto 模式。
9. 不把 CLI 风格理解为无图标、无卡片、无背景、无动作。
10. 不把图鉴做成纯文字列表，必须有卡片和迷雾。
11. 不把战斗主屏做成上下列表或单列文字日志。
12. 不让武器、Build、技能只有名称，没有图标和阶段徽章。

---

## 10. 验收标准

1. 战斗主屏能显示 HP、MP、ATB、状态、模型行动、裁判结果。
2. 英雄详情能显示 Build 类型、装备、词条、羁绊和策略摘要。
3. 怪物列表能显示 family tier 和 codex stage。
4. BattleLLMSession 能显示 Battle Echo / Sealed Echo / Echo Cost。
5. Provider 配置界面不泄露 API key。
6. ASCII-safe 模式在 Windows PowerShell 可读。
7. 动画可关闭，输出可用于快照测试。
8. 战斗过程至少包含 intro、hero_action、enemy_action、battle_report 四类快照。
9. 英雄选择页能展示武器、Build、技能组合和 Prompt 倾向。
10. 玩家不打开 trace，也能从屏幕理解每场战斗为什么赢或输。
11. 图鉴页面能展示 locked / observed / mastered 三种卡片状态。
12. Build 页面能展示成型阶段、active resonance 和差几张提示。
13. Context 页面能展示 Strategy/Codex/Memory/Prompt edit 槽位。

---

## 11. 左右对战图形化硬规则

战斗默认界面必须参考 `art/08_战斗界面图形与动作分镜_20260504.md`。任何实现只要仍是“文字日志 + 单位列表”，就不满足 G14。

要求：

1. 左侧固定英雄区，右侧固定怪物区。
2. 英雄和怪物使用 4-6 行战斗精灵。
3. 中央区域显示弹道、斩击、毒雾、铃波、护盾、打断等效果。
4. 武器使用 `[W:*]` 图标和 ASCII 轮廓。
5. Build 使用 `[SEED]`、`[PAIR]`、`[ONLINE]`、`[HIGH]`、`[LOCK]` 徽章。
6. 日志最多显示最近 3-5 条，只解释画面结果。
7. `--no-animation` 仍必须输出 turn frame，不得退化成最终报告。
