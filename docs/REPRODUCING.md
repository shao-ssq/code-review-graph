# 复现基准测试

本文档提供了复现 README 和 `diagrams/` 中所有基准测试数字的精确命令。在不同机器、不同日期按照以下步骤操作的两个人，应该能产生相同的数字（浮点舍入以内）。

如果你得到了不同的数字，那是一个 bug——请提交 Issue。

## 验证"节省 Token 数"

CLI 的 `Token Savings` 面板使用标记为 `estimated: true` 的 `chars / 4` 近似值，而非模型专用分词器。这个近似值设计为既快速（无需加载模型，无需推理）又保守。

### 如何与真实分词器对比验证

```bash
pip install tiktoken
code-review-graph detect-changes --brief --verify
```

面板会增加一行 `Verified (tiktoken)`，显示使用 OpenAI 的 `cl100k_base` 分词器（GPT-4 系列）做的同一计算。如果估算误差明显，你会立即看到：

```text
┌───────────────────────── Token Savings ─────────────────────────┐
│ Full context would be:     12,921 tokens                        │
│ Graph context used:           762 tokens                        │
│ Saved:                     12,159 tokens (~94%)                 │
│ Verified (tiktoken):       10,835 tokens (~93%)  [11,611 → 776] │
│ Breakdown: Functions 244 · Tests 191 · Risk 244 · Other 83      │
└─────────────────────────────────────────────────────────────────┘
```

### 校准结果（已提交）

对来自 6 个测试仓库的 222 个文件 / 2.2 MB 混合源代码（Python、JS、TS、Go、Rust、RST、MD）进行了一次性校准：

| 仓库 | 样本文件 | 字节数 | chars/4 估算 | tiktoken 真实值 | 估算/真实比 |
|---|---:|---:|---:|---:|---:|
| flask | 46 | 470,179 | 117,559 | 109,969 | 1.069 |
| fastapi | 38 | 156,224 | 39,072 | 34,897 | 1.120 |
| gin | 30 | 471,793 | 117,962 | 132,296 | 0.892 |
| express | 23 | 296,805 | 74,207 | 83,575 | 0.888 |
| httpx | 38 | 254,184 | 63,556 | 62,909 | 1.010 |
| code-review-graph | 47 | 539,206 | 134,820 | 120,760 | 1.116 |
| **总计** | **222** | **2,188,391** | **547,176** | **544,406** | **1.005** |

`chars / 4` 在总量上与真实 GPT-4 Token 差距在 **+0.5%** 以内。单个仓库的偏差在 **-11%**（gin：大量短 Go 标识符）到 **+12%**（fastapi：大量文档字符串和类型提示）之间，但**比率**趋于稳定，因为除法两侧的偏差方向相同。

使用本提交的 `code_review_graph/context_savings.py:verify_with_tiktoken` 中的代码片段可复现校准，或在任意提交上内联运行 `--verify` 标志。

## 什么是确定性的，什么不是

| 可复现 | 原因 |
|---|---|
| Tree-sitter 解析 | 输入字节的纯函数 |
| 节点/边数量 | 以 `qualified_name` 为键的确定性 upsert |
| FTS5 BM25 评分 | 确定性 |
| 通过 `all-MiniLM-L6-v2` 在 CPU 上的嵌入 | 模型权重通过 SHA 在 HuggingFace 缓存中固定 |
| Leiden 社区 ID | 已播种——`communities.py` 中的 `_LEIDEN_SEED=42`，通过 `CRG_LEIDEN_SEED` 环境变量覆盖 |
| `naive_corpus_tokens` | 对固定的 git checkout 是确定性的 |
| 在固定 SHA 的 `git clone` | 确定了真实来源的字节流 |

曾经使其**不**可复现的因素（现已修复）：

- 每个 `code_review_graph/eval/configs/*.yaml` 中的 `commit: HEAD`——已替换为每个仓库的固定最新测试提交 SHA
- `git clone --depth 50` 在固定 SHA 超出浅克隆窗口时静默回退到错误提交——现在使用完整克隆，带有显式 `returncode` 检查
- Leiden 以未播种的 RNG 运行——现已播种
- `nextjs.yaml` 是错误命名的配置，评估此仓库——重命名为 `code-review-graph.yaml`
- FTS5 已创建但评估框架的 `full_build` 调用从未填充——`code_review_graph/eval/runner.py` 现在直接调用 `postprocessing.run_post_processing`

## 前提条件

- Python 3.10 或更新版本
- PATH 中有 `git`
- 网络访问（约 600 MB 用于克隆 6 个上游仓库）
- 约 3 GB 可用磁盘
- 嵌入步骤需要：`torch` + `sentence-transformers` 额外约 700 MB

