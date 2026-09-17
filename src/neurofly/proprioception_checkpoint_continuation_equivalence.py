from __future__ import annotations

import argparse
import copy
import itertools
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from .proprioception import proprioceptive_channel_levels
from .sensory_contract import assert_unprivileged_agent_input
from .virtual_body import VirtualFeCOJointBody


SCHEMA = "neurofly-proprioception-checkpoint-continuation-equivalence-v0.1"
REPORT_SCHEMA = "neurofly-proprioception-checkpoint-continuation-equivalence-report-v0.1"
STATUS = "REVIEW_REQUIRED"
SCOPE = "representative-joint-checkpoint-continuation-only"
EXECUTIONS = ("HOLD", "FORWARD", "TURN_LEFT", "TURN_RIGHT")
MAX_SEQUENCE_LENGTH = 5
VIBRATION_PROFILES = (
    (0.0,),
    (0.17, 0.83),
)
REQUIRED_PROPERTIES = {
    "restored_private_state_matches_checkpoint",
    "post_restore_receptor_continuation_matches_uninterrupted",
    "post_restore_private_mechanics_match_uninterrupted",
    "checkpoint_boundary_injects_no_extra_receptor_event",
    "receptor_payload_passes_unprivileged_sensory_guard",
}
INTERPRETATION = {
    "checkpoint_is_private_state_only": True,
    "checkpoint_is_not_neural_input": True,
    "history_replay_into_neural_payload": False,
    "biological_memory_claimed": False,
}
HARD_LOCKS = {
    "systematic_type_mapping_exposed",
    "current_calibration_authorized",
    "stimulation_enabled",
    "runtime_transduction_enabled",
    "runtime_gating_authorized",
    "neural_payload_promotion_authorized",
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


def _sequences(max_length: int) -> Iterable[tuple[str, ...]]:
    for length in range(1, max_length + 1):
        yield from itertools.product(EXECUTIONS, repeat=length)


def _channels(payload: dict[str, Any]) -> tuple[float, float, float, float]:
    levels = proprioceptive_channel_levels(payload)
    return (
        levels["hook_extension"],
        levels["hook_flexion"],
        levels["club_motion"],
        levels["club_vibration"],
    )


def _private_mechanics(body: VirtualFeCOJointBody) -> tuple[float, float, int]:
    return (body.joint_phase, body.joint_position, body.step_index)


def audit_checkpoint_continuation_equivalence(
    contract: dict[str, Any],
) -> dict[str, Any]:
    upstream = contract.get("upstream", {})
    contract_gates = {
        "schema_exact": contract.get("schema") == SCHEMA,
        "status_exact": contract.get("status") == STATUS,
        "scope_exact": contract.get("scope") == SCOPE,
        "upstream_pr_exact": upstream.get("pull_request") == 81,
        "upstream_head_exact": upstream.get("head_sha")
        == "1d01ab056f9053ab7d4986db55ea1f467f87dadd",
        "turn_laterality_invariance_verified": upstream.get(
            "turn_laterality_invariance_verified"
        )
        is True,
        "execution_alphabet_exact": contract.get("execution_alphabet") == list(EXECUTIONS),
        "max_sequence_length_exact": contract.get("exhaustive_max_sequence_length")
        == MAX_SEQUENCE_LENGTH,
        "checkpoint_every_split_point": contract.get("checkpoint_every_split_point")
        is True,
        "required_properties_exact": _all_true_exact(
            contract.get("required_properties"), REQUIRED_PROPERTIES
        ),
        "interpretation_exact": contract.get("interpretation") == INTERPRETATION,
        "hard_locks_exact": _all_false_exact(contract.get("hard_locks"), HARD_LOCKS),
    }

    restored_state_matches = True
    receptor_continuation_matches = True
    private_mechanics_match = True
    no_extra_receptor_event = True
    sensory_guard_passes = True
    sequence_count = 0
    checkpoint_case_count = 0
    continuation_step_comparisons = 0
    first_failure: dict[str, Any] | None = None

    if all(contract_gates.values()):
        for sequence in _sequences(MAX_SEQUENCE_LENGTH):
            sequence_count += 1
            for profile in VIBRATION_PROFILES:
                reference = VirtualFeCOJointBody()
                reference_channels: list[tuple[float, float, float, float]] = []
                reference_states: list[tuple[float, float, int]] = [
                    _private_mechanics(reference)
                ]

                for index, action in enumerate(sequence):
                    vibration = profile[index % len(profile)]
                    payload = reference.advance(
                        action,
                        mechanical_vibration=vibration,
                    )
                    reference_channels.append(_channels(payload))
                    reference_states.append(_private_mechanics(reference))

                for split in range(len(sequence) + 1):
                    checkpoint_case_count += 1
                    prefix = VirtualFeCOJointBody()
                    for index in range(split):
                        vibration = profile[index % len(profile)]
                        prefix.advance(
                            sequence[index],
                            mechanical_vibration=vibration,
                        )

                    snapshot = prefix.persistence_snapshot()
                    restored = VirtualFeCOJointBody()
                    restore_result = restored.restore(copy.deepcopy(snapshot))

                    if restored.persistence_snapshot() != snapshot:
                        restored_state_matches = False
                        if first_failure is None:
                            first_failure = {
                                "kind": "restored-state-mismatch",
                                "sequence": list(sequence),
                                "split": split,
                                "profile": list(profile),
                            }

                    if restore_result is not None:
                        no_extra_receptor_event = False
                        if first_failure is None:
                            first_failure = {
                                "kind": "restore-returned-receptor-event",
                                "sequence": list(sequence),
                                "split": split,
                                "profile": list(profile),
                            }

                    if _private_mechanics(restored) != reference_states[split]:
                        private_mechanics_match = False
                        if first_failure is None:
                            first_failure = {
                                "kind": "restored-private-mechanics-mismatch",
                                "sequence": list(sequence),
                                "split": split,
                                "profile": list(profile),
                            }

                    for index in range(split, len(sequence)):
                        vibration = profile[index % len(profile)]
                        resumed_payload = restored.advance(
                            sequence[index],
                            mechanical_vibration=vibration,
                        )
                        continuation_step_comparisons += 1

                        resumed_channels = _channels(resumed_payload)
                        if resumed_channels != reference_channels[index]:
                            receptor_continuation_matches = False
                            if first_failure is None:
                                first_failure = {
                                    "kind": "receptor-continuation-mismatch",
                                    "sequence": list(sequence),
                                    "split": split,
                                    "step_index": index,
                                    "profile": list(profile),
                                    "expected": list(reference_channels[index]),
                                    "actual": list(resumed_channels),
                                }

                        if _private_mechanics(restored) != reference_states[index + 1]:
                            private_mechanics_match = False
                            if first_failure is None:
                                first_failure = {
                                    "kind": "post-restore-private-mechanics-mismatch",
                                    "sequence": list(sequence),
                                    "split": split,
                                    "step_index": index,
                                    "profile": list(profile),
                                }

                        try:
                            assert_unprivileged_agent_input(
                                {"proprioception": resumed_payload}
                            )
                        except ValueError:
                            sensory_guard_passes = False
                            if first_failure is None:
                                first_failure = {
                                    "kind": "sensory-guard-rejection",
                                    "sequence": list(sequence),
                                    "split": split,
                                    "step_index": index,
                                    "profile": list(profile),
                                }
    else:
        restored_state_matches = False
        receptor_continuation_matches = False
        private_mechanics_match = False
        no_extra_receptor_event = False
        sensory_guard_passes = False

    continuation_gates = {
        "restored_private_state_matches_checkpoint": restored_state_matches,
        "post_restore_receptor_continuation_matches_uninterrupted": receptor_continuation_matches,
        "post_restore_private_mechanics_match_uninterrupted": private_mechanics_match,
        "checkpoint_boundary_injects_no_extra_receptor_event": no_extra_receptor_event,
        "receptor_payload_passes_unprivileged_sensory_guard": sensory_guard_passes,
    }

    passed = all(contract_gates.values()) and all(continuation_gates.values())
    return {
        "schema": REPORT_SCHEMA,
        "status": STATUS if passed else "FAIL",
        "passed": passed,
        "scope": SCOPE,
        "sequence_count": sequence_count,
        "vibration_profile_count": len(VIBRATION_PROFILES),
        "checkpoint_case_count": checkpoint_case_count,
        "continuation_step_comparisons": continuation_step_comparisons,
        "contract_gates": contract_gates,
        "continuation_gates": continuation_gates,
        "first_failure": first_failure,
        "checkpoint_is_private_state_only": True,
        "checkpoint_is_not_neural_input": True,
        "history_replay_into_neural_payload": False,
        "biological_memory_claimed": False,
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
        default="data/proprioception_checkpoint_continuation_equivalence_v01.json",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    contract = json.loads(Path(args.contract).read_text())
    report = audit_checkpoint_continuation_equivalence(contract)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
