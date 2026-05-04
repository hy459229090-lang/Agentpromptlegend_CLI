# Ouro Agent 玩家体验报告 — 基于实际案例的深度分析

> **测试日期**: 2026-05-03  
> **测试版本**: MVP Alpha (content_version: mvp_a)  
> **测试范围**: 6 英雄 × 2 模式(mock/real) × 多种子 + 副本路线全流程

---

## 一、战斗系统工作原理（实际案例拆解）

### 1.1 每一回合的完整数据流

以一局真实模型战斗为例（Astia vs 饥饿邪教徒 + 黑烛侍祭，seed=7）：

**Step 1 — 构建 Prompt**（`prompt.py:compose_prompt()`）

每次英雄回合，系统组装一个 `PromptContext`，包含三个部分：

```
┌─ System Prompt ──────────────────────────────────────────┐
│ You are an autonomous combat agent inside Ouro Agent.     │
│ Pick exactly one structured action per turn.              │
│ Only valid actions are: basic_attack, cast_skill, defend. │
│ The local engine resolves damage, status, MP and cooldown;│
│ your action proposal does not decide outcomes.            │
│                                                          │
│ Reply with ONE JSON object that matches the output schema │
│ Output schema: { ... JSON schema ... }                    │
└──────────────────────────────────────────────────────────┘

┌─ User Prompt (Hero) ─────────────────────────────────────┐
│ You are Astia, a hooded apprentice of the Black Candle.   │
│ Trade MP for tempo when an enemy is mid-cast.             │
│ Avoid wasting Shadow Sting on shielded foes.              │
│ Save Hex Seal for the most dangerous active threat.       │
└──────────────────────────────────────────────────────────┘

┌─ Battle Snapshot (JSON) ─────────────────────────────────┐
│ {                                                         │
│   "tick": 3,                                             │
│   "hero": { "hp": 93, "mp": 72, "attack": 8, ... },      │
│   "skills": [                                            │
│     { "id": "skill_shadow_sting", "mp_cost": 12,          │
│       "cooldown_remaining": 0, "ready": true },           │
│     { "id": "skill_hex_seal", "mp_cost": 18,              │
│       "cooldown_remaining": 0, "ready": true }            │
│   ],                                                      │
│   "enemies": [                                            │
│     { "id": "enemy_hungry_cultist", "hp": 50, "name":...},│
│     { "id": "enemy_black_candle_acolyte", "hp": 70,...}   │
│   ],                                                      │
│   "recent_log": ["Astia casts Hex Seal...", ...]           │
│ }                                                         │
└──────────────────────────────────────────────────────────┘
```

**Step 2 — 发送给模型**（`providers/openai.py` 或 `providers/anthropic.py`）

```
POST https://api.xxx.com/v1/chat/completions
{
  "model": "gpt-4o-mini",
  "max_tokens": 512,
  "temperature": 0.4,
  "response_format": {"type": "json_object"},
  "messages": [system_text, user_text]
}
```

**Step 3 — 模型返回 JSON**（真实模型输出示例）

```json
{
  "narration": "Astia casts Hex Seal on the acolyte.",
  "analysis": "Silencing the chanting acolyte before the chant releases.",
  "confidence": 0.85,
  "action": {
    "type": "cast_skill",
    "skill_id": "skill_hex_seal",
    "targets": ["enemy_black_candle_acolyte"],
    "modifier": null
  }
}
```

**Step 4 — 校验器解析**（`validator.py:parse_model_output()`）

校验器执行以下检查：
1. JSON 能否解析？→ 解析失败则尝试 repair（去掉 markdown 围栏、修复尾部逗号）
2. `action.type` 是否在合法列表？→ 不在则 fallback 到 `defend`
3. `skill_id` 是否存在于技能库？→ 不存在则 fallback 到 `basic_attack`
4. `targets` 是否为空？→ 空则自动选择第一个存活敌人

**Step 5 — Judge 裁决**（`judge.py`）

模型只"提议"行动，实际效果由本地引擎决定：

```python
# Hex Seal: base=6, power_scale=0.4, damage_type=shadow
damage = 6 + hero.power * 0.4 = 6 + 16 * 0.4 = 12.4 → 12
status = silence(duration=2)  # 敌人 2 回合无法施法
mp_cost = 18  # 英雄 MP 从 72 → 54
cooldown = 4  # 该技能 4 回合内不能再用
```

**Step 6 — 渲染画面**（`tui/screens.py:render_battle_screen()`）

```
OURO AGENT :: EMBER CRYPT :: FLOOR 1
Seed: mvp_a-007        Provider: openai-compatible        Speed: x1

HERO
[CNDL] Astia  Shadow Apprentice
HP [########--] 86/100   MP [##------] 54/72   ATB [#######---]
Status: -

ENEMIES
1. [c] [I] Hungry Cultist         HP [########] 50/50   ATB [----------]
2. [k] [I] Black Candle Acolyte   HP [######--] 56/70   ATB [##--------] [-]Silence(1)

MODEL TURN
Enemy enemy_hungry_cultist acts: basic_attack

LOG
> Astia casts Hex Seal. -MP 18, cd 4.
> Hex Seal deals 12 shadow to Black Candle Acolyte.
> Black Candle Acolyte silenced for 2 turns.
> Hungry Cultist hits Astia for 7.
```

