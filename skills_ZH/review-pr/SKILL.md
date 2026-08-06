---
name: review-pr
description: 使用知识图谱审查 PR 或分支 diff，获取完整结构化上下文。输出带影响半径分析的结构化审查。
argument-hint: "[PR 号或分支名]"
---

# 审查 PR

使用知识图谱对 pull request 或分支 diff 进行全面的代码审查。

**Token 优化：** 开始前，调用 `get_docs_section_tool(section_name="review-pr")` 获取优化工作流。除非被明确要求，绝不包含完整文件。

## 步骤

1. **识别 PR 的变更**：
   - 若提供了 PR 号或分支，使用 `git diff main...<branch>` 获取变更文件
   - 否则从当前分支相对 main/master 自动检测

2. **更新图谱**，调用 `build_or_update_graph_tool(base="main")` 确保图谱反映当前状态。

3. **获取完整审查上下文**，调用 `get_review_context_tool(base="main")`：
   - 以 `main`（或指定基线分支）作为 diff 基线
   - 返回 PR 中所有提交的所有变更文件

4. **分析影响**，调用 `get_impact_radius_tool(base="main")`：
   - 审查整个 PR 的影响半径
   - 识别高风险区域（被广泛依赖的代码）

5. **深入每个变更文件**：
   - 读取变更显著文件的完整源码
   - 对高风险函数使用 `query_graph_tool(pattern="callers_of", target=<函数>)`
   - 使用 `query_graph_tool(pattern="tests_for", target=<函数>)` 验证测试覆盖
   - 检查公共 API 的破坏性变更

6. **生成结构化审查输出**：

   ```
   ## PR 审查：<标题>

   ### 摘要
   <1-3 句概述>

   ### 风险评估
   - **总体风险**：低 / 中 / 高
   - **影响半径**：X 个文件、Y 个函数受影响
   - **测试覆盖**：N 个变更函数有覆盖 / 共 M 个

   ### 逐文件审查
   #### <文件路径>
   - 变更：<描述>
   - 影响：<谁依赖它>
   - 问题：<bug、风格、关切>

   ### 缺失测试
   - <函数名> 在 <文件> 中 - 未找到测试覆盖

   ### 建议
   1. <可操作建议>
   2. <可操作建议>
   ```

## 提示

- 大型 PR 优先关注影响最大的文件（依赖方最多）
- 使用 `semantic_search_nodes_tool` 查找 PR 可能遗漏的相关代码
- 检查重命名/移动的函数是否已更新所有调用者
