from __future__ import annotations

from neurofly.behavior_evidence import summarize_behavior


def test_food_cue_evidence_keeps_raw_actions_separate_from_applied_actions() -> None:
    observations = [
        {
            "fly_x": 1,
            "fly_y": 1,
            "food_odor_left": 0.8,
            "food_odor_right": 0.2,
            "raw_brain_action": "TURN_LEFT",
            "applied_action": "TURN_LEFT",
            "action_overridden": False,
        },
        {
            "fly_x": 1,
            "fly_y": 1,
            "food_odor_left": 0.2,
            "food_odor_right": 0.8,
            "raw_brain_action": "TURN_LEFT",
            "applied_action": "FORWARD",
            "action_overridden": True,
            "override_reason": "anti_stall_followup_forward",
        },
        {
            "fly_x": 2,
            "fly_y": 1,
            "food_odor_left": 0.2,
            "food_odor_right": 0.8,
            "raw_brain_action": "TURN_RIGHT",
            "applied_action": "TURN_RIGHT",
            "action_overridden": False,
        },
        {
            "fly_x": 2,
            "fly_y": 2,
            "food_odor_left": 0.5,
            "food_odor_right": 0.5,
            "raw_brain_action": "HOLD",
            "applied_action": "FORWARD",
            "action_overridden": True,
            "override_reason": "anti_stall_hold_forward",
        },
        {
            "fly_x": 3,
            "fly_y": 2,
            "food_odor_left": 0.7,
            "food_odor_right": 0.1,
            "raw_brain_action": "FORWARD",
            "applied_action": "FORWARD",
            "action_overridden": False,
        },
    ]

    summary = summarize_behavior(
        observations,
        navigable_cells=10,
        food_before=0,
        food_after=0,
        clears_before=0,
        clears_after=0,
        deaths_before=0,
        deaths_after=0,
    )

    assert summary["food_cue_side_counts"] == {
        "LEFT": 2,
        "RIGHT": 2,
        "BALANCED": 1,
    }
    assert summary["raw_action_by_food_cue"]["LEFT"] == {
        "TURN_LEFT": 1,
        "TURN_RIGHT": 0,
        "FORWARD": 1,
        "HOLD": 0,
    }
    assert summary["raw_action_by_food_cue"]["RIGHT"] == {
        "TURN_LEFT": 1,
        "TURN_RIGHT": 1,
        "FORWARD": 0,
        "HOLD": 0,
    }
    assert summary["raw_food_directional_turn_trials"] == 3
    assert summary["raw_food_directional_turn_aligned"] == 2
    assert summary["raw_food_directional_turn_alignment_rate"] == 0.666667


def test_food_cue_alignment_rate_is_none_when_brain_never_turns() -> None:
    observations = [
        {
            "fly_x": 1,
            "fly_y": 1,
            "food_odor_left": 0.9,
            "food_odor_right": 0.1,
            "raw_brain_action": "FORWARD",
            "applied_action": "FORWARD",
            "action_overridden": False,
        }
    ]

    summary = summarize_behavior(
        observations,
        navigable_cells=1,
        food_before=0,
        food_after=0,
        clears_before=0,
        clears_after=0,
        deaths_before=0,
        deaths_after=0,
    )

    assert summary["raw_food_directional_turn_trials"] == 0
    assert summary["raw_food_directional_turn_aligned"] == 0
    assert summary["raw_food_directional_turn_alignment_rate"] is None
