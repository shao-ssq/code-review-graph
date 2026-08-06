# 知识图谱 Schema

## 节点类型

### File（文件）
表示一个源代码文件。

| 属性 | 类型 | 说明 |
|------|------|------|
| name | string | 绝对文件路径 |
| file_path | string | 与 File 节点的 name 相同 |
| language | string | 检测到的语言（python、typescript、go 等） |
| line_start | int | 始终为 1 |
| line_end | int | 总行数 |
| file_hash | string | 文件内容的 SHA-256（用于变更检测） |

### Class（类）
表示类、结构体、接口、枚举或模块定义。

| 属性 | 类型 | 说明 |
|------|------|------|
| name | string | 类名 |
| file_path | string | 包含该类的文件 |
| line_start | int | 定义起始行 |
| line_end | int | 定义结束行 |
| language | string | 源语言 |
| parent_name | string? | 外层类（用于嵌套类） |
| modifiers | string? | 访问修饰符（public、abstract 等） |

### Function（函数）
表示函数、方法或构造函数定义。

| 属性 | 类型 | 说明 |
|------|------|------|
| name | string | 函数名 |
| file_path | string | 包含该函数的文件 |
| line_start | int | 定义起始行 |
| line_end | int | 定义结束行 |
| language | string | 源语言 |
| parent_name | string? | 外层类（用于方法） |
| params | string? | 参数列表的源代码文本 |
| return_type | string? | 返回类型注解 |
| is_test | bool | 是否为测试函数 |

### Test（测试）
与 Function 的 Schema 相同，但 `kind = "Test"` 且 `is_test = true`。识别依据：
- 名称以 `test_` 或 `Test` 开头
- 名称以 `_test` 或 `_spec` 结尾
- 文件符合测试文件模式（`test_*.py`、`*.test.ts`、`*_test.go` 等）
- 支持时的语言特定测试标记，例如常见的 Rust 测试属性

### Type（类型）
表示类型别名、接口、枚举、类结构体类型，或语言暴露的解析器特定类型结构。

| 属性 | 类型 | 说明 |
|------|------|------|
| name | string | 类型名 |
| file_path | string | 包含该类型的文件 |
| line_start | int | 定义起始行 |
| line_end | int | 定义结束行 |

### Endpoint（端点）
表示一个路由入口点的合成节点，由 Spring 增强功能为请求映射生成。通过 `HANDLES` 边与处理它的方法相连。

### Scheduler（调度器）
表示调度调用的合成节点，为 `@Scheduled` 方法生成。通过 `TRIGGERS` 边与其触发的方法相连。

### ConfigProperty（配置属性）
从 Spring `application.properties` / `application.yml` 文件中解析出的外部化配置键。值被有意丢弃——只存储键。通过 `DEPENDS_ON_CONFIG` 边与绑定它的代码相连。

## 边类型

### CALLS
一个函数调用另一个函数。

| 属性 | 类型 | 说明 |
|------|------|------|
| source | string | 调用方的限定名称 |
| target | string | 被调用函数的名称（可能是非限定名） |
| file_path | string | 调用发生的文件 |
| line | int | 调用的行号 |

### IMPORTS_FROM
一个文件从另一个模块或文件导入。

| 属性 | 类型 | 说明 |
|------|------|------|
| source | string | 导入方的文件路径 |
| target | string | 被导入的模块/路径 |
| file_path | string | 与 source 相同 |
| line | int | 导入语句的行号 |

### INHERITS
一个类继承自另一个类。

| 属性 | 类型 | 说明 |
|------|------|------|
| source | string | 子类限定名称 |
| target | string | 父类名称 |
| file_path | string | 包含子类的文件 |

### IMPLEMENTS
一个类实现一个接口（Java、C#、TypeScript、Go）。

| 属性 | 类型 | 说明 |
|------|------|------|
| source | string | 实现类 |
| target | string | 接口名称 |

### CONTAINS
结构性包含关系：文件包含类，类包含方法。

| 属性 | 类型 | 说明 |
|------|------|------|
| source | string | 容器（文件路径或类限定名称） |
| target | string | 被包含节点的限定名称 |

### TESTED_BY
一个函数被一个测试函数所测试。

| 属性 | 类型 | 说明 |
|------|------|------|
| source | string | 被测试的函数 |
| target | string | 测试函数的限定名称 |

### DEPENDS_ON
通用依赖关系（用于非特定依赖）。

### REFERENCES
对另一个符号的值级引用，通常用于函数作为值的模式，如回调映射、数组或赋值。

### INJECTS
依赖注入关系，目前用于 Java/Spring 增强功能中注入的字段和构造函数参数。

