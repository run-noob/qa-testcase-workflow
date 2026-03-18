# 工作流错误处理指南

## 概述

本文档提供QA测试用例工作流（`/qa-workflow`）在执行过程中可能遇到的常见错误场景及其解决方案。

---

## 常见错误场景

### 场景1：PRD文件未找到

**症状**：
```
✗ [1/5] PRD 分析 执行失败
错误原因：未找到PRD文件
```

**原因**：
- `prd/current/` 目录为空
- PRD文件名与需求名称不匹配
- PRD文件被移动或删除

**解决方案**：
1. 检查PRD文件是否存在：
   ```bash
   ls prd/current/*.md
   ```

2. 如果文件不存在，将PRD文件放入 `prd/current/` 目录

3. 如果文件名不匹配，重新命名或在调用时指定正确的文件路径：
   ```bash
   /qa-prd-analysis prd/current/exact-filename.md
   ```

4. 重试工作流：
   ```bash
   /qa-workflow --resume
   ```

---

### 场景2：术语表缺失

**症状**：
```
✗ [3/5] 用例生成 执行失败
错误原因：未找到必要的术语定义
缺失术语：退款单、退款流水号
```

**原因**：
- `glossary/` 目录下术语表文件不存在或不完整
- 术语表中缺少PRD中使用的业务术语

**解决方案**：
1. 检查术语表文件：
   ```bash
   ls glossary/
   ```

2. 如果术语表不存在，创建 `glossary/business-terms.md`

3. 添加缺失的术语定义：
   ```markdown
   ## 退款单
   定义：用户申请退款后系统生成的凭证...

   ## 退款流水号
   定义：退款操作的唯一标识...
   ```

4. 重试失败的步骤：
   ```bash
   /qa-workflow --resume
   # 选择 [1] retry
   ```

---

### 场景3：用例ID冲突

**症状**：
```
✗ [5/5] 合并归档 执行失败
错误原因：用例ID冲突
冲突ID：OS-REFUND-FT-001
```

**原因**：
- 新生成的用例ID与全量库中已有用例ID重复
- 未正确处理用例编号的自增逻辑

**解决方案**：
1. 查看冲突的用例：
   ```bash
   grep -r "OS-REFUND-FT-001" test-cases/
   ```

2. 手动修改新生成用例的ID：
   - 打开 `prd/current/output/test-cases/` 中的用例文件
   - 将冲突的ID修改为新的编号（如 OS-REFUND-FT-015）
   - 保存文件

3. 重新执行合并：
   ```bash
   /qa-workflow --from 5
   ```

**预防措施**：
- 在用例生成阶段，先检查全量库中已有的最大编号
- 使用自增逻辑生成新ID

---

### 场景4：状态文件损坏

**症状**：
```
✗ 无法加载状态文件
错误原因：JSON解析失败
```

**原因**：
- 状态文件在写入过程中被中断
- 手动编辑状态文件时出错
- 文件系统故障

**解决方案**：

**方案A：尝试修复**（如果你知道如何修复JSON）
```bash
# 1. 备份损坏的文件
cp prd/current/.workflow-state.json prd/current/.workflow-state.backup.json

# 2. 使用文本编辑器修复JSON格式
vim prd/current/.workflow-state.json

# 3. 验证JSON有效性
cat prd/current/.workflow-state.json | jq .

# 4. 继续工作流
/qa-workflow --resume
```

**方案B：删除重新执行**（推荐）
```bash
# 1. 删除损坏的状态文件
rm prd/current/.workflow-state.json

# 2. 重新执行工作流
/qa-workflow 退款需求
```

**注意**：方案B会丢失进度，但最安全。

---

### 场景5：评审未通过但尝试合并

**症状**：
```
✗ [5/5] 合并归档 执行失败
错误原因：评审结论为"不通过"，无法合并
```

**原因**：
- 评审报告中发现严重问题
- 评审结论不是"通过"或"有条件通过"

**解决方案**：
1. 查看评审报告：
   ```bash
   cat prd/current/output/test-cases/review-report.md
   ```

2. 根据评审意见修复用例：
   - 打开用例文件进行修改
   - 修复严重问题和一般问题
   - 补充缺失场景

3. 重新执行评审：
   ```bash
   /qa-testcase-review 退款需求
   ```

4. 如果评审通过，继续合并：
   ```bash
   /qa-workflow --from 5 退款需求
   ```

---

### 场景6：并发执行冲突

**症状**：
```
✗ 无法启动工作流
错误原因：检测到正在进行的工作流：会员订阅需求
当前不支持并发执行
```

**原因**：
- 另一个工作流正在执行
- 上次工作流未正常完成，状态文件残留

**解决方案**：

**情况A：确实有另一个工作流在执行**
- 等待当前工作流完成
- 或者在另一个终端中终止当前工作流（Ctrl+C），然后使用 --resume 恢复