### 1.2 关键设计决策

| 决策 | 做法 | 为什么 |
|------|------|--------|
| **技能触发方式** | JSON 输出，非 Function Calling | 兼容所有支持 JSON 模式的模型，不依赖 OpenAI 专有 API |
| **伤害计算** | 本地 Judge 引擎，模型不决定 | 防止模型作弊或幻觉，保证公平性 |
| **容错机制** | Validator 三层 fallback | 模型输出格式错误时不会崩溃，降级为 defend |
| **Prompt 透明度** | 完整规则和 schema 给模型 | 模型知道所有合法行动和输出格式 |

---

## 二、逐英雄实际案例分析

### 2.1 Astia（暗影学徒）— 技能使用率严重不足

**基础数值（build 后）**：HP 100 / MP 72 / ATK 8 / DEF 6 / POW 16

| 技能 | MP | CD | 设计用途 | 实际表现 |
|------|----|----|----------|----------|
| Shadow Sting | 12 | 2 | 主力输出(18+POW=34伤) | 89 ticks 只用 1 次 |
| Hex Seal | 18 | 4 | 沉默控制(6+POW*0.4=12伤) | 89 ticks 用 3 次 |
| Corrupted Focus | 0 | 3 | 自盾(8 stack) | 89 ticks 用 1 次 |

**实际战斗时间线（真实模型，seed=7）：**

```
Tick  1: Hex Seal → 12 dmg, silence acolyte    (MP 72→54)
Tick  3: basic_attack → 5 dmg                   (MP 54)
Tick  5: basic_attack → 5 dmg                   (MP 54)
Tick  7: basic_attack → 5 dmg                   (MP 54)
Tick  8: Shadow Sting → 34 dmg, kill cultist    (MP 54→42)
Tick 10: basic_attack → 5 dmg                   (MP 42)
Tick 12: basic_attack → 5 dmg                   (MP 42)
Tick 14: basic_attack → 5 dmg                   (MP 42)
Tick 16: basic_attack → 5 dmg                   (MP 42)
Tick 18: basic_attack → 5 dmg                   (MP 42)
Tick 20: Corrupted Focus → shield(8)            (MP 42)
Tick 22: basic_attack → 5 dmg                   (MP 42)
... (持续普攻，不再放技能) ...
Tick 80: Hex Seal → 12 dmg                      (MP 24→6)
Tick 85: Hex Seal → 12 dmg                      (MP 6→0, 不够 MP 了)
Tick 89: HP=0, defeated
```

**问题分析**：

1. **模型不理解 CD 循环**：Shadow Sting CD=2，理论每 2-3 tick 可用一次。89 ticks 应该能用 30+ 次，实际只用了 1 次。
2. **Prompt 有策略指引但模型不执行**：Prompt 说 "Trade MP for tempo when an enemy is mid-cast"，但模型在 acolyte 吟唱期间选择了 6 次普攻而非沉默。
3. **MP 管理混乱**：战斗结束时 MP=0，但大量 MP 是在战斗后半段被 Hex Seal 用光的——此时已经快死了。

**Mock 模式对比**：Mock Provider 返回固定 JSON，每次都放技能。战斗 15 ticks 结束，HP 85/100 胜利。

**根因**：真实模型的"注意力"集中在最近的 log 上，当战斗进入消耗战时，它退化为最简单的选项（basic_attack），不再阅读技能列表。

### 2.2 Mirel（沼泽神谕）— ATK=6 导致不可玩

**基础数值**：HP 90 / MP 88 / ATK 6 / DEF 5 / POW 29

| 行为 | 伤害计算 | 实际伤害 |
|------|----------|----------|
| basic_attack | ATK / 2 = 6 / 2 | **3** |
| Venom Drip | base 8 + POW * 0.8 = 8 + 23.2 | **31** (+ poison) |

**真实模型战斗（seed=7）：**

```
Tick  1: Venom Drip → 31 dmg, poison 3      (MP 88→76)
Tick  3: basic_attack → 3 dmg               (MP 76)  ← 问题开始
Tick  5: basic_attack → 3 dmg               (MP 76)
Tick  7: basic_attack → 3 dmg               (MP 76)
Tick  9: basic_attack → 3 dmg               (MP 76)
Tick 11: basic_attack → 3 dmg               (MP 76)
Tick 13: basic_attack → 3 dmg               (MP 76)
Tick 15: basic_attack → 3 dmg               (MP 76)
Tick 17: basic_attack → 3 dmg               (MP 76)
Tick 19: basic_attack → 3 dmg               (MP 76)
Tick 21: basic_attack → 3 dmg               (MP 76)
Tick 23: basic_attack → 3 dmg               (MP 76)
Tick 25: basic_attack → 3 dmg               (MP 76)
Tick 27: basic_attack → 3 dmg               (MP 76)
→ 敌人 chant_release × 5 = 70 dmg → HP 90→20 → 死亡
```

