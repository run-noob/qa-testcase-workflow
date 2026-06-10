---
name: qa-testcase-workflow
description: QA测试用例工作流总控，自动编排执行PRD分析、用例生成、评审、合并归档的完整流程
---

# QA 工作流总控 Skill

## 适用场景

当用户需要对一个需求执行完整测试用例管理流程时使用本 Skill，包括：
- 一键执行完整的 4 步工作流（PRD分析 → 用例生成 → 用例评审 → 合并归档）
- 从中断处恢复，续接未完成的步骤
- 跳过已完成的步骤，只执行剩余步骤
- 指定从某个步骤开始执行

建议调用示例：
- `/qa-testcase-workflow 退款需求`
- `/qa-testcase-workflow prd/退款需求`
- `/qa-testcase-workflow 退款需求 --from step2`（从用例生成开始）
- `/qa-testcase-workflow 退款需求 --only step1`（仅执行PRD分析）
- `/qa-testcase-workflow 退款需求 --skip-merge`（跳过合并归档）

## 输入参数

- `$ARGUMENTS` 可选。
- 可传需求目录名、需求名或 PRD 路径，如 `退款需求`、`prd/退款需求`。
- 未传参数时，扫描 `prd/` 下的需求目录（排除 `prd/archive/`），若存在多个目录则必须先让用户确认。
- 支持附加控制参数：
  - `--from step{N}`：从第 N 步开始执行（跳过前面已完成的步骤）
  - `--only step{N}`：仅执行第 N 步
  - `--skip-merge`：执行到评审结束，跳过合并归档步骤
  - `--force`：不检查已有产物，强制重新执行所有步骤

## 工作流步骤定义

| 步骤 | ID | 子 Skill | 关键产物 |
|------|----|----------|----------|
| PRD 分析 | step1 | `qa-prd-analysis` | `prd/{feature-dir}/output/*-analysis.md` |
| 用例生成 | step2 | `qa-testcase-generation` | `prd/{feature-dir}/output/test-cases/*.md` |
| 用例评审 | step3 | `qa-testcase-review` | `prd/{feature-dir}/output/test-cases/review-report.md` |
| 合并归档 | step4 | `qa-testcase-merge` | `test-cases/` 更新 + `prd/archive/` 归档 |

## 执行前检查

在执行任意步骤前，先完成以下检查：

1. **确认需求目录**：根据 `$ARGUMENTS` 解析 `feature-dir`，若有歧义必须先向用户确认。
2. **扫描已有产物**：检查每个步骤的关键产物是否已存在，生成当前状态快照（见下方状态检测规则）。
3. **决定执行计划**：根据状态快照与用户参数，决定哪些步骤需要执行、哪些可跳过。

### 状态检测规则

| 步骤 | 产物路径 | 已完成判定条件 |
|------|---------|--------------|
| step1 | `prd/{feature-dir}/output/*-analysis.md` | 文件存在且非空 |
| step2 | `prd/{feature-dir}/output/test-cases/_progress.md` | 文件存在且所有模块状态为"已完成" |
| step3 | `prd/{feature-dir}/output/test-cases/review-report.md` | 文件存在且非空 |
| step4 | `prd/archive/` 下存在以 `{feature-dir}` 为后缀的目录 | 目录存在 |

### 断点恢复逻辑

若检测到某步骤已完成，默认跳过该步骤，并在执行前向用户展示恢复计划：

```
检测到以下步骤已完成，将跳过：
  ✅ step1 - PRD分析（已产出 output/退款需求-analysis.md）
  ✅ step2 - 用例生成（_progress.md 全部完成，共 4 个模块）
  ⏳ step3 - 用例评审（review-report.md 不存在，待执行）
  ⏳ step4 - 合并归档（archive 不存在，待执行）

将从 step3 开始继续执行，是否确认？[Y/n]
```

若用户希望重新执行已完成的步骤，回复 `n` 后可输入 `--force` 或手动指定 `--from step{N}`。

## 执行流程

### Step 0：初始化与状态展示

1. 解析 `$ARGUMENTS`，确定 `feature-dir`。
2. 读取各步骤产物，生成状态快照。
3. 向用户展示执行计划（含已完成/待执行/将跳过的步骤）。
4. 等待用户确认（若为断点恢复场景）；若所有步骤均待执行则直接开始。

进度展示格式：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 QA 工作流 · {feature-dir}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [ ] Step 1  PRD 分析
  [ ] Step 2  用例生成
  [ ] Step 3  用例评审
  [ ] Step 4  合并归档
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

图例：`[ ]` 待执行  `[→]` 执行中  `[✓]` 已完成  `[S]` 已跳过  `[✗]` 失败

### Step 1：PRD 分析

**触发条件**：step1 产物不存在，或用户指定重新执行。

**执行**：调用 `qa-prd-analysis` skill，传入当前 `feature-dir`。

