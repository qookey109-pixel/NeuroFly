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
from .smoke import _neural_decision_verified
from .training import _public_goal_state


SCHEMA = "neurofly-proprioception-self-training-restart-contract-v0.1"
REPORT_SCHEMA = "neurofly-proprioception-self-training-restart-report-v0.1"
STATUS = "REVIEW_REQUIRED"
SCOPE = "production-self-training-orchestration-restart-contract-only"
UPSTREAM_PR = 83
UPSTREAM_HEAD = "fa06b584eb8edd39672a1c4a7aae77613d9a7714"
ACTION_ALPHABET = ("HOLD", "FORWARD", "TURN_LEFT", "TURN_RIGHT")
EXPECTED_INVARIANTS = {
    "production_public_projection_used",
    "production_neural_verification_used",
    "post_restart_neural_proprioception_matches_uninterrupted",
    "post_restart_public_current_proprioception_matches_uninterrupted",
    "post_restart_stable_public_gameplay_state_matches_uninterrupted",
    "temporal_history_is_process_local_after_restart",
    "temporal_sequence_restarts_at_one",
    "temporal_latest_sample_matches_current_handoff",
    "private_checkpoint_state_not_public",
    "human_diagnostics_not_in_neural_context",
    "restored_handoffs_pass_unprivileged_guard",
}
EXPECTED_LIMITATIONS = {
    "actual_malecns_process_restart_executed": False,
    "malecns_brain_checkpoint_equivalence_proven": False,
    "biological_restart_memory_claimed": False,
    "production_orchestration_contract_only": True,
}
EXPECTED_LOCKS = {
    "systematic_type_mapping_exposed",
    "current_calibration_authorized",
    "stimulation_enabled",
    "runtime_transduction_enabled",
    "runtime_gating_authorized",
    "neural_payload_promotion_authorized",
}
_PRIVATE_PUBLIC_TOKENS = (
    "_pending_proprioception",
    "_virtual_body_state",
    "joint_position",
    "joint_phase",
    "joint_delta",
    "motor_execution",
)


