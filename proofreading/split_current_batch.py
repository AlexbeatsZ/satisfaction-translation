from __future__ import annotations

import csv
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "proofreading" / "current-batch.tsv"
OUT = ROOT / "proofreading" / "work" / "003730-004229"
CHUNK_SIZE = 50


def main() -> None:
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        rows = list(reader)

    if len(rows) != 500 or int(rows[0]["index"]) != 3730 or int(rows[-1]["index"]) != 4229:
        raise ValueError(
            f"Unexpected batch: count={len(rows)}, "
            f"range={rows[0]['index'] if rows else '-'}-{rows[-1]['index'] if rows else '-'}"
        )

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for offset in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[offset : offset + CHUNK_SIZE]
        path = OUT / f"chunk-{offset // CHUNK_SIZE + 1:02d}.tsv"
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
