from __future__ import annotations

import json

import pytest

from neurofly.proprioception import feco_motion_proprioception
from neurofly.proprioception_temporal_observability import (
    MAX_PROPRIOCEPTION_HISTORY_CAPACITY,
    PROPRIOCEPTION_TEMPORAL_SCHEMA,
    PROPRIOCEPTION_TEMPORAL_SOURCE,
    ProprioceptionTemporalRecorder,
    freeze_proprioception_handoff_sample,
)


def test_freezes_exact_receptor_domain_channels_without_systematic_mapping() -> None:
    payload = feco_motion_proprioception(joint_delta=-0.4, vibration=0.25)

    sample = freeze_proprioception_handoff_sample(payload, sequence=1)

    assert sample == {
        "sequence": 1,
        "source": PROPRIOCEPTION_TEMPORAL_SOURCE,
        "model": "neurofly-feco-motion-proxy-v0.1",
        "encoding": "virtual-joint-motion-only-proxy",
        "channels": {
            "hook_extension": 0.0,
            "hook_flexion": 0.4,
            "club_motion": 0.4,
            "club_vibration": 0.25,
        },
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "systematic_type_mapping_exposed": False,
        "current_calibration_authorized": False,
        "neural_payload_eligible": False,
    }


def test_recorder_keeps_only_latest_36_handoffs_in_order() -> None:
    recorder = ProprioceptionTemporalRecorder()

    for index in range(40):
        recorder.observe_neural_handoff(
            feco_motion_proprioception(joint_delta=(index % 10) / 10.0)
        )

    snapshot = recorder.snapshot()

    assert snapshot["schema"] == PROPRIOCEPTION_TEMPORAL_SCHEMA
    assert snapshot["capacity"] == 36
    assert snapshot["sample_count"] == 36
    assert [item["sequence"] for item in snapshot["samples"]] == list(range(5, 41))
    assert snapshot["samples"][-1]["channels"]["hook_extension"] == 0.9


def test_snapshot_is_human_only_nonpersistent_and_non_neural() -> None:
    recorder = ProprioceptionTemporalRecorder(capacity=2)
    recorder.observe_neural_handoff(feco_motion_proprioception(joint_delta=1.0))

    snapshot = recorder.snapshot()

    assert snapshot["human_only"] is True
    assert snapshot["history_persistence_enabled"] is False
    assert snapshot["systematic_type_mapping_exposed"] is False
    assert snapshot["current_calibration_authorized"] is False
    assert snapshot["stimulation_enabled"] is False
    assert snapshot["runtime_transduction_enabled"] is False
    assert snapshot["neural_payload_eligible"] is False

    encoded = json.dumps(snapshot, sort_keys=True)
    for forbidden in (
        "SNpp39",
        "SNpp41",
        "systematic_type_binding",
        "candidate_function",
        "joint_position",
        "joint_phase",
        "joint_delta",
        "motor_execution",
        "world_velocity",
        "world_displacement",
        "desired_action",
        "reward",
    ):
        assert forbidden not in encoded


def test_recorder_is_copy_safe() -> None:
    recorder = ProprioceptionTemporalRecorder(capacity=2)
    payload = feco_motion_proprioception(joint_delta=0.5)

    returned = recorder.observe_neural_handoff(payload)
    returned["channels"]["hook_extension"] = 0.0
    payload["channels"]["hook_extension"] = 0.0

    snapshot = recorder.snapshot()
    assert snapshot["samples"][0]["channels"]["hook_extension"] == 0.5

    snapshot["samples"][0]["channels"]["hook_extension"] = 0.0
    assert recorder.snapshot()["samples"][0]["channels"]["hook_extension"] == 0.5


def test_failed_sample_does_not_advance_sequence() -> None:
    recorder = ProprioceptionTemporalRecorder(capacity=2)
    invalid = feco_motion_proprioception(joint_delta=0.5)
    invalid["systematic_type_mapping"] = {"hook_extension": "SNpp39"}

    with pytest.raises(ValueError, match="Unexpected proprioception handoff payload fields"):
        recorder.observe_neural_handoff(invalid)

    sample = recorder.observe_neural_handoff(feco_motion_proprioception())
    assert sample["sequence"] == 1


def test_rejects_open_runtime_or_stimulation_locks() -> None:
    for key in ("stimulation_enabled", "runtime_transduction_enabled"):
        payload = feco_motion_proprioception()
        payload[key] = True
        with pytest.raises(ValueError):
            freeze_proprioception_handoff_sample(payload, sequence=1)


def test_capacity_is_strictly_bounded() -> None:
    assert MAX_PROPRIOCEPTION_HISTORY_CAPACITY == 36

    for invalid in (0, 37, 1000, True, 1.5):
        with pytest.raises(ValueError):
            ProprioceptionTemporalRecorder(capacity=invalid)  # type: ignore[arg-type]


def test_reset_only_clears_diagnostic_history() -> None:
    recorder = ProprioceptionTemporalRecorder(capacity=2)
    recorder.observe_neural_handoff(feco_motion_proprioception(joint_delta=1.0))
    recorder.reset()

    snapshot = recorder.snapshot()
    assert snapshot["sample_count"] == 0
    assert snapshot["samples"] == []
    assert recorder.observe_neural_handoff(feco_motion_proprioception())["sequence"] == 1
