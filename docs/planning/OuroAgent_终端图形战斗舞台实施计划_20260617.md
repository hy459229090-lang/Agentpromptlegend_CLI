# Ouro Agent 终端图形战斗舞台实施计划

> 日期：2026-06-17
> 输入：`22_TUI图形化Canvas美术研发规格_20260516.md`、`REQ-TUIMOTION-022`
> 目的：把“像 GIF 一样的 CLI 战斗动画”拆成可执行的美术、架构、实现、验收批次。

---

## 1. 决策结论

Ouro 的默认观战体验不再继续沿着“文字面板加颜色和闪烁”的方向迭代。新的战斗舞台采用分层 renderer：

1. **Bitmap Sprite Renderer**：最佳体验路径。终端支持时使用 Kitty Graphics、iTerm2 inline image 或 SIXEL 显示真实 PNG/GIF 帧。
2. **Unicode Cell Sprite Renderer**：默认兼容体验。终端不支持 bitmap 时，用 truecolor block、braille、mosaic cell 还原同一套 timeline。
3. **ASCII Renderer**：最低兼容和证据路径。用于 CI、管道、`--no-animation`、no-color、极弱终端和日志归档。

这意味着 Ouro 仍然是 CLI 游戏，但目标体验是 **terminal-native cinematic game**，不是纯文本战斗日志。

---

## 2. 不变边界

本计划只改展示层，不改玩法核心：

1. 不改 `BattleState` 结算。
2. 不改 `TurnRecord` 的伤害、状态、胜负和奖励事实。
3. 不改 provider adapter 输出契约。
4. 不让模型决定伤害、掉落、奖励或胜负。
5. mock provider 必须继续无网络、无 key 可玩。
6. `--no-animation` 只关闭延迟和动态图形，不删除 turn frames 和 battle logs。
7. 非 TTY、CI、管道输出必须 deterministic。
8. Bitmap 能力不可成为安装硬依赖；缺失时必须 fallback。

---

## 3. 目标画面和覆盖范围

最终目标不是做一个 Astia 演示案例，而是让当前 MVP 内容都具备可播放、可降级、可验收的图形资产。实现可以分批进入游戏，但资产生产计划和验收口径必须覆盖完整内容目录。

当前必须覆盖：

| 类别 | 范围 | 资产要求 |
|------|------|----------|
| 英雄 | 6 名：Astia、Norn、Vela、Mirel、Korr、Sera | portrait、battle idle、ready、attack、skill、guard、hit、low HP、victory、defeat、signature timeline |
| 敌人 | `content/enemies/mvp_enemies.yaml` 中全部敌人 | family silhouette、tier variant、idle、telegraph、attack/cast、hit、break、death、codex reveal |
| 技能 | `content/skills/mvp_skills.yaml` 中 18 个技能 | effect sprite、travel/impact/recover frames、damage/status pop、fallback cell effect |
| 装备 | `content/items/mvp_items.yaml` 中 15 件物品 | icon、card art、small silhouette、battle HUD mark |
| 词条/羁绊 | 12 个 affix、5 个 resonance | badge、reward card motif、build online/high roll visual |
| 场景 | Ember Crypt floors、shop、rest、event、boss chapel | stage background、low-density floor texture、combat intro plate |
| UI 状态 | HP/MP/ATB、buff/debuff、silence、bleed、poison、shield、corruption、codex、reward | icon/badge、damage pop、status chip、fallback glyph |

Astia / Hex Seal 仍作为冒烟播放切片，因为它最能证明 Black Candle 视觉、角色动作、法印飞行和 hit stop 是否成立；但它只是首个接入点。任何实现、验收、文档或 release gate 都不得把这个切片当成完成标准。

