from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
PROGRESS = ROOT / "PROOFREADING_PROGRESS.md"
CLAIMS_DIR = ROOT / "proofreading" / "claims" / "active"

STATUS_LABELS = {
    "claimed": "已占用，尚未开始",
    "reviewing": "正在校对",
    "ready_to_merge": "已完成，等待合并",
    "blocked": "已暂停，仍占用",
}


def progress_value(text: str, label: str) -> str:
    match = re.search(rf"\| {re.escape(label)} \| ([^|]+) \|", text)
    if not match:
        raise ValueError(f"PROOFREADING_PROGRESS.md 缺少字段：{label}")
    return match.group(1).strip()


def main() -> None:
    readme = README.read_text(encoding="utf-8")
    progress = PROGRESS.read_text(encoding="utf-8")

    claims: list[tuple[Path, dict[str, object]]] = []
    for path in sorted(CLAIMS_DIR.glob("*.json")):
        claims.append((path, json.loads(path.read_text(encoding="utf-8"))))

    table_rows: list[str] = []
    claim_links: list[str] = []
    for path, claim in claims:
        range_data = claim["range"]
        start = int(range_data["start"])
        end = int(range_data["end"])
        status = str(claim["status"])
        updated_at = str(claim.get("updated_at", ""))
        updated_date = updated_at.split("T", 1)[0] if updated_at else "未知"
        table_rows.append(
            f"| 第 {start:,}–{end:,} 条 | 日中翻译校对 | "
            f"{claim['owner']} | `{claim['branch']}` | "
            f"{STATUS_LABELS.get(status, status)} | {updated_date} |"
        )
        relative_path = path.relative_to(ROOT).as_posix()
        claim_links.append(f"[`{path.name}`]({relative_path})")

    if not table_rows:
        table_rows.append("| 无 | 无 | 无 | 无 | 当前没有活动占用 | — |")
        claims_line = "- 当前机器可读占用记录：无"
    else:
        claims_line = "- 当前机器可读占用记录：" + "、".join(claim_links)

    section = "\n".join(
        [
            "## 当前翻译／校对状态",
            "",
            "> 开始工作前，必须先检查 [`proofreading/claims/active/`](proofreading/claims/active/) 中的占用记录。**不得处理与现有占用范围重叠的条目。**",
            "",
            "| 范围 | 工作内容 | 负责人 | 工作分支 | 状态 | 更新时间 |",
            "|---|---|---|---|---|---|",
            *table_rows,
            "",
            f"- 总进度：**{progress_value(progress, '总进度')}**",
            f"- 实际校对：**{progress_value(progress, '实际校对')}**",
            f"- 跳过：**{progress_value(progress, '跳过')}**",
            claims_line,
            "- 完整断点与统计：[`PROOFREADING_PROGRESS.md`](PROOFREADING_PROGRESS.md)",
            "",
            "README 中的表格用于快速查看；发生差异时，以 `proofreading/claims/active/*.json` 和 `PROOFREADING_PROGRESS.md` 为准。",
            "",
            "---",
        ]
    )

    pattern = re.compile(r"## 当前翻译／校对状态\n.*?\n---", re.DOTALL)
    if not pattern.search(readme):
        raise ValueError("README.md 中未找到当前翻译／校对状态区块")
    README.write_text(pattern.sub(section, readme, count=1), encoding="utf-8")


if __name__ == "__main__":
    main()
