---
name: qa-workflow
description: QA测试用例工作流总控，自动编排执行PRD分析、变更分析、用例生成、评审、合并归档的完整流程
---

# QA 工作流总控 Skill

## 适用场景

当用户需要执行完整的测试用例管理流程，或需要部分执行、断点恢复时使用本 Skill。

**推荐使用场景**：
- 收到新PRD，需要完整执行从分析到归档的全流程
- 只需要快速生成测试用例，不进行评审和合并（部分执行）
- 工作流中断后需要从断点继续执行
- 需要灵活控制执行步骤范围

**建议调用示例**：
```bash
/qa-workflow                        # 执行完整5步流程
/qa-workflow 退款需求                # 指定需求名称执行完整流程
/qa-workflow --steps 1-3 退款需求    # 只执行前3步
/qa-workflow --from 3 退款需求       # 从步骤3开始执行
/qa-workflow --resume               # 从上次中断处继续
```

> 💡 **与独立Skills的关系**：本 Skill 会自动调用以下5个独立skills，但这些skills仍然可以单独调用用于灵活调试：
> - `/qa-prd-analysis` - PRD分析
> - `/qa-change-diff` - 变更影响分析
> - `/qa-testcase-generation` - 用例生成
> - `/qa-testcase-review` - 用例评审
> - `/qa-testcase-merge` - 合并归档

---

## 输入参数

### 基础参数
- `$ARGUMENTS` 可选：需求名称，如"退款需求"或"会员订阅需求"。若不指定，将尝试从状态文件恢复或在PRD目录只有一个文件时自动识别。

### 范围控制参数（可选）
- `--steps START-END`：只执行指定范围的步骤，如 `--steps 1-3` 只执行步骤1到3
- `--from START`：从指定步骤开始执行，如 `--from 3` 从步骤3开始

### 恢复参数（可选）
- `--resume`：从上次中断处继续执行工作流
- `--ignore-validation`：忽略依赖检查（慎用，仅在确认前置产物存在时使用）

### 调试参数（可选）
- `--verbose`：显示详细日志信息
- `--dry-run`：模拟执行，不实际调用子skills

---

## 工作流步骤映射

本 Skill 会按顺序执行以下5个步骤：