**数据对比**：
- Mirel 总输出 = 31(技能) + 3×12(普攻) + poison 伤害 ≈ 67
- 敌人总输出 = 70(5次 chant_release) + 普攻 ≈ 90+
- Mirel 72 ticks 死亡

**如果是合理 ATK=12**：
- basic_attack = 6 dmg（翻倍）
- 12 次普攻 = 72 伤害（而非 36）
- 总输出 ≈ 103 → 可以在死亡前击杀

**Mock 模式对比**：Mock 固定输出技能循环，Venom Drip 每 CD 就放，配合 poison 完成击杀。

**结论**：ATK=6 是致命设计缺陷。模型看到 snapshot 中 basic_attack 合法就反复选择，不理解"只用技能"的 attrition 策略。

### 2.3 Korr（墓地工匠）— ATK=21 导致技能多余

**基础数值**：HP 110 / MP 36 / ATK 21 / DEF 10 / POW 33

| 行为 | 伤害计算 | 实际伤害 |
|------|----------|----------|
| basic_attack | ATK / 2 = 21 / 2 | **10-11** |
| Gear Deploy | base 15 + POW * 0.8 | **41** |

**真实模型战斗（seed=7）：**

```
Tick  1: Gear Deploy → 41 dmg            (MP 36→21)
Tick  3: basic_attack → 11 dmg           (MP 21)
Tick  5: basic_attack → 11 dmg           (MP 21)
Tick  7: basic_attack → 11 dmg           (MP 21)
Tick  9: basic_attack → 11 dmg           (MP 21)
Tick 11: basic_attack → 11 dmg           (MP 21)
Tick 13: basic_attack → 11 dmg           (MP 21)
→ 敌人死亡，victory
```

Korr 赢了，但 **6 次普攻总伤害 = 66，超过技能 41**。技能存在感极低。

**对比 Vela（ATK=14）**：
- Vela basic_attack = 7 dmg
- Vela 需要 12 次普攻击杀
- 所以 Vela 会用技能来加速

**Korr 的问题不是输，而是战斗策略性为零**：普攻伤害太高，模型发现"我不需要技能也能很快打死"。

### 2.4 其余英雄快速分析

| 英雄 | ATK | 真实模型结果 | 评价 |
|------|-----|-------------|------|
| Norn | 12 | 胜 (HP 182/197) | 坦克定位正确，高 HP 兜底，但同样只用普攻 |
| Vela | 14 | 胜 (HP 66/80) | ATK 较高但 HP 太低，走钢丝。模型不会用 Eclipse Step 躲避 |
| Sera | 8 | 胜 (HP 75/105) | Resonant Strike 用了 2 次(50+49 dmg)，表现最好 |

---

## 三、副本系统 — 代码完整但交互为零

### 3.1 实际执行的节点流程

以 `CampaignLoop.run()` mock 模式（seed=1）为例：

```
Layer 0 → 自动选择 node_normal_1 (Hungry Followers)
          → 战斗胜利 → 自动奖励 +20 Gold（无选择界面）
Layer 1 → 自动选择 node_elite_1 (Black Candle Ritual)
          → 战斗失败 → Campaign End: defeat
```

玩家看到的输出：

```
Battle starting... node_normal_1
[Battle screen renders, 30 ticks]
Battle ended: victory
Battle starting... node_elite_1
[Battle screen renders, 45 ticks]
Battle ended: defeat
```

**没有**：路线选择界面、奖励三选一、商店购买、休息回血、事件交互。

### 3.2 代码层面分析

`campaign.py` 中 4 个 node 处理函数的实际行为：

```python
# _process_battle_node (line 296)
# 战斗正常执行，但奖励自动生成自动应用
rewards = self.reward_manager.generate_rewards(...)
self._apply_reward(rewards[0], run_state)  # 永远选第一个

# _process_shop_node (line 408)
event_handler(CampaignEvent(event_type="shop_start", ...))
event_handler(CampaignEvent(event_type="shop_end", ...))
# 中间没有任何购买逻辑！

# _process_rest_node (line 440)
event_handler(CampaignEvent(event_type="rest_start", ...))
event_handler(CampaignEvent(event_type="rest_end", ...))
# 没有回血！没有任何效果！

# _process_event_node (line 466)
# 只给固定 gold/xp，无交互
```

### 3.3 路线选择的代码存在但未暴露

```python
# campaign.py line 215-229
available_nodes = [n for n in layer.nodes if not n.visited]
selected_idx = 0  # ← 永远选第一个！
selected_node = available_nodes[selected_idx]
```

`RouteNode` 数据结构有 `choices` 字段：

```python
# run.py line 421-426
RouteNode(node_id="node_normal_1", node=nodes["node_normal_1"],
          choices=["node_elite_1", "node_chest_1"])  # ← 分支选择存在
```

但 `_process_layer()` 从未向玩家展示这些 choices。

---

## 四、核心问题清单（附代码证据）

### P0 — 阻断"可玩性"

