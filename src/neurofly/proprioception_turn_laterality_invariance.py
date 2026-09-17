from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from .proprioception import proprioceptive_channel_levels
from .sensory_contract import assert_unprivileged_agent_input
from .virtual_body import VirtualFeCOJointBody


SCHEMA = "neurofly-proprioception-turn-laterality-invariance-v0.1"
REPORT_SCHEMA = "neurofly-proprioception-turn-laterality-invariance-report-v0.1"
STATUS = "REVIEW_REQUIRED"
SCOPE = "representative-joint-turn-laterality-invariance-only"
EXECUTIONS = ("HOLD", "FORWARD", "TURN_LEFT", "TURN_RIGHT")
SWAP = {
    "HOLD": "HOLD",
    "FORWARD": "FORWARD",
    "TURN_LEFT": "TURN_RIGHT",
    "TURN_RIGHT": "TURN_LEFT",
}
MAX_SEQUENCE_LENGTH = 5
VIBRATION_PROFILES = (
    (0.0,),
    (0.17, 0.83),
)
REQUIRED_PROPERTIES = {
    "receptor_trajectory_invariant_under_turn_swap",
    "private_joint_mechanics_invariant_under_turn_swap",
    "receptor_payload_contains_no_motor_execution_label",
    "receptor_payload_contains_no_private_joint_state",
    "receptor_payload_passes_unprivileged_sensory_guard",
    "turn_laterality_not_recoverable_from_receptor_trajectory",
}
INTERPRETATION = {
    "motor_class_reafference_allowed": True,
    "turn_laterality_privileged_cue_forbidden": True,
    "six_leg_laterality_modeled": False,
    "biological_laterality_claimed": False,
}
HARD_LOCKS = {
    "systematic_type_mapping_exposed",
    "current_calibration_authorized",
    "stimulation_enabled",
    "runtime_transduction_enabled",
    "runtime_gating_authorized",
    "neural_payload_promotion_authorized",
}
FORBIDDEN_RECEPTOR_KEYS = {
    "action",
    "motor_execution",
    "heading",
    "world_velocity",
    "world_displacement",
    "joint_phase",
    "joint_position",
    "joint_delta",
    "mechanical_vibration",
    "reward",
    "desired_action",
    "x",
    "y",
}


def _all_true_exact(payload: Any, expected: set[str]) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload) == expected
        and all(payload[key] is True for key in expected)
    )


def _all_false_exact(payload: Any, expected: set[str]) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload) == expected
        and all(payload[key] is False for key in expected)
    )


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in FORBIDDEN_RECEPTOR_KEYS or _contains_forbidden_key(nested):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _channel_tuple(payload: dict[str, Any]) -> tuple[float, float, float, float]:
    levels = proprioceptive_channel_levels(payload)
    return (
        levels["hook_extension"],
        levels["hook_flexion"],
        levels["club_motion"],
        levels["club_vibration"],
    )


def _sequences(max_length: int) -> Iterable[tuple[str, ...]]:
    for length in range(1, max_length + 1):
        yield from itertools.product(EXECUTIONS, repeat=length)


