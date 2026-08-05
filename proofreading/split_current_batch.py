from __future__ import annotations

import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "proofreading" / "current-batch.tsv"
WORK_ROOT = ROOT / "proofreading" / "work"
CHUNK_SIZE = 50
EXPECTED_COUNT = 500


def main() -> None:
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    if len(rows) != EXPECTED_COUNT:
        raise ValueError(f"Unexpected batch count: {len(rows)}")

    start = int(rows[0]["index"])
    end = int(rows[-1]["index"])
    if end - start + 1 != EXPECTED_COUNT:
        raise ValueError(f"Batch is not contiguous: {start}-{end}")

    out = WORK_ROOT / f"{start:06d}-{end:06d}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    for offset in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[offset : offset + CHUNK_SIZE]
        path = out / f"chunk-{offset // CHUNK_SIZE + 1:02d}.tsv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fields,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(chunk)


if __name__ == "__main__":
    main()