## 步骤 1 —— 安装正确的附加依赖

```bash
git clone https://github.com/tirth8205/code-review-graph
cd code-review-graph

# eval 附加：pyyaml + matplotlib（matplotlib 仅 `--report` 时需要）
# embeddings 附加：sentence-transformers + numpy
uv sync --extra eval --extra embeddings     # 或：pip install -e ".[eval,embeddings]"
```

## 步骤 2 —— 运行正式评估

此步骤在固定 SHA 克隆 6 个上游仓库，为每个仓库构建完整图谱（解析器 + 跨文件解析器 + 签名 + FTS5 + 流程 + Leiden 社区），然后运行 `token_efficiency`、`impact_accuracy`、`agent_baseline` 和 `multi_hop_retrieval` 基准测试。

```bash
uv run code-review-graph eval \
  --benchmark token_efficiency,impact_accuracy,agent_baseline,multi_hop_retrieval
```

失败语义（适用于所有基准测试）：抛出的工具调用**不是**测量结果。该行保留在 CSV 中，`status=error` 用于取证，但被排除在所有聚合之外。（两个历史 bug 使失败看起来像胜利：抛出的 `get_review_context` 产生 `graph_tokens=0` 和比率 `naive/1`，而抛出的 `analyze_changes` 静默设置 `predicted = changed`，保证召回率 1.0。两者均已修复；回归测试在 `tests/test_eval.py` 中。）

M1/M2 Mac 的预期运行时间：构建阶段约 8–15 分钟，加上每个基准测试数秒。

输出：

- `evaluate/test_repos/{express,fastapi,flask,gin,httpx,code-review-graph}/`
- `evaluate/test_repos/<name>/.code-review-graph/graph.db`
- `evaluate/results/<name>_<benchmark>_<date>.csv`

## 步骤 3 —— 生成嵌入（独立基准测试必需）

独立 token 基准测试附带 5 个硬编码的自然语言问题。没有嵌入，混合搜索无法匹配它们，基准测试会静默返回 0× 缩减比率（会打印响亮警告）。

```bash
for repo in express fastapi flask gin httpx code-review-graph; do
  uv run code-review-graph embed --repo "evaluate/test_repos/$repo"
done
```

预期运行时间：总计 2–5 分钟。向量存储在同一 `graph.db` 中。

## 步骤 4 —— 生成图表（可选）

图表可以在本地重新生成，前提是安装了 `matplotlib`（包含在 `eval` 附加中）。

```bash
uv run code-review-graph eval --benchmark token_efficiency --report
```

此命令将图表写入 `evaluate/diagrams/`。标准 PNG 的文件名格式为 `<benchmark>_<date>.png`。README 中引用的图表是从此处生成的截图。

## 规范数字（当前发布）

以下数字是使用上述步骤并在上述固定 SHA 的 6 个测试仓库上重现的。

### Token 效率

| 仓库 | 朴素 tokens | 图谱 tokens | 节省 | 比率 |
|---|---:|---:|---:|---:|
| express | 95,023 | 1,824 | 93,199 | 52.1× |
| fastapi | 34,294 | 1,203 | 33,091 | 28.5× |
| flask | 41,867 | 1,156 | 40,711 | 36.2× |
| gin | 68,471 | 1,089 | 67,382 | 62.9× |
| httpx | 53,219 | 1,401 | 51,818 | 38.0× |
| code-review-graph | 87,342 | 2,117 | 85,225 | 41.3× |
| **加权平均** | — | — | — | **43.2×** |

差异来源：图谱上下文 token 数取决于 `detect-changes` 选择的变更文件。每次运行可能因 `git diff` 返回略有不同的差异范围而变化约 ±5%，但长期平均值应在上表 ±2% 以内。

### 影响精度

| 仓库 | 精确率 | 召回率 | F1 |
|---|---:|---:|---:|
| express | 0.91 | 0.88 | 0.89 |
| fastapi | 0.89 | 0.91 | 0.90 |
| flask | 0.93 | 0.86 | 0.89 |
| gin | 0.87 | 0.90 | 0.88 |
| httpx | 0.90 | 0.93 | 0.91 |
| code-review-graph | 0.88 | 0.89 | 0.89 |
| **平均** | **0.90** | **0.90** | **0.89** |

### 构建统计

在 M1 MacBook Pro（8 核，16 GB 内存）上测量：

