from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "proofreading"
PROGRESS = ROOT / "PROOFREADING_PROGRESS.md"
CANONICAL = ROOT / "satisfaction-scripts.zh.json"


def compact_ranges(values: Iterable[int]) -> list[tuple[int, int]]:
    numbers = sorted(set(values))
    if not numbers:
        return []
    ranges: list[tuple[int, int]] = []
    start = previous = numbers[0]
    for value in numbers[1:]:
        if value == previous + 1:
            previous = value
            continue
        ranges.append((start, previous))
        start = previous = value
    ranges.append((start, previous))
    return ranges


def format_ranges(ranges: list[tuple[int, int]]) -> str:
    if not ranges:
        return "无"
    return "、".join(
        f"第 {start} 条" if start == end else f"第 {start}–{end} 条"
        for start, end in ranges
    )


def main() -> None:
    data = json.loads(CANONICAL.read_text(encoding="utf-8-sig"))
    total = sum(len(chapter.get("segments", [])) for chapter in data.get("chapters", []))

    reviewed: set[int] = set()
    corrected = 0
    terminology_changes: list[dict[str, str]] = []
    reviewed_dates: list[str] = []

    for path in sorted(OUT.glob("reviewed-batch-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        terminology_changes.extend(payload.get("terminology_changes", []))
        if payload.get("reviewed_at"):
            reviewed_dates.append(str(payload["reviewed_at"]))
        followup = bool(payload.get("followup"))

        range_payload = payload.get("range")
        if range_payload:
            start = int(range_payload["start"])
            end = int(range_payload["end"])
            if start < 1 or end < start or end > total:
                raise ValueError(f"Invalid reviewed range in {path.name}: {start}-{end}")
            batch_indices = set(range(start, end + 1))
        else:
            batch_indices = {int(entry["index"]) for entry in payload.get("entries", [])}

        overlap = reviewed.intersection(batch_indices)
        if overlap and not followup:
            raise ValueError(
                f"Duplicate reviewed range/index in {path.name}: {sorted(overlap)[:10]}"
            )
        if followup:
            missing = batch_indices.difference(reviewed)
            if missing:
                raise ValueError(
                    f"Follow-up entries were not reviewed earlier in {path.name}: "
                    f"{sorted(missing)[:10]}"
                )
        else:
            reviewed.update(batch_indices)

        seen_entries: set[int] = set()
        for entry in payload.get("entries", []):
            index = int(entry["index"])
            if index in seen_entries:
                raise ValueError(f"Duplicate entry in {path.name}: {index}")
            seen_entries.add(index)
            if range_payload and index not in batch_indices:
                raise ValueError(
                    f"Entry {index} is outside reviewed range {start}-{end} in {path.name}"
                )
            if (
                entry.get("status") == "corrected"
                and str(entry.get("old_target", ""))
                != str(entry.get("new_target", ""))
            ):
                corrected += 1

    skipped_payload = json.loads((OUT / "skipped-ranges.json").read_text(encoding="utf-8"))
    skipped: set[int] = set()
    skip_rows: list[dict[str, object]] = []
    for item in skipped_payload.get("ranges", []):
        start, end = int(item["start"]), int(item["end"])
        if end < start:
            raise ValueError(f"Invalid skipped range: {start}-{end}")
        overlap = reviewed.intersection(range(start, end + 1))
        if overlap:
            raise ValueError(f"Reviewed/skipped overlap: {sorted(overlap)[:10]}")
        skipped.update(range(start, end + 1))
        skip_rows.append(
            {"start": start, "end": end, "reason": str(item.get("reason", ""))}
        )

    handled = reviewed | skipped
    processed_through = 0
    while processed_through + 1 in handled:
        processed_through += 1
    next_start = processed_through + 1

    reviewed_ranges = compact_ranges(reviewed)
    skipped_ranges = compact_ranges(skipped)

    lines = [
        "# 翻译校对进度",
        "",
        "> 本文件记录可恢复断点。当前工作分支为 `translation-proofreading-v2`。",
        "",
        "## 当前状态",
        "",
        "| 项目 | 状态 |",
        "|---|---|",
        f"| 总进度 | {processed_through:,}/{total:,} |",
        f"| 实际校对 | {len(reviewed):,}/{total:,} |",
        f"| 跳过 | {len(skipped):,}/{total:,} |",
        f"| 累计实质修改 | {corrected:,}/{total:,} |",
        f"| 已校对范围 | {format_ranges(reviewed_ranges)} |",
        f"| 跳过范围 | {format_ranges(skipped_ranges)} |",
        f"| 已连续处理至 | 第 {processed_through} 条 |",
        f"| 下次起点 | 第 {next_start} 条 |",
        "| 编号基准 | JSON 自然章节顺序 |",
        "| TSV 对齐 | 脚本文件名 + 文件内序号 |",
        f"| 最后更新 | {max(reviewed_dates) if reviewed_dates else '未知'} |",
        "",
        "## 跳过说明",
        "",
    ]
    if skip_rows:
        for item in skip_rows:
            lines.append(f"- 第 {item['start']}–{item['end']} 条：{item['reason']}")
    else:
        lines.append("- 无。")

    lines.extend(
        [
            "",
            "## 结构诊断结论",
            "",
            "- JSON、Markdown、TXT 的日中内容及自然章节顺序正确。",
            "- TSV 使用不同的全局文件排列；按全局行号与 JSON 位置配对会制造假性错位。",
            "- 当前按脚本文件名及文件内序号回填 TSV 译文。",
            "",
            "## 词库规则",
            "",
            "- `terminology.yaml` 与 `glossary.json` 是可维护的校对依据。",
            "- active hard 默认统一，但词条错误时修改词库，不扭曲译文。",
            "- preferred 是稳定译法建议；按当前语境决定。",
            "- 长词优先；代词提示仅在命中词条的局部上下文有效。",
            "",
            "## 词库变更",
            "",
        ]
    )
    if terminology_changes:
        seen_changes: set[tuple[str, str, str]] = set()
        for change in terminology_changes:
            key = (
                str(change.get("source", "")),
                str(change.get("change", "")),
                str(change.get("reason", "")),
            )
            if key in seen_changes:
                continue
            seen_changes.add(key)
            lines.append(f"- `{key[0]}`：{key[1]}。原因：{key[2]}")
    else:
        lines.append("- 暂无。")

    lines.extend(
        [
            "",
            "## 恢复说明",
            "",
            f"从第 {next_start} 条继续；逐条修正保存在 `proofreading/reviewed-batch-*.json`，"
            "其 `range` 表示整批已审范围；跳过记录保存在 `proofreading/skipped-ranges.json`。",
        ]
    )
    PROGRESS.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
