import copy
import json
from pathlib import Path

from neurofly.proprioception_curated_identity_evidence_review import (
    audit_review_preparation_contract,
    classify_validated_receipt,
)
from neurofly.proprioception_curated_identity_receipt import validate_candidate_receipt


CONTROL_PATH = Path("data/proprioception_curated_identity_evidence_review_preparation_v01.json")


def _synthetic_receipt(*, conflict: bool = False) -> dict:
    flexion_type = "SNpp39" if conflict else "SNpp41"
    extension_type = "SNpp41" if conflict else "SNpp39"
    return {
        "schema": "neurofly-proprioception-curated-identity-receipt-v0.1",
        "capture_method": "authorized-neuronbridge-session",
        "source": {
            "service": "NeuronBridge",
            "endpoint": "/curated_matches",
            "table": "janelia-neuronbridge-custom-annotations",
        },
        "source_version": "synthetic-test-version",
        "captured_at": "2026-09-17T00:00:00Z",
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
                "queried_identifier": "synthetic-flexion",
                "dataset": "synthetic:v1",
                "region": "vnc",
                "annotation": "Confident",
                "annotator": "synthetic-test-only",
                "cell_type": flexion_type,
                "raw_item_sha256": "b" * 64,
            },
            {
                "direction": "hook_extension",
                "driver_reference": {
                    "kind": "exact-functional-driver",
                    "components": ["VT018774-p65ADZ", "VT040547-GAL4.DBD"],
                },
                "queried_identifier": "synthetic-extension",
                "dataset": "synthetic:v1",
                "region": "vnc",
                "annotation": "Confident",
                "annotator": "synthetic-test-only",
                "cell_type": extension_type,
                "raw_item_sha256": "c" * 64,
            },
        ],
    }


def test_review_preparation_control_passes_and_locks_remain_closed():
    payload = json.loads(CONTROL_PATH.read_text())
    report = audit_review_preparation_contract(payload)
    assert report["passed"] is True
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["state"] == "WAITING_FOR_VALIDATED_RECEIPT"
    assert report["direct_crosswalk_found"] is False
    assert report["polarity_resolved"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["runtime_gating_authorized"] is False
    assert report["neural_payload_eligible"] is False
    assert report["promotion_ready"] is False


def test_synthetic_agreement_is_classified_for_human_review_only():
    validation = validate_candidate_receipt(_synthetic_receipt(conflict=False))
    assert validation["state"] == "VALID_RECEIPT_REVIEW_REQUIRED"
    report = classify_validated_receipt(validation)
    assert report["validated_receipt_accepted"] is True
    assert report["state"] == "EVIDENCE_SUPPORTS_CURRENT_HYPOTHESIS_REVIEW_REQUIRED"
    assert report["candidate_mapping"] == {
        "hook_extension": "SNpp39",
        "hook_flexion": "SNpp41",
    }
    assert report["hypothesis_agreement"] is True
    assert report["human_science_review_required"] is True
    assert report["science_review_completed"] is False
    assert report["synthetic_receipt_counts_as_evidence"] is False
    assert report["direct_crosswalk_found"] is False
    assert report["polarity_resolved"] is False
    assert report["promotion_ready"] is False


def test_synthetic_conflict_is_preserved_for_human_review():
    validation = validate_candidate_receipt(_synthetic_receipt(conflict=True))
    assert validation["state"] == "VALID_RECEIPT_CONFLICT_REVIEW_REQUIRED"
    report = classify_validated_receipt(validation)
    assert report["validated_receipt_accepted"] is True
    assert report["state"] == "EVIDENCE_CONFLICTS_CURRENT_HYPOTHESIS_REVIEW_REQUIRED"
    assert report["candidate_mapping"] == {
        "hook_extension": "SNpp41",
        "hook_flexion": "SNpp39",
    }
    assert report["hypothesis_agreement"] is False
    assert report["direct_crosswalk_found"] is False
    assert report["polarity_resolved"] is False
    assert report["promotion_ready"] is False


def test_tampered_state_hypothesis_pair_fails_closed():
    validation = validate_candidate_receipt(_synthetic_receipt(conflict=False))
    validation["state"] = "VALID_RECEIPT_CONFLICT_REVIEW_REQUIRED"
    report = classify_validated_receipt(validation)
    assert report["validated_receipt_accepted"] is False
    assert report["state"] == "INVALID_VALIDATION_REPORT"


def test_upstream_lock_opening_fails_closed():
    validation = validate_candidate_receipt(_synthetic_receipt(conflict=False))
    validation["direct_crosswalk_found"] = True
    report = classify_validated_receipt(validation)
    assert report["validated_receipt_accepted"] is False
    assert report["state"] == "INVALID_VALIDATION_REPORT"


def test_validation_report_exact_top_level_allowlist_rejects_extra_payload():
    validation = validate_candidate_receipt(_synthetic_receipt(conflict=False))
    validation["raw_response"] = {"not": "allowed in review-stage validation report"}
    report = classify_validated_receipt(validation)
    assert report["validated_receipt_accepted"] is False
    assert report["gates"]["validation_top_level_exact_allowlist"] is False


def test_failed_upstream_gate_cannot_be_reclassified_as_evidence():
    validation = validate_candidate_receipt(_synthetic_receipt(conflict=False))
    tampered = copy.deepcopy(validation)
    tampered["gates"]["both_direction_classes_covered"] = False
    report = classify_validated_receipt(tampered)
    assert report["validated_receipt_accepted"] is False
    assert report["gates"]["all_upstream_validation_gates_pass"] is False


def test_control_contains_no_real_receipt():
    payload = json.loads(CONTROL_PATH.read_text())
    assert payload["evidence_review_input"] is None
    assert payload["classification_policy"]["synthetic_receipts_are_evidence"] is False
