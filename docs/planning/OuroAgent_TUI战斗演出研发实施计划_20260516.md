# Ouro Agent TUI 战斗演出研发实施计划

> 日期：2026-05-16
> 输入：`20_战斗演出与TUI导演规格_20260516.md`
> 目的：把策划、美术、研发讨论落成可执行批次，避免继续在 `screens.py` 中堆字符串拼接。

---

## 1. 实施目标

把战斗表现升级为：

```text
engine facts -> BattleFrame -> BattleScreenModel -> layout blocks -> presenter
```

同时交付：

1. 局势台词。
2. Intent/Risk/Align 模型表达。
3. 数值 delta 和阈值反馈。
4. 反制窗口三段式。
5. 高潮事件横幅。
6. 80/100/120 宽度快照。

---

## 2. 批次拆分

### Batch TUI-0：战斗帧模型

目标：建立 `BattleFrame`，不急着重画界面。

任务：

1. 新增 `src/ouro_agent/tui/frame_builder.py`。
2. 定义 `BattleFrame`、`ResourceDelta`、`EffectFrame`、`SessionUsageFrame`。
3. 从现有 `BattleState` + `TurnRecord` 构建最小 BattleFrame。
4. 保持现有 `render_battle_screen()` 可用。

验收：

1. 固定 TurnRecord 可生成稳定 `BattleFrame`。
2. frame 包含 actor、target、action、judge、effect、session。

关联需求：

1. REQ-TUIARCH-001
2. REQ-TUIQA-002

### Batch TUI-1：布局组件

目标：消灭核心战斗屏中的裸截断和脆弱拼接。

任务：

1. 新增 `src/ouro_agent/tui/layout.py`。
2. 实现 `Block`、`panel`、`hstack`、`vstack`、`fit_text`、`wrap_visual`、`assert_width`。
3. 所有宽度使用 `visual_width()`。
4. 增加中文长文本、长 Boss 名、状态列表测试。

验收：

1. 80/100/120 列行宽硬断言通过。
2. 中文宽字符不破坏 panel。

关联需求：

1. REQ-TUIARCH-001
2. REQ-UIQA-001
3. REQ-TUIQA-002

### Batch TUI-2：战斗主屏 RenderModel

目标：让战斗屏消费展示模型，而不是直接猜 `TurnRecord`。

任务：

1. 新增 `src/ouro_agent/tui/render_model.py`。
2. 定义 `BattleScreenModel`、`ActorPanelModel`、`EffectLaneModel`、`ActionFocusModel`。
3. 新增 `src/ouro_agent/tui/battle_screen.py`。
4. 迁移 duel panel、effect lane、compact/standard/expanded 布局。
5. `screens.py` 保留兼容入口，内部调用新模块。

验收：

1. 当前集成测试不破。
2. ACTION 位于 Build/Session/Log 之前。
3. 80/100/120 battle snapshot 通过。

关联需求：

1. REQ-BATTLEUI-001
2. REQ-TUIARCH-001

### Batch TUI-3：资产注册表和局势台词

目标：把角色精灵、效果、台词从 `screens.py` 迁出。

任务：

1. 新增 `src/ouro_agent/art/battle_assets.py`。
2. 定义 hero/enemy pose registry。
3. 定义 effect glyph registry。
4. 定义 dialogue registry：intro、advantage、low_hp、mp_low、interrupt_success、build_trigger、boss_phase、near_defeat。
5. 主屏按 BattleFrame 选择 1 行台词。

验收：

1. 每个英雄至少 8 类台词，每类 3 条。
2. 低血、MP 紧张、打断成功、Boss 阶段能触发不同台词。

关联需求：

1. REQ-DLG-001
2. REQ-ART-003

### Batch TUI-4：Intent/Risk/Align 和数值阈值

目标：把模型解释和数值显示从 debug 变成可玩信息。

任务：

