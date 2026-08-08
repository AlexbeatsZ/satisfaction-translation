# 校对 Manifest 设计

## 普通批次

普通 `reviewed-batch-*.json` 用 `range.start`/`range.end` 表示整段已审范围，`entries` 只记录实际修改。不同普通批次的范围和条目不得重叠。

每项必须保存稳定索引、源文、`old_target`、`new_target`、状态和说明。同步时会核对源文，并只接受正文当前值等于旧译、新译或后续修订的最终值。

## 二次修订

已经审过的条目发现新问题时，新建不带 `range` 且含 `"followup": true` 的 manifest：

```json
{
  "followup": true,
  "reviewed_at": "YYYY-MM-DD",
  "entries": []
}
```

follow-up 条目必须落在既有已审范围内。若该索引此前已有实际修改记录，follow-up 的 `old_target` 必须等于上一条记录的 `new_target`。同步器先应用普通批次，再按文件名顺序应用 follow-up，因此重复执行仍会得到同一结果。

follow-up 不扩大已审范围，但其真实的旧译到新译修改会计入累计实质修改。

## 质量门禁

`proofreading/check_translation_quality.py` 检查：

- 普通批次、跳过范围和 follow-up 的覆盖关系；
- manifest 源文、修订链和权威 JSON 最终值；
- 已审译文中的日文假名残留和完整对话引号；
- JSON、Markdown、TXT、TSV 四种正文是否同步。

所有 manifest 或正文变更都必须通过该脚本；GitHub Actions 在相关 PR 和 `main` 推送时执行它。
