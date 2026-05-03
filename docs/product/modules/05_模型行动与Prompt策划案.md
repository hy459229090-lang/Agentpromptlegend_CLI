# G05 模型行动与 Prompt 策划案

> 状态：v0.2 草案
> 依赖：设计基线、G02 战斗系统、G03 Build、G07 图鉴、G09 Trace
> 本版目标：把“每次回合独立请求”升级为“每场战斗一个 Battle LLM Session”，减少重复上下文并提升模型连续决策能力。

---

## 1. 模块目标

模型是英雄战斗决策核心，但不能成为不可控裁判。

本模块解决三件事：

1. 模型如何在整场战斗中保持同一套战术记忆。
2. 哪些上下文只发送一次，哪些每回合发送 delta。
3. 模型输出如何继续被本地裁判安全结算。

---

## 2. Session 设计结论

旧方案：每次英雄 ATB 满时，构造完整 Prompt 并请求模型。

新方案：每场战斗创建一个 `BattleLLMSession`。静态上下文只初始化一次，每个英雄行动只追加“战况变化 delta + 需要决策的行动窗口”。

重要说明：

1. 仍然可以每个英雄行动请求一次模型输出 action，因为战况会变。
2. “一场战斗一个 LLM”指一个持续的模型会话/对话线程，而不是一次请求打完整场。
3. 如果 Provider 不支持服务端 session，就由本地维护 transcript 和 static context hash，尽量只拼接必要摘要。
4. 本地引擎仍然是唯一裁判，Session 不能保存隐藏未解锁图鉴。

---

## 3. BattleLLMSession 生命周期

| 阶段 | 输入 | 输出 | Trace 字段 |
|------|------|------|------------|
| `session_start` | 系统规则、英雄、Build、技能、已解锁图鉴、玩家 Prompt | `battle_session_id`、`static_context_hash` | session metadata |
| `turn_delta` | 当前 HP/MP/ATB、冷却、状态、敌人变化、最近行动 | 结构化 action | turn_id / delta_id |
| `judge_result` | 本地裁判结果、伤害、状态变化 | 供下回合模型读取 | judge summary |
| `session_summary` | 若上下文过长，压缩最近行动 | battle rolling memory | summary hash |
| `session_end` | 胜负、奖励、图鉴变化 | 结算摘要 | result |

---

## 4. 上下文分层

### 4.1 静态上下文，只发一次

1. 游戏硬规则：模型不决定伤害、掉落、胜负。
2. 英雄身份、职业、默认 Prompt。
3. 当前 Build 类型、装备、词条、羁绊。
4. 技能表：MP、冷却、目标规则、允许效果。
5. 已解锁图鉴阶段。
6. 输出 schema。

### 4.2 每回合 delta

1. 英雄 HP/MP/ATB 和当前状态。
2. 敌人 HP/ATB/状态和可见意图。
3. 技能冷却变化。
4. 上一回合本地裁判结果。
5. 新出现的图鉴观察。
6. 本回合必须决策的行动窗口。

### 4.3 滚动摘要

当 transcript 过长时，把最近战术历史压缩成：

```text
SESSION MEMORY
- Astia has spent most MP; conserve unless interrupting.
- Black Candle Acolyte has used chant twice; silence is high value.
- Hungry Cultist is low threat unless ignored for 3+ turns.
```

摘要不能加入未发生事实，不能写入隐藏图鉴。

---

## 5. 模型输出 Schema

```json
{
  "narration": "给玩家看的动作描述",
  "analysis": "简短战术理由，只能引用已知信息",
  "action": {
    "type": "cast_skill",
    "skill_id": "skill_shadow_sting",
    "targets": ["enemy_black_candle_acolyte"],
    "modifier": "interrupt_chant"
  },
  "session_notes": [
    "Enemy caster is the priority while ATB is high."
  ],
  "confidence": 0.78
}
```

只有 `action` 参与结算。`session_notes` 只能进入下一轮摘要候选，不能直接改状态。

---

## 6. Prompt 调整

玩家可以在以下时机调整英雄 Prompt：

| 时机 | 调整幅度 | 是否重建 BattleLLMSession |
|------|----------|---------------------------|
| 开局 | 完整编辑 | 是 |
| 商店 | 完整编辑 | 下一场战斗开始时生效 |
| 战后 | 小幅策略槽调整 | 下一场战斗开始时生效 |
| 战斗中 | 不允许 | 否 |

经验成长影响：

1. Prompt 容量。
2. 策略槽数量。
3. 可注入图鉴条数。
4. rolling summary 长度。

---

## 7. 降级与惩罚

| 情况 | 处理 | Session 策略 | 展示 |
|------|------|--------------|------|
| JSON 可修复 | 修复后执行 | 记录一次 format warning | 思绪短暂扭曲 |
| 意图可读但结构错误 | 降级执行，效果降低 | 写入 session warning | 动作不稳定 |
| 使用不可用技能 | 拒绝，改普通攻击或防御 | 注入 cooldown reminder | 法力/冷却不足 |
| 虚构技能或目标 | 拒绝，严重错误 | 清除该条 session note | 英雄迟疑 |
| 完全不可读 | 跳过或普通攻击 | 可触发 session reset | 意志断线 |
| Provider session 失效 | 切换 stateless fallback 或 mock | 保留本地 summary | 回声中断 |

---

## 8. 实现优先级

| 优先级 | 任务 | 原因 |
|--------|------|------|
| P0 | 设计并实现 `BattleLLMSession` 接口 | 真实模型成本和上下文质量的基础 |
| P0 | Trace 增加 `battle_session_id`、`static_context_hash`、`delta_context` | 后续评测模型决策需要证据 |
| P0 | Prompt Composer 拆成 static context + turn delta | 避免重复输入 |
| P1 | Provider 支持 conversation transcript / local cache | 不同 Provider 能力不同，要统一抽象 |
| P1 | Rolling summary 和 context budget | 内容和图鉴扩张后必要 |
| P2 | 多战斗 run-level memory | 等副本和图鉴存档稳定后再做 |

推荐顺序：先做 `BattleLLMSession`，再做更多怪物和复杂 Build。否则内容增加后每回合 Prompt 会膨胀，真实模型体验会变差。

---

## 9. 验收标准

1. 一场战斗有唯一 `battle_session_id`。
2. 静态上下文有 hash，可在 trace 中复盘。
3. 每个英雄行动只追加 turn delta 和必要摘要。
4. Prompt 中不重复完整技能/Build/图鉴大段内容，除非 session fallback。
5. Provider 不支持 session 时，系统有本地 transcript fallback。
6. 模型依然不能决定伤害、掉落、胜负。
7. 同 seed + mock 的结果仍然可复测。
