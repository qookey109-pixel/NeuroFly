from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


INTAKE_SCHEMA = "neurofly-proprioception-curated-identity-receipt-intake-v0.1"
RECEIPT_SCHEMA = "neurofly-proprioception-curated-identity-receipt-v0.1"
STATUS_REVIEW = "REVIEW_REQUIRED"
EXPECTED_DIRECTIONS = {"hook_flexion", "hook_extension"}
EXPECTED_TYPES = {"SNpp39", "SNpp41"}
EXPECTED_HYPOTHESES = {"SNpp39": "extension", "SNpp41": "flexion"}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

_EXACT_ANCHORS = {
    "hook_flexion": {
        ("GMR21D12-GAL4",),
        ("R32H08-GAL4.DBD", "VT038873-p65ADZ"),
    },
    "hook_extension": {
        ("VT018774-p65ADZ", "VT040547-GAL4.DBD"),
    },
}


def _sha256(value: str) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _driver_reference_valid(direction: str, ref: Any) -> bool:
    if not isinstance(ref, dict):
        return False
    kind = ref.get("kind")
    if kind == "exact-functional-driver":
        components = ref.get("components")
        if not isinstance(components, list) or not components:
            return False
        normalized = tuple(sorted(str(item) for item in components))
        return normalized in _EXACT_ANCHORS.get(direction, set())
    if kind == "immutable-equivalent-line":
        return bool(ref.get("line_identifier")) and _sha256(
            ref.get("equivalence_receipt_sha256")
        )
    return False


