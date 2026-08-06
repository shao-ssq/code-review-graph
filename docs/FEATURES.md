# 功能特性

## v2.3.6（当前版本）
- **框架感知 PHP 解析**：traits、枚举、对象创建和基类子句已被索引；Composer PSR-4 解析采用最长前缀匹配、多目录、带缓存且有仓库边界；Blade 引用忽略注释/转义指令；Laravel Route 和 Eloquent 边需要明确的框架/导入/接收者证据。
- **无需 fork 的自定义语言**：在仓库中放入 `.code-review-graph/languages.toml` 即可索引 tree-sitter-language-pack 附带的任何语法——扩展名映射加节点类型列表，经过验证和上限控制，内置语言始终优先。参见 [CUSTOM_LANGUAGES.md](CUSTOM_LANGUAGES.md)。
- **带风险评分的 PR 审查 GitHub Action**：复合 `action.yml` 从 CI 缓存构建/恢复图谱，对 PR 基准运行 `detect-changes`，并追加带风险表格、受影响流程、测试缺口和 Token 节省行的置顶评论。可选 `fail-on-risk` 合并门禁。通过 `.github/workflows/pr-review.yml` 在本仓库自我使用（dogfood）。参见 [GITHUB_ACTION.md](GITHUB_ACTION.md)。
- **`agent_baseline` 评估基准**：将图谱查询与真实的 grep + 读取 Top-K 代理基线进行比较，而非使用全语料库稻草人；已接入全部六个固定评估配置。
- **`impact_accuracy` 的共变更真值**：预测也会针对同一提交中实际共同变更的文件进行评分；遗留指标明确标记为"图谱派生（循环——上界）"。
- **每周评估 CI**：`.github/workflows/eval.yml` 对两个最小固定配置运行仅报告的定时任务，生成 CSV 制品和作业摘要。
- **docs/FAQ.md**：CRG 与 LSP、RAG、grep/代理式搜索及相邻工具的比较；何时不应使用；验证步骤；monorepo/worktree 和注册表指南。
- **贡献脚手架**：GitHub Issue 表单（bug/功能/平台）、与 CONTRIBUTING 检查清单对应的 PR 模板，以及 pip + GitHub Actions 的 dependabot 配置。
- **Windows 修复**：`daemon status` 不再因 WinError 87 崩溃（#511），CLI `detect-changes` 将差异路径映射为绝对原生路径，不再报告 0 个函数（#528）。
- **提供方名称验证**：未知的嵌入提供方名称现在会报告明确错误并列出有效提供方，而非静默回退到本地模型。
- **存储泄漏修复**：五个分析 MCP 工具和 wiki 页面工具不再泄漏 SQLite 连接（通过 try/finally `store.close()`）。
- **`fastmcp<4` 版本上限**：下一个 fastmcp 大版本不再能静默破坏服务器。
- **Worktree 安全 git hooks**：`install` 通过 `git rev-parse --git-path hooks` 解析真实 hooks 目录，因此链接的 worktree 和 `core.hooksPath`（husky）设置都能获得正常运行的 pre-commit hook。

