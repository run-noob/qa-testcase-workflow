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

## 自定义指令加载

执行本 Skill 前，按以下顺序读取并合并指令：

1. 本文件中的默认指令；
2. 项目根目录 `.qa-testcase-workflow/qa-prd-analysis.md`（项目级共享规则）；
3. 项目根目录 `.qa-testcase-workflow.local/qa-prd-analysis.md`（个人级规则）。

项目根目录是包含当前项目 `prd/`、`test-cases/` 目录的目录。自定义文件不存在时跳过，不报错；

冲突时按以下优先级执行：本次对话明确指令 > `.qa-testcase-workflow.local/` > `.qa-testcase-workflow/` > 本 Skill 默认指令。自定义指令不得关闭或削弱核心安全约束，包括安全的文件格式转换、图片处理、需求目录确认、术语不确定性标记，以及不得臆断需求事实；无法安全应用的自定义内容必须忽略并说明原因。

同一规则在项目级和个人级文件中冲突时采用个人级内容；两级文件中的追加规则均保留并同时生效。

## 输入参数
- `$ARGUMENTS` 可选。
- 如果传入的是文件路径，优先分析该文件。
- 如果传入的是需求名，先确认对应的需求目录名，再在 `prd/{feature-dir}/` 下定位主 PRD 文件。
- 如果未传参数，则扫描 `prd/` 下的需求目录，再向用户先确认本次要处理的需求目录。

## 强制规则
1. 在正式分析前，必须先确认需求目录名（`feature-dir`），再定位该目录下的主 PRD 文件。
2. 优先参考 `skills/qa-prd-analysis/analysis-template.md` 模板。
3. 所有输出使用中文；技术术语保留英文原文，并在必要时附中文解释。
4. 输出的文件或目录名尽量使用中文。
5. 遇到术语表中不存在且无法确定含义的术语，标记为 `[待确认术语: xxx]`，继续分析，不要臆断。
6. 如果 PRD 中含有原型图、流程图、截图等图片信息时，先判断当前模型是否支持视觉能力。
    - 支持视觉能力：使用可视化图片工具直接审阅图片，将关键布局、字段、状态和流程信息纳入需求分析报告；**无需**调用 `prd_image_parser.py`。
    - 不支持视觉能力：**严禁**尝试使用 `READ`、打开二进制文件或其他文本读取方式处理图片；**必须**使用图片解析脚本 `prd_image_parser.py` 生成图片解析结果并纳入需求分析报告。
7. **严禁直接读取非 Markdown 格式的 PRD 文件**（如 `.docx`、`.pdf`、`.pptx`、`.xlsx`、`.png` 等二进制或 Office 格式文件）。若 PRD 文件不是 `.md` 格式，必须先使用 `doc_convert_to_markdown.py` 脚本将其转换为 Markdown，再读取转换后的 `.md` 文件进行分析。
8. 编号命名规范，所有组件、流程使用统一编号格式：{SystemModule}-{Component}
    - SystemModule: 从系统角度划分的模块，如Trade：交易模块
    - Component：页面下的某一个区块或者子组件（注意划分的颗粒度），如Filter：筛选组件; SubmitBtn: 提交按钮
9. **信息优先级规则**：当 PRD 正文、图片/Figma 原型、用户在对话中的明确指示之间存在矛盾或不一致时，按以下优先级采纳：
    - **第一优先级（最高）**：用户在对话中明确提出的要求或纠正。用户的口头/文字指示覆盖一切。
    - **第二优先级**：PRD 正文中的业务逻辑描述。PRD 文字是需求的正式载体，业务规则以正文为准。
    - **第三优先级（最低）**：图片和 Figma 原型，**仅作为 UI 参考**。图片/Figma 中的 UI 布局、字段排列、交互细节若与 PRD 正文矛盾，以正文为准，并在澄清清单中标注该矛盾点（建议等级 B，供产品确认）。
    > **示例**：PRD 正文描述"提交按钮点击后弹窗确认"，但 Figma 原型中无弹窗直接提交 → 以 PRD 正文为准，将"Figma 与正文不一致：弹窗确认是否存在"记录为澄清项。