def validate_candidate_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    """Validate an offline frozen curated identity receipt without authorizing runtime use."""

    source = receipt.get("source", {})
    records = receipt.get("records")
    if not isinstance(records, list):
        records = []

    top_gates = {
        "receipt_schema_exact": receipt.get("schema") == RECEIPT_SCHEMA,
        "capture_method_allowed": receipt.get("capture_method")
        in {"authorized-neuronbridge-session", "verified-immutable-annotation-archive"},
        "source_service_exact": source.get("service") == "NeuronBridge",
        "source_endpoint_exact": source.get("endpoint") == "/curated_matches",
        "source_table_exact": source.get("table")
        == "janelia-neuronbridge-custom-annotations",
        "source_version_present": bool(receipt.get("source_version")),
        "captured_at_present": bool(receipt.get("captured_at")),
        "authorization_header_not_stored": receipt.get("authorization_header_stored")
        is False,
        "credentials_or_tokens_not_stored": receipt.get("credentials_or_tokens_stored")
        is False,
        "raw_response_sha256_valid": _sha256(receipt.get("raw_response_sha256")),
        "records_present": bool(records),
    }

    direction_targets: dict[str, set[str]] = {direction: set() for direction in EXPECTED_DIRECTIONS}
    record_results: list[dict[str, Any]] = []
    all_record_gates = True

    for index, record in enumerate(records):
        direction = record.get("direction") if isinstance(record, dict) else None
        gates = {
            "direction_allowed": direction in EXPECTED_DIRECTIONS,
            "driver_reference_valid": _driver_reference_valid(direction, record.get("driver_reference"))
            if isinstance(record, dict) and direction in EXPECTED_DIRECTIONS
            else False,
            "queried_identifier_present": bool(record.get("queried_identifier"))
            if isinstance(record, dict)
            else False,
            "dataset_present": bool(record.get("dataset")) if isinstance(record, dict) else False,
            "region_vnc": str(record.get("region", "")).lower() == "vnc"
            if isinstance(record, dict)
            else False,
            "annotation_confident": record.get("annotation") == "Confident"
            if isinstance(record, dict)
            else False,
            "annotator_present": bool(record.get("annotator")) if isinstance(record, dict) else False,
            "cell_type_allowed": record.get("cell_type") in EXPECTED_TYPES
            if isinstance(record, dict)
            else False,
            "raw_item_sha256_valid": _sha256(record.get("raw_item_sha256"))
            if isinstance(record, dict)
            else False,
        }
        passed = all(gates.values())
        all_record_gates = all_record_gates and passed
        if passed:
            direction_targets[direction].add(record["cell_type"])
        record_results.append({"index": index, "passed": passed, "gates": gates})

    coverage = all(direction_targets[direction] for direction in EXPECTED_DIRECTIONS)
    within_direction_consistent = all(
        len(direction_targets[direction]) == 1 for direction in EXPECTED_DIRECTIONS
    ) if coverage else False
    candidate_mapping = (
        {direction: next(iter(direction_targets[direction])) for direction in sorted(EXPECTED_DIRECTIONS)}
        if within_direction_consistent
        else {}
    )
    pure_bijection = (
        within_direction_consistent
        and set(candidate_mapping.values()) == EXPECTED_TYPES
        and len(set(candidate_mapping.values())) == 2
    )

    inferred_expected = {
        "hook_extension": "SNpp39",
        "hook_flexion": "SNpp41",
    }
    hypothesis_agreement = pure_bijection and candidate_mapping == inferred_expected

    gates = {
        **top_gates,
        "all_records_valid": all_record_gates,
        "both_direction_classes_covered": coverage,
        "within_direction_target_consistency": within_direction_consistent,
        "cross_direction_pure_bijection": pure_bijection,
    }
    receipt_valid = all(gates.values())

    if not receipt_valid:
        state = "INVALID_RECEIPT"
    elif hypothesis_agreement:
        state = "VALID_RECEIPT_REVIEW_REQUIRED"
    else:
        state = "VALID_RECEIPT_CONFLICT_REVIEW_REQUIRED"

    return {
        "schema": "neurofly-proprioception-curated-identity-receipt-validation-v0.1",
        "state": state,
        "receipt_valid": receipt_valid,
        "candidate_mapping": candidate_mapping if receipt_valid else {},
        "hypothesis_agreement": hypothesis_agreement if receipt_valid else None,
        "record_results": record_results,
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


def audit_intake_contract(payload: dict[str, Any]) -> dict[str, Any]:
    upstream = payload.get("upstream_provenance_gate", {})
    source = payload.get("official_source_contract", {})
    rules = payload.get("receipt_acceptance_rules", {})
    candidate = payload.get("candidate_receipt")

    gates = {
        "schema_exact": payload.get("schema") == INTAKE_SCHEMA,
        "status_review_required": payload.get("status") == STATUS_REVIEW,
        "receipt_not_provided": payload.get("receipt_state") == "NOT_PROVIDED" and candidate is None,
        "scope_offline_only": payload.get("scope")
        == "offline-authorized-curated-receipt-intake-only",
        "upstream_pr_exact": upstream.get("pull_request") == 76,
        "upstream_head_exact": upstream.get("head_sha")
        == "e6a2b99f27c6ba93286cc007c97ab5c4c60e539d",
        "upstream_state_exact": upstream.get("provenance_state")
        == "AUTHENTICATED_CURATED_SOURCE_REQUIRED",
        "capture_methods_exact": set(payload.get("accepted_capture_methods", []))
        == {"authorized-neuronbridge-session", "verified-immutable-annotation-archive"},
        "source_contract_exact": source.get("service") == "NeuronBridge"
        and source.get("curated_endpoint") == "/curated_matches"
        and source.get("curated_table") == "janelia-neuronbridge-custom-annotations"
        and source.get("required_confidence") == "Confident"
        and source.get("required_region") == "vnc"
        and set(source.get("allowed_systematic_types", [])) == EXPECTED_TYPES,
        "both_directions_required": rules.get("both_direction_classes_required") is True,
        "pure_bijection_required": rules.get("cross_direction_pure_bijection_required") is True,
        "tokens_forbidden": rules.get("authorization_header_storage_forbidden") is True
        and rules.get("credential_or_token_storage_forbidden") is True,
        "hashes_required": rules.get("raw_response_sha256_required") is True
        and rules.get("raw_item_sha256_required") is True,
        "direct_crosswalk_blocked": payload.get("direct_crosswalk_found") is False,
        "polarity_unresolved": payload.get("polarity_resolved") is False,
        "current_calibration_blocked": payload.get("current_calibration_authorized") is False,
        "stimulation_disabled": payload.get("stimulation_enabled") is False,
        "runtime_transduction_disabled": payload.get("runtime_transduction_enabled") is False,
        "runtime_gating_blocked": payload.get("runtime_gating_authorized") is False,
        "neural_payload_blocked": payload.get("neural_payload_eligible") is False,
        "promotion_blocked": payload.get("promotion_ready") is False,
    }
    passed = all(gates.values())
    return {
        "schema": "neurofly-proprioception-curated-identity-receipt-intake-audit-v1",
        "status": STATUS_REVIEW if passed else "FAIL",
        "passed": passed,
        "receipt_state": "NOT_PROVIDED",
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


def canonical_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--intake",
        default="data/proprioception_curated_identity_receipt_intake_v01.json",
    )
    parser.add_argument("--receipt")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    if args.receipt:
        report = validate_candidate_receipt(json.loads(Path(args.receipt).read_text()))
        exit_code = 0 if report["receipt_valid"] else 1
    else:
        report = audit_intake_contract(json.loads(Path(args.intake).read_text()))
        exit_code = 0 if report["passed"] else 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
