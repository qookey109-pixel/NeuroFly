from __future__ import annotations

"""Pure, evidence-only comparison for the isolated Stage 2 odor-gain A/B.

No action selection, runtime control, or production promotion is performed here.
"""

from typing import Any

PRIMARY_METRICS = (
    "blocked_forward_fraction",
    "near_wall_forward_fraction",
    "revisit_fraction_mean",
    "deaths_per_1000_decisions",
    "food_events",
    "best_episode_food_progress",
    "stage2_clear_delta",
    "world_tick_delta",
    "discarded_decision_count",
)


def compare_candidate(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    if baseline.get("initial_stage") != 2 or candidate.get("initial_stage") != 2:
        raise ValueError("Both arms must start from Stage 2")
    if baseline.get("source_sha256") != candidate.get("source_sha256"):
        raise ValueError("Comparisons require exactly identical source-state hashes")
    if baseline.get("steps") != candidate.get("steps"):
        raise ValueError("Both arms must contain the same number of decisions")

    deltas: dict[str, float | None] = {}
    for name in PRIMARY_METRICS:
        b, c = baseline.get(name), candidate.get(name)
        deltas[name] = None if b is None or c is None else float(c) - float(b)

    # An exploratory candidate is *not* production-safe or validated. A positive
    # signal must be independently repeated and then tested in a separate PR.
    required = (
        "blocked_forward_fraction",
        "near_wall_forward_fraction",
        "revisit_fraction_mean",
        "deaths_per_1000_decisions",
        "food_events",
        "stage2_clear_delta",
    )
    clock_baseline = baseline.get("world_tick_delta")
    clock_candidate = candidate.get("world_tick_delta")
    discarded_baseline = baseline.get("discarded_decision_count")
    discarded_candidate = candidate.get("discarded_decision_count")
    valid_exposure = all(
        isinstance(v, int) and not isinstance(v, bool) and v >= 0
        for v in (
            clock_baseline, clock_candidate,
            discarded_baseline, discarded_candidate,
        )
    )
    if valid_exposure:
        allowable_tick_drift = max(1, int(clock_baseline * 0.05))
        exposure_comparable = bool(
            clock_baseline > 0
            and clock_candidate > 0
            and abs(clock_candidate - clock_baseline) <= allowable_tick_drift
            and discarded_baseline <= baseline["steps"] * 0.1
            and discarded_candidate <= candidate["steps"] * 0.1
            and abs(discarded_candidate - discarded_baseline)
            <= max(1, int(baseline["steps"] * 0.01))
        )
    else:
        allowable_tick_drift = None
        exposure_comparable = False
    sufficient_data = all(deltas[name] is not None for name in required)
    exploratory_signal = bool(
        sufficient_data
        and exposure_comparable
        and deltas["blocked_forward_fraction"] <= -0.03
        and deltas["near_wall_forward_fraction"] <= 0.02
        and deltas["revisit_fraction_mean"] <= 0.02
        and deltas["deaths_per_1000_decisions"] <= (1000 / baseline["steps"])
        and deltas["food_events"] >= 0
        and deltas["stage2_clear_delta"] >= 0
    )

    return {
        "candidate_minus_baseline": deltas,
        "sufficient_data": sufficient_data,
        "exposure_comparable": exposure_comparable,
        "world_tick_drift_allowance": allowable_tick_drift,
        "wall_clock_comparability_gate": "world_ticks_within_5_percent_and_discarded_decisions_within_1_percent",
        "exploratory_signal_only": exploratory_signal,
        "repeat_study_required": True,
        "production_promotion_authorized": False,
    }
