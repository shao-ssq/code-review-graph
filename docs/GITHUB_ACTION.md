# GitHub Action：带风险评分的 PR 审查

code-review-graph 附带一个复合 GitHub Action（仓库根目录的 `action.yml`），它会在每个 Pull Request 上发布带风险评分的图谱感知审查评论——类似托管的 AI 审查机器人（Greptile 风格），但分析是**本地优先**的：知识图谱完全在你的 CI Runner 上构建和查询，不会将任何源代码发送到任何外部服务。

每次 PR 运行时，该 Action 会：

1. 从 PyPI 安装 `code-review-graph`。
2. 恢复缓存的 `.code-review-graph/` SQLite 图谱（或在缓存未命中时从头构建），并增量重新解析 PR 变更的文件。
3. 运行 `code-review-graph detect-changes --base origin/<base-branch>` 以获取带风险评分的函数、受影响的执行流程和测试缺口。
4. 渲染 Markdown 报告（通过 `scripts/render_pr_comment.py`）并更新单个固定 PR 评论——每次推送都更新同一条评论，PR 线程不会被刷屏。
5. 可选地在整体风险评分超过阈值时使作业失败（`fail-on-risk`）。

## 快速开始（外部仓库）

```yaml
# .github/workflows/code-review-graph.yml
name: code-review-graph

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: tirth8205/code-review-graph@v2.3.6
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

这就是全部配置。Actions 提供的默认 `GITHUB_TOKEN` 已足够——无需 PAT、无需 API Key、无需第三方服务。

自托管 Runner 必须是 `2.327.1` 或更高版本。复合 Action 使用基于 Node 24 的 GitHub Actions，包括 `actions/setup-python@v6`、`actions/cache@v6` 以及推荐的 `actions/checkout@v7`。

将审查变为合并门控：

```yaml
      - uses: tirth8205/code-review-graph@v2.3.6
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          fail-on-risk: high
```

## 输入参数

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `github-token` | 是 | — | 通过 GitHub API 发布固定 PR 评论所用的令牌。当作业具有 `pull-requests: write` 权限时，工作流的默认 `GITHUB_TOKEN` 即可。 |
| `comment` | 否 | `true` | 发布（并持续更新）固定 PR 评论。设为 `false` 可仅运行分析/门控而不评论。 |
| `fail-on-risk` | 否 | `none` | 整体风险评分达到指定级别时使作业失败：`none`（从不失败）、`high`（风险 ≥ 0.70）、`critical`（风险 ≥ 0.85）。 |
| `python-version` | 否 | `3.12` | 运行 code-review-graph 使用的 Python 版本（支持 3.10+）。 |

## 输出

| 输出 | 说明 |
|------|------|
| `comment-file` | Runner 本地渲染的 Markdown 报告路径。当 `comment: false` 时使用，由单独的受信工作流发布。 |

### 风险级别

`detect-changes` 生成 0.0–1.0 的整体风险评分（变更函数的最大值；评分因子见 `code_review_graph/changes.py:compute_risk_score`：流程参与度、社区跨越、测试覆盖、安全敏感名称、调用方数量）。Action 将其映射到以下级别：

| 级别 | 评分 |
|------|------|
| low | < 0.40 |
| medium | 0.40 – 0.69 |
| high | 0.70 – 0.84 |
| critical | ≥ 0.85 |

## 评论内容

- **整体风险**评分和级别，以及变更函数数、受影响流程数和测试缺口数。
- **带风险评分的变更**——按风险排序的顶部变更符号表格，含 file:line 位置和测试覆盖状态。
- **受影响的执行流程**——变更触及的入口点流程，按关键度排序。
- **测试缺口**——没有直接测试覆盖的变更函数。
- **Token 节省**——与完整读取每个变更文件相比，图谱支持的报告节省的 Token 数。这与 CLI Token Savings 面板显示的 `context_savings` 估算相同（`chars / 4` 近似，标注 `estimated: true`——校准方法参见 [REPRODUCING.md](REPRODUCING.md)）。
- `Powered by code-review-graph` 页脚。

评论以隐藏的 HTML 标记开头（`<!-- code-review-graph-report -->`）。Action 每次运行时通过 `gh api` 查找该标记，并 PATCH 已有的评论而不是新建（"固定"评论）。

## 缓存行为

Action 使用 `actions/cache` 缓存 `.code-review-graph/` 目录（SQLite 图谱数据库）：

- **键**：`code-review-graph-schema9-<runner.os>-<hashFiles(lockfiles)>`，其中 lockfile 哈希覆盖常见的 Python/JS/Go/Rust/Ruby/PHP lockfile（`uv.lock`、`poetry.lock`、`requirements*.txt`、`package-lock.json`、`go.sum`、`Cargo.lock`……）。
- **Schema 段**：`schema9` 跟踪数据库 Schema 版本（`code_review_graph/migrations.py` 中的 `LATEST_VERSION`）。Schema 变更时会更新，以避免跨不兼容版本恢复过时缓存。
- **恢复键**：回退到同一 OS 和 Schema 的任何缓存，因此 lockfile 变更时仍能复用之前的图谱。
- **命中缓存时**：Action 运行 `code-review-graph update --base origin/<base-branch>`，仅重新解析与 PR base ref 不同的文件。如果恢复的数据库不可用，则回退到全量 `build`。
- **未命中缓存时**：运行全量 `code-review-graph build`（一次性成本；后续 PR 运行为增量）。

## 安全说明

- **令牌作用域**：直接评论需要 `contents: read`（用于 checkout）和 `pull-requests: write`（用于发布评论）。在分叉安全的拆分配置中，分析工作流只需 `contents: read`；受信评论者只需 `actions: read` 和 `pull-requests: write`。在每个工作流中精确授予这些权限。
- **本地优先**：分析完全在 Runner 上运行。不会有任何代码、差异或元数据离开 GitHub 基础设施；没有外部 API、账号或密钥。
- **不受信任的输入**：所有动态值（`github.base_ref`、PR 编号、Action 输入）通过环境变量传递给脚本，从不内插到 shell 命令中。Markdown 渲染器在符号名称和文件路径到达评论正文之前会转义表格/标记字符并去除控制字符，这是在服务器端 `_sanitize_name()` 净化之外的额外防护。
- **固定版本**：从其他仓库使用该 Action 时，将 `uses:` 固定到发布标签或提交 SHA，而非 `@main`。
- **Fork PR**：来自 Fork 的 `pull_request` 运行只有只读 `GITHUB_TOKEN`，因此无法直接发布评论。使用不带权限的 `pull_request` 工作流加 `comment: false`，将 `comment-file` 作为制品上传，并从单独的受信 `workflow_run` 工作流发布。参见 [`.github/workflows/pr-review.yml`](../.github/workflows/pr-review.yml) 和 [`.github/workflows/pr-review-comment.yml`](../.github/workflows/pr-review-comment.yml)。GitHub 从默认分支加载 `workflow_run` 工作流，因此受信评论部分只在该工作流合并后才生效。受信工作流必须验证源事件和分析提交，仅在 `runner.temp` 下提取，限制并验证制品，并在发布前添加自己的固定标记。避免对 PR 代码进行 checkout 的 `pull_request_target`，因为它可能以特权令牌执行不受信任的代码（[详情](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/)）。

## 自我使用（Dogfooding）

本仓库通过 [`.github/workflows/pr-review.yml`](../.github/workflows/pr-review.yml) 在自己的 PR 上运行该 Action，该工作流在没有写权限的情况下运行本地 `action.yml` 并上传渲染的报告。受信 [`pr-review-comment.yml`](../.github/workflows/pr-review-comment.yml) 工作流验证该制品并发布固定评论，而不 checkout 或执行 PR 控制的代码。

## 渲染脚本

Markdown 渲染和风险门控逻辑位于 [`scripts/render_pr_comment.py`](../scripts/render_pr_comment.py)（仅使用标准库，在 `tests/test_action_render.py` 中有单元测试），而非内联在 YAML 中，因此可以被测试和复用：

```bash
code-review-graph detect-changes --base origin/main | \
  python scripts/render_pr_comment.py            # 将 Markdown 输出到 stdout

python scripts/render_pr_comment.py --input report.json \
  --fail-on-risk high --quiet                    # 仅门控：超出时以退出码 3 退出
```
