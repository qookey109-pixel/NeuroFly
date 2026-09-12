from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


BEHAVIOR_EVIDENCE_SCHEMA = "neurofly-behavior-evidence-v1"
VALID_ACTIONS = ("TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD")


def _action_histogram(observations: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    counts = Counter(
        str(item.get(field))
        for item in observations
        if item.get(field) in VALID_ACTIONS
    )
    return {action: int(counts.get(action, 0)) for action in VALID_ACTIONS}


def summarize_behavior(
    observations: list[dict[str, Any]],
    *,
    navigable_cells: int,
    food_before: int,
    food_after: int,
    clears_before: int,
    clears_after: int,
    deaths_before: int,
    deaths_after: int,
) -> dict[str, Any]:
    """Build deterministic behavior evidence without changing the controller.

    The summary only aggregates outcomes and provenance already emitted by a
    training batch. It never feeds back into the MaleCNS decoder, reward model,
    sensory adapters, maze state, or anti-stall policy.
    """

    decisions = len(observations)
    if decisions < 1:
        raise ValueError("Behavior evidence requires at least one observation")
    if navigable_cells < 1:
        raise ValueError("navigable_cells must be >= 1")

    positions: set[tuple[int, int]] = set()
    override_reasons: Counter[str] = Counter()
    overrides = 0
    stages: list[int] = []

    for item in observations:
        x = item.get("fly_x")
        y = item.get("fly_y")
        if x is not None and y is not None:
            positions.add((int(x), int(y)))

        if bool(item.get("action_overridden", False)):
            overrides += 1
            reason = item.get("override_reason")
            override_reasons[str(reason or "unspecified")] += 1

        stage = item.get("curriculum_stage")
        if stage is not None:
            stages.append(int(stage))

    batch_food = max(0, int(food_after) - int(food_before))
    batch_clears = max(0, int(clears_after) - int(clears_before))
    batch_deaths = max(0, int(deaths_after) - int(deaths_before))
    unique_cells = len(positions)

    return {
        "schema": BEHAVIOR_EVIDENCE_SCHEMA,
        "decisions": decisions,
        "batch_food": batch_food,
        "food_per_100_decisions": round((batch_food * 100.0) / decisions, 6),
        "batch_clears": batch_clears,
        "batch_deaths": batch_deaths,
        "unique_cells": unique_cells,
        "navigable_cells": int(navigable_cells),
        "coverage_ratio": round(unique_cells / float(navigable_cells), 6),
        "raw_action_histogram": _action_histogram(observations, "raw_brain_action"),
        "applied_action_histogram": _action_histogram(observations, "applied_action"),
        "overrides": overrides,
        "override_rate": round(overrides / float(decisions), 6),
        "override_reasons": dict(sorted(override_reasons.items())),
        "curriculum_stage_start": stages[0] if stages else None,
        "curriculum_stage_end": stages[-1] if stages else None,
    }