**完成后检查**：
- 验证 `prd/{feature-dir}/output/*-analysis.md` 已产出。
- 如有澄清项清单 `*-clarifications.md`，向用户说明，询问是否先处理 A/B 类澄清项再继续。
- 更新进度展示，将 Step 1 标记为 `[✓]`。

**失败处理**：见 [错误处理策略](#错误处理策略)。

### Step 2：用例生成

**触发条件**：step2 产物不存在或未全部完成，或用户指定重新执行。

**执行**：调用 `qa-testcase-generation` skill，传入当前 `feature-dir`。

**子 Skill 前置条件由该 Skill 自行处理**（若分析报告不存在，它会自动调用 step1，此时总控需感知到 step1 被重新触发，补充更新进度状态）。

**完成后检查**：
- 验证 `_progress.md` 全部模块为"已完成"状态。
- 验证 `test-case-summary.md` 已产出。
- 更新进度展示，将 Step 2 标记为 `[✓]`。

**失败处理**：见 [错误处理策略](#错误处理策略)。

### Step 3：用例评审

**触发条件**：step3 产物不存在，或用户指定重新执行。

**执行**：调用 `qa-testcase-review` skill，传入当前 `feature-dir`。

**完成后检查**：
- 验证 `review-report.md` 已产出。
- 读取评审结论（通过 / 有条件通过 / 不通过）。
- **若结论为"不通过"**：
  - 停止工作流，不进入 step4。
  - 向用户展示严重问题摘要，建议修复后重新执行 step3。
- **若结论为"有条件通过"**：
  - 向用户提示条件说明，询问是否确认已修复完成、可继续进入 step4。
- **若结论为"通过"**：直接进入 step4。
- 更新进度展示，将 Step 3 标记为 `[✓]`。

**失败处理**：见 [错误处理策略](#错误处理策略)。

### Step 4：合并归档

**触发条件**：step4 尚未执行（archive 不存在），且未使用 `--skip-merge`，且评审通过。

**执行**：调用 `qa-testcase-merge` skill，传入当前 `feature-dir`。

**注意**：`qa-testcase-merge` 会自行产出合并计划并等待用户确认，总控无需重复确认，直接透传即可。

**完成后检查**：
- 验证 `prd/archive/` 下存在对应归档目录。
- 更新进度展示，将 Step 4 标记为 `[✓]`。

**失败处理**：见 [错误处理策略](#错误处理策略)。

### Step 5：完成汇报

所有步骤执行完毕后，向用户输出最终汇总：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ QA 工作流完成 · {feature-dir}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [✓] Step 1  PRD 分析       → output/{feature-name}-analysis.md
  [✓] Step 2  用例生成       → output/test-cases/ ({N} 个模块，{M} 条用例)
  [✓] Step 3  用例评审       → output/test-cases/review-report.md（评审通过）
  [✓] Step 4  合并归档       → test-cases/ 已更新，已归档至 prd/archive/
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

若有步骤被跳过，在对应行标注 `[S] 已跳过（已有产物）`。

## 错误处理策略

每个步骤失败后，提供三层恢复选项：

```
Step {N}（{步骤名}）执行失败。
失败原因：{具体原因}

请选择：
  [R] 重试  - 重新执行本步骤
  [S] 跳过  - 跳过本步骤，继续执行后续步骤（可能导致后续步骤也失败）
  [A] 中止  - 停止工作流，保留已有产物
```

**特殊情况处理**：

| 失败场景 | 默认行为 |
|----------|----------|
| 未找到 PRD 文件 | **中止**，不提供跳过选项（无输入则无法继续） |
| 澄清项未处理（A类） | **暂停**，等待用户确认是否忽略后继续 |
| 用例生成中断（_progress 有未完成模块） | 子 Skill 会自动断点恢复，总控无需干预 |
| 评审结论不通过 | **停止**工作流，不进入 step4，提示修复后重新运行 |
| 合并时用例 ID 冲突 | 子 Skill 会停止并报告冲突，总控提示用户手动处理 |

## 部分执行示例

```bash
# 仅执行 PRD 分析（调试用）
/qa-testcase-workflow 退款需求 --only step1

# 跳过 PRD 分析，从用例生成开始
/qa-testcase-workflow 退款需求 --from step2

# 只执行到评审，不合并归档
/qa-testcase-workflow 退款需求 --skip-merge

# 强制重新执行全部步骤（忽略已有产物）
/qa-testcase-workflow 退款需求 --force
```

## 强制规则

1. 执行任何步骤前，必须先展示当前状态和执行计划。
2. 遇到需求目录歧义时，必须先向用户确认，不得自行猜测。
3. 不得跳过评审直接执行合并归档。
4. 评审不通过时，不得执行合并归档。
5. 子 Skill 的确认交互（如用例生成的"是否重新生成"、合并的"合并计划确认"）直接透传给用户，总控不额外拦截。
6. 所有步骤完成后，必须输出完整的汇总报告。
