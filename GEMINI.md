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