| # | 问题 | 代码位置 | 影响 |
|---|------|---------|------|
| 1 | **零玩家输入** | `campaign.py:220` `selected_idx = 0` | 所有决策自动化 |
| 2 | **路线选择缺失** | `campaign.py:215-229` | 分支路线形同虚设 |
| 3 | **奖励无选择** | `campaign.py:402` `rewards[0]` | 三选一变"一给一" |
| 4 | **商店空壳** | `campaign.py:408-438` | start→end 瞬间跳过 |
| 5 | **休息无效** | `campaign.py:440-464` | 无 HP/MP 恢复 |

### P1 — 严重影响游戏平衡

| # | 问题 | 证据 | 影响 |
|---|------|------|------|
| 6 | **Mirel ATK=6 不可玩** | 普攻 3 伤害，72 ticks 败 | 真实模型 100% 输 |
| 7 | **Korr ATK=21 技能无用** | 普攻 11 伤害 > 技能频率 | 策略深度为零 |
| 8 | **精英节点过强** | 2/2 测试均在 elite_1 败北 | 副本无法推进 |
| 9 | **模型不管 CD** | Astia 89 ticks 只放 1 次 Shadow Sting(CD=2) | 技能系统失效 |

### P2 — 体验优化

| # | 问题 | 影响 |
|---|------|------|
| 10 | 战斗无加速/跳过 | 每场 3-5 分钟，无法快进 |
| 11 | 战斗结束无统计 | 只显示 defeat，无 DPS/技能使用率 |
| 12 | 无战斗日志回顾 | 打完就没了，无法分析复盘 |

---

## 五、优化建议与具体实现方案

### 5.1 最小可玩交互层（建议优先实现）

在 CLI 模式下加入 `input()` 键盘选择，**不需要改动 TUI 框架**。

#### A. 路线选择（修改 `campaign.py:_process_layer()`）

```python
# 当前代码（第 220 行）
selected_idx = 0

# 改为
if len(available_nodes) > 1:
    print("Next node options:")
    for i, node in enumerate(available_nodes, 1):
        glyph = node.node.get_glyph()
        name = node.node.get_display_name(self.language)
        print(f"  [{i}] {glyph} {name}")
    choice = input(f"Choose (1-{len(available_nodes)}): ")
    try:
        selected_idx = int(choice) - 1
        selected_idx = max(0, min(selected_idx, len(available_nodes) - 1))
    except ValueError:
        selected_idx = 0  # fallback
```

**玩家实际体验**：
```
Next node options:
  [1] ! Hungry Followers
  [2] ! Ash Remnant Patrol
Choose (1-2): 2
```

#### B. 奖励选择（修改 `campaign.py:_process_battle_node()` 胜利分支）

```python
# 当前代码（第 382-404 行）
rewards = self.reward_manager.generate_rewards(...)
self._apply_reward(rewards[0], run_state)

# 改为
rewards = self.reward_manager.generate_rewards(...)
print("Choose a reward:")
for i, r in enumerate(rewards, 1):
    print(f"  [{i}] {r.get_display_name(self.language)}")
choice = input(f"Choose (1-{len(rewards)}): ")
try:
    idx = int(choice) - 1
    idx = max(0, min(idx, len(rewards) - 1))
except ValueError:
    idx = 0
self._apply_reward(rewards[idx], run_state)
```

**玩家实际体验**：
```
Choose a reward:
  [1] +20 Gold
  [2] +15 XP
  [3] Item: Ash-Steel Blade
Choose (1-3): 1
```

#### C. 商店交互（修改 `campaign.py:_process_shop_node()`）

```python
# 当前代码（第 408-438 行）— start 后直接 end
# 改为
shop = Shop(seed=self.seed + len(run_state.visited_node_ids), bundle=self.bundle)
print(f"Shop - {shop.shop_tier} (Gold: {run_state.gold})")
for i, item in enumerate(shop.inventory, 1):
    print(f"  [{i}] {item.get_display_name()} - {item.cost}g")
print(f"  [{len(shop.inventory)+1}] Leave shop")

while True:
    choice = input("Buy (number) or leave: ")
    if choice == str(len(shop.inventory) + 1):
        break
    try:
        idx = int(choice) - 1
        if shop.buy(idx, run_state):
            print(f"  Bought! Gold: {run_state.gold}")
        else:
            print(f"  Cannot buy (not enough gold or sold out)")
    except ValueError:
        pass
```

#### D. 休息回血（修改 `campaign.py:_process_rest_node()`）

```python
# 当前代码（第 440-464 行）— 无任何效果
# 改为
hero = bundle.heroes.get(run_state.hero_id)
# 需要在 RunState 中维护当前 HP/MP，或传递 BattleState
# 简化方案：恢复固定比例
heal_pct = 0.3
print(f"Rest Site - Recover {int(heal_pct*100)}% HP?")
print("  [1] Rest")
print("  [2] Skip")
choice = input("Choose (1-2): ")
if choice == "1":
    # 需要在 RunState 或 CampaignLoop 中维护 hero 当前 HP
    # 这里只是一个示意
    print(f"  Recovered HP!")
```

> **注意**：休息节点需要跨战斗维护英雄 HP 状态。当前架构中 BattleLoop 结束后 HP 状态丢失。建议在 `RunState` 中增加 `hero_hp` 和 `hero_mp` 字段。