| 项 | 决策 |
|----|------|
| 场景 | Ember Crypt / Black Candle ritual stage |
| 英雄 | Astia / Shadow Apprentice |
| 怪物 | Black Candle Firekeeper，必要时先映射到现有 Hungry Cultist / Black Candle Acolyte |
| 技能 | Hex Seal |
| 构图 | 左英雄、右怪物、中间 effect lane，顶部 status line，底部短 action strip 和 2 行 log |
| 动画 | 12 帧 timeline，8-12 fps，包含 anticipation、release、travel、hit stop、settle、recovery |
| 禁止 | ASCII 小人、长解释标题、闪烁冒充动作、重复大角色 filmstrip |

视觉组合采用：Black Candle 主视觉、Mirror Index 信息架构、Ash Gate 命中重量感。

---

## 4. 渲染架构

目标管线：

```text
BattleFrame
  -> BattleScreenModel
  -> CombatStageModel
  -> AnimationTimeline
  -> StageFrame
  -> RendererBackend
  -> PresentedFrame / terminal escape output
```

新增或调整模块：

| 模块 | 职责 |
|------|------|
| `src/ouro_agent/tui/terminal.py` | 检测 TTY、TERM、TERM_PROGRAM、tmux、color depth、bitmap protocol 候选 |
| `src/ouro_agent/tui/graphics.py` | `GraphicsCapability`、`GraphicsMode`、`select_graphics_backend()` |
| `src/ouro_agent/tui/renderers.py` | `RendererBackend` 协议和 fallback chain |
| `src/ouro_agent/tui/bitmap_renderer.py` | Kitty、iTerm2、SIXEL 的 escape writer 和 frame cache |
| `src/ouro_agent/tui/cell_renderer.py` | Unicode cell sprite 合成，复用当前 Canvas/Surface 能力 |
| `src/ouro_agent/art/sprite_atlas.py` | `SpriteAtlas`、`ActorSprite`、`EffectSprite`、metadata 读取 |
| `src/ouro_agent/art/timelines.py` | `AnimationTimeline`、Hex Seal smoke 12 帧和 6 英雄 signature timeline 定义 |
| `src/ouro_agent/tui/stage_model.py` | 把 `BattleFrame` 映射为舞台 actor、effect、HUD、damage pop |
| `scripts/record_combat_stage.py` | 生成 filmstrip、PTY log、fallback log 和证据摘要 |

`screens.py` 只保留兼容入口。战斗舞台不再在 `screens.py` 内部拼角色和特效。

---

## 5. 资产合同

### 5.1 Bitmap 资产

Bitmap 资产必须覆盖当前 MVP 全部内容，而不是只做一套演示图。资产生产可以按批次提交，但 `AssetManifest` 从一开始就要列出完整覆盖清单和每个条目的状态：`planned`、`generated`、`qa_passed`、`integrated`、`fallback_ready`、`evidence_done`。

| 资产 | 数量 | 尺寸建议 | 用途 |
|------|------|----------|------|
| Hero actor sheets | 6 套 | 96x96 或 128x128 PNG，透明背景 | 每名英雄 portrait + 8-10 个战斗姿态 |
| Enemy actor sheets | 当前全部敌人，后续随 content 增加 | 96x96、128x128，Boss 可 192x128 | family/tier 差异、telegraph、hit、break、death |
| Skill effect sheets | 当前 18 个技能 | 160x64 或 192x64，透明背景 | spawn、travel、near-hit、impact、dissolve、guard/buff |
| Stage textures | 每个 dungeon/floor/node type 至少 1 张 | 320x160 或 480x240 | 地表、背景、boss chapel、shop/rest/event mood |
| Item/reward cards | 当前 15 件物品 + affix/resonance | 64x64 icon + card crop | hero card、reward、shop、build online |
| Status/UI sprites | 当前战斗状态和 HUD token | 32x32 或 renderer text overlay | damage pop、SLN、BLD、PSN、SHD、CRP、Codex reveal |

资产原则：

