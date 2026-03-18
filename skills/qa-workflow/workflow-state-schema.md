# 工作流状态文件 Schema

## 概述

工作流状态文件用于追踪QA测试用例工作流的执行状态，支持断点恢复、错误处理和进度监控。

## 文件位置

```
prd/current/.workflow-state.json
```

**特性**：
- 临时文件，仅在工作流执行期间存在
- 工作流完成后自动删除（或移动到归档）
- 不纳入版本控制（建议添加到 .gitignore）
- 单个需求独占，不支持并发执行（初期版本）

---

## Schema定义

### 完整示例

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
      "duration_seconds": 300,
      "error": null
    },
    {
      "step": 2,
      "skill": "qa-change-diff",
      "status": "completed",
      "start_time": "2026-03-17T10:05:30Z",
      "end_time": "2026-03-17T10:08:00Z",
      "duration_seconds": 150,
      "error": null
    }
  ],
  "start_time": "2026-03-17T10:00:00Z",
  "last_update": "2026-03-17T10:08:30Z",
  "end_time": null
}
```

---

## 字段详解

### workflow_version (string, 必需)
工作流版本号，用于兼容性检查。

**当前版本**：`"1.0"`

**用途**：未来如果状态文件格式变更，可通过版本号识别并迁移。

### feature_name (string, 必需)
当前工作流处理的需求名称。

**示例**：`"退款需求"`, `"会员订阅需求"`

**用途**：
- 用于显示进度信息
- 用于并发冲突检测
- 用于生成产物文件名

### status (enum, 必需)
工作流当前状态。

**枚举值**：
| 值 | 说明 | 何时设置 |
|----|------|----------|
| `"pending"` | 已创建但未开始 | 初始化时 |
| `"in_progress"` | 正在执行中 | 开始执行第一个步骤时 |
| `"completed"` | 全部完成 | 所有步骤成功完成时 |
| `"partial_completed"` | 部分完成 | 用户在Step 5前取消合并时 |
| `"failed"` | 失败，等待恢复 | 任一步骤失败时 |

**状态转换图**：
```
pending → in_progress → completed
              ↓
            failed → in_progress (retry)
              ↓
          partial_completed
```

### current_step (number, 必需)
当前正在执行或即将执行的步骤号。

**取值范围**：`1-5`

**语义**：
- 如果 status="in_progress"：表示当前执行到哪一步
- 如果 status="completed"：等于 total_steps
- 如果 status="failed"：表示失败的步骤号

### total_steps (number, 必需)
工作流总步骤数。

**固定值**：`5`

**用途**：用于计算进度百分比（current_step / total_steps）

### completed_steps (array of numbers, 必需)
已成功完成的步骤列表。

**示例**：`[1, 2, 4]` 表示步骤1、2、4已完成，步骤3可能被跳过或失败

**用途**：
- 判断某个步骤是否已完成
- 计算完成进度
- 支持断点恢复

### failed_steps (array of numbers, 必需)
执行失败的步骤列表。

**示例**：`[3]` 表示步骤3失败

**用途**：
- 显示失败信息
- 支持错误恢复（retry）
- 审计和调试

### skipped_steps (array of numbers, 必需)
被用户主动跳过的步骤列表。

**示例**：`[2]` 表示步骤2被跳过

**用途**：
- 显示警告信息
- 记录非标准执行路径
- 审计

### artifacts (object, 必需)
每个步骤生成的产物文件路径。

**结构**：
```json
{
  "step1_analysis": "prd/current/output/refund-analysis.md",
  "step2_change_diff": "prd/current/output/refund-change-diff.md",
  "step3_testcases": "prd/current/output/test-cases/",
  "step4_review": "prd/current/output/test-cases/review-report.md",
  "step5_merge": "prd/archive/2026-03-17-refund/"
}
```

**字段说明**：
- 未执行的步骤值为 `null`
- 路径为相对于项目根目录的路径
- Step 3 和 5 可能是目录路径

**用途**：
- 依赖检查（验证产物是否存在）
- 显示产物路径给用户
- 支持断点恢复

### execution_history (array of objects, 必需)
每个步骤的执行历史记录。

**单个记录结构**：
```json
{
  "step": 1,
  "skill": "qa-prd-analysis",
  "status": "completed",
  "start_time": "2026-03-17T10:00:00Z",
  "end_time": "2026-03-17T10:05:00Z",
  "duration_seconds": 300,
  "error": null
}
```

**字段说明**：
- `step` (number): 步骤号（1-5）
- `skill` (string): 调用的子skill名称
- `status` (enum): 该步骤的状态（"completed", "failed", "skipped"）
- `start_time` (ISO8601 string): 开始时间
- `end_time` (ISO8601 string): 结束时间（进行中为null）
- `duration_seconds` (number): 执行耗时（秒）
- `error` (string | null): 错误信息（如有）

**用途**：
- 审计和追踪
- 性能分析（每步耗时）
- 错误诊断

### start_time (ISO8601 string, 必需)
工作流开始时间。

**格式**：`"2026-03-17T10:00:00Z"` (UTC时间)

**用途**：
- 计算总耗时
- 审计和日志

### last_update (ISO8601 string, 必需)
状态文件最后更新时间。

**格式**：`"2026-03-17T10:08:30Z"` (UTC时间)

**用途**：
- 检测状态文件是否失效（如超过24小时未更新）
- 并发冲突检测

### end_time (ISO8601 string | null, 必需)
工作流结束时间。

**取值**：
- 进行中：`null`
- 已完成/失败：`"2026-03-17T10:30:00Z"`

**用途**：
- 计算总耗时
- 判断工作流是否结束

---

## 状态转换规则

### 初始化
```json
{
  "workflow_version": "1.0",
  "feature_name": "{用户输入}",
  "status": "pending",
  "current_step": 1,
  "total_steps": 5,
  "completed_steps": [],
  "failed_steps": [],
  "skipped_steps": [],
  "artifacts": {
    "step1_analysis": null,
    "step2_change_diff": null,
    "step3_testcases": null,
    "step4_review": null,
    "step5_merge": null
  },
  "execution_history": [],
  "start_time": "{当前时间}",
  "last_update": "{当前时间}",
  "end_time": null
}
```

### 步骤开始
```
更新字段：
- status = "in_progress"
- current_step = N
- execution_history 添加新记录：
  {
    "step": N,
    "skill": "{skill_name}",
    "status": "in_progress",
    "start_time": "{当前时间}",
    "end_time": null,
    "duration_seconds": 0,
    "error": null
  }
