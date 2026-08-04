from __future__ import annotations

import csv
import json
import re
import unicodedata
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
BLOCKED_FROM = 90


def normalize_source(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = text.strip().lstrip("\u3000")
    text = SPEAKER_PREFIX_RE.sub("", text, count=1)
    text = re.sub(r"(?<=[\u3400-\u9fff々ヶ])\([ぁ-ゖァ-ヺー]+\)", "", text)
    text = re.sub(r"<[ぁ-ゖァ-ヺー]+>", "", text)
    return WHITESPACE_RE.sub("", text)


def load_files() -> tuple[
    dict[str, Any], list[tuple[int, dict[str, Any]]], list[str], list[str], list[dict[str, str]], list[str]
]:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8-sig"))
    flattened: list[tuple[int, dict[str, Any]]] = []
    for chapter_position, chapter in enumerate(data.get("chapters", [])):
        chapter_index = int(chapter.get("index", chapter_position))
        for segment in chapter.get("segments", []):
            flattened.append((chapter_index, segment))

    md_lines = MD_PATH.read_text(encoding="utf-8-sig").splitlines()
    txt_lines = TXT_PATH.read_text(encoding="utf-8-sig").splitlines()
    with TSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    return data, flattened, md_lines, txt_lines, rows, fields


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
        if str(term["source"]) in source:
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
    data, flattened, md_lines, txt_lines, tsv_rows, tsv_fields = load_files()
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

    manifests = sorted(OUT.glob("reviewed-batch-*.json"))
    applied: list[dict[str, Any]] = []
    seen: set[int] = set()

    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest.get("entries", []):
            index = int(entry["index"])
            if index in seen:
                raise ValueError(f"Duplicate reviewed entry: {index}")
            if index >= BLOCKED_FROM:
                raise ValueError(
                    f"Entry {index} is at or beyond structural mismatch boundary {BLOCKED_FROM}"
                )
            seen.add(index)
            position = index - 1

            tsv_source = normalize_source(tsv_rows[position].get("source", ""))
            json_source = normalize_source(flattened[position][1].get("source", ""))
            manifest_source = normalize_source(entry.get("source", ""))
            if not (tsv_source == json_source == manifest_source):
                raise ValueError(
                    f"Reviewed entry {index} source mismatch: "
                    f"tsv={tsv_source!r}, json={json_source!r}, manifest={manifest_source!r}"
                )

            old = str(entry["old_target"])
            new = str(entry["new_target"])
            segment = flattened[position][1]
            current_values = {
                "JSON": str(segment.get("target", "")),
                "Markdown": md_lines[md_nonempty[position]],
                "TXT": txt_lines[txt_nonempty[position]],
            }
            for label, current in current_values.items():
                if current not in (old, new):
                    raise ValueError(
                        f"{label} entry {index} mismatch: expected {old!r} or {new!r}, got {current!r}"
                    )

            segment["target"] = new
            md_lines[md_nonempty[position]] = new
            txt_lines[txt_nonempty[position]] = new
            tsv_rows[position]["translation"] = new
            applied.append(entry)

    # Preserve the repository's current translation in the TSV for inspection.
    # This is positional only; it does not claim semantic validity after BLOCKED_FROM.
    for position, (_chapter, segment) in enumerate(flattened):
        tsv_rows[position]["translation"] = str(segment.get("target", ""))
    for entry in applied:
        tsv_rows[int(entry["index"]) - 1]["translation"] = str(entry["new_target"])

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

    terms, glossary = load_terms()
    request = json.loads((OUT / "request.json").read_text(encoding="utf-8"))
    start = int(request.get("start", 85))
    count = int(request.get("count", 40))
    selected: list[dict[str, Any]] = []

    for index in range(start, min(start + count, len(tsv_rows) + 1)):
        position = index - 1
        chapter_index, segment = flattened[position]
        source = str(tsv_rows[position].get("source", ""))
        target = str(segment.get("target", ""))
        selected.append(
            {
                "index": index,
                "chapter": chapter_index,
                "file": tsv_rows[position].get("file", ""),
                "line": tsv_rows[position].get("line", ""),
                "kind": tsv_rows[position].get("kind", ""),
                "voice": tsv_rows[position].get("voice", ""),
                "source": source,
                "translation": target,
                "terms": visible_terms(terms, glossary, chapter_index, source, target),
            }
        )

    fieldnames = [
        "index", "chapter", "file", "line", "kind", "voice",
        "source", "translation", "terms"
    ]
    with (OUT / "current-batch.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in selected:
            writer.writerow({**row, "terms": json.dumps(row["terms"], ensure_ascii=False)})

    last = selected[-1]["index"] if selected else start - 1
    batch = [
        "# 当前校对批次", "",
        f"- 请求范围：第 {start}–{last} 条",
        f"- 实际条数：{len(selected)}",
        f"- 结构错位断点：第 {BLOCKED_FROM} 条；该条及以后只作诊断，不执行普通校对。",
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
                batch.append(
                    f"  - `{term['mode']}`：`{term['source']}` → `{term['target']}`；{state}"
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
        if row["index"] >= BLOCKED_FROM:
            batch.append("- **状态：** `结构错位，禁止普通校对`")
        batch.append("")

    (OUT / "current-batch.md").write_text("\n".join(batch) + "\n", encoding="utf-8")
    (OUT / "terminology-review.md").write_text(
        "\n".join(term_report) + "\n", encoding="utf-8"
    )

    corrected = sum(1 for entry in applied if entry.get("status") == "corrected")
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
        f"| 结构错位断点 | 第 {BLOCKED_FROM} 条 |",
        "| 下步工作 | 先修复第 90 条起的日中错位，再继续措辞校对 |",
        "| 最后更新 | 2026-08-05 |", "",
        "## 词库规则", "",
        "- `terminology.yaml` 与 `glossary.json` 是可维护的校对依据。",
        "- active hard 默认统一，但词条错误时修改词库，不扭曲译文。",
        "- preferred 是稳定译法建议；按当前语境决定。",
        "- 长词优先；代词提示仅在命中词条的局部上下文有效。", "",
        "## 恢复说明", "",
        f"普通校对从第 {BLOCKED_FROM} 条暂停。已完成条目均有 `reviewed-batch-*.json` 记录。",
    ]
    PROGRESS_PATH.write_text("\n".join(progress) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
