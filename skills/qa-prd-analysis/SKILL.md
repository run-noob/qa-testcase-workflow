---
name: qa-prd-analysis
description: 分析 prd/{feature-dir} 下的 PRD 文档，输出结构化需求分析报告、功能点、测试关注点与风险项
---

# QA PRD 分析 Skill

## 适用场景
当用户要求分析 PRD、拆解需求、识别测试关注点、输出需求分析报告时使用本 Skill。

建议调用示例：
- `/qa-prd-analysis prd/退款需求/退款需求.md`
- `/qa-prd-analysis 退款需求`

## 输入参数
- `$ARGUMENTS` 可选。
- 如果传入的是文件路径，优先分析该文件。
- 如果传入的是需求名，先确认对应的需求目录名，再在 `prd/{feature-dir}/` 下定位主 PRD 文件。
- 如果未传参数，则扫描 `prd/` 下的需求目录，再向用户先确认本次要处理的需求目录。
- 如果需求目录里匹配到多个候选目录或多个候选 PRD 文件，必须先向用户确认，不要自行猜测。

## 强制规则
1. 任务开始前，先读取 `glossary/` 下所有术语文件，建立业务上下文。
2. 优先参考 `skills/qa-prd-analysis/analysis-template.md` 模板。
3. 所有输出使用中文；技术术语保留英文原文，并在必要时附中文解释。
4. 文件名使用 kebab-case。
5. 在正式分析前，必须先确认需求目录名（`feature-dir`），再定位该目录下的主 PRD 文件。
6. 默认约定主 PRD 文件与需求目录同名，例如 `prd/退款需求/退款需求.md`；若不一致，可接受 `{feature-dir}-prd.md` 等命名，但必须先确认。
7. 分析产出写入 `prd/{feature-dir}/output/{feature-name}-analysis.md`。
8. 不要修改 `test-cases/` 全量用例库。
9. 遇到术语表中不存在且无法确定含义的术语，标记为 `[待确认术语: xxx]`，继续分析，不要臆断。
10. 如果 PRD 超过 3000 行，先生成结构化大纲，再按章节分段分析，最后汇总。
11. 如果 PRD 中含有原型图、流程图、截图等图片信息时，且当前模型不支持视觉能力。
    - **严禁**尝试使用 `READ`、打开二进制文件或其他文件读取方式处理图片。
    - **必须**使用图片解析脚本 `prd_image_parser.py`（该脚本使用的是专门的多模态模型） 生成图片解析结果并纳入需求分析报告。
12. **严禁直接读取非 Markdown 格式的 PRD 文件**（如 `.docx`、`.pdf`、`.pptx`、`.xlsx`、`.png` 等二进制或 Office 格式文件）。若 PRD 文件不是 `.md` 格式，必须先使用 `doc_convert_to_markdown.py` 脚本将其转换为 Markdown，再读取转换后的 `.md` 文件进行分析。
13. 编号命名规范，所有组件、流程使用统一编号格式：{SystemModule}-{Component}
    - SystemModule: 从系统角度划分的模块，如Trade：交易模块
    - Component：页面下的某一个区块或者子组件（注意划分的颗粒度），如Filter：筛选组件; SubmitBtn: 提交按钮


## 执行流程

### Step 1：定位待分析 PRD
1. 扫描 `prd/` 下的需求目录，排除 `prd/archive/`。
2. 根据用户输入先确认需求目录名；若未传参数且存在多个目录，必须先让用户确认。
3. 在目标目录下扫描 PRD 文件（优先 `.md`，也需关注 `.docx`、`.pdf`、`.pptx`、`.xlsx` 等格式），排除 `output/` 下的产出文件。
4. 优先匹配与目录同名的主 PRD 文件；若有多个候选文件，必须先确认。
5. 确定唯一目标 PRD 文件、`feature-dir` 与 `feature-name`。
6. **格式检查与转换**：若确定的 PRD 文件不是 `.md` 格式，必须先执行文档格式转换脚本将其转为 Markdown，再继续后续分析。严禁跳过转换直接读取非 Markdown 文件。

### Step 2：预处理 PRD

#### 在线文档下载辅助脚本

当 PRD 正文中引用了 `https://doc.weixin.qq.com/` 域名下的腾讯企业微信在线文档链接，说明关键信息在在线文档上，需要将这些在线文档下载到本地再纳入需求分析。

脚本路径：
- `.claude/plugins/marketplaces/qa-plugins/skills/qa-prd-analysis/scripts/wechat_doc_downloader.py`

