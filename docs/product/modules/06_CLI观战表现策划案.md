# G06 CLI 观战表现策划案

> 状态：v0.1 草案  
> 依赖：G02 战斗系统、G05 模型行动

---

## 1. 模块目标

让自动战斗在命令行里有观战价值。玩家虽然不能操作战斗，但必须持续知道英雄在判断什么、做了什么、造成什么后果。

---

## 2. 主屏信息

战斗中至少展示：

1. 英雄 HP / MP / ATB。
2. 敌人 HP / ATB / 关键状态。
3. 当前可见日志。
4. 模型行动状态。
5. 最近一次结算结果。

主屏不能只在战斗结束时展示。每次英雄或敌人行动后必须刷新一次 Battle Frame；如果启用 `--no-animation`，仍然要输出 turn frame，只是不 sleep、不做逐帧动画。

示例：

```text
阿斯缇娅 HP 82/100  MP 31/48  ATB ███████░░░

饥饿信徒 A HP 24/50  ATB ████░░░░░░  中毒 1
饥饿信徒 B HP 41/50  ATB ██████░░░░

[模型决策]
阿斯缇娅判断 B 的读条更危险，准备打断。
行动：暗影尖刺 -> 饥饿信徒 B
结算：造成 27 暗影伤害，附加 腐化 1 层
```

---

## 2.1 Battle Frame 结构

每个行动帧必须包含：

| 区块 | 内容 |
|------|------|
| Header | floor、seed、provider、speed、mode |
| Units | 英雄和敌人的 HP/MP/ATB/状态 |
| Action Beat | 谁行动、动作短句、目标 |
| Impact | 伤害、治疗、护盾、MP/CD、状态变化 |
| Judge | valid/fallback、降级原因 |
| Recent Log | 最近 6-10 条玩家可读日志 |

示例：

```text
TURN 07 :: HERO ACTION

Astia lifts the Black Candle; the shadow tightens into a needle.
Action : Shadow Sting -> Black Candle Acolyte
Impact : 34 shadow damage, CRP +1
Cost   : MP 54 -> 42, Shadow Sting CD 2
Judge  : valid

LOG
> Tick 12 Astia casts Shadow Sting.
> Black Candle Acolyte takes 34 shadow damage.
> Black Candle Acolyte gains CRP corrupt(1).
```

---

## 3. 表现节奏

| 事件 | 表现 |
|------|------|
| 读条推进 | 简短刷新，不刷屏 |
| 英雄行动 | 展示模型思考、动作描述、结算 |
| 敌人行动 | 展示敌人动作和伤害 |
| 非法行动 | 展示失败原因和惩罚 |
| 战斗结束 | 展示胜负、奖励、关键回合 |

### 3.1 动作反馈层级

| 层级 | MVP 要求 | 说明 |
|------|----------|------|
| L1 数值动作行 | 必做 | action、target、damage、status、MP/CD |
| L2 角色动作短句 | 必做 | 英雄/怪物各自有短动作句 |
| L3 ASCII 微动画 | 可选 | 2-3 帧，必须可关闭 |

动作短句必须像角色行动，不像 API 返回值；但不得加入未发生的效果。

---

## 4. 命令行控制

战斗中玩家不能控制英雄，但可以控制观看体验：

| 操作 | 作用 |
|------|------|
| pause / `p` | 暂停 |
| speed / `1-5` | 调整速度 |
| log / `l` | 查看完整日志 |
| inspect / `i` | 查看当前状态、技能 CD、状态详情 |
| quit / `q` | 放弃本局或退出 |

这些操作不能改变战斗结果。

MVP 如果暂不做实时按键监听，至少必须提供 CLI 参数：

| 参数 | 作用 |
|------|------|
| `--delay <sec>` | 每个 turn frame 后暂停 |
| `--fast` | 只输出关键 turn 和战报 |
| `--step` | 每个 turn 后等待 Enter |
| `--no-animation` | 关闭 sleep 和微动画，但保留 frame |
| `--auto` | 批跑模式，允许自动路线/奖励 |

---

## 5. 风格规则

1. 严肃暗黑，但优先可读。
2. 文案短，避免大段小说。
3. 关键数字必须清楚。
4. 动作描述要像角色行动，不像模型报告。
5. 不使用可爱化或过度玩梗语气。
6. 日志用玩家语言，不直接暴露内部 Python 类名或 JSON 字段名。
7. Echo/token 信息必须低于战斗信息，不能抢占屏幕中心。

---

## 6. 验收标准

1. 玩家能看懂每回合谁行动、打谁、造成什么。
2. HP、MP、冷却、状态变化清楚。
3. 模型错误有可理解的表现。
4. 日志可回看。
5. 测试模式可以关闭动画或加速。
6. `play --mock --delay 0.1` 能看到逐 turn 输出或刷新，不是静默等待后给最终屏。
7. 战斗结束必须输出技能使用率、普攻占比、主要伤害来源和死亡原因。
8. `--no-animation` 输出仍包含 turn frame，不能退化成最终快照。
