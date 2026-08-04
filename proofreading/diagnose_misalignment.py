from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "proofreading" / "misalignment-diagnostic.md"
JSON_PATH = ROOT / "satisfaction-scripts.zh.json"
TSV_PATH = ROOT / "satisfaction-text.tsv"

KEYWORDS = [
    "データベース",
    "天崎博士",
    "動物実験",
    "同位体",
    "陽電子",
    "見つからない",
    "カプセル",
    "研究室",
]


def compact(value: str, limit: int = 220) -> str:
    text = str(value or "").replace("\n", "\\n").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main() -> None:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8-sig"))
    with TSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    report = [
        "# 日中错位诊断",
        "",
        "## 已确认断点",
        "",
        "- 第 89 条仍位于 `noel0_001.dsf`，日中语义对应。",
        "- 第 90 条进入 `noel10_000.dsf` 后，日文与中文完全不对应。",
        "- 在结构原因查明前，不对第 90 条以后执行普通措辞校对。",
        "",
        "## 第 85–115 条当前状态",
        "",
    ]

    for index in range(85, min(115, len(rows)) + 1):
        row = rows[index - 1]
        report.extend(
            [
                f"### 条目 {index} — `{row.get('file', '')}:{row.get('line', '')}`",
                "",
                f"- **日文：** {compact(row.get('source', ''))}",
                f"- **当前中文：** {compact(row.get('translation', ''))}",
                "",
            ]
        )

    report.extend(["## 关键词源文检索", ""])
    for keyword in KEYWORDS:
        matches = [
            (index, row)
            for index, row in enumerate(rows, start=1)
            if keyword in str(row.get("source", ""))
        ]
        report.append(f"### `{keyword}` — {len(matches)} 处")
        report.append("")
        for index, row in matches[:30]:
            report.extend(
                [
                    f"- 第 {index} 条 `{row.get('file', '')}:{row.get('line', '')}`",
                    f"  - 日文：{compact(row.get('source', ''))}",
                    f"  - 当前中文：{compact(row.get('translation', ''))}",
                ]
            )
        report.append("")

    report.extend(["## JSON 章节开头抽样", ""])
    for chapter_position, chapter in enumerate(data.get("chapters", [])):
        segments = chapter.get("segments", [])
        report.extend(
            [
                f"### JSON 章节 {chapter_position} — `{chapter.get('title', '')}`",
                "",
            ]
        )
        for local_index, segment in enumerate(segments[:4]):
            report.extend(
                [
                    f"- 段 {local_index}",
                    f"  - 日文：{compact(segment.get('source', ''))}",
                    f"  - 中文：{compact(segment.get('target', ''))}",
                ]
            )
        report.append("")
        if chapter_position >= 12:
            break

    OUT.write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
