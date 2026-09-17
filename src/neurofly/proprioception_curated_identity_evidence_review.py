from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CONTROL_SCHEMA = "neurofly-proprioception-curated-identity-evidence-review-preparation-v0.1"
VALIDATION_SCHEMA = "neurofly-proprioception-curated-identity-receipt-validation-v0.1"
CLASSIFICATION_SCHEMA = "neurofly-proprioception-curated-identity-evidence-review-classification-v0.1"
STATUS_REVIEW = "REVIEW_REQUIRED"
EXPECTED_MAPPING = {"hook_extension": "SNpp39", "hook_flexion": "SNpp41"}
EXPECTED_DIRECTIONS = set(EXPECTED_MAPPING)
EXPECTED_TYPES = set(EXPECTED_MAPPING.values())
ALLOWED_VALIDATION_STATES = {
    "VALID_RECEIPT_REVIEW_REQUIRED",
    "VALID_RECEIPT_CONFLICT_REVIEW_REQUIRED",
}
EXPECTED_VALIDATION_KEYS = {
    "schema",
    "state",
    "receipt_valid",
    "candidate_mapping",
    "hypothesis_agreement",
    "record_results",
    "gates",
    "direct_crosswalk_found",
    "polarity_resolved",
    "current_calibration_authorized",
    "stimulation_enabled",
    "runtime_transduction_enabled",
    "runtime_gating_authorized",
    "neural_payload_eligible",
    "promotion_ready",
}
EXPECTED_RECORD_RESULT_KEYS = {"index", "passed", "gates"}


def _mapping_is_pure_bijection(mapping: Any) -> bool:
    return (
        isinstance(mapping, dict)
        and set(mapping) == EXPECTED_DIRECTIONS
        and set(mapping.values()) == EXPECTED_TYPES
        and len(set(mapping.values())) == 2
    )


def classify_validated_receipt(validation: dict[str, Any]) -> dict[str, Any]:
    """Classify an upstream validated receipt for later human science review.

    This function intentionally cannot resolve polarity or authorize runtime behavior.
    """

    top_level_exact = isinstance(validation, dict) and set(validation) == EXPECTED_VALIDATION_KEYS
    mapping = validation.get("candidate_mapping") if isinstance(validation, dict) else None
    record_results = validation.get("record_results") if isinstance(validation, dict) else None
    validation_gates = validation.get("gates") if isinstance(validation, dict) else None
    hypothesis_agreement = validation.get("hypothesis_agreement") if isinstance(validation, dict) else None
    state = validation.get("state") if isinstance(validation, dict) else None

    all_record_results_pass = (
        isinstance(record_results, list)
        and bool(record_results)
        and all(
            isinstance(item, dict)
            and set(item) == EXPECTED_RECORD_RESULT_KEYS
            and item.get("passed") is True
            and isinstance(item.get("gates"), dict)
            and bool(item["gates"])
            and all(value is True for value in item["gates"].values())
            for item in record_results
        )
    )
    all_validation_gates_pass = (
        isinstance(validation_gates, dict)
        and bool(validation_gates)
        and all(value is True for value in validation_gates.values())
    )
    state_matches_agreement = (
        (hypothesis_agreement is True and state == "VALID_RECEIPT_REVIEW_REQUIRED")
        or (
            hypothesis_agreement is False
            and state == "VALID_RECEIPT_CONFLICT_REVIEW_REQUIRED"
        )
    )

    locks_closed = (
        validation.get("direct_crosswalk_found") is False
        and validation.get("polarity_resolved") is False
        and validation.get("current_calibration_authorized") is False
        and validation.get("stimulation_enabled") is False
        and validation.get("runtime_transduction_enabled") is False
        and validation.get("runtime_gating_authorized") is False
        and validation.get("neural_payload_eligible") is False
        and validation.get("promotion_ready") is False
    ) if isinstance(validation, dict) else False

    gates = {
        "validation_top_level_exact_allowlist": top_level_exact,
        "validation_schema_exact": validation.get("schema") == VALIDATION_SCHEMA
        if isinstance(validation, dict)
        else False,
        "validation_state_allowed": state in ALLOWED_VALIDATION_STATES,
        "receipt_structurally_valid": validation.get("receipt_valid") is True
        if isinstance(validation, dict)
        else False,
        "candidate_mapping_pure_bijection": _mapping_is_pure_bijection(mapping),
        "hypothesis_agreement_boolean": isinstance(hypothesis_agreement, bool),
        "validation_state_matches_hypothesis_agreement": state_matches_agreement,
        "all_upstream_validation_gates_pass": all_validation_gates_pass,
        "all_upstream_record_results_pass": all_record_results_pass,
        "upstream_science_runtime_locks_closed": locks_closed,
    }
    accepted = all(gates.values())

    if not accepted:
        review_state = "INVALID_VALIDATION_REPORT"
    elif hypothesis_agreement:
        review_state = "EVIDENCE_SUPPORTS_CURRENT_HYPOTHESIS_REVIEW_REQUIRED"
    else:
        review_state = "EVIDENCE_CONFLICTS_CURRENT_HYPOTHESIS_REVIEW_REQUIRED"

    return {
        "schema": CLASSIFICATION_SCHEMA,
        "state": review_state,
        "validated_receipt_accepted": accepted,
        "candidate_mapping": dict(mapping) if accepted else {},
        "hypothesis_agreement": hypothesis_agreement if accepted else None,
        "gates": gates,
        "human_science_review_required": True,
        "science_review_completed": False,
        "synthetic_receipt_counts_as_evidence": False,
        "direct_crosswalk_found": False,
        "polarity_resolved": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "runtime_gating_authorized": False,
        "neural_payload_eligible": False,
        "promotion_ready": False,
    }


