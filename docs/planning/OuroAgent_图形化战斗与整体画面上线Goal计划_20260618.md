# Ouro Agent 图形化战斗与整体画面上线 Goal 计划

> 日期：2026-06-18
> 目标类型：上线级产品 Goal
> 上游依据：
> - `docs/product/22_TUI图形化Canvas美术研发规格_20260516.md`
> - `docs/planning/OuroAgent_终端图形战斗舞台实施计划_20260617.md`
> - `docs/product/06_需求追踪矩阵_20260503.md`

---

## 1. Goal Statement

将 Ouro Agent 从“ASCII 面板驱动的 CLI 肉鸽”升级为可以上线展示的 **terminal-native cinematic roguelike**。

完成本 Goal 后，项目应满足：

1. 玩家默认看到的是有画面、有动作、有命中反馈的终端战斗舞台，而不是动态日志或调试面板。
2. 支持 bitmap 的终端优先使用 QA 通过的本地 PNG sprite 和 timeline 动画。
3. 不支持 bitmap 的终端使用 Unicode cell sprite 表达同一套动作语义。
4. ASCII 和 `--no-animation` 只作为兼容、CI、日志和无障碍 fallback，不再作为推荐体验上限。
5. 当前 MVP 全量内容都有资产、fallback、证据和 release gate。
6. 完成后可以发布为可安装、可试玩、可截图传播的 mock-first CLI 游戏。

一句话版本：

> 做完这个 Goal，Ouro 的 mock 离线试玩应该能作为正式上线版本被新玩家打开、观看、理解、截图和复现。

---

## 2. 为什么必须做这个 Goal

当前 UI 已经具备信息完整性，但视觉上仍容易像“命令行调试报告”：

1. ASCII 面板可以保证兼容，却很难支撑好看的默认体验。
2. 继续堆 phase、rail、pulse、FOCUS、RISK、NEXT 只会让画面更像动态文档。
3. 玩家第一眼需要看到战斗动作，而不是读文字理解发生了什么。
4. README、截图墙、首次试玩和真实游戏观感必须一致，否则上线后会显得像概念说明多于游戏。

因此本 Goal 的判断是：

> 先用战斗动画目标图定义审美上限，再把战斗、Build、奖励、商店、Codex、结算和 README 媒体整体向这个目标收敛。

---

## 3. 上线定义

本 Goal 完成后，允许进入上线准备的版本必须满足以下条件。

### 3.1 玩家体验

1. 新玩家按 README 的推荐命令运行 mock 试玩，无需 API key、无需联网、无需额外配置。
2. 第一场战斗能看到左英雄、右敌人、中心 effect lane、技能起手、弹道、hit stop、伤害跳字和状态落定。
3. 玩家不读长说明，也能看懂模型选择了什么行动、本地裁判造成了什么结果。
4. 完整 run 能展示路线、战斗、奖励、商店/休息/事件、死亡或胜利结算，并保持同一套视觉语言。
5. 失败后玩家能知道下一局怎么重开，而不是只看到统计字段。

### 3.2 图形体验

1. `--graphics auto` 在支持 bitmap 的真实 TTY 中优先选择 bitmap。
2. iTerm2、Kitty、SIXEL 至少有能力检测、escape writer 或模拟 evidence。
3. Unicode fallback 使用 cell sprite 和同一套 timeline，不退回普通文字箭头。
4. ASCII fallback 保持可读、确定性和 CI 友好。
5. `--no-animation` 不输出 live chrome，但保留压缩分镜和战斗日志。

### 3.3 内容覆盖

当前 MVP 必须全量覆盖：

1. 6 名英雄。
2. 全部 MVP 敌人。
3. 18 个技能。
4. 15 件物品。
5. 12 个 affix。
6. 5 个 resonance。
7. Ember Crypt dungeon、当前 node type 和 UI 状态。

Astia / Hex Seal 只允许作为 smoke evidence，不能单独代表完成。

### 3.4 工程和安全

1. mock provider 永远可离线运行。
2. 运行时不调用 ImageGen，不依赖网络生成图片。
3. API key 不进入 trace、日志、截图、README 或 release evidence。
4. renderer 只消费展示模型，不修改 `BattleState`、伤害、奖励、状态、胜负或 provider 契约。
5. release check、隐私扫描和 evidence gate 全部通过。

