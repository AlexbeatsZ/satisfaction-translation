# 校对分支迁移

本分支从最新 `main` 创建，用于重新应用旧分支中已完成的逐条校对，避免新增 `terminology.yaml` 与 `glossary.json` 造成的 add/add 合并冲突。

- 校对记录来源：`translation-proofreading`
- 已记录范围：第 1–89 条
- 下一校对起点：第 90 条
- 诊断结论：JSON、Markdown、TXT 的自然章节顺序及日中对应正确
- TSV 特性：全局文件排序不同，不能与 JSON 按全局行号直接配对
- TSV 对齐：按脚本文件名与文件内序号映射并回填中文
- 兼容处理：说话者提示、括号及尖括号形式的日文振假名仅在身份核验时规范化，不修改正文
- 旧分支及 `translation-proofreading-safety-copy` 保留作恢复备份
