# 更新日志 (Changelog)

本文档记录 QA 测试用例工作流插件的所有重要变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [Unreleased]

### 计划中的功能
- 支持多个需求并发执行
- 执行历史查询功能 (`--history`)
- 配置文件支持 (`.qa-workflow-config.yml`)
- Web 可视化 Dashboard
- 与 Jira/GitLab/TestRail 集成
- 智能推荐：基于历史相似需求推荐用例模板
- 支持更多 Agent 平台：GitHub Copilot、Tabnine

---

## [0.1.0] - 2026-03-18

### 🎉 首次发布

这是 QA 测试用例工作流插件的首个公开版本，提供完整的测试用例管理自动化能力。

### ✨ 新增功能

#### 核心工作流
- **总控工作流** (`/qa-workflow`)：一键执行完整的 5 步测试用例管理流程
  - Step 1: PRD 分析
  - Step 2: 变更影响分析
  - Step 3: 测试用例生成
  - Step 4: 用例质量评审
  - Step 5: 用例合并归档

#### 独立 Skills
- **PRD 分析** (`/qa-prd-analysis`)：分析 PRD 文档，提取功能点、测试关注点和风险项
- **变更分析** (`/qa-change-diff`)：分析需求变更对存量用例的影响
- **用例生成** (`/qa-testcase-generation`)：基于分析结果自动生成结构化测试用例
- **用例评审** (`/qa-testcase-review`)：自动评审用例质量，识别问题并生成评审报告
- **合并归档** (`/qa-testcase-merge`)：将新用例合并到全量库，归档当前需求

#### 执行控制
- **部分执行**：支持 `--steps START-END`、`--from START`、`--only STEP1,STEP2` 参数
- **断点恢复**：支持 `--resume` 从中断处继续执行
- **错误处理**：智能错误检测，提供 retry/skip/abort 恢复选项
- **状态管理**：自动保存执行状态到 `prd/current/.workflow-state.json`

#### 用户体验
- **进度可视化**：实时显示执行进度，使用 ✓/→/○/⚠/✗ 图标表示状态
- **目录验证**：执行前检查必需目录，缺失时提供自动创建选项
- **交互式确认**：Step 5 合并前暂停，显示合并计划并请求用户确认
- **详细日志**：支持 `--verbose` 显示详细执行日志

#### 质量保证
- **术语表支持**：`glossary/` 目录下维护业务术语，提升 PRD 分析准确性
- **规范支持**：`standards/` 目录下自定义用例模板和评审规则
- **产物验证**：每步执行后验证产物文件是否生成
- **依赖检查**：部分执行时检查前置步骤产物是否存在

### 📚 文档

- **README.md**：完整的项目介绍、安装指南、使用示例、最佳实践
- **CLAUDE.md**：Claude Code 专用使用指南，包含配置、高级用法、常见问题
- **workflow-state-schema.md**：状态文件 Schema 详细说明
- **error-handling-guide.md**：错误处理详细指南（500+ 行）

### 🔧 配置文件

- **.claude-plugin/manifest.json**：Claude Code 插件配置
- **.codebuddy-plugin/config.yaml**：CodeBuddy 插件配置
- **图标和资源**：`.claude-plugin/icon.svg`

### 🏗️ 架构设计

- **零侵入式调用**：总控 Skill 通过 Skill 工具调用子 Skills，不修改子 Skills 内部逻辑
- **状态持久化**：使用 JSON 文件保存工作流状态，支持断点恢复
- **原子写入**：状态文件采用临时文件 + 原子重命名模式，避免损坏
- **两阶段执行**：Step 5 采用预览 → 确认 → 执行模式，确保安全性

### 🎯 支持的平台

- ✅ Claude Code (≥ 4.0.0)
- ✅ CodeBuddy (≥ 2.0.0)
- ✅ Cursor
- 🔄 其他平台持续适配中

### 📊 统计信息

- **代码行数**：约 3000+ 行（Skills + 文档）
- **文档字数**：约 20000+ 字
- **Skills 数量**：6 个（1 个总控 + 5 个子 Skills）
- **支持参数**：8 个命令行参数
- **错误场景**：10+ 种常见错误及解决方案

### 🐛 已知问题

- 当前版本不支持多个需求并发执行（检测到并发时会提示）
- 大型 PRD（> 5000 行）分析可能耗时较长（建议分段分析）
- 状态文件损坏时需要手动删除重新执行

### ⚠️ 破坏性变更

无（首次发布）

### 🔄 迁移指南

无需迁移（首次发布）

---

## 版本规范说明

### 版本号格式

遵循 [语义化版本 2.0.0](https://semver.org/lang/zh-CN/)：

```
主版本号.次版本号.修订号 (MAJOR.MINOR.PATCH)
```

- **主版本号 (MAJOR)**：不兼容的 API 变更
- **次版本号 (MINOR)**：向下兼容的功能新增
- **修订号 (PATCH)**：向下兼容的问题修正

### 变更类型

- **Added** (新增)：新功能
- **Changed** (变更)：现有功能的变化
- **Deprecated** (弃用)：即将移除的功能
- **Removed** (移除)：已移除的功能
- **Fixed** (修复)：问题修复
- **Security** (安全)：安全相关的修复

---

## 如何贡献

如果你发现问题或有改进建议，欢迎：

1. 提交 Issue：[GitHub Issues](https://github.com/run-noob/qa-testcase-workflow/issues)
2. 提交 Pull Request：[贡献指南](README.md#贡献指南)
3. 参与讨论：[GitHub Discussions](https://github.com/run-noob/qa-testcase-workflow/discussions)

---

## 致谢

感谢所有贡献者和早期用户的反馈！

特别感谢：
- Claude Code 团队提供的优秀平台和支持
- CodeBuddy 团队的插件生态支持
- 测试工程师社区的宝贵建议

---

[Unreleased]: https://github.com/run-noob/qa-testcase-workflow/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/run-noob/qa-testcase-workflow/releases/tag/v0.1.0
