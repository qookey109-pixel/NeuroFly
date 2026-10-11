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
    sufficient_data = all(deltas[name] is not None for name in required)
    exploratory_signal = bool(
        sufficient_data
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
        "exploratory_signal_only": exploratory_signal,
        "repeat_study_required": True,
        "production_promotion_authorized": False,
    }