1. 从 prompt style、action、judge、resource delta 生成 `Intent`。
2. 基于 MP/HP/CD/ATB 生成 `Risk`。
3. 基于 Prompt/Build/Codex 生成 `Align`。
4. 生成 HP/MP/ATB/CD 的前后变化和阈值标签。

验收：

1. 每次英雄行动主屏显示 Intent/Risk/Align。
2. MP 低于关键技能消耗时出现明确提示。
3. HP critical、ATB ready、CD locked 有短标签。

关联需求：

1. REQ-MODEL-001
2. REQ-NUMFEED-001
3. REQ-PLAY-005

### Batch TUI-5：反制窗口和高潮横幅

目标：让打断、破防、Boss 阶段、Build 升级有强反馈。

任务：

1. 定义 `CounterWindowFrame`：threat、window、result。
2. Boss/蓄力敌人显示 Phase/Charge/Break/Enrage。
3. 定义高潮事件横幅：CHARGE BROKEN、BUILD ONLINE、HIGH ROLL、BOSS PHASE II、EXECUTE。
4. 战报回指成功或错过的窗口。

验收：

1. 黑烛蓄力敌人能展示预告、窗口、结果。
2. 诺恩 Boss seed 不再只有 timeout，而能解释错过/利用了什么窗口。

关联需求：

1. REQ-COUNTER-001
2. REQ-CLIMAX-001
3. REQ-BOSSUI-001

### Batch TUI-6：Presenter 和 Replay 预留

目标：统一 `play/run/replay` 的帧调度。

任务：

1. 新增 `src/ouro_agent/tui/presenter.py`。
2. 统一 `model_waiting`、`turn_frame`、`no_animation`、`refresh`、`scroll`。
3. CLI 不再各自定义 thinking/turn frame 函数。
4. 为 replay 消费 BattleFrame 做预留。

验收：

1. `play` 和 `run` 使用同一 presenter。
2. `--no-animation` 输出 SELECT/IMPACT/JUDGE。
3. 当前 CLI 集成测试通过。

关联需求：

1. REQ-TUIARCH-001
2. REQ-TUIQA-002

---

## 3. 测试计划

### 3.1 快照矩阵

P0：

1. `battle_80_en_ascii`
2. `battle_100_en_ascii`
3. `battle_120_en_ascii`
4. `battle_80_zh_ascii`

P1：

1. `battle_100_zh_ascii`
2. `battle_100_en_unicode`
3. `boss_100_en_ascii`
4. `boss_120_zh_ascii`

### 3.2 行宽断言

所有战斗屏快照：

```text
visual_width(line) <= width
```

不得只用 `len(line)`。

### 3.3 帧序列确定性

固定 seed 下断言：

1. frame id。
2. phase。
3. actor / target。
4. effect kind。
5. judge label。
6. resource delta。
7. event banner。

### 3.4 人工试玩

固定命令：

```bash
venv312/bin/ouro --lang zh run --mock --seed 7 --no-animation --auto
venv312/bin/ouro --lang zh run --mock --seed 7 --no-animation --auto --hero hero_ash_guardian
```

记录：

1. 最强战斗瞬间。
2. 最困惑一帧。
3. 是否看懂 Intent/Risk/Align。
4. 是否看懂数值阈值。
5. 是否出现反制窗口。

---

## 4. 风险控制

1. 不一次性重写全部 TUI。
2. 先建立兼容层，保持 `render_battle_screen()` 入口。
3. 先迁移战斗屏，不顺手重构 hero card、route、reward。
4. 资产先硬编码迁移到 registry，后续再数据化。
5. Boss UI 可先用假 frame 测布局，再接入真实规则。

---

## 5. 完成定义

完成后应满足：

1. 战斗屏有明确导演节拍。
2. 英雄台词回应局势。
3. 模型表达是 Intent/Risk/Align。
4. 数值展示有 delta 和阈值。
5. 反制窗口有预告、窗口、结果。
6. Boss 有 Phase/Charge/Break/Enrage。
7. `screens.py` 中战斗表现职责显著减少。
8. 80/100/120 中英快照和行宽断言通过。
