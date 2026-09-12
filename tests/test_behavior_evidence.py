from __future__ import annotations

from neurofly.behavior_evidence import BEHAVIOR_EVIDENCE_SCHEMA, summarize_behavior


def test_behavior_summary_separates_raw_actions_from_engineered_overrides() -> None:
    observations = [
        {
            "fly_x": 1,
            "fly_y": 1,
            "raw_brain_action": "HOLD",
            "applied_action": "HOLD",
            "action_overridden": False,
            "override_reason": None,
            "curriculum_stage": 1,
        },
        {
            "fly_x": 2,
            "fly_y": 1,
            "raw_brain_action": "HOLD",
            "applied_action": "FORWARD",
            "action_overridden": True,
            "override_reason": "anti_stall_hold_forward",
            "curriculum_stage": 1,
        },
        {
            "fly_x": 2,
            "fly_y": 1,
            "raw_brain_action": "TURN_RIGHT",
            "applied_action": "TURN_RIGHT",
            "action_overridden": False,
            "override_reason": None,
            "curriculum_stage": 1,
        },
        {
            "fly_x": 2,
            "fly_y": 2,
            "raw_brain_action": "TURN_LEFT",
            "applied_action": "FORWARD",
            "action_overridden": True,
            "override_reason": "anti_stall_followup_forward",
            "curriculum_stage": 2,
        },
    ]

    summary = summarize_behavior(
        observations,
        navigable_cells=12,
        food_before=7,
        food_after=9,
        clears_before=1,
        clears_after=2,
        deaths_before=3,
        deaths_after=4,
    )

    assert summary["schema"] == BEHAVIOR_EVIDENCE_SCHEMA
    assert summary["decisions"] == 4
    assert summary["batch_food"] == 2
    assert summary["food_per_100_decisions"] == 50.0
    assert summary["batch_clears"] == 1
    assert summary["batch_deaths"] == 1
    assert summary["unique_cells"] == 3
    assert summary["navigable_cells"] == 12
    assert summary["coverage_ratio"] == 0.25
    assert summary["raw_action_histogram"] == {
        "TURN_LEFT": 1,
        "TURN_RIGHT": 1,
        "FORWARD": 0,
        "HOLD": 2,
    }
    assert summary["applied_action_histogram"] == {
        "TURN_LEFT": 0,
        "TURN_RIGHT": 1,
        "FORWARD": 2,
        "HOLD": 1,
    }
    assert summary["overrides"] == 2
    assert summary["override_rate"] == 0.5
    assert summary["override_reasons"] == {
        "anti_stall_followup_forward": 1,
        "anti_stall_hold_forward": 1,
    }
    assert summary["curriculum_stage_start"] == 1
    assert summary["curriculum_stage_end"] == 2


def test_behavior_summary_clamps_counter_resets_to_zero() -> None:
    observations = [
        {
            "fly_x": 1,
            "fly_y": 1,
            "raw_brain_action": "FORWARD",
            "applied_action": "FORWARD",
            "action_overridden": False,
        }
    ]

    summary = summarize_behavior(
        observations,
        navigable_cells=1,
        food_before=10,
        food_after=2,
        clears_before=5,
        clears_after=1,
        deaths_before=8,
        deaths_after=3,
    )

    assert summary["batch_food"] == 0
    assert summary["batch_clears"] == 0
    assert summary["batch_deaths"] == 0
    assert summary["coverage_ratio"] == 1.0