1. 不使用概念图本身作为游戏资源，只把它作为方向。
2. sprite 必须有透明背景和稳定 anchor。
3. actor 的视觉锚点要在 64x64 缩放下仍能识别。
4. effect 不能只是一条箭头，要有法印、拖尾、命中形变。
5. 运行时不依赖网络生成图片。
6. 每个 bitmap 资产必须有同语义的 Unicode cell fallback 和 ASCII-safe fallback。
7. 生图输出必须经过人工/脚本 QA 后才能进入 `content/assets/`。
8. repo 内保存的是可运行的本地资产和 metadata，不保存未筛选的大量候选图。

### 5.1.1 开发期生图流程

ImageGen 只用于开发期资产生产，不进入游戏运行时。运行时不得联网生成图片。

流程：

1. 为每个资产族生成 art brief：角色锚点、动作姿态、尺寸、透明背景、禁用元素、终端缩放目标。
2. 用 ImageGen 生成候选 sprite sheet、effect sheet、stage plate 和 card/icon sheet。
3. 对候选图做 art QA：
   - 缩到终端目标尺寸后仍能识别。
   - 左右站位和 anchor 稳定。
   - 没有文字假 UI、错字、品牌复刻或无关元素。
   - 相邻动作帧有真实 pose/effect 差异。
   - 不含不适合 MIT 项目分发的侵权或来源不明素材。
4. 通过 QA 后复制到 repo 资产目录，保留原始生成图在 Codex generated image cache，不直接依赖 cache。
5. 运行脚本切分、压缩并生成 metadata：
   - `asset_id`
   - `source_content_id`
   - `frame_id`
   - `anchor`
   - `duration_ms`
   - `role`
   - `terminal_size`
   - `fallback_cell_id`
   - `qa_status`
6. 对每个资产生成 fallback cell sprite 和 ASCII-safe glyph/card。

建议目录：

```text
content/assets/
  README.md
  _rules.md
  manifest.yaml
  source_briefs/
  sprites/heroes/
  sprites/enemies/
  effects/skills/
  stages/
  ui/
  generated_metadata/
```

创建该目录时必须同步 `docs/engineering/CODE_LAYOUT.md`、`content/README.md` 和本目录规则。

### 5.2 Unicode Cell 资产

同一套 timeline 必须有 cell fallback：

| 资产 | 要求 |
|------|------|
| actor cell frame | 固定宽高，例如 10x6 cells，不使用 `. ^ /|` 线条小人作为主体 |
| effect cell frame | 法印、trail、impact 使用 block、braille、sextant 或 truecolor mosaic |
| damage pop | 贴近目标侧，不能挤占 HUD |
| pose delta | 相邻帧至少有 pose、effect offset、damage pop、HUD delta 中一项变化 |

---

## 6. Capability 和 CLI 合同

新增可见命令和选项：

```bash
ouro doctor graphics
ouro play --mock --graphics auto
ouro play --mock --graphics bitmap
ouro play --mock --graphics unicode
ouro play --mock --graphics ascii
```

默认策略：

1. TTY + 用户未关闭 graphics：`auto`。
2. `auto` 优先级：iTerm2 inline image -> Kitty Graphics -> SIXEL -> Unicode cell -> ASCII。
3. tmux/screen 中默认保守选择 Unicode，除非检测到 passthrough 或用户显式指定。
4. 非 TTY、CI、pipe：ASCII 或 no-animation deterministic 输出。
5. `--no-animation` 不走 bitmap frame loop，但仍输出压缩分镜。

`ouro doctor graphics` 必须说明：

1. 当前选择的 backend。
2. 为什么没有选择更高 backend。
3. 如何强制切换。
4. fallback 是否可用。
5. 是否处于 tmux、CI、非 TTY 或 no-color。

---

## 7. 批次拆分

### Batch GFX-0：计划锁定和需求拆分

目标：让后续实现有可执行输入。

任务：

