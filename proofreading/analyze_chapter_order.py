from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = ROOT / "satisfaction-scripts.zh.json"
TSV_PATH = ROOT / "satisfaction-text.tsv"
OUT_PATH = ROOT / "proofreading" / "chapter-order-analysis.md"


def natural_key(value: str) -> tuple:
    parts = re.split(r"(\d+)", value)
    return tuple(int(part) if part.isdigit() else part.casefold() for part in parts)


def compact(value: str, limit: int = 180) -> str:
    text = str(value or "").replace("\n", "\\n").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main() -> None:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8-sig"))
    chapters = data.get("chapters", [])
    with TSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        tsv_rows = list(csv.DictReader(handle, delimiter="\t"))

    target_stream = [
        str(segment.get("target", ""))
        for chapter in chapters
        for segment in chapter.get("segments", [])
    ]

    current_offsets: dict[str, int] = {}
    offset = 0
    for chapter in chapters:
        current_offsets[str(chapter.get("title", ""))] = offset
        offset += len(chapter.get("segments", []))

    natural_chapters = sorted(chapters, key=lambda chapter: natural_key(str(chapter.get("title", ""))))
    natural_offsets: dict[str, int] = {}
    offset = 0
    for chapter in natural_chapters:
        natural_offsets[str(chapter.get("title", ""))] = offset
        offset += len(chapter.get("segments", []))

    tsv_start: dict[str, int] = {}
    for index, row in enumerate(tsv_rows, start=1):
        tsv_start.setdefault(str(row.get("file", "")), index)

    report = [
        "# 章节顺序与译文偏移分析",
        "",
        f"- JSON 章节数：{len(chapters)}",
        f"- JSON 段落数：{len(target_stream)}",
        f"- TSV 条目数：{len(tsv_rows)}",
        "- 假设：中文 target 流采用自然数字章节顺序，而 source/章节对象采用字符串顺序。",
        "",
        "## 当前顺序与自然顺序对照",
        "",
        "| 自然序号 | 章节 | 当前序号 | 段数 | 当前 source 起点 | 自然 target 起点 | TSV 起点 |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]

    current_position = {id(chapter): index for index, chapter in enumerate(chapters)}
    for natural_position, chapter in enumerate(natural_chapters):
        title = str(chapter.get("title", ""))
        report.append(
            f"| {natural_position} | `{title}` | {current_position[id(chapter)]} | "
            f"{len(chapter.get('segments', []))} | {current_offsets[title] + 1} | "
            f"{natural_offsets[title] + 1} | {tsv_start.get(title, 0)} |"
        )

    report.extend(["", "## 自然章节起点抽样", ""])
    for natural_position, chapter in enumerate(natural_chapters):
        title = str(chapter.get("title", ""))
        segments = chapter.get("segments", [])
        start = natural_offsets[title]
        report.extend(
            [
                f"### {natural_position}. `{title}`",
                "",
                f"- 段数：{len(segments)}",
                f"- 当前 source 起点：{current_offsets[title] + 1}",
                f"- 假设 target 起点：{start + 1}",
            ]
        )
        for local_index, segment in enumerate(segments[:3]):
            stream_index = start + local_index
            target = target_stream[stream_index] if stream_index < len(target_stream) else "<越界>"
            report.extend(
                [
                    f"- 段 {local_index + 1}",
                    f"  - 日文：{compact(segment.get('source', ''))}",
                    f"  - 假设中文：{compact(target)}",
                ]
            )
        report.append("")

    report.extend(
        [
            "## 关键断点验证",
            "",
            f"- `noel0_001.dsf` 段数：{len(next(ch['segments'] for ch in chapters if ch.get('title') == 'noel0_001.dsf'))}",
            f"- 自然顺序中 `noel1_001.dsf` target 起点：{natural_offsets.get('noel1_001.dsf', -1) + 1}",
            f"- 当前顺序中 `noel1_001.dsf` source 起点：{current_offsets.get('noel1_001.dsf', -1) + 1}",
            f"- 当前第 90 个 target：{compact(target_stream[89] if len(target_stream) > 89 else '')}",
            "",
        ]
    )

    OUT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
