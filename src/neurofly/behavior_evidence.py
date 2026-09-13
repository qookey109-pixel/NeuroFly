from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


BEHAVIOR_EVIDENCE_SCHEMA = "neurofly-behavior-evidence-v1"
HISTORICAL_BEHAVIOR_BASELINE_SCHEMA = "neurofly-historical-behavior-baseline-v1"
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


def summarize_historical_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct reproducible descriptive metrics from a signed legacy receipt.

    Older receipts predate native Behavior Evidence v1 and therefore may not
    contain per-decision fly coordinates. This helper intentionally computes
    only metrics that are directly reconstructable from the receipt's existing
    observations. It does not invent coverage, learning, causality, or intent.
    Food acquisition is counted from explicit food/energy-food events rather
    than from a food-left delta so the result remains valid across resets.
    """

    observations = receipt.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("Historical behavior baseline requires receipt observations")
    if not all(isinstance(item, dict) for item in observations):
        raise ValueError("Historical behavior observations must be objects")

    receipt_sha = receipt.get("receipt_sha256")
    if not isinstance(receipt_sha, str) or len(receipt_sha) != 64:
        raise ValueError("Historical behavior baseline requires a receipt SHA-256")

    decisions = len(observations)
    try:
        declared_steps = int(receipt.get("steps"))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Historical receipt steps are invalid") from exc
    if declared_steps != decisions:
        raise ValueError("Historical receipt observation count does not match steps")

    override_reasons: Counter[str] = Counter()
    overrides = 0
    stages: list[int] = []
    food_events: Counter[str] = Counter()
    state_kinds: Counter[str] = Counter()
    applied_decisions = 0
    memory_values: list[str] = []
    reward_total = 0.0

    for item in observations:
        if bool(item.get("action_overridden", False)):
            overrides += 1
            override_reasons[str(item.get("override_reason") or "unspecified")] += 1

        stage = item.get("curriculum_stage")
        if stage is not None:
            stages.append(int(stage))

        event = item.get("event")
        if event in {"food", "energy_food"}:
            food_events[str(event)] += 1

        state_kind = item.get("state_kind")
        if state_kind is not None:
            state_kinds[str(state_kind)] += 1

        if item.get("decision_applied") is True:
            applied_decisions += 1

        memory_sha = item.get("memory_sha256")
        if isinstance(memory_sha, str) and len(memory_sha) == 64:
            memory_values.append(memory_sha)

        try:
            reward_total += float(item.get("reward") or 0.0)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Historical receipt contains an invalid reward") from exc

    batch_food = int(food_events["food"] + food_events["energy_food"])
    final_state = receipt.get("final_state")
    if not isinstance(final_state, dict):
        final_state = {}

    first_food_left = observations[0].get("food_left")
    last_food_left = observations[-1].get("food_left")
    clears_before = int(receipt.get("clears_before", 0) or 0)
    clears_after = int(receipt.get("clears_after", clears_before) or 0)

    summary: dict[str, Any] = {
        "schema": HISTORICAL_BEHAVIOR_BASELINE_SCHEMA,
        "receipt_sha256": receipt_sha,
        "decisions": decisions,
        "declared_steps": declared_steps,
        "state_kind_counts": dict(sorted(state_kinds.items())),
        "decision_applied_count": applied_decisions,
        "batch_food": batch_food,
        "food_event_counts": {
            "food": int(food_events["food"]),
            "energy_food": int(food_events["energy_food"]),
        },
        "food_per_100_decisions": round((batch_food * 100.0) / decisions, 6),
        "food_left_start": int(first_food_left) if first_food_left is not None else None,
        "food_left_end": int(last_food_left) if last_food_left is not None else None,
        "reward_total": round(reward_total, 6),
        "clears_before": clears_before,
        "clears_after": clears_after,
        "batch_clears": max(0, clears_after - clears_before),
        "total_deaths_at_finish": int(final_state.get("total_deaths", 0) or 0),
        "raw_action_histogram": _action_histogram(observations, "raw_brain_action"),
        "applied_action_histogram": _action_histogram(observations, "applied_action"),
        "overrides": overrides,
        "override_rate": round(overrides / float(decisions), 6),
        "override_reasons": dict(sorted(override_reasons.items())),
        "curriculum_stage_start": stages[0] if stages else None,
        "curriculum_stage_end": stages[-1] if stages else None,
        "memory_sha256_first": memory_values[0] if memory_values else None,
        "memory_sha256_last": memory_values[-1] if memory_values else None,
        "memory_sha256_unique": len(set(memory_values)),
        "memory_sha256_observations": len(memory_values),
        "world_states_seen": int(receipt.get("world_states_seen", 0) or 0),
        "live_published": int(receipt.get("live_published", 0) or 0),
        "wall_seconds": round(float(receipt.get("wall_seconds", 0.0) or 0.0), 6),
        "final_total_active_seconds": float(final_state.get("total_active_seconds", 0.0) or 0.0),
        "final_ticks": int(final_state.get("ticks", 0) or 0),
        "final_total_world_ticks": int(final_state.get("total_world_ticks", 0) or 0),
    }
    summary.update(_food_cue_evidence(observations))
    return summary