## 执行流程

### Step 1：定位待分析 PRD
1. **TAPD 链接检测**：若用户输入的是 TAPD URL（包含 `tapd.cn` 或 `tapd_fe`），则跳过本地文件扫描，直接进入 Step 2 调用 `get_prd_detail_from_tapd.py` 脚本拉取需求详情。从 TAPD 获取到需求数据并生成 `.md` 文件后，将该 `.md` 文件作为 PRD 主文档继续后续分析。
2. 扫描 `prd/` 下的需求目录，排除 `prd/archive/`。
3. 根据用户输入先确认需求目录名；若未传参数且存在多个目录，必须先让用户确认。
4. 在目标目录下扫描 PRD 文件（优先 `.md`，也需关注 `.docx`、`.pdf`、`.pptx`、`.xlsx` 等格式），排除 `output/` 下的产出文件。
5. 优先匹配与目录同名的主 PRD 文件；若有多个候选文件，必须先确认。
6. 确定唯一目标 PRD 文件、`feature-dir` 与 `feature-name`。
7. **格式检查与转换**：若确定的 PRD 文件不是 `.md` 格式，必须先执行文档格式转换脚本将其转为 Markdown，再继续后续分析。严禁跳过转换直接读取非 Markdown 文件。

### Step 2：预处理 PRD
#### 脚本执行规范
- 所有的辅助脚本都存放在本技能目录的 `scripts/` 下。
- 在执行任何脚本之前，你必须先获取本 `SKILL.md` 所在的绝对路径，并将其作为基准路径来定位 `scripts/` 目录。
- **执行示例**：如果本 `SKILL.md` 路径为 `/path/to/my-skill/SKILL.md`，则你应当执行 `/path/to/my-skill/scripts/process.py`。

#### TAPD 需求详情获取辅助脚本

当用户直接提供了 TAPD 需求的 URL 链接（而非本地 PRD 文件），说明需要从 TAPD 平台在线拉取需求详情，必须先调用本脚本获取需求数据并生成本地 PRD 文件，再继续后续分析。

脚本路径：
- `scripts/get_prd_detail_from_tapd.py`

适用场景：
- 用户输入的是 TAPD 链接，例如 `https://www.tapd.cn/tapd_fe/58049171/story/detail/1158049171001607427`
- 用户输入的是 TAPD 列表页链接，例如 `https://www.tapd.cn/tapd_fe/58049171/story/list?...&dialog_preview_id=story_1158049171001607427`
- 需要从 TAPD 获取需求标题、描述、状态、负责人等基本信息作为 PRD 分析的输入

推荐命令：

```bash
python scripts/get_prd_detail_from_tapd.py \
  "https://www.tapd.cn/tapd_fe/58049171/story/detail/1158049171001607427" \
  --output-dir prd/{feature-dir}
```

常用参数：
- `url`：必填，TAPD 需求链接，支持列表页和详情页两种 URL 格式
- `--output-dir`：选填，输出目录路径，指定后在该目录下生成 `{需求名称}.md` 文件；不指定则打印 JSON 到控制台
- `--fields`：选填，自定义查询字段，逗号分隔

产物说明：
- `{需求名称}.md`：需求基本信息的 Markdown 文件，包含标题、基本信息、需求描述

认证要求：
- 需要配置环境变量 `TAPD_SIGN`
- 设置方式：`export TAPD_SIGN=your_sign_key`

注意事项：
- 如果未设置 `TAPD_SIGN` 环境变量，脚本将报错退出，通知用户手动输入TAPD需求正文
- 生成 `.md` 文件后，将其作为 PRD 主文档，后续分析流程与本地 PRD 一致

#### 在线文档下载辅助脚本

当 PRD 正文中引用了 `https://doc.weixin.qq.com/` 域名下的腾讯企业微信在线文档链接，说明关键信息在在线文档上，需要将这些在线文档下载到本地再纳入需求分析。

脚本路径：
- `scripts/wechat_doc_downloader.py`

