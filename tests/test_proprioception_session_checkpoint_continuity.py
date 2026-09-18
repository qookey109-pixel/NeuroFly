from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.proprioception_session_checkpoint_continuity import (
    REPORT_SCHEMA,
    STATUS,
    audit_session_checkpoint_continuity,
)


CONTRACT = Path("data/proprioception_session_checkpoint_continuity_v01.json")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text())


def test_frozen_session_checkpoint_continuity_passes() -> None:
    report = audit_session_checkpoint_continuity(_contract())

    assert report["schema"] == REPORT_SCHEMA
    assert report["status"] == STATUS
    assert report["passed"] is True
    assert report["coverage"] == {
        "sequence_count": 92,
        "checkpoint_restore_cases": 360,
        "continuation_handoff_comparisons": 556,
    }
    assert all(report["contract_gates"].values())
    assert all(report["coverage_gates"].values())
    assert all(report["invariants"].values())


def test_gate_keeps_temporal_history_and_runtime_promotion_locked() -> None:
    report = audit_session_checkpoint_continuity(_contract())

    assert report["temporal_history_persistence_enabled"] is False
    assert report["systematic_type_mapping_exposed"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["runtime_gating_authorized"] is False
    assert report["neural_payload_promotion_authorized"] is False


def test_contract_fails_closed_if_history_persistence_is_enabled() -> None:
    payload = copy.deepcopy(_contract())
    payload["required_invariants"]["temporal_history_not_persisted"] = False

    report = audit_session_checkpoint_continuity(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["required_invariants_exact"] is False


def test_contract_fails_closed_if_runtime_lock_is_opened() -> None:
    payload = copy.deepcopy(_contract())
    payload["hard_locks"]["runtime_gating_authorized"] = True

    report = audit_session_checkpoint_continuity(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["hard_locks_exact"] is False


def test_contract_fails_closed_if_exhaustive_depth_is_weakened() -> None:
    payload = copy.deepcopy(_contract())
    payload["exhaustive_max_length"] = 2

    report = audit_session_checkpoint_continuity(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["exhaustive_max_length_exact"] is False
    assert report["coverage_gates"]["sequence_count_exact"] is False


def test_contract_fails_closed_if_upstream_head_moves() -> None:
    payload = copy.deepcopy(_contract())
    payload["upstream"]["head_sha"] = "0" * 40

    report = audit_session_checkpoint_continuity(payload)
    assert report["passed"] is False
    assert report["contract_gates"]["upstream_head_exact"] is False