**情况B：上次工作流已结束但状态文件残留**
1. 检查状态文件的最后更新时间：
   ```bash
   ls -lh prd/current/.workflow-state.json
   ```

2. 如果更新时间超过30分钟，可能是僵尸状态：
   ```bash
   # 查看状态内容
   cat prd/current/.workflow-state.json | jq .

   # 如果确认已无用，删除
   rm prd/current/.workflow-state.json
   ```

3. 重新执行工作流：
   ```bash
   /qa-workflow 退款需求
   ```

---

### 场景7：依赖缺失（部分执行时）

**症状**：
```
✗ 无法执行步骤3
错误原因：步骤3依赖步骤2的产物：prd/current/output/refund-change-diff.md
产物不存在，请先执行步骤2
```

**原因**：
- 使用 `--from 3` 但前置步骤未执行
- 前置步骤的产物被手动删除

**解决方案**：

**方案A：执行缺失的前置步骤**
```bash
# 从步骤2开始执行
/qa-workflow --from 2 退款需求
```

**方案B：跳过依赖检查（慎用）**
```bash
# 如果你确认产物实际存在或不需要
/qa-workflow --from 3 --ignore-validation 退款需求
```

**警告**：方案B可能导致后续步骤失败，仅在确认前置产物存在时使用。

---

### 场景8：权限不足

**症状**：
```
✗ [5/5] 合并归档 执行失败
错误原因：权限不足，无法写入 test-cases/
```

**原因**：
- 文件系统权限配置错误
- 目录被其他进程占用

**解决方案**：
1. 检查目录权限：
   ```bash
   ls -ld test-cases/
   ls -ld prd/
   ```

2. 修复权限（如果需要）：
   ```bash
   chmod 755 test-cases/
   chmod 755 prd/
   ```

3. 检查是否有其他进程占用：
   ```bash
   lsof test-cases/
   ```

4. 重试工作流：
   ```bash
   /qa-workflow --resume
   ```

---

### 场景9：产物文件被手动删除

**症状**：
```
✗ [4/5] 用例评审 执行失败
错误原因：找不到用例汇总文件
预期产物：prd/current/output/test-cases/test-case-summary.md
实际状态：文件不存在
```

**原因**：
- 产物文件在工作流执行期间被手动删除
- 产物文件生成失败但状态文件标记为成功（极少见）

**解决方案**：
1. 确认文件是否确实不存在：
   ```bash
   ls prd/current/output/test-cases/
   ```

2. 重新执行生成该产物的步骤：
   ```bash
   /qa-workflow --from 3 --ignore-validation 退款需求
   ```

3. 或者直接单独执行该步骤：
   ```bash
   /qa-testcase-generation 退款需求
   /qa-workflow --from 4 退款需求
   ```

---

### 场景10：工作流执行超时

**症状**：
- 某个步骤执行时间超过预期（如超过30分钟）
- 终端无响应

**原因**：
- PRD文档过大，处理时间长
- 用例数量过多，生成时间长
- 网络或系统资源问题

**解决方案**：
1. 不要强制终止，等待自然完成（如果可以）

2. 如果必须中断（Ctrl+C）：
   - 状态已保存，可以使用 --resume 继续
   ```bash
   /qa-workflow --resume
   ```

3. 如果持续超时，考虑优化：
   - 拆分PRD文档
   - 减少用例数量
   - 检查系统资源

---

## 错误恢复策略

### 策略1：Retry（重试）

**适用场景**：
- 临时性错误（如网络中断）
- 环境问题已修复（如术语表已补充）
- 数据错误已修复（如PRD文件已补充）

**操作**：
```bash
/qa-workflow --resume
# 选择 [1] retry
```

**效果**：
- 从失败的步骤重新开始
- 保留之前完成的步骤
- 不影响已完成的产物

---

### 策略2：Skip（跳过）

**适用场景**：
- 非关键步骤（如步骤2变更分析可能对新需求不适用）
- 临时绕过问题继续执行

**操作**：
```bash
/qa-workflow --resume
# 选择 [2] skip
```

**效果**：
- 标记为跳过，继续下一步
- 后续步骤可能受影响
- 状态文件记录跳过原因

**警告**：
- 不推荐跳过步骤1、3、5（核心步骤）
- 跳过后可能导致后续步骤失败

---

### 策略3：Abort（终止）

**适用场景**：
- 需要手动修复复杂问题
- 需要修改PRD或用例文件
- 需要重新规划执行策略

**操作**：
```bash
/qa-workflow --resume
# 选择 [3] abort
```

**效果**：
- 保存当前状态
- 退出工作流
- 可以手动修复后使用 --resume 继续

---

### 策略4：重新开始

**适用场景**：
- 状态文件损坏无法恢复
- 需求发生重大变更
- 之前的产物全部作废

