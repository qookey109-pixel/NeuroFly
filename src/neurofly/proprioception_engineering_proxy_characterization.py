from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .proprioception import (
    PROPRIOCEPTION_ENCODING,
    PROPRIOCEPTION_MODEL,
    feco_motion_proprioception,
    proprioceptive_channel_levels,
)


SCHEMA = "neurofly-proprioception-engineering-proxy-characterization-v0.1"
REPORT_SCHEMA = "neurofly-proprioception-engineering-proxy-characterization-report-v0.1"
STATUS = "REVIEW_REQUIRED"
SCOPE = "engineering-proxy-characterization-only"
EXPECTED_DELTAS = [-2.0, -1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 2.0]
EXPECTED_VIBRATIONS = [0.0, 0.25, 0.5, 1.0, 2.0]
EXPECTED_PROPERTIES = {
    "neutral_zero",
    "hook_mutual_exclusion",
    "directional_magnitude_symmetry",
    "club_motion_equals_directional_magnitude",
    "bounded_unit_interval",
    "magnitude_monotonic_nondecreasing",
    "saturates_at_unit_magnitude",
    "vibration_does_not_change_joint_motion_channels",
    "joint_delta_does_not_change_vibration_channel",
}
EXPECTED_BIOLOGY_LOCKS = {
    "systematic_type_identity_resolved",
    "biological_current_calibrated",
    "biological_latency_calibrated",
    "step_cycle_phase_resolved",
    "predictive_inhibition_kernel_resolved",
}
EXPECTED_HARD_LOCKS = {
    "direct_crosswalk_found",
    "polarity_resolved",
    "current_calibration_authorized",
    "stimulation_enabled",
    "runtime_transduction_enabled",
    "runtime_gating_authorized",
    "systematic_type_mapping_exposed",
    "neural_payload_eligible",
    "promotion_ready",
}


def _all_false_exact(payload: Any, expected: set[str]) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload) == expected
        and all(payload[key] is False for key in expected)
    )


def _all_true_exact(payload: Any, expected: set[str]) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload) == expected
        and all(payload[key] is True for key in expected)
    )


def _levels(delta: float, vibration: float) -> dict[str, Any]:
    payload = feco_motion_proprioception(joint_delta=delta, vibration=vibration)
    levels = proprioceptive_channel_levels(payload)
    return {
        "payload": payload,
        "levels": levels,
    }


