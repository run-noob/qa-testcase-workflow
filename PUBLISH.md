# 插件配置
---

## 插件市场发布配置

本项目支持发布到多个Agent插件市场，以下是配置指南。

### 支持的插件市场

1. **Claude Code Plugin Marketplace**
   - 官方市场：[Claude Code Plugins](https://marketplace.claude.com)
   - 配置目录：`.claude-plugin/`

2. **CodeBuddy Plugin Marketplace**
   - 官方市场：[CodeBuddy Plugins](https://marketplace.codebuddy.ai)
   - 配置目录：`.codebuddy-plugin/`

3. **Cursor Plugin Marketplace**
   - 官方市场：[Cursor Extensions](https://marketplace.cursor.sh)
   - 配置目录：`.cursor/`

### Claude Code 插件配置

在项目根目录创建 `.claude-plugin/` 目录并配置：

**文件：`.claude-plugin/manifest.json`**
```json
{
  "name": "qa-testcase-workflow",
  "version": "1.0.0",
  "displayName": "QA 测试用例工作流",
  "description": "测试工程师测试用例管理的完整工作流自动化，支持 PRD 分析、变更分析、用例生成、评审和归档",
  "author": "zengzhihua",
  "license": "MIT",
  "homepage": "https://github.com/your-repo/qa-testcase-workflow",
  "repository": {
    "type": "git",
    "url": "https://github.com/your-repo/qa-testcase-workflow.git"
  },
  "keywords": [
    "qa",
    "testing",
    "test-case",
    "workflow",
    "automation",
    "prd-analysis",
    "测试用例",
    "测试管理"
  ],
  "category": "testing",
  "skills": [
    "skills/qa-workflow",
    "skills/qa-prd-analysis",
    "skills/qa-change-diff",
    "skills/qa-testcase-generation",
    "skills/qa-testcase-review",
    "skills/qa-testcase-merge"
  ],
  "entrypoint": "skills/qa-workflow/SKILL.md",
  "requirements": {
    "minClaudeVersion": "4.0.0",
    "directories": [
      "prd/current",
      "prd/archive",
      "test-cases",
      "glossary"
    ]
  },
  "documentation": {
    "readme": "README.md",
    "guide": "CLAUDE.md",
    "changelog": "CHANGELOG.md"
  }
}
```

**文件：`.claude-plugin/icon.svg`**
```svg
<!-- 插件图标，建议尺寸 256x256 -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect fill="#4A90E2" width="256" height="256" rx="32"/>
  <text x="128" y="160" font-size="120" text-anchor="middle" fill="white">QA</text>
</svg>
```

### CodeBuddy 插件配置

**文件：`.codebuddy-plugin/config.yaml`**
```yaml
name: qa-testcase-workflow
version: 1.0.0
display_name: "QA 测试用例工作流"
description: "测试工程师测试用例管理的完整工作流自动化"
author: zengzhihua
license: MIT

# 插件类型
type: workflow

# 主入口
main_skill: qa-workflow

# 所有技能列表
skills:
  - name: qa-workflow
    path: skills/qa-workflow
    description: "工作流总控"
    primary: true
  - name: qa-prd-analysis
    path: skills/qa-prd-analysis
    description: "PRD分析"
  - name: qa-change-diff
    path: skills/qa-change-diff
    description: "变更影响分析"
  - name: qa-testcase-generation
    path: skills/qa-testcase-generation
    description: "测试用例生成"
  - name: qa-testcase-review
    path: skills/qa-testcase-review
    description: "用例评审"
  - name: qa-testcase-merge
    path: skills/qa-testcase-merge
    description: "用例合并归档"

# 依赖项
dependencies:
  directories:
    - prd/current
    - prd/archive
    - test-cases
    - glossary

# 标签
tags:
  - testing
  - qa
  - automation
  - workflow
  - test-management

# 文档
docs:
  readme: README.md
  guide: CLAUDE.md
  changelog: CHANGELOG.md
```

### 发布到插件市场

#### 1. Claude Code 插件市场发布

```bash
# 安装 Claude CLI
npm install -g @anthropic/claude-cli

# 登录
claude login

# 发布插件
claude plugin publish .

# 查看发布状态
claude plugin status
```

#### 2. CodeBuddy 插件市场发布

```bash
# 安装 CodeBuddy CLI
npm install -g @codebuddy/cli

# 登录
codebuddy auth login

# 验证插件配置
codebuddy plugin validate

# 发布插件
codebuddy plugin publish .

# 查看发布状态
codebuddy plugin status
```

#### 3. 通用发布检查清单

发布前确保以下内容完整：

- [ ] `README.md` 编写完整（见下方自动生成）
- [ ] `CLAUDE.md` 配置完整（见下方自动生成）
- [ ] `CHANGELOG.md` 记录版本历史
- [ ] 所有 Skills 的 `SKILL.md` 完整且正确
- [ ] 配置文件 manifest.json 或 config.yaml 正确
- [ ] 图标文件准备完毕
- [ ] 示例 PRD 和术语表（可选，但推荐）
- [ ] License 文件（MIT, Apache 2.0 等）
- [ ] 测试通过（至少一个完整流程）

### 插件版本管理

**版本号规范**（遵循语义化版本）：
- `1.0.0` - 主版本号.次版本号.修订号
- 主版本号：不兼容的 API 变更
- 次版本号：向下兼容的功能新增
- 修订号：向下兼容的问题修正

**更新插件**：
```bash
# 更新版本号
# 修改 .claude-plugin/manifest.json 或 .codebuddy-plugin/config.yaml 中的 version

# 重新发布
claude plugin publish .
# 或
codebuddy plugin publish .
```

---
# 发布检查清单 (Publication Checklist)

本文档提供发布 QA 测试用例工作流插件到插件市场前的完整检查清单。

---

## 📋 发布前检查清单

### 1. 核心文档 ✅

- [x] **README.md** - 项目主文档
  - [x] 项目简介完整
  - [x] 安装指南清晰
  - [x] 使用示例丰富
  - [x] 常见问题充分
  - [x] 版本号正确 (v0.1.0)

- [x] **CLAUDE.md** - Claude Code 使用指南
  - [x] 配置说明详细
  - [x] Skills 详解完整
  - [x] 高级用法清晰
  - [x] 故障排查充分

- [x] **CHANGELOG.md** - 版本变更历史
  - [x] 版本号正确 (0.1.0)
  - [x] 发布日期正确 (2026-03-18)
  - [x] 变更内容详细
  - [x] 格式符合规范

- [x] **LICENSE** - 开源许可证
  - [x] 使用 MIT 许可证
  - [x] 版权信息完整

### 2. 配置文件 ✅

- [x] **.claude-plugin/manifest.json**
  - [x] 版本号正确 (0.1.0)
  - [x] Skills 列表完整 (6个)
  - [x] 依赖项正确
  - [x] 作者信息待填写 ⚠️
  - [x] 仓库 URL 待填写 ⚠️

- [x] **.codebuddy-plugin/config.yaml**
  - [x] 版本号正确 (0.1.0)
  - [x] Skills 列表完整 (6个)
  - [x] 配置项详细
  - [x] 作者信息待填写 ⚠️
  - [x] 仓库 URL 待填写 ⚠️

- [x] **.gitignore**
  - [x] 排除临时文件
  - [x] 排除状态文件
  - [x] 保留重要目录

### 3. Skills 定义 ✅

- [x] **skills/qa-workflow/SKILL.md**
  - [x] 总控工作流逻辑完整
  - [x] 目录验证逻辑详细
  - [x] 参数说明清晰
  - [x] 错误处理完善

- [x] **skills/qa-prd-analysis/SKILL.md**
  - [x] PRD 分析流程完整
  - [x] 产物格式明确

- [x] **skills/qa-change-diff/SKILL.md**
  - [x] 变更分析逻辑清晰
  - [x] 差异报告格式明确

- [x] **skills/qa-testcase-generation/SKILL.md**
  - [x] 用例生成流程完整
  - [x] 模板支持清晰

- [x] **skills/qa-testcase-review/SKILL.md**
  - [x] 评审标准明确
  - [x] 问题分级清晰

- [x] **skills/qa-testcase-merge/SKILL.md**
  - [x] 两阶段执行清晰
  - [x] 安全机制完善

### 4. 辅助文档 ✅

- [x] **skills/qa-workflow/workflow-state-schema.md**
  - [x] Schema 定义完整
  - [x] 字段说明详细
  - [x] 示例充分

- [x] **skills/qa-workflow/error-handling-guide.md**
  - [x] 常见错误覆盖充分 (10+)
  - [x] 解决方案详细
  - [x] 恢复策略明确

### 5. 资源文件 ⚠️

- [x] **.claude-plugin/icon.svg**
  - [x] 图标已创建
  - [x] 尺寸正确 (256x256)
  - [x] 格式正确 (SVG)

- [ ] **screenshots/** - 截图目录
  - [ ] workflow-progress.png (工作流进度)
  - [ ] error-handling.png (错误处理)
  - [ ] directory-validation.png (目录验证)

### 6. 测试验证 ⚠️

- [ ] **功能测试**
  - [ ] 完整流程测试 (新需求)
  - [ ] 部分执行测试 (--steps 1-3)
  - [ ] 断点恢复测试 (--resume)
  - [ ] 错误处理测试 (各种失败场景)
  - [ ] 目录验证测试 (缺失目录)

- [ ] **兼容性测试**
  - [ ] Claude Code 测试
  - [ ] CodeBuddy 测试
  - [ ] Cursor 测试
  - [ ] Windows 平台测试
  - [ ] macOS 平台测试
  - [ ] Linux 平台测试

- [ ] **性能测试**
  - [ ] 小型 PRD (< 500 行)
  - [ ] 中型 PRD (500-2000 行)
  - [ ] 大型 PRD (> 2000 行)

### 7. Git 版本管理 ⚠️

- [ ] **Git 仓库**
  - [ ] 创建 Git 仓库
  - [ ] 首次提交所有文件
  - [ ] 创建 v0.1.0 标签
  - [ ] 推送到远程仓库

```bash
# 初始化 Git 仓库
git init

# 添加所有文件
git add .

# 首次提交
git commit -m "chore: initial commit v0.1.0"

# 创建标签
git tag -a v0.1.0 -m "Release version 0.1.0"

# 推送到远程
git remote add origin https://github.com/run-noob/qa-testcase-workflow.git
git push -u origin main
git push --tags
```

### 8. 发布准备 ⚠️

- [ ] **更新配置文件中的占位符**
  - [ ] 替换 `zengzhihua` 为真实姓名
  - [ ] 替换 `1036181341@qq.com` 为真实邮箱
  - [ ] 替换 `your-username` 为 GitHub 用户名
  - [ ] 更新仓库 URL

- [ ] **创建 GitHub Release**
  - [ ] 标题：v0.1.0 - 初始发布
  - [ ] 描述：从 CHANGELOG.md 复制
  - [ ] 附件：插件包 (可选)

- [ ] **准备示例文件** (可选但推荐)
  - [ ] examples/sample-prd.md
  - [ ] examples/sample-glossary.md
  - [ ] examples/sample-testcase.md

---

## 🚀 发布到插件市场

### Claude Code 插件市场

```bash
# 1. 安装 Claude CLI (如果未安装)
npm install -g @anthropic/claude-cli

# 2. 登录
claude login

# 3. 验证配置
claude plugin validate .

# 4. 发布插件
claude plugin publish .

# 5. 查看发布状态
claude plugin status
```

**预期输出**：
```
✓ Plugin validated successfully
✓ Publishing to Claude Code Plugin Marketplace...
✓ Published: qa-testcase-workflow v0.1.0
✓ Marketplace URL: https://marketplace.claude.com/plugins/qa-testcase-workflow
```

### CodeBuddy 插件市场

```bash
# 1. 安装 CodeBuddy CLI (如果未安装)
npm install -g @codebuddy/cli

# 2. 登录
codebuddy auth login

# 3. 验证配置
codebuddy plugin validate

# 4. 发布插件
codebuddy plugin publish .

# 5. 查看发布状态
codebuddy plugin status
```

**预期输出**：
```
✓ Plugin validated successfully
✓ Publishing to CodeBuddy Plugin Marketplace...
✓ Published: qa-testcase-workflow v0.1.0
✓ Marketplace URL: https://marketplace.codebuddy.ai/plugins/qa-testcase-workflow
```

---

## ⚠️ 发布前必须完成的项

以下是**必须**完成的项，否则无法通过市场审核：

### 1. 更新作者信息

**manifest.json**:
```json
"author": {
  "name": "你的真实姓名",
  "email": "你的邮箱",
  "url": "https://github.com/你的用户名"
}
```

**config.yaml**:
```yaml
author:
  name: 你的真实姓名
  email: 你的邮箱
  url: https://github.com/你的用户名
```

### 2. 更新仓库 URL

在以下文件中替换所有 `your-username` 和 `your-repo`：
- manifest.json
- config.yaml
- README.md
- CLAUDE.md
- CHANGELOG.md

使用命令批量替换：
```bash
# macOS/Linux
find . -type f -name "*.json" -o -name "*.yaml" -o -name "*.md" | \
  xargs sed -i '' 's/your-username/actual-username/g'

# Windows (PowerShell)
Get-ChildItem -Recurse -Include *.json,*.yaml,*.md | \
  ForEach-Object { (Get-Content $_) -replace 'your-username', 'actual-username' | Set-Content $_ }
```

### 3. 创建截图

在 `screenshots/` 目录下添加以下截图：

1. **workflow-progress.png**
   - 展示工作流执行进度
   - 包含 5 个步骤的进度指示
   - 显示当前步骤和已完成步骤

2. **error-handling.png**
   - 展示错误处理界面
   - 包含 retry/skip/abort 选项
   - 显示详细错误信息

3. **directory-validation.png**
   - 展示目录验证提示
   - 包含自动创建选项
   - 显示完整的目录结构说明

截图要求：
- 分辨率：1920x1080 或 1280x720
- 格式：PNG
- 文件大小：< 1MB

### 4. 至少一次完整测试

执行以下测试流程并记录结果：

```bash
# 1. 创建测试目录
mkdir -p test-project && cd test-project

# 2. 复制 skills 目录
cp -r ../skills .

# 3. 执行工作流（会自动创建目录）
# 在 Claude Code 中执行：
/qa-workflow 测试需求

# 4. 验证结果
# - 检查所有目录是否创建
# - 检查所有产物文件是否生成
# - 检查状态文件是否正确
# - 检查归档是否成功
```

---

## 📝 发布后操作

### 1. 宣传推广

- [ ] 在 GitHub 仓库添加 README badge
- [ ] 在 Claude Code 社区分享
- [ ] 在 CodeBuddy 社区分享
- [ ] 撰写博客文章介绍
- [ ] 在测试工程师社区宣传

### 2. 用户反馈收集

- [ ] 监控 GitHub Issues
- [ ] 监控插件市场评论
- [ ] 收集用户使用反馈
- [ ] 建立用户交流群

### 3. 持续维护

- [ ] 定期检查依赖更新
- [ ] 修复用户报告的 Bug
- [ ] 根据反馈优化功能
- [ ] 规划下一版本 (v0.2.0)

---

## 🔄 版本更新流程

当需要发布新版本时：

1. **更新 CHANGELOG.md**
```markdown
## [0.2.0] - YYYY-MM-DD

### Added
- 新功能描述

### Fixed
- Bug 修复描述
```

2. **更新版本号**
- manifest.json: `"version": "0.2.0"`
- config.yaml: `version: 0.2.0`
- README.md: 版本徽章和更新日志

3. **Git 标签**
```bash
git add .
git commit -m "chore: bump version to 0.2.0"
git tag -a v0.2.0 -m "Release version 0.2.0"
git push && git push --tags
```

4. **发布到市场**
```bash
claude plugin publish .
codebuddy plugin publish .
```

---

## 📞 需要帮助？

如有任何问题，请：

- 查阅 [README.md](README.md) 和 [CLAUDE.md](CLAUDE.md)
- 提交 [GitHub Issue](https://github.com/run-noob/qa-testcase-workflow/issues)
- 发送邮件至：1036181341@qq.com

---

**祝发布顺利！🎉**
