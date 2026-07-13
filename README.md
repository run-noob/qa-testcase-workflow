# QA 测试用例工作流插件

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-brightgreen.svg)](https://claude.ai/code)
[![CodeBuddy](https://img.shields.io/badge/CodeBuddy-Compatible-orange.svg)](https://codebuddy.ai)

测试工程师测试用例管理的完整工作流自动化插件

[功能特性](#功能特性) • [快速开始](#快速开始)  • [文档](#文档)

</div>

---

## 📋 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [工作流程](#工作流程)
- [安装配置](#安装配置)
- [快速开始](#快速开始)
- [目录结构](#目录结构)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

---

## 项目简介

**QA 测试用例工作流插件**是一个为测试工程师设计的完整测试用例管理自动化解决方案，适用于 Claude Code、Cursor、CodeBuddy 等主流 AI Agent 工具。

### 适用场景

- 产品需求测试用例设计与管理
- PRD 文档分析与测试关注点提取
- 测试用例质量评审
- 用例库版本管理与归档

---

## 功能特性

### 🎯 总控工作流（`/qa-testcase-workflow`）

一键执行完整的 4 步测试用例管理流程：

```
PRD分析 → 用例生成 → 用例评审 → 合并归档
```

### 🔍 独立 Skills（灵活调用）

每个步骤都可以单独调用，满足特殊场景需求：

| Skill | 命令 | 功能描述 |
|-------|------|----------|
| **PRD 分析** | `/qa-prd-analysis` | 分析 PRD 文档，提取功能点、测试关注点和风险项 |
| **用例生成** | `/qa-testcase-generation` | 基于分析结果自动生成结构化测试用例 |
| **用例评审** | `/qa-testcase-review` | 自动评审用例质量，识别问题并生成评审报告 |
| **合并归档** | `/qa-testcase-merge` | 将新用例合并到全量库，归档当前需求文档 |

---

## 工作流程

```mermaid
graph LR
    A[PRD文档] --> B[Step 1: PRD分析]
    B --> C[Step 2: 用例生成]
    C --> D[Step 3: 用例评审]
    D --> E[Step 4: 合并归档]
    E --> F[全量用例库]

    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#fff4e1
    style D fill:#fff4e1
    style E fill:#fff4e1
    style F fill:#ffe1e1
```

### 详细流程说明

#### Step 1: PRD 分析
- **输入**：`prd/{feature-dir}/{feature-name}.md`
- **输出**：`prd/{feature-dir}/output/{feature-name}-analysis.md`
- **内容**：功能点清单、测试关注点、涉及模块、风险项、术语说明

#### Step 2: 用例生成
- **输入**：PRD + 分析报告
- **输出**：`prd/{feature-dir}/output/test-cases/*.md`
- **内容**：按模块分类的结构化测试用例（含 P0-P3 优先级）

#### Step 3: 用例评审
- **输入**：生成的测试用例
- **输出**：`prd/{feature-dir}/output/test-cases/review-report.md`
- **内容**：用例质量评分、问题清单、修改建议、评审结论

#### Step 4: 合并归档
- **输入**：评审通过的用例 + 全量用例库
- **输出**：更新 `test-cases/`，归档到 `prd/archive/YYYY-MM-DD-{需求名}/`
- **内容**：新增/修改/废弃用例、更新索引、归档 PRD

---

## 安装配置

### 前置要求

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 最新版本
- Python 3（skill 脚本依赖 python3）
- Git

### 安装方式

#### 方式一：通过 Marketplace 注册安装

```bash
# 1. 添加 Marketplace 源
/plugin marketplace add qa-plugins https://github.com/run-noob/qa-testcase-workflow.git

# 2. 从 Marketplace 安装插件
/plugin install qa-plugins@qa-testcase-workflow
```

#### 方式二：本地手动安装

```bash
# 1. 克隆仓库到本地
git clone https://github.com/run-noob/qa-testcase-workflow.git

# 2. 在项目目录或 Claude Code 中注册本地插件
/plugin marketplace add qa-plugins /path/to/qa-testcase-workflow

# 3. 安装插件
/plugin install qa-plugins@qa-testcase-workflow
```

### 验证安装

```bash
# 查看已安装的插件
/plugin list

```

### 初始化项目结构

首次使用时，在目标项目目录下创建必要的目录结构：

```bash
# 自动创建所有必需目录
mkdir -p prd/archive test-cases glossary standards
```

### 更新插件

```bash
# 更新到最新版本
/plugin update qa-plugins@qa-testcase-workflow

# 或卸载后重新安装
/plugin uninstall qa-plugins@qa-testcase-workflow
```

## 快速开始

1. **放置 PRD 文档**
```bash
# 创建需求目录
mkdir -p prd/退款需求/images prd/退款需求/output/test-cases

# 将主 PRD 文档复制到对应需求目录
cp your-prd.md prd/退款需求/退款需求.md

# 如果 PRD 中有图片，一并复制
cp prd-images/* prd/退款需求/images/
```

2. **执行工作流**
```bash
/qa-prd-analysis 退款需求
/qa-testcase-generation 退款需求
/qa-testcase-review 退款需求
/qa-testcase-merge 退款需求

```

3. **查看结果**
```bash
# 分析报告
cat prd/退款需求/output/退款需求-analysis.md

# 生成的用例
ls prd/退款需求/output/test-cases/

# 评审报告
cat prd/退款需求/output/test-cases/review-report.md
```

---

## 目录结构

完整的项目目录结构规范：

```
项目根目录/
├── prd/                           # 需求文档目录
│   ├── {feature-dir}/                # 单个需求目录（✅ 必需）
│   │   ├── {feature-name}.md         # 主 PRD 文档，通常与目录同名
│   │   ├── images/                # PRD引用的图片
│   │   └── output/                # 工作流产物输出目录
│   │       ├── {feature}-analysis.md  # prd评审分析产出报告
│   │       ├── {feature}-clarifications.md  # prd评审分析产出的澄清项清单
│   │       └── test-cases/
│   └── archive/                   # 归档需求目录（✅ 必需）
│       └── YYYY-MM-DD-{feature}/
│
├── test-cases/                    # 全量测试用例库（✅ 必需）
│   ├── index.md                   # 用例库总索引
│   └── {module}/                  # 模块目录
│       ├── index.md
│       └── {feature}-cases.md
│
├── glossary/                      # 业务术语表（🔶 强烈推荐）
│   ├── business-terms.md
│   └── technical-terms.md
│
└── standards/                     # 测试规范文档（💡 推荐）
    ├── test-case-template.md
    └── review-checklist.md


```

---

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

---

## 致谢

感谢所有贡献者和使用者的支持！

- 特别感谢 Claude Code、CodeBuddy、Cursor 团队提供的优秀平台
- 感谢测试工程师社区提供的宝贵反馈

---

<div align="center">

**如有问题或建议，欢迎提交 Issue 或 PR！**

[GitHub 仓库](https://github.com/run-noob/qa-testcase-workflow) • [问题反馈](https://github.com/run-noob/qa-testcase-workflow/issues)

</div>
