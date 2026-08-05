# Satisfaction Game Script Chinese Translation（《satisfaction～あなたと私の絆～》游戏全剧本中文译本）

本仓库收录 GALGAME **《satisfaction～あなたと私の絆～》（RJ050165）** 完整 92 个剧情章节（共 21,204 条对话/显示文本，约 48 万字）的简体中文全本翻译文本与结构化数据。

本译本由 [Wenyi Direct](https://github.com/AlexbeatsZ/wenyi-direct) 自动化文学/剧本翻译框架完成初译，并由人工与 AI 协作进行事实核对、术语维护和中文润色。

---

## 当前翻译／校对状态

> 开始工作前，必须先检查 [`proofreading/claims/active/`](proofreading/claims/active/) 中的占用记录。**不得处理与现有占用范围重叠的条目。**

| 范围 | 工作内容 | 负责人 | 工作分支 | 状态 | 更新时间 |
|---|---|---|---|---|---|
| 第 6,730–7,229 条 | 日中翻译校对 | OpenAI ChatGPT | `translation-proofreading-6730-7229` | 已占用，尚未开始 | 2026-08-05 |
| 第 7,230–7,729 条 | 日中翻译校对 | OpenAI ChatGPT | `translation-proofreading-7230-7729` | 已占用，尚未开始 | 2026-08-05 |

- 总进度：**7,229/21,204**
- 实际校对：**6,900/21,204**
- 跳过：**329/21,204**
- 当前机器可读占用记录：[`006730-007229-openai-chatgpt.json`](proofreading/claims/active/006730-007229-openai-chatgpt.json)、[`007230-007729-openai-chatgpt.json`](proofreading/claims/active/007230-007729-openai-chatgpt.json)
- 完整断点与统计：[`PROOFREADING_PROGRESS.md`](PROOFREADING_PROGRESS.md)

README 中的表格用于快速查看；发生差异时，以 `proofreading/claims/active/*.json` 和 `PROOFREADING_PROGRESS.md` 为准。

---

## 翻译与校对原则

### 1. 原文、语境和人物意图优先

- 先确认原文实际表达的事实、动作顺序、说话对象、情绪和潜台词，再组织中文。
- 必须结合相邻条目、说话者、场景和前后剧情判断，不按孤立句子机械直译。
- 原文故意含混时保留含混；无法确认时记录疑问，不自行补写设定或剧情。

### 2. 不盲从词库

- [`terminology.yaml`](terminology.yaml) 和 [`glossary.json`](glossary.json) 是**可维护的校对依据**，不是不可修改的标准答案。
- `hard` 词条默认应保持统一，但若词条本身错误、过时、范围不当或不符合当前语境，应修改词库并说明原因，不能为了命中词库而扭曲原文。
- `preferred` 词条只是稳定译法建议，应根据具体语境决定是否采用。
- 新出现的人名、组织名、武器名、称谓和设定词，应先检查既有用法；确认稳定后再写入词库。
- 一词多义、敬称、省略主语和代词指向必须按上下文处理，禁止无条件全局替换。

### 3. 中文自然，但不得擅自扩写

- 消除日语式倒装、冗长定语链、机械被动句和生硬名词句，使译文符合自然中文表达。
- 保留原文的信息量、语气强度和叙事节奏；不额外增加心理活动、动作细节、感官描写或剧情解释。
- 不为了“文采”改变事实，不把简单句过度文学化，也不把角色差异抹平成同一种书面语。

### 4. 保持人物口吻与关系

- 区分正式敬语、同辈口语、亲密称呼、命令、讽刺、幼态口吻和情绪失控等语域。
- 避免在中文叙述和亲密对话中机械重复人物全名；在指代明确时使用名字、姓氏或代词。
- 校内固定问候、角色称谓和组织内部术语应保持一致，但仍受具体语境约束。

### 5. 保护结构与技术信息

- 不修改脚本索引、章节、文件名、物理行号、语音 ID、引擎定位 ID 和 JSON/TSV 结构，除非任务明确要求修复结构。
- 清除误入译文的说话者元数据、振假名、日文促音和其他解析残留。
- JSON、Markdown、TXT 和 TSV 四种正文必须保持内容同步。
- TSV 按“脚本文件名 + 文件内序号”映射，不得直接假设其全局行序与 JSON 相同。

### 6. 修改必须可审计

- 已校对范围必须写入 `proofreading/reviewed-batch-*.json`；`range` 表示整批已经检查，`entries` 记录实际修正项。
- 每个修正项应保留索引、原文、旧译、定稿、状态和简要原因；紧凑 manifest 会由工作流补齐原文与旧译。
- 无法处理的范围必须写入 `proofreading/skipped-ranges.json`，不得伪装成已校对文本。
- 完成一批后更新 `PROOFREADING_PROGRESS.md`，同步全部正文格式，并通过 PR 合并到 `main`。

---

## Wenyi Direct 方法与提示词速查

本项目沿用 Wenyi Direct 的章节优先、读写范围分离和分阶段审校方法。完整说明、术语生命周期和可直接复制的提示词骨架见：

- [`proofreading/WENYI_DIRECT_GUIDE.md`](proofreading/WENYI_DIRECT_GUIDE.md)

| 阶段 | 输入边界 | 核心任务 | 禁止事项 |
|---|---|---|---|
| 直接翻译／重译 | 原文、说话者、只读上下文、有效词库 | 从原文建立语义，按自然中文重组 | 不依赖错误草稿，不提前写入未来剧情 |
| 事实审校 | 原文 + 中文 | 查误译、漏译、增译、指代、说话者、数量、术语和跨段关系 | 不做无原文依据的纯风格润色 |
| 中文阅读验收 | **只看读者可见中文** | 查翻译腔、不成立搭配、人物声音、主语和衔接 | 不猜原意，不查看词库后机械挑错 |
| 原文验证／修复 | 阅读问题 + 邻近原文 | 确认问题真实，并在完整因果范围内统一修复 | 不只替换被点名的单词，不越过写入范围 |
| 忠实度复核 | 所有实际修改 + 原文 | 确认准确、完整且无凭空增写 | 不因未采用 `preferred` 词条而否决 |

必须遵守的信息边界：

- **读取范围可以大于写入范围**，但只能修改已占用的稳定索引。
- 中文阅读验收不得接触原文、词库或翻译说明；其发现必须重新对照原文后才能修复。
- 只有有效的 `active hard` 词条默认强制；`active preferred` 仅为建议。
- `candidate` 和 `rejected` 词条不得作为当前强制依据。
- 发现词库错误时修改词库，不得反向迁就错误词条。
- 修改区域必须逐条通过原文忠实度复核后才能同步正式正文。

---

## 多人协作与范围占用

为避免两名译者或多个 Agent 同时修改同一段文本，本项目使用按范围拆分的占用文件。

### 开始工作前

1. 查看 [`proofreading/claims/active/`](proofreading/claims/active/) 中所有活动占用。
2. 选择一个不与现有记录重叠的连续范围。
3. 新建 `proofreading/claims/active/起点-终点-负责人.json`。
4. 填写负责人、分支、工作类型、状态和时间。
5. 提交占用记录后再开始翻译或校对。

### 活动状态值

| 状态 | 含义 |
|---|---|
| `claimed` | 已预留范围，尚未正式开始 |
| `reviewing` | 正在翻译或校对 |
| `ready_to_merge` | 已完成，等待同步或合并 |
| `blocked` | 暂停处理，但范围仍被占用 |

`merged` 不是合法的活动状态。PR 合并后必须把记录从 `active/` 移出或删除，立即释放范围。

### 完成工作后

1. 确认校对 manifest、词库变更、正文和进度文件均已同步。
2. 创建正式 PR 并合并到 `main`。
3. 将对应占用文件从 `active/` 移除，或迁移到完成记录目录。
4. 下一位协作者只能从 `PROOFREADING_PROGRESS.md` 的下一起点或其他未占用范围开始。

占用文件格式、检查规则和示例见 [`proofreading/claims/README.md`](proofreading/claims/README.md)。仓库会运行 `proofreading/check_active_claims.py`，检测范围重叠和字段错误。

---

## 标准校对流程

1. **占用范围**：先提交活动占用文件。
2. **读取上下文**：同时查看原文、旧译、说话者、相邻条目和命中的词库项。
3. **逐条判断**：准确的译文保持不变；有问题的译文写入校对 manifest。
4. **维护词库**：发现词库错误时修改词库，不反向迁就错误词条。
5. **分别审校**：先做原文事实审校，再做纯中文阅读验收；阅读问题必须回到原文验证。
6. **统一同步**：应用 manifest，更新 JSON、Markdown、TXT 和 TSV。
7. **检查统计**：更新进度、跳过范围和实质修改数量。
8. **合并**：创建非草稿 PR，确认无冲突后合并到 `main`。
9. **释放范围**：删除或归档活动占用文件。

---

## 包含文件与格式

| 文件名 | 格式 | 说明 |
| :--- | :--- | :--- |
| [`satisfaction-scripts.zh.md`](satisfaction-scripts.zh.md) | Markdown | 包含全剧本 92 章完整中文显示文本，按章节划分。 |
| [`satisfaction-scripts.zh.txt`](satisfaction-scripts.zh.txt) | Plain Text | 纯文本格式剧本，方便搜索与文本处理。 |
| [`satisfaction-scripts.zh.json`](satisfaction-scripts.zh.json) | JSON Interchange | 结构化剧本数据，包含章节标题、日文原文、中文译文、说话者角色名及引擎定位 ID。 |
| [`satisfaction-text.tsv`](satisfaction-text.tsv) | TSV | 全书 21,204 条对齐双语表，包含语音 ID（WVP）与物理行定位。 |
| [`terminology.yaml`](terminology.yaml) | YAML | 术语表与规则配置（人名、专有名词、代词映射与强制/建议翻译规则）。 |
| [`glossary.json`](glossary.json) | JSON Dump | 自动抽取的全书术语库、叙事实体映射与事实知识库。 |
| [`PROOFREADING_PROGRESS.md`](PROOFREADING_PROGRESS.md) | Markdown | 当前校对进度、连续断点、跳过范围和词库变更摘要。 |
| [`proofreading/WENYI_DIRECT_GUIDE.md`](proofreading/WENYI_DIRECT_GUIDE.md) | Markdown | Wenyi Direct 方法、分阶段提示词和质量验收规则。 |
| [`proofreading/claims/active/`](proofreading/claims/active/) | JSON | 当前正在翻译／校对的范围占用记录。 |

---

## 文本统计与元数据

- **作品名称**：《satisfaction～あなたと私の絆～》
- **作品编号**：RJ050165
- **章节数量**：92 个 `.dsf` 脚本章节（`noel0_001.dsf` 至 `noel10_ed.dsf`）
- **显示文本总条数**：21,204 条对话／显示文本
- **目标语言**：简体中文（zh-CN）
- **源语言**：日语（ja）

---

## 许可与说明

仅供学习交流与翻译学术研究使用。游戏版权归原制作公司所有。
