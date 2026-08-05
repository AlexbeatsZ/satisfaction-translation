# 翻译／校对范围占用

本目录用于记录当前正在翻译或校对的条目范围，避免多个协作者重复处理同一段文本。

## 目录约定

- `active/`：当前仍被占用的范围。
- 完成并合并后，应删除活动文件，或迁移到后续建立的完成记录目录。
- 一个占用文件只表示一个连续区间。
- 不同占用文件之间不得有任何索引重叠。
- 已经合并的范围不得继续留在 `active/` 中。

## 文件名

```text
起点六位数-终点六位数-负责人标识.json
```

例如：

```text
002730-003229-openai-chatgpt.json
```

文件名只用于快速识别；实际检查以 JSON 内的 `range` 为准。

## JSON 格式

```json
{
  "range": {
    "start": 2730,
    "end": 3229
  },
  "owner": "OpenAI ChatGPT",
  "work_type": "translation-proofreading",
  "branch": "translation-proofreading-v2",
  "status": "reviewing",
  "started_at": "2026-08-05T10:53:00+08:00",
  "updated_at": "2026-08-05T10:53:00+08:00",
  "note": "从 PROOFREADING_PROGRESS.md 的下一起点继续。"
}
```

## 必填字段

| 字段 | 说明 |
|---|---|
| `range.start` | 起始索引，包含该条 |
| `range.end` | 结束索引，包含该条 |
| `owner` | 负责人、账号或 Agent 名称 |
| `work_type` | `translation`、`proofreading` 或 `translation-proofreading` |
| `branch` | 实际提交工作的 Git 分支 |
| `status` | `claimed`、`reviewing`、`ready_to_merge` 或 `blocked` |
| `started_at` | 开始占用时间，ISO 8601 格式 |
| `updated_at` | 最近更新时间，ISO 8601 格式 |

## 协作规则

1. 开始工作前，先拉取最新 `main` 并检查所有活动占用。
2. 新范围不得与任何 `active/*.json` 重叠，包括状态为 `blocked` 的范围。
3. 先提交占用文件，再开始修改翻译正文。
4. 扩大或缩小范围时必须先更新占用文件，并重新运行检查脚本。
5. 工作完成后将状态改为 `ready_to_merge`。
6. PR 合并后立即释放该范围，不得长期保留过期的活动占用。
7. `merged` 不是活动状态；合并完成应删除或归档记录，而不是把状态改成 `merged` 后继续留在 `active/`。
8. 禁止通过修改索引、拆分文件或另开分支绕过已有占用。
9. 占用只防止协作冲突，不代表该范围已经校对完成；完成情况仍以 manifest 和 `PROOFREADING_PROGRESS.md` 为准。

## 本地检查

```bash
python proofreading/check_active_claims.py
```

检查脚本会验证：

- JSON 格式和必填字段；
- 索引边界与起止顺序；
- 状态与工作类型是否合法；
- 活动范围之间是否重叠；
- 占用范围是否超过全书 21,204 条。
