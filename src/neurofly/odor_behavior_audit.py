from __future__ import annotations

"""Read-only signed predator-odor / neural-turn diagnostics for published states.

Every statistic is descriptive. The analyzed states are post-decision telemetry,
not experimental causal evidence. No actions are computed for the fly.
"""

from collections import Counter
from typing import Any

SCHEMA = "neurofly-stage2-live-odor-action-audit-v1"
CONTRAST_THRESHOLD = 0.10
MIN_LATERAL_CONTRAST = 0.01
ACTIONS = {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}


def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["orientation"] for row in rows)
    turns = counts["away"] + counts["toward"]
    size = len(rows)
    return {
        "decisions": size,
        "away_turns": counts["away"],
        "toward_turns": counts["toward"],
        "forward": counts["forward"],
        "hold": counts["hold"],
        "ambiguous_turns": counts["ambiguous_turn"],
        "away_given_turn_fraction": (
            counts["away"] / turns if turns else None
        ),
        "net_away_minus_toward_per_decision": (
            (counts["away"] - counts["toward"]) / size if size else None
        ),
        "episodes": len({row["episode"] for row in rows}),
    }


def audit_published_state(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("verified") is not True or state.get("backend") != "malecns":
        raise ValueError("Only verified real MaleCNS publications can be audited")
    final = state.get("final_state") or {}
    if int(final.get("curriculum_stage", 0)) != 2:
        raise ValueError("Audit is scoped to live Stage 2 records")
    trajectory = state.get("trajectory")
    if not isinstance(trajectory, list) or not trajectory:
        raise ValueError("A nonempty published trajectory is required")

    rows: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    for sample in trajectory:
        if sample.get("state_kind") != "neural_decision":
            continue
        if sample.get("action_overridden") or sample.get("direct_action_override_enabled"):
            raise ValueError("Cannot audit overwritten or externally forced neural actions")
        action = str(sample.get("raw_brain_action", ""))
        if action not in ACTIONS or action != sample.get("applied_action"):
            raise ValueError("Publication must contain a valid unchanged neural action")
        episode = int(sample["episode"])
        total_ticks = int(sample["total_ticks"])
        key = (episode, total_ticks)
        if key in seen:
            raise ValueError("Duplicate neural decision in published trajectory")
        seen.add(key)

        telemetry = (sample.get("brain") or {}).get("telemetry") or {}
        odor = telemetry.get("olfaction") or {}
        danger_diff = float(odor["danger_left"]) - float(odor["danger_right"])
        food_diff = float(odor["food_left"]) - float(odor["food_right"])
        strong = abs(danger_diff) >= CONTRAST_THRESHOLD
        if danger_diff > MIN_LATERAL_CONTRAST:
            orientation = (
                "away" if action == "TURN_RIGHT" else
                "toward" if action == "TURN_LEFT" else action.lower()
            )
        elif danger_diff < -MIN_LATERAL_CONTRAST:
            orientation = (
                "away" if action == "TURN_LEFT" else
                "toward" if action == "TURN_RIGHT" else action.lower()
            )
        else:
            orientation = "ambiguous_turn" if action.startswith("TURN") else action.lower()

        vision = telemetry.get("vision") or {}
        walls = vision.get("wall_distance_cells") or {}
        try:
            near_wall = (
                float(walls["front"]) <= float(
                    telemetry.get("frontal_wall_distance_threshold", 0.75)
                )
            )
        except (ValueError, KeyError, TypeError):
            near_wall = False

        rows.append({
            "episode": episode,
            "tick": total_ticks,
            "strong": strong,
            "near_wall": near_wall,
            "orientation": orientation,
            "odor_conflict": danger_diff * food_diff < 0,
        })
    if not rows:
        raise ValueError("No neural decisions available in the published trajectory")

    strong = [row for row in rows if row["strong"]]
    return {
        "schema": SCHEMA,
        "source_generated_unix": state.get("generated_unix"),
        "curriculum_stage": 2,
        "curriculum_stage_clears": final.get("curriculum_stage_clears"),
        "total_clears": final.get("total_clears"),
        "total_deaths": final.get("total_deaths"),
        "counts": {
            "all": _stats(rows),
            "strong_danger": _stats(strong),
            "weak_danger": _stats([row for row in rows if not row["strong"]]),
            "near_wall_strong_danger": _stats([
                row for row in strong if row["near_wall"]
            ]),
            "strong_danger_food_conflict": _stats([
                row for row in strong if row["odor_conflict"]
            ]),
        },
        "sampling": {
            "distinct_episodes": len({row["episode"] for row in rows}),
            "independent_replicates": 0,
            "threshold_absolute_danger_lateral_contrast": CONTRAST_THRESHOLD,
            "threshold_minimum_directional_contrast": MIN_LATERAL_CONTRAST,
        },
        "claim_limits": {
            "descriptive_observations_only": True,
            "temporal_correlation_not_causality": True,
            "away_turn_is_odor_proxy_not_validated_escape": True,
            "stage2_improvement_verified": False,
            "production_gain_change_authorized": False,
            "decoder_change_authorized": False,
        },
    }
