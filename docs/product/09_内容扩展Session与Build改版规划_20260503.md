# Ouro Agent 内容扩展、Session 与 Build 改版规划

> 版本：v0.3
> 日期：2026-05-04
> 用途：承接 Cursor 已完成 Slice 0/A/B 后的下一阶段策划，统一英雄、Build、怪物、图鉴、TUI 和模型 Session 的优先级。

---

## 1. 当前判断

Cursor 已完成可运行基础：CLI、mock 战斗、真实 Provider adapter、3 英雄、技能、装备、词条、羁绊和双语 UI。下一阶段不要马上堆副本路线，应先补齐会影响后续所有玩法的四类基础：

1. BattleLLMSession：降低真实模型重复上下文，提升连续决策。
2. Build 表达：让装备、词条、羁绊真正影响技能和目标选择。
3. 内容体系：扩展英雄、怪物家族、怪物三档和图鉴字段。
4. 游戏化体验：让 CLI 有卡片、图标、动作、背景、胡牌反馈和 context 成长。

---

## 2. 优先级建议

| 优先级 | 工作 | 原因 | 进入研发前置 |
|--------|------|------|--------------|
| P0 | BattleLLMSession 改版 | 真实模型成本、上下文质量和 trace 复盘的底座 | G05 v0.2 |
| P0 | Build 类型和 UI 展示 | 直接解决“Build 影响不明确” | G03 v0.3、G14 v0.2 |
| P0 | Buff/Debuff 统一表 | 怪物、装备、技能和 UI 都依赖 | G03 v0.3、art/04 v0.2 |
| P1 | 怪物家族三档和图鉴字段 | 完整副本、路线和长期成长依赖 | G07 v0.2、G10 v0.2 |
| P1 | 新增 3 个英雄规划 | 增加选择，但要等 Build 表达清楚 | G13 v0.3、art/02 v0.3 |
| P1 | 英雄详情/图鉴/Session UI | 提升游戏感和可读性 | G14 v0.2、art/07 |
| P1 | CLI 游戏化界面和动作资产 | 避免纯文本日志感，补左右对战、角色/怪物精灵、背景、图鉴卡片、胡牌反馈 | G17、G14、art/02/03/07/08 |
| P2 | 副本路线、商店、奖励 | 内容基础稳定后再进入 | G04 后续细化 |
| P2 | 图鉴长期存档和死亡保留 | 完整 run loop 后实现 | G07 + G09 |

---

## 3. 推荐下一轮研发切片

### Slice C0：BattleLLMSession

目标：把每场战斗从“多次 stateless prompt”升级为“一个 battle session + 多次 turn delta”。

交付：

1. `BattleLLMSession` 接口。
2. static context / turn delta 拆分。
3. trace 增加 `battle_session_id`、`static_context_hash`、`delta_context`。
4. mock 结果仍可复测。

不做：副本、商店、图鉴存档。

### Slice C1：Build 和 UI 可读性

目标：让玩家能在英雄详情和战斗主屏看到 Build、装备、词条、羁绊和状态。

交付：

1. Build 类型字段。
2. 英雄详情 Build 面板。
3. Buff/Debuff 分组显示。
4. 怪物 tier + codex stage 显示。
5. no-color 快照测试。

不做：新增大量数值平衡。

### Slice C2：内容扩展数据准备

目标：把新增 3 英雄和怪物三档变成内容数据的可验证 schema。

交付：

1. 6 英雄数据规划。
2. 4 个怪物家族 I/II 档，1 个 III 档 Boss。
3. 怪物 family/tier/codex 字段。
4. 内容校验测试。

不做：完整路线和商店经济。

### Slice C3：CLI 游戏化体验

目标：把英雄、Build、图鉴和战斗表现从文字列表升级为 CLI 游戏界面。

交付：

1. 主菜单和主要入口状态。
2. 英雄卡、Build 卡、奖励卡、图鉴卡。
3. 战斗场景背景和图标。
4. 左右对战主屏、中央弹道/命中效果层。
5. 英雄/怪物 4-6 行动作精灵。
6. 武器图标、Build 阶段徽章。
7. Build 成型阶段和胡牌事件。
8. 经验升级和 Context 窗口槽位。

不做：GUI、图片资源、大型剧情文本。

---

## 4. Cursor / Claude Code 分工建议

| 工具 | 建议任务 |
|------|----------|
| Cursor | 按 Slice C0/C1 做研发实现，补 tests 和 trace |
| Claude Code | Review session 边界、模型是否绕过本地裁判、UI 是否符合 no-color |
| Codex | 维护策划源、需求矩阵、工作区 JOBS/WAL 和 GitHub 文档一致性 |

---

## 5. 验收总标准

1. `python -m pytest -q` 通过。
2. `python -m ouro_agent.cli.main --lang en play --mock --seed 1 --no-trace` 可跑。
3. trace 中能看到 BattleLLMSession 字段。
4. 英雄详情能展示 Build 类型、核心标签、装备、羁绊。
5. 战斗主屏能展示 Buff/Debuff、怪物 tier、codex stage。
6. 图鉴详情能展示 locked/fog/unlocked 卡片。
7. Build 面板能展示 active / near / best next picks。
8. Context 窗口能展示 Strategy/Codex/Memory/Prompt edit 槽位。
9. 战斗主屏能展示左英雄右怪物、中央效果层、武器图标和 Build 阶段徽章。
10. 需求矩阵中新增 REQ 有证据路径或测试说明。
