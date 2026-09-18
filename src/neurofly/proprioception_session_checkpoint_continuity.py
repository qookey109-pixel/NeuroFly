from __future__ import annotations

import argparse
import copy
import itertools
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

from .brain_runtime import BrainDecision
from .goal_training import GoalMazeEnvironment
from .proprioception_temporal_runtime import TemporalGoalMazeSession
from .sensory_contract import assert_unprivileged_agent_input


SCHEMA = "neurofly-proprioception-session-checkpoint-continuity-v0.1"
REPORT_SCHEMA = "neurofly-proprioception-session-checkpoint-continuity-report-v0.1"
STATUS = "REVIEW_REQUIRED"
SCOPE = "session-level-proprioception-checkpoint-continuity-only"
UPSTREAM_PR = 82
UPSTREAM_HEAD = "0ff85ce5396f500307429fd1d0f023c45e209a54"
ACTION_ALPHABET = ("HOLD", "FORWARD", "TURN_LEFT", "TURN_RIGHT")
EXPECTED_INVARIANTS = {
    "pending_proprioception_persisted_exactly",
    "virtual_body_state_persisted_exactly",
    "restored_handoff_matches_uninterrupted",
    "restored_body_continuation_matches_uninterrupted",
    "temporal_history_not_persisted",
    "last_observed_diagnostics_not_persisted",
    "restore_emits_no_receptor_event",
    "restored_recorder_restarts_from_empty",
    "restored_recorder_restarts_sequence_at_one",
    "human_diagnostics_never_enter_neural_context",
    "restored_handoffs_pass_unprivileged_guard",
}
EXPECTED_LOCKS = {
    "systematic_type_mapping_exposed",
    "current_calibration_authorized",
    "stimulation_enabled",
    "runtime_transduction_enabled",
    "runtime_gating_authorized",
    "neural_payload_promotion_authorized",
}


class _AuditBrain:
    name = "checkpoint-continuity-audit"

    def __init__(self, actions: Iterable[str]) -> None:
        self.actions = list(actions)
        self.contexts: list[dict[str, Any]] = []

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision:
        self.contexts.append(copy.deepcopy({} if context is None else context))
        action = self.actions.pop(0) if self.actions else "HOLD"
        return BrainDecision(action=action, backend=self.name, telemetry={})

    def save(self, path: str | Path) -> None:
        Path(path).write_text("checkpoint-continuity-audit-brain\n")


class _AuditEnvironment(GoalMazeEnvironment):
    def __init__(self) -> None:
        super().__init__(seed=109)
        for y in range(1, self.rows - 1):
            for x in range(1, self.cols - 1):
                self.grid[y][x] = " "
        self.fly = {"x": self.cols // 2, "y": self.rows // 2, "dir": "RIGHT"}
        self.enemies = [{"x": self.cols - 2, "y": self.rows - 2}]

    def render_rgb(self, *, width: int = 320, height: int = 180) -> Any:
        return [[[0, 0, 0]]]


def _all_true_exact(payload: Any, keys: set[str]) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload) == keys
        and all(payload[key] is True for key in keys)
    )


def _all_false_exact(payload: Any, keys: set[str]) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload) == keys
        and all(payload[key] is False for key in keys)
    )


def _sequences(contract: dict[str, Any]) -> list[tuple[str, ...]]:
    max_length = contract.get("exhaustive_max_length")
    stress = contract.get("stress_sequences")
    if max_length != 3 or not isinstance(stress, list):
        return []

    sequences: list[tuple[str, ...]] = []
    for length in range(1, max_length + 1):
        sequences.extend(itertools.product(ACTION_ALPHABET, repeat=length))

    for item in stress:
        if (
            not isinstance(item, list)
            or len(item) != 5
            or any(action not in ACTION_ALPHABET for action in item)
        ):
            return []
        sequence = tuple(item)
        if sequence not in sequences:
            sequences.append(sequence)
    return sequences


