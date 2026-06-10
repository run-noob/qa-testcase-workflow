# QA 测试用例工作流插件

## 项目概述
测试工程师测试用例管理的完整工作流自动化插件，适用于 Claude Code/Cursor/CodeBuddy 等 AI Agent 工具。

## 核心功能
- **完整工作流**：PRD分析 → 变更分析 → 用例生成 → 评审 → 合并归档
- **灵活执行**：支持完整流程、部分执行、断点恢复、单步调试
- **智能容错**：三层错误处理，retry/skip/abort 恢复机制
- **进度可视化**：实时显示执行进度和步骤状态

## Skills 列表
| Skill | 命令 | 功能 |
|-------|------|------|
| 总控工作流 | `/qa-testcase-workflow` | 一键执行完整的 5 步流程 |
| PRD 分析 | `/qa-prd-analysis` | 分析 PRD 文档，提取功能点和测试关注点 |
| 用例生成 | `/qa-testcase-generation` | 基于分析结果自动生成测试用例 |
| 用例评审 | `/qa-testcase-review` | 自动评审用例质量，生成评审报告 |
| 合并归档 | `/qa-testcase-merge` | 将新用例合并到全量库并归档 PRD |

## 目录结构规范
```
项目根目录/
├── prd/
│   ├── {feature-dir}/           # 单个需求目录 (必需)
│   │   ├── {feature-name}.md     # 主 PRD，通常与目录同名
│   │   ├── images/           # PRD 引用的图片
│   │   └── output/           # 工作流产物输出
├── prd/archive/              # 归档需求 (必需)
├── test-cases/               # 全量测试用例库 (必需)
│   └── index.md
├── glossary/                 # 业务术语表 (强烈推荐)
└── skills/                   # 工作流 Skills 定义
```

## 常用命令示例
```bash
# 完整流程
/qa-testcase-workflow 退款需求

# 单独调试某个步骤
/qa-prd-analysis 退款需求
/qa-testcase-generation 退款需求
```

## 注意事项
- 每个需求使用独立目录：`prd/{feature-dir}/`
- 使用需求分析 Skill 时，先确认需求目录名，再定位主 PRD 文件
- 主 PRD 文件名通常与需求目录名保持一致，如 `prd/退款需求/退款需求.md`
- PRD 中图片引用使用相对路径：`![](images/flow.png)`
