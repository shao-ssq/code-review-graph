# Code Review Graph —— 用户指南

## 安装

```bash
pip install code-review-graph
code-review-graph install    # 自动检测并配置所有支持的平台
code-review-graph build      # 解析你的代码库
```

`install` 会检测你安装了哪些 AI 编码工具，为每个工具写入正确的 MCP 配置，并在支持的平台上安装原生 Hook。安装完成后请重启编辑器/工具。

若要针对特定平台而非自动检测所有平台：

```bash
code-review-graph install --platform codex
code-review-graph install --platform cursor
code-review-graph install --platform claude-code
code-review-graph install --platform codebuddy
```

### 支持的平台

| 平台 | 配置文件 |
|------|----------|
| **Codex** | `~/.codex/config.toml` + `~/.codex/hooks.json` |
| **Claude Code** | `.mcp.json` + `.claude/settings.json` |
| **CodeBuddy Code** | `.mcp.json` + `CODEBUDDY.md` + `.codebuddy/settings.json` + `.codebuddy/skills/<name>/SKILL.md` |
| **Cursor** | `.cursor/mcp.json` |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` |
| **Zed** | `~/Library/Application Support/Zed/settings.json`（macOS）或 `~/.config/zed/settings.json` |
| **Continue** | `~/.continue/config.json` |
| **OpenCode** | `opencode.jsonc`（优先）或 `opencode.json` |
| **Antigravity** | `~/.gemini/antigravity/mcp_config.json` |
| **Gemini CLI** | `.gemini/settings.json` |
| **Qwen Code** | `~/.qwen/settings.json` |
| **Kiro** | `.kiro/settings/mcp.json` |
| **Qoder** | `.qoder/mcp.json` |
| **GitHub Copilot** | `.vscode/mcp.json` |
| **GitHub Copilot CLI** | `~/.copilot/mcp-config.json` |

## 核心工作流

### 1. 构建图（仅首次）
```
/code-review-graph:build-graph
```
解析整个代码库。500 个文件约需 10 秒。

### 2. 审查变更（日常使用）
```
/code-review-graph:review-delta
```
仅审查自上次提交以来变更的文件，以及图谱推导出的影响半径。相关审查和影响响应包含紧凑的 `context_savings` 估算元数据。在 6 个基准仓库中，图谱查询每个问题使用的 Token 比读取整个语料库少约 65 倍（中位数；范围 36x–376x）——参见 [README 基准测试](../README.md#benchmarks) 和 [REPRODUCING.md](REPRODUCING.md) 了解方法论。

### 3. 审查 PR
```
/code-review-graph:review-pr
```
对分支差异进行全面的结构化审查，含影响半径分析。

### 4. 监听模式（可选）
```bash
code-review-graph watch
```
在每次文件保存时自动更新图谱。无需任何手动操作。

### 5. 可视化图谱（可选）
```bash
code-review-graph visualize
open .code-review-graph/graph.html
```
交互式 D3.js 力导向图。初始状态为折叠（仅显示 File 节点）——点击文件展开其子节点。使用搜索栏过滤，点击图例中的边类型可切换可见性。

### 6. 语义搜索（可选）
```bash
pip install "code-review-graph[embeddings]"
```
然后使用 `embed_graph_tool` 计算向量。`semantic_search_nodes_tool` 在有匹配嵌入时自动使用向量相似度，否则回退到关键词/FTS 搜索。

嵌入提供方包括：本地 sentence-transformers、OpenAI 兼容端点、Google Gemini、MiniMax 和 Voyage。本地嵌入使用 `CRG_EMBEDDING_MODEL`；OpenAI 兼容提供方使用 `CRG_OPENAI_BASE_URL`、`CRG_OPENAI_API_KEY` 和 `CRG_OPENAI_MODEL`；Voyage 使用 `VOYAGE_API_KEY` 和可选的 `CRG_VOYAGE_MODEL`。云端提供方需显式选择，且除非设置 `CRG_ACCEPT_CLOUD_EMBEDDINGS=1`，否则会打印出境警告。

函数/类文档摘要已包含在嵌入文本中。对于旧版本创建的图谱，在重新嵌入之前请先执行一次全量构建，以确保所有文件都获得该元数据。嵌入刷新在 build/update/watch 之后始终默认关闭；需显式指定提供方和模型来开启，例如：

```bash
code-review-graph build \
  --embedding-provider local \
  --embedding-model all-MiniLM-L6-v2
