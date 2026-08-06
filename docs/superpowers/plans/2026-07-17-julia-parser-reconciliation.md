# Julia 解析器协调实现计划

> **面向 Agent 工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现本计划。步骤使用复选框（`- [ ]`）语法进行追踪。

**目标：** 从 PR #560 移植安全的 Julia 解析器行为，同时为嵌套和模块限定的定义提供无冲突的标识和可解析的下游图谱边。

**架构：** 保持现有解析器和图谱 schema 不变。Julia 专用 AST 辅助函数推导字段组件、操作符名称、别名和完整词法作用域；解析器节点在 `parent_name` 中编码词法作用域加显式限定符，而后解析调用解析从调用方最近的作用域向外搜索。

**技术栈：** Python 3.10+、通过 `tree-sitter-language-pack` 的 Tree-sitter、pytest、SQLite `GraphStore`、Ruff、mypy、Bandit。

## 全局约束

- 不改变其他语言的图谱 schema 或通用行为。
- 不从 Tree-sitter `ERROR` 节点推断定义。
- 不将 Julia 标量 `const` 绑定转换为 Type 节点。
- 保持源 PR #560 不变，并在实现提交中注明 `dan <danvinci@fastmail.net>` 的贡献。
- 每个生产变更必须遵循可见的红/绿/重构循环。
- 保留所有现有的 Julia 宏、枚举、testset、导出、include 和 fixture 测试。

---

## 文件结构

- 创建 `tests/test_julia_reconciliation.py`：专注的解析器、作用域、软失败、持久化和下游查询回归测试，独立于共享的多语言 fixture。
- 修改 `code_review_graph/parser.py`：Julia 专用辅助函数和提取、作用域、导入别名、调用目标和同文件解析行为。
- 保持 `tests/fixtures/sample.jl` 和 `tests/test_multilang.py` 不变，以使其保持作为现有 Julia 行为的独立无回归检查。

### 任务 1：Julia 叶节点构造和软失败提取

**文件：**

- 创建：`tests/test_julia_reconciliation.py`
- 修改：`code_review_graph/parser.py:3361-3695,7431-7475,7909-7950`

**接口：**

- 消费：`CodeParser.parse_bytes(Path, bytes) -> tuple[list[NodeInfo], list[EdgeInfo]]`。
- 产出：`_julia_component_name(node) -> Optional[str]`、`_julia_field_parts(node) -> list[str]`、`_julia_field_info(node) -> tuple[Optional[str], Optional[str]]`，以及对源构造有效的 Function/Type/import 输出。

- [ ] **步骤 1：编写专注的失败测试**

创建一个不写生产文件、直接解析片段的辅助函数：

```python
from pathlib import Path

import pytest

from code_review_graph.parser import CodeParser


def _parse(source: str):
    return CodeParser().parse_bytes(Path("/repo/case.jl"), source.encode())


def test_function_stub_is_a_function():
    nodes, _ = _parse("function hook end")
    assert [(n.kind, n.name) for n in nodes if n.kind != "File"] == [
        ("Function", "hook"),
    ]


@pytest.mark.parametrize("signature", ["+(a, b) = a", "Base.:+(a, b) = a"])
def test_operator_definition_uses_operator_name(signature):
    nodes, _ = _parse(signature)
    functions = [n for n in nodes if n.kind == "Function"]
    assert [n.name for n in functions] == ["+"]


def test_parameterized_const_only_is_a_type():
    nodes, _ = _parse(
        "const FloatVec = Vector{Float64}\nconst MAX_RETRIES = 3\n"
    )
    assert {n.name for n in nodes if n.kind == "Type"} == {"FloatVec"}


def test_import_alias_records_real_dependency():
    _, edges = _parse(
        "import DataFrames as DF\nimport Tables: AbstractColumns as Columns\n"
    )
    assert {e.target for e in edges if e.kind == "IMPORTS_FROM"} == {
        "DataFrames",
        "Tables.AbstractColumns",
    }


def test_malformed_qualified_stub_fails_soft():
    nodes, edges = _parse("function A.B.hook end")
    assert [n.kind for n in nodes] == ["File"]
    assert edges == []
```

- [ ] **步骤 2：验证红色（RED）**

运行：

```bash
uv run --frozen --no-sync pytest -q \
  tests/test_julia_reconciliation.py::test_function_stub_is_a_function \
  tests/test_julia_reconciliation.py::test_operator_definition_uses_operator_name \
  tests/test_julia_reconciliation.py::test_parameterized_const_only_is_a_type \
  tests/test_julia_reconciliation.py::test_import_alias_records_real_dependency \
  tests/test_julia_reconciliation.py::test_malformed_qualified_stub_fails_soft
```

预期：stub、操作符、类型别名和导入别名断言因缺少行为而失败；畸形输入已通过并保护实现。

- [ ] **步骤 3：实现最小 Julia 叶节点处理**

添加对未知形状返回 `None` 的辅助函数，在 `_julia_short_func_name` 和 Julia `_get_name` 中使用它们，将 `const_statement` 分支添加到 `_extract_julia_constructs`，并扩展 `_extract_import` 以支持直接和选择的 `import_alias` 节点。具体的无作用域辅助函数约定如下：

