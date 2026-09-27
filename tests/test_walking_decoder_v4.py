from __future__ import annotations

from neurofly.brain_runtime import (
    WALKING_STEERING_BASELINE_ALPHA,
    WALKING_STEERING_BASELINE_POLICY,
    WALKING_STEERING_THRESHOLD_HZ,
    _baseline_centered_steering_difference,
    _walking_action,
)


def test_persistent_dna02_side_offset_is_not_a_chronic_turn_command() -> None:
    signal, used_left, used_right, left_baseline, right_baseline = (
        _baseline_centered_steering_difference(
            steering_left_hz=60.0,
            steering_right_hz=0.0,
            left_baseline_hz=None,
            right_baseline_hz=None,
        )
    )

    assert signal == 0.0
    assert used_left == 60.0
    assert used_right == 0.0
    assert left_baseline == 60.0
    assert right_baseline == 0.0
    assert (
        _walking_action(
            steering_left_hz=60.0,
            steering_right_hz=0.0,
            steering_spikes=3,
            drive_spikes=2,
            steering_threshold_hz=WALKING_STEERING_THRESHOLD_HZ,
            steering_difference_hz=signal,
        )
        == "FORWARD"
    )


def test_transient_dna02_residual_preserves_ipsilateral_turning() -> None:
    left_signal, *_ = _baseline_centered_steering_difference(
        steering_left_hz=120.0,
        steering_right_hz=0.0,
        left_baseline_hz=60.0,
        right_baseline_hz=0.0,
    )
    right_signal, *_ = _baseline_centered_steering_difference(
        steering_left_hz=60.0,
        steering_right_hz=60.0,
        left_baseline_hz=60.0,
        right_baseline_hz=0.0,
    )

    assert left_signal == -60.0
    assert right_signal == 60.0
    assert (
        _walking_action(
            steering_left_hz=120.0,
            steering_right_hz=0.0,
            steering_spikes=6,
            drive_spikes=2,
            steering_threshold_hz=WALKING_STEERING_THRESHOLD_HZ,
            steering_difference_hz=left_signal,
        )
        == "TURN_LEFT"
    )
    assert (
        _walking_action(
            steering_left_hz=60.0,
            steering_right_hz=60.0,
            steering_spikes=6,
            drive_spikes=2,
            steering_threshold_hz=WALKING_STEERING_THRESHOLD_HZ,
            steering_difference_hz=right_signal,
        )
        == "TURN_RIGHT"
    )


def test_dna02_baseline_updates_slowly_without_using_environment_state() -> None:
    signal, used_left, used_right, next_left, next_right = (
        _baseline_centered_steering_difference(
            steering_left_hz=80.0,
            steering_right_hz=20.0,
            left_baseline_hz=60.0,
            right_baseline_hz=10.0,
        )
    )

    assert signal == -10.0
    assert used_left == 60.0
    assert used_right == 10.0
    assert abs(next_left - 60.4) < 1e-12
    assert abs(next_right - 10.2) < 1e-12
    assert WALKING_STEERING_BASELINE_ALPHA == 0.02
    assert WALKING_STEERING_BASELINE_POLICY == "bilateral-ewma-baseline-centered-v1"