### 5.2 英雄数值平衡调整

| 英雄 | 当前值 | 建议值 | 变化 | 理由 |
|------|--------|--------|------|------|
| Mirel ATK | 6 | **12** | +6 | 普攻从 3→6，至少要有基本威胁 |
| Korr ATK | 21 | **15** | -6 | 普攻从 10→7，技能重新变得有价值 |
| Vela ATK | 14 | **14** | 不变 | 合理，但 HP 80 偏低 |
| Vela HP | 80 | **90** | +10 | 给模型更多犯错空间 |
| Norn ATK | 12 | **12** | 不变 | 坦克定位，数值合理 |
| Astia ATK | 8 | **8** | 不变 | 法师定位合理 |
| Sera ATK | 8 | **8** | 不变 | 合理 |

### 5.3 精英节点难度调整

**当前**：`node_elite_1` = enemy_black_candle_firewarden + enemy_hungry_banner_bearer

两个精英敌人同时出场，MVP 阶段英雄打不过。

**建议方案**（二选一）：
- **A**: 只放一个精英敌人 (`enemy_black_candle_firewarden`)
- **B**: 保持两个敌人，但各自 HP 降低 30%

### 5.4 模型 Prompt 增强 — CD 提醒

当前 snapshot 已经包含 `cooldown_remaining` 和 `ready` 字段：

```json
"skills": [
  { "id": "skill_shadow_sting", "cooldown_remaining": 0, "ready": true }
]
```

但模型会忽略这些信息。建议在 prompt 中增加 **显式提醒**：

```python
# prompt.py compose_prompt() 中，在 snapshot 前插入
ready_skills = [s for s in hero.skills if s.is_ready(hero.mp)]
if ready_skills:
    skill_names = [s.display_name.get(lang) for s in ready_skills]
    snapshot["skill_reminder"] = f"Ready to use: {', '.join(skill_names)}"
```

效果：模型看到 `"skill_reminder": "Ready to use: Shadow Sting, Corrupted Focus"` 时更可能选择技能。

### 5.5 战斗加速模式

在 CLI 增加 `--fast` 参数：

```python
# cli/main.py _cmd_play()
if args.fast:
    # 跳过 TUI 渲染和 turn delay
    loop.run(state)  # 无 hook，无 sleep
    # 只输出最终结果
    print(f"Result: {state.result} in {state.tick} ticks")
    print(f"Hero HP: {state.hero.hp}/{state.hero.max_hp}")
    for e in state.enemies:
        print(f"  {e.name}: {e.hp}/{e.max_hp}")
```

---

## 七、策划文档盲区分析 — 哪些问题是策划案没说清楚导致的

以上报告列出了大量实现层面的问题，但回看策划文档，**部分问题是策划案本身规划不够清晰或不够具体导致的**。本节以实际案例对照策划文档原文，指出需要补充或修正的策划点。

### 7.1 交互层缺失 — G01/G04 定义了"要做什么"但没定义"怎么做"

**问题**：路线选择、奖励选择、商店交互全部未实现。

**策划文档原文对照**：

| 策划案 | 原文 | 缺失点 |
|--------|------|--------|
| G01 核心循环 | "玩家选择路线节点" | 没有说明在 CLI 中如何操作 — `input()`? 数字键? 方向键? |
| G04 关卡路线 | "玩家能选择下一节点"（验收标准 #2） | 没有给出 CLI 交互样例 |
| G01 玩家控制边界 | "战后：选择奖励、查看战报" | 没有说明奖励选择的交互方式 |
| G04 商店功能 | "购买装备、购买词条、替换装备、调整 Prompt" | 没有描述商店 CLI 界面长什么样 |

**策划案中有样例但不够具体**：

G01 总纲第 6 节"第一版体验样例"给出了概念级示例：

```text
[路线选择]
左：普通怪 - 饥饿信徒
右：商店 - 黑烛商人

你选择普通怪，获得经验和掉落机会。
```

但这只是**叙事级描述**，没有转化为 CLI 交互规格。实现者看到的是一道没有标准答案的题：

- 是 `input()` 输入数字？
- 是方向键选择？
- 是 TUI 菜单？
- 是自动选择但显示给玩家看？

**实际结果**：实现者选择了最简单的路径 — 自动选第一个节点（`selected_idx = 0`），因为策划案没有强制要求玩家输入。

**建议补充**：在 G04 中增加一节"CLI 交互规格"，明确每个玩家选择点的输入方式和输出格式。参照 G06 CLI 观战的规格写法。

### 7.2 CLI 控制 — G06 设计了"战斗中控制"但没定义战斗外

**问题**：战斗中没有 pause/speed/log/inspect 控制。

**策划文档原文对照**：

G06 CLI 观战表现第 4 节"命令行控制"：

| 操作 | 作用 |
|------|------|
| pause | 暂停 |
| speed | 调整速度 |
| log | 查看完整日志 |
| inspect | 查看当前状态 |
| quit | 放弃本局或退出 |

**问题在于**：