## v2.3.5
- **每次简要 CLI 调用都有 Token Savings 面板**：`code-review-graph detect-changes --brief` 和新增的 `code-review-graph update --brief` 打印带框的 `Token Savings` 面板——全量上下文基线、图谱响应、节省 Token 数、百分比，以及按类别分解（函数/测试/风险/其他）且总和精确等于图谱响应大小。
- **`--verify` 标志**：与 OpenAI 的 `cl100k_base` 分词器（GPT-4 系列）交叉验证显示数字。添加第二行 `Verified (tiktoken)` 显示真实 Token 数。对 222 个混合语言文件的校准显示估算在总量上与真实 Token 差距约 1%。
- **`update --brief`**：增量更新 + 同一风险面板一步完成。区别于 `detect-changes --brief`（对现有图谱只读）——当图谱可能过时时（rebase 后、大型变更集）使用 update。
- **`code-review-graph embed` CLI 子命令**：显式 Shell 级别的嵌入生成入口。此前只能通过 MCP 访问。
- **确定性评估流水线**：所有 6 个评估配置固定上游 SHA，`eval/runner.py` 使用完整克隆并进行显式 `returncode` 检查，Leiden 社区检测使用固定种子（`CRG_LEIDEN_SEED=42`）。在不同机器上的两次运行产生相同数字。
- **`multi_hop_retrieval` 基准**：11 个手工整理的 2 步工具链任务（`hybrid_search` → `query_graph`），跨 6 个测试仓库。平均得分 0.909。
- **更丰富的语义搜索**：`embeddings._node_to_text` 现在包含点分形式（`Module.Class.method`）、词分标识符和外层模块目录。自然语言查询的搜索排名从 0.545 提升至 0.909（multi-hop 基准）。
- **标识符感知搜索提升**：`extract_query_identifiers` 从自然语言查询中提取点分/snake_case/CamelCase Token，并将匹配限定名的权重提升 ×2.0（混合搜索中）。
- **路径规范化修复**：`eval/runner.py` 现在在存储前绝对解析仓库路径，使评估构建的图谱与 CLI/MCP 构建的图谱一致，`update` 不再为同一源位置创建重复节点。
- **测试缺口去重**：简要摘要中的 `Untested:` 行按裸名去重（防止限定名重复的防御性保护）。
- **评估中 FTS5 自动重建**：评估框架在 `full_build` 后自动调用 `run_post_processing`，FTS5 自动填充，不再留空索引。

## v2.3.4
- **估算上下文节省**：审查、影响、detect-changes 和紧凑架构响应包含微型 `context_savings` 元数据（`estimated`、`saved_tokens`、`saved_percent`），当可估算基线时。
- **紧凑架构概览为默认**：`get_architecture_overview_tool` 默认 `detail_level="minimal"` 以避免庞大的成员列表和逐边有效载荷。使用 `detail_level="standard"` 获取完整细节。
- **有界变更分析**：`CRG_MAX_CHANGED_FUNCS`、`CRG_MAX_TRANSITIVE_FRONTIER` 和 `CRG_TOOL_TIMEOUT` 帮助大型 MCP 审查调用保持响应速度。
- **Windows MCP 可靠性**：本地嵌入模型在 FastMCP 启动 worker 调度前在 Windows 上预热，避免语义搜索死锁。
- **解析器正确性**：Rust `#[test]` 和常见异步测试属性现在产生 `Test` 节点。
- **图谱查找正确性**：审查、影响和文件摘要工具将用户可见路径解析为存储的图谱路径；`callers_of` 包含跨文件调用方，即使同文件调用方也存在。
- **安装/运行时可靠性**：生成的 Codex/Claude hooks 排空 stdin，bundled 文档可从 wheel 获取，缺失的本地嵌入报告不可用状态，`.svn` 根目录通过验证。
- **CLI 可靠性**：`build --skip-postprocess` 和 `update --skip-flows` 遵从请求的后处理级别。
- **广泛解析语言**：Python、JavaScript/TypeScript/TSX、Go、Rust、Java、C/C++、C#、VB.NET、Ruby、Kotlin、Swift、PHP、Scala、Solidity、Dart、R、Perl、Lua/Luau、Objective-C、Shell 脚本、Elixir、Zig、PowerShell、Julia、ReScript、GDScript、Nix、Verilog/SystemVerilog、SQL、Terraform/OpenTofu 结构（`.tf`；通用 `.hcl` 文件识别为文件节点）、Ansible playbooks/roles/tasks、Vue/Svelte SFC、Astro 文件（通过 TypeScript 解析器）、Jupyter/Databricks 笔记本，以及 Perl XS 文件。通用 YAML 不视为源代码。
- **本地优先设计**：SQLite 图谱存储保持本地，无遥测，无云默认行为。

