from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "neurofly-proprioception-curated-identity-provenance-audit-v1"
EVIDENCE_SCHEMA = "neurofly-proprioception-curated-identity-provenance-gate-v0.1"
STATUS_REVIEW = "REVIEW_REQUIRED"
EXPECTED_HYPOTHESES = {"SNpp39": "extension", "SNpp41": "flexion"}


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    open_data = payload.get("neuronbridge_open_data", {})
    curated = payload.get("neuronbridge_curated_service", {})
    archive = payload.get("neuronbridge_annotation_archive", {})
    frontend = payload.get("neuronbridge_frontend", {})
    conclusion = payload.get("provenance_conclusion", {})
    upstream = payload.get("upstream_bridge_gate", {})
    types = payload.get("systematic_types", {})

    hypotheses_exact = set(types) == set(EXPECTED_HYPOTHESES) and all(
        types.get(name, {}).get("direct_directional_tuning") is None
        and types.get(name, {}).get("circuit_consistent_hypothesis") == direction
        and types.get(name, {}).get("hypothesis_strength")
        == "PHYSIOLOGY_SUPPORTED_INFERENCE"
        for name, direction in EXPECTED_HYPOTHESES.items()
    )

    required_open_families = {
        "current.txt",
        "schemas",
        "config.json",
        "publishedNames.txt",
        "references.json",
        "metadata/by_body",
        "metadata/by_line",
        "metadata/cdsresults",
        "metadata/pppresults",
    }
    required_archive_columns = {
        "Line Name",
        "Dataset",
        "Region",
        "Term",
        "Term type",
        "Annotation",
        "Annotator",
    }

    gates = {
        "evidence_schema_exact": payload.get("schema") == EVIDENCE_SCHEMA,
        "status_review_required": payload.get("status") == STATUS_REVIEW,
        "scope_evidence_only": payload.get("scope") == "evidence-provenance-only",
        "upstream_pr_exact": upstream.get("pull_request") == 75,
        "upstream_head_exact": upstream.get("head_sha")
        == "e308dbe815db8c3d65e3d0f03d26eab4387651af",
        "upstream_access_required": upstream.get("bridge_state") == "ACCESS_REQUIRED",
        "upstream_receipt_absent": upstream.get("direct_bridge_receipt") is None,
        "open_data_repo_pinned": open_data.get("repository")
        == "JaneliaSciComp/neuronbridge-data"
        and open_data.get("reviewed_commit")
        == "0b6c184ce5af4fc6ae3264f8c89ba88c62ef2caa",
        "open_data_version_pinned": open_data.get("production_pointer") == "v3_10_0",
        "open_data_api_documented": open_data.get("documented_as_open_rest_api") is True,
        "open_data_families_exact": set(open_data.get("documented_object_families", []))
        == required_open_families,
        "curated_not_documented_as_open_api_family": open_data.get(
            "expert_curated_identity_records_documented_in_open_api"
        )
        is False,
        "computed_morphology_not_identity_authority": open_data.get(
            "computed_or_precomputed_morphology_is_identity_authority"
        )
        is False,
        "curated_service_repo_pinned": curated.get("repository")
        == "JaneliaSciComp/neuronbridge-services"
        and curated.get("reviewed_commit")
        == "3847c602fcc5e3ae2bae47b7308ee11263ae6cef",
        "curated_endpoint_exact": curated.get("endpoint") == "/curated_matches"
        and curated.get("method") == "GET",
        "curated_jwt_required": curated.get("jwt_authorizer_required") is True
        and curated.get("jwt_identity_source") == "$request.header.Authorization",
        "curated_table_exact": curated.get("dynamodb_table")
        == "janelia-neuronbridge-custom-annotations",
        "curated_direct_result_not_obtained": curated.get("direct_query_result_obtained")
        is False,
        "archive_repo_pinned": archive.get("repository")
        == "JaneliaSciComp/neuronbridge-precompute"
        and archive.get("reviewed_commit")
        == "e51e7c1ed6523597a7f6f6f9cbe18a53ac4eb1f3",
        "archive_schema_exact": set(archive.get("input_columns", []))
        == required_archive_columns,
        "archive_table_exact": archive.get("dynamodb_table")
        == "janelia-neuronbridge-custom-annotations",
        "archive_bucket_exact": archive.get("archive_bucket")
        == "s3://janelia-neuronbridge-annotation"
        and archive.get("archive_input_prefix") == "input",
        "archive_public_read_not_claimed": archive.get("public_readability_verified")
        is False,
        "archive_exact_driver_object_absent": archive.get(
            "exact_hook_driver_archive_object_obtained"
        )
        is False
        and archive.get("immutable_archive_receipt") is None,
        "frontend_repo_pinned": frontend.get("repository")
        == "JaneliaSciComp/neuronbridge"
        and frontend.get("reviewed_commit")
        == "18d97306372d27322482208432663f9f2b6b52a8",
        "frontend_curated_separate": frontend.get(
            "curated_results_are_distinct_from_computed_matches"
        )
        is True
        and frontend.get("curated_endpoint_used") == "/curated_matches",
        "provenance_state_exact": conclusion.get("state")
        == "AUTHENTICATED_CURATED_SOURCE_REQUIRED",
        "open_morphology_cannot_resolve": conclusion.get(
            "open_morphology_api_can_resolve_polarity"
        )
        is False,
        "computed_score_cannot_resolve": conclusion.get(
            "computed_match_score_can_resolve_polarity"
        )
        is False,
        "component_expression_cannot_resolve": conclusion.get(
            "component_expression_can_resolve_split_identity"
        )
        is False,
        "curated_or_archive_receipt_required": conclusion.get(
            "authenticated_curated_record_or_equivalent_immutable_archive_required"
        )
        is True,
        "authorization_bypass_forbidden": conclusion.get(
            "login_or_authorization_bypass_permitted"
        )
        is False,
        "systematic_hypotheses_preserved": hypotheses_exact,
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
        "schema": SCHEMA,
        "status": STATUS_REVIEW if passed else "FAIL",
        "passed": passed,
        "provenance_state": "AUTHENTICATED_CURATED_SOURCE_REQUIRED",
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
            "NeuronBridge public precomputed morphology data and expert-curated identity "
            "annotations have distinct provenance paths. The reviewed curated endpoint is "
            "JWT-protected and no exact hook-driver curated receipt or independently "
            "verifiable immutable archive receipt has been obtained. Public morphology "
            "matches therefore cannot promote SNpp39/SNpp41 polarity."
        ),
    }


def load_evidence(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence",
        default="data/proprioception_curated_identity_provenance_gate_v01.json",
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
