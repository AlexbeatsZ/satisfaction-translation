from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROOFREADING = ROOT / "proofreading"
JSON_PATH = ROOT / "satisfaction-scripts.zh.json"
MD_PATH = ROOT / "satisfaction-scripts.zh.md"
TXT_PATH = ROOT / "satisfaction-scripts.zh.txt"
TSV_PATH = ROOT / "satisfaction-text.tsv"

SPEAKER_PREFIX_RE = re.compile(r"^【話者[:：][^】]*】")
JAPANESE_LETTER_RE = re.compile(r"[ぁ-ゖァ-ヺー]")
WHITESPACE_RE = re.compile(r"\s+")
PAREN_RUBY_RE = re.compile(r"(?<=[\u3400-\u9fff々ヶ])\([ぁ-ゖァ-ヺー]+\)")
ANGLE_RUBY_RE = re.compile(r"<[ぁ-ゖァ-ヺー]+>")


def normalize_source(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lstrip("\u3000")
    text = SPEAKER_PREFIX_RE.sub("", text, count=1)
    text = PAREN_RUBY_RE.sub("", text)
    text = ANGLE_RUBY_RE.sub("", text)
    return WHITESPACE_RE.sub("", text)


def flatten(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    return [
        (str(chapter.get("title", "")), segment)
        for chapter in payload.get("chapters", [])
        for segment in chapter.get("segments", [])
    ]


def fail(errors: list[str], message: str) -> None:
    if len(errors) < 100:
        errors.append(message)


def main() -> None:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8-sig"))
    segments = flatten(data)
    errors: list[str] = []
    reviewed: set[int] = set()
    final_manifest_target: dict[int, str] = {}

    payloads = [
        (path, json.loads(path.read_text(encoding="utf-8")))
        for path in sorted(PROOFREADING.glob("reviewed-batch-*.json"))
    ]
    payloads.sort(key=lambda item: bool(item[1].get("followup")))

    for path, payload in payloads:
        followup = bool(payload.get("followup"))
        entry_indices: set[int] = set()
        for entry in payload.get("entries", []):
            index = int(entry["index"])
            if index in entry_indices:
                fail(errors, f"{path.name}: duplicate entry {index}")
                continue
            entry_indices.add(index)
            if not 1 <= index <= len(segments):
                fail(errors, f"{path.name}: invalid entry {index}")
                continue
            source = str(segments[index - 1][1].get("source", ""))
            if normalize_source(entry.get("source", "")) != normalize_source(source):
                fail(errors, f"{path.name}: source mismatch at {index}")
            old = str(entry.get("old_target", ""))
            new = str(entry.get("new_target", ""))
            if followup:
                if index not in reviewed:
                    fail(errors, f"{path.name}: follow-up {index} was not reviewed earlier")
                elif index in final_manifest_target and final_manifest_target[index] != old:
                    fail(errors, f"{path.name}: broken old_target chain at {index}")
            elif index in reviewed:
                fail(errors, f"{path.name}: duplicate reviewed entry {index}")
            final_manifest_target[index] = new

        range_payload = payload.get("range")
        if followup:
            continue
        if range_payload:
            start, end = int(range_payload["start"]), int(range_payload["end"])
            covered = set(range(start, end + 1))
            if not 1 <= start <= end <= len(segments):
                fail(errors, f"{path.name}: invalid range {start}-{end}")
                continue
            if not entry_indices.issubset(covered):
                fail(errors, f"{path.name}: entry outside range")
        else:
            covered = entry_indices
        overlap = reviewed.intersection(covered)
        if overlap:
            fail(errors, f"{path.name}: overlapping reviewed range at {min(overlap)}")
        reviewed.update(covered)

    skipped_payload = json.loads(
        (PROOFREADING / "skipped-ranges.json").read_text(encoding="utf-8")
    )
    skipped: set[int] = set()
    for item in skipped_payload.get("ranges", []):
        start, end = int(item["start"]), int(item["end"])
        current = set(range(start, end + 1))
        overlap = (reviewed | skipped).intersection(current)
        if overlap:
            fail(errors, f"skipped range {start}-{end} overlaps at {min(overlap)}")
        skipped.update(current)

    for index, expected in final_manifest_target.items():
        actual = str(segments[index - 1][1].get("target", ""))
        if actual != expected:
            fail(errors, f"canonical target does not match manifest at {index}")

    for index in sorted(reviewed):
        source = str(segments[index - 1][1].get("source", ""))
        target = str(segments[index - 1][1].get("target", ""))
        visible_source = SPEAKER_PREFIX_RE.sub("", source, count=1).strip()
        if not target.strip():
            fail(errors, f"reviewed target is empty at {index}")
        if JAPANESE_LETTER_RE.search(target):
            fail(errors, f"Japanese letter remains in reviewed target at {index}: {target}")
        if visible_source.startswith("「") and visible_source.endswith("」"):
            if not (target.startswith("「") and target.endswith("」")):
                fail(errors, f"dialogue quotes missing at {index}: {target}")

    targets = [str(segment.get("target", "")) for _, segment in segments]
    md_nonempty = [
        line for line in MD_PATH.read_text(encoding="utf-8-sig").splitlines() if line.strip()
    ]
    txt_nonempty = [
        line for line in TXT_PATH.read_text(encoding="utf-8-sig").splitlines() if line.strip()
    ]
    if md_nonempty != targets:
        fail(errors, "Markdown targets are not synchronized with JSON natural order")
    if txt_nonempty != targets:
        fail(errors, "TXT targets are not synchronized with JSON natural order")

    with TSV_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    rows_by_file: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_file[str(row.get("file", ""))].append(row)
    for title, chapter in ((str(c.get("title", "")), c) for c in data.get("chapters", [])):
        chapter_segments = list(chapter.get("segments", []))
        chapter_rows = rows_by_file.get(title, [])
        if len(chapter_rows) != len(chapter_segments):
            fail(errors, f"TSV segment count mismatch for {title}")
            continue
        for local_index, (segment, row) in enumerate(zip(chapter_segments, chapter_rows)):
            if str(row.get("translation", "")) != str(segment.get("target", "")):
                fail(errors, f"TSV target mismatch for {title}[{local_index}]")

    if errors:
        raise SystemExit("Translation quality check failed:\n- " + "\n- ".join(errors))
    print(
        f"OK: {len(segments):,} segments; {len(reviewed):,} reviewed; "
        f"{len(skipped):,} skipped; {len(final_manifest_target):,} manifested targets"
    )


if __name__ == "__main__":
    main()