---

## 4. 非目标

本 Goal 不包括：

1. 新增英雄、敌人、技能、地图或大型内容包。
2. 真实 provider 调用体验优化。
3. 排行榜、多人、云存档、成就系统。
4. GUI、Web 版、Electron 版或非终端客户端。
5. 为了视觉效果修改战斗数值、模型决策或本地裁判规则。
6. 把某一张概念图直接作为运行时资产。

如果上述内容必须进入上线范围，必须先新增或更新 `REQ-*`。

---

## 5. 产品北极星画面

本 Goal 的北极星不是“更多 CLI 面板”，而是一张可执行的战斗动画目标图。

目标图必须表达：

1. Black Candle 暗黑仪式氛围。
2. 左英雄、右敌人、中心 effect lane。
3. 角色不是 ASCII 线条小人，而是 Ouro 自有 bitmap / Unicode cell sprite。
4. 技能有起手、释放、飞行、命中、hit stop、恢复。
5. HUD 只服务战斗，不压过舞台。
6. 行动解释压缩为短 action strip 和短 log。
7. 画面能反推 Build、奖励、Codex、结算的整体视觉语言。

该目标图用于指导资产、renderer、UI 和 README 媒体；它本身不等于运行时完成。

---

## 6. 阶段计划

### Phase 0：Goal 锁定和上线范围冻结

目标：确认“完成后可上线”的定义，避免继续漂移到玩法扩展。

任务：

1. 写入本 Goal 计划。
2. 关联现有 ready / in-progress 需求：
   - `REQ-TUIMOTION-022`
   - `REQ-ASSETGEN-001`
   - `REQ-TERMGRAPHICS-002`
   - `REQ-TERMGRAPHICS-003`
   - `REQ-REWARDASSET-001`
   - 已完成的 `REQ-TUICANVAS-*`、`REQ-ANIMSTAGE-001`
3. 列出尚未覆盖的上线缺口；缺口如无现有 REQ，必须补矩阵。
4. 明确 ASCII 是 fallback，不是推荐体验目标。

退出标准：

1. planning README 指向本计划。
2. 需求矩阵中相关 REQ 状态和证据口径清晰。
3. 不再以单个 Astia / Hex Seal smoke 作为完成口径。

---

### Phase 1：战斗动画目标图和视觉系统冻结

目标：先定义“好看”的具体画面，再继续实现。

任务：

1. 生成或整理 1 张战斗动画目标图。
2. 从目标图提炼视觉系统：
   - 构图比例。
   - 舞台留白。
   - sprite 尺寸。
   - effect lane 位置。
   - hit stop 表现。
   - damage pop 位置。
   - HUD 最大密度。
   - action strip 和 log 字数限制。
3. 明确三层 renderer 的视觉等价规则：
   - bitmap 最佳。
   - Unicode 推荐 fallback。
   - ASCII 兼容 fallback。
4. 写入产品规格或补充本计划。

退出标准：

1. 目标图能作为 README / issue / release review 的审美锚点。
2. 后续 UI 改动可以用目标图判断是否跑偏。
3. 明确禁止继续堆长解释 HUD 冒充动效。

证据：

1. 目标图文件或截图。
2. 视觉系统说明。
3. 人工 review note。

---

### Phase 2：全量资产和 QA 状态收敛

目标：确保上线不是单点 demo，而是当前 MVP 全量内容都有资产责任。

任务：

1. 校验 `content/assets/manifest.yaml` 覆盖当前 MVP 全量内容。
2. 校验 82/82 runtime 资产：
   - 有 QA record。
   - `qa_status: qa_passed`。
   - 有 frame metadata。
   - 有 anchor / duration / fallback。
   - runtime file 存在。
3. 确认运行时不读取 scratch candidate 或未 QA 资产。
4. 对资产质量做一次上线前人工审查：
   - 终端尺寸缩小后仍可识别。
   - 没有错字假 UI。
   - 没有品牌复刻。
   - 没有无关噪声。
   - pose / effect 有真实差异。

退出标准：

1. `asset_manifest_check.py` 通过。
2. `asset_qa_check.py` 通过。
3. `asset_status_report.py --require-all-runtime` 通过。
4. 资产缺口为 0，或有明确 QA 后 fallback 且不阻断上线。

