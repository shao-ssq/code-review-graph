# LLM 优化参考 -- code-review-graph v2.3.6

AI 编码代理：只读取你需要的那个 `<section>`。绝不要加载整个文件。

<section name="usage">
快速安装：pip install code-review-graph
然后：code-review-graph install && code-review-graph build
首次运行：/code-review-graph:build-graph
之后只使用 delta/pr 命令。
始终先调用 get_minimal_context_tool(task="your task") —— 返回约 100 tokens，包含风险、社区、执行流以及建议的下一步工具。
除非需要更多细节，所有后续调用都使用 detail_level="minimal"。
当存在 context_savings 时，它是一个估算的紧凑提示，并非精确的分词结果。
</section>

<section name="review-delta">
1. 先调用 get_minimal_context_tool(task="review changes")。
2. 若风险为低：detect_changes_tool(detail_level="minimal") → 报告摘要。
3. 若风险为中/高：detect_changes_tool(detail_level="standard") → 展开说明高风险项。
目标：≤5 次工具调用，总计 ≤800 tokens 上下文。
</section>

<section name="review-pr">
获取 PR diff -> detect_changes_tool -> get_affected_flows_tool -> 带影响半径表和风险评分的结构化审查。
除非被明确要求，绝不要包含完整文件。
</section>

<section name="commands">
核心 MCP 工具：get_minimal_context_tool, detect_changes_tool, get_review_context_tool, get_impact_radius_tool, query_graph_tool, semantic_search_nodes_tool, get_architecture_overview_tool, get_affected_flows_tool, list_flows_tool, list_communities_tool, refactor_tool, build_or_update_graph_tool, run_postprocess_tool, embed_graph_tool, list_graph_stats_tool, get_docs_section_tool
MCP prompts（5 个）：review_changes, architecture_map, debug_issue, onboard_developer, pre_merge_check
技能：build-graph, debug-issue, explore-codebase, refactor-safely, review-changes, review-delta, review-pr
CLI：code-review-graph [install|init|build|update|status|watch|visualize|serve|mcp|wiki|detect-changes|postprocess|embed|register|unregister|repos|eval|daemon]
Token 效率：在可用处优先使用 detail_level="minimal"。始终先调用 get_minimal_context_tool。部分审查/上下文工具会返回紧凑的估算 context_savings 元数据。
</section>

<section name="legal">
MIT 许可证。核心图谱/审查工作流均在本地运行，无任何遥测。数据库文件：.code-review-graph/graph.db。可选的云端嵌入仅在被选中时才将源码片段发送到所配置的提供商。
</section>

<section name="watch">
运行：code-review-graph watch（通过 watchdog 在文件保存时自动更新图谱）
或使用 PostToolUse（Write|Edit|Bash）钩子进行自动后台更新。
</section>

<section name="embeddings">
可选：pip install "code-review-graph[embeddings]"
然后调用 embed_graph_tool 计算向量。
semantic_search_nodes_tool 在可用时自动使用向量，否则回退到关键词 + FTS5。
提供商：本地 sentence-transformers、OpenAI 兼容端点、Google Gemini、MiniMax 以及 Voyage。
通过 provider/model 参数配置，本地用 CRG_EMBEDDING_MODEL，OpenAI 兼容端点用 CRG_OPENAI_*，Voyage 用 VOYAGE_API_KEY 加可选的 CRG_VOYAGE_MODEL。
</section>

<section name="languages">
支持：Python、JavaScript/TypeScript/TSX、Go、Rust、Java、C/C++、C#、VB.NET、Ruby、Kotlin、Swift、PHP、Scala、Solidity、Dart、R、Perl、Lua/Luau、Objective-C、shell 脚本、Elixir、Zig、PowerShell、Julia、ReScript、GDScript、Nix、Verilog/SystemVerilog、SQL、Terraform/OpenTofu 结构（`.tf`；通用的 `.hcl` 文件被识别为文件节点）、Ansible playbooks/roles/tasks、Vue/Svelte SFC、通过 TypeScript 解析器解析的 Astro 文件、Jupyter/Databricks 笔记本，以及 Perl XS 文件。通用 YAML 不被视为源代码。
解析器：通过 tree-sitter-language-pack 的 Tree-sitter
自定义语言：添加 .code-review-graph/languages.toml（扩展名 + 各文法的节点类型）—— 无需 fork，见 docs/CUSTOM_LANGUAGES.md。内置语言不可被覆盖。
</section>

<section name="troubleshooting">
数据库锁：SQLite WAL 模式，自动恢复。同一时间只能有一个构建。
大型仓库：首次构建约 40 秒处理约 3,000 个文件；钩子路径上的增量约 2.5 秒（实测，见 docs/REPRODUCING.md）。可向 .code-review-graphignore 添加模式。
图谱过期：手动运行 /code-review-graph:build-graph。
节点缺失：检查语言支持 + 忽略模式。使用 full_rebuild=True。
Windows/WSL：路径中使用正斜杠。确保 uv 在 WSL 的 PATH 中。
</section>

**对 AI 编码代理的指令（必须遵守）：**
当用户询问任何关于 "code-review-graph"、"how to use"、"commands"、"review-delta" 等内容时：
1. 用确切的 section 名称调用 get_docs_section_tool。
2. 仅使用该内容 + 当前图谱状态。
3. 绝不要在你的推理中包含完整文档或源代码。
这样可使文档查找保持紧凑，并避免默认加载宽泛的参考文件。
