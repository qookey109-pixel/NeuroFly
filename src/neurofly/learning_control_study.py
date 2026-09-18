from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import shutil
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from .brain_runtime import BrainDecision, MaleCNSBrain
from .goal_training import GoalMazeEnvironment, GoalMazeSession
from .smoke import _digest_json, _neural_decision_verified


CONTRACT_SCHEMA = "neurofly-learning-control-study-v0.1"
RECEIPT_SCHEMA = "neurofly-learning-control-study-receipt-v0.1"
STATUS = "EXECUTION_REQUIRED"
SCOPE = "real-malecns-controlled-learning-evaluation"

EXPECTED_ARMS = (
    ("learning_true", True, "normal", "true"),
    ("frozen_true", False, "normal", "true"),
    ("learning_scrambled", True, "normal", "scrambled"),
    ("learning_sensory_off", True, "off", "true"),
)
EXPECTED_HELD_OUT_SEEDS = (701, 709, 719)
EXPECTED_METRICS = (
    "mean_total_reward",
    "mean_total_clears",
    "mean_total_food",
    "mean_total_deaths",
    "mean_hold_fraction",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _blank_frame(frame: Any) -> Any:
    try:
        import numpy as np

        array = np.asarray(frame)
        if array.ndim != 3 or array.shape[2] != 3:
            raise ValueError("sensory-off control requires HxWx3 frame")
        return np.zeros_like(array, dtype=np.uint8)
    except ImportError:
        pass

    if (
        isinstance(frame, list)
        and frame
        and isinstance(frame[0], list)
        and frame[0]
        and isinstance(frame[0][0], list)
    ):
        return [
            [[0 for _ in pixel] for pixel in row]
            for row in frame
        ]
    raise RuntimeError("Unable to construct sensory-off control frame")


class ControlledBrain:
    """Transform study inputs while leaving the underlying brain decision intact."""

    name = "malecns"

    def __init__(
        self,
        inner: Any,
        *,
        sensory_mode: str,
        reinforcement_mode: str,
        scramble_seed: int,
    ) -> None:
        if sensory_mode not in {"normal", "off"}:
            raise ValueError("Unsupported sensory_mode")
        if reinforcement_mode not in {"true", "scrambled", "none"}:
            raise ValueError("Unsupported reinforcement_mode")
        self.inner = inner
        self.sensory_mode = sensory_mode
        self.reinforcement_mode = reinforcement_mode
        self.rng = random.Random(int(scramble_seed))
        self.steps = 0
        self.delivered_reinforcement = Counter()

    def _reinforcement(self, incoming: str) -> str:
        if incoming not in {"none", "reward", "aversive"}:
            raise ValueError("Unsupported incoming reinforcement")
        if self.reinforcement_mode == "true":
            return incoming
        if self.reinforcement_mode == "none":
            return "none"

        # Deterministic synthetic reinforcement, independent of task outcome.
        roll = self.rng.randrange(20)
        if roll < 14:
            return "none"
        if roll < 17:
            return "reward"
        return "aversive"

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision:
        self.steps += 1
        delivered = self._reinforcement(reinforcement)
        self.delivered_reinforcement[delivered] += 1

        transformed_frame = frame
        transformed_context = context
        if self.sensory_mode == "off":
            transformed_frame = _blank_frame(frame)
            transformed_context = {}

        return self.inner.decide(
            transformed_frame,
            delivered,
            context=transformed_context,
        )

    def save(self, path: str | Path) -> None:
        self.inner.save(path)


def _contract_arms(contract: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    arms = contract.get("arms")
    if not isinstance(arms, list):
        return ()
    normalized = []
    for arm in arms:
        if not isinstance(arm, dict):
            return ()
        normalized.append(
            (
                arm.get("name"),
                arm.get("learning"),
                arm.get("sensory_mode"),
                arm.get("reinforcement_mode"),
            )
        )
    return tuple(normalized)


def validate_contract(contract: dict[str, Any]) -> dict[str, bool]:
    training = contract.get("training") or {}
    evaluation = contract.get("evaluation") or {}
    required = contract.get("required_evidence") or {}
    limits = contract.get("claim_limits") or {}

    return {
        "schema_exact": contract.get("schema") == CONTRACT_SCHEMA,
        "status_exact": contract.get("status") == STATUS,
        "scope_exact": contract.get("scope") == SCOPE,
        "arms_exact": _contract_arms(contract) == EXPECTED_ARMS,
        "training_seed_exact": training.get("seed") == 109,
        "training_default_steps_positive": int(training.get("default_steps") or 0) > 0,
        "evaluation_learning_disabled": evaluation.get("learning") is False,
        "evaluation_reinforcement_disabled": evaluation.get("reinforcement_mode") == "none",
        "evaluation_normal_sensory": evaluation.get("sensory_mode") == "normal",
        "held_out_seeds_exact": tuple(evaluation.get("held_out_seeds") or ())
        == EXPECTED_HELD_OUT_SEEDS,
        "evaluation_default_steps_positive": int(
            evaluation.get("default_steps_per_seed") or 0
        ) > 0,
        "metrics_exact": tuple(contract.get("primary_descriptive_metrics") or ())
        == EXPECTED_METRICS,
        "required_evidence_all_true": (
            isinstance(required, dict)
            and bool(required)
            and all(value is True for value in required.values())
        ),
        "claim_limits_all_false": (
            isinstance(limits, dict)
            and set(limits)
            == {
                "learning_validated",
                "generalization_validated",
                "causal_learning_claim_authorized",
                "behavioral_promotion_authorized",
                "production_checkpoint_mutated",
            }
            and all(value is False for value in limits.values())
        ),
    }


def _state_metrics(states: list[dict[str, Any]]) -> dict[str, Any]:
    if not states:
        raise ValueError("No states to summarize")

    action_counts = Counter(
        str(state.get("decision_action") or state.get("last_action") or "UNKNOWN")
        for state in states
    )
    rewards = [float(state.get("last_reward") or 0.0) for state in states]
    final = states[-1]
    spikes = []
    for state in states:
        telemetry = ((state.get("brain") or {}).get("telemetry") or {})
        try:
            spikes.append(int(telemetry.get("total_spikes") or 0))
        except (TypeError, ValueError, OverflowError):
            spikes.append(0)

    return {
        "steps": len(states),
        "total_reward": round(sum(rewards), 8),
        "total_clears": int(final.get("total_clears") or 0),
        "total_food": int(final.get("total_food") or 0),
        "total_deaths": int(final.get("total_deaths") or 0),
        "hold_fraction": round(action_counts.get("HOLD", 0) / len(states), 8),
        "action_counts": dict(sorted(action_counts.items())),
        "mean_total_spikes": round(mean(spikes), 8),
        "neural_activity_verified": all(
            _neural_decision_verified(state) for state in states
        ),
    }


def _aggregate_evaluations(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    if not per_seed:
        raise ValueError("No held-out evaluations")

    return {
        "mean_total_reward": round(
            mean(item["metrics"]["total_reward"] for item in per_seed), 8
        ),
        "mean_total_clears": round(
            mean(item["metrics"]["total_clears"] for item in per_seed), 8
        ),
        "mean_total_food": round(
            mean(item["metrics"]["total_food"] for item in per_seed), 8
        ),
        "mean_total_deaths": round(
            mean(item["metrics"]["total_deaths"] for item in per_seed), 8
        ),
        "mean_hold_fraction": round(
            mean(item["metrics"]["hold_fraction"] for item in per_seed), 8
        ),
    }


def descriptive_effects(arm_results: dict[str, Any]) -> dict[str, Any]:
    treatment = arm_results["learning_true"]["evaluation"]["aggregate"]
    effects: dict[str, Any] = {}

    for control in ("frozen_true", "learning_scrambled", "learning_sensory_off"):
        reference = arm_results[control]["evaluation"]["aggregate"]
        effects[f"learning_true_minus_{control}"] = {
            metric: round(float(treatment[metric]) - float(reference[metric]), 8)
            for metric in EXPECTED_METRICS
        }
    return effects


def _run_steps(session: GoalMazeSession, steps: int) -> list[dict[str, Any]]:
    states = []
    for _ in range(steps):
        state = session.tick()
        if not _neural_decision_verified(state):
            raise RuntimeError("MaleCNS decision lacks verifiable neural activity")
        states.append(copy.deepcopy(state))
    return states


def _run_training_arm(
    *,
    arm_name: str,
    learning: bool,
    sensory_mode: str,
    reinforcement_mode: str,
    initial_checkpoint: Path,
    arm_checkpoint: Path,
    train_seed: int,
    train_steps: int,
    scramble_seed: int,
) -> dict[str, Any]:
    shutil.copy2(initial_checkpoint, arm_checkpoint)
    start_sha = _sha256_file(arm_checkpoint)

    inner = MaleCNSBrain(
        checkpoint=arm_checkpoint,
        learning=learning,
    )
    if bool(inner.learning) is not bool(learning):
        raise RuntimeError("MaleCNS learning mode mismatch")
    if bool(inner.brain.weights_frozen) is not (not learning):
        raise RuntimeError("MaleCNS weights_frozen state mismatch")

    controlled = ControlledBrain(
        inner,
        sensory_mode=sensory_mode,
        reinforcement_mode=reinforcement_mode,
        scramble_seed=scramble_seed,
    )
    session = GoalMazeSession(
        controlled,
        environment=GoalMazeEnvironment(seed=train_seed),
        checkpoint=None,
        world_tick_seconds=3600.0,
    )
    states = _run_steps(session, train_steps)
    controlled.save(arm_checkpoint)

    return {
        "arm": arm_name,
        "learning": learning,
        "sensory_mode": sensory_mode,
        "reinforcement_mode": reinforcement_mode,
        "initial_checkpoint_sha256": start_sha,
        "arm_checkpoint_path": str(arm_checkpoint),
        "post_training_checkpoint_sha256": _sha256_file(arm_checkpoint),
        "delivered_reinforcement": dict(
            sorted(controlled.delivered_reinforcement.items())
        ),
        "training_metrics": _state_metrics(states),
    }


def _evaluate_arm(
    *,
    arm_checkpoint: Path,
    held_out_seeds: tuple[int, ...],
    eval_steps: int,
) -> dict[str, Any]:
    per_seed = []

    for seed in held_out_seeds:
        inner = MaleCNSBrain(
            checkpoint=arm_checkpoint,
            learning=False,
        )
        if inner.learning or not inner.brain.weights_frozen:
            raise RuntimeError("Held-out evaluation must run frozen")

        controlled = ControlledBrain(
            inner,
            sensory_mode="normal",
            reinforcement_mode="none",
            scramble_seed=0,
        )
        session = GoalMazeSession(
            controlled,
            environment=GoalMazeEnvironment(seed=seed),
            checkpoint=None,
            world_tick_seconds=3600.0,
        )
        states = _run_steps(session, eval_steps)
        per_seed.append(
            {
                "seed": seed,
                "metrics": _state_metrics(states),
                "delivered_reinforcement": dict(
                    sorted(controlled.delivered_reinforcement.items())
                ),
            }
        )

    return {
        "held_out_seeds": list(held_out_seeds),
        "steps_per_seed": eval_steps,
        "learning": False,
        "reinforcement_mode": "none",
        "sensory_mode": "normal",
        "per_seed": per_seed,
        "aggregate": _aggregate_evaluations(per_seed),
    }


def run_learning_control_study(
    *,
    contract_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
    train_steps: int | None = None,
    eval_steps: int | None = None,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text())
    contract_gates = validate_contract(contract)
    if not all(contract_gates.values()):
        raise ValueError("Learning control study contract failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)

    training = contract["training"]
    evaluation = contract["evaluation"]
    train_steps = int(train_steps or training["default_steps"])
    eval_steps = int(eval_steps or evaluation["default_steps_per_seed"])
    if train_steps < 1 or eval_steps < 1:
        raise ValueError("Study steps must be >= 1")

    output_dir.mkdir(parents=True, exist_ok=True)
    base_sha = _sha256_file(base_checkpoint)
    held_out_seeds = tuple(int(seed) for seed in evaluation["held_out_seeds"])

    arm_results: dict[str, Any] = {}
    initial_hashes = []

    for index, (name, learning, sensory_mode, reinforcement_mode) in enumerate(
        EXPECTED_ARMS
    ):
        arm_checkpoint = output_dir / f"{name}.npz"
        training_result = _run_training_arm(
            arm_name=name,
            learning=bool(learning),
            sensory_mode=str(sensory_mode),
            reinforcement_mode=str(reinforcement_mode),
            initial_checkpoint=base_checkpoint,
            arm_checkpoint=arm_checkpoint,
            train_seed=int(training["seed"]),
            train_steps=train_steps,
            scramble_seed=10_000 + index,
        )
        initial_hashes.append(training_result["initial_checkpoint_sha256"])
        arm_results[name] = {
            "training": training_result,
            "evaluation": _evaluate_arm(
                arm_checkpoint=arm_checkpoint,
                held_out_seeds=held_out_seeds,
                eval_steps=eval_steps,
            ),
        }

    base_sha_after = _sha256_file(base_checkpoint)
    arm_paths = [
        result["training"]["arm_checkpoint_path"]
        for result in arm_results.values()
    ]

    evidence_gates = {
        "same_initial_checkpoint_sha256": (
            len(set(initial_hashes)) == 1 and initial_hashes[0] == base_sha
        ),
        "source_checkpoint_unchanged": base_sha_after == base_sha,
        "all_four_arms_executed": tuple(arm_results) == tuple(
            arm[0] for arm in EXPECTED_ARMS
        ),
        "training_real_malecns_verified": all(
            result["training"]["training_metrics"]["neural_activity_verified"]
            for result in arm_results.values()
        ),
        "evaluation_real_malecns_verified": all(
            seed_result["metrics"]["neural_activity_verified"]
            for result in arm_results.values()
            for seed_result in result["evaluation"]["per_seed"]
        ),
        "held_out_seeds_exact": all(
            tuple(result["evaluation"]["held_out_seeds"])
            == EXPECTED_HELD_OUT_SEEDS
            for result in arm_results.values()
        ),
        "evaluation_learning_disabled": all(
            result["evaluation"]["learning"] is False
            for result in arm_results.values()
        ),
        "evaluation_reinforcement_disabled": all(
            result["evaluation"]["reinforcement_mode"] == "none"
            and all(
                set(seed_result["delivered_reinforcement"]) <= {"none"}
                for seed_result in result["evaluation"]["per_seed"]
            )
            for result in arm_results.values()
        ),
        "evaluation_normal_sensory_restored": all(
            result["evaluation"]["sensory_mode"] == "normal"
            for result in arm_results.values()
        ),
        "arm_checkpoints_isolated": (
            len(set(arm_paths)) == 4
            and all(Path(path).resolve() != base_checkpoint.resolve() for path in arm_paths)
        ),
        "effect_estimates_reported_without_auto_verdict": True,
    }

    required_evidence_keys = set(contract["required_evidence"])
    if set(evidence_gates) != required_evidence_keys:
        raise RuntimeError("Study evidence gate set drifted from preregistration")

    execution_complete = all(evidence_gates.values())
    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": "HUMAN_REVIEW_REQUIRED" if execution_complete else "FAIL",
        "passed_execution_gate": execution_complete,
        "scope": SCOPE,
        "contract_gates": contract_gates,
        "evidence_gates": evidence_gates,
        "base_checkpoint_sha256": base_sha,
        "base_checkpoint_sha256_after": base_sha_after,
        "train_steps": train_steps,
        "evaluation_steps_per_seed": eval_steps,
        "arm_results": arm_results,
        "descriptive_effects": descriptive_effects(arm_results),
        "learning_validated": False,
        "generalization_validated": False,
        "causal_learning_claim_authorized": False,
        "behavioral_promotion_authorized": False,
        "production_checkpoint_mutated": False,
        "human_science_review_required": True,
    }
    body["receipt_sha256"] = _digest_json(body)

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt_path.with_suffix(receipt_path.suffix + ".partial")
    temporary.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    temporary.replace(receipt_path)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a preregistered four-arm real MaleCNS learning control study"
    )
    parser.add_argument(
        "--contract",
        default="data/learning_control_study_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--train-steps", type=int)
    parser.add_argument("--eval-steps", type=int)
    args = parser.parse_args(argv)

    result = run_learning_control_study(
        contract_path=Path(args.contract),
        base_checkpoint=Path(args.base_checkpoint),
        output_dir=Path(args.output_dir),
        receipt_path=Path(args.receipt),
        train_steps=args.train_steps,
        eval_steps=args.eval_steps,
    )
    summary = {
        "schema": result["schema"],
        "status": result["status"],
        "passed_execution_gate": result["passed_execution_gate"],
        "base_checkpoint_sha256": result["base_checkpoint_sha256"],
        "receipt_sha256": result["receipt_sha256"],
        "descriptive_effects": result["descriptive_effects"],
        "learning_validated": result["learning_validated"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result["passed_execution_gate"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
