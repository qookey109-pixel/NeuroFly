from __future__ import annotations

"""Observer-only turn metrics for isolated bilateral odor experiments.

This module scores decoded neural actions; it never chooses or applies an action.
An away-turn proxy is *not* evidence of successful avoidance in a live maze.
"""

from collections import Counter
from collections.abc import Iterable
from typing import Any


ACTIONS = ("TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD")
AWAY_TURN_FOR_DANGER = {
    "danger_left": "TURN_RIGHT",
    "danger_right": "TURN_LEFT",
}
CONTROL_CONDITIONS = {"neutral", "food_left", "food_right"}


def summarize_decoded_turns(
    actions: Iterable[str], *, condition: str
) -> dict[str, Any]:
    """Summarize the unchanged decoder's action output under one odor condition.

    The correct away-turn is defined only for isolated unilateral danger.
    Controls have no implied target action, and a neural decision is never
    executed in the environment by this function.
    """
    if condition not in AWAY_TURN_FOR_DANGER and condition not in CONTROL_CONDITIONS:
        raise ValueError(f"Unsupported isolated odor condition: {condition}")
    seen = tuple(actions)
    if not seen:
        raise ValueError("At least one observed neural decision is required")
    invalid = set(seen).difference(ACTIONS)
    if invalid:
        raise ValueError(f"Unknown decoded action(s): {sorted(invalid)}")

    observed = Counter(seen)
    counts = {action: int(observed[action]) for action in ACTIONS}
    total = len(seen)
    turns = counts["TURN_LEFT"] + counts["TURN_RIGHT"]
    expected_away = AWAY_TURN_FOR_DANGER.get(condition)

    result: dict[str, Any] = {
        "condition": condition,
        "decision_count": total,
        "action_counts": counts,
        "turn_count": turns,
        "turn_fraction": turns / total,
        "expected_away_turn": expected_away,
        "away_turn_fraction": None,
        "toward_turn_fraction": None,
        "net_away_minus_toward_fraction": None,
        "away_given_turn_fraction": None,
    }
    if expected_away is not None:
        toward = "TURN_LEFT" if expected_away == "TURN_RIGHT" else "TURN_RIGHT"
        result.update(
            away_turn_fraction=counts[expected_away] / total,
            toward_turn_fraction=counts[toward] / total,
            net_away_minus_toward_fraction=(
                counts[expected_away] - counts[toward]
            ) / total,
            away_given_turn_fraction=(
                counts[expected_away] / turns if turns else None
            ),
        )
    return result