```python
@staticmethod
def _julia_component_name(node) -> Optional[str]:
    if node.type in ("identifier", "operator"):
        return node.text.decode("utf-8", errors="replace")
    if node.type == "quote_expression":
        for child in node.children:
            name = CodeParser._julia_component_name(child)
            if name is not None:
                return name
    if node.type == "parenthesized_expression":
        for child in node.children:
            if child.type == "operator":
                return child.text.decode("utf-8", errors="replace")
    return None
```

对于参数化 const，追加 `NodeInfo(kind="Type", ...)` 和匹配的 `CONTAINS` 边，然后返回 `True`。不消费其他任何 const 语句。

- [ ] **步骤 4：验证绿色（GREEN）且无 Julia 回归**

运行：

```bash
uv run --frozen --no-sync pytest -q \
  tests/test_julia_reconciliation.py tests/test_multilang.py::TestJuliaParsing
```

预期：所有选定测试通过。

### 任务 2：规范化限定标识和作用域调用解析

**文件：**

- 修改：`tests/test_julia_reconciliation.py`
- 修改：`code_review_graph/parser.py:2423-2460,3361-3695,4889-5225,5257-5360`

**接口：**

- 消费：任务 1 中的 Julia 字段辅助函数。
- 产出：`_julia_scope_join(left, right) -> Optional[str]`、`_julia_definition_qualifier(node) -> Optional[str]`、规范化父名称、带点调用目标，以及 `_resolve_call_targets` 中的最近作用域解析。

- [ ] **步骤 1：编写冲突和调用失败测试**

添加使用如下模块的测试：定义本地 `show`、`Base.show`、`Base.length`、`Base.:+`、`A.B.run`、单行委托和带点调用。断言这些精确的标识和边：

```python
assert ("show", "Demo") in identities
assert ("show", "Demo.Base") in identities
assert ("length", "Demo.Base") in identities
assert ("+", "Demo.Base") in identities
assert ("run", "Demo.A.B") in identities
assert ("Demo.delegate", "Demo.show") in call_tails
assert ("Demo.caller", "Demo.A.B.run") in call_tails
assert any(
    e.target == "LinearAlgebra.BLAS.gemv"
    and e.extra["julia_call_module"] == "LinearAlgebra.BLAS"
    for e in calls
)
```

同时断言来自 `Demo.Base.show` 的限定符引用指向字面量 `Base`，即使文件中包含名为 `Base` 的本地函数。

- [ ] **步骤 2：验证红色（RED）**

单独用 `pytest -vv` 运行新的冲突/调用测试。预期：限定标识折叠到 `Demo` 下，`Base.:+` 变成错误的 `Base` 函数，单行调用缺失，带点目标保留为裸叶子。

- [ ] **步骤 3：实现规范化作用域和限定调用**

在长形和短形定义中使用此标识规则：

```python
lexical_parent = self._julia_scope_join(enclosing_class, enclosing_func)
identity_parent = self._julia_scope_join(lexical_parent, qualifier)
```

当 `qualifier` 缺失时，`identity_parent` 就是 `lexical_parent`。将显式限定符存储在 `extra["julia_module_qualifier"]` 中；从 `lexical_parent` 创建 `CONTAINS`；用 `enclosing_class=identity_parent` 和 `enclosing_func=name` 递归进入函数。

在 `_extract_calls` 中，将 Julia 字段表达式被调用方替换为其完整的 `qualifier.leaf` 文本，并设置 `julia_call_module`。在下降到其子节点之前直接分发短形 RHS 调用节点。

在 `_resolve_call_targets` 中，对非 Julia 文件保留当前实现。对于 Julia，按规范化限定名称的尾部索引每个定义，并按此顺序测试候选（源 `file::Outer.Inner.caller`，目标 `f`）：`Outer.Inner.caller.f`、`Outer.Inner.f`、`Outer.f`、`f`。对 extra 中包含 `julia_qualified_def` 的 REFERENCES 边跳过本地重写。

- [ ] **步骤 4：验证绿色（GREEN）**

运行新测试加 `tests/test_multilang.py::TestJuliaParsing`；预期：全部通过，无现有 Julia 断言变更。

### 任务 3：嵌套作用域、别名、宏和 testset

**文件：**

- 修改：`tests/test_julia_reconciliation.py`
- 修改：`code_review_graph/parser.py:3630-3695,4889-5020,6707-6760`

**接口：**

- 消费：任务 2 中的规范化作用域和解析器。
- 产出：嵌套模块/函数/testset 的完整词法路径，以及 `import_map` 中的 Julia 别名绑定。

- [ ] **步骤 1：编写嵌套和别名失败测试**

添加包含 shadowed `f` 的嵌套 `Outer.Inner` 片段、嵌套函数、函数本地 `@testset`、`@inline`/普通宏调用，以及 `import DataFrames as DF`。断言：

