# PHP 与 Laravel 解析器移植设计

## 背景

Pull Request #252 包含有用的 PHP、Composer、Blade 和 Laravel 解析工作，但其分支早于 `main` 上已有的更强 PHP 调用和 `use` 处理。本次移植仅采纳剩余行为，并保留当前通用解析器路径。

源实现归功于 Minidoracat（`minidora0702@gmail.com`）。移植提交将保留该归属。

## 目标

- 识别 PHP trait、枚举、对象创建和继承/接口子句，而不改变现有 PHP 调用或导入格式化。
- 将 PHP 的 `boot`、`register` 和 `__invoke` 方法视为语言范围的入口点。现有的通用 `handle`、`up` 和 `down` 行为保持不变。
- 通过 Composer PSR-4 映射安全且确定性地解析 PHP 命名空间。
- 解析 Blade 模板引用，同时忽略 Blade 注释和转义指令。
- 仅在 AST 包含明确的框架和接收者证据时，才添加 Laravel Route 到控制器和 Eloquent 关系边。
- 保持串行和进程池构建在行为上等效。

## 非目标

- 替换现有的 PHP 解析器或导入解析器。
- 仅凭方法名推断 Laravel 语义。
- 支持所有 Blade 指令或动态路由目标。
- 解析仓库外的 Composer 依赖。
- 重新打开、合并或以其他方式修改源 PR #252。

## 设计

### PHP 语法和入口点

现有 Tree-sitter 表新增 PHP `trait_declaration`、`enum_declaration` 和 `object_creation_expression`。当前 PHP `_get_call_name` 分支仅为对象创建扩展，`_get_bases` 新增 PHP `base_clause` 和 `class_interface_clause` 处理。

流程检测新增用于 `boot`、`register` 和 `__invoke` 的 PHP 专用模式集。已是通用的名称不会重复。

### Composer PSR-4 解析

`CodeParser` 记录其解析的仓库根目录。Composer 查找从调用方目录开始，止于该根目录（含）。如果未提供根目录，解析器使用最近的 VCS 根目录；没有安全边界时，不会爬升到调用方目录以上。

仅当每个容器具有预期的 JSON 形状时才接受 Composer 数据：

- 文档、`autoload` 和 `autoload-dev`：对象；
- `psr-4`：对象；
- 前缀：字符串；
- 映射路径：字符串或字符串列表。

两个节的映射合并时不覆盖。所有有效的映射目录按声明顺序保留。前缀被规范化并按最长优先搜索。解析后的基目录和目标文件必须在符号链接解析后仍留在仓库内；离开仓库的绝对路径和 `..` 转义将被忽略。

解析后的映射是不可变的。有界进程本地缓存以 Composer 路径、仓库根目录、文件修改时间和大小为键。这使串行解析器和长寿命进程池工作进程能够复用配置，而不产生陈旧的跨仓库结果。

当前的祖先查找解析器作为 Composer 解析后的兼容回退保留。

### Blade 模板

复合 `.blade.php` 名称在普通 `.php` 后缀处理之前检测。专用的轻量级解析器生成一个 File 节点和：

- `IMPORTS_FROM`，用于 `@extends`、`@include` 和 `@component`；
- `REFERENCES`，用于 `@livewire`。

Blade 注释跨度（`{{-- ... --}}`）被遮盖，同时保留换行符和字符偏移。指令匹配器要求未转义的 `@`，因此 `@@include` 和等效转义形式不生成边。边的行号因此与原始源保持对齐。

### Laravel 语义证据

Laravel 分析作为独立的 PHP AST 后处理通道在通用提取之后运行。它从不消耗 Tree-sitter 节点，也从不重建普通的 CALLS 边。这保留了当前目标，如 `Route::get`、`hasMany` 和所有嵌套调用。

后处理通道构建命名空间局部类导入绑定（包括别名和分组导入），并追踪外层类。

仅在以下条件满足时生成 Route 控制器 CALLS 边：

1. 作用域调用是支持的路由动词；
2. 其接收者是从 `Illuminate\\Support\\Facades\\Route` 导入的别名，或使用了该完整类名；
3. 处理器具有静态数组形式 `[Controller::class, 'method']`。

仅在以下条件满足时生成 Eloquent REFERENCES 边：

1. 调用使用支持的关系方法；
2. 接收者恰好是 `$this`；
3. 外层类扩展了已导入/完全限定的 `Illuminate\\Database\\Eloquent\\Model`；
4. 第一个相关参数是 `Target::class`。

导入或完全限定的控制器/模型名称通过 Composer 解析。当目标文件存在时，语义边使用图谱真实的限定名形状（路由为 `file.php::Class.method`，模型为 `file.php::Class`）。否则保留稳定的短语义目标，而不是凭空发明文件名。

## 测试

每个界面均以红色优先方式实现：

1. PHP trait、枚举、`new`、基类子句和语言范围入口点。
2. Composer 畸形形状、最长前缀、多目录映射、`autoload-dev` 合并、缓存失效/复用、仓库遍历、绝对路径和符号链接转义。
3. Blade 指令、行号、注释、转义指令、畸形输入和普通 PHP 隔离。
4. Laravel 正向别名/FQCN 情况和负向无关 `Route`、非模型关系、错误接收者、动态处理器和缺少导入情况。
5. 拥有足够文件进入并行路径的 Composer PHP 项目上的串行/进程池对等性。

专注测试之后，完整套件、Ruff、schema 生成检查、图谱变更审查和 GitHub CI 必须通过，才能开启就绪 PR。