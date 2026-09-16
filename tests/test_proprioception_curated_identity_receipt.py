from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.proprioception_curated_identity_receipt import (
    audit_intake_contract,
    canonical_sha256,
    validate_candidate_receipt,
)


INTAKE = Path("data/proprioception_curated_identity_receipt_intake_v01.json")


def _intake() -> dict:
    return json.loads(INTAKE.read_text())


def _synthetic_receipt(*, conflicting: bool = False) -> dict:
    flexion_type = "SNpp39" if conflicting else "SNpp41"
    extension_type = "SNpp41" if conflicting else "SNpp39"
    return {
        "schema": "neurofly-proprioception-curated-identity-receipt-v0.1",
        "capture_method": "authorized-neuronbridge-session",
        "source": {
            "service": "NeuronBridge",
            "endpoint": "/curated_matches",
            "table": "janelia-neuronbridge-custom-annotations",
        },
        "source_version": "synthetic-test-version",
        "captured_at": "2099-01-01T00:00:00Z",
        "authorization_header_stored": False,
        "credentials_or_tokens_stored": False,
        "raw_response_sha256": "a" * 64,
        "records": [
            {
                "direction": "hook_flexion",
                "driver_reference": {
                    "kind": "exact-functional-driver",
                    "components": ["GMR21D12-GAL4"],
                },
                "queried_identifier": "SYNTHETIC_FLEXION_LINE",
                "dataset": "synthetic:v1",
                "region": "vnc",
                "annotation": "Confident",
                "annotator": "synthetic-test-annotator",
                "cell_type": flexion_type,
                "raw_item_sha256": "b" * 64,
            },
            {
                "direction": "hook_extension",
                "driver_reference": {
                    "kind": "exact-functional-driver",
                    "components": ["VT018774-p65ADZ", "VT040547-GAL4.DBD"],
                },
                "queried_identifier": "SYNTHETIC_EXTENSION_LINE",
                "dataset": "synthetic:v1",
                "region": "vnc",
                "annotation": "Confident",
                "annotator": "synthetic-test-annotator",
                "cell_type": extension_type,
                "raw_item_sha256": "c" * 64,
            },
        ],
    }


def test_intake_contract_is_waiting_only_and_keeps_all_locks_closed() -> None:
    report = audit_intake_contract(_intake())

    assert report["passed"] is True
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["receipt_state"] == "NOT_PROVIDED"
    assert report["direct_crosswalk_found"] is False
    assert report["polarity_resolved"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["runtime_gating_authorized"] is False
    assert report["neural_payload_eligible"] is False
    assert report["promotion_ready"] is False


def test_synthetic_structurally_valid_receipt_requires_review_and_never_promotes() -> None:
    report = validate_candidate_receipt(_synthetic_receipt())

    assert report["receipt_valid"] is True
    assert report["state"] == "VALID_RECEIPT_REVIEW_REQUIRED"
    assert report["candidate_mapping"] == {
        "hook_extension": "SNpp39",
        "hook_flexion": "SNpp41",
    }
    assert report["hypothesis_agreement"] is True
    assert report["direct_crosswalk_found"] is False
    assert report["polarity_resolved"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["promotion_ready"] is False


def test_synthetic_valid_but_hypothesis_conflicting_receipt_is_not_rejected_or_promoted() -> None:
    report = validate_candidate_receipt(_synthetic_receipt(conflicting=True))

    assert report["receipt_valid"] is True
    assert report["state"] == "VALID_RECEIPT_CONFLICT_REVIEW_REQUIRED"
    assert report["candidate_mapping"] == {
        "hook_extension": "SNpp41",
        "hook_flexion": "SNpp39",
    }
    assert report["hypothesis_agreement"] is False
    assert report["direct_crosswalk_found"] is False
    assert report["polarity_resolved"] is False
    assert report["promotion_ready"] is False


def test_candidate_or_non_vnc_record_fails_closed() -> None:
    receipt = _synthetic_receipt()
    receipt["records"][0]["annotation"] = "Candidate"
    assert validate_candidate_receipt(receipt)["receipt_valid"] is False

    receipt = _synthetic_receipt()
    receipt["records"][0]["region"] = "brain"
    assert validate_candidate_receipt(receipt)["receipt_valid"] is False


def test_credentials_or_authorization_header_must_never_be_stored() -> None:
    receipt = _synthetic_receipt()
    receipt["credentials_or_tokens_stored"] = True
    report = validate_candidate_receipt(receipt)
    assert report["receipt_valid"] is False
    assert report["gates"]["credentials_or_tokens_not_stored"] is False

    receipt = _synthetic_receipt()
    receipt["authorization_header_stored"] = True
    report = validate_candidate_receipt(receipt)
    assert report["receipt_valid"] is False
    assert report["gates"]["authorization_header_not_stored"] is False


def test_component_only_or_unreviewed_driver_reference_cannot_pass() -> None:
    receipt = _synthetic_receipt()
    receipt["records"][1]["driver_reference"] = {
        "kind": "exact-functional-driver",
        "components": ["VT018774-p65ADZ"],
    }
    report = validate_candidate_receipt(receipt)
    assert report["receipt_valid"] is False
    assert report["record_results"][1]["gates"]["driver_reference_valid"] is False


def test_immutable_equivalent_line_requires_a_separate_equivalence_hash() -> None:
    receipt = _synthetic_receipt()
    receipt["records"][0]["driver_reference"] = {
        "kind": "immutable-equivalent-line",
        "line_identifier": "SYNTHETIC-LINE-ID",
        "equivalence_receipt_sha256": "d" * 64,
    }
    assert validate_candidate_receipt(receipt)["receipt_valid"] is True

    receipt["records"][0]["driver_reference"].pop("equivalence_receipt_sha256")
    assert validate_candidate_receipt(receipt)["receipt_valid"] is False


def test_both_directions_and_pure_bijection_are_required() -> None:
    receipt = _synthetic_receipt()
    receipt["records"] = receipt["records"][:1]
    assert validate_candidate_receipt(receipt)["receipt_valid"] is False

    receipt = _synthetic_receipt()
    receipt["records"][1]["cell_type"] = "SNpp41"
    report = validate_candidate_receipt(receipt)
    assert report["receipt_valid"] is False
    assert report["gates"]["cross_direction_pure_bijection"] is False


def test_canonical_hash_is_order_stable_for_future_offline_receipts() -> None:
    left = {"b": 2, "a": {"y": 1, "x": 0}}
    right = {"a": {"x": 0, "y": 1}, "b": 2}
    assert canonical_sha256(left) == canonical_sha256(right)


def test_intake_contract_cannot_silently_include_a_candidate_receipt() -> None:
    payload = copy.deepcopy(_intake())
    payload["candidate_receipt"] = _synthetic_receipt()
    payload["receipt_state"] = "PROVIDED"
    report = audit_intake_contract(payload)
    assert report["passed"] is False
    assert report["gates"]["receipt_not_provided"] is False
