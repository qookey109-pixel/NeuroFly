from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "neurofly-proprioception-cross-dataset-hook-identity-audit-v1"
EVIDENCE_SCHEMA = "neurofly-proprioception-cross-dataset-hook-identity-v0.1"
STATUS_REVIEW = "REVIEW_REQUIRED"
EXPECTED_TYPES = {"SNpp39", "SNpp41"}
EXPECTED_DATASETS = {"BANC_626", "MaleCNS_v1.0"}
EXPECTED_BANC_LEGS = {"front", "middle", "hind"}
EXPECTED_CLASSIFICATION = "femoral chordotonal hook neuron"
EXPECTED_HYPOTHESES = {"SNpp39": "extension", "SNpp41": "flexion"}


def _records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records = payload.get("records")
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    records = _records(payload)
    systematic_types = payload.get("systematic_types")
    if not isinstance(systematic_types, dict):
        systematic_types = {}

    unique_ids = {
        (record.get("dataset"), str(record.get("body_id"))) for record in records
    }
    records_have_unique_ids = len(unique_ids) == len(records)

    record_contract_exact = bool(records) and all(
        record.get("dataset") in EXPECTED_DATASETS
        and record.get("systematic_type") in EXPECTED_TYPES
        and record.get("leg") in {"front", "middle", "hind"}
        and record.get("classification") == EXPECTED_CLASSIFICATION
        and isinstance(record.get("body_id"), str)
        and bool(record.get("body_id"))
        and isinstance(record.get("vfb_id"), str)
        and str(record.get("vfb_id")).startswith("VFB_")
        and isinstance(record.get("source_url"), str)
        and str(record.get("source_url")).startswith(
            "https://www.virtualflybrain.org/term/"
        )
        for record in records
    )

    datasets_by_type = {
        systematic_type: {
            record.get("dataset")
            for record in records
            if record.get("systematic_type") == systematic_type
        }
        for systematic_type in EXPECTED_TYPES
    }
    cross_dataset_type_coverage = all(
        datasets_by_type[systematic_type] == EXPECTED_DATASETS
        for systematic_type in EXPECTED_TYPES
    )

    banc_legs_by_type = {
        systematic_type: {
            record.get("leg")
            for record in records
            if record.get("dataset") == "BANC_626"
            and record.get("systematic_type") == systematic_type
        }
        for systematic_type in EXPECTED_TYPES
    }
    banc_serial_leg_coverage = all(
        banc_legs_by_type[systematic_type] == EXPECTED_BANC_LEGS
        for systematic_type in EXPECTED_TYPES
    )

    banc_subclasses_consistent = all(
        record.get("subclass") == f"{record.get('leg')}_leg_hook_chordotonal_organ_neuron"
        for record in records
        if record.get("dataset") == "BANC_626"
    )

    type_names_exact = set(systematic_types) == EXPECTED_TYPES
    hook_identity_supported = all(
        systematic_types.get(name, {}).get("hook_identity_supported") is True
        for name in EXPECTED_TYPES
    )
    direct_tuning_unresolved = all(
        systematic_types.get(name, {}).get("direct_directional_tuning") is None
        for name in EXPECTED_TYPES
    )
    hypotheses_unchanged = all(
        systematic_types.get(name, {}).get("circuit_consistent_hypothesis") == expected
        for name, expected in EXPECTED_HYPOTHESES.items()
    )
    hypotheses_stay_inferential = all(
        systematic_types.get(name, {}).get("hypothesis_strength")
        == "PHYSIOLOGY_SUPPORTED_INFERENCE"
        for name in EXPECTED_TYPES
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
        "scope_identity_only": payload.get("scope") == "systematic-hook-identity-only",
        "source_kind_snapshot": payload.get("source_kind")
        == "public-vfb-annotation-snapshot",
        "record_contract_exact": record_contract_exact,
        "record_ids_unique": records_have_unique_ids,
        "both_types_present_in_both_datasets": cross_dataset_type_coverage,
        "banc_front_middle_hind_coverage_per_type": banc_serial_leg_coverage,
        "banc_hook_subclasses_match_leg": banc_subclasses_consistent,
        "exact_systematic_types": type_names_exact,
        "hook_identity_supported_for_both": hook_identity_supported,
        "direct_directional_tuning_unresolved": direct_tuning_unresolved,
        "circuit_hypotheses_unchanged": hypotheses_unchanged,
        "hypotheses_marked_inferential": hypotheses_stay_inferential,
        "cross_dataset_hook_identity_consistent": payload.get(
            "cross_dataset_hook_identity_consistent"
        )
        is True,
        **locks,
    }
    passed = all(gates.values())

    return {
        "schema": SCHEMA,
        "status": STATUS_REVIEW if passed else "FAIL",
        "passed": passed,
        "systematic_hook_identity_supported": passed,
        "direct_crosswalk_found": False,
        "polarity_resolved": False,
        "direct_directional_tuning": {name: None for name in sorted(EXPECTED_TYPES)},
        "circuit_consistent_hypotheses": dict(sorted(EXPECTED_HYPOTHESES.items())),
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "runtime_gating_authorized": False,
        "neural_payload_eligible": False,
        "promotion_ready": False,
        "gates": gates,
        "interpretation": (
            "Public VFB records independently preserve SNpp39 and SNpp41 as femoral chordotonal "
            "hook systematic types across BANC and MaleCNS examples. This strengthens hook identity "
            "consistency only; it does not provide an exact flexion/extension functional crosswalk."
        ),
    }


def load_evidence(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence",
        default="data/proprioception_cross_dataset_hook_identity_v01.json",
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