## v2.0.0
- **22 个 MCP 工具**（从 9 个增加）：13 个新工具，涵盖流程、社区、架构、重构、wiki、多仓库和带风险评分的变更检测。
- **5 个 MCP prompts**：`review_changes`、`architecture_map`、`debug_issue`、`onboard_developer`、`pre_merge_check` 工作流模板。
- **18 种语言**（从 15 种增加）：新增 Dart、R、Perl 支持。
- **执行流程**：从入口点（HTTP 处理器、CLI 命令、测试）追踪调用链，按关键度评分排序。
- **社区检测**：通过 Leiden 算法（igraph）或基于文件的分组聚类相关代码实体。
- **架构概览**：自动生成架构图，包含模块摘要和跨社区耦合警告。
- **带风险评分的变更检测**：`detect_changes` 将 git 差异映射到受影响的函数、流程、社区和测试覆盖缺口，按优先级排序。
- **重构工具**：带编辑列表的重命名预览、死代码检测、社区驱动的重构建议。
- **Wiki 生成**：为每个社区自动生成 Markdown wiki 页面，支持可选的 LLM 摘要（ollama）。
- **多仓库注册表**：注册多个仓库，通过 `cross_repo_search` 跨所有仓库搜索。
- **全文搜索**：带 Porter stemming 的 FTS5 虚拟表，用于混合关键词 + 向量搜索。
- **数据库迁移**：带自动升级的版本化 schema 迁移（v1-v5）。
- **可选依赖组**：`[embeddings]`、`[google-embeddings]`、`[communities]`、`[eval]`、`[wiki]`、`[all]`。
- **评估框架**：带 matplotlib 可视化的基准套件。
- **TypeScript 路径解析**：tsconfig.json paths/baseUrl 别名解析用于导入。
- **486 个测试**，跨 22 个测试文件。

## v1.8.4
- **多词 AND 搜索**：`search_nodes` 现在要求所有词都匹配（不区分大小写），产生更精确的结果。
- **调用目标解析**：裸调用目标使用同文件定义解析为限定名，提升 `callers_of`/`callees_of` 准确性。
- **影响半径分页**：`get_impact_radius` 返回 `truncated` 标志和 `total_impacted` 计数；`max_results` 参数控制输出大小。
- **`find_large_functions_tool`**：新增 MCP 工具，查找超过行数阈值的函数、类或文件。
- **15 种语言**：新增 Vue SFC 和 Solidity 支持。
- **文档全面更新**：所有文档更新为准确的语言/工具数量、版本引用和 VS Code 扩展对等。

## v1.8.3
- **解析器递归保护**：`_MAX_AST_DEPTH = 180` 防止深度嵌套 AST 上的栈溢出。
- **模块缓存上限**：`_MODULE_CACHE_MAX = 15,000`，带自动驱逐。
- **嵌入线程安全**：EmbeddingStore SQLite 使用 `check_same_thread=False`。
- **嵌入重试逻辑**：Google Gemini API 调用的指数退避。
- **可视化 XSS 加固**：JSON 序列化中 `</` 转义为 `<\/`。
- **CLI 错误处理**：将宽泛的 `except` 拆分为具体处理器。
- **Git 超时**：通过 `CRG_GIT_TIMEOUT` 环境变量可配置。
- **治理文件**：CONTRIBUTING.md、SECURITY.md、CODE_OF_CONDUCT.md。

## v1.8.2
- **C# 解析修复**：语言标识符从 `c_sharp` 重命名为 `csharp`。
- **监听模式线程安全**：SQLite 连接兼容 Python 3.10/3.11 watchdog 线程。
- **全量重建清理**：全量重建时清除已删除文件的过时数据。
- **依赖精简**：移除未使用的 `gitpython` 依赖。

## v1.7.0
- **`install` 命令**：新的主要设置入口（`code-review-graph install`）。`init` 保留为别名。
- **`--dry-run` 标志**：预览 `install`/`init` 将写入什么，而不修改文件。
- **PyPI 自动发布**：GitHub 发布现在自动发布到 PyPI。
- **README 重写**：包含来自 httpx、FastAPI 和 Next.js 真实基准数据的专业文档。

## v1.6.4
- **可移植 MCP 配置**：`init` 现在生成基于 `uvx` 的 `.mcp.json`——无绝对路径，在任何安装了 `uv` 的机器上都能工作。
- **移除符号链接变通方案**：使用 `uvx` 后不再需要处理路径中空格的 `_safe_path` 辅助函数。

