from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.proprioception_turn_laterality_invariance import (
    REPORT_SCHEMA,
    SCOPE,
    STATUS,
    audit_turn_laterality_invariance,
)


CONTRACT_PATH = Path("data/proprioception_turn_laterality_invariance_v01.json")


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text())


def test_exhaustive_turn_laterality_invariance_passes() -> None:
    report = audit_turn_laterality_invariance(_contract())

    assert report["schema"] == REPORT_SCHEMA
    assert report["status"] == STATUS
    assert report["scope"] == SCOPE
    assert report["passed"] is True
    assert report["sequence_count"] == 1364
    assert report["vibration_profile_count"] == 2
    assert report["trajectory_case_count"] == 2728
    assert report["receptor_step_comparisons"] == 12744
    assert report["first_failure"] is None
    assert all(report["contract_gates"].values())
    assert all(report["invariance_gates"].values())


def test_gate_allows_reafference_but_forbids_turn_laterality_cue() -> None:
    report = audit_turn_laterality_invariance(_contract())

    assert report["motor_class_reafference_allowed"] is True
    assert report["turn_laterality_privileged_cue_forbidden"] is True
    assert report["six_leg_laterality_modeled"] is False
    assert report["biological_laterality_claimed"] is False


def test_gate_keeps_science_and_runtime_promotion_locked() -> None:
    report = audit_turn_laterality_invariance(_contract())

    assert report["systematic_type_mapping_exposed"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["runtime_gating_authorized"] is False
    assert report["neural_payload_promotion_authorized"] is False


def test_contract_fails_closed_if_turn_swap_is_weakened() -> None:
    payload = copy.deepcopy(_contract())
    payload["laterality_swap"]["TURN_LEFT"] = "TURN_LEFT"

    report = audit_turn_laterality_invariance(payload)
    assert report["passed"] is False
    assert report["status"] == "FAIL"
    assert report["contract_gates"]["laterality_swap_exact"] is False
    assert report["sequence_count"] == 0


def test_contract_fails_closed_if_exhaustive_depth_is_reduced() -> None:
    payload = copy.deepcopy(_contract())
    payload["exhaustive_max_sequence_length"] = 2

    report = audit_turn_laterality_invariance(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["max_sequence_length_exact"] is False
    assert report["sequence_count"] == 0


def test_contract_fails_closed_if_runtime_lock_is_opened() -> None:
    payload = copy.deepcopy(_contract())
    payload["hard_locks"]["runtime_transduction_enabled"] = True

    report = audit_turn_laterality_invariance(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["hard_locks_exact"] is False
    assert report["runtime_transduction_enabled"] is False


def test_contract_fails_closed_if_six_leg_laterality_is_claimed() -> None:
    payload = copy.deepcopy(_contract())
    payload["interpretation"]["six_leg_laterality_modeled"] = True

    report = audit_turn_laterality_invariance(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["interpretation_exact"] is False
    assert report["six_leg_laterality_modeled"] is False