1. 更新 `22_TUI图形化Canvas美术研发规格` 的技术边界。
2. 在需求矩阵登记 graphics backend、Astia vertical slice、fallback parity。
3. 增加本实施计划到 planning README。

验收：

1. `tests/unit/test_requirement_matrix.py` 通过。
2. `git diff --check` 通过。
3. `REQ-*` 仍为 ready，未实现前不标 done。

### Batch GFX-1：Graphics Capability Doctor

目标：先知道玩家终端能显示什么，不碰战斗画面。

任务：

1. 扩展 `terminal.py` 或新增 `graphics.py`。
2. 实现 backend 选择和 explain reason。
3. CLI 增加 `doctor graphics`。
4. 加测试覆盖 iTerm2、Kitty、SIXEL、tmux、CI、pipe、forced mode。

验收：

1. mock/offline 不变。
2. `ouro doctor graphics` 在当前机器给出 backend 和 fallback chain。
3. forced invalid mode 有清晰错误。
4. 不新增 runtime heavy dependency。

### Batch GFX-1.5：全量美术生图和资产 QA 管线

目标：先把当前 MVP 全部内容变成可生产、可审查、可追踪的资产清单。这个批次不是概念验证；它是后续 renderer 和播放集成的资产门禁。

任务：

1. 新增 `AssetManifest` 规格，覆盖 6 英雄、当前全部敌人、18 技能、15 物品、12 affix、5 resonance、`dungeon_ember_crypt`、所有当前 node type 和 UI 状态。
2. 为每个资产族写 ImageGen prompt brief 和禁用项，不只写 Astia/Hex Seal。
3. 用 ImageGen 生成候选资产，并按 `qa_passed` 才能进入 repo 的原则筛选。
4. 增加切图/压缩/metadata 脚本设计，后续实现时落到 `scripts/`。
5. 为每个 bitmap 资产登记 Unicode cell fallback 和 ASCII-safe fallback 责任。
6. 建立 coverage check：当前 content 增删 ID 时，manifest 缺项必须失败。
7. 明确 Astia/Hex Seal 是 smoke test，不允许作为全量资产完成证据。
8. 生成候选图必须按 manifest 的 82 个 work order 批量推进；任何单张好看的候选图只证明方向或流程，不证明资产完成。
9. 每个 work order 至少经历 `planned -> generated -> qa_passed -> integrated -> fallback_ready -> evidence_done`，缺任一状态都不能算完成。
10. `generated` 候选图只能保留在开发期 cache 或 scratch 目录；进入 repo 的运行时图片必须是 QA 通过、切帧完成、metadata 完整、fallback 已登记的产物。
11. 每个资产族都需要统一审美约束和禁用项：无文字假 UI、无品牌复刻、无不可分发素材、无与角色/技能无关的装饰噪声。
12. smoke 切片仍优先用 Astia / Black Candle / Hex Seal，但只用于验证 renderer、timeline、hit stop、切图和 fallback，不得替代其他英雄、敌人、技能、装备和 UI 状态的生产。

验收：

1. manifest 没有漏掉当前 content 中的英雄、敌人、技能、物品、affix、resonance、dungeon、node type 和 UI 状态。
2. 资产条目有状态字段，不允许未 QA 的图直接成为 runtime asset。
3. 运行时不需要 ImageGen、网络或外部账号。
4. 所有保存到 repo 的图片都有来源 brief、用途和 fallback 链接。
5. `content/assets/manifest.yaml` 是全量生产清单；planned 条目可以存在，但不能 runtime-enabled。
6. 82/82 个当前 MVP 资产条目都有候选图 QA 记录；只有 QA 通过并完成切帧/metadata/fallback 的条目才能进入运行时。
7. 完成口径按全量内容计算，不按 smoke 切片计算；Astia、Black Candle 或 Hex Seal 即使效果很好，也只能作为局部证据。

### Batch GFX-2：全量 SpriteAtlas 和 Timeline 数据结构

