---
name: build-graph
description: 构建或更新代码审查知识图谱。首次使用时运行以初始化，或由钩子自动保持更新。
argument-hint: "[full]"
---

# 构建图谱

为本仓库构建或增量更新持久化的代码知识图谱。

## 步骤

1. **检查图谱状态**，调用 `list_graph_stats_tool` MCP 工具。
   - 若图谱从未构建（last_updated 为 null），执行全量构建。
   - 若图谱已存在，执行增量更新。

2. **构建图谱**，调用 `build_or_update_graph_tool` MCP 工具：
   - 首次设置：`build_or_update_graph_tool(full_rebuild=True)`
   - 更新：`build_or_update_graph_tool()`（默认增量）

3. **验证**，再次调用 `list_graph_stats_tool` 并报告结果：
   - 解析的文件数
   - 创建的节点数与边数
   - 检测到的语言
   - 遇到的任何错误

## 何时使用

- 首次为仓库设置图谱
- 大型重构或切换分支之后
- 图谱显得过期或不同步时
- 图谱会在编辑/提交时通过钩子自动更新，因此手动构建很少需要

## 说明

- 图谱以 SQLite 数据库形式存储在仓库根目录（`.code-review-graph/graph.db`）
- 二进制文件、生成文件以及 `.code-review-graphignore` 中的模式会被跳过
- 支持的语言：Python、TypeScript/JavaScript、Vue、Go、Rust、Java、Scala、C#、Ruby、Kotlin、Swift、PHP、Solidity、C/C++