- last_update = "{当前时间}"
```

### 步骤成功
```
更新字段：
- completed_steps.push(N)
- current_step = N + 1
- artifacts["stepN_xxx"] = "{产物路径}"
- execution_history[N-1] 更新：
  {
    "status": "completed",
    "end_time": "{当前时间}",
    "duration_seconds": {计算耗时}
  }
- last_update = "{当前时间}"
```

### 步骤失败
```
更新字段：
- status = "failed"
- failed_steps.push(N)
- execution_history[N-1] 更新：
  {
    "status": "failed",
    "end_time": "{当前时间}",
    "duration_seconds": {计算耗时},
    "error": "{错误信息}"
  }
- last_update = "{当前时间}"
```

### 步骤跳过
```
更新字段：
- skipped_steps.push(N)
- current_step = N + 1
- execution_history[N-1] 更新：
  {
    "status": "skipped",
    "end_time": "{当前时间}",
    "duration_seconds": 0,
    "error": "User skipped this step"
  }
- last_update = "{当前时间}"
```

### 工作流完成
```
更新字段：
- status = "completed" (或 "partial_completed")
- current_step = total_steps
- end_time = "{当前时间}"
- last_update = "{当前时间}"
```

---

## 文件操作规范

### 读取
```
1. 检查文件是否存在
2. 读取文件内容
3. 解析JSON
4. 验证schema（检查必需字段）
5. 检查workflow_version兼容性
6. 返回状态对象
```

### 写入（原子操作）
```
1. 构造完整的状态对象
2. 序列化为JSON（带缩进，便于阅读）
3. 写入临时文件：prd/current/.workflow-state.tmp.json
4. 验证临时文件有效性
5. 原子重命名：.tmp.json → .workflow-state.json
6. 删除临时文件（如果重命名失败）
```

**为什么使用原子写入**：
- 避免并发写入导致文件损坏
- 避免写入过程中断导致部分数据
- 保证状态文件始终可读

### 删除
```
1. 确认工作流已完成（status="completed"）
2. 可选：备份到归档目录
3. 删除文件：prd/current/.workflow-state.json
```

---

## 错误处理

### 文件不存在
**场景**：使用 --resume 但状态文件不存在

**处理**：提示用户"未找到状态文件，无法恢复工作流"

### 文件损坏（JSON解析失败）
**场景**：状态文件格式错误或内容损坏

**处理**：
1. 提示："状态文件损坏，无法解析"
2. 显示文件路径
3. 建议："删除文件重新执行：rm prd/current/.workflow-state.json"
4. 可选：尝试读取部分字段进行恢复

### 版本不兼容
**场景**：workflow_version 不是当前支持的版本

**处理**：
1. 提示："状态文件版本不兼容（{version}），当前支持版本：1.0"
2. 建议迁移或删除重新执行

### 并发冲突
**场景**：检测到其他工作流正在执行

**处理**：
1. 读取状态文件的 feature_name 和 last_update
2. 检查 last_update 是否在最近（如30分钟内）
3. 如果是：提示"检测到正在进行的工作流：{feature_name}"
4. 如果否：可能是僵尸状态，询问是否覆盖

---

## 最佳实践

### 开发者建议
1. **每个步骤完成后立即写入**，不要批量写入
2. **使用原子写入**，避免文件损坏
3. **记录详细的错误信息**，便于调试
4. **定期清理失效状态文件**（如超过24小时未更新）

### 用户建议
1. **不要手动编辑**状态文件，除非明确知道自己在做什么
2. **不要手动删除**正在执行的工作流的状态文件
3. **如果工作流卡死**，可以删除状态文件重新执行，但会丢失进度

---

## 调试与审计

### 查看状态文件
```bash
cat prd/current/.workflow-state.json
```

### 美化输出
```bash
cat prd/current/.workflow-state.json | jq .
```

### 检查特定字段
```bash
# 查看当前状态
cat prd/current/.workflow-state.json | jq '.status'

# 查看已完成步骤
cat prd/current/.workflow-state.json | jq '.completed_steps'

# 查看执行历史
cat prd/current/.workflow-state.json | jq '.execution_history'
```

### 手动修复（慎用）
如果状态文件需要修复，可以：
1. 备份原文件
2. 使用 jq 或文本编辑器修改
3. 验证JSON格式有效性
4. 使用 --resume 继续执行

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-03-17 | 初始版本，支持基础工作流状态追踪 |

---

## 相关文档

- 工作流核心文档：`SKILL.md`
- 错误处理指南：`error-handling-guide.md`
