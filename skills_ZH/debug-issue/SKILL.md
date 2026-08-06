---
name: debug-issue
description: 使用图谱驱动的代码导航系统性调试问题
---

## 调试问题

使用知识图谱系统性追踪并调试问题。

### 步骤

1. 使用 `semantic_search_nodes_tool` 查找与问题相关的代码。
2. 使用 `query_graph_tool` 配合 `callers_of` 和 `callees_of` 追踪调用链。
3. 使用 `get_flow` 查看疑似区域的完整执行路径。
4. 运行 `detect_changes_tool` 检查近期变更是否导致了该问题。
5. 对疑似文件使用 `get_impact_radius_tool` 查看还有哪些受影响。

### 提示

- 同时检查调用者和被调用者以理解完整上下文。
- 查看受影响的执行流以找到触发 bug 的入口点。
- 近期变更是新问题最常见的来源。

## Token 效率规则
- 始终先调用 `get_minimal_context(task="<your task>")`，再使用其他图工具。
- 所有调用都使用 `detail_level="minimal"`。仅当 minimal 不够时才升级到 "standard"。
- 目标：在 ≤5 次工具调用、总计 ≤800 输出 token 内完成任何审查/调试/重构任务。