证据：

1. 脚本输出。
2. QA 记录。
3. 人工资产审查 note。

---

### Phase 3：战斗舞台上线级接入

目标：让真实 `play` 和 `run` 的战斗体验达到上线观感。

任务：

1. `play` live path 使用 sprite timeline。
2. `run` live path 使用 sprite timeline。
3. 6 名英雄至少各有 signature 12 beat timeline。
4. 18 个技能都有可播放 effect timeline。
5. 全部 MVP 敌人都有可识别 idle / telegraph / hit / break / death 或 fallback silhouette。
6. hit stop、damage pop、状态落定在战斗帧中可见。
7. 精简战斗 live HUD：
   - 长模型解释不抢舞台。
   - phase 名不替代动作。
   - action strip 和 log 控制在短文本。
8. 宽度覆盖 80 / 100 / 120。

退出标准：

1. `ouro play --mock --seed 2 --graphics unicode --delay 0 --no-trace` 输出 sprite stage。
2. `ouro run --mock --seed 7 --graphics unicode --delay 0 --auto --no-trace` 输出 sprite stage。
3. `scripts/timeline_coverage_report.py --require-all-skills` 通过。
4. 战斗规则、trace schema、provider schema 没有变化。

证据：

1. 单测。
2. fake TTY 测试。
3. timeline coverage report。
4. 固定 seed 输出日志。

---

### Phase 4：战斗外 UI 视觉统一

目标：让完整 run 的非战斗界面也不像纯文本工具。

范围：

1. hero / build。
2. route。
3. reward。
4. shop。
5. rest。
6. event。
7. codex。
8. run result / run report。

任务：

1. 已有 ASCII board 保持兼容，但推荐 Unicode / asset path 展示图形化卡片。
2. 奖励、物品、affix、resonance 使用 QA-promoted runtime asset 或 fallback thumbnail。
3. Build 阶段统一使用 `[SEED]`、`[PAIR]`、`[ONLINE]`、`[HIGH]`、`[LOCK]` 视觉语言。
4. 选择页第一眼能看出当前选择对 Build、资源、风险或下一战的影响。
5. 中文和英文都不泄漏内部 ID。
6. 80 / 100 / 120 宽度稳定。

退出标准：

1. 完整 `ouro run --mock --auto` 从开局到结算视觉语言一致。
2. reward / shop / rest / event 不再像普通列表。
3. 有 atlas 时优先显示 runtime asset card；无 atlas 时 fallback 可读。

证据：

1. UI 单测。
2. 固定 seed run log。
3. 关键界面截图或 SVG。

---

### Phase 5：Fallback Parity 和终端能力闭环

目标：保证上线体验不只在开发机可看。

任务：

1. `ouro doctor graphics` 能解释当前 backend、fallback chain 和原因。
2. `--graphics auto` 行为稳定：
   - bitmap-capable TTY 选 bitmap。
   - tmux 默认保守 fallback。
   - CI / pipe / `--no-animation` deterministic。
3. iTerm2、Kitty、SIXEL 有测试或 simulated evidence。
4. Unicode filmstrip 和 ASCII filmstrip 与 bitmap timeline 语义一致。
5. `--no-animation` 无 live ANSI，但保留完整 turn frames。

退出标准：

1. `record_combat_stage.py` 输出 bitmap / Unicode / ASCII evidence。
2. `release_check.py --combat-stage-only` 通过。
3. `release_check.py --timeline-coverage-only` 通过。
4. `doctor graphics` 文案不误导玩家。

证据：

1. filmstrip。
2. capability report。
3. no-animation deterministic log。
4. terminal graphics tests。

---

### Phase 6：README、安装和上线材料

目标：确保上线后玩家看到的 README、命令和实际体验一致。

任务：

1. README / README.zh 首屏展示真实可复现画面，不使用无法复现的概念图冒充实机。
2. README 明确：
   - mock 离线可玩。
   - bitmap 是最佳路径。
   - Unicode 是 fallback。
   - ASCII / no-animation 是兼容路径。
   - runtime 不生图。
3. 截图墙覆盖：
   - Build。
   - Fight。
   - Learn / after-action。