适用场景：
- PRD 正文中出现了 `https://doc.weixin.qq.com/sheet/...` 或 `https://doc.weixin.qq.com/doc/...` 等在线文档链接
- 在线文档包含了需求功能描述、数据字段定义、流程图说明等 PRD 正文未覆盖的关键信息
- 希望将在线文档下载为本地文件，方便后续离线分析或归档

推荐命令：

```bash
python3 .claude/plugins/marketplaces/qa-plugins/skills/qa-prd-analysis/scripts/wechat_doc_downloader.py \
  "https://doc.weixin.qq.com/sheet/e3_AbYA7wb9AAYCNoSNuQCISQ0aTj0ej" \
  --output-dir prd/{feature-dir}
```

常用参数：
- `doc_url`：必填，腾讯文档 URL，支持 `sheet`、`doc`、`pdf` 三种类型
- `--output-dir` / `-o`：选填，下载文件保存目录，默认为当前目录

注意事项：
- 脚本依赖内置 Cookie 完成认证，若 Cookie 失效或需要验证码，下载将失败，立即终止流程，通知用户手动下载该文档放到需求目录内
- 下载成功后会在指定目录生成对应文件（Excel/Docx/PDF），并在控制台输出本地文件路径
- 如果 PRD 中同时存在图片和在线文档链接，优先并行执行图片解析脚本和文档下载脚本，再汇总分析

#### 所有PRD统一转为Markdown格式

当需求目录下的 PRD 文档为非 Markdown 格式（如 `.docx`、`.xlsx`、`.pptx`、`.pdf`等）时，必须先使用转换脚本将其转为 Markdown，再读取转换后的 `.md` 文件进行分析。

脚本路径：
- `.claude/plugins/marketplaces/qa-plugins/skills/qa-prd-analysis/scripts/doc_convert_to_markdown.py`

适用场景：
- PRD 主文档为 `.docx`、`.pdf`、`.pptx`、`.xlsx` 或图片格式
- 需求目录中不存在同名 `.md` 文件，仅存在二进制/Office 格式文档
- 需要将非 Markdown 文档转为大模型可读的 Markdown 格式

推荐命令：

```bash
python3 .claude/plugins/marketplaces/qa-plugins/skills/qa-prd-analysis/scripts/doc_convert_to_markdown.py \
  prd/{feature-dir}/{feature-name}.docx \
```

常用参数：
- `file`：必填，输入文件路径，支持 PDF/DOCX/PPTX/XLSX/图片
- `--poll-interval`：异步模式轮询间隔秒数（默认: 2）
- `--max-wait`：异步模式最大等待秒数（默认: 120）
- `--health`：仅检查服务健康状态后退出

转换产物：
- 在源文件同目录下生成 `{源文件名}.zip` 中间产物
- 解压后生成 `{源文件名}.md` 和 `images/` 图片目录

使用要求：
- **严禁直接读取非 Markdown 格式的 PRD 文件**（如 docx、pdf、pptx、xlsx、png 等二进制文件），必须先转换为 Markdown 再读取
- 转换完成后，读取生成的 `.md` 文件作为 PRD 正文进行分析

检查并记录：
- 文档格式（原始格式 → Markdown，如有转换）
- 是否包含需求背景/目标
- 是否包含功能描述
- 是否包含 UI 交互说明、流程图或图片引用
- 是否包含接口说明（如有）
- 文档总行数、主要章节数、图片引用数、在线文档引用数

如文档较大：
- 先输出文档结构大纲
- 按章节或模块分段读取
- 每段提炼中间结论，最后统一合并

#### 解析PRD内的图片

当 PRD 中包含图片，且图片承载了页面布局、交互状态、流程流转、字段说明等关键信息时，先运行图片解析脚本，再继续正文分析。

脚本路径：
- `.claude/plugins/marketplaces/qa-plugins/skills/qa-prd-analysis/scripts/prd_image_parser.py`

适用场景：
- PRD 中有 UI 原型图、流程图、架构图、页面截图
- Markdown 正文对图片说明不足，需要从视觉内容补全组件与交互信息
- 只想针对某一张图做深度分析，辅助确认模块边界或流程细节

推荐命令：

```bash
python3 .claude/plugins/marketplaces/qa-plugins/skills/qa-prd-analysis/scripts/prd_image_parser.py \
  --prd-file prd/{feature-dir}/{feature-name}.md
```

常用参数：
- `--prd-file`：必填，目标 PRD Markdown 文件
- `--image-path`：选填，只分析某一张图片时使用，支持相对路径或绝对路径
- `--detail-level`：图片解析深度，可选 `brief`、`standard`、`deep`
- `--force-refresh`：忽略缓存，强制重新生成 PRD 摘要和图片分析结果
- `--include-image-snippet`：在输出中附带原始图片引用语句