```

这两个选项同样适用于 `update`、`postprocess` 和 `watch`，必须同时提供。刷新操作只会更新先前已嵌入的图谱，拒绝将向量迁移到不同的提供方/模型/端点，清除已删除节点的向量，并将提供方或传输失败降级为图构建警告。

### 7. 带风险评分的变更检测（v2）
```
向 MCP 客户端询问："使用风险评分审查我的近期变更"
```
使用 `detect_changes_tool` 将差异映射到受影响的函数、流程、社区和测试缺口。

### 8. 探索架构（v2）
```
向 MCP 客户端询问："展示这个项目的架构"
```
使用 `get_architecture_overview_tool` 生成基于社区的架构图，并显示耦合警告。

### 9. 生成 Wiki（v2）
```bash
code-review-graph wiki
```
为每个检测到的社区在 `.code-review-graph/wiki/` 中创建 Markdown wiki 页面。

### 10. 多仓库搜索（v2）
```bash
code-review-graph register /path/to/other/repo --alias mylib
```
然后使用 `cross_repo_search_tool` 跨所有已注册仓库进行搜索。

## 上下文节省

CRG 通过发送图谱推导的结构化上下文而非大量文件内容来减少审查上下文。具体节省量取决于仓库和变更形态。评估运行器报告 README 中使用的当前基准数据：

```bash
code-review-graph eval --all
```

自 v2.3.4 起，审查和影响工具包含紧凑的 `context_savings` 元数据。在 v2.3.5 中，CLI 在 `detect-changes --brief` 和 `update --brief` 上都以框式 `Token Savings` 面板呈现，包含按类别细分（Functions / Tests / Risk / Other），总和恰好等于图响应大小。添加 `--verify` 可使用 OpenAI 的 `cl100k_base` 分词器（要求 `pip install tiktoken`）交叉验证显示的数字。所有数字标注为"估算"，因为使用的是保守近似而非模型特定分词；校准显示该估算在聚合层面与真实 GPT-4 Token 数的误差在约 1% 以内。单文件的小改动偶尔可能使用比原始文件更多的上下文，因为图谱元数据本身也有开销。

## 支持的语言

解析器目前支持：Python、JavaScript、TypeScript/TSX、Go、Rust、Java、C/C++、C#、VB.NET、Ruby、Kotlin、Swift、PHP、Scala、Solidity、Dart、R、Perl、Lua/Luau、Objective-C、Shell 脚本、Elixir、Zig、PowerShell、Julia、ReScript、GDScript、Nix、Verilog/SystemVerilog、SQL、Vue/Svelte 单文件组件、通过 TypeScript 解析器处理的 Astro 文件、Jupyter/Databricks 笔记本（`.ipynb`）以及 Perl XS 文件（`.xs`）。

无扩展名的脚本通过 shebang 检测，支持常见的 bash/sh/zsh/ksh/dash/ash、Python、Node、Ruby、Perl、Lua、Rscript 和 PHP 解释器。

尚未覆盖的语言可通过 `.code-review-graph/languages.toml` 配置无需 Fork 地添加——参见 [CUSTOM_LANGUAGES.md](CUSTOM_LANGUAGES.md)。

## 索引内容

- **节点**：Files、Classes、Functions/Methods、Types、Tests——以及框架增强适用时的 Endpoints、Schedulers 和 ConfigProperties
- **边**：CALLS、IMPORTS_FROM、INHERITS、IMPLEMENTS、CONTAINS、TESTED_BY、DEPENDS_ON、REFERENCES——以及框架特定类型（INJECTS、HANDLES、TRIGGERS、PUBLISHES、CONSUMES/PRODUCES、DEPENDS_ON_CONFIG、TEMPORAL_STUB）

完整详情参见 [schema.md](schema.md)。

## 忽略模式

默认情况下，以下路径被排除在索引之外：

```
.code-review-graph/**    node_modules/**    .git/**
__pycache__/**           *.pyc              .venv/**
venv/**                  dist/**            build/**
.next/**                 target/**          *.min.js
*.min.css                *.map              *.lock
package-lock.json        yarn.lock          *.db
*.sqlite                 *.db-journal
```

要添加自定义模式，在仓库根目录创建 `.code-review-graphignore` 文件（语法与 `.gitignore` 相同）：

```
generated/**
vendor/**
*.generated.ts
```

在 git 仓库中，索引基于已追踪文件（`git ls-files`），因此被 gitignore 的文件会自动跳过。当 git 不可用或需要排除已追踪文件时，使用 `.code-review-graphignore`。
