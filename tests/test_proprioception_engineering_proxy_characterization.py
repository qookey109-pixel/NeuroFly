from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.proprioception_engineering_proxy_characterization import (
    REPORT_SCHEMA,
    SCOPE,
    STATUS,
    audit_characterization,
)


CONTRACT_PATH = Path("data/proprioception_engineering_proxy_characterization_v01.json")


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text())


def test_frozen_engineering_proxy_characterization_passes() -> None:
    report = audit_characterization(_contract())

    assert report["schema"] == REPORT_SCHEMA
    assert report["status"] == STATUS
    assert report["scope"] == SCOPE
    assert report["passed"] is True
    assert report["sample_count"] == 55
    assert all(report["contract_gates"].values())
    assert all(report["characterization_gates"].values())


def test_characterization_does_not_promote_biology_or_runtime() -> None:
    report = audit_characterization(_contract())

    assert report["engineering_proxy_only"] is True
    assert report["human_diagnostic_or_ci_only"] is True
    assert report["biological_current_calibrated"] is False
    assert report["biological_latency_calibrated"] is False
    assert report["systematic_type_identity_resolved"] is False
    assert report["direct_crosswalk_found"] is False
    assert report["polarity_resolved"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["runtime_gating_authorized"] is False
    assert report["systematic_type_mapping_exposed"] is False
    assert report["neural_payload_eligible"] is False
    assert report["promotion_ready"] is False


def test_contract_fails_closed_if_upstream_boundary_is_changed() -> None:
    payload = copy.deepcopy(_contract())
    payload["upstream_boundary"]["state"] = "RESOLVED"

    report = audit_characterization(payload)
    assert report["passed"] is False
    assert report["status"] == "FAIL"
    assert report["contract_gates"]["upstream_state_frozen"] is False


def test_contract_fails_closed_if_a_runtime_lock_is_opened() -> None:
    payload = copy.deepcopy(_contract())
    payload["hard_locks"]["runtime_transduction_enabled"] = True

    report = audit_characterization(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["hard_locks_exact"] is False
    assert report["runtime_transduction_enabled"] is False


def test_contract_fails_closed_if_sweep_is_weakened() -> None:
    payload = copy.deepcopy(_contract())
    payload["joint_delta_sweep"] = [-1.0, 0.0, 1.0]

    report = audit_characterization(payload)
    assert report["passed"] is False
    assert report["sample_count"] == 0
    assert report["contract_gates"]["joint_delta_sweep_exact"] is False
    assert report["characterization_gates"]["sample_contract_valid"] is False


def test_contract_fails_closed_if_biological_calibration_is_claimed() -> None:
    payload = copy.deepcopy(_contract())
    payload["biological_claims"]["biological_current_calibrated"] = True

    report = audit_characterization(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["biological_claims_locked"] is False
