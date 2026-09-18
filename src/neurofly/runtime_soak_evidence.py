from __future__ import annotations

from datetime import datetime
from typing import Any


SCHEMA = "neurofly-segmented-runtime-soak-evidence-v0.1"


def _timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_segmented_soak_evidence(payload: dict[str, Any]) -> dict[str, bool]:
    runs = payload.get("runs")
    observed = payload.get("observed") or {}
    rule = payload.get("acceptance_rule") or {}
    interpretation = payload.get("interpretation") or {}

    if not isinstance(runs, list) or not runs:
        return {
            "schema_exact": payload.get("schema") == SCHEMA,
            "runs_present": False,
        }

    sorted_runs = sorted(runs, key=lambda item: int(item["run_number"]))
    numbers = [int(item["run_number"]) for item in sorted_runs]
    consecutive = all(
        number == numbers[0] + index
        for index, number in enumerate(numbers)
    )
    all_success = all(
        item.get("status") == "completed"
        and item.get("conclusion") == "success"
        for item in sorted_runs
    )

    first_created = _timestamp(sorted_runs[0]["created_at"])
    last_updated = _timestamp(sorted_runs[-1]["updated_at"])
    span_seconds = (last_updated - first_created).total_seconds()

    gaps = []
    for previous, current in zip(sorted_runs, sorted_runs[1:]):
        previous_end = _timestamp(previous["updated_at"])
        current_start = _timestamp(
            current.get("run_started_at") or current["created_at"]
        )
        gaps.append((current_start - previous_end).total_seconds())
    max_positive_gap = max([0.0, *gaps])

    minimum_hours = float(rule.get("minimum_wall_clock_hours") or 0.0)
    maximum_gap = float(
        rule.get("maximum_positive_handoff_idle_gap_seconds") or 0.0
    )

    summary_matches = (
        observed.get("first_run_number") == numbers[0]
        and observed.get("last_run_number") == numbers[-1]
        and observed.get("run_count") == len(sorted_runs)
        and int(observed.get("wall_clock_seconds") or -1) == int(span_seconds)
        and observed.get("all_runs_success") is all_success
        and observed.get("consecutive_run_numbers") is consecutive
        and float(
            observed.get("maximum_positive_handoff_idle_gap_seconds") or 0.0
        )
        == max_positive_gap
    )

    return {
        "schema_exact": payload.get("schema") == SCHEMA,
        "status_pass": payload.get("status") == "PASS",
        "runs_present": True,
        "run_numbers_consecutive": consecutive,
        "all_runs_success": all_success,
        "minimum_wall_clock_met": span_seconds >= minimum_hours * 3600.0,
        "handoff_idle_gap_within_limit": max_positive_gap <= maximum_gap,
        "summary_recomputes_exactly": summary_matches,
        "segmented_claim_open": (
            interpretation.get("segmented_runtime_24h_soak_validated") is True
        ),
        "single_process_claim_closed": (
            interpretation.get("continuous_single_process_uptime_validated")
            is False
        ),
        "zero_data_loss_claim_closed": (
            interpretation.get("zero_data_loss_claimed") is False
        ),
    }