目标：建立全内容资产和动画语法，不接默认播放。

任务：

1. 新增 `SpriteAtlas`、`ActorSprite`、`EffectSprite`、`AnimationTimeline`。
2. 为 6 英雄、当前全部敌人、18 技能登记 metadata。
3. 每名英雄至少 1 个 signature timeline；每个技能至少 1 个 effect timeline；Boss/elite 敌人至少 1 个 telegraph/break timeline。
4. 为所有 bitmap 资产登记 Unicode fallback cell frame。
5. 单测检查帧数量、anchor、尺寸、keyframe delta、禁止 ASCII 小人主体。

验收：

1. 当前 content 中的英雄、敌人、技能资产覆盖率为 100%。
2. Hex Seal 等 signature timeline 至少 12 帧；非 signature 技能至少具备可播放的 6-8 帧 effect timeline。
3. 每帧能输出 actor pose、effect offset、duration、damage pop slot。
4. Unicode fallback 每帧宽高稳定。

### Batch GFX-3：RendererBackend Spike

目标：单独证明终端里能播放 sprite 舞台，不接 `ouro play`。

任务：

1. 实现 renderer 协议：`render_stage_frame()`、`begin()`、`present()`、`end()`。
2. 实现 Unicode cell renderer。
3. 实现 iTerm2 inline image writer。
4. 实现 Kitty writer，SIXEL 可先通过 chafa 或外部 capability 标记。
5. 写 `scripts/record_combat_stage.py --backend unicode/iterm2/kitty/auto`。

验收：

1. 可生成 filmstrip PNG/SVG 或日志证据。
2. 当前终端不支持 bitmap 时，脚本自动输出 Unicode 证据而不是失败。
3. renderer close 后光标、alternate screen、颜色状态恢复。

### Batch GFX-4：全量资产接入真实 play/run

目标：让真实战斗使用新舞台。接入顺序可以从 Astia/Hex Seal 开始，但完成口径必须覆盖当前所有英雄、敌人、技能、装备/词条/共鸣、场景和 UI 状态。

任务：

1. 从 `BattleFrame` 生成 `CombatStageModel`。
2. 先接入 Astia 的 Hex Seal 命中 Black Candle/Hungry Cultist 目标，用作冒烟播放切片。
3. 继续接入并打磨 Norn、Vela、Mirel、Korr、Sera 的 signature timeline；当前目标是每名英雄至少 12 beat。
4. 接入当前全部敌人的 idle/telegraph/hit/break/death。
5. 接入 18 个技能的 effect timeline；缺少 bitmap 的技能必须使用 Unicode cell fallback，不得退回普通文字箭头。
6. 接入 15 件物品、12 个 affix、5 个 resonance 的 icon/card/badge。
7. 接入 dungeon/node stage plate 和 UI 状态 sprite。
8. `--graphics auto` 在真实 TTY 播放 timeline。
9. `--no-animation` 输出同一 timeline 的压缩分镜。

验收：

1. 固定命令可看到 12 帧 Astia Hex Seal 动画，但该命令只算 smoke evidence。
2. 任意 MVP 英雄出战时都能看到该英雄的自有 actor sprite，而不是统一占位。
3. 当前全部敌人都有家族/tier 可识别的 sprite 或 fallback silhouette。
4. 18 个技能都有 effect timeline 或明确的 fallback timeline。
5. 15 件物品、12 个 affix、5 个 resonance 在 build/reward/shop/codex 相关界面有 icon/card/badge。
6. dungeon/node stage 和 UI 状态不是纯文字占位。
7. `BattleState`、伤害、状态、胜负、trace 不变。
8. Unicode fallback 和 bitmap path 的 frame semantics 一致。
9. 80/100/120 宽度不溢出。

### Batch GFX-5：证据、QA 和 release gate

目标：让“好不好看”有可复验材料。

任务：

