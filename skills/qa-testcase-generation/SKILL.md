---
name: qa-testcase-generation
description: 基于 PRD 分析报告和变更影响分析结果，生成流程化的结构化测试用例、覆盖矩阵与本次需求用例汇总
---

# QA 测试用例生成 Skill

## 适用场景
当用户要求基于当前 PRD 生成测试用例、输出覆盖矩阵、形成本次需求测试包时使用本 Skill。

建议调用示例：
- `/qa-testcase-generation`
- `/qa-testcase-generation 退款需求`
- `/qa-testcase-generation payment`

> 💡 本 Skill 也可以作为 `/qa-testcase-workflow` 工作流的一部分自动执行。如需执行完整流程（PRD分析 → 变更分析 → 用例生成 → 评审 → 合并归档），建议使用 `/qa-testcase-workflow` 一键执行。

## 输入参数
- `$ARGUMENTS` 可选。
- 可传需求名、目标模块名或分析文件线索。
- 未传参数时，默认定位 `prd/current/output/` 下当前需求的分析文件。

## 前置条件
优先检查：
1. 存在 `prd/current/output/*-analysis.md`
2. 若是已有项目变更需求，优先存在 `prd/current/output/*-change-diff.md`

如果没有 `*-change-diff.md`，但项目明显是新需求或空用例库：
- 不要阻塞执行
- 在汇总文件中说明：`当前按新需求直出测试用例，未进行存量差异分析。`

## 强制规则
2. 生成的测试用例统一写入 `prd/current/output/test-cases/`。
3. 永远不要直接修改 `test-cases/` 全量用例库。
4. 用例文件名、目录名使用中文。
5. 用例编号必须关联到 `prd/current/output/*-analysis.md`里的组件编号。
6. **流程化设计规则**：禁止生成破碎的单步验证用例。用例设计必须以“用户任务”或“业务流程”为核心。一个典型的功能性测试用例应覆盖一个完整的业务闭环或逻辑闭环，**测试步骤通常不少于 3 步**，应包含“环境准备 -> 操作序列 -> 多维度校验 -> 清理（如有）”的完整链路。

## 执行流程

### Step 1：加载输入材料
读取：
- `AGENTS.md` （如有）
- `prd/current/output/*-analysis.md`
- `skills/qa-testcase-generation/case-template.md`
- `skills/qa-testcase-generation/case-standards.md`
- `skills/qa-testcase-generation/priority-rules.md`
- `glossary/`： 遇到不懂的业务概念，从该目录内查找相关术语文件。

### Step 2：制定用例设计方案
在真正写文件前，先完成设计规划：

#### 2.1 用例分组
按“系统模块 → 页面区块/组件”组织输出，例如：
- `prd/current/output/test-cases/{SystemModule}-{Component}.md`
- `prd/current/output/test-cases/test-case-summary.md`

#### 2.2 设计方法选择
根据功能点选择合适方法：
- **场景法 (Main Focus)**：用于设计端到端流程用例
- 等价类划分/边界值分析：用于细化流程中的关键输入项
- 状态转换：用于复杂生命周期的对象测试
- 错误推测：用于异常路径设计

### Step 3：生成测试用例文件
 参考`case-template.md`，对每个模块/组件生成结构化用例，文件名推荐格式：{模块名}-{组件名}-用例.md

### Step 4：生成测试用例汇总文件

内部先完成功能点覆盖自检，并将结果直接写入 `prd/current/output/test-cases/test-case-summary.md`。
汇总文件至少包含：
  - 每个模块组件的用例数量及总数
  - P0/P1/P2/P3 分布
  - 文件清单
  - 功能点覆盖矩阵（功能点ID、描述、覆盖用例ID、覆盖状态）
  - 覆盖缺口说明（若有未覆盖项，必须说明原因）
  - 待确认项

## 编写原则
1. **流程化优先**：标题应描述一个完整的动作过程，如“验证用户在余额充足时成功订阅高级会员”而非“测试订阅按钮”。
2. **步骤可执行**：测试步骤必须是连续的操作流，预期结果需涵盖数据库变更、页面跳转、消息推送等多维度校验。
3. **数据具体化**：给出足以驱动流程流转的具体测试数据。
4. **去冗余**：不要生成大量重复步骤的用例，可以通过数据驱动或合并路径来精简。

## 大量用例处理策略
当预计生成用例超过 100 条时：
- 按其中复杂的组件拆分为独立文件
- 单文件尽量不超过 50 条用例
- 分批生成，每批完成后更新汇总

## 失败处理
如遇以下情况，中止并说明：
- 分析报告缺失
- 分析报告中的功能点过于模糊，无法构建操作流
