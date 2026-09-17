from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "neurofly-proprioception-polarity-boundary-freeze-v0.1"
STATUS = "FROZEN_PENDING_DIRECT_TYPE_LEVEL_EVIDENCE"
EXPECTED_MAPPING = {"SNpp39": "extension", "SNpp41": "flexion"}
EXPECTED_SNPP41_CANDIDATES = {
    "SS00359",
    "SS02407",
    "SS45467",
    "SS46317",
    "SS58881",
}


def audit_polarity_boundary(payload: dict[str, Any]) -> dict[str, Any]:
    physiology = payload.get("primary_physiology", {})
    flexion = physiology.get("hook_flexion", {})
    extension = physiology.get("hook_extension", {})
    curated = payload.get("authenticated_curated_ui_observations", {})
    snpp39 = curated.get("snpp39", {})
    snpp41 = curated.get("snpp41", {})
    context = payload.get("systematic_annotation_context", {})
    crosswalk = payload.get("crosswalk_audit", {})
    locks = {
        "direct_crosswalk_found": payload.get("direct_crosswalk_found") is False,
        "polarity_resolved": payload.get("polarity_resolved") is False,
        "current_calibration_authorized": payload.get("current_calibration_authorized") is False,
        "stimulation_enabled": payload.get("stimulation_enabled") is False,
        "runtime_transduction_enabled": payload.get("runtime_transduction_enabled") is False,
        "runtime_gating_authorized": payload.get("runtime_gating_authorized") is False,
        "systematic_type_mapping_exposed": payload.get("systematic_type_mapping_exposed") is False,
        "neural_payload_eligible": payload.get("neural_payload_eligible") is False,
        "promotion_ready": payload.get("promotion_ready") is False,
    }

    confident39 = snpp39.get("confident_vnc_matches", [])
    candidate41 = snpp41.get("candidate_vnc_matches", [])

    gates = {
        "schema_exact": payload.get("schema") == SCHEMA,
        "status_exact": payload.get("status") == STATUS,
        "scope_exact": payload.get("scope") == "snpp39-snpp41-hook-polarity-evidence-boundary",
        "upstream_pr_exact": payload.get("upstream", {}).get("pull_request") == 78,
        "upstream_head_exact": payload.get("upstream", {}).get("head_sha")
        == "c8d4e7ace04d75dc0e9e696b8b5826fc67c73092",
        "flexion_driver_exact": flexion.get("ad") == "VT038873-p65ADZ"
        and flexion.get("dbd") == "R32H08-GAL4.DBD",
        "extension_driver_exact": extension.get("ad") == "VT018774-p65ADZ"
        and extension.get("dbd") == "VT040547-GAL4.DBD",
        "physiology_does_not_claim_systematic_types": flexion.get("systematic_type_named_in_source") is False
        and extension.get("systematic_type_named_in_source") is False,
        "ui_observation_not_immutable_api_receipt": curated.get("immutable_api_receipt_present") is False,
        "snpp39_confident_observation_exact": len(confident39) == 1
        and confident39[0].get("line") == "SS57886"
        and confident39[0].get("confidence") == "Confident"
        and str(confident39[0].get("region", "")).lower() == "vnc"
        and confident39[0].get("cell_type") == "SNpp39"
        and confident39[0].get("public_line_ad") == "R23G05-p65ADZp"
        and confident39[0].get("public_line_dbd") == "R41A08-ZpGdbd"
        and confident39[0].get("matches_hook_extension_functional_driver") is False
        and confident39[0].get("matches_hook_flexion_functional_driver") is False,
        "snpp41_no_confident_observation": snpp41.get("confident_vnc_match_count") == 0,
        "snpp41_candidate_set_exact": set(candidate41) == EXPECTED_SNPP41_CANDIDATES,
        "candidate_not_promotion_evidence": snpp41.get("candidate_matches_are_promotion_evidence") is False,
        "hook_identity_only_context": context.get("snpp39_hook_identity_supported") is True
        and context.get("snpp41_hook_identity_supported") is True
        and context.get("exact_flexion_extension_polarity_named_by_authors") is False
        and context.get("circuit_level_polarity_inference_only") is True,
        "no_exact_driver_type_bridge": crosswalk.get("functional_driver_to_snpp39_exact") is False
        and crosswalk.get("functional_driver_to_snpp41_exact") is False
        and crosswalk.get("direct_type_level_polarity_crosswalk_found") is False,
        "best_mapping_is_inference_only": crosswalk.get("best_supported_mapping") == EXPECTED_MAPPING
        and crosswalk.get("mapping_strength") == "PHYSIOLOGY_SUPPORTED_INFERENCE",
        "all_runtime_and_promotion_locks_closed": all(locks.values()),
    }

    passed = all(gates.values())
    return {
        "schema": "neurofly-proprioception-polarity-boundary-freeze-audit-v1",
        "status": STATUS if passed else "FAIL",
        "passed": passed,
        "gates": gates,
        "best_supported_mapping": EXPECTED_MAPPING if passed else {},
        "mapping_strength": "PHYSIOLOGY_SUPPORTED_INFERENCE" if passed else None,
        "direct_crosswalk_found": False,
        "polarity_resolved": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "runtime_gating_authorized": False,
        "systematic_type_mapping_exposed": False,
        "neural_payload_eligible": False,
        "promotion_ready": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/proprioception_polarity_boundary_freeze_v01.json",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    report = audit_polarity_boundary(json.loads(Path(args.input).read_text()))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
