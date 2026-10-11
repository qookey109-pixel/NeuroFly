from __future__ import annotations

import pytest

from neurofly.odor_behavior_audit import audit_published_state


def sample(
    tick: int, *, action: str, left: float, right: float,
    food_left: float = 0.0, food_right: float = 0.0,
    near_wall: bool = False, episode: int = 10,
) -> dict:
    return {
        "episode": episode, "total_ticks": tick, "state_kind": "neural_decision",
        "raw_brain_action": action, "applied_action": action,
        "action_overridden": False, "direct_action_override_enabled": False,
        "brain": {"telemetry": {
            "olfaction": {
                "danger_left": left, "danger_right": right,
                "food_left": food_left, "food_right": food_right,
            },
            "vision": {"wall_distance_cells": {"front": 0.3 if near_wall else 1.8}},
            "frontal_wall_distance_threshold": 0.75,
        }},
    }


def publication(*rows: dict) -> dict:
    return {
        "backend": "malecns", "verified": True, "generated_unix": 123,
        "final_state": {
            "curriculum_stage": 2, "curriculum_stage_clears": 0,
            "total_clears": 2, "total_deaths": 12,
        },
        "trajectory": list(rows),
    }


def test_signed_away_and_toward_uses_unchanged_decoded_action() -> None:
    report = audit_published_state(publication(
        sample(1, action="TURN_RIGHT", left=0.8, right=0.1, near_wall=True),
        sample(2, action="TURN_LEFT", left=0.8, right=0.1),
        sample(3, action="TURN_LEFT", left=0.0, right=0.5),
        sample(4, action="FORWARD", left=0.9, right=0.0),
        sample(5, action="HOLD", left=0.02, right=0.02),
    ))
    all_counts = report["counts"]["all"]
    assert all_counts["away_turns"] == 2
    assert all_counts["toward_turns"] == 1
    assert all_counts["forward"] == 1
    assert all_counts["hold"] == 1
    assert all_counts["away_given_turn_fraction"] == pytest.approx(2 / 3)
    assert report["counts"]["near_wall_strong_danger"]["away_turns"] == 1
    assert report["sampling"]["distinct_episodes"] == 1
    assert report["sampling"]["independent_replicates"] == 0
    assert report["claim_limits"]["production_gain_change_authorized"] is False


def test_food_competition_and_episode_count_are_descriptive() -> None:
    report = audit_published_state(publication(
        sample(1, action="TURN_RIGHT", left=0.4, right=0.0,
               food_left=0.0, food_right=0.6, episode=4),
        sample(2, action="TURN_LEFT", left=0.0, right=0.4,
               food_left=0.0, food_right=0.6, episode=5),
        sample(3, action="TURN_RIGHT", left=0.0, right=0.0, episode=5),
    ))
    assert report["counts"]["strong_danger_food_conflict"]["decisions"] == 1
    assert report["counts"]["weak_danger"]["ambiguous_turns"] == 1
    assert report["sampling"]["distinct_episodes"] == 2


@pytest.mark.parametrize("change", [
    {"verified": False}, {"backend": "demo"},
    {"final_state": {"curriculum_stage": 1}},
    {"trajectory": []},
])
def test_invalid_publications_fail_closed(change: dict) -> None:
    state = publication(sample(1, action="FORWARD", left=0.0, right=0.2))
    state.update(change)
    with pytest.raises(ValueError):
        audit_published_state(state)


def test_duplicate_and_action_overrides_are_rejected() -> None:
    row = sample(1, action="FORWARD", left=0.3, right=0.1)
    with pytest.raises(ValueError, match="Duplicate"):
        audit_published_state(publication(row, row))
    changed = dict(row, applied_action="TURN_LEFT")
    with pytest.raises(ValueError, match="unchanged"):
        audit_published_state(publication(changed))
    changed = dict(row, action_overridden=True)
    with pytest.raises(ValueError, match="overwritten"):
        audit_published_state(publication(changed))
