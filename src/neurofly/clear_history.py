from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_SCHEMA = "neurofly-clear-history-v1"


def _normalized_clear(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "runtime_clear_index": max(1, int(item.get("clear_index", 1))),
        "episode": max(1, int(item.get("episode", 1))),
        "seconds": max(0.0, float(item.get("seconds", 0.0))),
        "ticks": max(1, int(item.get("ticks", 1))),
        "total_ticks": max(1, int(item.get("total_ticks", 1))),
        "world_ticks": max(0, int(item.get("world_ticks", 0))),
        "total_world_ticks": max(0, int(item.get("total_world_ticks", 0))),
    }


def _event_id(item: dict[str, Any]) -> str:
    payload = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def empty_history() -> dict[str, Any]:
    return {
        "schema": HISTORY_SCHEMA,
        "total_records": 0,
        "records": [],
    }


def merge_clear_history(
    history: dict[str, Any],
    site_state: dict[str, Any],
    *,
    run_id: str,
    run_attempt: str,
    recorded_at_utc: str | None = None,
) -> tuple[dict[str, Any], int]:
    if history.get("schema") != HISTORY_SCHEMA:
        raise ValueError("Invalid clear-history schema")
    records = history.get("records")
    if not isinstance(records, list):
        raise ValueError("Invalid clear-history records")

    if site_state.get("verified") is not True or site_state.get("backend") != "malecns":
        raise ValueError("Clear history only accepts verified MaleCNS site state")
    source_receipt = str(site_state.get("source_receipt_sha256") or "")
    if len(source_receipt) != 64:
        raise ValueError("Verified site state is missing source receipt SHA256")

    final_state = site_state.get("final_state") or {}
    source_history = final_state.get("clear_history") or []
    if not isinstance(source_history, list):
        raise ValueError("Invalid source clear history")

    existing_ids = {
        str(record.get("event_id"))
        for record in records
        if isinstance(record, dict) and record.get("event_id")
    }
    next_index = max(
        [int(record.get("history_index", 0)) for record in records if isinstance(record, dict)] or [0]
    )
    timestamp = recorded_at_utc or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    added = 0

    for raw_item in source_history:
        if not isinstance(raw_item, dict):
            raise ValueError("Invalid clear-history entry")
        normalized = _normalized_clear(raw_item)
        event_id = _event_id(normalized)
        if event_id in existing_ids:
            continue
        next_index += 1
        records.append(
            {
                "history_index": next_index,
                "event_id": event_id,
                **normalized,
                "source_receipt_sha256": source_receipt,
                "recorded_by_run_id": str(run_id),
                "recorded_by_run_attempt": str(run_attempt),
                "recorded_at_utc": timestamp,
            }
        )
        existing_ids.add(event_id)
        added += 1

    history["total_records"] = len(records)
    return history, added


def load_history(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_history()
    return json.loads(path.read_text(encoding="utf-8"))


def write_history(path: Path, history: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(history, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Append verified maze clears to the permanent NeuroFly history.")
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--history", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    args = parser.parse_args()

    site_state = json.loads(args.state.read_text(encoding="utf-8"))
    history = load_history(args.history)
    history, added = merge_clear_history(
        history,
        site_state,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
    )
    write_history(args.history, history)
    print(
        "PERMANENT_CLEAR_HISTORY",
        f"added={added}",
        f"total={history['total_records']}",
        f"path={args.history}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
