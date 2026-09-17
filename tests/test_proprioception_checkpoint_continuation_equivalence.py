from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.proprioception_checkpoint_continuation_equivalence import (
    REPORT_SCHEMA,
    SCOPE,
    STATUS,
    audit_checkpoint_continuation_equivalence,
)


CONTRACT_PATH = Path("data/proprioception_checkpoint_continuation_equivalence_v01.json")


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text())


def test_exhaustive_checkpoint_continuation_equivalence_passes() -> None:
    report = audit_checkpoint_continuation_equivalence(_contract())

    assert report["schema"] == REPORT_SCHEMA
    assert report["status"] == STATUS
    assert report["scope"] == SCOPE
    assert report["passed"] is True
    assert report["sequence_count"] == 1364
    assert report["vibration_profile_count"] == 2
    assert report["checkpoint_case_count"] == 15472
    assert report["continuation_step_comparisons"] == 36712
    assert report["first_failure"] is None
    assert all(report["contract_gates"].values())
    assert all(report["continuation_gates"].values())


def test_checkpoint_boundary_remains_private_and_non_neural() -> None:
    report = audit_checkpoint_continuation_equivalence(_contract())

    assert report["checkpoint_is_private_state_only"] is True
    assert report["checkpoint_is_not_neural_input"] is True
    assert report["history_replay_into_neural_payload"] is False
    assert report["biological_memory_claimed"] is False


def test_runtime_and_science_promotion_remain_locked() -> None:
    report = audit_checkpoint_continuation_equivalence(_contract())

    assert report["systematic_type_mapping_exposed"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["runtime_gating_authorized"] is False
    assert report["neural_payload_promotion_authorized"] is False


def test_contract_fails_closed_if_checkpoint_coverage_is_weakened() -> None:
    payload = copy.deepcopy(_contract())
    payload["checkpoint_every_split_point"] = False

    report = audit_checkpoint_continuation_equivalence(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["checkpoint_every_split_point"] is False
    assert report["sequence_count"] == 0


def test_contract_fails_closed_if_exhaustive_depth_is_reduced() -> None:
    payload = copy.deepcopy(_contract())
    payload["exhaustive_max_sequence_length"] = 3

    report = audit_checkpoint_continuation_equivalence(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["max_sequence_length_exact"] is False
    assert report["checkpoint_case_count"] == 0


def test_contract_fails_closed_if_checkpoint_is_reclassified_as_neural_input() -> None:
    payload = copy.deepcopy(_contract())
    payload["interpretation"]["checkpoint_is_not_neural_input"] = False

    report = audit_checkpoint_continuation_equivalence(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["interpretation_exact"] is False
    assert report["checkpoint_is_not_neural_input"] is True


def test_contract_fails_closed_if_runtime_lock_is_opened() -> None:
    payload = copy.deepcopy(_contract())
    payload["hard_locks"]["runtime_gating_authorized"] = True

    report = audit_checkpoint_continuation_equivalence(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["hard_locks_exact"] is False
    assert report["runtime_gating_authorized"] is False