```python
assert "Outer.Inner" in class_parents_and_names
assert ("f", "Outer.Inner") in identities
assert ("leaf", "Outer.Inner.wrapper") in identities
assert any(e.target.endswith("::Outer.Inner.f") for e in calls_from_inner)
assert any(n.kind == "Test" and n.parent_name == "Outer.Inner.wrapper" for n in nodes)
assert any(e.target == "DataFrames.transform" for e in alias_calls)
assert any(e.target == "@inline" for e in calls)
```

- [ ] **步骤 2：验证红色（RED）**

仅运行这些测试。预期：嵌套函数/模块使用截断的父名称，最近调用选取 `Outer.f`，testset 标识与其边来源不同，别名调用保留为 `DF.transform`。

- [ ] **步骤 3：实现嵌套作用域和别名规范化**

对于 Julia 类/模块提取，用连接的作用域递归，并从封闭作用域（而非总是从 File）发出 `CONTAINS`。对于 testset，使用连接的词法函数作用域作为 `parent_name`、containment 来源和递归作用域。

扩展 `_collect_import_names` 以支持 Julia 别名，使得：

```python
import_map["DF"] = "DataFrames"
import_map["Columns"] = "Tables.AbstractColumns"
```

当限定调用的第一个模块段是别名时，在形成最终带点目标之前替换它。保持直接模块不变。

- [ ] **步骤 4：验证绿色（GREEN）并重构**

运行专注文件和现有 Julia 类。仅在所有测试通过后移除重复的 AST 遍历，然后重新运行同一命令。

### 任务 4：GraphStore 和下游查询持久化

**文件：**

- 修改：`tests/test_julia_reconciliation.py`

**接口：**

- 消费：`full_build(Path, GraphStore) -> dict` 和规范化解析器输出。
- 产出：证明 SQLite 节点和边 API 看到与解析器相同标识的集成回归测试。

- [ ] **步骤 1：编写完整构建测试**

在 `tmp_path` 下创建 `.git` 和 Julia 源文件，运行 `full_build`，然后断言：

```python
local = store.get_node(f"{source_path}::Demo.show")
base = store.get_node(f"{source_path}::Demo.Base.show")
assert local is not None and base is not None and local.id != base.id

callers = store.get_edges_by_target(f"{source_path}::Demo.Base.show")
assert any(edge.kind == "CALLS" and edge.source.endswith("::Demo.invoke")
           for edge in callers)
assert result["errors"] == []
```

同时查询持久化的嵌套目标和 Type 别名，并在 `finally` 块中关闭 store。

- [ ] **步骤 2：验证红色（RED）或证明前置任务已覆盖**

在任何集成专用生产变更之前运行此测试。它必须在预移植生产代码上失败；如果任务 1-3 已使其通过，临时回退解析器变更，确认预期的标识/调用失败，恢复它们，然后重新运行绿色。

- [ ] **步骤 3：验证专注和完整测试套件**

运行：

```bash
uv run --frozen --no-sync pytest -q tests/test_julia_reconciliation.py \
  tests/test_multilang.py::TestJuliaParsing
uv run --frozen --no-sync pytest -q
```

预期基线增量：所有 1,573 个先前通过的测试保持绿色，加上新的 Julia 测试；现有的 skip/xpass 保持非失败状态。

### 任务 5：静态检查、图谱审查、归因、变基和发布

**文件：**

- 验证：`code_review_graph/parser.py`
- 验证：`tests/test_julia_reconciliation.py`
- 验证：设计和计划文档

**接口：**

- 产出：基于最新 `origin/main` 的就绪替代 PR，Dan 的贡献已注明，源 PR #560 未被修改。

- [ ] **步骤 1：运行本地质量门禁**

```bash
uv run --frozen --no-sync ruff check code_review_graph tests
uv run --frozen --no-sync ruff format --check code_review_graph tests
uv run --frozen --no-sync mypy code_review_graph
uv run --frozen --no-sync bandit -q -r code_review_graph
uv run --frozen --no-sync python scripts/check_schema_sync.py
git diff --check
```

预期：每个命令都以 0 退出。

- [ ] **步骤 2：审查图谱和差异**

增量重建知识图谱，然后针对 `origin/main` 运行变更检测、受影响流程、tests-for 查询和专注审查上下文。检查 `git diff --stat`、`git diff`，确保只有已批准的文件和行为发生了变更。

- [ ] **步骤 3：带归因提交**

使用此 trailer 提交生产代码/测试：

```text
Co-authored-by: dan <danvinci@fastmail.net>
```

- [ ] **步骤 4：变基并重复全新验证**

获取 `origin/main`，变基分支，重新运行专注/完整测试和所有静态检查，更新图谱，并检查最终差异。不解决任何无关变更，未经明确批准绝不强制推送。

- [ ] **步骤 5：推送并开启就绪替代 PR**

PR 正文必须：命名源 PR #560 及其精确 HEAD、枚举重叠和移植的行为、解释额外冲突/调用解析阻塞因素、说明精确的 base/head 和本地测试证据、注明 Dan 的贡献，并声明源 PR #560 未被修改。等待所有必需检查（包括 Windows）成功完成后，再报告就绪状态。