适用场景：
- PRD 正文中出现了 `https://doc.weixin.qq.com/sheet/...` 或 `https://doc.weixin.qq.com/doc/...` 等在线文档链接
- 在线文档包含了需求功能描述、数据字段定义、流程图说明等 PRD 正文未覆盖的关键信息
- 希望将在线文档下载为本地文件，方便后续离线分析或归档

推荐命令：

```bash
python scripts/wechat_doc_downloader.py \
  "https://doc.weixin.qq.com/sheet/e3_AbYA7wb9AAYCNoSNuQCISQ0aTj0ej" \
  --output-dir prd/{feature-dir}
  --to-markdown
```

常用参数：
- `doc_url`：必填，腾讯文档 URL，支持 `sheet`、`doc`、`pdf` 三种类型
- `--output-dir` / `-o`：选填，下载文件保存目录，默认为当前目录
- `--to-markdown` / `-m`: 选填，**强烈建议开启**，下载完成后会直接转为markdown格式，更方便读取

注意事项：
- 脚本依赖内置 Cookie 完成认证，若 Cookie 失效或需要验证码，下载将失败，立即终止流程，通知用户手动下载该文档放到需求目录内
- 下载成功后会在指定目录生成对应文件（Excel/Docx/PDF），并在控制台输出本地文件路径。若有`--to-markdown`参数，则会生成对应的.md文件，并将原始文件归档至`raw/`目录下
- 如果 PRD 中同时存在图片和在线文档链接，按当前模型视觉能力处理图片；在无需人工确认图片结论时，可与在线文档下载并行执行，再汇总分析

#### 所有PRD统一转为Markdown格式

当需求目录下的 PRD 文档为非 Markdown 格式（如 `.docx`、`.xlsx`、`.pptx`、`.pdf`等）时，必须先使用转换脚本将其转为 Markdown，再读取转换后的 `.md` 文件进行分析。

脚本路径：
- `scripts/doc_convert_to_markdown.py`

适用场景：
- PRD 主文档为 `.docx`、`.pdf`、`.pptx`、`.xlsx` 或图片格式
- 需求目录中不存在同名 `.md` 文件，仅存在二进制/Office 格式文档
- 需要将非 Markdown 文档转为大模型可读的 Markdown 格式

推荐命令：

```bash
python scripts/doc_convert_to_markdown.py \
  prd/{feature-dir}/{feature-name}.docx
  --parse-images
```

常用参数：
- `file`：必填，输入文件路径，支持 PDF/DOCX/PPTX/XLSX/图片
- `--health`：仅检查服务健康状态后退出
- `--parse-images`：选填，开启后会将文档中的图片提取并解析，并将图片描述嵌入至markdown文本中，**强烈建议开启**

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

当 PRD 中包含图片，且图片承载了页面布局、交互状态、流程流转、字段说明等关键信息时，按以下规则处理后再继续正文分析：

1. 当前模型支持视觉能力：使用可视化图片工具直接审阅图片，不运行图片解析脚本；在报告中记录图片结论及图片路径。
2. 当前模型不支持视觉能力：运行图片解析脚本，将输出结果或无法识别项纳入报告。

无论是否支持视觉能力，图片都仅作为 UI 参考；与 PRD 正文冲突时以正文为准，并记录矛盾点。

脚本路径：
- `scripts/prd_image_parser.py`

图片解析脚本适用场景（仅当前模型不支持视觉能力时）：
- PRD 中有 UI 原型图、流程图、架构图、页面截图
- Markdown 正文对图片说明不足，需要从视觉内容补全组件与交互信息
- 只想针对某一张图做深度分析，辅助确认模块边界或流程细节

推荐命令：

```bash
python scripts/prd_image_parser.py \
  --prd-file prd/{feature-dir}/{feature-name}.md \
  --embed
```

