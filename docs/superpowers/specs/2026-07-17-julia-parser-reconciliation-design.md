# Julia 解析器协调设计

## 背景

Pull Request #560 新增了有用的 Julia 覆盖，但其 HEAD `f66721a6f63cc352ea515ddf9ca6e9cba21c4666` 已陈旧，与当前 `main` 冲突。当前 `main` 已能解析 Julia 模块、结构体、长短形式函数、导入、include、export/public 符号、宏、枚举和 testset。剩余的源行为包括：函数存根、运算符、参数化常量别名、别名导入、单行调用体和完整模块限定符。

源实现将限定符仅存储在 `extra` 中。这保留了显示元数据，但不改变图谱标识或调用目标。因此，本地 `show` 可能与 `Base.show` 碰撞，限定调用可能被简化为 `show`，下游图谱查询无法区分它们。当前嵌套 Julia 模块和函数也会丢失其外层词法作用域。

源工作归功于 Dan（`danvinci`，`danvinci@fastmail.net`）。移植提交将保留该公认归属。源 PR #560 保持不变。

## 目标

- 从 PR #560 移植安全的、无重叠的 Julia 行为。
- 为限定 Julia 定义赋予无碰撞的规范标识。
- 将裸调用和限定调用解析为最近匹配的词法符号。
- 通过持久化保留完整的嵌套模块和函数作用域。
- 为别名导入记录真实模块，并通过别名规范化调用。
- 保持畸形或不支持的 Julia 语法静默失败，不产生虚假节点。
- 保留现有的宏、枚举、testset、export、include 和 Julia 测试。

## 非目标

- 替换 Julia 解析器或更改图谱 schema。
- 按参数类型或多重派发建模 Julia 方法派发。
- 为普通标量 `const` 绑定创建节点。
- 为文件中不存在的外部模块发明定义。
- 支持捆绑语法仅作为 `ERROR` 节点生成的畸形限定函数存根。
- 合并、关闭、重新打开或评论源 PR #560。

## 规范作用域和包含关系

实现复用现有的 `NodeInfo.parent_name` 标识模型。仅对 Julia，词法作用域被连接而非相互替换：

- `Outer.Inner` 中的函数 `f` 的父级为 `Outer.Inner`，限定名为 `file.jl::Outer.Inner.f`；
- 该函数内部的嵌套函数 `g` 的父级为 `Outer.Inner.f`，限定名为 `file.jl::Outer.Inner.f.g`；
- 在 `Outer.Inner` 内部写的 `function Base.show` 的父级为 `Outer.Inner.Base`，名称为 `show`，限定名为 `file.jl::Outer.Inner.Base.show`。

显式限定符仍保留在 `extra["julia_module_qualifier"]` 中，供直接需要它的消费者使用。限定定义的 `CONTAINS` 来源仍是其词法模块（`file.jl::Outer.Inner`），而非合成的 `Base` 节点。这在保持源结构的同时使标识无碰撞。

嵌套 `module` 定义以完整词法路径递归。嵌套函数和 testset 同样使用其外层函数路径，因此每个持久化的 `CONTAINS`、`CALLS` 和 `TESTED_BY` 端点都引用与其节点相同的限定名。

## Julia AST 辅助函数

小型 Julia 专用辅助函数处理语法形状，而不改变通用语言行为：

- 按源顺序展平嵌套的 `field_expression` 节点；
- 读取最终的标识符或引用运算符组件；
- 将字段分割为限定符和叶名称；
- 在 `where_expression` 和 `typed_expression` 等签名包装器中查找可调用项（有界遍历）；
- 连接词法作用域而不重复路径段；
- 从 `import_alias` 节点读取导入别名。

每个辅助函数对未知形状返回 `None` 或空结果。它不索引未检查的子节点，也不从 Tree-sitter `ERROR` 节点恢复定义。

## 定义和导入

长短形式的限定定义使用上述规范作用域。裸运算符和引用运算符使用运算符文本作为函数名，包括短形式如 `+(a, b) = a` 和 `Base.:+(a, b) = a`。当 Tree-sitter 提供有效的 `function_definition` 时，`function hook end` 这样的存根成为普通 Function 节点。

仅当 `const` 赋值的右侧是参数化/大括号类型表达式（如 `const FloatVec = Vector{Float64}`）时，才成为 Type 节点。值常量保留在现有通用路径上。

别名 Julia 导入在真实导入模块或符号上生成依赖：`import DataFrames as DF` 记录 `DataFrames`，选定别名保留选定符号路径。文件作用域别名映射记录本地别名，以便通过该别名的限定调用可以规范化为真实模块路径。

## 调用提取和解析

限定调用保留其点分被调用者目标，而非折叠为叶节点。例如，`LinearAlgebra.BLAS.gemv(x)` 初始目标为 `LinearAlgebra.BLAS.gemv`，并记录 `extra["julia_call_module"] = "LinearAlgebra.BLAS"`。别名头部在解析前被替换为其真实导入路径。

后处理同文件解析器从规范节点标识构建作用域 Julia 符号键。对于每个未解析的 Julia 调用，它从调用方最近的父级作用域向外搜索，然后检查文件级符号。因此 `Outer.Inner.g` 内的裸 `f()` 优先选择 `Outer.Inner.f` 而非 `Outer.f`，而 `Base.show()` 可以解析为同一词法模块中的 `Outer.Inner.Base.show`。未匹配的外部调用保持稳定的点分目标。

Julia 限定符 `REFERENCES` 边不作为本地函数重写。这防止文件中其他地方命名为 `Base` 的定义改变限定符引用的含义。

短形式定义在递归进入其子节点之前直接派发右侧调用节点。这捕获了 `delegate(x) = greet(x)` 而不将左侧签名重新访问为自调用。

## 测试

实现在专用 Julia 测试模块中以目击的红绿循环推进：

1. 函数存根和畸形限定存根的静默失败行为；
2. 裸、引用、限定和多段运算符定义；
3. 参数化常量别名与标量常量；
4. 顶层和选定别名导入，以及别名限定调用；
5. 单行右侧调用；
6. 长短形式限定定义、局部名称碰撞和完整多段调用目标；
7. 嵌套模块、嵌套函数、最近作用域调用、宏和 testset；
8. 证明不同持久化节点、规范调用目标和下游调用方查询的 `full_build`/`GraphStore` 集成。

每个专注循环之后都运行现有 Julia fixture 测试。最终验证包括完整测试套件、Ruff、CI 使用的类型/schema/安全检查、差异检查、图谱变更/流程审查，以及所有 GitHub 检查（包括 Windows）在替换 PR 标记为就绪之前通过。