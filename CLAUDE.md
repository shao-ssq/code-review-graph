# 通用规则

1，不要主动运行代码，我会自己手动运行。
2，遇到英文描述，尝试翻译成中文替换原本内容。


# CLAUDE.md - Claude Code 项目上下文

## 项目概述

**code-review-graph** 是一个持久化、增量更新、本地优先的知识图谱，面向通过 MCP 与 CLI 进行省 token 代码审查的场景。它使用 Tree-sitter 和有针对性的回退解析器解析代码库，在 SQLite 中构建结构化图谱，并向 AI 编码工具（包括 Claude Code、Codex、Cursor、Windsurf、Zed、Continue、OpenCode、Gemini CLI、Qwen、Kiro、Qoder 和 GitHub Copilot）暴露紧凑的上下文。

## 图工具使用（省 token）
使用 code-review-graph 的 MCP 工具时，遵循以下规则：
1. 首次调用：`get_minimal_context(task="<描述>")` —— 约耗 100 tokens，给你全局视图。
2. 后续所有调用：除非确需更多信息，一律使用 `detail_level="minimal"`。
3. 优先用 `query_graph_tool` 指定具体 target，而非宽泛的 `list_*` 调用。
4. 每个响应里的 `next_tool_suggestions` 字段会告诉你下一步最优动作。
5. 目标：每个任务 ≤5 次工具调用，图上下文总量 ≤800 tokens。

## 架构

- **核心包**：`code_review_graph/`（Python 3.10+）
  - `parser.py` —— 基于 Tree-sitter 的多语言 AST 解析器，并配有针对性回退解析，以支持广泛的源语言与笔记本
  - `custom_languages.py` —— 配置驱动的自定义语言支持（`.code-review-graph/languages.toml`，见 docs/CUSTOM_LANGUAGES.md）
  - `graph.py` —— 基于 SQLite 的图存储（节点、边、加权评分的影响分析）
  - `tools/` —— 按领域拆分的 30 个 MCP 工具实现
  - `main.py` —— FastMCP 服务器入口，注册 30 个工具 + 5 个 prompt
  - `incremental.py` —— 基于 git 的变更检测、文件监听
  - `embeddings.py` —— 可选的向量嵌入（本地 sentence-transformers、OpenAI 兼容端点、Google Gemini、MiniMax）
  - `visualization.py` —— D3.js 交互式 HTML 图生成器
  - `cli.py` —— CLI 入口（install/init、build、update、postprocess、embed、watch、status、visualize、serve/mcp、wiki、detect-changes、register、unregister、repos、eval、daemon）
  - `flows.py` —— 执行流检测与关键度评分
  - `communities.py` —— 社区检测（Leiden 算法或按文件分组）与架构概览
  - `search.py` —— FTS5 混合搜索（关键词 + 向量）
  - `changes.py` —— 带风险评分的变更影响分析（detect-changes）
  - `refactor.py` —— 重命名预览、死代码检测、重构建议
  - `hints.py` —— 审查提示生成
  - `prompts.py` —— 5 个 MCP prompt 模板（review_changes、architecture_map、debug_issue、onboard_developer、pre_merge_check）
  - `wiki.py` —— 从社区结构生成 Markdown wiki
  - `skills.py` —— 多平台安装/配置生成与随包技能元数据
  - `registry.py` —— 多仓库注册表辅助函数
  - `migrations.py` —— 数据库 schema 迁移（v1-v9）
  - `tsconfig_resolver.py` —— TypeScript 路径别名解析

- **VS Code 扩展**：`code-review-graph-vscode/`（TypeScript）
  - 独立子项目，有自己的 `package.json`、`tsconfig.json`
  - 通过 SQLite 读取 `.code-review-graph/graph.db`

- **数据库**：`.code-review-graph/graph.db`（SQLite，WAL 模式）

## 关键命令

```bash
# 开发
uv run ruff check code_review_graph/        # Lint
uv run mypy code_review_graph/ --ignore-missing-imports --no-strict-optional

# 构建与测试
uv run code-review-graph build              # 全量构建图
uv run code-review-graph update             # 增量更新
uv run code-review-graph status             # 查看统计
uv run code-review-graph serve              # 启动 MCP 服务器
uv run code-review-graph wiki               # 生成 markdown wiki
uv run code-review-graph detect-changes     # 带风险评分的变更分析
uv run code-review-graph register <path>    # 将仓库注册到多仓库注册表
uv run code-review-graph repos              # 列出已注册仓库
uv run code-review-graph eval               # 运行评估基准
```

## 代码规范

- **行长**：100 字符（ruff）
- **Python 目标**：3.10+
- **SQL**：一律使用参数化查询（`?` 占位符），绝不把值拼进 f-string
- **错误处理**：捕获具体异常，用 `logger.warning/error` 记录
- **线程安全**：共享缓存用 `threading.Lock`，SQLite 用 `check_same_thread=False`
- **节点名**：返回给 MCP 客户端前一律经 `_sanitize_name()` 处理
- **文件读取**：读一次字节、哈希、再解析（TOCTOU 安全模式）

