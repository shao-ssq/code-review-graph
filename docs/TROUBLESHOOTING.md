# 故障排除

## 常见安装/配置问题快速参考

四类问题占了大多数支持请求，请优先检查以下内容：

### 1. `.claude/settings.json` 中出现 `Hooks use a matcher + hooks array` 错误

**你使用的是 v2.2.3 之前的版本。** v2.2.1 和 v2.2.2 附带了错误的 Hook Schema——扁平的 `{matcher, command, timeout}` 条目缺少必需的嵌套 `hooks: []` 数组，超时单位为毫秒而非秒，以及一个不是真实 Claude Code 事件的 `PreCommit` 事件。PR #208（在 v2.2.3 中发布）重写了生成器以生成正确的 v1.x+ Schema。

**修复方法：**

```bash
pip install --upgrade code-review-graph   # → v2.2.4 或更新版本
cd /path/to/your/project
code-review-graph install                 # 重写 .claude/settings.json
```

重新安装会将整个错误的 `hooks` 块替换为新的嵌套格式，并将真实的 git pre-commit hook 放入通过 `git rev-parse --git-path hooks` 解析的 hooks 目录——通常是 `.git/hooks/pre-commit`，但也会正确处理关联的 worktree 和 `core.hooksPath`（husky）配置。v2.2.3+ 中"提交前检查"就在那里，而不在 Claude Code 设置里。

有效的 Claude Code Hook 事件：`PreToolUse`、`PostToolUse`、`UserPromptSubmit`、`Stop`、`SubagentStop`、`SessionStart`、`SessionEnd`、`PreCompact`、`Notification`。不存在 `PreCommit`。

### 2. `pip install` 后出现 `code-review-graph: command not found`

`pip install` 将控制台脚本放入了不在 `$PATH` 上的 `bin/` 目录。按推荐顺序，有四种修复方式：

**方式 1 —— 使用 `pipx`（最简洁）：**

```bash
pip uninstall code-review-graph
pipx install code-review-graph
```

`pipx` 将 CLI 工具安装在独立的 venv 中。如果之后仍找不到命令，运行 `pipx ensurepath` 或将 `~/.local/bin` 添加到 PATH。

**方式 2 —— 使用 `uvx`（无需安装）：**

```bash
uvx code-review-graph install
uvx code-review-graph build
```

**方式 3 —— 作为 Python 模块运行（始终有效）：**

```bash
python -m code_review_graph install
python -m code_review_graph build
```

**方式 4 —— 手动修复 PATH：**

