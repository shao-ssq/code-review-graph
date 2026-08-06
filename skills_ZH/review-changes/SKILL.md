---
name: review-changes
description: 使用变更检测与影响分析执行结构化代码审查
---

## 审查变更

使用知识图谱进行彻底的、风险感知的代码审查。

### 步骤

1. 运行 `detect_changes_tool` 获取带风险评分的变更分析。
2. 运行 `get_affected_flows_tool` 查找受影响的执行路径。
3. 对每个高风险函数，运行 `query_graph_tool` 配合 pattern="tests_for" 检查测试覆盖。
4. 运行 `get_impact_radius_tool` 理解影响半径。
5. 对任何未测试的变更，建议具体的测试用例。

### 输出格式

按风险级别（高/中/低）分组提供发现，包含：
- 变更内容及为何重要
- 测试覆盖状态
- 建议的改进
- 总体合并建议

## Token 效率规则
- 始终先调用 `get_minimal_context(task="<your task>")`，再使用其他图工具。
- 所有调用都使用 `detail_level="minimal"`。仅当 minimal 不够时才升级到 "standard"。
- 目标：在 ≤5 次工具调用、总计 ≤800 输出 token 内完成任何审查/调试/重构任务。
