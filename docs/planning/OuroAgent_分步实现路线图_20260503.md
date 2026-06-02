# Ouro Agent 分步实现路线图

> 日期：2026-05-03
> 最近同步：2026-06-01
> 状态：v0.4 release candidate；S0-S9 的实现与自动化证据已对齐到 `docs/product/06_需求追踪矩阵_20260503.md`。
> 原则：当前不再继续旧 S6/S7/S8/S9 的实现排队；完整目标是否 complete 取决于用户满意度、License、live-provider smoke 和 git 边界签收。

---

## 总体拆分

| 阶段 | 目标 | 状态 |
|------|------|------|
| S0 | 规则与计划沉淀 | done |
| S1 | 技术栈、发布安装与工程骨架 | done |
| S2 | 确定性战斗引擎 | done |
| S3 | 内容数据模型 | done |
| S4 | 模型行动协议与 mock model | done |
| S5 | 真实模型接入 | done |
| S6 | CLI / TUI 观战体验基础 | done |
| S6.1 | BattleLLMSession 改版 | done |
| S6.2 | Build / Buff / 图鉴 UI 改版 | done |
| S6.3 | 英雄与怪物内容扩展 | done |
| S7 | 节点型副本与商店 | done |
| S8 | 图鉴、成长、失败机制 | done |
| S9 | MVP 打磨与验证 | done |
| S10 | 无限模式、排行榜、模型对战预留 | later |

---

## 2026-06-01 Release Candidate 同步

当前路线图以 `06_需求追踪矩阵` 为唯一实现状态来源。S6-S9 已从旧的 `partial` / `next` / `pending` 同步为 release candidate done：

| 阶段 | 当前证据锚点 |
|------|--------------|
| S6 | `REQ-ART-*`、`REQ-BATTLEUI-001`、`REQ-TUIQA-002`、`REQ-TUICANVAS-*`；主战斗屏、no-animation 帧、ASCII/Unicode 舞台和宽度回归均有测试 |
| S6.1 | `REQ-SESSION-*`；trace 记录 `battle_session_id`、`static_context_hash`、`delta_context_id` |
| S6.2 | `REQ-BUILD-*`、`REQ-STATUS-001`、`REQ-CODEX-*`、`REQ-MODEL-001`；Build、Buff/Debuff、图鉴阶段、Intent/Risk/Align 可见 |
| S6.3 | `REQ-CONTENT-004`、`REQ-MON-001`；6 英雄、9 敌人、家族/tier/Boss 与内容校验通过 |
| S7 | `REQ-PLAY-001`、`REQ-PLAY-002`、`REQ-PLAY-003`、`REQ-RUNSTATE-*`；路线、奖励、商店、休息、Boss 楼层和完整 run 可玩 |
| S8 | `REQ-CODEX-002`、`REQ-RUNSAVE-001`、`REQ-LONGVIEW-*`；Codex、run archive、death history、status 下一局计划跨运行保留 |
| S9 | `REQ-QA-001`、`REQ-MANUAL-001`、`REQ-AUDIT-001`、`REQ-REL-*`；自动门禁、固定 seed 试玩、人工试玩记录、安装 smoke 和发布交接齐备 |

仍不能把整个用户目标标记为 complete 的项目不属于 S6-S9 未实现，而是外部签收：

1. 用户满意度确认：目标包含“让我满意”，需要用户试玩或明确接受。
2. License 或私有发布策略：需要用户选择，不能由实现代替。
3. live-provider smoke：需要用户提供真实 env 后运行。
4. git-boundary：需要人工审查并提交 release 范围。

这些项目由 `docs/engineering/RELEASE_SIGNOFF_20260601.md` 和 `scripts/signoff_check.py --strict` 跟踪。

---

## S0. 规则与计划沉淀

目标：让后续 AI 有清晰上下文，不靠对话残留推进。

已完成产物：

1. `OuroAgent_命令行AI肉鸽系统规划_20260503.md`
2. `OuroAgent_AI协作规则_20260503.md`
3. `OuroAgent_分步实现路线图_20260503.md`
4. `05-deliverables/ouro-agent/AGENTS.md`

验收标准：

1. 工作区地图可定位项目。
2. JOBS 可看到当前状态。
3. WAL 有核心决策记录。

---

## S1. 技术栈、发布安装与工程骨架

目标：建立最小可安装、可运行、可配置的 CLI 工程，不进入复杂玩法。

建议动作：

