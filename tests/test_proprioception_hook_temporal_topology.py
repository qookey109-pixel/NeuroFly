from __future__ import annotations

import copy

import pytest

from neurofly.proprioception import feco_motion_proprioception
from neurofly.proprioception_temporal_observability import ProprioceptionTemporalRecorder
from neurofly.proprioception_temporal_topology import (
    PROPRIOCEPTION_HOOK_TOPOLOGY_SCHEMA,
    analyze_proprioception_hook_temporal_topology,
)


def _history(deltas: list[float]) -> dict:
    recorder = ProprioceptionTemporalRecorder()
    for delta in deltas:
        recorder.observe_neural_handoff(feco_motion_proprioception(joint_delta=delta))
    return recorder.snapshot()


def test_hook_topology_describes_alternation_and_idle_gaps_without_biological_time() -> None:
    topology = analyze_proprioception_hook_temporal_topology(
        _history([0.0, 1.0, 0.6, 0.0, -0.5, -0.25, 0.0, 0.4])
    )

    assert topology["schema"] == PROPRIOCEPTION_HOOK_TOPOLOGY_SCHEMA
    assert topology["source"] == "verified-neural-handoff-receptor-domain"
    assert topology["human_only"] is True
    assert topology["timebase"] == "decision-index-only"
    assert topology["sample_count"] == 8
    assert topology["directional_active_sample_count"] == 5
    assert topology["idle_sample_count"] == 3
    assert topology["directional_event_count"] == 3
    assert topology["event_transition_count"] == 2
    assert topology["alternating_event_transition_count"] == 2
    assert topology["direct_reversal_count"] == 0
    assert topology["reversal_after_idle_count"] == 2
    assert topology["same_direction_reentry_count"] == 0
    assert topology["observed_idle_gap_decisions_total"] == 2
    assert topology["observed_idle_gap_decisions_max"] == 1

    first, second, third = topology["directional_events"]
    assert first == {
        "direction": "hook_extension",
        "observed_start_sequence": 2,
        "observed_end_sequence": 3,
        "observed_duration_decisions": 2,
        "peak_level": 1.0,
        "left_censored": False,
        "right_censored": False,
    }
    assert second["direction"] == "hook_flexion"
    assert second["observed_start_sequence"] == 5
    assert second["observed_end_sequence"] == 6
    assert third["direction"] == "hook_extension"
    assert third["observed_start_sequence"] == 8
    assert third["right_censored"] is True

    assert topology["event_transitions"][0] == {
        "from_direction": "hook_extension",
        "to_direction": "hook_flexion",
        "from_end_sequence": 3,
        "to_start_sequence": 5,
        "idle_gap_decisions": 1,
        "alternating": True,
        "direct_reversal": False,
        "reversal_after_idle": True,
        "same_direction_reentry": False,
    }

    assert topology["milliseconds_inferred"] is False
    assert topology["step_cycle_phase_resolved"] is False
    assert topology["inhibitory_lead_time_resolved"] is False
    assert topology["biological_identity_resolved"] is False
    assert "SNpp39" not in str(topology)
    assert "SNpp41" not in str(topology)


def test_hook_topology_distinguishes_direct_reversal_from_same_direction_reentry() -> None:
    topology = analyze_proprioception_hook_temporal_topology(
        _history([1.0, -1.0, 0.0, -0.5, 0.0, -0.2])
    )

    assert topology["directional_event_count"] == 4
    assert topology["event_transition_count"] == 3
    assert topology["alternating_event_transition_count"] == 1
    assert topology["direct_reversal_count"] == 1
    assert topology["reversal_after_idle_count"] == 0
    assert topology["same_direction_reentry_count"] == 2
    assert topology["event_transitions"][0]["idle_gap_decisions"] == 0
    assert topology["event_transitions"][0]["direct_reversal"] is True
    assert topology["event_transitions"][1]["same_direction_reentry"] is True


def test_hook_topology_preserves_bounded_window_censoring() -> None:
    topology = analyze_proprioception_hook_temporal_topology(_history([1.0] * 40))

    assert topology["sample_count"] == 36
    assert topology["first_retained_sequence"] == 5
    assert topology["last_retained_sequence"] == 40
    assert topology["window_left_censoring_possible"] is True
    assert topology["directional_event_count"] == 1
    event = topology["directional_events"][0]
    assert event["observed_start_sequence"] == 5
    assert event["observed_end_sequence"] == 40
    assert event["observed_duration_decisions"] == 36
    assert event["left_censored"] is True
    assert event["right_censored"] is True


def test_hook_topology_fails_closed_on_mutual_exclusion_violation() -> None:
    history = _history([0.5])
    contaminated = copy.deepcopy(history)
    contaminated["samples"][0]["channels"]["hook_flexion"] = 0.5

    with pytest.raises(ValueError, match="mutually exclusive"):
        analyze_proprioception_hook_temporal_topology(contaminated)


def test_hook_topology_fails_closed_when_club_motion_does_not_cover_hook_magnitude() -> None:
    history = _history([0.8])
    contaminated = copy.deepcopy(history)
    contaminated["samples"][0]["channels"]["club_motion"] = 0.2

    with pytest.raises(ValueError, match="club motion"):
        analyze_proprioception_hook_temporal_topology(contaminated)


def test_hook_topology_inherits_strict_history_field_firewall_and_keeps_locks_closed() -> None:
    history = _history([0.0, -0.7])
    contaminated = copy.deepcopy(history)
    contaminated["samples"][0]["reward"] = 1.0

    with pytest.raises(ValueError, match="Unexpected temporal sample fields"):
        analyze_proprioception_hook_temporal_topology(contaminated)

    topology = analyze_proprioception_hook_temporal_topology(history)
    assert topology["engineering_mutual_exclusion_verified"] is True
    assert topology["engineering_club_motion_coverage_verified"] is True
    assert topology["motor_command_used"] is False
    assert topology["reward_used"] is False
    assert topology["world_state_used"] is False
    assert topology["private_body_state_used"] is False
    assert topology["systematic_type_mapping_exposed"] is False
    assert topology["current_calibration_authorized"] is False
    assert topology["stimulation_enabled"] is False
    assert topology["runtime_gating_authorized"] is False
    assert topology["neural_payload_eligible"] is False
    assert topology["analysis_persistence_enabled"] is False
