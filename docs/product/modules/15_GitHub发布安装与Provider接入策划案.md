# G15 GitHub 发布、安装与 Provider 接入策划案

> 状态：v0.1 草案  
> 依赖：G05、G08、G09、G14  
> 目的：让 Ouro Agent 从一开始按“可上传 GitHub、玩家可命令行安装、可配置模型 Provider”的产品形态设计。

---

## 1. 模块目标

MVP 不是只能在开发者机器上跑的脚本。目标是：

1. 上传 GitHub 后，玩家能按 README 安装。
2. 无 API key 时能用 mock mode 试玩。
3. 玩家能通过命令行配置 API key 环境变量、base URL 和模型。
4. 支持 OpenAI、Anthropic 和 OpenAI-compatible Provider。
5. 不明文保存 API key。

---

## 2. 推荐发布形态

技术栈最终仍需审批，但策划推荐：

| 项 | 推荐 |
|----|------|
| 语言 | Python |
| 安装 | `pipx install git+https://github.com/<owner>/ouro-agent.git` |
| 后续正式发布 | PyPI 包：`pipx install ouro-agent` |
| CLI 命令 | `ouro` 或 `ouro-agent` |
| TUI 库 | Rich / Textual 二选一，先 Rich 后 Textual |
| 配置目录 | 用户目录下的 Ouro Agent 配置目录 |
| 默认模式 | mock provider |

选择 Python 的理由：跨平台、CLI/TUI 生态成熟、测试和内容数据处理简单、玩家可用 pipx 从 GitHub 安装。

---

## 3. 玩家安装体验

README 目标流程：

```bash
pipx install git+https://github.com/<owner>/ouro-agent.git
ouro --version
ouro play --mock
```

真实模型配置示例：

```bash
setx OPENAI_API_KEY "sk-..."
ouro config set provider openai
ouro config set model gpt-5.4
ouro play
```

Anthropic 示例：

```bash
setx ANTHROPIC_API_KEY "sk-ant-..."
ouro config set provider anthropic
ouro config set model claude-sonnet-4-5
ouro play
```

OpenAI-compatible 示例：

```bash
setx OURO_API_KEY "..."
ouro config set provider openai-compatible
ouro config set api_key_env OURO_API_KEY
ouro config set base_url https://example.com/v1
ouro config set model your-model-name
ouro play
```

具体模型名不应写死为唯一选择；README 可以给默认推荐，但配置系统必须允许玩家改。

---

## 4. Provider 类型

| Provider | 接入方式 | 配置字段 |
|----------|----------|----------|
| `mock` | 本地模拟，不联网 | `model=mock-smart` |
| `openai` | OpenAI 官方 API | `api_key_env`, `model`, 可选 `base_url` |
| `anthropic` | Anthropic Messages API | `api_key_env`, `model`, 可选 `base_url` |
| `openai-compatible` | 兼容 OpenAI Chat/Responses 风格的第三方端点 | `api_key_env`, `base_url`, `model` |

Provider Adapter 输出统一为游戏内部的 `ModelTurnResult`，不能让上层战斗系统关心具体 Provider。

---

## 5. 配置字段

| 字段 | 必需 | 说明 |
|------|------|------|
| `provider` | 是 | mock/openai/anthropic/openai-compatible |
| `model` | 是 | 玩家选择的模型 |
| `api_key_env` | 否 | 环境变量名，默认按 provider 推断 |
| `base_url` | 否 | 自定义 API 地址 |
| `api_version` | 否 | Provider 需要版本头时使用，例如 Anthropic |
| `timeout_seconds` | 是 | 模型调用超时 |
| `max_retries` | 是 | 重试次数 |
| `trace_level` | 是 | trace 记录级别 |
| `unicode_mode` | 是 | 是否使用 Unicode 增强界面 |

默认环境变量：

| Provider | 默认环境变量 |
|----------|--------------|
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI-compatible | `OURO_API_KEY` |

---

## 6. API 设计边界

必须遵守：

1. API key 不写入普通配置文件。
2. 默认不上传 trace。
3. Provider 错误要给玩家可读提示。
4. 网络失败不能破坏存档。
5. mock mode 必须永远可用。
6. Provider Adapter 必须能被 mock 测试替换。

OpenAI 和 Anthropic 官方 API 形态会更新，因此实现时应先看官方文档：

| Provider | 官方文档 |
|----------|----------|
| OpenAI | `https://platform.openai.com/docs/api-reference/responses/create?api-mode=responses`、`https://platform.openai.com/docs/api-reference/authentication?api-mode=responses` |
| Anthropic | `https://docs.anthropic.com/en/api/messages-examples`、`https://docs.anthropic.com/en/api/messages` |

---

## 7. GitHub 仓库最低要求

可上传 GitHub 的最低仓库内容：

1. `README.md`：安装、mock 试玩、Provider 配置、隐私说明。
2. `AGENTS.md`：AI 协作规则。
3. `LICENSE`：开源许可证，待 RicHe 决定。
4. `pyproject.toml` 或等价包配置。
5. `src/`：代码。
6. `tests/`：测试。
7. `content/`：结构化内容数据。
8. `examples/`：示例配置和 trace。
9. `.gitignore`：排除本地配置、trace、缓存。

---

## 8. CLI 命令规划

| 命令 | 作用 |
|------|------|
| `ouro play` | 开始游戏 |
| `ouro play --mock` | 使用 mock provider 试玩 |
| `ouro config show` | 显示配置，不显示 key 明文 |
| `ouro config set provider <name>` | 设置 Provider |
| `ouro config set model <model>` | 设置模型 |
| `ouro config set base_url <url>` | 设置 API URL |
| `ouro doctor` | 检查安装、配置、Provider 连通性 |
| `ouro validate-content` | 校验内容数据 |
| `ouro replay <trace>` | 后续预留，重放 trace |

---

## 9. 验收标准

1. 从 GitHub 安装后能运行 `ouro --version`。
2. 无 API key 时 `ouro play --mock` 可完成一场战斗。
3. `ouro config show` 不显示 key 明文。
4. OpenAI / Anthropic / OpenAI-compatible 至少在配置层可选择。
5. Provider 错误显示为可读提示。
6. README 能让玩家完成安装和 mock 试玩。
