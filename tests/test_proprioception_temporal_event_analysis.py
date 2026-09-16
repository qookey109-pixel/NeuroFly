from __future__ import annotations

import copy

import pytest

from neurofly.proprioception import feco_motion_proprioception
from neurofly.proprioception_temporal_analysis import (
    PROPRIOCEPTION_TEMPORAL_ANALYSIS_SCHEMA,
    analyze_proprioception_temporal_history,
)
from neurofly.proprioception_temporal_observability import ProprioceptionTemporalRecorder


def _history(deltas: list[float]) -> dict:
    recorder = ProprioceptionTemporalRecorder()
    for delta in deltas:
        recorder.observe_neural_handoff(feco_motion_proprioception(joint_delta=delta))
    return recorder.snapshot()


def test_event_analysis_uses_decision_index_only_and_keeps_all_runtime_locks_closed() -> None:
    analysis = analyze_proprioception_temporal_history(
        _history([0.0, 1.0, 1.0, 0.0, -0.5, 0.0])
    )

    assert analysis["schema"] == PROPRIOCEPTION_TEMPORAL_ANALYSIS_SCHEMA
    assert analysis["source"] == "verified-neural-handoff-receptor-domain"
    assert analysis["human_only"] is True
    assert analysis["timebase"] == "decision-index-only"
    assert analysis["sample_count"] == 6
    assert analysis["milliseconds_inferred"] is False
    assert analysis["step_cycle_phase_resolved"] is False
    assert analysis["inhibitory_lead_time_resolved"] is False
    assert analysis["motor_command_used"] is False
    assert analysis["reward_used"] is False
    assert analysis["world_state_used"] is False
    assert analysis["private_body_state_used"] is False
    assert analysis["systematic_type_mapping_exposed"] is False
    assert analysis["current_calibration_authorized"] is False
    assert analysis["stimulation_enabled"] is False
    assert analysis["runtime_gating_authorized"] is False
    assert analysis["neural_payload_eligible"] is False
    assert analysis["analysis_persistence_enabled"] is False


def test_extension_and_flexion_events_are_descriptive_not_identity_labels() -> None:
    analysis = analyze_proprioception_temporal_history(
        _history([0.0, 1.0, 0.6, 0.0, -0.5, 0.0])
    )

    extension = analysis["channels"]["hook_extension"]
    assert extension["active_sample_count"] == 2
    assert extension["rising_transition_count_within_window"] == 1
    assert extension["falling_transition_count_within_window"] == 1
    assert extension["event_count_observed"] == 1
    assert extension["events"] == [
        {
            "observed_start_sequence": 2,
            "observed_end_sequence": 3,
            "observed_duration_decisions": 2,
            "peak_level": 1.0,
            "left_censored": False,
            "right_censored": False,
        }
    ]

    flexion = analysis["channels"]["hook_flexion"]
    assert flexion["active_sample_count"] == 1
    assert flexion["rising_transition_count_within_window"] == 1
    assert flexion["falling_transition_count_within_window"] == 1
    assert flexion["event_count_observed"] == 1
    assert flexion["events"][0]["observed_start_sequence"] == 5
    assert "SNpp39" not in str(analysis)
    assert "SNpp41" not in str(analysis)


def test_retained_window_censors_events_instead_of_inventing_true_onset_or_offset() -> None:
    analysis = analyze_proprioception_temporal_history(_history([1.0] * 40))

    assert analysis["sample_count"] == 36
    assert analysis["first_retained_sequence"] == 5
    assert analysis["last_retained_sequence"] == 40
    assert analysis["window_left_censoring_possible"] is True

    event = analysis["channels"]["hook_extension"]["events"][0]
    assert event["observed_start_sequence"] == 5
    assert event["observed_end_sequence"] == 40
    assert event["observed_duration_decisions"] == 36
    assert event["left_censored"] is True
    assert event["right_censored"] is True
    assert analysis["channels"]["hook_extension"]["rising_transition_count_within_window"] == 0
    assert analysis["channels"]["hook_extension"]["falling_transition_count_within_window"] == 0


def test_first_sequence_one_can_still_be_left_censored_because_pre_session_state_is_unknown() -> None:
    analysis = analyze_proprioception_temporal_history(_history([0.8, 0.0]))

    assert analysis["window_left_censoring_possible"] is False
    event = analysis["channels"]["hook_extension"]["events"][0]
    assert event["left_censored"] is True
    assert event["right_censored"] is False


def test_analysis_rejects_privileged_or_unreviewed_fields_in_history() -> None:
    history = _history([0.0, 1.0])
    contaminated = copy.deepcopy(history)
    contaminated["samples"][0]["motor_command"] = "FORWARD"

    with pytest.raises(ValueError, match="Unexpected temporal sample fields"):
        analyze_proprioception_temporal_history(contaminated)

    contaminated = copy.deepcopy(history)
    contaminated["world_state"] = {"x": 1, "y": 2}
    with pytest.raises(ValueError, match="Unexpected temporal history fields"):
        analyze_proprioception_temporal_history(contaminated)


def test_analysis_fails_closed_if_any_history_lock_opens() -> None:
    history = _history([0.0, -1.0])
    history["neural_payload_eligible"] = True

    with pytest.raises(ValueError, match="lock opened"):
        analyze_proprioception_temporal_history(history)