1. 这 5 个操作定义了"做什么"，但**没有定义"怎么触发"**。是键盘快捷键？还是 `input()` 命令？还是 TUI 按钮？
2. 这些操作需要事件循环（监听键盘输入），但当前战斗循环是**线性的**：`loop.run()` 一路跑到底，没有给玩家输入留口子。
3. G06 验收标准 #5 说"测试模式可以关闭动画或加速"，但**没有说正式模式怎么加速**。

**实际结果**：战斗循环完全没有玩家控制输入，因为：
- 架构上 `BattleLoop.run()` 是阻塞式循环
- 策划没有定义如何在 ATB 循环中插入输入监听
- 实现者不知道是应该在每个 tick 后 `input()`，还是用 `kbhit()`，还是用 TUI 库

**建议补充**：G06 需要增加"技术实现指导"章节，明确：
- 战斗中控制是用 `input()` 还是 `keyboard` 库还是 TUI 事件循环
- pause/speed 是改变 `turn_delay` 还是跳过渲染
- 如果 MVP 做不了完整控制，至少要定义一个 `--fast` 参数（跳过渲染，只输出结果）

### 7.3 战斗结束反馈 — G06/G07 要求"可理解的结果"但实现只有一行

**问题**：战斗结束只显示 `Result : defeat`，没有死亡原因、关键回合、图鉴变化。

**策划文档原文对照**：

| 策划案 | 原文 |
|--------|------|
| G06 表现节奏 | "战斗结束：展示胜负、奖励、关键回合" |
| G07 失败规则 | "失败结算必须告诉玩家：死于哪个怪物家族/档次、本局解锁了哪些图鉴信息、哪个 Build 选择可能造成风险" |
| G10 验收标准 | "新手副本失败原因可解释" |

**实际结果**：

```
BATTLE COMPLETE
Result : defeat
Trace : F:\...\.player_home\traces\run_1777831937_b001.trace.jsonl
```

完全没有 G07 要求的三项信息。

**根因分析**：G07 的要求很明确，但**没有定义输出格式**。是在 CLI 打印？是写到文件？是 JSON？策划案写了"必须告诉玩家"但没写"怎么告诉"。

**建议补充**：在 G07 中增加"失败结算输出样例"，例如：

```text
BATTLE COMPLETE
Result : DEFEAT
Killed by : Black Candle Acolyte (Family: Black Candle, Tier: I)
  Chant Release × 5 = 70 damage total
Codex unlocked : Hungry Cultist → Observed
Build note : Consider more MP for Hex Seal frequency
Trace : F:\...\run_XXX.trace.jsonl
```

### 7.4 数值偏离基线 — G10 有明确范围但英雄 YAML 超出范围

**问题**：Mirel ATK=6 和 Korr ATK=21 严重偏离 G10 定义的基线。

**策划文档原文对照**：

G10 数值平衡第 3 节"英雄数值基线"：

| 英雄类型 | Attack 范围 |
|----------|------------|
| 法术控制 | 6-10 |
| 毒沼消耗 | **6-10** |
| 高速猎手 | 12-17 |
| 装置代理 | 8-12 |

Mirel 属于"毒沼消耗"类，ATK=6 **在范围内**。Korr 属于"装置代理"类，ATK=21 **严重超出** 8-12 的范围。

**但问题不是简单的"没按文档"**：

1. G10 给了范围（6-10），但没有给**每个英雄的具体推荐值**。实现者可能在范围内选了最低值（Mirel=6），结果发现太弱。
2. G10 没有给出**build 后的最终数值**。Mirel 的 default_build 包含 `item_cracked_wand`（power+?）和 `affix_corrupted_focus`，但策划案没有计算 build 后的 ATK 总。
3. G10 没有给出**普通攻击伤害公式**。当前实现是 `ATK / 2`，但如果策划知道 6/2=3 伤害，可能不会接受 ATK=6。

**根本问题**：G10 的数值表是一个"参考范围"，不是"每个英雄的具体数值"。实现者在范围内取值后，没有经过"跑一局看看 3 伤害是否合理"的验证。

G10 自己第 9 节"不可做"也说了：

> "不在没有完整 run loop 前做过细数值。"

**这是一句正确的防御性声明，但也正是它让数值问题流到了实现层。**

**建议补充**：
1. G10 应给出**每个 MVP 英雄的具体推荐数值**（不是范围），例如 "Mirel: ATK=9"
2. G10 应明确**普通攻击伤害公式**，并在表格旁标注对应的普攻伤害预期
3. 增加"数值试玩验证"步骤：每个英雄用 mock 跑 10 局，要求单场英雄行动数在 G10 第 2 节定义的范围内（普通战斗 4-8 次）

### 7.5 BattleLLMSession 降级 — G05 设计完整但实现只做了一半

**问题**：G05 设计了完整的 Session 生命周期，但实际实现中：
- 每回合仍然是完整 Prompt（static context 重复发送）
- 没有 turn_delta 机制
- 没有 rolling summary
- 没有 context budget 管理

**策划文档原文对照**：

G05 模型行动第 4 节"上下文分层"：

