from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "neurofly-proprioception-functional-driver-bridge-gate-audit-v1"
EVIDENCE_SCHEMA = "neurofly-proprioception-functional-driver-bridge-gate-v0.1"
STATUS_REVIEW = "REVIEW_REQUIRED"
BRIDGE_ACCESS_REQUIRED = "ACCESS_REQUIRED"
EXPECTED_TYPES = {"SNpp39", "SNpp41"}
EXPECTED_HYPOTHESES = {"SNpp39": "extension", "SNpp41": "flexion"}
EXPECTED_DIRECTIONS = {"hook_flexion", "hook_extension"}


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    functional = payload.get("functional_driver_evidence")
    if not isinstance(functional, dict):
        functional = {}

    systematic_types = payload.get("systematic_types")
    if not isinstance(systematic_types, dict):
        systematic_types = {}

    capability = payload.get("neuronbridge_capability")
    if not isinstance(capability, dict):
        capability = {}

    requirements = payload.get("predeclared_promotion_requirements")
    if not isinstance(requirements, dict):
        requirements = {}

    direct_functional_labels = set(functional) == EXPECTED_DIRECTIONS and all(
        functional.get(direction, {}).get("direct_functional_label_supported") is True
        and isinstance(functional.get(direction, {}).get("drivers"), list)
        and len(functional.get(direction, {}).get("drivers", [])) >= 1
        for direction in EXPECTED_DIRECTIONS
    )

    exact_types = set(systematic_types) == EXPECTED_TYPES
    direct_tuning_unresolved = all(
        systematic_types.get(name, {}).get("direct_directional_tuning") is None
        for name in EXPECTED_TYPES
    )
    hypotheses_unchanged = all(
        systematic_types.get(name, {}).get("circuit_consistent_hypothesis") == expected
        for name, expected in EXPECTED_HYPOTHESES.items()
    )
    hypotheses_inferential = all(
        systematic_types.get(name, {}).get("hypothesis_strength")
        == "PHYSIOLOGY_SUPPORTED_INFERENCE"
        for name in EXPECTED_TYPES
    )

    curated_capability_present = (
        capability.get("curated_split_gal4_to_cell_type_supported") is True
        and capability.get("curated_endpoint") == "/curated_matches"
        and capability.get("reviewed_commit")
        == "18d97306372d27322482208432663f9f2b6b52a8"
        and set(capability.get("confidence_levels", []))
        == {"Confident", "Probable", "Candidate"}
    )

    bridge_still_unobtained = (
        capability.get("search_requires_login") is True
        and capability.get("authenticated_curated_result_obtained") is False
        and capability.get("public_exact_pair_receipt_frozen") is False
        and payload.get("direct_bridge_receipt") is None
    )

    promotion_requirements_frozen = (
        requirements.get("exact_functional_driver_or_immutable_line_identifier") is True
        and requirements.get("expert_curated_match_record_required") is True
        and requirements.get("minimum_curated_confidence") == "Confident"
        and requirements.get("vnc_anatomical_region_required") is True
        and requirements.get("source_or_annotator_required") is True
        and set(requirements.get("systematic_type_must_be_one_of", [])) == EXPECTED_TYPES
        and requirements.get("both_direction_classes_required") is True
        and requirements.get("pure_bijection_required") is True
        and requirements.get("independent_hook_identity_consistency_required") is True
        and requirements.get("conflicting_assignments_forbidden") is True
        and requirements.get("immutable_receipt_required") is True
    )

    component_boundary_closed = (
        payload.get("component_only_public_evidence", {}).get("available") is True
        and payload.get("component_only_public_evidence", {}).get(
            "sufficient_for_split_identity"
        )
        is False
    )
    conflict_guard_closed = (
        payload.get("cross_dataset_conflict_guard", {}).get(
            "manc_legacy_conflicts_observed"
        )
        is True
        and payload.get("cross_dataset_conflict_guard", {}).get(
            "manc_conflict_examples_are_identity_authority"
        )
        is False
        and payload.get("cross_dataset_conflict_guard", {}).get(
            "computed_morphology_match_alone_is_sufficient"
        )
        is False
    )

    locks = {
        "direct_crosswalk_absent": payload.get("direct_crosswalk_found") is False,
        "polarity_unresolved": payload.get("polarity_resolved") is False,
        "current_calibration_blocked": payload.get("current_calibration_authorized") is False,
        "stimulation_disabled": payload.get("stimulation_enabled") is False,
        "runtime_transduction_disabled": payload.get("runtime_transduction_enabled") is False,
        "runtime_gating_blocked": payload.get("runtime_gating_authorized") is False,
        "neural_payload_blocked": payload.get("neural_payload_eligible") is False,
        "promotion_blocked": payload.get("promotion_ready") is False,
    }

    gates = {
        "evidence_schema_exact": payload.get("schema") == EVIDENCE_SCHEMA,
        "status_review_required": payload.get("status") == STATUS_REVIEW,
        "bridge_state_access_required": payload.get("bridge_state")
        == BRIDGE_ACCESS_REQUIRED,
        "identity_only_scope": payload.get("scope")
        == "functional-driver-to-systematic-type-identity-only",
        "functional_direction_labels_present": direct_functional_labels,
        "neuronbridge_curated_capability_present": curated_capability_present,
        "authenticated_bridge_not_claimed": bridge_still_unobtained,
        "promotion_requirements_predeclared": promotion_requirements_frozen,
        "component_only_evidence_not_promoted": component_boundary_closed,
        "manc_conflict_guard_closed": conflict_guard_closed,
        "exact_systematic_types": exact_types,
        "direct_directional_tuning_unresolved": direct_tuning_unresolved,
        "circuit_hypotheses_unchanged": hypotheses_unchanged,
        "hypotheses_marked_inferential": hypotheses_inferential,
        **locks,
    }
    passed = all(gates.values())

    return {
        "schema": SCHEMA,
        "status": STATUS_REVIEW if passed else "FAIL",
        "passed": passed,
        "bridge_state": BRIDGE_ACCESS_REQUIRED if passed else "INVALID_GATE",
        "direct_bridge_ready": False,
        "direct_crosswalk_found": False,
        "polarity_resolved": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "runtime_gating_authorized": False,
        "neural_payload_eligible": False,
        "promotion_ready": False,
        "gates": gates,
        "interpretation": (
            "Direct flexion/extension functional driver identities are supported, and current "
            "NeuronBridge software exposes expert-curated Split-GAL4-to-cell-type matches. "
            "However, no authenticated curated result or immutable exact-pair receipt for these "
            "hook drivers is frozen in NeuroFly. The systematic-type polarity therefore remains "
            "unresolved and all runtime/current promotion locks stay closed."
        ),
    }


def load_evidence(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence",
        default="data/proprioception_functional_driver_bridge_gate_v01.json",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    report = audit(load_evidence(Path(args.evidence)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