1. 生成 bitmap 能力机器上的短录屏或 filmstrip。
2. 生成 Unicode fallback filmstrip。
3. 生成 `--no-animation` deterministic log。
4. README 放一张 evidence 图，但不夸大所有终端都能 bitmap。
5. release check 增加 graphics evidence gate。

验收：

1. 证据里能看出 windup、travel、hit stop、damage pop、settle。
2. no-animation 不含 ANSI live chrome。
3. 隐私扫描不包含本地密钥、真实 trace、个人路径泄漏。

### Batch GFX-6：未来内容扩展合同

目标：当前 MVP 全量完成后，保证后续内容不会重新变成无资产占位。

顺序：

1. 新英雄进入 content 前，必须先有 portrait、battle poses、signature timeline 和 fallback。
2. 新敌人进入 content 前，必须先有 family silhouette、tier variant、telegraph/hit/death 和 fallback。
3. 新技能进入 content 前，必须先有 effect timeline、damage/status pop 和 fallback。
4. 新 dungeon/node type 进入 content 前，必须先有 stage plate 或继承关系。

验收：

1. `validate-content` 能检查缺失资产或显式继承关系。
2. 新 content 没有对应资产时不能被标为 release-ready。
3. Boss 和普通怪在尺寸、节奏、命中重量上有区别。

---

## 8. 测试矩阵

P0 单测：

1. `test_graphics_capability_selects_iterm2_when_term_program_matches`
2. `test_graphics_capability_falls_back_under_ci_or_pipe`
3. `test_asset_manifest_covers_all_mvp_content`
4. `test_generated_assets_require_qa_before_runtime_use`
5. `test_sprite_atlas_all_heroes_enemies_and_skills_have_entries`
6. `test_sprite_atlas_astia_hex_seal_has_required_frames`
7. `test_timeline_frames_have_pose_or_effect_delta`
8. `test_unicode_cell_renderer_keeps_actor_columns_stable`
9. `test_no_animation_keeps_combat_storyboard_without_live_escape`

P0 集成：

1. `ouro doctor graphics`
2. `ouro play --mock --seed 2 --hero astia --graphics unicode --no-trace`
3. `ouro play --mock --seed 2 --hero hero_ash_guardian --graphics unicode --no-trace`
4. `ouro play --mock --seed 2 --hero hero_broken_string_hunter --graphics unicode --no-trace`
5. `ouro play --mock --seed 2 --hero astia --graphics ascii --no-animation --no-trace`
6. `scripts/record_combat_stage.py --backend auto --seed 2`

P1 人工证据：

1. iTerm2 bitmap screenshot 或 short recording。
2. Kitty bitmap screenshot 或 short recording。
3. Unicode fallback filmstrip。
4. no-animation log。

---

## 9. 风险和规避

| 风险 | 规避 |
|------|------|
| 终端支持不一致 | `auto` detection + explicit fallback + `doctor graphics` |
| 安装变重 | runtime 不强依赖 Pillow/Chafa/Notcurses；外部工具只做 optional evidence path |
| tmux 不透传图片 | 默认 Unicode，doctor 给出原因 |
| 录屏证据不可复现 | 同时保留 Unicode filmstrip 和 no-animation log |
| 美术资源过大 | 全量 manifest 覆盖，但 repo 只保留 QA 通过、压缩后、runtime 必需的资产 |
| 游戏规则被 renderer 污染 | renderer 只消费 `BattleFrame`，不写回 `RunState` |
| 又退回文字 HUD | 每帧验收 pose/effect/damage/HUD delta，限制解释文案行数 |
| 生图质量不稳定 | 候选图不直接进 runtime；必须通过 terminal-size QA、切帧、metadata 和 fallback 检查 |

---

## 10. 完成口径

`REQ-TUIMOTION-022` 和 graphics 批次完成时，应满足：