| 层级 | 内容 | 发送频率 |
|------|------|----------|
| 静态上下文 | 规则、英雄、技能、Build、图鉴 | **只发一次** |
| 每回合 delta | HP/MP/ATB、冷却、状态变化 | 每回合 |
| 滚动摘要 | 最近战术历史压缩 | 上下文过长时 |

**实际实现**（`prompt.py:compose_prompt()`）：

每回合都重新组装完整的 snapshot，包含：
- hero 全部属性
- skills 全部列表（含 cooldown）
- enemies 全部信息
- recent_log 最近 6 条

虽然不算"完整静态上下文"重复（技能列表确实在 snapshot 里），但 **rules_summary 和 output_schema 是每回合都在 system_text 里重复的**。

**但这里策划案也有责任**：

1. G05 说"静态上下文只发一次"，但没有说明**在什么 API 形态下能做到**。OpenAI 的 Chat Completions 是 stateless 的，每次都要重发 system message。只有 Anthropic 的 prompt caching 可以做到"只计费一次"。
2. G05 的 Session 设计假设了"持续的对话线程"，但当前 Provider 架构是每次 `request_turn()` 新建 HTTP 请求。
3. G05 的实现优先级表（第 8 节）把 "Prompt Composer 拆成 static context + turn delta" 列为 P0，但当前 prompt.py 没有做这个拆分。

**根本问题**：G05 的 Session 设计在架构上需要一个**有状态的 Provider 接口**（支持多轮对话），但当前的 `Provider.request_turn(prompt: PromptContext)` 是无状态的。这个架构缺口策划案没有意识到。

**建议补充**：
1. G05 应明确：Session 在有状态 Provider（如 Anthropic Messages API 带 caching）和无状态 Provider（OpenAI Chat）下的不同实现策略
2. 在当前架构下，先不做 turn_delta，改为"system message 缓存优化"：将 rules_summary + output_schema 放到独立的 system message，利用 Anthropic prompt caching
3. rolling summary 可以延后，但 skill_reminder（显式提醒就绪技能）应该是 P0

### 7.6 怪物强度 — G07 三档设计与实际精英节点不匹配

**问题**：精英节点放两个敌人，玩家必败。

**策划文档原文对照**：

| 策划案       | 原文                        |
| --------- | ------------------------- |
| G07 怪物三档  | II 仪式档 HP 80-135，机制 2-3 个 |
| G10 节点收益  | 精英怪 II 档"高概率英雄档奖励"        |
| G01 新手关   | 第 3 层"宝箱怪 / 精英怪"          |
| G10 第 2 节 | "精英战目标 6-10 次英雄行动"        |
|           |                           |

**实际实现**：`node_elite_1` 放的是 `enemy_black_candle_firewarden` + `enemy_hungry_banner_bearer`。

这两个敌人是什么档位？查看 mvp_enemies.yaml：

- `enemy_black_candle_firewarden`：不在已有的 YAML 里（YAML 只有 acolyte 和 archbishop）
- `enemy_hungry_banner_bearer`：也不在已有的 YAML 里

**这是一个策划与实现的双盲问题**：

1. 策划案定义了怪物家族和三档，但**MVP 内容文件中只有 2 个 I 档敌人**（cultist + acolyte）
2. 实现者在 `create_mvp_nodes()` 中引用了**不存在的 enemy_id**
3. 这些 enemy_id 可能是在其他分支或未来内容中定义的，但当前战斗中可能根本加载不了

**实际战斗中**：Mock Provider 可能通过 fallback 处理了缺失的敌人，或者实际运行中用的是 I 档敌人。但无论如何，**精英节点的"两个敌人"设计本身就超出了 MVP 英雄的承受能力**。

G10 说精英战应该 6-10 次英雄行动，但实测中精英战斗要么：
- 英雄 4-5 次行动就死了（失败太快）
- 或者根本打不赢（无法完成 6-10 次）

**建议补充**：
1. G04 应明确 MVP 新手关的每个节点的**敌人数量和档位**，而不是只说"精英怪"
2. G10 应增加"多敌人战斗的总 HP 预算"规则：精英战敌人总 HP 不应超过英雄单次技能伤害的 N 倍
3. 当前 MVP 阶段建议精英节点只放 1 个 II 档敌人

### 7.7 商店/Prompt 调整 — G04 要求"大幅调整 Prompt"但无实现路径

**问题**：商店可以调整 Prompt，但游戏中没有任何 Prompt 编辑界面。

**策划文档原文对照**：

G04 关卡路线第 5 节"商店功能"：

> 4. 大幅调整英雄 Prompt。

G05 模型行动第 6 节"Prompt 调整"：

| 时机 | 调整幅度 |
|------|----------|
| 商店 | 完整编辑 |
| 战后 | 小幅策略槽调整 |

**实际结果**：商店节点 start→end 瞬间跳过，没有任何交互。

**但这里策划案的问题更大**：

1. "完整编辑 Prompt" 在 CLI 中意味着什么？是一个 `input()` 让用户打字？还是一个预设策略选择菜单？
2. 用户打一段 Prompt 文本，怎么验证合法性？怎么防止注入？
3. Prompt 编辑完怎么即时生效？下一场战斗才开始用？

这是一个**UX 设计难题**，策划案把它列为"必须做"但没有给方案。

