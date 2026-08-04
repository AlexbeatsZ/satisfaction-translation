# 校对分支迁移

本分支从最新 `main` 创建，用于重新应用旧分支中已完成的逐条校对，避免新增 `terminology.yaml` 与 `glossary.json` 造成的 add/add 合并冲突。

- 校对记录来源：`translation-proofreading`
- 已记录范围：第 1–89 条
- 普通校对暂停点：第 90 条
- 暂停原因：从 `noel10_000.dsf` 开始，当前日文与中文出现明显结构性错位
- 恢复策略：只对已审条目逐条验证 TSV、JSON 与校对清单中的日文一致性
- 兼容处理：说话者提示在 NFKC 后同时接受半角与全角冒号
- 兼容处理：身份核验时忽略括号及尖括号形式的日文振假名，不修改正文
- 当前诊断：验证字符串排序与自然数字章节顺序混用是否导致 target 流错装
- 旧分支及 `translation-proofreading-safety-copy` 保留作恢复备份