4. 安装命令、试玩命令、doctor graphics 命令可复制运行。
5. release handoff、signoff、user acceptance 文档同步当前状态。

退出标准：

1. 新用户按 README 可完成首次 mock play。
2. README 不夸大 bitmap 支持范围。
3. README 图片和固定 seed 输出一致。
4. 文档测试和 privacy scan 通过。

证据：

1. README docs tests。
2. fixed seed logs。
3. screenshot / SVG media。
4. release handoff。

---

### Phase 7：上线硬门禁

目标：只有所有发布阻断项关闭后，才允许标记 Goal 完成。

必须通过：

1. `venv312/bin/python scripts/release_check.py`
2. `venv312/bin/python scripts/release_check.py --combat-stage-only`
3. `venv312/bin/python scripts/release_check.py --timeline-coverage-only`
4. `venv312/bin/python scripts/asset_status_report.py --content-dir content --require-all-runtime`
5. `venv312/bin/python scripts/asset_qa_check.py --content-dir content`
6. `venv312/bin/python scripts/asset_manifest_check.py --content-dir content`
7. privacy scan 无 API key、真实 trace、私密路径泄漏。
8. README 推荐命令人工试玩通过。

最终人工验收：

1. 新用户视角：README -> install -> mock play -> run -> report。
2. 视觉视角：战斗第一眼像游戏，不像日志。
3. 兼容视角：bitmap / Unicode / ASCII fallback 都能跑。
4. 工程视角：无规则污染、无 provider 破坏、无 trace schema 破坏。

---

## 7. 上线阻断条件

出现以下任一情况，本 Goal 不能标记完成，也不能上线：

1. `ouro play --mock` 或 `ouro run --mock --auto` 不能离线完成。
2. README 推荐命令失败。
3. 运行时需要 ImageGen、网络或 API key 才能看到推荐体验。
4. 未 QA 的图片被 runtime 读取。
5. 18 个技能 timeline coverage 不完整。
6. 6 名英雄仍有统一占位 actor 作为推荐体验。
7. bitmap 和 Unicode / ASCII 表达的战斗事实不一致。
8. `--no-animation` 丢失 turn frames 或 battle logs。
9. release check 或 privacy scan 失败。
10. 战斗规则、伤害、奖励、胜负被 renderer 改动。
11. README 截图与实际可复现输出明显不一致。

---

## 8. Goal Done Checklist

只有以下全部为真，才允许宣布本 Goal 完成：

1. [ ] Goal 文档和 planning README 已同步。
2. [ ] 战斗动画目标图和视觉系统已冻结。
3. [ ] 当前 MVP 82/82 资产 runtime / QA / fallback 状态通过。
4. [ ] 6 英雄 live battle 均有自有 sprite / signature timeline 证据。
5. [ ] 18 技能 timeline coverage 通过。
6. [ ] play 和 run 的 live graphics path 均有测试证据。
7. [ ] bitmap / Unicode / ASCII fallback parity 有 filmstrip 或日志证据。
8. [ ] reward / build / codex / run result 关键界面接入 runtime asset 或明确 fallback。
9. [ ] README / README.zh 的截图、命令、fallback 说明同步。
10. [ ] release check 全量通过。
11. [ ] privacy scan 通过。
12. [ ] 人工 mock-first 上线试玩通过。

---

## 9. 推荐 Codex Goal 文案

可以把本轮 Codex goal 设置为：

```text
完成 Ouro Agent 图形化战斗与整体画面上线 Goal：以战斗动画目标图为北极星，将默认体验从 ASCII 面板升级为 bitmap/Unicode sprite 驱动的 terminal-native cinematic roguelike；覆盖当前 MVP 全量英雄、敌人、技能、装备、词条、共鸣、场景和 UI 状态；保持 mock 离线可玩、战斗规则不变、fallback deterministic；补齐测试、filmstrip、截图/log、README 和 release gate，直到项目可作为 mock-first CLI 游戏上线。
```

---

## 10. 执行原则

1. 每次实现只推进一个可验证闭环。
2. 每个闭环必须包含代码、测试、证据和矩阵更新。
3. 没有证据的 REQ 不标 done。
4. 视觉目标优先于新增玩法。
5. fallback 是产品能力，不是失败路径。
6. 上线前宁可少做新内容，也不能让首屏观感回到调试面板。
