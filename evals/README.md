# QA 工作流评测

当前评测集包含一个真实黄金样本：`coupon-001`，端到端执行：

```text
qa-prd-analysis → qa-testcase-generation → 产物收集 → Promptfoo assertions
```

## 评测范围

- PRD：`【Buff】优惠券系统小细节优化`
- 输入：Markdown PRD 与 3 张 TAPD 截图
- 被测对象：当前仓库的 `skills/qa-prd-analysis/` 和 `skills/qa-testcase-generation/`
- 输出：分析报告、独立澄清清单、进度文件、模块用例和用例汇总
- 不生成 Excel/XMind，不修改全量 `test-cases/`

每次运行都会在 `evals/.runs/` 创建独立工作区，并实时写入 Codex JSONL
事件、stderr、provider 心跳日志和全部生成产物。评测执行期间，终端每 30 秒会显示
一次心跳，包括运行时长、日志大小、最近事件类型和工作区文件数。

## 指标

| Metric | 含义 | 门槛 |
|---|---|---:|
| `artifact_contract` | 文件与流程契约 | 必须 1.0 |
| `core_fact_recall` | PRD 核心事实加权召回率 | 至少 0.95 |
| `forbidden_claim_control` | 严重无依据结论控制 | 必须 1.0 |
| `clarification_recall` | 必需澄清项召回率 | 至少 0.75 |
| `testcase_coverage` | 必需测试覆盖单元加权覆盖率 | 至少 0.90 |
| `testcase_quality` | 用例结构、步骤和可执行性 | 建议至少 0.90 |
| `cross_artifact_consistency` | 进度、用例和汇总一致性 | 建议至少 0.90 |

综合分权重：核心事实 30%、严重臆断控制 15%、澄清项 15%、用例覆盖 25%、用例质量 7.5%、跨产物一致性 7.5%。综合分至少 0.85，且所有硬门禁必须通过。

## 前置条件

1. Node.js 22.22 或更高版本。
2. 已登录并可使用 `codex` CLI：

   ```bash
   codex login status
   ```

3. 安装项目依赖：

   ```bash
   npm install
   ```

## 执行

先运行 assertion 单元测试和配置校验：

```bash
npm run test:evals
npm run eval:validate
```

执行完整优惠券评测：

```bash
npm run eval:coupon
```

执行独立的 LLM 语义覆盖评测（其余指标与原评测一致）：

```bash
npm run eval:validate:llm
npm run eval:coupon:llm
```

默认使用 Promptfoo 配置中的 `gpt-5.6-luna`。如需覆盖被测模型：

```bash
CODEX_EVAL_MODEL=<model-id> npm run eval:coupon
```

LLM grader 默认复用被测模型和 Codex 登录态。可单独指定评分模型和超时秒数：

```bash
CODEX_EVAL_GRADER_MODEL=<model-id> CODEX_EVAL_GRADER_TIMEOUT_SECONDS=180 npm run eval:coupon:llm
```

输出报告：

- `evals/reports/coupon-results.json`
- `evals/reports/coupon-report.html`
- `evals/reports/coupon-results.junit.xml`

LLM 版本报告独立写入：

- `evals/reports/coupon-llm-results.json`
- `evals/reports/coupon-llm-report.html`
- `evals/reports/coupon-llm-results.junit.xml`

### 基于历史结果重新评测

通用重评命令会读取某份 Promptfoo JSON 报告中的 `response.output`，不重新执行
工作流。每次重评都会创建新的 Promptfoo eval，并使用时间戳生成独立报告。

只重跑一个评测点：

```bash
npm run eval:replay -- \
  --report evals/reports/coupon-llm-results.json \
  --metrics core_fact_recall
```

只重跑 LLM 用例覆盖：

```bash
CODEX_EVAL_GRADER_TIMEOUT_SECONDS=300 npm run eval:replay -- \
  --report evals/reports/coupon-llm-results.json \
  --metrics llm_testcase_coverage
```

同时重跑多个评测点：

```bash
npm run eval:replay -- \
  --report evals/reports/coupon-llm-results.json \
  --metrics core_fact_recall,clarification_recall,cross_artifact_consistency
```

按预设重跑全部评测点：

```bash
# 使用 LLM 语义覆盖
npm run eval:replay -- --profile llm

# 使用正则覆盖
npm run eval:replay -- \
  --report evals/reports/coupon-results.json \
  --profile standard
```

其他选项：

```bash
# 查看支持的评测点
npm run eval:replay -- --list-metrics

# 报告包含多个结果时选择索引，并指定输出名前缀
npm run eval:replay -- \
  --report evals/reports/some-results.json \
  --result-index 1 \
  --metrics testcase_quality \
  --output-name testcase-quality-rerun
```

可选评测点包括：`artifact_contract`、`core_fact_recall`、
`forbidden_claim_control`、`clarification_recall`、`testcase_coverage`、
`llm_testcase_coverage`、`testcase_quality` 和
`cross_artifact_consistency`。其中只有 `llm_testcase_coverage` 会再次请求 LLM。

查看 Promptfoo UI：

```bash
npm run eval:view
```

若失败，先从 JSON 报告获取 provider metadata 中的 `runDir`，再检查：

```text
evals/.runs/<run-id>/codex-events.jsonl
evals/.runs/<run-id>/codex-stderr.log
evals/.runs/<run-id>/provider-diagnostics.log
evals/.runs/<run-id>/project/prd/优惠券系统小细节优化/output/
```

如需在另一个终端查看 Codex 原始事件和错误，可执行：

```bash
tail -f evals/.runs/<run-id>/codex-events.jsonl
tail -f evals/.runs/<run-id>/codex-stderr.log
```

## 设计说明

- 黄金答案不是完整 Markdown，而是原子事实、禁止结论、必需澄清项和测试覆盖单元。
- 核心事实与覆盖单元使用加权召回率，避免以“用例条数”代替真实覆盖率。
- LLM 覆盖评测沿用相同黄金覆盖点和权重，只把正则匹配替换为逐项语义判断；`covered`、`partial`、`missing` 分别计 1、0.5、0 分。
- LLM 必须为覆盖结论提供真实用例编号和原文证据；结构化结果异常会报告为 grader error，不会按覆盖缺失计分。
- `artifact_contract` 和 `forbidden_claim_control` 是硬门禁，不能被其他高分抵消。
- 当前只有一个样本，适合作为 smoke eval；暂不能代表跨业务域的总体质量。
