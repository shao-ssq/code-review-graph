# 架构设计

## 系统概述

`code-review-graph` 是一个本地优先的代码智能图谱，通过 CLI 和 MCP 服务器对外提供能力。它为代码库维护一个持久化、增量更新的知识图谱，使 AI 编码工具能够借助结构化上下文进行代码审查，而无需读取大量文件。Claude Code 是其支持的客户端之一，但并非唯一。

## 组件图

```
┌──────────────────────────────────────────────────────────────┐
│                    AI 编码客户端 / CLI                         │
│                                                              │
│  MCP 客户端                Hooks / 监听模式                    │
│  ├── Codex                └── 增量更新                        │
│  ├── Claude Code, CodeBuddy Code                             │
│  ├── Cursor, Windsurf, Zed, Continue                         │
│  └── Gemini CLI, Qwen, Qoder, Copilot, OpenCode              │
│          │                        │                          │
│          ▼                        ▼                          │
│  ┌────────────────────────────────────────────┐              │
│  │    MCP 服务器（stdio 或 localhost HTTP）    │              │
│  │                                            │              │
│  │  30 个 MCP 工具 + 5 个 MCP Prompt          │              │
│  │  ├── 核心：build、impact、query、review、  │              │
│  │  │   search、traverse、embed、stats、docs  │              │
│  │  ├── 流程：list、get、affected             │              │
│  │  ├── 社区：list、get、architecture         │              │
│  │  ├── 分析：detect_changes、refactor、      │              │
│  │  │   apply_refactor、hotspots、gaps        │              │
│  │  ├── Wiki：generate、get_page              │              │
│  │  └── 多仓库：list_repos、cross_search      │              │
│  └────────────────┬───────────────────────────┘              │
└───────────────────┼──────────────────────────────────────────┘
                    │
        ┌───────────┼───────────────┐
        ▼           ▼               ▼
   ┌─────────┐ ┌─────────┐  ┌─────────────┐
   │ 解析器  │ │  图存储 │  │  增量引擎   │
   │         │ │         │  │             │
   └────┬────┘ └────┬────┘  └──────┬──────┘
        │           │              │
        ▼           ▼              ▼
   Tree-sitter   SQLite DB      git/svn diff
    语法库       (.code-review- 子进程
                 graph/
                 graph.db)
```

## 数据流

### 全量构建
1. `collect_all_files()` 收集被追踪的文件（`git ls-files`）并应用 `.code-review-graphignore`（git 忽略文件在 git 可用时会自动跳过）
2. 对每个文件，`CodeParser.parse_file()` 使用 Tree-sitter 提取 AST
3. AST 遍历器识别结构化节点（类、函数、导入）和边（调用、继承）
4. `GraphStore.store_file_nodes_edges()` 将数据持久化到 SQLite，并记录文件哈希以进行变更检测
5. 更新带时间戳的元数据

### 增量更新
1. `get_changed_files()` 使用版本控制元数据识别变更文件（默认使用 git diff，增量层也支持 SVN）
2. `find_dependents()` 查询图中导入了变更文件的文件
3. 重新解析变更文件及其依赖文件（通过哈希比较跳过未变更文件）
4. 仅更新 SQLite 中受影响的行

### 审查上下文生成
1. 识别变更文件（git diff 或明确指定的列表）
2. `get_impact_radius()` 从变更节点向外遍历，对每个节点进行加权最优路径评分（每种边类型的权重 × 深度衰减），而非简单 BFS
3. 仅对变更区域提取源代码片段
4. 生成审查建议（测试覆盖缺口、宽泛影响半径警告）
5. 为 MCP 客户端和 CLI 组装结构化、Token 高效的上下文
6. 若可估算简化基准，则附加紧凑的 `context_savings` 元数据（估算值，非精确分词）

## 存储

### SQLite Schema
- **nodes** 表：id、kind、name、qualified_name、file_path、line_start/end、language、community_id 等
- **edges** 表：id、kind、source_qualified、target_qualified、file_path、line
- **metadata** 表：键值对（last_updated、build_type、schema_version）
- **flows** 表：id、name、entry_point_id、depth、node_count、file_count、criticality、path_json
- **flow_memberships** 表：flow_id、node_id、position
- **communities** 表：id、name、level、parent_id、cohesion、size、dominant_language、description
- **nodes_fts**（FTS5 虚拟表）：对 name、qualified_name、file_path、signature 进行全文搜索
- **community_summaries**、**flow_snapshots**、**risk_index** 表：用于 Token 高效查询的预计算紧凑摘要
- **embeddings** 表（独立数据库）：qualified_name、vector、text_hash、provider

在 qualified_name、file_path、边的 source/target、criticality、community_id 和 cohesion 上建有索引，以实现快速查询。

启用 WAL 模式以支持更新期间的并发读访问。

### 限定名称
节点通过限定名称唯一标识：
- 文件：绝对路径（例如 `/repo/src/auth.py`）
- 函数：`file_path::function_name`（例如 `/repo/src/auth.py::authenticate`）
- 方法：`file_path::ClassName.method_name`（例如 `/repo/src/auth.py::AuthService.login`）

## 解析策略

Tree-sitter 提供与语言无关的 AST 访问能力。解析器：
1. 递归遍历 AST
2. 对节点类型进行模式匹配（`_CLASS_TYPES`、`_FUNCTION_TYPES` 等中的语言特定映射）
3. 提取名称、参数、返回类型、基类
4. 识别函数体内的调用
5. 将导入解析为模块路径

相比跨语法版本的 tree-sitter 查询，此方式更为健壮。

## 可视化

`visualization.py` 模块生成一个交互式 D3.js 力导向图，输出为自包含的 HTML 文件。它从 SQLite 图存储读取所有节点和边，并在浏览器中渲染，使开发者可以可视化探索代码关系、按节点类型过滤、检查依赖关系。

## 影响分析算法

从种子节点（变更文件的内容）出发进行 BFS：
1. 种子 = 变更文件中的所有限定名称
2. 对边界中的每个节点：
   - 追踪前向边（该节点影响的内容）
   - 追踪反向边（依赖该节点的内容）
3. 展开至最多 `max_depth` 跳（默认：2）
4. 收集所有到达的节点作为"受影响节点"

这既能捕获下游影响（调用变更代码的内容），也能获取上游上下文（变更代码所依赖的内容）。
