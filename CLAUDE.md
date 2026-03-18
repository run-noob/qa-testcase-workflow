# QA 测试用例工作流 - Claude Code 使用指南

本文档为使用 Claude Code 的开发者提供详细的配置和使用指南。

---

## 目录

- [快速开始](#快速开始)
- [项目配置](#项目配置)
- [工作流使用](#工作流使用)
- [Skills 详解](#skills-详解)
- [自定义配置](#自定义配置)
- [常见问题](#常见问题)
- [高级用法](#高级用法)

---

## 快速开始

### 1. 验证安装

确认 Claude Code 已正确识别本项目的 Skills：

```bash
# 在项目目录下执行
claude skills list

# 应该看到以下输出：
# ✓ qa-workflow (QA工作流总控)
# ✓ qa-prd-analysis (PRD分析)
# ✓ qa-change-diff (变更分析)
# ✓ qa-testcase-generation (用例生成)
# ✓ qa-testcase-review (用例评审)
# ✓ qa-testcase-merge (合并归档)
```

### 2. 初始化项目结构

在 Claude Code 中执行：

```
请帮我初始化 QA 测试用例工作流所需的目录结构
```

Claude Code 会自动创建以下目录：
```
prd/current/images/
prd/current/output/test-cases/
prd/archive/
test-cases/
glossary/
standards/
```

### 3. 执行第一个工作流

```
/qa-workflow 退款需求
```

---

## 项目配置

### Claude Code 专用配置

本项目已包含 Claude Code 的配置文件，位于项目根目录。

#### `.claudeignore`

定义 Claude Code 在分析代码时应忽略的文件和目录：

```
# 临时产物
prd/current/output/
prd/current/.workflow-state.json

# 当前需求文档（避免混淆）
prd/current/*.md
prd/current/images/

# 依赖和缓存
node_modules/
.git/
*.log
```

#### `.claude/config.json`（可选）

自定义 Claude Code 行为：

```json
{
  "skills": {
    "qa-workflow": {
      "enabled": true,
      "alias": ["workflow", "qa"],
      "description": "QA测试用例工作流总控"
    },
    "qa-prd-analysis": {
      "enabled": true,
      "alias": ["prd", "analysis"]
    },
    "qa-change-diff": {
      "enabled": true,
      "alias": ["diff", "change"]
    },
    "qa-testcase-generation": {
      "enabled": true,
      "alias": ["gen", "generate"]
    },
    "qa-testcase-review": {
      "enabled": true,
      "alias": ["review"]
    },
    "qa-testcase-merge": {
      "enabled": true,
      "alias": ["merge"]
    }
  },
  "context": {
    "include": [
      "glossary/**/*.md",
      "standards/**/*.md",
      "test-cases/index.md",
      "prd/current/*.md"
    ],
    "exclude": [
      "prd/current/output/**",
      "prd/archive/**"
    ]
  }
}
```

**配置说明**：

- `skills.*.enabled`：是否启用该 Skill
- `skills.*.alias`：Skill 的别名，可以通过 `/alias` 调用
- `context.include`：Claude Code 自动加载的上下文文件
- `context.exclude`：排除的文件，减少 token 消耗

---

## 工作流使用

### 调用方式

在 Claude Code 的对话框中，可以通过以下方式调用工作流：

#### 方式 1：直接调用（推荐）

```
/qa-workflow 退款需求
```

#### 方式 2：使用自然语言

```
请帮我执行完整的测试用例工作流，需求名称是退款需求
```

Claude Code 会自动识别并调用 `/qa-workflow`。

#### 方式 3：使用别名（需配置）

```
/workflow 退款需求
# 或
/qa 退款需求
```

### 交互式确认

工作流在关键步骤会请求确认，Claude Code 会显示交互式提示：

#### 示例：Step 5 合并前确认

```
⚠️  即将执行合并归档 [5/5]

合并计划摘要：
  - 新增用例：42条
  - 修改用例：3条
  - 废弃用例：1条
  - 影响模块：payment、order
  - 归档路径：prd/archive/2026-03-17-refund/

此操作将修改全量用例库并归档当前PRD，是否继续？
  [1] 确认执行
  [2] 查看详细合并计划
  [3] 取消合并
```

**Claude Code 中的操作**：
- 输入数字（如 `1`）并回车
- 或直接回复自然语言（如 "确认执行"、"我要查看详细计划"）

### 状态追踪

工作流执行过程中，可以随时查询状态：

```
请帮我查看当前工作流的执行状态
```

Claude Code 会读取 `prd/current/.workflow-state.json` 并显示：

```
工作流状态：
  需求名称：退款需求
  当前状态：进行中
  当前步骤：3/5 (用例生成)
  已完成步骤：1 (PRD分析), 2 (变更分析)
  失败步骤：无
  开始时间：2026-03-17 10:00:00
  最近更新：2026-03-17 10:15:30
```

---

## Skills 详解

### Skill 1: qa-workflow（总控）

**功能**：一键执行完整的 5 步测试用例管理流程

**调用方式**：
```
/qa-workflow 需求名称 [选项]
```

**常用选项**：

| 选项 | 说明 | 示例 |
|------|------|------|
| `--steps 1-3` | 只执行步骤 1 到 3 | `/qa-workflow --steps 1-3 退款需求` |
| `--from 3` | 从步骤 3 开始执行 | `/qa-workflow --from 3 退款需求` |
| `--only 2,4` | 只执行步骤 2 和 4 | `/qa-workflow --only 2,4 退款需求` |
| `--resume` | 从上次中断处继续 | `/qa-workflow --resume` |
| `--verbose` | 显示详细日志 | `/qa-workflow --verbose 退款需求` |

**Claude Code 增强功能**：

- **智能提示**：如果目录结构不完整，自动提示并询问是否创建
- **上下文感知**：自动加载 glossary 和 standards 作为上下文
- **实时反馈**：每个步骤完成后立即显示结果摘要
- **错误高亮**：失败时高亮显示错误信息和建议

### Skill 2: qa-prd-analysis（PRD 分析）

**功能**：分析 PRD 文档，提取功能点、测试关注点和风险项

**调用方式**：
```
/qa-prd-analysis 需求名称
# 或
/qa-prd-analysis prd/current/退款需求.md
```

**Claude Code 交互**：

1. 如果 `prd/current/` 下有多个 PRD，会显示列表供选择：
```
找到多个 PRD 文档：
  [1] 退款需求.md
  [2] 会员订阅.md
  [3] 活动页面改版.md
请选择要分析的 PRD：
```

2. 如果 PRD 中引用了图片，Claude Code 会自动读取图片：
```
检测到 PRD 中引用了以下图片：
  - images/refund-flow.png (退款流程图)
  - images/ui-mockup.png (UI 界面图)

正在读取图片...
✓ 已读取所有图片
```

### Skill 3: qa-change-diff（变更分析）

**功能**：分析需求变更对存量用例的影响

**调用方式**：
```
/qa-change-diff 需求名称
```

**Claude Code 增强**：

- 自动加载相关模块的存量用例作为上下文
- 如果涉及模块较多（> 3 个），会分批加载避免超出 token 限制
- 显示变更差异的可视化对比

### Skill 4: qa-testcase-generation（用例生成）

**功能**：基于分析结果自动生成结构化测试用例

**调用方式**：
```
/qa-testcase-generation 需求名称
```

**Claude Code 增强**：

- 自动读取 `standards/test-case-template.md` 作为模板
- 生成用例时实时显示进度：
```
正在生成测试用例...
  ✓ 订单模块：15条用例 (P0: 3, P1: 7, P2: 5)
  ✓ 支付模块：12条用例 (P0: 2, P1: 6, P2: 4)
  → 退款模块：生成中...
```

### Skill 5: qa-testcase-review（用例评审）

**功能**：自动评审用例质量，识别问题并生成评审报告

**调用方式**：
```
/qa-testcase-review 需求名称
```

**Claude Code 增强**：

- 自动读取 `standards/review-checklist.md` 作为评审标准
- 评审结果分级显示：
```
评审报告摘要：
  ✓ 致命问题：0个
  ⚠ 严重问题：2个
  ℹ 一般问题：5个
  💡 优化建议：8个

评审结论：有条件通过
```

### Skill 6: qa-testcase-merge（合并归档）

**功能**：将新用例合并到全量库，归档当前需求文档

**调用方式**：
```
/qa-testcase-merge 需求名称
```

**Claude Code 交互**：

1. **Phase A：生成合并计划**
```
正在分析合并影响...
  ✓ 新增用例：42条
  ✓ 修改用例：3条（TC-ORDER-001, TC-ORDER-015, TC-PAY-003）
  ✓ 废弃用例：1条（TC-REFUND-OLD-001）
  ✓ 影响模块：order, payment, refund
  ✓ 用例ID冲突检查：无冲突
```

2. **Phase B：请求确认**
```
合并计划已生成，是否执行？
  [1] 确认执行
  [2] 查看详细合并计划
  [3] 取消合并
```

3. **Phase C：执行合并**（仅在确认后）
```
正在执行合并...
  ✓ 新增用例：42条已追加到 test-cases/
  ✓ 修改用例：3条已更新
  ✓ 废弃用例：1条已标记为 [已废弃]
  ✓ 更新索引：test-cases/index.md
  ✓ 归档PRD：prd/archive/2026-03-17-refund/
```

---

## 自定义配置

### 自定义术语表（Glossary）

在 `glossary/` 目录下维护业务术语，Claude Code 会自动加载：

**示例：`glossary/business-terms.md`**

```markdown
# 业务术语表

## 订单相关

### 订单
- **定义**：用户下单购买商品或服务的记录
- **英文**：Order
- **属性**：订单号、订单状态、订单金额、创建时间
- **状态流转**：待支付 → 已支付 → 已发货 → 已完成
- **相关术语**：订单号、订单流水、子订单

### 订单状态
- **定义**：订单当前所处的业务状态
- **英文**：Order Status
- **枚举值**：
  - `pending`：待支付
  - `paid`：已支付
  - `shipped`：已发货
  - `completed`：已完成
  - `cancelled`：已取消
  - `refunded`：已退款
```

**Claude Code 使用**：
- PRD 分析时自动识别术语
- 用例生成时使用术语的准确定义
- 避免术语歧义导致的理解偏差

### 自定义用例模板（Standards）

在 `standards/test-case-template.md` 定义用例格式：

**示例**：

```markdown
# 测试用例模板

## 基本信息
- **用例ID**：{模块缩写}-{功能缩写}-{序号}
- **用例标题**：{简短描述测试目标}
- **所属模块**：{模块名称}
- **优先级**：P0 | P1 | P2 | P3
- **用例类型**：功能测试 | 接口测试 | 性能测试 | 安全测试

## 前置条件
{列出执行本用例前必须满足的条件}

## 测试步骤
1. {步骤1描述}
2. {步骤2描述}
3. ...

## 预期结果
{每个步骤对应的预期结果}

## 实际结果
{留空，执行时填写}

## 测试数据
{列出测试所需的数据}

## 备注
{补充说明}
```

**Claude Code 使用**：
- 用例生成时严格遵循此模板
- 评审时检查是否符合模板规范

### 自定义评审规则（Standards）

在 `standards/review-checklist.md` 定义评审标准：

**示例**：

```markdown
# 用例评审清单

## 完整性检查
- [ ] 用例ID唯一且符合命名规范
- [ ] 用例标题清晰描述测试目标
- [ ] 前置条件完整列出
- [ ] 测试步骤详细可执行
- [ ] 预期结果明确可验证
- [ ] 测试数据齐全

## 准确性检查
- [ ] 测试步骤与需求一致
- [ ] 预期结果符合PRD描述
- [ ] 边界条件覆盖充分
- [ ] 异常场景考虑全面

## 可执行性检查
- [ ] 步骤描述清晰无歧义
- [ ] 测试数据可获取
- [ ] 前置条件可满足
- [ ] 不依赖特定环境或数据

## 优先级判定
- **P0**：核心功能，必须通过
- **P1**：重要功能，影响主流程
- **P2**：一般功能，影响次要流程
- **P3**：边缘功能，影响体验
```

**Claude Code 使用**：
- 评审时逐项检查清单
- 根据规则自动判定问题等级
- 生成评审报告时引用具体规则

---

## 常见问题

### Q1: Claude Code 无法识别 Skills

**症状**：
```
/qa-workflow 退款需求
# 提示：Unknown command: qa-workflow
```

**解决**：
1. 确认 `skills/` 目录存在且包含 Skills
2. 重启 Claude Code
3. 或手动重新加载 Skills：
```
请重新加载项目的 Skills
```

### Q2: 工作流执行到一半卡住

**症状**：
- 步骤执行中没有任何输出
- Claude Code 界面无响应

**解决**：
1. 检查状态文件：
```
请帮我查看工作流状态文件：prd/current/.workflow-state.json
```

2. 如果状态文件显示 `status: "in_progress"`，可以强制恢复：
```
/qa-workflow --resume
```

3. 如果仍然卡住，删除状态文件重新执行：
```
请删除 prd/current/.workflow-state.json 文件，然后重新执行工作流
```

### Q3: 用例生成质量不理想

**症状**：
- 生成的用例覆盖不全
- 用例步骤不够详细
- 边界条件考虑不足

**解决**：
1. **丰富 PRD 文档**：
   - 补充详细的功能描述
   - 明确列出异常场景和边界条件
   - 添加流程图和状态图

2. **完善术语表**：
   - 补充业务术语定义
   - 明确术语间的关系
   - 添加使用场景说明

3. **自定义用例模板**：
   - 在 `standards/test-case-template.md` 中细化模板
   - 增加必填项和检查项
   - 提供示例用例

4. **分步执行并人工审查**：
```
# 先生成草稿
/qa-workflow --steps 1-3 退款需求

# 人工审查后，调整 PRD 和术语表

# 重新生成
/qa-testcase-generation 退款需求

# 继续后续步骤
/qa-workflow --from 4 退款需求
```

### Q4: 合并时用例 ID 冲突

**症状**：
```
⚠️  用例ID冲突
步骤5合并时检测到以下ID已存在：
  - TC-ORDER-001
  - TC-ORDER-002
```

**解决**：

**方式 1：自动重新编号**
```
/qa-testcase-merge 退款需求
# 提示冲突时选择 "自动重新编号"
```

**方式 2：手动修改**
```
# 打开用例文件
请打开 prd/current/output/test-cases/order-cases.md

# 手动修改冲突的ID
# TC-ORDER-001 → TC-ORDER-101
# TC-ORDER-002 → TC-ORDER-102

# 继续合并
/qa-workflow --from 5 退款需求
```

### Q5: 评审报告过于严格

**症状**：
- 很多"一般问题"其实是可接受的
- 评审结论"未通过"，但实际可以接受

**解决**：

**自定义评审规则**：

编辑 `standards/review-checklist.md`，调整规则严格程度：

```markdown
# 调整前（严格）
- [ ] 每个步骤必须有对应的预期结果

# 调整后（宽松）
- [ ] 关键步骤必须有对应的预期结果（次要步骤可省略）
```

**忽略特定类型的问题**：

在评审时添加说明：
```
/qa-testcase-review 退款需求

# 评审完成后，如果有可接受的问题：
请忽略以下问题类型，重新生成评审报告：
- 用例步骤过于简洁（对于简单功能可接受）
- 缺少测试数据示例（可后续补充）
```

---

## 高级用法

### 使用 Claude Code 的 Memory 功能

Claude Code 支持记忆功能，可以记住项目特定的偏好和规则。

**设置记忆**：
```
请记住以下规则：
1. 本项目的用例ID格式为：{模块}-{功能}-{序号}，例如 ORDER-REFUND-001
2. P0用例必须覆盖核心业务流程
3. 评审时忽略"测试数据过于简单"的提示
4. 合并时默认采用自动重新编号
```

Claude Code 会将这些规则保存到记忆中，后续执行工作流时自动应用。

### 批量处理多个需求

虽然当前版本不支持并发执行，但可以通过脚本批量处理：

**创建脚本**：`batch-workflow.sh`

```bash
#!/bin/bash

# 需求列表
requirements=("退款需求" "会员订阅" "活动页面改版")

for req in "${requirements[@]}"; do
  echo "处理需求：$req"

  # 执行工作流
  claude exec "/qa-workflow $req"

  # 等待完成
  while [ -f "prd/current/.workflow-state.json" ]; do
    sleep 5
  done

  echo "需求 $req 处理完成"
done

echo "所有需求处理完成"
```

**在 Claude Code 中调用**：
```
请执行脚本：./batch-workflow.sh
```

### 集成到 CI/CD 流程

将工作流集成到 CI/CD 中，实现自动化测试用例生成：

**GitHub Actions 示例**：

```yaml
name: QA Workflow CI

on:
  push:
    paths:
      - 'prd/current/*.md'

jobs:
  qa-workflow:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Claude Code
        run: |
          npm install -g @anthropic/claude-cli
          claude login --token ${{ secrets.CLAUDE_TOKEN }}

      - name: Extract requirement name
        id: req
        run: |
          REQ_FILE=$(ls prd/current/*.md | head -n 1)
          REQ_NAME=$(basename "$REQ_FILE" .md)
          echo "name=$REQ_NAME" >> $GITHUB_OUTPUT

      - name: Run QA Workflow
        run: |
          claude exec "/qa-workflow ${{ steps.req.outputs.name }}"

      - name: Commit generated test cases
        run: |
          git config user.name "QA Workflow Bot"
          git config user.email "bot@example.com"
          git add test-cases/
          git commit -m "chore: add test cases for ${{ steps.req.outputs.name }}"
          git push
```

### 自定义 Claude Code Hooks

在 `.claude/hooks/` 目录下创建钩子脚本，在工作流执行前后触发：

**示例：`.claude/hooks/pre-workflow.sh`**

```bash
#!/bin/bash

# 工作流执行前检查
echo "执行前检查..."

# 检查 PRD 文件是否存在
if [ ! -f "prd/current/$1.md" ]; then
  echo "错误：PRD文件不存在"
  exit 1
fi

# 检查 glossary 是否为空
if [ ! "$(ls -A glossary)" ]; then
  echo "警告：术语表为空，可能影响分析质量"
fi

echo "检查完成"
```

**示例：`.claude/hooks/post-workflow.sh`**

```bash
#!/bin/bash

# 工作流执行后操作
echo "执行后操作..."

# 自动提交到 Git
git add test-cases/
git add prd/archive/
git commit -m "feat: add test cases for $1"

# 发送通知
curl -X POST https://hooks.slack.com/... \
  -d "{\"text\": \"QA工作流完成：$1\"}"

echo "操作完成"
```

**在 Claude Code 中启用 Hooks**：

编辑 `.claude/config.json`：

```json
{
  "hooks": {
    "pre-workflow": ".claude/hooks/pre-workflow.sh",
    "post-workflow": ".claude/hooks/post-workflow.sh"
  }
}
```

---

## 总结

本指南涵盖了在 Claude Code 中使用 QA 测试用例工作流的所有关键内容。

**关键要点**：

1. ✅ **Skills 自动识别**：确保 `skills/` 目录结构正确
2. ✅ **上下文管理**：合理配置 `.claude/config.json` 减少 token 消耗
3. ✅ **自定义配置**：通过 glossary 和 standards 提升质量
4. ✅ **交互式确认**：关键步骤人工确认，避免误操作
5. ✅ **状态追踪**：随时查询工作流执行状态
6. ✅ **错误恢复**：使用 `--resume` 从中断处继续

**建议工作流**：

```
1. 放置 PRD → prd/current/{需求名}.md
2. 执行工作流 → /qa-workflow {需求名}
3. 人工确认 → Step 5 合并前检查
4. 查看结果 → test-cases/ 和 prd/archive/
```

如有更多问题，欢迎查阅 [README.md](README.md) 或提交 Issue。
