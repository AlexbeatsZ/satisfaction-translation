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

SPEAKER_PREFIX_RE = re.compile(r"^【話者：[^】]*】")
WHITESPACE_RE = re.compile(r"\s+")


def normalize_source(value: str) -> str:
    """Normalize only extraction noise; preserve actual Japanese wording."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.strip().lstrip("\u3000")
    text = SPEAKER_PREFIX_RE.sub("", text, count=1)
    return WHITESPACE_RE.sub("", text)


def load_canonical() -> tuple[dict[str, Any], list[str], list[str], list[dict[str, str]], list[str]]:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8-sig"))
    md_lines = MD_PATH.read_text(encoding="utf-8-sig").splitlines()
    txt_lines = TXT_PATH.read_text(encoding="utf-8-sig").splitlines()
    with TSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    return data, md_lines, txt_lines, rows, fields


def build_alignment(
    data: dict[str, Any], tsv_rows: list[dict[str, str]]
) -> tuple[list[int], list[tuple[int, dict[str, Any]]], dict[str, dict[str, int]]]:
    """Map every TSV row to its JSON segment using chapter filename and source order."""
    flattened: list[tuple[int, dict[str, Any]]] = []
    chapters_by_title: dict[str, list[tuple[int, int, dict[str, Any]]]] = defaultdict(list)

    for chapter_position, chapter in enumerate(data["chapters"]):
        chapter_index = int(chapter.get("index", chapter_position))
        title = str(chapter.get("title", ""))
        for local_index, segment in enumerate(chapter.get("segments", [])):
            flat_index = len(flattened)
            flattened.append((chapter_index, segment))
            chapters_by_title[title].append((flat_index, local_index, segment))

    cursor_by_file: dict[str, int] = defaultdict(int)
    mapping: list[int] = []
    diagnostics: dict[str, dict[str, int]] = defaultdict(
        lambda: {"tsv_rows": 0, "json_segments": 0, "matched": 0}
    )
    for title, segments in chapters_by_title.items():
        diagnostics[title]["json_segments"] = len(segments)

    unmatched: list[str] = []
    used_json: set[int] = set()

    for tsv_position, row in enumerate(tsv_rows):
        filename = str(row.get("file", ""))
        diagnostics[filename]["tsv_rows"] += 1
        candidates = chapters_by_title.get(filename)
        if not candidates:
            unmatched.append(
                f"TSV {tsv_position + 1}: JSON chapter not found for {filename!r}"
            )
            mapping.append(-1)
            continue

        wanted = normalize_source(row.get("source", ""))
        start = cursor_by_file[filename]
        matched_position: int | None = None

        # Normal path: exact source match at or after the previous match in this file.
        for candidate_position in range(start, len(candidates)):
            flat_index, _local_index, segment = candidates[candidate_position]
            if flat_index in used_json:
                continue
            if normalize_source(segment.get("source", "")) == wanted:
                matched_position = candidate_position
                break

        # Diagnostic fallback for out-of-order extraction. This remains deterministic
        # and requires a unique unused source match within the same script file.
        if matched_position is None:
            fallback = [
                position
                for position, (flat_index, _local_index, segment) in enumerate(candidates)
                if flat_index not in used_json
                and normalize_source(segment.get("source", "")) == wanted
            ]
            if len(fallback) == 1:
                matched_position = fallback[0]

        if matched_position is None:
            unmatched.append(
                f"TSV {tsv_position + 1} {filename}:{row.get('line', '')}: "
                f"source not found: {row.get('source', '')!r}"
            )
            mapping.append(-1)
            continue

        flat_index, _local_index, _segment = candidates[matched_position]
        mapping.append(flat_index)
        used_json.add(flat_index)
        cursor_by_file[filename] = matched_position + 1
        diagnostics[filename]["matched"] += 1

    duplicate_mappings = [index for index, count in Counter(mapping).items() if index >= 0 and count > 1]
    if duplicate_mappings:
        unmatched.append(f"Duplicate JSON mappings: {duplicate_mappings[:20]}")

    if unmatched:
        report = ["# 对齐失败", "", *[f"- {item}" for item in unmatched[:200]]]
        (OUT / "alignment-report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
        raise RuntimeError(
            f"Unable to align {len(unmatched)} TSV rows; see proofreading/alignment-report.md"
        )

    return mapping, flattened, diagnostics


def load_terminology() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    terminology: dict[str, Any] = {"groups": {}, "terms": []}
    if TERM_PATH.exists():
        terminology = yaml.safe_load(TERM_PATH.read_text(encoding="utf-8")) or terminology

    glossary_by_source: dict[str, dict[str, Any]] = {}
    if GLOSSARY_PATH.exists():
        glossary_data = json.loads(GLOSSARY_PATH.read_text(encoding="utf-8-sig"))
        for item in glossary_data.get("glossary", []):
            source = str(item.get("source", "")).strip()
            if source:
                glossary_by_source[source] = item

    active_terms = [
        term
        for term in terminology.get("terms", [])
        if term.get("status", "active") == "active" and term.get("source")
    ]
    return active_terms, glossary_by_source


def visible_terms(
    active_terms: list[dict[str, Any]],
    glossary_by_source: dict[str, dict[str, Any]],
    chapter_index: int,
    source: str,
    target: str,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for term in active_terms:
        valid_from = term.get("valid_from")
        valid_to = term.get("valid_to")
        if valid_from is not None and chapter_index < int(valid_from):
            continue
        if valid_to is not None and chapter_index > int(valid_to):
            continue
        term_source = str(term["source"])
        if term_source in source:
            matches.append(term)

    matches.sort(key=lambda term: len(str(term["source"])), reverse=True)
    selected: list[dict[str, Any]] = []
    for term in matches:
        term_source = str(term["source"])
        if any(term_source in str(existing["source"]) for existing in selected):
            continue
        selected.append(term)

    result: list[dict[str, Any]] = []
    for term in selected:
        source_term = str(term["source"])
        expected = str(term.get("target", ""))
        glossary = glossary_by_source.get(source_term, {})
        result.append(
            {
                "source": source_term,
                "target": expected,
                "mode": term.get("mode", "preferred"),
                "pronoun": term.get("pronoun"),
                "present_in_target": bool(expected and expected in target),
                "type": glossary.get("type"),
                "note": glossary.get("note"),
            }
        )
    return result


def main() -> None:
    OUT.mkdir(exist_ok=True)
    data, md_lines, txt_lines, tsv_rows, tsv_fields = load_canonical()
    mapping, flattened, diagnostics = build_alignment(data, tsv_rows)

    md_nonempty = [index for index, line in enumerate(md_lines) if line.strip()]
    txt_nonempty = [index for index, line in enumerate(txt_lines) if line.strip()]
    if len(md_nonempty) != len(flattened) or len(txt_nonempty) != len(flattened):
        raise ValueError(
            "JSON/Markdown/TXT segment count mismatch: "
            f"json={len(flattened)}, md={len(md_nonempty)}, txt={len(txt_nonempty)}"
        )

    # JSON is authoritative for current Chinese. Rebuild every TSV translation by
    # the verified mapping, repairing the previously positional TSV misalignment.
    for tsv_position, json_position in enumerate(mapping):
        tsv_rows[tsv_position]["translation"] = flattened[json_position][1].get("target", "")

    manifests = sorted(OUT.glob("reviewed-batch-*.json"))
    applied: list[dict[str, Any]] = []
    seen_indexes: set[int] = set()

    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest["entries"]:
            index = int(entry["index"])
            if index in seen_indexes:
                raise ValueError(f"Duplicate reviewed entry: {index}")
            seen_indexes.add(index)

            tsv_position = index - 1
            json_position = mapping[tsv_position]
            old = entry["old_target"]
            new = entry["new_target"]
            segment = flattened[json_position][1]

            json_current = segment.get("target", "")
            md_current = md_lines[md_nonempty[json_position]]
            txt_current = txt_lines[txt_nonempty[json_position]]
            for label, current in (
                ("JSON", json_current),
                ("Markdown", md_current),
                ("TXT", txt_current),
            ):
                if current not in (old, new):
                    raise ValueError(
                        f"{label} entry {index} mismatch: expected {old!r} or {new!r}, got {current!r}"
                    )

            segment["target"] = new
            md_lines[md_nonempty[json_position]] = new
            txt_lines[txt_nonempty[json_position]] = new
            tsv_rows[tsv_position]["translation"] = new
            applied.append(entry)

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

    alignment_report = [
        "# 数据对齐报告",
        "",
        f"- TSV 条目：{len(tsv_rows)}",
        f"- JSON 条目：{len(flattened)}",
        f"- 成功匹配：{len(mapping)}",
        "- 匹配方法：脚本文件名 + 规范化日文源文 + 文件内顺序",
        "",
        "| 脚本文件 | TSV | JSON | 匹配 |",
        "|---|---:|---:|---:|",
    ]
    for filename in sorted(diagnostics):
        values = diagnostics[filename]
        alignment_report.append(
            f"| `{filename}` | {values['tsv_rows']} | {values['json_segments']} | {values['matched']} |"
        )
    (OUT / "alignment-report.md").write_text(
        "\n".join(alignment_report) + "\n", encoding="utf-8"
    )

    active_terms, glossary_by_source = load_terminology()
    request_path = OUT / "request.json"
    request = (
        json.loads(request_path.read_text(encoding="utf-8"))
        if request_path.exists()
        else {"start": 1, "count": 40}
    )
    start = int(request.get("start", 1))
    count = int(request.get("count", 40))

    selected: list[dict[str, Any]] = []
    for index, row in enumerate(tsv_rows[start - 1 : start - 1 + count], start=start):
        tsv_position = index - 1
        json_position = mapping[tsv_position]
        chapter_index, segment = flattened[json_position]
        source = row.get("source", "")
        translation = segment.get("target", "")
        selected.append(
            {
                "index": index,
                "chapter": chapter_index,
                "file": row.get("file", ""),
                "line": row.get("line", ""),
                "kind": row.get("kind", ""),
                "voice": row.get("voice", ""),
                "source": source,
                "translation": translation,
                "terms": visible_terms(
                    active_terms,
                    glossary_by_source,
                    chapter_index,
                    source,
                    translation,
                ),
            }
        )

    fields = [
        "index",
        "chapter",
        "file",
        "line",
        "kind",
        "voice",
        "source",
        "translation",
        "terms",
    ]
    with (OUT / "current-batch.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n"
        )
        writer.writeheader()
        for row in selected:
            writer.writerow(
                {**row, "terms": json.dumps(row["terms"], ensure_ascii=False)}
            )

    last = start + len(selected) - 1
    batch_md = [
        "# 当前校对批次",
        "",
        f"- 请求范围：第 {start}–{last} 条",
        f"- 实际条数：{len(selected)}",
        "- 对齐方式：脚本文件名 + 日文源文 + 文件内顺序。",
        "- 词库说明：词条是可编辑的校对依据；hard 项会突出显示，但发现词条不当时应修改词库，而非扭曲译文。",
        "",
    ]
    term_review = ["# 当前批次词库命中", "", f"- 范围：第 {start}–{last} 条", ""]

    for row in selected:
        batch_md.extend(
            [
                f"## 条目 {row['index']}",
                "",
                f"- **定位：** `{row['file']}:{row['line']}`",
                f"- **章节索引：** `{row['chapter']}`",
                f"- **类型：** `{row['kind']}`",
                f"- **语音：** `{row['voice']}`",
                f"- **日文：** {row['source']}",
                f"- **中文：** {row['translation']}",
            ]
        )
        if row["terms"]:
            batch_md.append("- **词库命中：**")
            for term in row["terms"]:
                state = "已采用" if term["present_in_target"] else "未采用，需结合语境复核"
                extra = []
                if term.get("pronoun"):
                    extra.append(f"代词提示={term['pronoun']}")
                if term.get("type"):
                    extra.append(f"类型={term['type']}")
                suffix = f"（{'；'.join(extra)}）" if extra else ""
                batch_md.append(
                    f"  - `{term['mode']}`：`{term['source']}` → `{term['target']}`；{state}{suffix}"
                )
                term_review.extend(
                    [
                        f"## 条目 {row['index']}：`{term['source']}`",
                        "",
                        f"- 建议译法：`{term['target']}`",
                        f"- 模式：`{term['mode']}`",
                        f"- 当前译文是否包含：`{term['present_in_target']}`",
                        f"- 词库备注：{term.get('note') or '无'}",
                        "",
                    ]
                )
        else:
            batch_md.append("- **词库命中：** 无")
        batch_md.append("")

    (OUT / "current-batch.md").write_text(
        "\n".join(batch_md) + "\n", encoding="utf-8"
    )
    (OUT / "terminology-review.md").write_text(
        "\n".join(term_review) + "\n", encoding="utf-8"
    )
    (OUT / "translated-markdown-head.md").write_text(
        "\n".join(md_lines[:320]) + "\n", encoding="utf-8"
    )
    (OUT / "translated-text-head.txt").write_text(
        "\n".join(txt_lines[:240]) + "\n", encoding="utf-8"
    )

    corrected = sum(1 for entry in applied if entry.get("status") == "corrected")
    summary = [
        "# 已应用校对批次",
        "",
        f"- 审阅条目：{len(applied)}",
        f"- 实质修正：{corrected}",
        "- 同步文件：JSON、Markdown、TXT、TSV",
        "",
    ]
    for entry in applied:
        summary.extend(
            [
                f"## 条目 {entry['index']}",
                "",
                f"- 状态：`{entry['status']}`",
                f"- 原译：{entry['old_target']}",
                f"- 定稿：{entry['new_target']}",
                f"- 说明：{entry['note']}",
                "",
            ]
        )
    (OUT / "applied-review.md").write_text(
        "\n".join(summary) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
