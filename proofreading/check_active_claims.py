from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CLAIMS_DIR = ROOT / "proofreading" / "claims" / "active"
CANONICAL = ROOT / "satisfaction-scripts.zh.json"

ALLOWED_STATUSES = {"claimed", "reviewing", "ready_to_merge", "blocked"}
ALLOWED_WORK_TYPES = {"translation", "proofreading", "translation-proofreading"}


@dataclass(frozen=True)
class Claim:
    path: Path
    start: int
    end: int
    owner: str
    branch: str
    status: str
    work_type: str


def require_string(payload: dict[str, Any], key: str, path: Path) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: `{key}` must be a non-empty string")
    return value.strip()


def total_entries() -> int:
    payload = json.loads(CANONICAL.read_text(encoding="utf-8-sig"))
    return sum(len(chapter.get("segments", [])) for chapter in payload.get("chapters", []))


def load_claim(path: Path, total: int) -> Claim:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc

    range_payload = payload.get("range")
    if not isinstance(range_payload, dict):
        raise ValueError(f"{path}: `range` must be an object")

    start = range_payload.get("start")
    end = range_payload.get("end")
    if not isinstance(start, int) or isinstance(start, bool):
        raise ValueError(f"{path}: `range.start` must be an integer")
    if not isinstance(end, int) or isinstance(end, bool):
        raise ValueError(f"{path}: `range.end` must be an integer")
    if start < 1 or end < start or end > total:
        raise ValueError(f"{path}: invalid range {start}-{end}; valid bounds are 1-{total}")

    owner = require_string(payload, "owner", path)
    branch = require_string(payload, "branch", path)
    status = require_string(payload, "status", path)
    work_type = require_string(payload, "work_type", path)
    require_string(payload, "started_at", path)
    require_string(payload, "updated_at", path)

    if status not in ALLOWED_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_STATUSES))
        raise ValueError(f"{path}: invalid status `{status}`; allowed: {allowed}")
    if work_type not in ALLOWED_WORK_TYPES:
        allowed = ", ".join(sorted(ALLOWED_WORK_TYPES))
        raise ValueError(f"{path}: invalid work_type `{work_type}`; allowed: {allowed}")

    return Claim(
        path=path,
        start=start,
        end=end,
        owner=owner,
        branch=branch,
        status=status,
        work_type=work_type,
    )


def main() -> None:
    total = total_entries()
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    claims = [load_claim(path, total) for path in sorted(CLAIMS_DIR.glob("*.json"))]
    claims.sort(key=lambda claim: (claim.start, claim.end, claim.path.name))

    for previous, current in zip(claims, claims[1:]):
        if current.start <= previous.end:
            raise ValueError(
                "Overlapping active translation claims:\n"
                f"- {previous.path.name}: {previous.start}-{previous.end} "
                f"({previous.owner}, {previous.branch}, {previous.status})\n"
                f"- {current.path.name}: {current.start}-{current.end} "
                f"({current.owner}, {current.branch}, {current.status})"
            )

    if not claims:
        print("No active translation claims.")
        return

    print(f"Validated {len(claims)} active translation claim(s):")
    for claim in claims:
        print(
            f"- {claim.start}-{claim.end}: {claim.owner} | "
            f"{claim.work_type} | {claim.status} | {claim.branch}"
        )


if __name__ == "__main__":
    main()