def audit_review_preparation_contract(payload: dict[str, Any]) -> dict[str, Any]:
    upstream = payload.get("upstream_intake", {})
    policy = payload.get("classification_policy", {})
    hypothesis = payload.get("current_hypothesis", {})

    gates = {
        "schema_exact": payload.get("schema") == CONTROL_SCHEMA,
        "status_review_required": payload.get("status") == STATUS_REVIEW,
        "waiting_for_validated_receipt": payload.get("state")
        == "WAITING_FOR_VALIDATED_RECEIPT"
        and payload.get("evidence_review_input") is None,
        "scope_machine_classification_only": payload.get("scope")
        == "machine-classification-of-validated-curated-receipt-only",
        "upstream_pr_exact": upstream.get("pull_request") == 77,
        "upstream_head_exact": upstream.get("head_sha")
        == "e65738731c44f831eb50a8e8ee102b0da8014a2a",
        "upstream_validation_schema_exact": upstream.get("validation_schema")
        == VALIDATION_SCHEMA,
        "accepted_validation_states_exact": set(
            payload.get("accepted_validation_states", [])
        )
        == ALLOWED_VALIDATION_STATES,
        "current_hypothesis_exact": hypothesis.get("hook_extension") == "SNpp39"
        and hypothesis.get("hook_flexion") == "SNpp41"
        and hypothesis.get("strength") == "PHYSIOLOGY_SUPPORTED_INFERENCE",
        "structural_validation_required": policy.get(
            "structural_receipt_validation_required"
        )
        is True,
        "all_validation_gates_required": policy.get(
            "all_upstream_validation_gates_must_pass"
        )
        is True,
        "all_record_results_required": policy.get(
            "all_upstream_record_results_must_pass"
        )
        is True,
        "bijection_recheck_required": policy.get(
            "candidate_mapping_bijection_rechecked"
        )
        is True,
        "state_agreement_consistency_required": policy.get(
            "validation_state_must_match_hypothesis_agreement"
        )
        is True,
        "exact_allowlist_required": policy.get(
            "validation_report_top_level_exact_allowlist_required"
        )
        is True,
        "synthetic_not_evidence": policy.get("synthetic_receipts_are_evidence")
        is False,
        "human_review_required": policy.get("human_science_review_required") is True,
        "automatic_polarity_promotion_forbidden": policy.get(
            "automatic_polarity_promotion_forbidden"
        )
        is True,
        "automatic_runtime_mapping_forbidden": policy.get(
            "automatic_runtime_mapping_forbidden"
        )
        is True,
        "direct_crosswalk_blocked": payload.get("direct_crosswalk_found") is False,
        "polarity_unresolved": payload.get("polarity_resolved") is False,
        "current_calibration_blocked": payload.get("current_calibration_authorized")
        is False,
        "stimulation_disabled": payload.get("stimulation_enabled") is False,
        "runtime_transduction_disabled": payload.get("runtime_transduction_enabled")
        is False,
        "runtime_gating_blocked": payload.get("runtime_gating_authorized") is False,
        "neural_payload_blocked": payload.get("neural_payload_eligible") is False,
        "promotion_blocked": payload.get("promotion_ready") is False,
    }
    passed = all(gates.values())
    return {
        "schema": "neurofly-proprioception-curated-identity-evidence-review-preparation-audit-v1",
        "status": STATUS_REVIEW if passed else "FAIL",
        "passed": passed,
        "state": "WAITING_FOR_VALIDATED_RECEIPT",
        "gates": gates,
        "direct_crosswalk_found": False,
        "polarity_resolved": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "runtime_gating_authorized": False,
        "neural_payload_eligible": False,
        "promotion_ready": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--control",
        default="data/proprioception_curated_identity_evidence_review_preparation_v01.json",
    )
    parser.add_argument("--validation-report")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    if args.validation_report:
        report = classify_validated_receipt(
            json.loads(Path(args.validation_report).read_text())
        )
        exit_code = 0 if report["validated_receipt_accepted"] else 1
    else:
        report = audit_review_preparation_contract(
            json.loads(Path(args.control).read_text())
        )
        exit_code = 0 if report["passed"] else 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
