from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "neurofly-snpp39-snpp41-tuning-evidence-audit-v1"
EVIDENCE_SCHEMA = "neurofly-snpp39-snpp41-tuning-evidence-v0.1"
STATUS_REVIEW = "REVIEW_REQUIRED"
STATUS_FAIL = "FAIL"
FORBIDDEN_POLARITY_ASSIGNMENTS = {
    "SNpp39=flexion",
    "SNpp39=extension",
    "SNpp41=flexion",
    "SNpp41=extension",
}


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def audit_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    decision = payload.get("decision", {})
    unresolved = payload.get("unresolved_claims", [])
    forbidden = set(str(item) for item in payload.get("forbidden_inferences", []))
    supported = payload.get("supported_claims", [])
    conflicts = payload.get("annotation_conflicts", [])

    unresolved_text = "\n".join(str(item.get("claim", "")) for item in unresolved)
    gates = {
        "exact_evidence_schema": payload.get("schema") == EVIDENCE_SCHEMA,
        "exact_systematic_types": payload.get("systematic_types") == ["SNpp39", "SNpp41"],
        "hook_directional_identity_supported": decision.get("hook_directional_movement_identity_supported") is True,
        "polarity_explicitly_unresolved": decision.get("systematic_type_direction_polarity_resolved") is False,
        "both_systematic_types_have_unresolved_polarity_claims": (
            "SNpp39" in unresolved_text and "SNpp41" in unresolved_text and len(unresolved) >= 2
        ),
        "all_four_polarity_assignments_forbidden": FORBIDDEN_POLARITY_ASSIGNMENTS.issubset(forbidden),
        "supported_claims_have_sources": bool(supported)
        and all(bool(item.get("sources")) for item in supported),
        "annotation_conflicts_preserved": len(conflicts) >= 2,
        "current_calibration_blocked": decision.get("current_calibration_authorized") is False,
        "stimulation_disabled": decision.get("stimulation_enabled") is False,
        "runtime_transduction_disabled": decision.get("runtime_transduction_enabled") is False,
        "promotion_blocked": decision.get("promotion_ready") is False,
    }
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "status": STATUS_REVIEW if passed else STATUS_FAIL,
        "passed": passed,
        "evidence_sha256": _sha256_json(payload),
        "systematic_types": payload.get("systematic_types"),
        "hook_directional_movement_identity_supported": decision.get(
            "hook_directional_movement_identity_supported"
        ),
        "systematic_type_direction_polarity_resolved": decision.get(
            "systematic_type_direction_polarity_resolved"
        ),
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "promotion_ready": False,
        "gates": gates,
        "interpretation": (
            "Current public evidence supports FeCO hook-related directional movement identity for "
            "SNpp39/SNpp41 but does not explicitly resolve which systematic type is flexion- versus "
            "extension-encoding. NeuroFly therefore forbids polarity assignment by morphology or "
            "predicted reflex sign and keeps proprioceptive current/stimulation blocked."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", default="data/snpp39_snpp41_tuning_evidence_v01.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.evidence).read_text())
    report = audit_evidence(payload)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