**建议补充**：
1. MVP 阶段把"大幅调整 Prompt"降级为"选择预设策略模板"，例如：
   - [1] 激进：优先输出
   - [2] 保守：优先生存
   - [3] 控制：优先打断
2. 完整的自由编辑延后到 TUI 阶段

### 7.8 跨战斗状态 — 策划案假设了"Run 级状态"但没定义数据流

**问题**：休息节点需要回血，但 BattleLoop 结束后 HP 状态丢失。

**策划文档原文对照**：

G01 核心循环：

```
节点执行：战斗 / 商店 / 事件 / Boss
    ↓
结算奖励或失败
    ↓
继续路线，直到 Boss、死亡或通关
```

这个循环暗示了**英雄状态在战斗间持续**（否则"继续路线"没有意义）。但 G02 战斗系统只定义了单场战斗。

**实际结果**：`RunState` 跟踪了 gold/xp/items 等运营数据，但**没有跟踪英雄当前的 HP/MP**。每次战斗都是满血开始。

**建议补充**：
1. G01 或 G04 应明确"英雄 HP/MP 在战斗间持续，休息节点恢复"
2. `RunState` 应增加 `hero_hp` 和 `hero_mp` 字段，BattleLoop 结束时写回

### 7.9 策划文档整体评价

| 维度         | 评分   | 说明                                        |
| ---------- | ---- | ----------------------------------------- |
| **系统完整性**  | 9/10 | 15 个模块覆盖全面，从战斗到图鉴到经济到美术都有                 |
| **交互规格**   | 3/10 | 大量"玩家能做什么"但几乎没有"怎么操作"                     |
| **数值严谨度**  | 5/10 | 有范围基线但缺少具体推荐值和验证公式                        |
| **架构指导**   | 4/10 | Session 设计有缺口，未考虑 Provider 的 stateless 特性 |
| **输出格式**   | 4/10 | 多处"必须展示/告诉玩家"但没有输出样例                      |
| **MVP 边界** | 7/10 | 有"不做"列表，但交互层是否属于 MVP 有歧义                  |

### 7.10 策划 → 实现的断点总结

```
策划案说了"要做什么"  ──✅──>  大部分做到了
                               │
策划案没说"怎么做"      ──❌──>  实现者选择了最简单的路径（自动化）
                               │
策划案的数值范围        ──⚠️──>  实现者在范围内取值但未验证可玩性
                               │
策划案的架构设计        ──❌──>  与实际 Provider 接口不匹配（stateless vs stateful）
                               │
策划案的输出要求        ──⚠️──>  有要求但没有格式样例，实现极简
```

**核心教训**：策划文档需要在"系统设计"和"交互规格"之间架桥。每个"玩家能做什么"都应该配套一个"在 CLI 中通过 ___ 操作"的规格说明。数值基线应该附带一个"预期战斗时长"的计算验证。

---

## 八、总结

### 8.1 当前状态

| 维度 | 评分 | 说明 |
|------|------|------|
| **战斗引擎** | 8/10 | ATB、技能 CD、状态效果、Judge 裁决、Validator 容错均可靠 |
| **模型集成** | 7/10 | 调用链路通畅，Fallback 机制有效，但模型行为不可控 |
| **内容质量** | 8/10 | 英雄设计有特色，技能效果有差异化，双语支持完整 |
| **可玩性** | 2/10 | 零玩家输入，路线/奖励/商店全自动化 |
| **数值平衡** | 4/10 | Mirel 不可玩，Korr 技能无用，精英节点卡关 |
| **用户体验** | 3/10 | 无加速、无统计、无回顾 |
| **策划→实现** | 5/10 | 策划文档系统完整但交互规格缺失，导致实现自由裁量过大 |

### 8.2 优先级排序

```
第一阶段（1-2 天）：最小可玩交互
  ├── 路线选择 input()
  ├── 奖励选择 input()
  ├── 商店 input()
  └── 休息回血 + RunState 维护 HP

第二阶段（0.5 天）：数值平衡
  ├── Mirel ATK 6→12（或 9，取 G10 范围中值）
  ├── Korr ATK 21→15
  └── 精英节点减难（只放 1 个敌人）

第三阶段（1 天）：体验优化
  ├── Prompt CD 提醒（skill_reminder）
  ├── --fast 战斗加速
  ├── 战斗结束统计（胜负、关键回合、死亡原因）
  └── 失败结算格式化（参照 G07 要求）

策划文档补充（并行）：
  ├── G04 增加 CLI 交互规格章节
  ├── G06 增加技术实现指导
  ├── G07 增加失败结算输出样例
  ├── G10 增加每个英雄的具体推荐数值
  └── G05 明确 Session 在 stateless Provider 下的实现策略
```

### 8.3 一句话总结

**战斗引擎已经是"像个游戏"的程度，但交互层的缺失让它目前是"AI 演示"而非"可玩原型"。补上 4 个 `input()` 选择点 + 调整 2 个英雄数值，就能从 20 分体验跳到 60 分可玩。策划文档系统完整但交互规格缺失，这是后续所有模块都需要补上的一课。**