常用参数：
- `--prd-file`：必填，目标 PRD Markdown 文件
- `--embed`：**强烈推荐开启**，会将图片描述直接嵌入源 Markdown 文件中图片引用的紧后方，生成`{feature-name}-image-desc-embedded.md`，无需再单独读取image-analysis 报告
- `--detail-level`：图片解析深度，可选 `brief`、`standard`、`deep`
- `--image-path`：选填，只分析某一张图片时使用，支持相对路径或绝对路径。用于需要对某张重要图片进行二次确认的情况。单图模式下，分析结果会直接输出到控制台。
- `--custom-prompt`：选填，仅与 `--image-path` 配合使用。传入自定义分析指令，用于深度解析某张图的特定信息（如"重点关注弹窗的按钮状态变化逻辑"），会合并到默认分析 prompt 中。
- `--force-refresh`：忽略缓存，强制重新生成 PRD 摘要和图片分析结果

默认产物：
- `prd/{feature-dir}/output/{feature-name}-image-analysis.md`
- `prd/{feature-dir}/output/.cache/prd-image-parser/` 缓存目录
- `prd/{feature-dir}/{feature-name}-image-desc-embedded.md` 有`--embed`参数时生成
使用要求：
- 如果脚本输出了 `[无法识别: xxx]`、错误日志或缺失图片，需要在分析报告中保留不确定性说明，不要自行脑补

#### 检索历史归档需求参考

**本步骤按需触发，不强制每次执行。** 仅当阅读 PRD 后发现以下任一情况，才通过 Agent tool 启动子 Agent 检索 `prd/archive/`；若无下列信号则跳过：

- PRD 中存在模糊引用，如"参考线上逻辑"、"同现有逻辑保持一致"、"与 XX 相同"，但未给出具体规则描述
- PRD 中出现业务术语或专有名词，在当前 PRD 正文找不到定义或解释
- 某个功能点描述过于简略，缺乏足够上下文，需要借助历史版本理解背景

**若 `prd/archive/` 目录不存在或为空，跳过本步骤。**

子 Agent 任务：
1. 扫描 `prd/archive/` 下所有需求目录，根据当前需求的功能域、业务模块、关键词快速筛选相关目录（无需逐一深读，先看目录名和文件名判断相关性）
2. 对筛选出的相关目录，优先读取 `output/{name}-analysis.md`（若有），其次读取 PRD 正文
3. 重点提炼能解决上述触发信号的内容：
   - 模糊引用对应的历史具体规则或约束
   - 不清晰的业务术语的定义与使用上下文
   - 简略功能点的历史背景、已知遗留问题或特殊处理逻辑
4. 输出精简摘要，略去与触发信号无关的细节
5. 若有相关内容，将摘要写入 `prd/{feature-dir}/output/{feature-name}-archive-ref.md`；若无相关归档需求则不生成此文件，直接返回"无相关归档需求"

主 Agent 将子 Agent 返回的摘要作为分析报告的参考背景，在 Step 3 输出报告时，如有引用须标注"参考归档需求：{归档目录名}"。

> **优先级说明**：历史归档需求仅作背景参考，优先级低于当前 PRD 正文。若归档内容与当前 PRD 存在矛盾或冲突，以当前 PRD 为准，并在分析报告中注明差异点（如"与归档需求 {归档目录名} 存在变更：…"）。

### Step 3 输出分析报告和澄清项清单

分析报告格式结构参考`analysis-template.md`，写入：`prd/{feature-dir}/output/{feature-name}-analysis.md`

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
  - **仅在边界或异常条件下有重大影响时才澄清**

- D类：安全相关问题（优先级：P2） 
  - 涉及支付、刷单、抽奖活动等资金财产安全问题
  - 涉及法律、法务风险问题
  - **仅在有明显安全风险时才澄清**

- E类：性能相关问题（优先级：P3） 
  - 预计的访问量、并发数以及响应时间要求
  - **仅在PRD明确提及性能要求时才澄清**

优先处理A、B类问题，澄清清单输出格式参考：
```
# 问题 1：[问题标题]
上下文：
[相关需求描述的简短引用]
疑问：[具体的问题]
为什么重要：
[澄清这个问题对业务逻辑测试的意义]
回答: 
[留空引导用户将确认方案填写在这里]
```

### Step 4: 完成汇报
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