1. 选择语言和包管理方式，当前策划推荐 Python + pipx。
2. 创建 `05-deliverables/ouro-agent/` 下的工程骨架。
3. 建立基本目录：engine、content、llm、sessions、tui、tests。
4. 创建一个能启动的 CLI 命令：`ouro` 或 `ouro-agent`。
5. 支持 `ouro --version`、`ouro play --mock`、`ouro config show`。
6. 写入项目 README、安装命令、Provider 配置和开发命令。
7. 建立 Provider 配置骨架：mock/openai/anthropic/openai-compatible。

验收标准：

1. 从 GitHub 安装后 `ouro --version` 能运行。
2. 一条命令能跑测试。
3. 不需要真实 API key 也能跑 `ouro play --mock`。
4. `ouro config show` 不显示 API key 明文。

不要做：

1. 不做复杂 TUI。
2. 不做真实模型完整接入，只做配置层和 adapter 接口。
3. 不写大量装备和怪物。

---

## S2. 确定性战斗引擎

目标：先让游戏在没有 LLM 的情况下能完成一场战斗。

建议动作：

1. 定义 Actor、Stats、Skill、Status、BattleState。
2. 实现读条推进。
3. 实现普通攻击、技能、冷却、MP 消耗。
4. 实现敌人规则 AI。
5. 实现胜负判定和战斗日志。

验收标准：

1. mock 英雄和敌人能自动打完整场战斗。
2. 固定 seed 下结果一致。
3. 单元测试覆盖 HP、MP、冷却、状态、胜负。

不要做：

1. 不调用模型。
2. 不做路线地图。
3. 不做商店经济。

---

## S3. 内容数据模型

目标：让英雄、技能、装备、怪物从结构化数据加载。

建议动作：

1. 定义内容 schema。
2. 建立最少内容集：1 个英雄、3 个技能、2 个敌人、3 件装备。
3. 支持标签系统。
4. 支持装备三档：普通、英雄、传奇。
5. 支持基础羁绊判断。

验收标准：

1. 内容数据能通过校验。
2. 无悬空引用。
3. 同一场战斗可从内容数据生成。

不要做：

1. 不追求内容数量。
2. 不做复杂平衡。

---

## S4. 模型行动协议与 mock model

目标：先把模型协议打通，但用 mock model 代替真实 LLM。

建议动作：

1. 定义 action schema。
2. 实现 Prompt Composer。
3. 实现 Action Validator。
4. 实现 Repair / Fallback / Penalty。
5. 实现 mock model：根据战况返回结构化行动。
6. 保存 Model Turn trace。

验收标准：

1. mock model 能通过协议参与战斗。
2. 非法 action 会被拦截。
3. 可修复输出会被修复。
4. 不可用技能会触发降级或惩罚。

不要做：

1. 不先接真实 API。
2. 不让自然语言参与结算。

---

## S5. 真实模型接入

目标：让玩家配置 API key 后可以用真实模型自动战斗。

建议动作：

1. 实现 OpenAI-compatible Provider Adapter。
2. 支持环境变量或本地配置读取 API key。
3. 支持模型名配置。
4. 支持超时、重试、成本统计。
5. 输出原始响应到 trace。

验收标准：

1. 无 API key 时仍可用 mock mode。
2. 有 API key 时能跑完整战斗。
3. 模型输出错误不会导致程序崩溃。

不要做：

1. 不上传玩家数据。
2. 不做排行榜。
3. 不默认记录敏感 API key。

---

## S6. CLI / TUI 观战体验

目标：让战斗看起来像游戏，而不是日志打印。

建议动作：

1. 设计命令行主屏：英雄、敌人、读条、日志。
2. 展示模型思考状态和行动描述。
3. 展示伤害、状态、冷却和 MP 变化。
4. 支持快速模式和测试模式。
5. 输出战斗结算面板。

验收标准：

1. 玩家能看懂每次行动发生了什么。
2. 读条和行动反馈有节奏。
3. 日志不刷屏到无法阅读。

不要做：

1. 不做过度花哨动画。
2. 不牺牲可读性。

---

## S6.1 BattleLLMSession 改版

目标：把每场战斗从多次 stateless prompt 升级为一个持续的模型战斗会话。

建议动作：

1. 建立 `BattleLLMSession` 接口。
2. 把 Prompt Composer 拆成 static context 和 turn delta。
3. trace 记录 `battle_session_id`、`static_context_hash`、`delta_context_id`。
4. Provider 不支持服务端 session 时使用本地 transcript fallback。
5. mock 固定 seed 仍然可复测。

验收标准：

1. 同一场战斗只有一个 `battle_session_id`。
2. 静态 Build、技能、图鉴不在每回合完整重复。
3. 模型依然不能决定伤害、掉落、胜负。

不要做：

1. 不借 Session 机制让模型持有未解锁图鉴。
2. 不为了省 token 牺牲裁判可解释性。

---

