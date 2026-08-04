# 2026-08-05 校对阶段摘要

- 已校对范围：第 1–229 条
- 已校对条数：229
- 累计实质修改：148 条
- 下一起点：第 230 条
- 工作分支：`translation-proofreading-v2`
- 草稿 PR：#2

## 本阶段关键处理

- 修复 TSV 与 JSON 因全局文件排序不同造成的假性错位；TSV 改按脚本文件名与文件内序号映射。
- 统一辅助工作流，不再从旧备份分支覆盖当前 `terminology.yaml`。
- 新增核心专名：`白鷺` / `白<しらさぎ>鷺` → `白鹭`（hard、active、valid_from: 1）。
- 所有定稿同步写入 JSON、Markdown、TXT、TSV。

详细逐条理由见 `proofreading/reviewed-batch-*.json`，准确断点见 `PROOFREADING_PROGRESS.md`。
