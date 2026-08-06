# 自定义语言（自带语言支持）

code-review-graph 内置了 35+ 种语言的解析器，但它所依赖的
[tree-sitter-language-pack](https://github.com/Goldziher/tree-sitter-language-pack)
捆绑了远比内置列表更多的语法。如果你的仓库使用了图谱尚未覆盖的语言——Erlang、Haskell、OCaml、Fortran、Ada、Clojure 等——你可以通过一个小配置文件来让解析器支持它。无需 Fork，无需修改代码。

## 快速开始

在 `<repo_root>/.code-review-graph/languages.toml` 中创建配置文件：

```toml
[languages.erlang]
extensions = [".erl"]
grammar = "erlang"
function_node_types = ["function_clause"]
class_node_types = ["record_decl"]
import_node_types = ["import_attribute"]
call_node_types = ["call"]
comment = "通过内置的 tree-sitter-erlang 语法支持 Erlang"
```

然后重新构建：

```bash
uv run code-review-graph build
```

匹配配置扩展名的文件现在将使用指定语法进行解析，生成的 Function/Class 节点和 CALLS/IMPORTS_FROM 边会像内置语言一样流经所有下游功能（影响半径、搜索、社区、Wiki、MCP 工具）。节点的 `language` 字段记录自定义语言名称（此处为 `erlang`）。

## Schema 参考

每种自定义语言对应一个 `[languages.<name>]` 表。

| 键 | 类型 | 必填 | 含义 |
|----|------|------|------|
| `<name>` | 表键 | 是 | 存储在每个解析节点上的语言标识符。小写字母、数字、`_`、`-`；最多 32 个字符；必须以字母开头。 |
| `extensions` | 字符串列表 | 是 | 要匹配的文件扩展名，每个以点开头（如 `".erl"`）。大小写不敏感匹配。 |
| `grammar` | 字符串 | 是 | `tree_sitter_language_pack` 提供的语法名称（探测可用性——见下文）。 |
| `function_node_types` | 字符串列表 | 否* | 定义函数/方法的 Tree-sitter 节点类型。匹配的节点变为 `Function` 节点（或在名称/文件看起来像测试时变为 `Test` 节点）。 |
| `class_node_types` | 字符串列表 | 否* | 定义类/记录/类型的节点类型。匹配的节点变为 `Class` 节点。 |
| `import_node_types` | 字符串列表 | 否* | 导入/include 语句的节点类型。每个生成一条 `IMPORTS_FROM` 边。 |
| `call_node_types` | 字符串列表 | 否* | 调用表达式的节点类型。每个从外层函数生成一条 `CALLS` 边。 |
| `name_field` | 字符串或字符串列表 | 否 | 当定义的名称不在 `name` 字段或普通 `identifier` 子节点中时，用于定位名称的候选（见下文）。 |
| `comment` | 字符串 | 否 | 供人阅读的备注；解析器忽略它。 |

\* 四个节点类型列表中至少一个不为空，否则该条目被跳过（没有任何可提取的内容）。

### 验证规则（安全优先）

加载器绝不会导致构建崩溃。无效条目会被跳过并打印 `WARNING` 日志：

- **内置语言始终优先。** 自定义语言不能声明内置扩展名（`.py`、`.ts`、`.ex` 等），也不能复用内置语言名称（`python`、`elixir` 等）。
- `grammar` 必须能从 `tree_sitter_language_pack` 加载；未知语法会被跳过。
- 每个扩展名必须以点开头。
- 两种自定义语言不能声明同一扩展名（先定义者优先）。
- 每个仓库最多加载 **20** 种自定义语言。
- 格式错误的 TOML 会对该次构建禁用自定义语言（并打印警告）。
- `name_field` 必须是字符串或非空字符串列表（最多 8 个候选）；否则跳过该条目并打印警告。

### 使用 `name_field` 命名定义

默认情况下，解析器从 `identifier` 类型的子节点或字面上称为 `name` 的字段中找到定义的名称。许多语法把名称放在别处——在不同名称的字段中，或嵌套一两层。发生这种情况时，该定义会被**提取为无名称并静默丢弃**。`name_field` 告诉解析器在哪里查找。

每个候选依次尝试，通过两个步骤解析：

1. **字段优先** —— 通过该 tree-sitter 字段名访问的子节点。字段在任何类型搜索之前跨*所有*候选尝试，因此精确字段总是优先于更宽泛的匹配。
2. **类型后代** —— 如果没有候选匹配字段，则查找*节点类型*等于某个候选的第一个后代（有界深度）。这适用于名称位于无字段包装器下方的情况。

解析出的节点随后递归到其第一个带文本的叶节点并清理（去除周围的 `{}`/引号/空白；多行或过大文本会被拒绝）。由于解析锚定在你配置的候选上，它不会捕获不相关的内部标识符。

```toml
[languages.bibtex]
extensions = [".bib"]
grammar = "bibtex"
class_node_types = ["entry"]
name_field = ["key"]            # @article{smith2020,...} -> "smith2020"

[languages.latex]
extensions = [".tex"]
grammar = "latex"
class_node_types = ["section", "chapter", "subsection"]
function_node_types = ["new_command_definition"]
name_field = ["name", "text", "declaration"]
#   \section{Introduction}   -> "Introduction" (通过 `text`)
#   \newcommand{\foo}{bar}    -> "\foo"        (通过 `declaration`)

[languages.markdown]
extensions = [".md"]
grammar = "markdown"
class_node_types = ["section"]
name_field = ["inline"]         # "# My Heading" -> "My Heading"（类型后代）
```

当语法的节点类型在不同地方保存名称时（LaTeX `section` 使用 `text`，`\newcommand` 使用 `declaration`），使用**列表**：第一个解析成功的候选优先。省略 `name_field` 会完全保留之前的行为。

## 查找正确的节点类型名称

节点类型名称是语法特定的，需要查看语法实际产生的树。两种简便方式：

**方式 1 —— tree-sitter playground。** 将片段粘贴到
<https://tree-sitter.github.io/tree-sitter/7-playground.html> 并从解析树中读取节点名称（先选择对应语法）。

**方式 2 —— 用 Python 在本地探测。** 你构建时使用的确切语法版本在 `tree_sitter_language_pack` 中，因此在本地探测是最可靠的：

```bash
uv run python - <<'EOF'
import tree_sitter_language_pack as tslp

source = b"""
-module(math_utils).
add(A, B) -> helper(A) + B.
helper(X) -> X * 2.
"""

def dump(node, depth=0):
    print("  " * depth + node.type, node.text.decode()[:40].replace("\n", " "))
    for child in node.children:
        dump(child, depth + 1)

dump(tslp.get_parser("erlang").parse(source).root_node)
EOF
```

选择包裹整个定义的节点类型（`function_clause`，而非内部的 `atom`）和整个调用表达式（`call`，而非被调函数标识符）。

## 完整示例：Erlang 端到端

`src/math_utils.erl`：

```erlang
-module(math_utils).
-export([add/2, scale/2]).
-import(lists, [map/2]).

-record(point, {x, y}).

add(A, B) ->
    helper(A) + B.

helper(X) -> X * 2.

scale(Points, F) ->
    lists:map(fun(P) -> add(P, F) end, Points).
```

使用快速开始中的 `[languages.erlang]` 配置，构建后会产生：

- `Function` 节点 `add`、`helper`、`scale`（来自 `function_clause`），每个 `language = "erlang"`。
- `Class` 节点 `point`（来自 `record_decl`）。
- `CALLS` 边 `add → helper` 和 `scale → add`（解析为同文件限定名），以及 `scale → lists:map`（远程调用）。
- 一条目标为 `lists` 的 `IMPORTS_FROM` 边（来自 `import_attribute`）。
- 从文件到每个定义的 `CONTAINS` 边。

## 提取机制（及其限制）

自定义语言通过与内置语言相同的通用 tree-sitter 遍历器运行——没有需要维护的语言专用代码路径。这使功能保持简单，但通用启发式方法有其限制：

- **名称提取使用默认名称字段启发式。** 遍历器查找常见标识符类型（`identifier`、`name`、`type_identifier` 等）的子节点，并回退到语法的 `name` 字段（`node.child_by_field_name("name")`）。将定义名称存储在其他形状中的语法（例如嵌套两层深且字段名非标准）将产生无名称——因此被跳过——的定义。
- **被调函数提取探测常见字段名**（`function`、`callee`、`expr`、`name`），并遍历柯里化应用。特殊的调用形态可能会被遗漏。
- **导入目标**来自语法的 `module`/`name`/`path`/`source` 字段（如果存在），否则记录原始语句文本。
- **无跨文件模块解析。** 导入边保持模块名称原样（例如 `lists`）；不像内置语言有专用解析器那样解析为文件路径。
- **无语言特定附加功能**：基于装饰器的测试检测、框架注解（Spring、Temporal）或 SFC 处理仅适用于内置语言。

如果某种语言需要比通用遍历器更深层的支持，请提交 Issue——配置驱动的支持是入门，而非上限。

## 故障排除

- 启用 `-v`/日志记录运行构建，并在 `languages.toml` 警告中查找——每个被跳过的条目都会说明被跳过的原因。
- 探测语法可用性：
  `uv run python -c "import tree_sitter_language_pack as t; t.get_language('erlang')"`
  （如果语法未捆绑，则抛出 `LookupError`）。
- 配置在解析器构建时（每次 `build`/`update`）读取，因此配置变更在下次构建时生效——编辑后重新运行
  `uv run code-review-graph build`。
