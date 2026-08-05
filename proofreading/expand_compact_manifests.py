from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "proofreading"
CANONICAL = ROOT / "satisfaction-scripts.zh.json"


def flatten_segments(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        segment
        for chapter in payload.get("chapters", [])
        for segment in chapter.get("segments", [])
    ]


def main() -> None:
    data = json.loads(CANONICAL.read_text(encoding="utf-8-sig"))
    segments = flatten_segments(data)

    for path in sorted(OUT.glob("reviewed-batch-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for entry in payload.get("entries", []):
            index = int(entry["index"])
            if index < 1 or index > len(segments):
                raise ValueError(f"Invalid entry index in {path.name}: {index}")
            segment = segments[index - 1]
            if "source" not in entry:
                entry["source"] = str(segment.get("source", ""))
                changed = True
            if "old_target" not in entry:
                entry["old_target"] = str(segment.get("target", ""))
                changed = True
            if "status" not in entry:
                entry["status"] = "corrected"
                changed = True
            if "note" not in entry:
                entry["note"] = "人工校对。"
                changed = True
        if changed:
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    main()
