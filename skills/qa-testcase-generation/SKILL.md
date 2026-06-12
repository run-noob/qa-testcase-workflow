---
name: qa-testcase-generation
description: 基于 PRD 分析报告和变更影响分析结果，生成流程化的结构化测试用例、覆盖矩阵与本次需求用例汇总
---

# QA 测试用例生成 Skill

## 适用场景
当用户要求基于当前 PRD 生成测试用例、输出覆盖矩阵、形成本次需求测试包时使用本 Skill。

建议调用示例：
- `/qa-testcase-generation 退款需求`
- `/qa-testcase-generation payment`

## 输入参数
- `$ARGUMENTS` 可选。
- 可传需求名、目标模块名或分析文件线索。
- 未传参数时，默认先确认需求目录，再定位 `prd/{feature-dir}/output/` 下当前需求的分析文件。

## 前置条件
优先检查：
1. 存在 `prd/{feature-dir}/output/*-analysis.md`
   - **若分析报告不存在**，你需要自行完成 PRD 分析：
     1. 读取 `skills/qa-prd-analysis/SKILL.md` 了解分析流程与输出规范。
     2. 按照其执行流程（Step 1～5）对当前 PRD 进行分析。
     3. 产出 `prd/{feature-dir}/output/{feature-name}-analysis.md` 及 `*-clarifications.md`（如有澄清项）。
     4. 验证产物已成功生成后，再继续执行本技能的后续流程。
     - 若以上步骤最终仍无法产出有效的分析报告，则按下方 [失败处理](#失败处理) 规则中止。
   - 生成完成后，验证 `prd/{feature-dir}/output/*-analysis.md` 已成功产出，若仍未生成则中止并报错。
2. **检查是否已有用例**：检查 `prd/{feature-dir}/output/test-cases/` 目录是否已存在。
   - **若存在 `_progress.md` 且有未完成模块**（状态为 `待生成` ）：说明上次是中断退出，**不询问重新生成**，直接读取 `_progress.md` 续接未完成的模块。参见 [断点恢复与进度跟踪](#断点恢复与进度跟踪)。
   - 如果目录已存在且有 `.md` 用例文件，但无 `_progress.md`（或全部已完成），**必须先征求用户确认**是否要继续重新生成。
   - 向用户说明：
     - 旧用例目录：`prd/{feature-dir}/output/test-cases/`
     - 备份名称示例：`prd/{feature-dir}/output/test-cases-backup-{序号}/`
   - 如果用户选择**重新生成**，先将旧的 `test-cases/` 目录重命名为 `test-cases-backup-{序号}/`（如 `test-cases-backup-001/`、`test-cases-backup-002/`，序号自动递增避免冲突），然后再继续生成新的用例。
   - 如果用户选择**不重新生成**，直接终止执行，提示用户可查看已有用例。

## 强制规则
2. 生成的测试用例统一写入 `prd/{feature-dir}/output/test-cases/`。
3. 永远不要直接修改 `test-cases/` 全量用例库。
4. 用例文件名、目录名使用中文。
5. 用例编号必须关联到 `prd/{feature-dir}/output/*-analysis.md` 里的组件编号。
6. **流程化设计规则**：禁止生成破碎的单步验证用例。用例设计必须以“用户任务”或“业务流程”为核心。一个典型的功能性测试用例应覆盖一个完整的业务闭环或逻辑闭环，**测试步骤通常不少于 3 步**，应包含“环境准备 -> 操作序列 -> 多维度校验 -> 清理（如有）”的完整链路。
7. **严禁**随意编造测试数据，如URL、测试账号等

## 执行流程

### Step 1：加载输入材料
读取：
- `AGENTS.md` （如有）
- `prd/{feature-dir}/output/*-analysis.md`，若不存在，参照前置条件中的说明自行完成 PRD 分析后再继续
- `prd/{feature-dir}/output/*-clarifications.md`, 若澄清问题清单内还有未确认的问题，优先询问用户是否忽略未澄清的问题
- `skills/qa-testcase-generation/case-template.md`
- `skills/qa-testcase-generation/case-standards.md`
- `skills/qa-testcase-generation/priority-rules.md`
- `glossary/`： 遇到不懂的业务概念，从该目录内查找相关术语文件。

### Step 2：制定用例设计方案
在真正写文件前，先完成设计规划：

#### 2.1 用例分组
按”系统模块 → 页面区块/组件”组织输出，例如：
- `prd/{feature-dir}/output/test-cases/{SystemModule}-{Component}.md`
- `prd/{feature-dir}/output/test-cases/test-case-summary.md`

**在分组阶段即创建进度跟踪文件**：
- 文件路径：`prd/{feature-dir}/output/test-cases/_progress.md`
- 该文件用于断点恢复：列出所有待生成的模块清单，每完成一个模块即更新状态
- 文件格式参见 [断点恢复与进度跟踪](#断点恢复与进度跟踪) 章节

#### 2.2 设计方法选择
在生成用例前，必须为每个功能点明确测试设计方法，并输出设计方法清单。要求：

2.2.1 **方法选用原则**
   - 涉及输入范围、数值、长度、时间的 → 必须使用 `等价类 + 边界值`
   - 涉及状态变化、流程分支的 → 必须使用 `状态转换 / 场景法`
   - 涉及多条件组合的 → 必须使用 `判定表 / 正交试验`（至少覆盖关键组合）
   - 涉及异常、权限、逆向操作的 → 必须使用 `错误推测法`
   - 涉及数据格式、必填校验的 → 使用 `等价类 + 边界值 + 异常分析`

2.2.2 **输出设计方法清单**（内嵌在思考过程中，或作为临时输出，不写入最终文件）
   对每个功能点，列出：
   - 功能点 ID
   - 功能描述
   - 选用方法（可多个）
   - 简要设计思路（如：有效等价类1个，无效等价类3个，边界值取0、最大值、最大值+1）

   示例：
   | 功能点ID | 功能描述 | 选用方法 | 设计思路 |
   |----------|----------|----------|----------|
   | F-01 | 退款金额输入 | 等价类+边界值 | 有效：0<金额≤订单金额；无效：负数、0、大于订单金额；边界：0、1、订单金额、订单金额+0.01 |
   | F-02 | 退款原因选择 | 等价类+异常 | 有效：预置原因；无效：不选、自定义超长文本 |
   | F-03 | 退款状态流转 | 状态转换 | 覆盖：待审核→审核通过→退款中→退款成功；待审核→审核拒绝；退款中→退款失败 |

2.2.3 **覆盖保证**
   - 每个功能点至少使用一种方法
   - 正向用例至少覆盖所有有效等价类 + 典型场景
   - 反向用例至少覆盖关键无效等价类 + 核心异常路径
   - 边界用例必须覆盖边界值及边界附近的值（如最小值-1、最大值+1）

### Step 3：生成测试用例文件
 参考`case-template.md`，对每个模块/组件生成结构化用例，文件名推荐格式：{模块名}-{组件名}.md

 **每完成一个模块文件后**：立即更新 `_progress.md` 将该模块标记为`已完成`，防止上下文丢失导致进度不可追溯。

### Step 4：转换为 Excel 文件


#### 4.1 转换脚本
使用 `skills/qa-testcase-generation/scripts/markdown_case_convert_to_excel.py` 执行转换。
首次运行前，请确保执行以下命令安装依赖：
```bash
python -m pip install -r scripts/requirements.txt
	将生成的 Markdown 用例文件转换为 Excel 格式，便于导入测试管理平台或分享给非技术人员。
```

#### 4.2 使用方式
- 所有的辅助脚本都存放在本技能目录的 `scripts/` 下。
- 在执行任何脚本之前，你必须先获取本 `SKILL.md` 所在的绝对路径，并将其作为基准路径来定位 `scripts/` 目录。
- **执行示例**：如果本 `SKILL.md` 路径为 `/path/to/my-skill/SKILL.md`，则你应当执行 `/path/to/my-skill/scripts/process.py`。

```bash
# 转换指定目录下的所有 .md 用例文件
python scripts/markdown_case_convert_to_excel.py prd/{feature-dir}/output/test-cases/

# 指定输出路径
python scripts/markdown_case_convert_to_excel.py prd/{feature-dir}/output/test-cases/ -o prd/{feature-dir}/output/test-cases.xlsx
```

#### 4.3 输出说明
- 输入：`prd/{feature-dir}/output/test-cases/` 目录下所有 `.md` 用例文件
- 输出：Excel 文件（默认 `testcases.xlsx`），包含以下列：ID、模块、优先级、类型、标题、前置条件、步骤、预期、测试数据、备注

### Step 5：生成测试用例汇总文件

内部先完成组件的功能点覆盖自检，并将结果直接写入 `prd/{feature-dir}/output/test-cases/test-case-summary.md`。
汇总文件至少包含：
  - 每个模块组件的用例数量及总数
  - P0/P1/P2/P3 分布
  - 文件清单
  - 功能点覆盖矩阵
   - 功能点ID
   - 组件功能点描述 
   - 对应PRD分析编号: 引用`prd/current/output/*-analysis.md`的章节序号，如4.1，方便追溯
   - 覆盖用例ID
   - 覆盖状态
  - 覆盖缺口说明（若有未覆盖项，必须说明原因）
  - 待确认项

## 编写原则
1. **流程化优先**：标题应描述一个完整的动作过程，如“验证用户在余额充足时成功订阅高级会员”而非“测试订阅按钮”。
2. **步骤可执行**：测试步骤必须是连续的操作流，预期结果需涵盖数据库变更、页面跳转、消息推送等多维度校验。
3. **数据具体化**：给出足以驱动流程流转的具体测试数据。**严禁**随意编造测试数据，如URL、测试账号等
4. **去冗余**：不要生成大量重复步骤的用例，可以通过数据驱动或合并路径来精简。

## 断点恢复与进度跟踪

### 进度文件格式

文件路径：`prd/{feature-dir}/output/test-cases/_progress.md`

```markdown
# 用例生成进度跟踪

## 需求信息
- 需求名称：{feature-name}
- 需求目录：prd/{feature-dir}/
- 分析报告：prd/{feature-dir}/output/{analysis-file}.md
- 创建时间：{YYYY-MM-DD HH:mm}

## 模块进度

| 序号 | 模块/组件 | 文件名 | 状态 | 预计用例数 | 实际用例数 | 完成时间 |
|------|-----------|--------|------|-----------|-----------|---------|
| 1 | 退款申请 | 退款模块-退款申请.md | 已完成 | 15 | 16 | 2026-06-08 10:30 |
| 2 | 退款审核 | 退款模块-退款审核.md | 生成中 | 10 | - | - |
| 3 | 退款查询 | 退款模块-退款查询.md | 待生成 | 8 | - | - |
| 4 | 退款回调 | 退款模块-回调处理.md | 待生成 | 12 | - | - |

## 断点恢复指引
> 如果你是新会话，请读取本文件，从状态为 `待生成` 的第一个模块继续生成。
> 完成后更新对应行状态，最终全部 `已完成` 后再执行 Step 4（Excel 转换）和 Step 5（汇总）。
```

## 大量用例处理策略
当预计生成用例超过 100 条时：
- 按其中复杂的组件拆分为独立文件
- 单文件尽量不超过 50 条用例
- 按功能模块分批生成，每批完成后更新汇总，模块用例全部完成后，清空该模块的用例上下文，继续下一个模块
- **必须**创建 `_progress.md` 进度文件，防止上下文溢出导致进度丢失

## 失败处理
如遇以下情况，中止并说明：
- 分析报告缺失且自行分析生成失败（已尝试按 PRD 分析流程生成但仍未产出有效分析报告）
- 分析报告中的功能点过于模糊，无法构建操作流