def _run_uninterrupted(
    sequence: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    brain = _AuditBrain(sequence)
    session = TemporalGoalMazeSession(
        brain,
        environment=_AuditEnvironment(),
        world_tick_seconds=3600.0,
    )
    pending_after: list[dict[str, Any]] = []
    body_after: list[dict[str, Any]] = []
    for _ in sequence:
        session.tick()
        pending_after.append(copy.deepcopy(session.pending_proprioception))
        body_after.append(copy.deepcopy(session.virtual_body.persistence_snapshot()))
    return brain.contexts, pending_after, body_after


def audit_session_checkpoint_continuity(contract: dict[str, Any]) -> dict[str, Any]:
    upstream = contract.get("upstream", {})
    expected_coverage = contract.get("expected_coverage", {})
    contract_gates = {
        "schema_exact": contract.get("schema") == SCHEMA,
        "status_exact": contract.get("status") == STATUS,
        "scope_exact": contract.get("scope") == SCOPE,
        "upstream_pr_exact": upstream.get("pull_request") == UPSTREAM_PR,
        "upstream_head_exact": upstream.get("head_sha") == UPSTREAM_HEAD,
        "action_alphabet_exact": contract.get("action_alphabet") == list(ACTION_ALPHABET),
        "exhaustive_max_length_exact": contract.get("exhaustive_max_length") == 3,
        "required_invariants_exact": _all_true_exact(
            contract.get("required_invariants"), EXPECTED_INVARIANTS
        ),
        "hard_locks_exact": _all_false_exact(contract.get("hard_locks"), EXPECTED_LOCKS),
        "expected_sequence_count_exact": expected_coverage.get("sequence_count") == 92,
        "expected_checkpoint_cases_exact": expected_coverage.get("checkpoint_restore_cases")
        == 360,
        "expected_handoff_comparisons_exact": expected_coverage.get(
            "continuation_handoff_comparisons"
        )
        == 556,
    }

    sequences = _sequences(contract)
    sequence_count = len(sequences)
    checkpoint_cases = 0
    continuation_comparisons = 0

    invariants = {key: True for key in EXPECTED_INVARIANTS}

    with tempfile.TemporaryDirectory(prefix="neurofly-session-checkpoint-") as tmpdir:
        root = Path(tmpdir)

        for case_index, sequence in enumerate(sequences):
            baseline_contexts, baseline_pending, baseline_body = _run_uninterrupted(sequence)

            for split in range(len(sequence) + 1):
                checkpoint_cases += 1
                checkpoint = root / f"case-{case_index}-{split}.npz"
                state_path = checkpoint.with_suffix(".maze.json")
                if checkpoint.exists():
                    checkpoint.unlink()
                if state_path.exists():
                    state_path.unlink()

                prefix_brain = _AuditBrain(sequence[:split])
                prefix_session = TemporalGoalMazeSession(
                    prefix_brain,
                    checkpoint=checkpoint,
                    environment=_AuditEnvironment(),
                    world_tick_seconds=3600.0,
                )
                for _ in range(split):
                    prefix_session.tick()

                prefix_pending = copy.deepcopy(prefix_session.pending_proprioception)
                prefix_body = copy.deepcopy(prefix_session.virtual_body.persistence_snapshot())
                prefix_history = prefix_session.proprioception_temporal_recorder.snapshot()
                if prefix_history["sample_count"] != split:
                    invariants["restore_emits_no_receptor_event"] = False

                prefix_session.save()
                saved = json.loads(state_path.read_text())
                encoded = json.dumps(saved, sort_keys=True)

                invariants["pending_proprioception_persisted_exactly"] &= (
                    saved.get("_pending_proprioception") == prefix_pending
                )
                invariants["virtual_body_state_persisted_exactly"] &= (
                    saved.get("_virtual_body_state") == prefix_body
                )
                invariants["temporal_history_not_persisted"] &= (
                    "proprioception_temporal" not in encoded
                    and "temporal_history" not in encoded
                )
                invariants["last_observed_diagnostics_not_persisted"] &= (
                    "last_observed_proprioception" not in encoded
                    and "human_diagnostics" not in encoded
                )

                suffix_brain = _AuditBrain(sequence[split:])
                restored = TemporalGoalMazeSession(
                    suffix_brain,
                    checkpoint=checkpoint,
                    environment=_AuditEnvironment(),
                    world_tick_seconds=3600.0,
                )

                invariants["pending_proprioception_persisted_exactly"] &= (
                    restored.pending_proprioception == prefix_pending
                )
                invariants["virtual_body_state_persisted_exactly"] &= (
                    restored.virtual_body.persistence_snapshot() == prefix_body
                )

                restored_history = restored.proprioception_temporal_recorder.snapshot()
                invariants["restored_recorder_restarts_from_empty"] &= (
                    restored_history["sample_count"] == 0
                    and restored_history["samples"] == []
                )
                invariants["restore_emits_no_receptor_event"] &= (
                    restored_history["sample_count"] == 0
                )

                for suffix_index, _ in enumerate(sequence[split:]):
                    restored.tick()
                    absolute_index = split + suffix_index
                    continuation_comparisons += 1

                    restored_context = suffix_brain.contexts[suffix_index]
                    baseline_context = baseline_contexts[absolute_index]
                    restored_proprioception = restored_context.get("proprioception")
                    baseline_proprioception = baseline_context.get("proprioception")

                    invariants["restored_handoff_matches_uninterrupted"] &= (
                        restored_proprioception == baseline_proprioception
                    )
                    invariants["restored_body_continuation_matches_uninterrupted"] &= (
                        restored.pending_proprioception == baseline_pending[absolute_index]
                        and restored.virtual_body.persistence_snapshot()
                        == baseline_body[absolute_index]
                    )

                    context_encoded = json.dumps(restored_context, sort_keys=True)
                    invariants["human_diagnostics_never_enter_neural_context"] &= (
                        "human_diagnostics" not in restored_context
                        and "proprioception_temporal" not in context_encoded
                        and "temporal_history" not in context_encoded
                    )

                    try:
                        if not isinstance(restored_proprioception, dict):
                            raise ValueError("Missing restored proprioception")
                        assert_unprivileged_agent_input(
                            {"proprioception": restored_proprioception}
                        )
                    except ValueError:
                        invariants["restored_handoffs_pass_unprivileged_guard"] = False

                    history = restored.proprioception_temporal_recorder.snapshot()
                    expected_sequence = suffix_index + 1
                    invariants["restored_recorder_restarts_sequence_at_one"] &= (
                        history["sample_count"] == expected_sequence
                        and history["samples"][-1]["sequence"] == expected_sequence
                        and history["samples"][-1]["channels"]
                        == restored_proprioception["channels"]
                    )

    coverage_gates = {
        "sequence_count_exact": sequence_count == 92,
        "checkpoint_restore_cases_exact": checkpoint_cases == 360,
        "continuation_handoff_comparisons_exact": continuation_comparisons == 556,
    }

    passed = (
        all(contract_gates.values())
        and all(coverage_gates.values())
        and all(invariants.values())
    )

    return {
        "schema": REPORT_SCHEMA,
        "status": STATUS if passed else "FAIL",
        "passed": passed,
        "scope": SCOPE,
        "coverage": {
            "sequence_count": sequence_count,
            "checkpoint_restore_cases": checkpoint_cases,
            "continuation_handoff_comparisons": continuation_comparisons,
        },
        "contract_gates": contract_gates,
        "coverage_gates": coverage_gates,
        "invariants": invariants,
        "temporal_history_persistence_enabled": False,
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
        default="data/proprioception_session_checkpoint_continuity_v01.json",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    contract = json.loads(Path(args.contract).read_text())
    report = audit_session_checkpoint_continuity(contract)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