## S6.2 Build / Buff / 图鉴 UI 改版

目标：让玩家能看懂英雄为什么这样行动，以及怪物危险程度和图鉴阶段。

建议动作：

1. 英雄详情显示 Build 类型、核心标签、装备、词条、羁绊。
2. 战斗主屏显示 Buff / Debuff 分组。
3. 怪物显示 family tier、glyph、codex stage。
4. BattleLLMSession 显示 Battle Echo / Sealed Echo / Echo Cost。
5. 增加 no-color 快照测试。

验收标准：

1. 玩家只看战斗屏就能知道当前 Build 和敌人档次。
2. 状态不依赖颜色也能读懂。
3. Session 成本展示不抢占 HP/MP/ATB。

---

## S6.3 英雄与怪物内容扩展

目标：把内容扩展到足以支撑新手副本和后续图鉴成长。

建议动作：

1. 规划并实现 6 英雄数据。
2. 定义至少 4 个怪物家族 I/II 档，1 个 III 档 Boss。
3. 新增 family/tier/codex 字段和校验。
4. 对 Build、怪物档次和英雄胜率做批量试跑。

验收标准：

1. 内容校验通过。
2. 每个怪物家族至少有图鉴 unknown/observed/familiar。
3. Build 改动能影响模型策略提示。

---

## S7. 节点型副本与商店

目标：从单场战斗扩展为一局肉鸽。

建议动作：

1. 实现固定新手副本地图。
2. 支持路线选择。
3. 支持普通怪、宝箱怪、商店、Boss。
4. 支持金币、经验、奖励三选一。
5. 支持商店购买和装备替换。
6. 支持关卡之间修改英雄 Prompt。

验收标准：

1. 玩家能从开局走到 Boss。
2. 选商店会牺牲战斗收益。
3. 奖励能影响下一场战斗。

不要做：

1. 不做随机生成大地图。
2. 不做多个副本难度。

---

## S8. 图鉴、成长、失败机制

目标：补齐长期驱动力。

建议动作：

1. 实现怪物图鉴阶段：未知、观察、熟悉、掌握、猎杀。
2. 实现战斗后图鉴进度更新。
3. 实现死亡后本局结束。
4. 保留图鉴、成就、少量残响货币。
5. 实现一次污染复活机制原型。

验收标准：

1. 重复遭遇怪物会解锁更多信息。
2. 模型只能看到已解锁信息。
3. 死亡后保留的东西明确、可解释。

不要做：

1. 不做复杂 meta 升级树。
2. 不让永久成长压过单局构筑。

---

## S9. MVP 打磨与验证

目标：从能跑变成可试玩。

建议动作：

1. 平衡新手副本。
2. 增加 3 个英雄。
3. 补足最低内容量。
4. 做 3-5 个羁绊。
5. 跑 10 次 mock model 测试。
6. 跑 3 次真实模型试玩。
7. 记录验证报告。

验收标准：

1. 新玩家能在 10 分钟内完成或失败一局。
2. 战斗失败原因可理解。
3. 模型错误有处理，不破坏整局。
4. CLI 反馈有观战乐趣。

不要做：

1. 不做线上功能。
2. 不做大型内容库。

---

## S10. 后续扩展

这些只做设计预留，不进入 MVP：

| 方向 | 预留点 |
|------|--------|
| 无限模式 | 战斗 trace、层数、seed、模型名、成本 |
| 排行榜 | 上传结果必须不含原始 prompt 和敏感 key |
| 玩家模型对战 | 需要标准化 build、seed、模型配置 |
| 自定义副本 | 需要内容 schema 和校验器成熟 |
| Build 分享 | 需要稳定 ID 和版本兼容 |

---

## 当前建议执行顺序

当前实现顺序已经推进到 MVP release candidate。下一轮建议不再按旧 S6.x/S7/S8/S9 继续排实现任务，而是按发布完成度处理：

1. 用户试玩或明确验收，生成 `docs/engineering/USER_ACCEPTANCE_20260601.md` 并写入 `SIGN-OFF: accepted`。
2. 决定 License 或私有发布策略，同步 `pyproject.toml`、README、release handoff。
3. 如需要真实 Provider 证据，设置用户提供的 env 后运行 `scripts/provider_smoke.py --live`，生成 `docs/engineering/PROVIDER_LIVE_SMOKE_20260601.md` 并写入 `SIGN-OFF: passed`。
4. 按 `docs/engineering/CHANGESET_MANIFEST_20260601.md` 审查 git 边界、stage、commit、tag。

如果后续要进入 S10，必须先新建 v0.2 范围需求，不能把无限模式、排行榜或模型对战混进 v0.1.0 release candidate。
