from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "proofreading"
BATCH = OUT / "current-batch.tsv"
INPUT = OUT / "review-input-008230-008729.json"


def main() -> None:
    payload = json.loads(INPUT.read_text(encoding="utf-8"))
    reviewed_at = str(payload["reviewed_at"])
    ranges = [(int(start), int(end)) for start, end in payload["ranges"]]
    corrections = {int(index): str(target) for index, target in payload["corrections"]}

    with BATCH.open("r", encoding="utf-8", newline="") as handle:
        rows = {
            int(row["index"]): row
            for row in csv.DictReader(handle, delimiter="\t")
        }

    expected = set(range(8230, 8730))
    if set(rows) != expected:
        missing = sorted(expected - set(rows))
        extra = sorted(set(rows) - expected)
        raise ValueError(
            f"Unexpected batch indexes; missing={missing[:10]}, extra={extra[:10]}"
        )

    covered: set[int] = set()
    for start, end in ranges:
        current = set(range(start, end + 1))
        overlap = covered & current
        if overlap:
            raise ValueError(f"Overlapping reviewed ranges: {sorted(overlap)[:10]}")
        covered |= current

        entries = []
        for index in sorted(i for i in corrections if start <= i <= end):
            row = rows[index]
            old_target = row["translation"]
            new_target = corrections[index]
            if old_target == new_target:
                raise ValueError(f"Correction {index} does not change the target")
            entries.append(
                {
                    "index": index,
                    "new_target": new_target,
                    "status": "corrected",
                    "note": "人工校对。",
                    "source": row["source"],
                    "old_target": old_target,
                }
            )

        manifest = {
            "range": {"start": start, "end": end},
            "reviewed_at": reviewed_at,
            "format": "compact-v1",
            "entries": entries,
        }
        path = OUT / f"reviewed-batch-{start:06d}-{end:06d}.json"
        path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if covered != expected:
        missing = sorted(expected - covered)
        raise ValueError(f"Reviewed ranges do not cover full batch: {missing[:10]}")
    if not set(corrections).issubset(expected):
        extra = sorted(set(corrections) - expected)
        raise ValueError(f"Correction indexes outside batch: {extra[:10]}")

    print(f"Generated {len(ranges)} manifests with {len(corrections)} corrections.")


if __name__ == "__main__":
    main()
