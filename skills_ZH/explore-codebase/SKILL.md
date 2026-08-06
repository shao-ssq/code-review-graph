---
name: explore-codebase
description: 使用知识图谱导航并理解代码库结构
---

## 探索代码库

使用 code-review-graph 的 MCP 工具探索并理解代码库。

### 步骤

1. 运行 `list_graph_stats` 查看代码库整体指标。
2. 运行 `get_architecture_overview_tool` 获取高层社区结构。
3. 使用 `list_communities_tool` 找到主要模块，再用 `get_community` 查看详情。
4. 使用 `semantic_search_nodes_tool` 查找特定函数或类。
5. 使用 `query_graph_tool` 配合 `callers_of`、`callees_of`、`imports_of` 等 pattern 追踪关系。
6. 使用 `list_flows` 和 `get_flow` 理解执行路径。

### 提示

- 从宽到窄：先看统计与架构，再深入具体区域。
- 对文件使用 `children_of` 查看其全部函数和类。
- 使用 `find_large_functions` 识别复杂代码。

## Token 效率规则
- 始终先调用 `get_minimal_context(task="<your task>")`，再使用其他图工具。
- 所有调用都使用 `detail_level="minimal"`。仅当 minimal 不够时才升级到 "standard"。
- 目标：在 ≤5 次工具调用、总计 ≤800 输出 token 内完成任何审查/调试/重构任务。