```bash
pip show code-review-graph | grep Location
# 找到同级的 bin/ 目录；macOS 用户安装通常在
# ~/Library/Python/3.X/bin。添加到 shell 配置：
echo 'export PATH="$HOME/Library/Python/3.12/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### 3. code-review-graph 是项目级还是用户级的？

**两者都是** —— 共四个部分，各有不同作用域：

| 部分 | 作用域 | 位置 |
|------|--------|------|
| Python 包 | 用户级 | 通过 `pip`/`pipx`/`uvx` 安装一次 |
| 图数据库 | 项目级 | 每个项目内的 `.code-review-graph/graph.db` |
| MCP 服务器配置（`.mcp.json`）| 项目级 | Claude Code 为每个项目启动一个 MCP 服务器，`cwd=<project>` |
| 多仓库注册表 | 用户级 | `~/.code-review-graph/registry.json`（仅用于 `cross_repo_search`） |

**简言之**：安装工具**一次**，然后在**每个**需要图谱感知审查的项目中运行 `code-review-graph install && code-review-graph build`。

### 4. 使用 venv？必须手动更新 `settings.json`

`.claude/settings.json` 中的 Claude Code Hooks 和 MCP 工具路径**在安装时硬编码**。如果在运行 `code-review-graph install` 之后切换到（或创建）虚拟环境，这些路径仍指向旧的解释器，服务器将静默失败或使用错误的 Python。

**修复方法 —— 更新 `.mcp.json` 中的 `command`/`args` 以及 `.claude/settings.json` 中的 hook 命令以匹配你的 venv：**

```json
// .mcp.json —— 指向你 venv 的 Python 或 venv 内的 uvx
{
  "mcpServers": {
    "code-review-graph": {
      "command": "/path/to/your/venv/bin/uvx",
      "args": ["code-review-graph", "serve"]
    }
  }
}
```

或者在激活的 venv 中重新运行 `code-review-graph install` 以重新生成路径：

```bash
source .venv/bin/activate          # 先激活 venv
code-review-graph install          # 重写 .mcp.json 和 hook 路径
```

然后完全退出并重新打开 Claude Code 以加载新配置。

### 5. "我构建了图谱，但新会话中 Claude Code 看不到它"

最可能的原因（按优先级排列）：

1. **在 `install` 后没有重启 Claude Code。** Claude Code 在启动时读取 `.mcp.json`——如果你在一个会话中运行了 `install`，需要完全退出并重新打开 Claude Code 以注册 MCP 服务器。
2. **新会话的 `cwd` 是不同的目录。** MCP 服务器以 `cwd=<project>` 启动，从那里读取 `.code-review-graph/graph.db`。如果你的新会话在父文件夹或不同项目中打开，将找不到你构建的图谱。
3. **运行了 `build` 但没有运行 `install`。** `build` 创建 `graph.db`；`install` 才是通过 `.mcp.json` 向 Claude Code 注册 MCP 服务器的步骤。两者都需要。
4. **MCP 服务器启动时崩溃。** 在 Claude Code 中运行 `/mcp` 查看服务器状态，或在 macOS 上检查 `~/Library/Logs/Claude/mcp*.log`。

**快速检查清单：**

```bash
cd /path/to/your/project
code-review-graph status    # 应显示构建图谱的 Files/Nodes/Edges
ls .mcp.json                # 应存在
cat .mcp.json               # 应引用 `code-review-graph serve`
# 然后：完全退出 Claude Code 并在此项目中重新打开
```

如果 `status` 显示了图谱但新会话的 `/mcp` 中没有列出 `code-review-graph`，说明 `.mcp.json` 不在会话的 `cwd` 中——在正确的项目根目录重新运行 `code-review-graph install`。

---

## 数据库锁定错误
图谱使用 SQLite WAL 模式。如果出现锁定错误：
- 确保一次只运行一个构建进程
- 数据库会自动恢复；直接重试即可
- 如果损坏，删除 `.code-review-graph/graph.db-wal` 和 `.code-review-graph/graph.db-shm`

## 大型仓库（>10k 文件）
- 首次构建可能需要 30-60 秒
- 后续增量更新速度很快（在约 3,000 文件的仓库上约 2.5 秒，Hook 路径）
- 在 `.code-review-graphignore` 中添加更多忽略模式：
  ```
  generated/**
  vendor/**
  *.min.js
  ```

## 构建后节点缺失
- 检查文件的语言是否受支持（参见 [FEATURES.md](FEATURES.md)）
- 检查文件是否被忽略模式匹配
- 使用 `full_rebuild=True` 强制完整重新解析

## 图谱似乎过时
- Hook 在编辑/提交时自动更新
- 如果过时，手动运行 `/code-review-graph:build-graph`
- 检查 `.claude/settings.json` 中是否配置了 Hook（重新运行 `code-review-graph install` 以重新生成）

## 嵌入功能不工作
- 安装方式：`pip install "code-review-graph[embeddings]"`
- 运行 `embed_graph_tool` 计算向量
- 首次嵌入运行会下载模型（约 90MB，仅一次）

## MCP 服务器无法启动
- 验证 `uv` 已安装（`uv --version`；通过 `pip install uv` 或 `brew install uv` 安装）
- 检查 `uvx code-review-graph serve` 是否无错误运行
- 如果使用自定义 `.mcp.json`，确保它使用 `"command": "uvx"` 和 `"args": ["code-review-graph", "serve"]`
- 重新运行 `code-review-graph install` 以重新生成配置

## Windows / WSL

- 如果 `daemon status` 崩溃并显示 WinError 87（#511）或 CLI `detect-changes` 在 Windows 上映射 0 个函数（#528），请升级到 v2.3.6+——两者都已在该版本修复
- 向 MCP 工具传递 `repo_root` 时使用正斜杠
- 在 WSL 中，确保在 WSL 内安装 `uv`（而非 Windows 版本）：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- 如果安装后找不到 `uv`，将 `~/.cargo/bin` 添加到 PATH
- 由于文件系统事件限制，WSL1 上的文件监听（`code-review-graph watch`）可能有延迟；推荐使用 WSL2
- 在 Windows 原生（非 WSL）环境中，可能需要启用长路径支持：`git config --system core.longpaths true`

## 社区检测需要 igraph

- 安装方式：`pip install "code-review-graph[communities]"`
- 没有 igraph 时，社区检测回退到基于文件的分组（精度较低但可用）

## 带 LLM 摘要的 Wiki 生成

- 安装方式：`pip install "code-review-graph[wiki]"`
- 需要运行中的 Ollama 实例以提供 LLM 摘要
- 没有 Ollama 时，Wiki 页面仅包含结构信息（无文字摘要）

## 可选依赖组

如果工具返回 ImportError，请安装对应的可选组：
- `pip install "code-review-graph[embeddings]"` —— 语义搜索
- `pip install "code-review-graph[google-embeddings]"` —— Google Gemini 嵌入
- OpenAI 兼容和 MiniMax 嵌入使用标准库 HTTP 客户端，只需设置相应的环境变量
- `pip install "code-review-graph[communities]"` —— 基于 igraph 的社区检测
- `pip install "code-review-graph[enrichment]"` —— 通过 Jedi 进行 Python 调用解析增强
- `pip install "code-review-graph[eval]"` —— 评估基准（matplotlib）
- `pip install "code-review-graph[wiki]"` —— Wiki LLM 摘要（ollama）
- `pip install "code-review-graph[all]"` —— 安装所有可选依赖
