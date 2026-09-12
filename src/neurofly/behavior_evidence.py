from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


BEHAVIOR_EVIDENCE_SCHEMA = "neurofly-behavior-evidence-v1"
VALID_ACTIONS = ("TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD")
FOOD_CUE_SIDES = ("LEFT", "RIGHT", "BALANCED")
FOOD_CUE_EPSILON = 1e-6


def _action_histogram(observations: Iterable[dict[str, Any]], field: str) -> dict[str, int]:
    counts = Counter(
        str(item.get(field))
        for item in observations
        if item.get(field) in VALID_ACTIONS
    )
    return {action: int(counts.get(action, 0)) for action in VALID_ACTIONS}


def _food_cue_side(item: dict[str, Any]) -> str:
    try:
        left = float(item.get("food_odor_left") or 0.0)
        right = float(item.get("food_odor_right") or 0.0)
    except (TypeError, ValueError, OverflowError):
        return "BALANCED"
    difference = left - right
    if difference > FOOD_CUE_EPSILON:
        return "LEFT"
    if difference < -FOOD_CUE_EPSILON:
        return "RIGHT"
    return "BALANCED"


def _food_cue_evidence(observations: list[dict[str, Any]]) -> dict[str, Any]:
    cue_counts = Counter({side: 0 for side in FOOD_CUE_SIDES})
    actions_by_cue = {
        side: Counter({action: 0 for action in VALID_ACTIONS})
        for side in FOOD_CUE_SIDES
    }
    directional_turn_trials = 0
    directional_turn_aligned = 0

    for item in observations:
        side = _food_cue_side(item)
        cue_counts[side] += 1
        raw_action = item.get("raw_brain_action")
        if raw_action in VALID_ACTIONS:
            actions_by_cue[side][str(raw_action)] += 1

        if side not in {"LEFT", "RIGHT"} or raw_action not in {"TURN_LEFT", "TURN_RIGHT"}:
            continue
        directional_turn_trials += 1
        if (side == "LEFT" and raw_action == "TURN_LEFT") or (
            side == "RIGHT" and raw_action == "TURN_RIGHT"
        ):
            directional_turn_aligned += 1

    return {
        "food_cue_side_counts": {
            side: int(cue_counts[side])
            for side in FOOD_CUE_SIDES
        },
        "raw_action_by_food_cue": {
            side: {
                action: int(actions_by_cue[side][action])
                for action in VALID_ACTIONS
            }
            for side in FOOD_CUE_SIDES
        },
        "raw_food_directional_turn_trials": directional_turn_trials,
        "raw_food_directional_turn_aligned": directional_turn_aligned,
        "raw_food_directional_turn_alignment_rate": (
            round(directional_turn_aligned / float(directional_turn_trials), 6)
            if directional_turn_trials
            else None
        ),
    }


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
    sensory adapters, maze state, or anti-stall policy. Bilateral food-cue
    statistics are observational associations only and do not establish learned
    navigation, causality, or biological intent.
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

    summary = {
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
    summary.update(_food_cue_evidence(observations))
    return summary
