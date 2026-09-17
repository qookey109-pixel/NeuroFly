from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.proprioception_polarity_boundary_freeze import audit_polarity_boundary


DATA = Path("data/proprioception_polarity_boundary_freeze_v01.json")


def _payload() -> dict:
    return json.loads(DATA.read_text())


def test_frozen_boundary_contract_passes() -> None:
    report = audit_polarity_boundary(_payload())
    assert report["passed"] is True
    assert report["status"] == "FROZEN_PENDING_DIRECT_TYPE_LEVEL_EVIDENCE"
    assert report["best_supported_mapping"] == {
        "SNpp39": "extension",
        "SNpp41": "flexion",
    }
    assert report["mapping_strength"] == "PHYSIOLOGY_SUPPORTED_INFERENCE"
    assert report["polarity_resolved"] is False
    assert report["promotion_ready"] is False


def test_opening_polarity_lock_fails_closed() -> None:
    payload = copy.deepcopy(_payload())
    payload["polarity_resolved"] = True
    report = audit_polarity_boundary(payload)
    assert report["passed"] is False
    assert report["status"] == "FAIL"
    assert report["gates"]["all_runtime_and_promotion_locks_closed"] is False


def test_false_driver_to_type_bridge_fails_closed() -> None:
    payload = copy.deepcopy(_payload())
    payload["crosswalk_audit"]["functional_driver_to_snpp41_exact"] = True
    report = audit_polarity_boundary(payload)
    assert report["passed"] is False
    assert report["gates"]["no_exact_driver_type_bridge"] is False


def test_candidate_cannot_become_promotion_evidence() -> None:
    payload = copy.deepcopy(_payload())
    payload["authenticated_curated_ui_observations"]["snpp41"][
        "candidate_matches_are_promotion_evidence"
    ] = True
    report = audit_polarity_boundary(payload)
    assert report["passed"] is False
    assert report["gates"]["candidate_not_promotion_evidence"] is False


def test_snpp39_curated_line_cannot_be_relabelled_as_functional_driver() -> None:
    payload = copy.deepcopy(_payload())
    record = payload["authenticated_curated_ui_observations"]["snpp39"][
        "confident_vnc_matches"
    ][0]
    record["matches_hook_extension_functional_driver"] = True
    report = audit_polarity_boundary(payload)
    assert report["passed"] is False
    assert report["gates"]["snpp39_confident_observation_exact"] is False
