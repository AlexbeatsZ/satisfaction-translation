# Goal

维护《satisfaction～あなたと私の絆～》21,204 条剧本的可审计中文译文，并保持 JSON、Markdown、TXT、TSV 四种导出一致。

# Current State

- 权威正文：`satisfaction-scripts.zh.json`，按章节自然顺序编号。
- 已连续处理至第 11,229 条；实际校对 10,655 条，跳过 574 条。
- 第 11,230–11,729 条仍有活动占用，开始新批次前先检查 `proofreading/claims/active/`。
- 校对记录分为普通批次和 `followup: true` 的二次修订；详细约束见 `docs/design/proofreading-manifests.md`。

# Active Work

- 后续校对从现有活动占用或未占用范围继续。
- 合并新批次后运行同步、进度生成和质量检查。

# Build / Run / Test

```powershell
uv run --with pyyaml python proofreading/sync_proofreading_v3.py
uv run python proofreading/update_progress_with_skips.py
uv run python proofreading/update_readme_status.py
uv run python proofreading/check_translation_quality.py
```

同步命令必须可重复运行；第二次运行不得改变正文或失败。

# Durable Lessons

- JSON/Markdown/TXT 使用自然章节顺序；TSV 只能按“脚本文件名 + 文件内序号”映射，不能按全局行号配对。
- 已审条目的再修订必须使用 follow-up manifest 保存旧译到新译的链条，不能改写历史 manifest。
- 历史 manifest 中的“人工校对”是通用说明，不足以证明该条经过独立人工终审；对外描述应使用“人工与 AI 协作校对”。
