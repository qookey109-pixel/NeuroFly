from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.proprioception_functional_driver_bridge_gate_audit import audit


EVIDENCE_PATH = Path("data/proprioception_functional_driver_bridge_gate_v01.json")


def _evidence() -> dict:
    return json.loads(EVIDENCE_PATH.read_text())


def test_bridge_gate_passes_only_as_access_required_review() -> None:
    report = audit(_evidence())

    assert report["passed"] is True
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["bridge_state"] == "ACCESS_REQUIRED"
    assert report["direct_bridge_ready"] is False
    assert report["direct_crosswalk_found"] is False
    assert report["polarity_resolved"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["runtime_gating_authorized"] is False
    assert report["neural_payload_eligible"] is False
    assert report["promotion_ready"] is False


def test_functional_direction_driver_context_is_frozen_for_both_hook_classes() -> None:
    evidence = _evidence()
    functional = evidence["functional_driver_evidence"]

    assert set(functional) == {"hook_flexion", "hook_extension"}
    assert functional["hook_flexion"]["direct_functional_label_supported"] is True
    assert functional["hook_extension"]["direct_functional_label_supported"] is True

    flexion_components = {
        tuple(driver["components"]) for driver in functional["hook_flexion"]["drivers"]
    }
    extension_components = {
        tuple(driver["components"])
        for driver in functional["hook_extension"]["drivers"]
    }
    assert ("GMR21D12-GAL4",) in flexion_components
    assert ("VT038873-p65ADZ", "R32H08-GAL4.DBD") in flexion_components
    assert ("VT018774-p65ADZ", "VT040547-GAL4.DBD") in extension_components


def test_neuronbridge_capability_is_not_misrepresented_as_an_obtained_bridge() -> None:
    evidence = _evidence()
    capability = evidence["neuronbridge_capability"]

    assert capability["curated_split_gal4_to_cell_type_supported"] is True
    assert capability["curated_endpoint"] == "/curated_matches"
    assert capability["search_requires_login"] is True
    assert capability["authenticated_curated_result_obtained"] is False
    assert capability["public_exact_pair_receipt_frozen"] is False
    assert evidence["direct_bridge_receipt"] is None


def test_claiming_an_authenticated_result_without_a_receipt_fails_closed() -> None:
    evidence = copy.deepcopy(_evidence())
    evidence["neuronbridge_capability"]["authenticated_curated_result_obtained"] = True

    report = audit(evidence)

    assert report["passed"] is False
    assert report["gates"]["authenticated_bridge_not_claimed"] is False


def test_component_only_expression_cannot_be_promoted_to_split_identity() -> None:
    evidence = copy.deepcopy(_evidence())
    evidence["component_only_public_evidence"]["sufficient_for_split_identity"] = True

    report = audit(evidence)

    assert report["passed"] is False
    assert report["gates"]["component_only_evidence_not_promoted"] is False


def test_morphology_match_alone_cannot_become_identity_authority() -> None:
    evidence = copy.deepcopy(_evidence())
    evidence["cross_dataset_conflict_guard"][
        "computed_morphology_match_alone_is_sufficient"
    ] = True

    report = audit(evidence)

    assert report["passed"] is False
    assert report["gates"]["manc_conflict_guard_closed"] is False


def test_direct_directional_tuning_cannot_be_inserted_before_exact_bridge() -> None:
    evidence = copy.deepcopy(_evidence())
    evidence["systematic_types"]["SNpp39"]["direct_directional_tuning"] = "extension"

    report = audit(evidence)

    assert report["passed"] is False
    assert report["gates"]["direct_directional_tuning_unresolved"] is False


def test_predeclared_promotion_rule_cannot_be_weakened_to_candidate_confidence() -> None:
    evidence = copy.deepcopy(_evidence())
    evidence["predeclared_promotion_requirements"]["minimum_curated_confidence"] = (
        "Candidate"
    )

    report = audit(evidence)

    assert report["passed"] is False
    assert report["gates"]["promotion_requirements_predeclared"] is False


def test_runtime_and_promotion_locks_remain_closed() -> None:
    for lock in (
        "current_calibration_authorized",
        "stimulation_enabled",
        "runtime_transduction_enabled",
        "runtime_gating_authorized",
        "neural_payload_eligible",
        "promotion_ready",
    ):
        evidence = copy.deepcopy(_evidence())
        evidence[lock] = True
        report = audit(evidence)
        assert report["passed"] is False