### CONSUMES / PRODUCES
由特殊解析器在源代码消费或产生命名资源时生成的数据或事件流关系。

### TEMPORAL_STUB
当检测到时间/顺序关系但无法解析为更强边类型时，由特殊解析器生成的 Temporal 依赖占位符。

### DEPENDS_ON_CONFIG
代码与外部化配置之间的绑定关系，由 Spring 增强功能为 `@ConfigurationProperties` 类以及从 `application.properties` / `application.yml` 解析出的 `ConfigProperty` 节点生成。

### HANDLES
派发点与处理它的方法之间的处理关系——Spring 请求映射将 `Endpoint` 节点绑定到其控制器方法，`@EventListener` 方法绑定到其消费的事件。

### TRIGGERS
调度调用关系，为 `@Scheduled` 方法生成，将合成的 `Scheduler` 节点链接到其触发的方法。

### PUBLISHES
事件发布关系，在代码发布 Spring 应用事件时生成。

> `OVERRIDES` 出现在影响评分表（`constants.py`）中，但目前没有任何解析器生成它。

## 限定名称格式

节点通过限定名称唯一标识：

```
# File 节点
/absolute/path/to/file.py

# 顶级函数
/absolute/path/to/file.py::function_name

# 类中的方法
/absolute/path/to/file.py::ClassName.method_name

# 嵌套类的方法
/absolute/path/to/file.py::OuterClass.InnerClass.method_name
```

## SQLite 表

```sql
-- 节点表
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL UNIQUE,
    file_path TEXT NOT NULL,
    line_start INTEGER,
    line_end INTEGER,
    language TEXT,
    parent_name TEXT,
    params TEXT,
    return_type TEXT,
    modifiers TEXT,
    is_test INTEGER DEFAULT 0,
    file_hash TEXT,
    extra TEXT DEFAULT '{}',
    community_id INTEGER,
    updated_at REAL NOT NULL
);

-- 边表
CREATE TABLE edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    source_qualified TEXT NOT NULL,
    target_qualified TEXT NOT NULL,
    file_path TEXT NOT NULL,
    line INTEGER DEFAULT 0,
    extra TEXT DEFAULT '{}',
    confidence REAL DEFAULT 1.0,
    confidence_tier TEXT DEFAULT 'EXTRACTED',
    updated_at REAL NOT NULL
);

-- 元数据表
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 流程表（v2.0）
CREATE TABLE flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    entry_point_id INTEGER NOT NULL,
    depth INTEGER NOT NULL,
    node_count INTEGER NOT NULL,
    file_count INTEGER NOT NULL,
    criticality REAL NOT NULL DEFAULT 0.0,
    path_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 流程成员表（v2.0）
CREATE TABLE flow_memberships (
    flow_id INTEGER NOT NULL,
    node_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (flow_id, node_id)
);

-- 社区表（v2.0）
CREATE TABLE communities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 0,
    parent_id INTEGER,
    cohesion REAL NOT NULL DEFAULT 0.0,
    size INTEGER NOT NULL DEFAULT 0,
    dominant_language TEXT,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- 全文搜索虚拟表（v2.0）
CREATE VIRTUAL TABLE nodes_fts USING fts5(
    name, qualified_name, file_path, signature,
    content='nodes', content_rowid='rowid',
    tokenize='porter unicode61'
);

-- Token 高效摘要表（v6）
CREATE TABLE community_summaries (
    community_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    purpose TEXT DEFAULT '',
    key_symbols TEXT DEFAULT '[]',
    risk TEXT DEFAULT 'unknown',
    size INTEGER DEFAULT 0,
    dominant_language TEXT DEFAULT ''
);

CREATE TABLE flow_snapshots (
    flow_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    entry_point TEXT NOT NULL,
    critical_path TEXT DEFAULT '[]',
    criticality REAL DEFAULT 0.0,
    node_count INTEGER DEFAULT 0,
    file_count INTEGER DEFAULT 0
);

CREATE TABLE risk_index (
    node_id INTEGER PRIMARY KEY,
    qualified_name TEXT NOT NULL,
    risk_score REAL DEFAULT 0.0,
    caller_count INTEGER DEFAULT 0,
    test_coverage TEXT DEFAULT 'unknown',
    security_relevant INTEGER DEFAULT 0,
    last_computed TEXT DEFAULT ''
);

-- 嵌入表，存储在嵌入数据库中
CREATE TABLE embeddings (
    qualified_name TEXT PRIMARY KEY,
    vector BLOB NOT NULL,
    text_hash TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'unknown'
);
```

索引覆盖限定名称、文件路径、节点类型、边的 source/target/kind、社区、流程关键度、风险评分、复合边查找索引以及复合边 upsert 索引。