**操作**：
```bash
# 删除状态文件
rm prd/current/.workflow-state.json

# 可选：清理旧产物
rm -rf prd/current/output/

# 重新执行
/qa-workflow 退款需求
```

**效果**：
- 完全从头开始
- 丢失所有进度
- 重新生成所有产物

---

## 调试方法

### 方法1：查看状态文件

```bash
# 查看完整状态
cat prd/current/.workflow-state.json | jq .

# 查看当前步骤
cat prd/current/.workflow-state.json | jq '.current_step'

# 查看失败步骤
cat prd/current/.workflow-state.json | jq '.failed_steps'

# 查看执行历史
cat prd/current/.workflow-state.json | jq '.execution_history'
```

### 方法2：检查产物文件

```bash
# 查看所有产物
find prd/current/output -type f -name "*.md"

# 检查特定步骤的产物
ls -lh prd/current/output/*-analysis.md
ls -lh prd/current/output/*-change-diff.md
ls -lh prd/current/output/test-cases/
```

### 方法3：单独执行子Skill

```bash
# 单独测试某个步骤
/qa-prd-analysis 退款需求
/qa-change-diff 退款需求
/qa-testcase-generation 退款需求
/qa-testcase-review 退款需求
/qa-testcase-merge 退款需求
```

### 方法4：使用详细模式（未来支持）

```bash
# 显示详细日志
/qa-workflow --verbose 退款需求
```

---

## 最佳实践

### 预防错误

1. **执行前检查**：
   - 确认PRD文件存在
   - 确认术语表完整
   - 确认目录权限正确

2. **分阶段执行**：
   - 先执行前3步验证（`--steps 1-3`）
   - 确认用例质量后再合并

3. **定期备份**：
   - 备份重要的产物文件
   - 备份全量用例库

### 快速恢复

1. **保持冷静**：不要panic删除文件
2. **查看错误信息**：仔细阅读错误提示
3. **检查状态文件**：了解当前进度
4. **选择合适策略**：retry > skip > abort > 重新开始

### 获取帮助

如果以上方法都无法解决问题：

1. 保留现场（不要删除状态文件和产物）
2. 收集以下信息：
   - 错误信息截图
   - 状态文件内容
   - 执行的完整命令
3. 提交Issue或联系技术支持

---

## 常见问题FAQ

### Q1: 可以同时执行多个需求的工作流吗？
**A**: 初期版本不支持并发执行。如需处理多个需求，请依次执行。

### Q2: 工作流中断后，之前完成的步骤会丢失吗？
**A**: 不会。状态文件会记录所有完成的步骤，使用 `--resume` 可以从中断处继续。

### Q3: 可以跳过某些步骤吗？
**A**: 可以使用 `--steps` 或 `--only` 参数指定执行哪些步骤。但要注意依赖关系。

### Q4: 状态文件可以手动编辑吗？
**A**: 不推荐。如果必须编辑，请确保JSON格式正确，并理解每个字段的含义。

### Q5: 如何清理失败的工作流？
**A**: 删除状态文件即可：`rm prd/current/.workflow-state.json`

### Q6: Step 5合并失败会影响全量库吗？
**A**: 不会。合并操作是事务性的，失败时会回滚，不会损坏全量库。

### Q7: 可以重复执行已完成的工作流吗？
**A**: 可以。删除状态文件后重新执行，或者在提示时选择"重新开始"。

### Q8: 工作流执行需要多长时间？
**A**: 通常10-20分钟，取决于PRD大小和用例数量。

---

## 错误码参考（未来支持）

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| E001 | PRD文件未找到 | 检查文件路径 |
| E002 | 术语表缺失 | 补充术语定义 |
| E003 | 用例ID冲突 | 修改冲突ID |
| E004 | 状态文件损坏 | 删除重新执行 |
| E005 | 评审未通过 | 修复用例后重新评审 |
| E006 | 并发冲突 | 等待或删除状态文件 |
| E007 | 依赖缺失 | 执行前置步骤 |
| E008 | 权限不足 | 修复文件系统权限 |
| E009 | 产物文件缺失 | 重新执行生成步骤 |
| E010 | 执行超时 | 优化文档大小或等待 |

---

## 相关文档

- 工作流核心文档：[SKILL.md](SKILL.md)
- 状态文件详解：[workflow-state-schema.md](workflow-state-schema.md)
- 子Skills文档：
  - [../qa-prd-analysis/SKILL.md](../qa-prd-analysis/SKILL.md)
  - [../qa-change-diff/SKILL.md](../qa-change-diff/SKILL.md)
  - [../qa-testcase-generation/SKILL.md](../qa-testcase-generation/SKILL.md)
  - [../qa-testcase-review/SKILL.md](../qa-testcase-review/SKILL.md)
  - [../qa-testcase-merge/SKILL.md](../qa-testcase-merge/SKILL.md)