## v1.6.3
- **SessionStart hook**：会话开始时 Claude Code 自动优先使用图谱 MCP 工具而非全代码库扫描。
- **Marketplace 就绪**：plugin.json 已修正，用于官方 Claude Code 插件市场提交。
- **README 清理**：移除截图占位符。

## v1.6.2
- **24 项审计修复**：关键 bug 修复、性能提升、解析器增强、测试覆盖扩展。
- **解析器：C/C++ 支持**：C 和 C++ 的完整节点提取（类、函数、导入、调用、继承）。
- **解析器：名称提取**：修复 Kotlin、Swift（simple_identifier）、Ruby（constant）的问题。
- **性能**：NetworkX 图谱缓存、批量边查询、分块嵌入搜索、git 子进程超时。
- **CI 加固**：覆盖率强制（50%）、bandit 安全扫描、mypy 类型检查。
- **测试**：+40 个新测试，覆盖增量更新、嵌入和 7 种新语言 fixtures。
- **文档**：API 响应 schema、ignore 模式文档、修复 hook 配置引用。
- **无障碍**：D3.js 可视化全面添加 ARIA 标签。

## v1.5.3
- **路径含空格处理**：*（v1.6.4 中被基于 `uvx` 的配置取代）* 此前通过符号链接处理路径中的空格。
- **无需 git**：`build`、`status`、`visualize`、`watch` 现在可在没有 git 的任何目录运行。
- **插件就绪**：技能在 plugin.json 中注册，SKILL.md frontmatter 已修复。
- **文件组织**：生成文件移入 `.code-review-graph/` 目录（自动创建 `.gitignore`，遗留迁移）。
- **可视化密度**：起始折叠（只显示 File 节点）、搜索栏、可点击边类型切换、大型图谱的感知比例布局。
- **项目清理**：移除冗余的 `references/`、`agents/`、`settings.json`。

## v1.4.0
- **`init` 命令**：自动设置 Claude Code 集成的 `.mcp.json`。
- **交互式 D3.js 图谱可视化**：`code-review-graph visualize` 生成可在浏览器中探索的 HTML 图谱。
- **文档全面更新**：跨所有参考文件的综合文档审计。

## v1.3.0
- **带 Docker 回退的 Python 版本检查**：自动检测 Python 3.10+，如不可用建议使用 Docker。
- **通用安装**：`pip install code-review-graph`——无需 git clone。
- **CLI 入口**：pip 安装后全局可用 `code-review-graph` 命令。

## v1.2.0
- **日志改进**：整个代码库的结构化日志。
- **监听防抖**：监听模式中更智能的文件变更检测。
- **tools.py 修复**：MCP 工具的 bug 修复和可靠性改进。
- **CI 覆盖**：带测试覆盖率报告的 GitHub Actions CI/CD 流水线。

## v1.1.0
- **监听模式**：`code-review-graph watch`——文件变更时自动重建图谱。
- **向量嵌入**：可选的 `pip install .[embeddings]` 用于语义代码搜索。
- **Go、Rust、Java 已验证**：12+ 种语言，有专属测试覆盖。
- **47 个测试通过**，注册 8 个 MCP 工具。
- README 徽章和更简洁的安装流程。

## v1.0.0（基础版）
- **持久化 SQLite 知识图谱**——零外部依赖。
- **Tree-sitter 多语言解析**——类、函数、导入、调用、继承。
- **通过 `git diff` 增量更新** + 自动依赖级联。
- **影响半径/爆炸半径分析**——通过调用/导入/继承图的 BFS。
- **6 个 MCP 工具**用于完整图谱交互。
- **3 个审查优先技能**：build-graph、review-delta、review-pr。
- **PostToolUse hooks**（Write|Edit|Bash）用于自动后台更新。
- **FastMCP 3.0 兼容** stdio MCP 服务器。

## 隐私与数据
- 核心图谱数据存储在本地。
- 图谱存储在 `.code-review-graph/graph.db`（SQLite），自动添加到 `.gitignore`。
- 无遥测；核心图谱/审查工作流不需要网络访问。
- 可选的嵌入和 wiki 功能在明确启用时可能调用配置的本地或远端服务。
- 遵从 `.gitignore` 和 `.code-review-graphignore`。
