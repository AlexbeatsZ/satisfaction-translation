from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "proofreading"
JSON_PATH = ROOT / "satisfaction-scripts.zh.json"
MD_PATH = ROOT / "satisfaction-scripts.zh.md"
TXT_PATH = ROOT / "satisfaction-scripts.zh.txt"
TSV_PATH = ROOT / "satisfaction-text.tsv"
TERM_PATH = ROOT / "terminology.yaml"
GLOSSARY_PATH = ROOT / "glossary.json"
PROGRESS_PATH = ROOT / "PROOFREADING_PROGRESS.md"

SPEAKER_PREFIX_RE = re.compile(r"^【話者[:：][^】]*】")
WHITESPACE_RE = re.compile(r"\s+")
PAREN_RUBY_RE = re.compile(r"(?<=[\u3400-\u9fff々ヶ])\([ぁ-ゖァ-ヺー]+\)")
ANGLE_RUBY_RE = re.compile(r"<[ぁ-ゖァ-ヺー]+>")


def normalize_source(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.strip().lstrip("\u3000")
    text = SPEAKER_PREFIX_RE.sub("", text, count=1)
    text = PAREN_RUBY_RE.sub("", text)
    text = ANGLE_RUBY_RE.sub("", text)
    return WHITESPACE_RE.sub("", text)


def load_canonical() -> tuple[
    dict[str, Any],
    list[tuple[int, str, int, dict[str, Any]]],
    list[str],
    list[str],
    list[dict[str, str]],
    list[str],
]:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8-sig"))
    flattened: list[tuple[int, str, int, dict[str, Any]]] = []
    for chapter_position, chapter in enumerate(data.get("chapters", [])):
        chapter_index = int(chapter.get("index", chapter_position))
        title = str(chapter.get("title", ""))
        for local_index, segment in enumerate(chapter.get("segments", [])):
            flattened.append((chapter_index, title, local_index, segment))

    md_lines = MD_PATH.read_text(encoding="utf-8-sig").splitlines()
    txt_lines = TXT_PATH.read_text(encoding="utf-8-sig").splitlines()
    with TSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    return data, flattened, md_lines, txt_lines, rows, fields


def build_tsv_mapping(
    data: dict[str, Any], tsv_rows: list[dict[str, str]]
) -> tuple[list[int], list[str]]:
    """Map JSON natural order to TSV positions by filename and ordinal within file."""
    positions_by_file: dict[str, list[int]] = defaultdict(list)
    for position, row in enumerate(tsv_rows):
        positions_by_file[str(row.get("file", ""))].append(position)

    mapping: list[int] = []
    report = [
        "# TSV 与 JSON 对齐报告",
        "",
        "- JSON 保持作品的自然章节顺序，是校对编号、日文与中文的权威来源。",
        "- TSV 可采用不同的全局文件排序；通过脚本文件名与文件内序号映射。",
        "- TSV 的全局行号不再用于与 JSON 段落位置直接配对。",
        "",
        "| JSON 章节序号 | 脚本文件 | JSON 段数 | TSV 行数 | 规范化源文差异 |",
        "|---:|---|---:|---:|---:|",
    ]

    failures: list[str] = []
    json_titles: set[str] = set()
    for chapter_position, chapter in enumerate(data.get("chapters", [])):
        title = str(chapter.get("title", ""))
        json_titles.add(title)
        segments = list(chapter.get("segments", []))
        positions = positions_by_file.get(title, [])
        if len(segments) != len(positions):
            failures.append(
                f"{title}: JSON={len(segments)}, TSV={len(positions)}"
            )
            report.append(
                f"| {chapter_position} | `{title}` | {len(segments)} | {len(positions)} | **计数不一致** |"
            )
            continue

        mismatch_count = 0
        for local_index, (segment, tsv_position) in enumerate(zip(segments, positions)):
            mapping.append(tsv_position)
            if normalize_source(segment.get("source", "")) != normalize_source(
                tsv_rows[tsv_position].get("source", "")
            ):
                mismatch_count += 1

        report.append(
            f"| {chapter_position} | `{title}` | {len(segments)} | {len(positions)} | {mismatch_count} |"
        )

    extra_files = sorted(set(positions_by_file) - json_titles)
    if extra_files:
        failures.append(f"TSV contains unknown files: {extra_files}")

    expected = sum(len(chapter.get("segments", [])) for chapter in data.get("chapters", []))
    if failures or len(mapping) != expected:
        report.extend(["", "## 阻断错误", ""])
        report.extend(f"- {failure}" for failure in failures)
        (OUT / "tsv-alignment-report.md").write_text(
            "\n".join(report) + "\n", encoding="utf-8"
        )
        raise RuntimeError("TSV per-file alignment failed")

    report.extend(
        [
            "",
            f"- JSON 总段数：{expected}",
            f"- TSV 总条目：{len(tsv_rows)}",
            f"- 映射条目：{len(mapping)}",
            "- 计数一致；规范化文本差异仅作诊断，不改变按文件内序号建立的映射。",
        ]
    )
    return mapping, report


def load_terms() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    document: dict[str, Any] = {"groups": {}, "terms": []}
    if TERM_PATH.exists():
        document = yaml.safe_load(TERM_PATH.read_text(encoding="utf-8")) or document
    active = [
        term
        for term in document.get("terms", [])
        if term.get("status", "active") == "active" and term.get("source")
    ]

    glossary: dict[str, dict[str, Any]] = {}
    if GLOSSARY_PATH.exists():
        payload = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8-sig"))
        for item in payload.get("glossary", []):
            source = str(item.get("source", "")).strip()
            if source:
                glossary[source] = item
    return active, glossary


def visible_terms(
    terms: list[dict[str, Any]],
    glossary: dict[str, dict[str, Any]],
    chapter_index: int,
    source: str,
    target: str,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for term in terms:
        valid_from = term.get("valid_from")
        valid_to = term.get("valid_to")
        if valid_from is not None and chapter_index < int(valid_from):
            continue
        if valid_to is not None and chapter_index > int(valid_to):
            continue
        visible_source = SPEAKER_PREFIX_RE.sub("", source, count=1)
        if str(term["source"]) in visible_source:
            matches.append(term)

    matches.sort(key=lambda term: len(str(term["source"])), reverse=True)
    selected: list[dict[str, Any]] = []
    for term in matches:
        source_term = str(term["source"])
        if any(source_term in str(existing["source"]) for existing in selected):
            continue
        selected.append(term)

    result: list[dict[str, Any]] = []
    for term in selected:
        source_term = str(term["source"])
        expected = str(term.get("target", ""))
        info = glossary.get(source_term, {})
        result.append(
            {
                "source": source_term,
                "target": expected,
                "mode": term.get("mode", "preferred"),
                "pronoun": term.get("pronoun"),
                "present_in_target": bool(expected and expected in target),
                "type": info.get("type"),
                "note": info.get("note"),
            }
        )
    return result


def main() -> None:
    OUT.mkdir(exist_ok=True)
    data, flattened, md_lines, txt_lines, tsv_rows, tsv_fields = load_canonical()
    md_nonempty = [index for index, line in enumerate(md_lines) if line.strip()]
    txt_nonempty = [index for index, line in enumerate(txt_lines) if line.strip()]
    counts = {
        "json": len(flattened),
        "markdown": len(md_nonempty),
        "text": len(txt_nonempty),
        "tsv": len(tsv_rows),
    }
    if len(set(counts.values())) != 1:
        raise ValueError(f"Canonical segment counts differ: {counts}")

    json_to_tsv, alignment_report = build_tsv_mapping(data, tsv_rows)

    manifest_payloads = [
        (path, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(OUT.glob("reviewed-batch-*.json"))
    ]
    # Follow-up manifests deliberately revisit an already reviewed entry. Apply
    # them after ordinary batches so old_target -> new_target remains a checked,
    # reproducible correction chain even when the sync command is run repeatedly.
    manifest_payloads.sort(key=lambda item: bool(item[1].get("followup")))
    followup_targets: dict[int, set[str]] = defaultdict(set)
    for _, manifest in manifest_payloads:
        if manifest.get("followup"):
            for entry in manifest.get("entries", []):
                followup_targets[int(entry["index"])].add(str(entry["new_target"]))
    applied: list[dict[str, Any]] = []
    seen: set[int] = set()
    reviewed_coverage: set[int] = set()
    terminology_changes: list[dict[str, Any]] = []

    for manifest_path, manifest in manifest_payloads:
        followup = bool(manifest.get("followup"))
        if not followup:
            range_payload = manifest.get("range")
            if range_payload:
                reviewed_coverage.update(
                    range(int(range_payload["start"]), int(range_payload["end"]) + 1)
                )
            else:
                reviewed_coverage.update(
                    int(entry["index"]) for entry in manifest.get("entries", [])
                )
        terminology_changes.extend(manifest.get("terminology_changes", []))
        for entry in manifest.get("entries", []):
            index = int(entry["index"])
            if index in seen and not followup:
                raise ValueError(f"Duplicate reviewed entry: {index}")
            if followup and index not in reviewed_coverage:
                raise ValueError(
                    f"Follow-up entry {index} has no earlier reviewed entry in {manifest_path.name}"
                )
            seen.add(index)
            position = index - 1
            chapter_index, title, local_index, segment = flattened[position]
            manifest_source = normalize_source(entry.get("source", ""))
            json_source = normalize_source(segment.get("source", ""))
            if manifest_source != json_source:
                raise ValueError(
                    f"Reviewed entry {index} source mismatch in {title}[{local_index}]: "
                    f"json={json_source!r}, manifest={manifest_source!r}"
                )

            old = str(entry["old_target"])
            new = str(entry["new_target"])
            current_values = {
                "JSON": str(segment.get("target", "")),
                "Markdown": md_lines[md_nonempty[position]],
                "TXT": txt_lines[txt_nonempty[position]],
            }
            for label, current in current_values.items():
                accepted = {old, new}
                if not followup:
                    accepted.update(followup_targets.get(index, set()))
                if current not in accepted:
                    raise ValueError(
                        f"{label} entry {index} mismatch: expected {old!r} or {new!r}, got {current!r}"
                    )

            segment["target"] = new
            md_lines[md_nonempty[position]] = new
            txt_lines[txt_nonempty[position]] = new
            applied.append(entry)

    # JSON/Markdown/TXT use natural chapter order. Populate every TSV row through
    # the verified filename + ordinal mapping, regardless of TSV's global sort order.
    for json_position, tsv_position in enumerate(json_to_tsv):
        target = str(flattened[json_position][3].get("target", ""))
        tsv_rows[tsv_position]["translation"] = target

    JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    MD_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    TXT_PATH.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")
    with TSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=tsv_fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(tsv_rows)

    (OUT / "tsv-alignment-report.md").write_text(
        "\n".join(alignment_report) + "\n", encoding="utf-8"
    )

    terms, glossary = load_terms()
    request_path = OUT / "request.json"
    request = (
        json.loads(request_path.read_text(encoding="utf-8"))
        if request_path.exists()
        else {"start": 90, "count": 40}
    )
    start = int(request.get("start", 90))
    if start < 90:
        start = 90
    count = int(request.get("count", 40))

    selected: list[dict[str, Any]] = []
    for index in range(start, min(start + count, len(flattened) + 1)):
        json_position = index - 1
        chapter_index, title, local_index, segment = flattened[json_position]
        tsv_position = json_to_tsv[json_position]
        tsv_row = tsv_rows[tsv_position]
        source = str(segment.get("source", ""))
        target = str(segment.get("target", ""))
        selected.append(
            {
                "index": index,
                "chapter": chapter_index,
                "file": title,
                "line": tsv_row.get("line", ""),
                "kind": tsv_row.get("kind", segment.get("kind", "")),
                "voice": tsv_row.get("voice", ""),
                "source": source,
                "translation": target,
                "terms": visible_terms(terms, glossary, chapter_index, source, target),
            }
        )

    fields = [
        "index", "chapter", "file", "line", "kind", "voice",
        "source", "translation", "terms"
    ]
    with (OUT / "current-batch.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for row in selected:
            writer.writerow({**row, "terms": json.dumps(row["terms"], ensure_ascii=False)})

    last = selected[-1]["index"] if selected else start - 1
    batch = [
        "# 当前校对批次", "",
        f"- 请求范围：第 {start}–{last} 条",
        f"- 实际条数：{len(selected)}",
        "- 编号及日中正文：JSON 自然章节顺序。",
        "- TSV 定位信息：按脚本文件名与文件内序号映射。",
        "- 词库是可编辑校对依据；hard 词条若本身不当，应修改词库。", "",
    ]
    term_report = ["# 当前批次词库命中", "", f"- 范围：第 {start}–{last} 条", ""]

    for row in selected:
        batch.extend(
            [
                f"## 条目 {row['index']}", "",
                f"- **定位：** `{row['file']}:{row['line']}`",
                f"- **章节索引：** `{row['chapter']}`",
                f"- **类型：** `{row['kind']}`",
                f"- **语音：** `{row['voice']}`",
                f"- **日文：** {row['source']}",
                f"- **中文：** {row['translation']}",
            ]
        )
        if row["terms"]:
            batch.append("- **词库命中：**")
            for term in row["terms"]:
                state = "已采用" if term["present_in_target"] else "未采用，需结合语境复核"
                extras = []
                if term.get("pronoun"):
                    extras.append(f"代词提示={term['pronoun']}")
                if term.get("type"):
                    extras.append(f"类型={term['type']}")
                suffix = f"（{'；'.join(extras)}）" if extras else ""
                batch.append(
                    f"  - `{term['mode']}`：`{term['source']}` → `{term['target']}`；{state}{suffix}"
                )
                term_report.extend(
                    [
                        f"## 条目 {row['index']}：`{term['source']}`", "",
                        f"- 建议译法：`{term['target']}`",
                        f"- 模式：`{term['mode']}`",
                        f"- 当前译文是否包含：`{term['present_in_target']}`",
                        f"- 词库备注：{term.get('note') or '无'}", "",
                    ]
                )
        else:
            batch.append("- **词库命中：** 无")
        batch.append("")

    (OUT / "current-batch.md").write_text("\n".join(batch) + "\n", encoding="utf-8")
    (OUT / "terminology-review.md").write_text(
        "\n".join(term_report) + "\n", encoding="utf-8"
    )

    corrected = sum(
        1
        for entry in applied
        if entry.get("status") == "corrected"
        and str(entry.get("old_target", "")) != str(entry.get("new_target", ""))
    )
    summary = [
        "# 已应用校对批次", "",
        f"- 审阅条目：{len(applied)}",
        f"- 实质修正：{corrected}",
        "- 同步文件：JSON、Markdown、TXT、TSV", "",
    ]
    for entry in applied:
        summary.extend(
            [
                f"## 条目 {entry['index']}", "",
                f"- 状态：`{entry['status']}`",
                f"- 原译：{entry['old_target']}",
                f"- 定稿：{entry['new_target']}",
                f"- 说明：{entry['note']}", "",
            ]
        )
    (OUT / "applied-review.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    reviewed_max = max(seen) if seen else 0
    progress = [
        "# 翻译校对进度", "",
        "> 本文件记录可恢复断点。当前工作分支为 `translation-proofreading-v2`。", "",
        "## 当前状态", "",
        "| 项目 | 状态 |", "|---|---|",
        f"| 数据总量 | {len(flattened):,} 条 |",
        f"| 已校对范围 | 第 1–{reviewed_max} 条 |",
        f"| 已校对条数 | {len(applied)} |",
        f"| 累计实质修改条数 | {corrected} |",
        f"| 最后校对条目 | 第 {reviewed_max} 条 |",
        f"| 下次起点 | 第 {reviewed_max + 1} 条 |",
        "| 编号基准 | JSON 自然章节顺序 |",
        "| TSV 对齐 | 脚本文件名 + 文件内序号 |",
        "| 最后更新 | 2026-08-05 |", "",
        "## 结构诊断结论", "",
        "- JSON、Markdown、TXT 的日中内容及自然章节顺序正确。",
        "- TSV 使用不同的全局文件排列；此前按全局行号与 JSON 位置配对，制造了第 90 条起的假性错位。",
        "- 已改为按脚本文件名及文件内序号回填 TSV 译文。", "",
        "## 词库规则", "",
        "- `terminology.yaml` 与 `glossary.json` 是可维护的校对依据。",
        "- active hard 默认统一，但词条错误时修改词库，不扭曲译文。",
        "- preferred 是稳定译法建议；按当前语境决定。",
        "- 长词优先；代词提示仅在命中词条的局部上下文有效。", "",
        "## 词库变更", "",
    ]
    if terminology_changes:
        for change in terminology_changes:
            progress.append(
                f"- `{change.get('source', '')}`：{change.get('change', '')}。原因：{change.get('reason', '')}"
            )
    else:
        progress.append("- 暂无。")
    progress.extend(
        [
            "", "## 恢复说明", "",
            f"从第 {reviewed_max + 1} 条继续；每批校对记录保存在 `reviewed-batch-*.json`。",
        ]
    )
    PROGRESS_PATH.write_text("\n".join(progress) + "\n", encoding="utf-8")

    resolved = [
        "# 第 90 条假性错位说明", "",
        "此前的错位来自校对工具的错误配对，并非正式 JSON 译文错位：", "",
        "- JSON/Markdown/TXT：自然章节顺序；",
        "- TSV：不同的全局文件排序；",
        "- 错误做法：按 TSV 全局行号与 JSON 全局位置直接配对；",
        "- 正确做法：以 JSON 为正文基准，TSV 按文件名和文件内序号映射。", "",
        "第 90 条现恢复为 `noel1_001.dsf` 的首段日中对照，可继续普通校对。",
    ]
    (OUT / "misalignment-resolved.md").write_text(
        "\n".join(resolved) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