class _SyntheticVerifiedMaleCNSBrain:
    """CI-only orchestration fixture.

    It deliberately satisfies the production neural-verification predicate while
    carrying no claim that MaleCNS checkpoint memory itself was restored.
    """

    name = "malecns"

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
        return BrainDecision(
            action=action,
            backend="malecns",
            telemetry={
                "brain_ms": 1.0,
                "compute_seconds": 0.0,
                "total_spikes": 1,
                "memory": {"sha256": "synthetic-orchestration-fixture"},
            },
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text("synthetic-orchestration-fixture\n")


class _StableTrainingEnvironment(GoalMazeEnvironment):
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


def _limitations_exact(payload: Any) -> bool:
    return isinstance(payload, dict) and payload == EXPECTED_LIMITATIONS


def _sequences(contract: dict[str, Any]) -> list[tuple[str, ...]]:
    if contract.get("exhaustive_max_length") != 3:
        return []
    stress = contract.get("stress_sequences")
    if not isinstance(stress, list):
        return []

    sequences: list[tuple[str, ...]] = []
    for length in range(1, 4):
        sequences.extend(itertools.product(ACTION_ALPHABET, repeat=length))

    for raw in stress:
        if (
            not isinstance(raw, list)
            or len(raw) != 5
            or any(action not in ACTION_ALPHABET for action in raw)
        ):
            return []
        sequence = tuple(raw)
        if sequence not in sequences:
            sequences.append(sequence)
    return sequences


def _stable_public_state(public: dict[str, Any]) -> dict[str, Any]:
    """Remove only process-local/time-varying diagnostic surfaces.

    Current receptor diagnostics stay in the comparison. Temporal history is
    intentionally process-local and is validated separately.
    """

    stable = copy.deepcopy(public)
    stable.pop("survival_seconds", None)
    stable.pop("total_active_seconds", None)
    stable.pop("brain", None)

    diagnostics = stable.get("human_diagnostics")
    if isinstance(diagnostics, dict):
        diagnostics.pop("proprioception_temporal", None)
    return stable


def _run_uninterrupted(
    sequence: tuple[str, ...],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    brain = _SyntheticVerifiedMaleCNSBrain(sequence)
    session = TemporalGoalMazeSession(
        brain,
        environment=_StableTrainingEnvironment(),
        world_tick_seconds=3600.0,
    )
    contexts: list[dict[str, Any]] = []
    raw_states: list[dict[str, Any]] = []
    public_states: list[dict[str, Any]] = []

    for _ in sequence:
        raw = session.tick()
        if not _neural_decision_verified(raw):
            raise ValueError("Synthetic production-orchestration state failed neural verification")
        contexts.append(copy.deepcopy(brain.contexts[-1]))
        raw_states.append(copy.deepcopy(raw))
        public_states.append(_public_goal_state(raw))
    return contexts, raw_states, public_states


def audit_self_training_restart_contract(contract: dict[str, Any]) -> dict[str, Any]:
    upstream = contract.get("upstream", {})
    coverage = contract.get("expected_coverage", {})
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
        "proof_limitations_exact": _limitations_exact(contract.get("proof_limitations")),
        "hard_locks_exact": _all_false_exact(contract.get("hard_locks"), EXPECTED_LOCKS),
        "expected_sequence_count_exact": coverage.get("sequence_count") == 92,
        "expected_restart_cases_exact": coverage.get("restart_cases") == 360,
        "expected_step_comparisons_exact": coverage.get("post_restart_step_comparisons")
        == 556,
    }

    sequences = _sequences(contract)
    restart_cases = 0
    post_restart_step_comparisons = 0
    invariants = {key: True for key in EXPECTED_INVARIANTS}
    invariants["production_public_projection_used"] = True
    invariants["production_neural_verification_used"] = True
    first_public_state_mismatch: dict[str, Any] | None = None

    with tempfile.TemporaryDirectory(prefix="neurofly-training-restart-") as tmpdir:
        root = Path(tmpdir)

        for case_index, sequence in enumerate(sequences):
            baseline_contexts, baseline_raw, baseline_public = _run_uninterrupted(sequence)

            for split in range(len(sequence) + 1):
                restart_cases += 1
                checkpoint = root / f"case-{case_index}-{split}.npz"
                maze_path = checkpoint.with_suffix(".maze.json")
                for path in (checkpoint, maze_path):
                    if path.exists():
                        path.unlink()

                prefix_brain = _SyntheticVerifiedMaleCNSBrain(sequence[:split])
                prefix = TemporalGoalMazeSession(
                    prefix_brain,
                    checkpoint=checkpoint,
                    environment=_StableTrainingEnvironment(),
                    checkpoint_every=999999.0,
                    world_tick_seconds=3600.0,
                )
                for _ in range(split):
                    prefix_state = prefix.tick()
                    invariants["production_neural_verification_used"] &= (
                        _neural_decision_verified(prefix_state)
                    )
                    _public_goal_state(prefix_state)
                prefix.save()

                saved_encoded = maze_path.read_text()
                invariants["temporal_history_is_process_local_after_restart"] &= (
                    "proprioception_temporal" not in saved_encoded
                    and "temporal_history" not in saved_encoded
                )

                suffix_brain = _SyntheticVerifiedMaleCNSBrain(sequence[split:])
                restored = TemporalGoalMazeSession(
                    suffix_brain,
                    checkpoint=checkpoint,
                    environment=_StableTrainingEnvironment(),
                    checkpoint_every=999999.0,
                    world_tick_seconds=3600.0,
                )
                initial_history = restored.proprioception_temporal_recorder.snapshot()
                invariants["temporal_history_is_process_local_after_restart"] &= (
                    initial_history["sample_count"] == 0
                    and initial_history["samples"] == []
                )

                for suffix_index, _ in enumerate(sequence[split:]):
                    absolute_index = split + suffix_index
                    raw = restored.tick()
                    context = suffix_brain.contexts[suffix_index]
                    public = _public_goal_state(raw)
                    baseline_context = baseline_contexts[absolute_index]
                    baseline_public_state = baseline_public[absolute_index]

                    post_restart_step_comparisons += 1
                    invariants["production_neural_verification_used"] &= (
                        _neural_decision_verified(raw)
                        and _neural_decision_verified(baseline_raw[absolute_index])
                    )

                    restored_proprioception = context.get("proprioception")
                    baseline_proprioception = baseline_context.get("proprioception")
                    invariants[
                        "post_restart_neural_proprioception_matches_uninterrupted"
                    ] &= restored_proprioception == baseline_proprioception

                    try:
                        if not isinstance(restored_proprioception, dict):
                            raise ValueError("Missing proprioception")
                        assert_unprivileged_agent_input(
                            {"proprioception": restored_proprioception}
                        )
                    except ValueError:
                        invariants["restored_handoffs_pass_unprivileged_guard"] = False

                    public_diag = public.get("human_diagnostics") or {}
                    baseline_diag = baseline_public_state.get("human_diagnostics") or {}
                    invariants[
                        "post_restart_public_current_proprioception_matches_uninterrupted"
                    ] &= (
                        public_diag.get("proprioception")
                        == baseline_diag.get("proprioception")
                    )

                    restored_stable = _stable_public_state(public)
                    baseline_stable = _stable_public_state(baseline_public_state)
                    stable_matches = restored_stable == baseline_stable
                    invariants[
                        "post_restart_stable_public_gameplay_state_matches_uninterrupted"
                    ] &= stable_matches
                    if not stable_matches and first_public_state_mismatch is None:
                        keys = sorted(set(restored_stable) | set(baseline_stable))
                        differing = {
                            key: {
                                "baseline": baseline_stable.get(key),
                                "restored": restored_stable.get(key),
                            }
                            for key in keys
                            if baseline_stable.get(key) != restored_stable.get(key)
                        }
                        first_public_state_mismatch = {
                            "sequence": list(sequence),
                            "split": split,
                            "absolute_index": absolute_index,
                            "differing_top_level_fields": differing,
                        }

                    temporal = public_diag.get("proprioception_temporal")
                    expected_sequence = suffix_index + 1
                    if not isinstance(temporal, dict):
                        invariants["temporal_sequence_restarts_at_one"] = False
                        invariants["temporal_latest_sample_matches_current_handoff"] = False
                    else:
                        samples = temporal.get("samples")
                        invariants["temporal_sequence_restarts_at_one"] &= (
                            temporal.get("sample_count") == expected_sequence
                            and isinstance(samples, list)
                            and len(samples) == expected_sequence
                            and samples[-1].get("sequence") == expected_sequence
                            and samples[0].get("sequence") == 1
                        )
                        current = public_diag.get("proprioception") or {}
                        invariants["temporal_latest_sample_matches_current_handoff"] &= (
                            isinstance(samples, list)
                            and bool(samples)
                            and samples[-1].get("channels") == current.get("channels")
                        )

                    context_encoded = json.dumps(context, sort_keys=True)
                    invariants["human_diagnostics_not_in_neural_context"] &= (
                        "human_diagnostics" not in context
                        and "proprioception_temporal" not in context_encoded
                    )

                    public_encoded = json.dumps(public, sort_keys=True)
                    invariants["private_checkpoint_state_not_public"] &= all(
                        token not in public_encoded for token in _PRIVATE_PUBLIC_TOKENS
                    )

    coverage_gates = {
        "sequence_count_exact": len(sequences) == 92,
        "restart_cases_exact": restart_cases == 360,
        "post_restart_step_comparisons_exact": post_restart_step_comparisons == 556,
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
            "sequence_count": len(sequences),
            "restart_cases": restart_cases,
            "post_restart_step_comparisons": post_restart_step_comparisons,
        },
        "contract_gates": contract_gates,
        "coverage_gates": coverage_gates,
        "invariants": invariants,
        "first_public_state_mismatch": first_public_state_mismatch,
        "actual_malecns_process_restart_executed": False,
        "malecns_brain_checkpoint_equivalence_proven": False,
        "biological_restart_memory_claimed": False,
        "production_orchestration_contract_only": True,
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
        default="data/proprioception_self_training_restart_contract_v01.json",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    contract = json.loads(Path(args.contract).read_text())
    report = audit_self_training_restart_contract(contract)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
