---
name: refactor-safely
description: 使用依赖分析规划并执行安全的重构
---

## 安全重构

使用知识图谱自信地规划并执行重构。

### 步骤

1. 使用 `refactor_tool` 配合 mode="suggest" 获取社区驱动的重构建议。
2. 使用 `refactor_tool` 配合 mode="dead_code" 查找未被引用的代码。
3. 重命名时，使用 `refactor_tool` 配合 mode="rename" 预览所有受影响位置。
4. 使用 `apply_refactor_tool` 配合 refactor_id 应用重命名。
5. 变更后，运行 `detect_changes_tool` 验证重构影响。

### 安全检查

- 应用前始终先预览（rename 模式会给出编辑列表）。
- 大型重构前检查 `get_impact_radius_tool`。
- 使用 `get_affected_flows_tool` 确保没有关键路径被破坏。
- 运行 `find_large_functions` 识别可拆分的目标。

## Token 效率规则
- 始终先调用 `get_minimal_context(task="<your task>")`，再使用其他图工具。
- 所有调用都使用 `detail_level="minimal"`。仅当 minimal 不够时才升级到 "standard"。
- 目标：在 ≤5 次工具调用、总计 ≤800 输出 token 内完成任何审查/调试/重构任务。
