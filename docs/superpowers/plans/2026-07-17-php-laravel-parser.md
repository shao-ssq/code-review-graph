# PHP 与 Laravel 解析器移植实现计划

> **执行：** 严格遵循红/绿/重构顺序。在前一个专注测试变绿之前，不要合并界面。

**目标：** 将可行的 PHP/Laravel 行为从已关闭的 PR #252 移植到当前 `main`，同时保留更强的现有 PHP 调用/导入，并添加所需的正确性、仓库边界和进程池覆盖。

**架构：** 最小化扩展通用 PHP 语法表。将 Composer 解析保留在有界不可变辅助函数中。通过专用轻量级分支解析 Blade。在独立的 PHP AST 后处理通道中添加 Laravel 边，使通用递归提取器保持不变。

**来源归属：** 功能提交必须包含 `Co-authored-by: Minidoracat <minidora0702@gmail.com>`。

---

## 任务 1：PHP 语法和 PHP 专用流程入口点

**文件：**

- 修改：`tests/test_multilang.py`
- 修改：`tests/test_flows.py`
- 修改：`code_review_graph/parser.py`
- 修改：`code_review_graph/flows.py`

1. 为 trait 和枚举 Class 节点、`new` CALLS、PHP extends/implements 目标，以及不变的现有作用域/成员调用格式化添加专注测试。
2. 添加流程测试，证明被调用的 PHP `boot`、`register` 和 `__invoke` 方法是入口点，而相同名称的 Python 方法不是。
3. 运行两个专注命令，确认新断言因缺少行为而失败：
   - `uv run --frozen --no-sync pytest -q tests/test_multilang.py -k PHP`
   - `uv run --frozen --no-sync pytest -q tests/test_flows.py -k php_entry`
4. 仅添加 PHP 表、对象创建名称、基类子句和语言范围流程变更。
5. 重新运行专注测试，仅在绿色时重构。

## 任务 2：形状安全、仓库有界的 Composer PSR-4

**文件：**

- 创建：`tests/test_php_laravel.py`
- 修改：`code_review_graph/parser.py`

1. 构建临时 Composer 仓库，为以下情况添加失败测试：
   - 正常 PSR-4 解析；
   - 最长前缀选择；
   - 一个前缀的多个目录；
   - 合并 `autoload` 和 `autoload-dev` 目录；
   - 畸形文档/节/`psr-4`/条目形状；
   - 调用方和映射路径在配置仓库之外；
   - `..`、绝对路径和符号链接转义；
   - Composer 没有匹配文件时的兼容性回退。
2. 运行：`uv run --frozen --no-sync pytest -q tests/test_php_laravel.py -k composer`，确认失败是缺少解析的失败，而非 fixture 错误。
3. 在 `CodeParser` 上存储解析后的仓库根目录。
4. 添加有界 Composer 祖先搜索和不可变映射加载器。验证 JSON 形状，保留所有目录，合并节，规范化前缀，按最长优先排序，并要求解析路径保留在根目录内。
5. 在现有 PHP 祖先回退之前集成 Composer。
6. 重新运行专注测试。

## 任务 3：Composer 缓存和工作进程行为

**文件：**

- 修改：`tests/test_php_laravel.py`
- 修改：`code_review_graph/parser.py`

1. 添加失败缓存测试，证明：
   - 独立解析器实例复用不变的 Composer 文件；
   - 变更的 stat 键重新加载它；
   - 仓库不共享缓存的映射。
2. 添加以 Composer 路径、仓库根目录、`mtime_ns` 和大小为键的有界进程本地缓存，仅返回不可变数据。
3. 重新运行 Composer 测试。

## 任务 4：带注释和转义的 Blade 解析

**文件：**

- 修改：`tests/test_php_laravel.py`
- 修改：`code_review_graph/parser.py`

1. 为复合扩展名检测、File 节点形状、`@extends`/`@include`/`@component` 导入、`@livewire` 引用、精确行号、Blade 注释抑制、`@@` 转义抑制、未终止注释、无效 UTF-8 和普通 PHP 隔离添加失败测试。
2. 运行：`uv run --frozen --no-sync pytest -q tests/test_php_laravel.py -k blade`。
3. 添加 Blade 检测、保留换行符/偏移的注释遮盖，以及负向后视指令匹配器。
4. 重新运行专注测试。

## 任务 5：证据门控的 Laravel 语义边

**文件：**

- 修改：`tests/test_php_laravel.py`
- 修改：`code_review_graph/parser.py`

1. 为 Route facade 别名/FQCN、控制器导入别名/FQCN、Eloquent Model 别名/FQCN、关系目标、命名空间块和 Composer 限定图谱目标添加正向失败测试。
2. 为无关 `Route` 类、缺少 facade 导入、动态路由处理器、非 Model 类、错误接收者、类似命名方法和非 `::class` 参数添加负向失败测试。
3. 断言每个正向案例仍具有 `main` 已产生的精确通用 CALLS 目标，没有重复的通用边。
4. 运行：`uv run --frozen --no-sync pytest -q tests/test_php_laravel.py -k laravel`。
5. 添加带别名/分组导入的命名空间局部 PHP 导入绑定。
6. 添加独立的 PHP 语义 AST 后处理通道。尽可能通过 Composer 解析语义目标；否则发出稳定的短目标。
7. 重新运行专注测试并检查边列表是否有重复。

## 任务 6：串行/进程池对等性

**文件：**

- 修改：`tests/test_php_laravel.py`

1. 添加包含至少八个已追踪 PHP 文件的 Composer 项目。
2. 用 `CRG_SERIAL_PARSE=1` 构建一次，用真实进程执行器构建一次。断言无错误且归一化的节点/边相同。
3. 当 OS 信号量访问需要时，在受限沙箱之外运行进程测试：`uv run --frozen --no-sync pytest -q tests/test_php_laravel.py -k process_pool`。

## 任务 7：文档和来源归属

**文件：**

- 修改：`README.md`
- 修改：`docs/FEATURES.md`

1. 记录 Composer/Blade/Laravel 支持，不声称仅启发式的 Route 或 Eloquent 检测。
2. 运行 `git diff --check`。
3. 使用 Minidoracat 共同作者 trailer 提交实现和测试。

## 任务 8：验证、图谱审查和发布

1. 运行专注测试：`uv run --frozen --no-sync pytest -q tests/test_php_laravel.py tests/test_multilang.py tests/test_flows.py tests/test_incremental.py`。
2. 运行所有本地 CI 等效门禁：
   - `uv run --frozen --no-sync ruff check code_review_graph/`
   - `uv run --frozen --no-sync --with mypy --with types-networkx mypy code_review_graph/ --ignore-missing-imports --no-strict-optional`
   - `uv run --frozen --no-sync --with 'bandit[toml]' bandit -r code_review_graph/ -c pyproject.toml`
   - `.github/workflows/ci.yml` 中 schema 同步比较的可移植本地等效版本
   - `uv run --frozen --no-sync pytest --tb=short -q --cov=code_review_graph --cov-report=term-missing --cov-fail-under=65`
3. 使用仓库图谱检测变更风险、受影响流程和测试覆盖；检查任何高风险上下文。
4. 获取并变基最新的 `origin/main`，重新运行专注/完整门禁，确认 `git diff --check`。
5. 推送 `codex/port-php-laravel`，开启草稿 PR（CI 仅在推送到 `main` 或 pull request 时运行），等待完整 PR CI 通过，然后标记为就绪。
6. 不要修改源 PR #252。仅在就绪 PR 和必需 CI 确认后更新/关闭 bead `crg-erd.2.1`。