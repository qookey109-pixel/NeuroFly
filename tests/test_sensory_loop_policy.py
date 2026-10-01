from __future__ import annotations

from neurofly.brain_runtime import (
    SENSORY_LOOP_COOLDOWN,
    SENSORY_LOOP_POLICY,
    SENSORY_LOOP_REPEAT_THRESHOLD,
    SENSORY_LOOP_WINDOW,
    _sensory_familiarity_signature,
    _sensory_loop_should_trigger,
)
from neurofly.training import _public_goal_state


def test_sensory_familiarity_signature_uses_only_egocentric_sensory_channels() -> None:
    signature = _sensory_familiarity_signature(
        {
            "wall_distance_cells": {"left": 2.1, "front": 4.2, "right": 1.0},
            "visible_food": 17,
            "visible_enemies": 1,
            "nearest_enemy": {"bearing_degrees": -44.0, "distance_cells": 3.2},
        },
        {
            "food_left": 0.31,
            "food_right": 0.58,
            "food_front": 0.77,
            "food_back": 0.12,
            "danger_left": 0.15,
            "danger_right": 0.45,
            "danger_front": 0.62,
            "danger_back": 0.08,
        },
    )

    assert isinstance(signature, tuple)
    assert len(signature) == 15
    assert SENSORY_LOOP_POLICY == "egocentric-sensory-familiarity-aversive-v1"
    assert SENSORY_LOOP_WINDOW == 64


def test_sensory_loop_gate_requires_repeated_stage2_state_and_no_event_train() -> None:
    assert SENSORY_LOOP_REPEAT_THRESHOLD == 3
    assert SENSORY_LOOP_COOLDOWN == 6

    assert not _sensory_loop_should_trigger(
        repeat_count=2,
        cooldown=0,
        curriculum_stage=1,
        reinforcement="none",
    )
    assert _sensory_loop_should_trigger(
        repeat_count=2,
        cooldown=0,
        curriculum_stage=2,
        reinforcement="none",
    )
    assert not _sensory_loop_should_trigger(
        repeat_count=2,
        cooldown=1,
        curriculum_stage=2,
        reinforcement="none",
    )
    assert not _sensory_loop_should_trigger(
        repeat_count=2,
        cooldown=0,
        curriculum_stage=2,
        reinforcement="reward",
    )
    assert not _sensory_loop_should_trigger(
        repeat_count=1,
        cooldown=0,
        curriculum_stage=2,
        reinforcement="none",
    )


def test_public_receipt_preserves_v4_baseline_and_sensory_loop_evidence() -> None:
    state = {
        "episode": 9,
        "ticks": 1,
        "fly": {"x": 1, "y": 1, "dir": "RIGHT"},
        "enemies": [{"x": 5, "y": 5}],
        "power_ticks": 0,
        "last_action": "FORWARD",
        "last_reward": 0.0,
        "episode_reward": 0.0,
        "cumulative_reward": 0.0,
        "episode_food": 0,
        "total_food": 0,
        "food_left": 10,
        "total_deaths": 0,
        "total_clears": 2,
        "last_event": None,
        "survival_seconds": 1.0,
        "reinforcement": "none",
        "demo_action": "FORWARD",
        "brain": {
            "backend": "malecns",
            "telemetry": {
                "brain_ms": 50.0,
                "total_spikes": 100,
                "motor_decoder": "neurofly-walking-decoder-v4",
                "steering_type": "DNa02",
                "walking_drive_type": "DNb05",
                "forward_type": "DNb05",
                "left_hz": 20.0,
                "right_hz": 10.0,
                "difference_hz": -10.0,
                "raw_difference_hz": -10.0,
                "decoder_difference_hz": 4.0,
                "steering_left_baseline_hz": 18.0,
                "steering_right_baseline_hz": 12.0,
                "steering_baseline_policy": "bilateral-ewma-baseline-centered-v1",
                "steering_baseline_alpha": 0.02,
                "walking_drive_hz": 8.0,
                "walking_drive_left_hz": 7.0,
                "walking_drive_right_hz": 9.0,
                "walking_drive_spikes": 2,
                "steering_threshold_hz": 30.0,
                "forward_hz": 8.0,
                "forward_left_hz": 7.0,
                "forward_right_hz": 9.0,
                "steering_spikes": 3,
                "forward_spikes": 2,
                "walking_spikes": 5,
                "dnpe017_gate_used": False,
                "sensory_loop_policy": SENSORY_LOOP_POLICY,
                "sensory_loop_triggered": True,
                "sensory_loop_repeat_count": 3,
                "sensory_loop_window": SENSORY_LOOP_WINDOW,
                "sensory_loop_repeat_threshold": SENSORY_LOOP_REPEAT_THRESHOLD,
                "sensory_loop_cooldown_remaining": SENSORY_LOOP_COOLDOWN,
                "sensory_loop_direction_command": False,
            },
        },
    }

    public = _public_goal_state(state)
    telemetry = public["brain"]["telemetry"]

    assert telemetry["raw_difference_hz"] == -10.0
    assert telemetry["decoder_difference_hz"] == 4.0
    assert telemetry["steering_left_baseline_hz"] == 18.0
    assert telemetry["steering_right_baseline_hz"] == 12.0
    assert telemetry["sensory_loop_policy"] == SENSORY_LOOP_POLICY
    assert telemetry["sensory_loop_triggered"] is True
    assert telemetry["sensory_loop_direction_command"] is False