1. 支持 bitmap 的终端里，战斗舞台以真实 sprite/timeline 运动为主；Astia 的 Hex Seal 是 smoke evidence，但不是完成口径。
2. 当前 6 名英雄、全部 MVP 敌人、18 个技能、15 件物品、12 个 affix、5 个 resonance、`dungeon_ember_crypt`、当前 node type 和 UI 状态都有 bitmap 资产或明确的 QA 后 fallback。
3. 不支持 bitmap 的终端里，Unicode cell sprite 仍能看懂同一套动作。
4. ASCII/no-animation 仍能用于 CI、日志和低兼容试玩。
5. 玩家不用读长说明，也能从画面看出起手、施法、法印飞行、命中、打断和状态落定。
6. 所有完成的 REQ 都有测试、命令输出、截图/log 或人工试玩证据。

---

## 11. 新 Goal：全量资产覆盖的终端图形化 Ouro

把 Ouro Agent 从“ASCII 面板驱动的 CLI 肉鸽”升级为“terminal-native cinematic roguelike”。核心玩法保持不变：玩家配置一个英雄 Agent，战斗中模型只选择行动，本地引擎裁决伤害、状态、奖励和胜负；mock provider 永远离线可玩。

新的完成目标：

1. 全量资产覆盖：当前 6 英雄、全部 MVP 敌人、18 技能、15 物品、12 affix、5 resonance、Ember Crypt 场景/节点类型和 UI 状态全部进入 `AssetManifest`，后续新增 content 必须同步资产条目。
2. 开发期生图管线：ImageGen 只用于开发期候选资产生产；运行时只读取 repo 内 QA 通过的本地资产，不联网、不依赖外部账号、不读取未 QA 候选图。
3. 自有视觉语言：人物和怪物不再以 ASCII 线条小人为主体，而是使用 Ouro 自有 bitmap sprite / Unicode cell sprite / ASCII fallback 三层资产。
4. 连续动画：默认推荐体验像短 GIF 一样连续播放角色 pose、弹道、hit stop、伤害跳字、状态落定和 recovery，不用颜色、闪烁或文字标题冒充动效。
5. 全内容接入：任意 MVP 英雄、敌人、技能、构筑奖励、商店/休息/事件/Boss 场景都不能退回“只有文字说明”的旧体验。
6. 研发架构：renderer 只消费 `BattleFrame`/展示模型，不修改战斗规则；`--graphics auto` 选择 bitmap/Unicode/ASCII fallback；`--no-animation` 保留分镜和日志。
7. 证据门禁：每个完成的 REQ 必须有测试、manifest coverage、QA 记录、filmstrip/截图/log 或人工试玩证据；Astia/Hex Seal 只能作为 smoke evidence。

### 11.1 Goal 执行口径

当前 goal 不再是“做一个好看的 Astia/Hex Seal 案例”，而是：

1. 资产生产：基于 `content/assets/manifest.yaml` 的 82 个当前 MVP 资产条目，逐项生成 ImageGen 候选图、登记 QA 记录、完成切帧、压缩、metadata 和 fallback 映射。
2. 运行时接入：把 QA 通过的全量资产接入 `SpriteAtlas`、`AnimationTimeline` 和 renderer fallback chain；任意当前英雄、敌人、技能、装备/词条/共鸣、场景和 UI 状态都不能退回纯文字占位。
3. 演出升级：默认战斗画面以左英雄、右敌人、中心 effect lane 和连续 8-12fps timeline 为主体；颜色、闪烁、标题、rail、说明文字只能作为辅助。
4. 兼容兜底：bitmap 是最佳体验，Unicode cell sprite 是推荐 fallback，ASCII 是最低兼容；三者必须表达同一战斗事实。
5. 完成门禁：只有全量资产 coverage、QA 通过记录、运行时集成、宽度/无溢出测试、filmstrip/截图/log 证据和 release gate 都通过后，才能把图形化 goal 判定为完成。