def audit_characterization(contract: dict[str, Any]) -> dict[str, Any]:
    upstream = contract.get("upstream_boundary", {})
    deltas = contract.get("joint_delta_sweep")
    vibrations = contract.get("vibration_sweep")

    contract_gates = {
        "schema_exact": contract.get("schema") == SCHEMA,
        "status_exact": contract.get("status") == STATUS,
        "scope_exact": contract.get("scope") == SCOPE,
        "upstream_pr_exact": upstream.get("pull_request") == 79,
        "upstream_head_exact": upstream.get("head_sha")
        == "4fb65959ea180bdaeec35d53b680a60e325bd5f2",
        "upstream_state_frozen": upstream.get("state")
        == "FROZEN_PENDING_DIRECT_TYPE_LEVEL_EVIDENCE",
        "model_exact": contract.get("expected_model") == PROPRIOCEPTION_MODEL,
        "encoding_exact": contract.get("expected_encoding") == PROPRIOCEPTION_ENCODING,
        "joint_delta_sweep_exact": deltas == EXPECTED_DELTAS,
        "vibration_sweep_exact": vibrations == EXPECTED_VIBRATIONS,
        "required_properties_exact": _all_true_exact(
            contract.get("required_properties"), EXPECTED_PROPERTIES
        ),
        "biological_claims_locked": _all_false_exact(
            contract.get("biological_claims"), EXPECTED_BIOLOGY_LOCKS
        ),
        "hard_locks_exact": _all_false_exact(
            contract.get("hard_locks"), EXPECTED_HARD_LOCKS
        ),
    }

    grid: dict[tuple[float, float], dict[str, Any]] = {}
    sample_contract_valid = True
    bounded = True
    mutual_exclusion = True
    club_equals_directional = True

    if deltas == EXPECTED_DELTAS and vibrations == EXPECTED_VIBRATIONS:
        for delta in EXPECTED_DELTAS:
            for vibration in EXPECTED_VIBRATIONS:
                sample = _levels(delta, vibration)
                payload = sample["payload"]
                levels = sample["levels"]
                grid[(delta, vibration)] = sample

                sample_contract_valid = sample_contract_valid and (
                    payload.get("model") == PROPRIOCEPTION_MODEL
                    and payload.get("encoding") == PROPRIOCEPTION_ENCODING
                    and payload.get("claw_position_available") is False
                    and payload.get("stimulation_enabled") is False
                    and payload.get("runtime_transduction_enabled") is False
                    and payload.get("engineering_proxy") is True
                )
                channel_values = [
                    levels["hook_extension"],
                    levels["hook_flexion"],
                    levels["club_motion"],
                    levels["club_vibration"],
                ]
                bounded = bounded and all(0.0 <= value <= 1.0 for value in channel_values)
                mutual_exclusion = mutual_exclusion and not (
                    levels["hook_extension"] > 0.0
                    and levels["hook_flexion"] > 0.0
                )
                club_equals_directional = club_equals_directional and abs(
                    levels["club_motion"]
                    - max(levels["hook_extension"], levels["hook_flexion"])
                ) <= 1e-12
    else:
        sample_contract_valid = False
        bounded = False
        mutual_exclusion = False
        club_equals_directional = False

    neutral_zero = False
    symmetry = False
    monotonic = False
    saturation = False
    vibration_independent_motion = False
    delta_independent_vibration = False

    if grid:
        neutral = grid[(0.0, 0.0)]["levels"]
        neutral_zero = all(
            neutral[name] == 0.0
            for name in (
                "hook_extension",
                "hook_flexion",
                "club_motion",
                "club_vibration",
            )
        )

        magnitudes = [0.25, 0.5, 0.75, 1.0, 2.0]
        symmetry = all(
            abs(
                grid[(magnitude, 0.0)]["levels"]["hook_extension"]
                - grid[(-magnitude, 0.0)]["levels"]["hook_flexion"]
            )
            <= 1e-12
            and grid[(magnitude, 0.0)]["levels"]["hook_flexion"] == 0.0
            and grid[(-magnitude, 0.0)]["levels"]["hook_extension"] == 0.0
            for magnitude in magnitudes
        )

        ordered_magnitudes = [0.0, 0.25, 0.5, 0.75, 1.0, 2.0]
        extension_curve = [
            grid[(magnitude, 0.0)]["levels"]["hook_extension"]
            for magnitude in ordered_magnitudes
        ]
        flexion_curve = [
            grid[(-magnitude, 0.0)]["levels"]["hook_flexion"]
            for magnitude in ordered_magnitudes
        ]
        club_curve = [
            grid[(magnitude, 0.0)]["levels"]["club_motion"]
            for magnitude in ordered_magnitudes
        ]
        monotonic = all(
            curve[index] <= curve[index + 1]
            for curve in (extension_curve, flexion_curve, club_curve)
            for index in range(len(curve) - 1)
        )

        saturation = all(
            grid[(delta, 0.0)]["levels"]["club_motion"] == 1.0
            and max(
                grid[(delta, 0.0)]["levels"]["hook_extension"],
                grid[(delta, 0.0)]["levels"]["hook_flexion"],
            )
            == 1.0
            for delta in (-2.0, -1.0, 1.0, 2.0)
        )

        vibration_independent_motion = all(
            (
                grid[(delta, vibration)]["levels"]["hook_extension"],
                grid[(delta, vibration)]["levels"]["hook_flexion"],
                grid[(delta, vibration)]["levels"]["club_motion"],
            )
            == (
                grid[(delta, 0.0)]["levels"]["hook_extension"],
                grid[(delta, 0.0)]["levels"]["hook_flexion"],
                grid[(delta, 0.0)]["levels"]["club_motion"],
            )
            for delta in EXPECTED_DELTAS
            for vibration in EXPECTED_VIBRATIONS
        )

        delta_independent_vibration = all(
            grid[(delta, vibration)]["levels"]["club_vibration"]
            == grid[(0.0, vibration)]["levels"]["club_vibration"]
            for vibration in EXPECTED_VIBRATIONS
            for delta in EXPECTED_DELTAS
        )

    characterization_gates = {
        "sample_contract_valid": sample_contract_valid,
        "neutral_zero": neutral_zero,
        "hook_mutual_exclusion": mutual_exclusion,
        "directional_magnitude_symmetry": symmetry,
        "club_motion_equals_directional_magnitude": club_equals_directional,
        "bounded_unit_interval": bounded,
        "magnitude_monotonic_nondecreasing": monotonic,
        "saturates_at_unit_magnitude": saturation,
        "vibration_does_not_change_joint_motion_channels": vibration_independent_motion,
        "joint_delta_does_not_change_vibration_channel": delta_independent_vibration,
    }

    passed = all(contract_gates.values()) and all(characterization_gates.values())
    return {
        "schema": REPORT_SCHEMA,
        "status": STATUS if passed else "FAIL",
        "passed": passed,
        "scope": SCOPE,
        "sample_count": len(grid),
        "contract_gates": contract_gates,
        "characterization_gates": characterization_gates,
        "engineering_proxy_only": True,
        "human_diagnostic_or_ci_only": True,
        "biological_current_calibrated": False,
        "biological_latency_calibrated": False,
        "systematic_type_identity_resolved": False,
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
        "--contract",
        default="data/proprioception_engineering_proxy_characterization_v01.json",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    contract = json.loads(Path(args.contract).read_text())
    report = audit_characterization(contract)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