## 安全不变量

- 禁用 `eval()`、`exec()`、`pickle`、`yaml.unsafe_load()`
- 子进程调用禁用 `shell=True`
- `_validate_repo_root()` 防止通过 repo_root 参数进行路径穿越
- `_sanitize_name()` 剥离控制字符，上限 256 字符（防 prompt 注入）
- 可视化中的 `escH()` 转义 HTML 实体，包括引号与反引号
- D3.js CDN script 标签带 SRI 哈希
- API key 只从环境变量读取，绝不硬编码

## CI 流水线

- **lint**：Python 3.10 上跑 ruff
- **type-check**：mypy
- **security**：bandit 扫描


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads 问题跟踪

本项目使用 **bd（beads）** 进行问题跟踪。运行 `bd prime` 查看完整工作流上下文与命令。

### 快速参考

```bash
bd ready              # 查找可用工作
bd show <id>          # 查看问题详情
bd update <id> --claim  # 认领工作
bd close <id>         # 完成工作
```

### 规则

- 所有任务跟踪一律使用 `bd`——不要使用 TodoWrite、TaskCreate 或 markdown TODO 列表
- 运行 `bd prime` 获取详细命令参考与会话收尾协议
- 使用 `bd remember` 持久化知识——不要使用 MEMORY.md 文件

## 会话收尾

**结束工作会话时**，你必须完成以下全部步骤。`git push` 成功之前，工作都不算完成。

**强制工作流：**

1. **为剩余工作建档** —— 为任何需要后续跟进的事项创建 issue
2. **运行质量门禁**（若有代码变更）—— 测试、lint、构建
3. **更新问题状态** —— 关闭已完成项，更新进行中的项
4. **推送到远端** —— 这是强制的：
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # 必须显示 "up to date with origin"
   ```
5. **清理** —— 清空 stash，修剪远端分支
6. **验证** —— 所有变更已提交且已推送
7. **交接** —— 为下一个会话提供上下文

**关键规则：**
- `git push` 成功之前，工作都不算完成
- 绝不在推送前停下——那会让工作滞留在本地
- 绝不说"随时可以推送"——推送是你必须完成的动作
- 若推送失败，解决后重试，直到成功
<!-- END BEADS INTEGRATION -->

<!-- code-review-graph MCP 工具 -->
## MCP 工具：code-review-graph

**重要：本项目带有知识图谱。在探索代码库时，务必先使用
code-review-graph 的 MCP 工具，再考虑 Grep/Glob/Read。**
图更快、更省 token，并且能提供文件扫描无法给出的结构性上下文
（调用者、依赖方、测试覆盖等）。

### 何时优先使用图工具

- **探索代码**：用 `semantic_search_nodes_tool` 或 `query_graph_tool`，而非 Grep
- **理解影响面**：用 `get_impact_radius_tool`，而非手动追踪 import
- **代码审查**：用 `detect_changes_tool` + `get_review_context_tool`，而非读取整个文件
- **查找关系**：用 `query_graph_tool` 配合 callers_of / callees_of / imports_of / tests_for
- **架构问题**：用 `get_architecture_overview_tool` + `list_communities_tool`

仅当图无法覆盖你的需求时，才回退到 Grep/Glob/Read。

### 关键工具

| 工具 | 适用场景 |
|------|----------|
| `detect_changes_tool` | 审查代码变更——给出带风险评分的分析 |
| `get_review_context_tool` | 审查时需要源码片段——省 token |
| `get_impact_radius_tool` | 理解某次变更的影响半径 |
| `get_affected_flows_tool` | 查找受影响的执行路径 |
| `query_graph_tool` | 追踪调用者、被调用者、import、测试、依赖 |
| `semantic_search_nodes_tool` | 按名称或关键字查找函数/类 |
| `get_architecture_overview_tool` | 理解代码库的高层结构 |
| `refactor_tool` | 规划重命名、查找死代码 |

### 工作流

1. 图会在文件变更时自动更新（通过钩子）。
2. 代码审查时使用 `detect_changes_tool`。
3. 用 `get_affected_flows_tool` 理解影响面。
4. 用 `query_graph_tool` 的 pattern="tests_for" 检查测试覆盖。

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes_tool` or `query_graph_tool` instead of Grep
- **Understanding impact**: `get_impact_radius_tool` instead of manually tracing imports
- **Code review**: `detect_changes_tool` + `get_review_context_tool` instead of reading entire files
- **Finding relationships**: `query_graph_tool` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview_tool` + `list_communities_tool`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
| ------ | ---------- |
| `detect_changes_tool` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context_tool` | Need source snippets for review — token-efficient |
| `get_impact_radius_tool` | Understanding blast radius of a change |
| `get_affected_flows_tool` | Finding which execution paths are impacted |
| `query_graph_tool` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes_tool` | Finding functions/classes by name or keyword |
| `get_architecture_overview_tool` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes_tool` for code review.
3. Use `get_affected_flows_tool` to understand impact.
4. Use `query_graph_tool` pattern="tests_for" to check coverage.