def _mirrored(sequence: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(SWAP[action] for action in sequence)


def audit_turn_laterality_invariance(contract: dict[str, Any]) -> dict[str, Any]:
    upstream = contract.get("upstream", {})
    contract_gates = {
        "schema_exact": contract.get("schema") == SCHEMA,
        "status_exact": contract.get("status") == STATUS,
        "scope_exact": contract.get("scope") == SCOPE,
        "upstream_pr_exact": upstream.get("pull_request") == 80,
        "upstream_head_exact": upstream.get("head_sha")
        == "99b8596deb1a2b110571a4b1e563ce084614348b",
        "engineering_proxy_characterized": upstream.get("engineering_proxy_characterized")
        is True,
        "execution_alphabet_exact": contract.get("execution_alphabet") == list(EXECUTIONS),
        "laterality_swap_exact": contract.get("laterality_swap") == SWAP,
        "max_sequence_length_exact": contract.get("exhaustive_max_sequence_length")
        == MAX_SEQUENCE_LENGTH,
        "required_properties_exact": _all_true_exact(
            contract.get("required_properties"), REQUIRED_PROPERTIES
        ),
        "interpretation_exact": contract.get("interpretation") == INTERPRETATION,
        "hard_locks_exact": _all_false_exact(contract.get("hard_locks"), HARD_LOCKS),
    }

    receptor_trajectory_invariant = True
    private_joint_mechanics_invariant = True
    no_motor_execution_label = True
    no_private_joint_state = True
    passes_sensory_guard = True
    sequence_count = 0
    trajectory_case_count = 0
    receptor_step_comparisons = 0
    first_failure: dict[str, Any] | None = None

    if all(contract_gates.values()):
        for sequence in _sequences(MAX_SEQUENCE_LENGTH):
            sequence_count += 1
            mirrored = _mirrored(sequence)
            for profile in VIBRATION_PROFILES:
                trajectory_case_count += 1
                left = VirtualFeCOJointBody()
                right = VirtualFeCOJointBody()

                for index, (left_action, right_action) in enumerate(zip(sequence, mirrored)):
                    vibration = profile[index % len(profile)]
                    left_payload = left.advance(
                        left_action,
                        mechanical_vibration=vibration,
                    )
                    right_payload = right.advance(
                        right_action,
                        mechanical_vibration=vibration,
                    )
                    receptor_step_comparisons += 1

                    left_channels = _channel_tuple(left_payload)
                    right_channels = _channel_tuple(right_payload)
                    if left_channels != right_channels:
                        receptor_trajectory_invariant = False
                        if first_failure is None:
                            first_failure = {
                                "kind": "receptor-trajectory-mismatch",
                                "sequence": list(sequence),
                                "mirrored_sequence": list(mirrored),
                                "step_index": index,
                                "left_channels": list(left_channels),
                                "right_channels": list(right_channels),
                            }

                    same_private_mechanics = (
                        left.joint_phase == right.joint_phase
                        and left.joint_position == right.joint_position
                        and left.step_index == right.step_index
                    )
                    if not same_private_mechanics:
                        private_joint_mechanics_invariant = False
                        if first_failure is None:
                            first_failure = {
                                "kind": "private-joint-mechanics-mismatch",
                                "sequence": list(sequence),
                                "mirrored_sequence": list(mirrored),
                                "step_index": index,
                            }

                    for payload in (left_payload, right_payload):
                        if _contains_forbidden_key(payload):
                            no_motor_execution_label = no_motor_execution_label and (
                                "motor_execution" not in payload and "action" not in payload
                            )
                            no_private_joint_state = False
                            if first_failure is None:
                                first_failure = {
                                    "kind": "forbidden-receptor-field",
                                    "sequence": list(sequence),
                                    "step_index": index,
                                }
                        try:
                            assert_unprivileged_agent_input({"proprioception": payload})
                        except ValueError:
                            passes_sensory_guard = False
                            if first_failure is None:
                                first_failure = {
                                    "kind": "sensory-guard-rejection",
                                    "sequence": list(sequence),
                                    "step_index": index,
                                }
    else:
        receptor_trajectory_invariant = False
        private_joint_mechanics_invariant = False
        no_motor_execution_label = False
        no_private_joint_state = False
        passes_sensory_guard = False

    # Check the two direct motor-label keys independently rather than relying on
    # the larger private-state set above.
    if all(contract_gates.values()):
        probe = VirtualFeCOJointBody().advance("TURN_LEFT")
        no_motor_execution_label = no_motor_execution_label and not any(
            key in probe for key in ("action", "motor_execution")
        )

    turn_laterality_not_recoverable = (
        receptor_trajectory_invariant
        and private_joint_mechanics_invariant
        and no_motor_execution_label
        and no_private_joint_state
        and passes_sensory_guard
    )

    invariance_gates = {
        "receptor_trajectory_invariant_under_turn_swap": receptor_trajectory_invariant,
        "private_joint_mechanics_invariant_under_turn_swap": private_joint_mechanics_invariant,
        "receptor_payload_contains_no_motor_execution_label": no_motor_execution_label,
        "receptor_payload_contains_no_private_joint_state": no_private_joint_state,
        "receptor_payload_passes_unprivileged_sensory_guard": passes_sensory_guard,
        "turn_laterality_not_recoverable_from_receptor_trajectory": turn_laterality_not_recoverable,
    }

    passed = all(contract_gates.values()) and all(invariance_gates.values())
    return {
        "schema": REPORT_SCHEMA,
        "status": STATUS if passed else "FAIL",
        "passed": passed,
        "scope": SCOPE,
        "sequence_count": sequence_count,
        "vibration_profile_count": len(VIBRATION_PROFILES),
        "trajectory_case_count": trajectory_case_count,
        "receptor_step_comparisons": receptor_step_comparisons,
        "contract_gates": contract_gates,
        "invariance_gates": invariance_gates,
        "first_failure": first_failure,
        "motor_class_reafference_allowed": True,
        "turn_laterality_privileged_cue_forbidden": True,
        "six_leg_laterality_modeled": False,
        "biological_laterality_claimed": False,
        "systematic_type_mapping_exposed": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "runtime_gating_authorized": False,
        "neural_payload_promotion_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        default="data/proprioception_turn_laterality_invariance_v01.json",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    contract = json.loads(Path(args.contract).read_text())
    report = audit_turn_laterality_invariance(contract)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
