---
name: qa-testcase-merge
description: 将当前需求的测试用例合并到全量用例库，并在确认后归档 prd/current 内容
---

# QA 测试用例合并归档 Skill

## 适用场景
当用户确认当前需求测试完成、评审通过，准备把 `prd/current/output/test-cases/` 产出并入 `test-cases/` 全量用例库，并归档当前 PRD 时使用本 Skill。

建议调用示例：
- `/qa-testcase-merge`
- `/qa-testcase-merge 退款需求`
- `/qa-testcase-merge prd/current/output/test-cases/review-report.md`

> 💡 本 Skill 也可以作为 `/qa-workflow` 工作流的一部分自动执行。如需执行完整流程（PRD分析 → 变更分析 → 用例生成 → 评审 → 合并归档），建议使用 `/qa-workflow` 一键执行。

## 关键建议
本 Skill 采用“两阶段执行”：
1. **先生成合并计划**：分析将新增、修改、废弃哪些文件与用例。
2. **等待用户确认后再落盘**：只有用户明确确认，才真正修改 `test-cases/` 与归档 `prd/current/`。

这样可以显著降低误合并和误归档风险。

## 输入参数
- `$ARGUMENTS` 可选。
- 未传参数时，默认读取当前需求的 review、summary、change-diff 等文件。

## 前置条件
优先检查：
1. `prd/current/output/test-cases/` 下存在当前需求生成的用例文件。
2. 存在 `prd/current/output/test-cases/review-report.md`。
3. 评审结论为“通过”或“有条件通过且已修复完成”。
4. `test-cases/index.md` 可读取；若不存在，则需要同时初始化它。

如果评审未通过：
- 不要执行真实合并。
- 先提示用户回到 `/qa-testcase-review` 修复问题。

## 强制规则
1. 任务开始前先读取 `glossary/`、`test-cases/index.md`。
2. 先产出合并计划，再请求用户确认，不要直接改全量用例库。
3. 只在用户明确确认后，才允许修改 `test-cases/` 和归档 `prd/current/`。
4. 合并时必须确保用例 ID 唯一；如冲突，必须重新编号并记录映射关系。
5. 处理废弃用例时，默认保留历史记录，不直接物理删除，除非用户明确要求。
6. 更新 `test-cases/index.md`，必要时更新模块级 `index.md`。
7. 归档目录使用：`prd/archive/YYYY-MM-DD-{feature-name}/`。
8. 归档完成后，保留 `prd/current/images/`、`prd/current/output/`、`prd/current/output/test-cases/` 的空目录结构。

## 执行流程

### Phase A：生成合并计划（只读分析）
读取：
- `prd/current/output/test-cases/test-case-summary.md`
- `prd/current/output/test-cases/review-report.md`
- `prd/current/output/*-change-diff.md`（如存在）
- `test-cases/index.md`
- 与目标模块有关的存量用例文件（按需）

输出合并计划，至少说明：
- 新增用例有哪些
- 需修改的存量用例有哪些
- 需标记废弃的用例有哪些
- 将影响哪些文件
- 是否需要新建模块目录或模块级索引
- 是否存在用例 ID 冲突
- 是否存在模块归属不明确的问题

### Phase B：请求用户确认
必须向用户展示合并计划摘要，并明确询问：
- 是否按此计划执行真实合并与归档

未得到确认前，不要修改任何全量库文件，也不要移动 `prd/current/`。

### Phase C：执行真实合并（仅在确认后）

#### C1. 处理新增用例
- 确定目标模块目录，例如 `test-cases/payment/`
- 如模块目录不存在，则创建目录与模块级 `index.md`
- 将新增用例追加到合适文件，或新建 `{feature}-cases.md`
- 如编号冲突，重新编号并记录映射

#### C2. 处理修改用例
- 定位全量库中的原用例
- 更新相关步骤、预期结果、前置条件、测试数据、优先级等
- 在用例中追加修改历史，例如：
  - `YYYY-MM-DD: 因{需求名}变更，更新{具体内容}`

#### C3. 处理废弃用例
- 默认不直接删除
- 在标题或状态中标记 `[已废弃]`
- 补充废弃原因与日期

#### C4. 更新索引
- 更新 `test-cases/index.md`
- 若存在模块级 `index.md`，同步更新文件映射、用例数、最近更新时间
- 更新最近变更记录

### Phase D：归档 PRD
仅在合并完成后执行：
1. 创建归档目录：`prd/archive/YYYY-MM-DD-{feature-name}/`
2. 将 `prd/current/` 下本次需求相关文件移动到归档目录
3. 清空 `prd/current/` 中本次需求内容，但保留目录结构：
   - `prd/current/images/`
   - `prd/current/output/`
   - `prd/current/output/test-cases/`

### Phase E：输出合并结果
合并完成后，向用户输出摘要：
- 新增用例数
- 修改用例数
- 废弃用例数
- 涉及模块数
- 新建文件列表
- 修改文件列表
- 归档目录路径
- 更新后的总模块数/总用例数（如可统计）

## 质量要求
- 不能跳过确认直接合并。
- 不能在存在 ID 冲突时静默覆盖。
- 不能把本次需求的临时产物误并入错误模块。
- 合并结果必须与 `change-diff`、`summary`、`review-report` 保持一致。
- 更新索引时，保证文件路径和统计数字自洽。

## 失败处理
如遇以下情况，优先停止并说明原因：
- 评审未通过
- 用例 ID 冲突无法自动解决
- 模块归属不明确
- 存量文件结构异常，无法安全更新
- 当前需求范围与产出文件不一致
- 用户未确认但尝试进入真实合并阶段