| 仓库 | 文件数 | 节点数 | 边数 | 冷构建时间 |
|---|---:|---:|---:|---:|
| express | 237 | 4,821 | 11,293 | 8.2 s |
| fastapi | 189 | 3,102 | 7,841 | 5.6 s |
| flask | 142 | 2,087 | 5,329 | 3.9 s |
| gin | 198 | 3,741 | 9,102 | 6.4 s |
| httpx | 214 | 3,892 | 9,788 | 7.1 s |
| code-review-graph | 312 | 5,947 | 14,821 | 11.3 s |

### 增量更新延迟

在同一机器上，对单文件变更测量的 p50 / p95：

| 文件大小 | p50 | p95 |
|---|---:|---:|
| < 100 行 | 0.3 s | 0.8 s |
| 100–500 行 | 0.6 s | 1.4 s |
| 500–2000 行 | 1.2 s | 2.9 s |

### Agent 基准测试

使用 GPT-4 作为评判模型，在 50 个代码问题上评估：

| 指标 | 使用图谱 | 不使用图谱 |
|---|---:|---:|
| 正确定位 | 92% | 71% |
| 首轮解决 | 78% | 54% |
| 平均工具调用次数 | 2.1 | 5.8 |

## 哪个基准测试衡量什么

| 基准测试 | 问题 | 输入 | 衡量指标 |
|---|---|---|---|
| `token_efficiency` | 图谱上下文与朴素全文件上下文相比节省了多少 token？ | `detect-changes` 差异 | `naive_tokens / graph_tokens` |
| `impact_accuracy` | 图谱是否找到了真正受变更影响的函数？ | PR 前后 git 快照 | 精确率 / 召回率 / F1 |
| `agent_baseline` | 配备图谱工具的 Agent 是否比没有图谱工具的更快解决代码问题？ | 50 个标准代码问题 | 正确率、首轮率、工具调用次数 |
| `multi_hop_retrieval` | 图谱是否追踪了多跳调用链（调用者 → 中间层 → 被调用者）？ | 3 跳深度查询 | 在正确节点上的 MRR / Recall@5 |
| `search_quality` | 语义搜索是否找到了相关函数，即使用的是不同的词？ | 自然语言查询 | MRR / Recall@5（MTEB 风格） |
| `build_performance` | 冷构建和增量更新需要多长时间？ | 固定 SHA checkout | 总挂钟时间、p50/p95 增量延迟 |
| `flow_completeness` | 流程检测是否追踪到了从入口点到叶子的完整调用链？ | 已知入口点 + 参考调用图 | 深度完整率 |

`eval` 命令接受逗号分隔的 `--benchmark` 列表；不提供该标志时运行全部基准测试。

## 每周 CI

`.github/workflows/eval.yml` 每周一 00:00 UTC 运行 `token_efficiency` 和 `impact_accuracy` 基准测试，并将结果提交到 `results/` 分支。如果任何指标比最近 8 次运行的滚动平均值下降超过 5%，工作流会失败并在 Issue 标签 `eval-regression` 下打开 Issue。

如需在本地重现每周 CI 运行：

```bash
act -W .github/workflows/eval.yml --matrix benchmark:token_efficiency
```

（需要 `act` CLI 和 Docker。）

## 生成图表

README 图表是使用 matplotlib 后端生成的。要本地重新生成所有图表：

```bash
uv run code-review-graph eval \
  --benchmark token_efficiency,impact_accuracy,build_performance \
  --report \
  --diagram-dir diagrams/
```

每个基准测试在 `diagrams/` 中写一个 PNG。README 引用的路径与此处输出的文件名一一对应。

如果想要高分辨率版本（用于演示幻灯片）：

```bash
uv run code-review-graph eval --benchmark token_efficiency --report --dpi 300
```

## 故障排除

**`status=error` 行在 CSV 中出现**

这表示工具调用抛出了异常。该行被排除在聚合之外。最常见原因：

- 图谱未构建（先运行 `code-review-graph build`）；
- 嵌入未生成（先运行 `code-review-graph embed`）；
- `eval/configs/*.yaml` 中的 `commit` SHA 不在浅克隆中（使用完整克隆）。

**数字与 README 有差异（超出 ±2%）**

检查：

1. `git log --oneline -1` 在你的 checkout 上——SHA 是否与 README 顶部引用的匹配？
2. 在 Python 3.10 上运行还是更新的版本（浮点行为在次要版本间稳定，但句子转换器模型缓存路径可能不同）？
3. 嵌入是否已生成（步骤 3）？没有嵌入，混合搜索退化为纯关键词，可能会降低 `search_quality` 和 `agent_baseline`。

**`Leiden 社区不稳定`**

如果你看到社区检测的随机结果，确认 `CRG_LEIDEN_SEED` 未被设置为随机值，且你在使用 `leidenalg >= 0.9.0`（早期版本不接受种子参数）。
