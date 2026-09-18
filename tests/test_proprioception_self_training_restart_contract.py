from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.proprioception_self_training_restart_contract import (
    REPORT_SCHEMA,
    STATUS,
    audit_self_training_restart_contract,
)


CONTRACT = Path("data/proprioception_self_training_restart_contract_v01.json")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text())


def test_self_training_restart_orchestration_contract_passes() -> None:
    report = audit_self_training_restart_contract(_contract())

    diagnostics = json.dumps(report, indent=2, sort_keys=True)
    assert report["schema"] == REPORT_SCHEMA, diagnostics
    assert report["status"] == STATUS, diagnostics
    assert report["passed"] is True, diagnostics
    assert report["coverage"] == {
        "sequence_count": 92,
        "restart_cases": 360,
        "post_restart_step_comparisons": 556,
    }, diagnostics
    assert all(report["contract_gates"].values()), diagnostics
    assert all(report["coverage_gates"].values()), diagnostics
    assert all(report["invariants"].values()), diagnostics


def test_report_does_not_overclaim_real_malecns_restart() -> None:
    report = audit_self_training_restart_contract(_contract())

    assert report["actual_malecns_process_restart_executed"] is False
    assert report["malecns_brain_checkpoint_equivalence_proven"] is False
    assert report["biological_restart_memory_claimed"] is False
    assert report["production_orchestration_contract_only"] is True


def test_runtime_and_science_locks_remain_closed() -> None:
    report = audit_self_training_restart_contract(_contract())

    assert report["systematic_type_mapping_exposed"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["runtime_gating_authorized"] is False
    assert report["neural_payload_promotion_authorized"] is False


def test_contract_fails_closed_if_malecns_restart_is_falsely_claimed() -> None:
    payload = copy.deepcopy(_contract())
    payload["proof_limitations"]["actual_malecns_process_restart_executed"] = True

    report = audit_self_training_restart_contract(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["proof_limitations_exact"] is False


def test_contract_fails_closed_if_temporal_process_locality_is_weakened() -> None:
    payload = copy.deepcopy(_contract())
    payload["required_invariants"]["temporal_history_is_process_local_after_restart"] = False

    report = audit_self_training_restart_contract(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["required_invariants_exact"] is False


def test_contract_fails_closed_if_runtime_lock_is_opened() -> None:
    payload = copy.deepcopy(_contract())
    payload["hard_locks"]["runtime_transduction_enabled"] = True

    report = audit_self_training_restart_contract(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["hard_locks_exact"] is False
