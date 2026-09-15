from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCHEMA = "neurofly-proprioception-hook-direction-evidence-audit-v1"
EVIDENCE_SCHEMA = "neurofly-proprioception-hook-direction-evidence-v0.1"
STATUS_REVIEW = "REVIEW_REQUIRED"
EXPECTED_TYPES = {"SNpp39", "SNpp41"}
EXPECTED_HYPOTHESES = {"SNpp39": "extension", "SNpp41": "flexion"}


def audit(payload: dict[str, Any]) -> dict[str, Any]:
    types = payload.get("systematic_types", {})
    type_names = set(types)
    direct_tuning_null = all(
        types.get(name, {}).get("direct_directional_tuning") is None
        for name in EXPECTED_TYPES
    )
    hypotheses_exact = all(
        types.get(name, {}).get("circuit_consistent_hypothesis") == expected
        for name, expected in EXPECTED_HYPOTHESES.items()
    )
    hypotheses_explicitly_inferential = all(
        types.get(name, {}).get("hypothesis_strength")
        == "strong-inference-not-direct-crosswalk"
        for name in EXPECTED_TYPES
    )
    evidence_present = all(
        len(types.get(name, {}).get("evidence", [])) >= 2
        and all(item.get("url") for item in types.get(name, {}).get("evidence", []))
        for name in EXPECTED_TYPES
    )
    locks = {
        "direct_crosswalk_absent": payload.get("direct_crosswalk_found") is False,
        "current_calibration_blocked": payload.get("current_calibration_authorized") is False,
        "stimulation_disabled": payload.get("stimulation_enabled") is False,
        "runtime_transduction_disabled": payload.get("runtime_transduction_enabled") is False,
        "promotion_blocked": payload.get("promotion_ready") is False,
    }
    gates = {
        "evidence_schema_exact": payload.get("schema") == EVIDENCE_SCHEMA,
        "status_review_required": payload.get("status") == STATUS_REVIEW,
        "exact_systematic_types": type_names == EXPECTED_TYPES,
        "direct_directional_tuning_unresolved": direct_tuning_null,
        "circuit_hypotheses_exact": hypotheses_exact,
        "hypotheses_marked_inferential": hypotheses_explicitly_inferential,
        "multiple_evidence_links_per_type": evidence_present,
        "direct_functional_driver_context_present": bool(
            payload.get("direct_functional_context", {}).get("hook_flexion_driver")
            and payload.get("direct_functional_context", {}).get("hook_extension_driver")
        ),
        **locks,
    }
    passed = all(gates.values())
    return {
        "schema": SCHEMA,
        "status": STATUS_REVIEW if passed else "FAIL",
        "passed": passed,
        "direct_crosswalk_found": False,
        "direct_directional_tuning": {name: None for name in sorted(EXPECTED_TYPES)},
        "circuit_consistent_hypotheses": dict(sorted(EXPECTED_HYPOTHESES.items())),
        "promotion_ready": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "gates": gates,
        "interpretation": (
            "The available evidence supports a strong circuit-consistent hypothesis that SNpp41 is "
            "flexion-tuned and SNpp39 is extension-tuned, but no direct type-to-physiology crosswalk "
            "has been frozen. The hypotheses therefore remain non-authoritative and cannot authorize "
            "proprioceptive current, stimulation, or runtime transduction."
        ),
    }


def load_evidence(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--evidence",
        default="data/proprioception_hook_direction_evidence_v01.json",
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