默认产物：
- `prd/{feature-dir}/output/{feature-name}-image-analysis.md`
- `prd/{feature-dir}/output/{feature-name}-image-analysis.json`
- `prd/{feature-dir}/output/.cache/prd-image-parser/` 缓存目录

使用要求：
- 阅读图片解析 Markdown 结果，把图片中的页面结构、组件信息、交互状态、流程节点、流程分支、限制条件补充进最终分析报告
- 如果脚本输出了 `[无法识别: xxx]`、错误日志或缺失图片，需要在分析报告中保留不确定性说明，不要自行脑补
- 如果图片很多(>20张)，选择关键图片使用 `--image-path {image_relative_path}` 进行分析


### Step 3：提取需求核心信息与结构化分析

#### 3.1 需求概览
提取如下基本信息：
- 需求名称
- 需求编号/版本（如有）
- PRD 路径
- 需求背景与目标
- 目标用户/角色
- 计划上线时间（如有）

#### 3.2 功能模块清单
梳理需求，按系统模块=>页面=>页面模块/组件进行结构层级划分，包含功能概览、页面结构与交互流等子章节，对于复杂的系统模块另加页面功能层级关系图、页面功能矩阵、页面跳转关系图。若图片解析结果中补充了页面布局、入口出口、显隐条件、状态差异，需要一并合入。

#### 3.3 组件级交互说明
通过标准化的编号与结构化维度，详尽定义页面内各组件的功能描述、优先级、视觉特征表现、交互逻辑，旨在为开发与测试提供精确的组件级功能规格参考。组件的视觉特征、状态变化、按钮可用性、提示文案等，可结合图片解析结果补充。

#### 3.4 核心业务流程
*针对跨多个页面模块组件的复杂业务*，梳理其核心流程。若流程图来自图片，需将节点、分支条件、流转方向转写成文本，不要只引用原图。

#### 3.5 风险与疑问
标记：
- `[需求模糊: xxx，建议确认: xxx]`
- 潜在冲突点
- 可能遗漏场景
- 待补充资料（接口、图片、状态机、角色权限等）

### Step 4:

### Step 4：输出报告

#### 4.1 输出分析报告
分析报告格式结构参考`analysis-template.md`，写入：`prd/{feature-dir}/output/{feature-name}-analysis.md`

#### 4.2 输出澄清项清单
在分析PRD过程中发现需要澄清的业务逻辑问题进行分类整理，写入：`prd/{feature-dir}/output/{feature-name}-clarifications.md`

- A类：核心业务逻辑问题（优先级：P0）
  - 核心流程不明确
  - 功能点缺失或矛盾
  - 业务规则不清晰
  - 数据流转和状态变化不明确

- B类：影响范围问题（优先级：P1）
  - 对现有功能的影响不明确或存在明显冲突
  - 对线上数据兼容性问题处理方案和上线策略

- C类：边界与异常问题（优先级：P2）
  - 异常场景处理策略不明确
  - 业务规则的边界处理不明确
  - 仅在边界或异常条件下有重大影响时才澄清

- D类：安全相关问题（优先级：P2） 
  - 涉及支付、刷单、抽奖活动等资金财产安全问题
  - 涉及法律、法务风险问题
  - 仅在有明显安全风险时才澄清

- E类：性能相关问题（优先级：P3） 
  - 预计的访问量、并发数以及响应时间要求
  - 仅在PRD明确提及性能要求时才澄清

优先处理A、B类问题，澄清清单输出格式参考：
```
# 问题 1：[问题标题]
上下文：
[相关需求描述的简短引用]
疑问：[具体的问题]
为什么重要：
[澄清这个问题对业务逻辑测试的意义]
```

### Step 5：完成汇报
完成后向用户明确反馈：
- 分析报告路径
- PRD 文件路径
- 功能模块和组件数量
- 风险/待确认项数量

## 质量要求
- 结论必须可追溯到 PRD 原文、图片或明确的业务推断。
- 所有在 PRD 中提到的必须在功能模块清单中有所体现。
- 不要输出“正常/异常”这类空泛结论，尽量明确条件与结果。
- 对图片、表格、流程图中的关键信息必须落到分析报告中，而不是只写“见原图”。

## 失败处理
如果无法完成分析，优先说明具体阻塞原因，例如：
- 未找到 PRD 文件
- 找到多个候选文件
- PRD 缺少核心章节
- 图片或附件缺失
- 模块术语/缩写无法确认