| 步骤号 | Skill名称 | 步骤名称 | 预期产物 | 是否必需确认 |
|--------|-----------|----------|----------|--------------|
| 1 | qa-prd-analysis | PRD 分析 | prd/current/output/{feature}-analysis.md | 否 |
| 2 | qa-change-diff | 变更分析 | prd/current/output/{feature}-change-diff.md | 否 |
| 3 | qa-testcase-generation | 用例生成 | prd/current/output/test-cases/*.md（核心产物test-case-summary.md） | 否 |
| 4 | qa-testcase-review | 用例评审 | prd/current/output/test-cases/review-report.md | 否 |
| 5 | qa-testcase-merge | 合并归档 | test-cases/（更新），prd/archive/（归档） | **是** |

---

## 强制规则

1. **状态管理**：每个步骤完成后立即更新状态文件 `prd/current/.workflow-state.json`
2. **依赖检查**：执行步骤N前，必须确保步骤N-1的产物存在（除非使用 `--ignore-validation`）
3. **并发限制**：初期版本不支持多个需求并发执行，如检测到进行中的工作流，必须先完成或终止
4. **确认机制**：步骤5（合并归档）前必须暂停并请求用户确认，因为此操作会修改全量用例库
5. **错误保存**：任何步骤失败时，必须保存状态并提供恢复选项
6. **零侵入**：通过Skill工具调用子skills，不修改子skills内部逻辑，通过检查产物文件判断成功/失败

---

## 执行流程

### Phase 1: 初始化与预检

#### Step 1.1: 解析输入参数
1. 从 `$ARGUMENTS` 提取需求名称（featureName）
2. 解析范围控制参数（如 `--steps`, `--from`）
3. 解析恢复参数（如 `--resume`）
4. 解析调试参数（如 `--verbose`, `--dry-run`）
5. 验证参数有效性：
   - 步骤范围必须在1-5之间
   - 如果指定 `--resume`，不能同时指定其他范围参数

#### Step 1.2: 检查状态文件
```
状态文件路径：prd/current/.workflow-state.json

情况A：状态文件不存在
  → 创建新的状态文件
  → 初始化状态：status="pending", current_step=1, completed_steps=[]

情况B：状态文件存在
  → 读取状态文件
  → 检查状态：
    - 如果 status="in_progress"：
        如果用户指定 --resume：从 current_step 继续
        否则询问用户：[1] 继续未完成的工作流 [2] 重新开始
    - 如果 status="completed"：
        询问用户：[1] 重新执行完整流程 [2] 退出
    - 如果 status="failed"：
        显示失败步骤和错误信息
        询问用户：[1] 从失败步骤重试 [2] 跳过失败步骤 [3] 重新开始

情况C：检测到并发冲突
  → 如果状态文件显示另一个需求正在执行：检测到状态文件存在且 `feature_name` ≠ 当前传入的 featureName，且 `status`="in_progress"
    提示："检测到正在进行的工作流：{feature_name}
          当前不支持并发执行。
          选项：[1] 使用 --resume 继续 [2] 删除状态文件重新开始（慎用）"
```

#### Step 1.3: 预检前置条件

本步骤对项目目录结构进行全面验证，确保工作流执行所需的目录和文件都已就绪。

##### 1.3.1 必需目录结构检查

**检查以下必需目录**：

| 目录路径 | 用途 | 必需程度 | 缺失时的处理 |
|----------|------|----------|--------------|
| `prd/current/` | 存放当前需求的PRD文档 | **必需** | 提示创建或中止 |
| `prd/current/output/` | 存放分析产物 | **必需** | 可自动创建 |
| `prd/current/output/test-cases/` | 存放用例产物 | **必需** | 可自动创建 |
| `prd/current/images/` | 存放PRD引用图片 | **必需** | 可自动创建 |
| `prd/archive/` | 存放归档的历史需求 | **必需（步骤5）** | 提示创建或跳过步骤5 |
| `test-cases/` | 全量测试用例库 | **必需（步骤5）** | 提示创建或跳过步骤5 |
| `glossary/` | 业务术语表 | **强烈推荐** | 警告但可继续 |
| `standards/` | 测试规范文档 | 推荐 | 仅提示 |

**验证逻辑**：
```
function validate_directory_structure(steps_to_execute):
  missing_required = []
  missing_recommended = []

  # 检查必需目录
  required_dirs = [
    "prd/current/",
    "prd/current/output/",
    "prd/current/output/test-cases/",
    "prd/current/images/"
  ]

  # 如果要执行步骤5，额外检查归档和用例库目录
  if 5 in steps_to_execute:
    required_dirs.extend(["prd/archive/", "test-cases/"])

  for dir in required_dirs:
    if not exists(dir):
      missing_required.append(dir)

  # 检查推荐目录
  if not exists("glossary/"):
    missing_recommended.append("glossary/")
  if not exists("standards/"):
    missing_recommended.append("standards/")

  # 处理缺失情况
  if missing_required:
    handle_missing_required_directories(missing_required)

  if missing_recommended:
    handle_missing_recommended_directories(missing_recommended)
```

##### 1.3.2 缺失目录的处理策略

**必需目录缺失时的用户提示**：
```
⚠️  目录结构不完整

以下必需目录不存在：
  ✗ prd/current/
  ✗ prd/archive/
  ✗ test-cases/

这些目录是工作流正常运行的前置条件。

请选择：
  [1] 自动创建缺失的目录（推荐）
  [2] 查看完整的目录结构说明
  [3] 我会手动创建，稍后重新执行
```

**用户选择处理逻辑**：
- **选项1：自动创建**
  ```
  for dir in missing_required:
    create_directory(dir)

  ✓ 已自动创建以下目录：
    - prd/current/
    - prd/current/output/
    - prd/current/output/test-cases/
    - prd/current/images/
    - prd/archive/
    - test-cases/

  💡 提示：请将PRD文档放入 prd/current/ 目录后重新执行。

  继续执行工作流？
    [1] 是，我已放置PRD文档
    [2] 否，我稍后执行
  ```

- **选项2：查看说明**
  ```
  显示完整的目录结构文档（见下方"目录结构规范"章节）
  显示后返回选项菜单
  ```

- **选项3：手动创建**
  ```
  工作流已中止。

  请按以下结构创建目录：
    项目根目录/
    ├── prd/
    │   ├── current/           # 存放当前需求PRD
    │   │   ├── output/        # 分析产物输出目录
    │   │   │   └── test-cases/  # 用例产物目录
    │   │   └── images/        # PRD引用的图片
    │   └── archive/           # 归档的历史需求
    ├── test-cases/            # 全量测试用例库
    │   └── index.md          # 用例库索引
    ├── glossary/              # 业务术语表（推荐）
    └── standards/             # 测试规范（可选）

  创建完成后，重新执行：/qa-workflow {feature_name}
  ```

**推荐目录缺失时的处理**：
```
⚠️  以下推荐目录不存在：
  - glossary/ （业务术语表）
  - standards/ （测试规范文档）

说明：
- glossary/ 用于PRD分析阶段识别业务术语，缺失可能影响分析准确性
- standards/ 用于提供测试规范参考，缺失不影响核心流程

是否继续执行？
  [1] 继续执行（接受风险）
  [2] 创建这些目录后再执行
  [3] 查看如何配置术语表和规范文档
```

##### 1.3.3 PRD文件存在性检查

**检查 prd/current/ 下是否有PRD文档**：
```
function validate_prd_file(feature_name):
  prd_files = glob("prd/current/*.md")

  # 排除output目录下的文件
  prd_files = filter(prd_files, not in "output/")

  if len(prd_files) == 0:
    error: "
    ✗ 未找到PRD文档

    prd/current/ 目录为空，请添加PRD文档。

    文件命名建议：
    - {feature-name}.md
    - {feature-name}-prd.md
    - {需求名称}.md

    示例：refund-feature.md, 退款需求.md

    添加PRD后，重新执行：/qa-workflow {feature_name}
    "
    return false

  if len(prd_files) > 1 and not feature_name:
    ask_user: "
    找到多个PRD文档：
    {list prd_files}

    请指定要分析的PRD：
    [显示文件列表供选择]
    "

  return true
```

##### 1.3.4 依赖产物检查（仅部分执行时）

**如果使用 `--from` 或 `--steps` 参数部分执行**：
```
function validate_dependencies(steps_to_execute):
  for step in steps_to_execute:
    if step > 1:
      required_artifact = get_required_artifact(step - 1)

      if not file_exists(required_artifact):
        error: "
        ⚠️  前置依赖缺失

        步骤{step}（{step_name}）依赖步骤{step-1}的产物：
          {required_artifact}

        该文件不存在，无法继续执行。

        解决方案：
          [1] 先执行步骤{step-1}：/qa-workflow --steps {step-1}
          [2] 从步骤1完整执行：/qa-workflow {feature_name}
          [3] 忽略依赖检查（慎用）：/qa-workflow --from {step} --ignore-validation
        "
        return false

  return true

function get_required_artifact(step):
  mapping = {
    0: "prd/current/{feature}-*.md",  # PRD文档本身
    1: "prd/current/output/{feature}-analysis.md",
    2: "prd/current/output/{feature}-change-diff.md",
    3: "prd/current/output/test-cases/test-case-summary.md",
    4: "prd/current/output/test-cases/review-report.md"
  }
  return mapping[step]
```

##### 1.3.5 权限检查

**检查关键目录的读写权限**：
```
function validate_permissions():
  dirs_to_check = [
    "prd/current/",
    "prd/current/output/",
    "test-cases/"  # 仅步骤5需要
  ]

  for dir in dirs_to_check:
    if not has_write_permission(dir):
      error: "
      ✗ 权限不足

      无法写入目录：{dir}

      请检查：
      1. 文件系统权限设置
      2. 目录是否被其他程序锁定
      3. 磁盘空间是否充足

      修复后重新执行工作流。
      "
      return false

  return true
```

##### 1.3.6 预检失败的汇总处理

**如果任何预检项失败**：
```
如果预检失败：
  1. 汇总所有失败项
  2. 显示清晰的错误信息
  3. 提供明确的修复建议
  4. 不要继续执行工作流
  5. 保存预检状态（用于调试）

如果所有预检通过：
  ✓ 预检完成，所有前置条件满足
  继续执行工作流...
```

#### Step 1.4: 显示执行计划
```
输出格式：
🚀 QA 测试用例工作流已启动：{feature_name}

执行计划：
  {status_icon} [1/5] PRD 分析
  {status_icon} [2/5] 变更分析
  {status_icon} [3/5] 用例生成
  {status_icon} [4/5] 用例评审
  {status_icon} [5/5] 合并归档

图例：
  ✓ 已完成
  → 正在执行
  ○ 待执行
  ⚠ 已跳过
  ✗ 执行失败

---
```

### Phase 2: 执行工作流步骤

对于每个步骤（1到5），按以下逻辑执行：

#### Step 2.1: 检查是否需要执行
```
检查逻辑：
1. 如果当前步骤在 completed_steps 中 → 跳过（已完成）
2. 如果当前步骤不在执行范围内 → 跳过（不在计划中）
3. 如果当前步骤 > current_step 且 status="in_progress" → 跳过（尚未到达）
4. 否则 → 需要执行
特殊情况：如果 status="partial_completed" 且 current_step=5，表示上次在步骤5前取消，需要重新询问是否执行合并。
```

#### Step 2.2: 显示步骤开始
```
输出格式：
[N/5] 正在执行 {步骤名称}...
调用子skill: /{skill_name} {featureName}
```

#### Step 2.3: 调用子Skill
```
调用方式：
Step 1: Skill("qa-prd-analysis", featureName)
Step 2: Skill("qa-change-diff", featureName)
Step 3: Skill("qa-testcase-generation", featureName)
Step 4: Skill("qa-testcase-review", featureName)
Step 5: Skill("qa-testcase-merge", featureName)

注意：
- 使用 Skill 工具进行调用
- 传递需求名称作为参数
- 等待子skill完成
```

#### Step 2.4: 验证执行结果
```
验证逻辑：
1. 检查预期产物是否生成：
   Step 1: 检查 prd/current/output/*-analysis.md
   Step 2: 检查 prd/current/output/*-change-diff.md
   Step 3: 检查 prd/current/output/test-cases/test-case-summary.md
   Step 4: 检查 prd/current/output/test-cases/review-report.md
   Step 5: 检查 test-cases/ 更新 和 prd/archive/ 目录

2. 如果产物存在：
   ✓ 标记为成功
   → 更新状态文件：
      - completed_steps.push(N)
      - artifacts["stepN"] = 产物路径
      - current_step = N + 1
      - last_update = 当前时间
   → 显示成功信息

3. 如果产物不存在或子skill报错：
   ✗ 标记为失败
   → 更新状态文件：
      - failed_steps.push(N)
      - status = "failed"
      - current_step = N
   → 进入错误处理流程（见 Phase 3）
```

#### Step 2.5: 显示步骤完成
```
输出格式：
✓ {步骤名称} 完成
  - 产物路径：{artifact_path}
  - {步骤特定统计信息，如用例数、功能点数等}

继续下一步 [N+1/5] {下一步骤名称}...
```

#### Step 2.6: Step 5 的前置确认（合并归档前必须确认）
```
在执行 Step 5 之前：

1. 暂停执行，显示提示：
   ⚠️  即将执行合并归档（Step 5/5）

   此操作将：
   - 修改全量用例库 test-cases/
   - 归档当前PRD到 prd/archive/
   - 此操作不可逆，请仔细确认

2. 尝试读取合并计划（如果子skill支持Phase A输出）：
   读取 prd/current/output/test-cases/review-report.md
   提取关键信息：
   - 新增用例数
   - 修改用例数
   - 废弃用例数
   - 影响模块列表
   - 归档路径

3. 显示合并计划摘要：
   合并计划摘要：
   - 新增用例：XX条
   - 修改用例：XX条
   - 废弃用例：XX条
   - 影响模块：{module_list}
   - 归档路径：prd/archive/{date-feature}/

4. 询问用户确认：
   是否继续执行合并归档？
   [1] 确认执行
   [2] 查看详细合并计划（显示完整的review-report.md内容）
   [3] 取消合并（工作流在Step 4完成）

5. 处理用户选择：
   选择1：继续执行 Step 5
   选择2：显示详细内容后，重新询问确认
   选择3：
     - 更新状态：status="partial_completed"
     - 显示："工作流已在 Step 4 完成，未执行合并归档"
     - 提示："如需稍后合并，执行：/qa-testcase-merge {featureName}"
     - 清理状态文件
     - 退出工作流
```

### Phase 3: 错误处理

#### 错误处理触发条件
1. 子skill执行失败（返回错误信息）
2. 预期产物文件缺失
3. 文件系统权限错误
4. 用户主动中断（Ctrl+C）

#### 错误处理流程
```
步骤N执行失败：

1. 保存状态：
   - status = "failed"
   - current_step = N
   - failed_steps.push(N)
   - last_update = 当前时间

2. 显示错误信息：
   ✗ [N/5] {步骤名称} 执行失败

   错误原因：
   {从子skill输出或文件检查中提取的错误信息}

   预期产物：{expected_artifact}
   实际状态：{文件不存在 / 文件损坏 / 其他}

3. 询问用户选择：
   请选择如何继续：
   [1] retry - 重试步骤{N}（修复问题后选择此项）
   [2] skip - 跳过步骤{N}，继续步骤{N+1}（不推荐，可能导致后续步骤失败）
   [3] abort - 终止工作流，保留状态（稍后使用 --resume 继续）
   [4] debug - 查看详细错误日志和调试信息

4. 处理用户选择：
   选择1 (retry)：
     - 清除 failed_steps 中的步骤N
     - 重新执行步骤N
     - 如果再次失败，重新进入错误处理流程

   选择2 (skip)：
     - 将步骤N标记为 skipped_steps
     - current_step = N + 1
     - 显示警告："⚠ 步骤{N}已跳过，后续步骤可能受影响"
     - 继续执行步骤N+1

   选择3 (abort)：
     - 保持状态为 "failed"
     - 显示："工作流已终止，状态已保存。"
     - 显示："修复问题后，使用以下命令继续："
     - 显示："  /qa-workflow --resume"
     - 退出工作流

   选择4 (debug)：
     - 显示详细的执行历史
     - 显示状态文件内容
     - 显示预期产物路径和实际文件系统状态
     - 显示最近的系统日志（如有）
     - 重新显示选项1-3
```

### Phase 4: 完成与清理

#### 工作流完成条件
1. 所有计划步骤都已完成（completed_steps 包含所有步骤）
2. 没有失败的步骤（failed_steps 为空）
3. 或者用户在 Step 5 前选择取消合并（partial_completed）

#### 完成流程
```
1. 更新状态文件：
   - status = "completed" (或 "partial_completed")
   - current_step = 最大步骤号
   - end_time = 当前时间

2. 显示执行摘要：
   🎉 工作流执行完成！

   执行摘要：
   - 需求名称：{feature_name}
   - 执行步骤：{执行的步骤范围}
   - 总耗时：约{duration}分钟
   - 完成步骤：{completed_steps}
   - 跳过步骤：{skipped_steps}（如有）
   - 失败步骤：{failed_steps}（如有）

   关键产物：
   - PRD 分析报告：{step1_artifact}
   - 变更分析报告：{step2_artifact}
   - 测试用例目录：{step3_artifact}
   - 评审报告：{step4_artifact}
   - 归档目录：{step5_artifact}（如执行）

   下一步建议：
   {根据执行情况给出建议，如："可以开始执行测试" 或 "如需合并用例，执行：/qa-testcase-merge"}

3. 清理状态文件：
   选项A：直接删除（默认）
     - 删除 prd/current/.workflow-state.json

   选项B：移动到归档（用于审计）
     - 如果执行了 Step 5（合并归档）：
       移动到 prd/archive/{date-feature}/.workflow-state.json
     - 否则：
       移动到 prd/current/output/.workflow-state-{timestamp}.json

4. 退出工作流
```

---

## 状态文件详解

### 状态文件位置
`prd/current/.workflow-state.json`

### 状态文件结构
```json
{
  "workflow_version": "1.0",
  "feature_name": "退款需求",
  "status": "in_progress",
  "current_step": 3,
  "total_steps": 5,
  "completed_steps": [1, 2],
  "failed_steps": [],
  "skipped_steps": [],
  "artifacts": {
    "step1_analysis": "prd/current/output/refund-analysis.md",
    "step2_change_diff": "prd/current/output/refund-change-diff.md",
    "step3_testcases": null,
    "step4_review": null,
    "step5_merge": null
  },
  "execution_history": [
    {
      "step": 1,
      "skill": "qa-prd-analysis",
      "status": "completed",
      "start_time": "2026-03-17T10:00:00Z",
      "end_time": "2026-03-17T10:05:00Z",
      "error": null
    }
  ],
  "start_time": "2026-03-17T10:00:00Z",
  "last_update": "2026-03-17T10:08:30Z"
}
```

### 状态值说明
- `pending`: 工作流已创建但尚未开始执行
- `in_progress`: 工作流正在执行中
- `completed`: 工作流全部完成
- `partial_completed`: 工作流部分完成（如在Step 5前取消合并）
- `failed`: 工作流因错误失败，等待恢复

### 状态文件管理规则
1. 每个步骤完成后立即写入
2. 使用原子写入（先写临时文件，再重命名）
3. 出现错误时保留状态文件供恢复
4. 完成后根据配置删除或归档

---

## 产物路径映射表

用于验证每个步骤的产物是否生成：

| 步骤号 | 产物类型 | 路径模式 | 验证方法 |
|--------|----------|----------|----------|
| 1 | PRD分析报告 | `prd/current/output/{feature}-analysis.md` | 检查文件存在 |
| 2 | 变更分析报告 | `prd/current/output/{feature}-change-diff.md` | 检查文件存在 |
| 3 | 测试用例汇总 | `prd/current/output/test-cases/test-case-summary.md` | 检查文件存在 |
| 4 | 评审报告 | `prd/current/output/test-cases/review-report.md` | 检查文件存在 |
| 5 | 全量库更新 + 归档 | `test-cases/` 更新，`prd/archive/{date-feature}/` 创建 | 检查目录存在 |

**注意**：
- {feature} 需要从需求名称转换为 kebab-case 格式，如 "退款需求" → "refund"
- Step 5 的验证较复杂，需要检查归档目录是否创建

---

## 依赖检查规则

当执行部分流程时（如 `--from 3` 或 `--steps 2-4`），需要验证依赖：

| 执行步骤 | 依赖步骤 | 必需的产物 |
|----------|----------|------------|
| 2 | 1 | prd/current/output/{feature}-analysis.md |
| 3 | 2 | prd/current/output/{feature}-change-diff.md |
| 4 | 3 | prd/current/output/test-cases/test-case-summary.md |
| 5 | 4 | prd/current/output/test-cases/review-report.md |

**验证逻辑**：
```
function validate_dependencies(steps_to_execute):
  for step in steps_to_execute:
    if step > 1:
      required_step = step - 1
      required_artifact = get_artifact_path(required_step)
      if not file_exists(required_artifact):
        if not ignore_validation:
          error: "步骤{step}依赖步骤{required_step}的产物：{required_artifact}
                 产物不存在，请先执行步骤{required_step}或使用 --ignore-validation 跳过检查（慎用）"
          return false
        else:
          warning: "⚠ 跳过依赖检查，步骤{step}可能因缺少前置产物而失败"
  return true
```

---

## 质量要求

1. **状态一致性**：状态文件必须始终反映真实的执行状态
2. **原子操作**：状态文件更新必须是原子的，避免并发写入导致损坏
3. **错误透明**：所有错误信息必须清晰地传递给用户，不隐藏问题
4. **可恢复性**：任何中断或失败都必须能够通过 `--resume` 恢复
5. **零侵入**：不修改子skills的内部逻辑，完全通过外部调用和文件检查
6. **用户友好**：进度显示清晰，错误提示具体，操作选项明确

---

## 失败处理

如遇以下情况，优先停止并说明原因：

1. **状态文件损坏**：
   - 无法解析 JSON
   - 缺少必需字段
   - 数据类型错误
   → 提示："状态文件损坏，建议删除后重新执行：rm prd/current/.workflow-state.json"

2. **并发冲突**：
   - 检测到其他工作流正在执行
   → 提示："当前不支持并发执行，请等待或终止现有工作流"

3. **依赖缺失**：
   - 前置步骤产物不存在
   → 提示："步骤{N}依赖缺失，请先执行步骤{N-1}"

4. **子Skill调用失败**：
   - 子skill返回错误
   - 预期产物未生成
   → 进入错误处理流程，提供恢复选项

5. **权限不足**：
   - 无法读写必要目录
   → 提示："权限不足，请检查文件系统权限"

**不要**：
- 不要伪造成功状态
- 不要静默跳过失败步骤
- 不要在未确认的情况下修改全量用例库

---

## 使用示例

### 示例1：标准完整流程
```bash
/qa-workflow 会员订阅需求

# 输出：
🚀 QA 测试用例工作流已启动：会员订阅需求

执行计划：
  → [1/5] PRD 分析
  ○ [2/5] 变更分析
  ○ [3/5] 用例生成
  ○ [4/5] 用例评审
  ○ [5/5] 合并归档

[1/5] 正在执行 PRD 分析...
（调用 /qa-prd-analysis 会员订阅需求）
✓ PRD 分析完成
  - 报告：prd/current/output/member-subscription-analysis.md
  - 功能点：12个

[2/5] 正在执行变更分析...
...
（依次执行所有步骤）
```

### 示例2：部分执行（只生成用例）
```bash
/qa-workflow --steps 1-3 活动页面改版

# 只执行前3步，完成后停止
```

### 示例3：从中间步骤开始
```bash
/qa-workflow --from 4 退款需求

# 假设步骤1-3已完成，从步骤4开始执行
```

### 示例4：断点恢复
```bash
# 执行到步骤3时失败
/qa-workflow 退款需求
# ... 步骤3失败 ...
# 用户选择 abort

# 修复问题后恢复
/qa-workflow --resume

# 输出：
检测到未完成的工作流：退款需求
上次执行到步骤3失败，是否继续？
...
```

---

## 目录结构规范

本工作流要求项目遵循特定的目录结构，以确保各个步骤能够正确执行和产物能够正确保存。

### 完整目录结构

```
项目根目录/
├── prd/                           # 需求文档目录
│   ├── current/                   # 当前需求目录（必需）
│   │   ├── {需求名称}.md         # PRD文档（必需）
│   │   ├── images/                # PRD引用的图片（必需）
│   │   └── output/                # 工作流产物输出目录（自动创建）
│   │       ├── {feature}-analysis.md         # Step 1产物
│   │       ├── {feature}-change-diff.md      # Step 2产物
│   │       └── test-cases/        # Step 3-4产物目录
│   │           ├── test-case-summary.md
│   │           ├── review-report.md
│   │           └── {module}-cases.md
│   └── archive/                   # 归档需求目录（必需）
│       └── YYYY-MM-DD-{feature}/  # Step 5归档产物
│
├── test-cases/                    # 全量测试用例库（必需）
│   ├── index.md                   # 用例库总索引
│   ├── {module1}/                 # 模块目录
│   │   ├── index.md              # 模块索引
│   │   └── {feature}-cases.md    # 用例文件
│   └── {module2}/
│       └── ...
│
├── glossary/                      # 业务术语表（强烈推荐）
│   ├── business-terms.md          # 业务术语定义
│   ├── technical-terms.md         # 技术术语定义
│   └── abbreviations.md           # 缩写说明
│
└── standards/                     # 测试规范文档（推荐）
    ├── test-case-template.md     # 用例模板
    └── review-checklist.md       # 评审清单

```

### 目录说明

| 目录 | 说明 | 必需性 |
|------|------|--------|
| `prd/current/` | 存放当前正在处理的需求PRD文档 | ✅ 必需 |
| `prd/current/output/` | 工作流各步骤的产物输出目录 | ✅ 必需（自动创建） |
| `prd/archive/` | 已完成需求的归档目录 | ✅ 必需（步骤5） |
| `test-cases/` | 全量测试用例库，所有用例的最终存储位置 | ✅ 必需（步骤5） |
| `glossary/` | 业务术语表，用于PRD分析时识别专业术语 | 🔶 强烈推荐 |
| `standards/` | 测试规范文档，提供用例编写和评审标准 | 💡 推荐 |

### 首次使用配置

如果是首次使用本工作流，建议按以下步骤初始化目录结构：

1. **创建必需目录**：
```bash
mkdir -p prd/current/images
mkdir -p prd/current/output/test-cases
mkdir -p prd/archive
mkdir -p test-cases
mkdir -p glossary
mkdir -p standards
```

2. **创建基础文件**：
```bash
# 创建用例库索引
cat > test-cases/index.md << 'EOF'
# 测试用例库索引

## 模块列表
- 待添加...

## 统计信息
- 总模块数：0
- 总用例数：0
- 最近更新：初始化
EOF

# 创建术语表模板
cat > glossary/business-terms.md << 'EOF'
# 业务术语表

## 术语列表
<!-- 示例：
### 订单
- **定义**：用户下单购买商品或服务的记录
- **英文**：Order
- **相关术语**：订单号、订单状态
-->
EOF
```

3. **放置PRD文档**：
```bash
# 将PRD文档放入 prd/current/ 目录
cp your-prd.md prd/current/退款需求.md

# 如果PRD中有图片，放入 images/ 目录
cp prd-images/* prd/current/images/
```

4. **执行工作流**：
```bash
/qa-workflow 退款需求
```

## 参考文档

- 状态文件详细Schema：`workflow-state-schema.md`
- 错误处理详细指南：`error-handling-guide.md`
- 子Skills文档：
  - `../qa-prd-analysis/SKILL.md`
  - `../qa-change-diff/SKILL.md`
  - `../qa-testcase-generation/SKILL.md`
  - `../qa-testcase-review/SKILL.md`
  - `../qa-testcase-merge/SKILL.md`
