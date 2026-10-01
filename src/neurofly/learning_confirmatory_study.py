from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import shutil
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from .brain_runtime import BrainDecision, MaleCNSBrain
from .environment_adapter import (
    ENVIRONMENT_ADAPTER_SCHEMA,
    EnvironmentSession,
    MazeChaseAdapter,
    assert_sensory_only_context,
)
from .goal_training import GoalMazeEnvironment
from .learning_control_study import ControlledBrain
from .smoke import _digest_json, _neural_decision_verified


CONTRACT_SCHEMA = "neurofly-confirmatory-sensory-learning-v0.1"
RECEIPT_SCHEMA = "neurofly-confirmatory-sensory-learning-receipt-v0.1"
STATUS = "EXECUTION_REQUIRED"
SCOPE = "fixed-malecns-maze-task-confirmatory-learning"

EXPECTED_ARMS = (
    ("learning_true", True, "normal", "true"),
    ("frozen_true", False, "normal", "true"),
    ("learning_scrambled", True, "normal", "scrambled"),
    ("learning_sensory_off", True, "off", "true"),
)
EXPECTED_REPLICATES = (
    (1, 211, (811, 821)),
    (2, 223, (823, 827)),
    (3, 227, (829, 839)),
    (4, 229, (853, 857)),
    (5, 233, (859, 863)),
    (6, 239, (877, 881)),
    (7, 241, (883, 887)),
    (8, 251, (907, 911)),
    (9, 257, (919, 929)),
    (10, 263, (937, 941)),
)
COMPARISONS = (
    "learning_true_minus_frozen_true",
    "learning_true_minus_learning_scrambled",
    "learning_true_minus_learning_sensory_off",
)
PRIMARY_ENDPOINT = "mean_total_reward"
VALID_ACTIONS = {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _trajectory_sha256(states: list[dict[str, Any]]) -> str:
    public = [
        {
            "fly": state.get("fly"),
            "enemies": state.get("enemies"),
            "action": state.get("last_action"),
            "reward": state.get("last_reward"),
            "event": state.get("step_event") or state.get("last_event"),
            "episode": state.get("episode"),
        }
        for state in states
    ]
    return _digest_json(public)


class AuditBrain:
    """Record the exact transformed inputs that reach real MaleCNS."""

    name = "malecns"

    def __init__(self, inner: MaleCNSBrain) -> None:
        self.inner = inner
        self.last_context: dict[str, Any] | None = None
        self.context_history: list[dict[str, Any] | None] = []

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision:
        captured = copy.deepcopy(context)
        self.last_context = captured
        self.context_history.append(captured)
        return self.inner.decide(frame, reinforcement, context=context)

    def save(self, path: str | Path) -> None:
        self.inner.save(path)


def _contract_arms(contract: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    arms = contract.get("arms")
    if not isinstance(arms, list):
        return ()
    out = []
    for arm in arms:
        if not isinstance(arm, dict):
            return ()
        out.append(
            (
                arm.get("name"),
                arm.get("learning"),
                arm.get("sensory_mode"),
                arm.get("reinforcement_mode"),
            )
        )
    return tuple(out)


def _contract_replicates(contract: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    reps = contract.get("replicates")
    if not isinstance(reps, list):
        return ()
    out = []
    for item in reps:
        if not isinstance(item, dict):
            return ()
        out.append(
            (
                item.get("replicate"),
                item.get("training_seed"),
                tuple(item.get("evaluation_seeds") or ()),
            )
        )
    return tuple(out)


def validate_contract(contract: dict[str, Any]) -> dict[str, bool]:
    execution = contract.get("execution") or {}
    rule = contract.get("confirmatory_rule") or {}
    evaluation = contract.get("evaluation") or {}
    required = contract.get("required_evidence") or {}
    claims = contract.get("claim_policy") or {}

    return {
        "schema_exact": contract.get("schema") == CONTRACT_SCHEMA,
        "status_exact": contract.get("status") == STATUS,
        "scope_exact": contract.get("scope") == SCOPE,
        "arms_exact": _contract_arms(contract) == EXPECTED_ARMS,
        "replicates_exact": _contract_replicates(contract) == EXPECTED_REPLICATES,
        "orchestration_exact": execution.get("orchestration") == "EnvironmentSession",
        "adapter_exact": execution.get("adapter") == "MazeChaseAdapter",
        "environment_exact": execution.get("environment") == "GoalMazeEnvironment",
        "synchronous_enemy_motion_required": execution.get(
            "synchronous_enemy_motion_per_action"
        )
        is True,
        "sensory_only_required": execution.get("sensory_only_context_required") is True,
        "training_steps_exact": execution.get("training_steps") == 60,
        "evaluation_steps_exact": execution.get("evaluation_steps_per_seed") == 40,
        "replicate_count_exact": execution.get("replicate_count") == 10,
        "primary_endpoint_exact": contract.get("primary_endpoint") == PRIMARY_ENDPOINT,
        "comparison_set_exact": tuple(rule.get("comparisons") or ()) == COMPARISONS,
        "positive_count_exact": rule.get("positive_replicates_required") == 9,
        "fixed_n_exact": rule.get("replicate_count_fixed") == 10,
        "zero_not_positive": rule.get("zero_difference_counts_as_positive") is False,
        "median_threshold_exact": float(
            rule.get("median_reward_difference_minimum", -1)
        )
        == 1.0,
        "sign_test_exact": rule.get("sign_test")
        == "exact_one_sided_binomial_p_ge_observed_positives_under_p_0.5",
        "holm_exact": rule.get("familywise_correction") == "holm_bonferroni",
        "alpha_exact": float(rule.get("familywise_alpha", -1)) == 0.05,
        "no_optional_stopping": rule.get("no_optional_stopping") is True,
        "no_sample_extension": rule.get("no_data_dependent_replicate_extension")
        is True,
        "evaluation_frozen": evaluation.get("learning") is False,
        "evaluation_reinforcement_none": evaluation.get("reinforcement_mode") == "none",
        "evaluation_normal_sensory": evaluation.get("sensory_mode") == "normal",
        "fresh_environment_per_seed": evaluation.get("fresh_environment_per_seed")
        is True,
        "fresh_brain_per_seed": evaluation.get("fresh_brain_restore_per_seed") is True,
        "required_evidence_all_true": (
            isinstance(required, dict)
            and bool(required)
            and all(value is True for value in required.values())
        ),
        "claim_policy_exact": (
            claims.get("learning_validation_scope")
            == "this_fixed_malecns_checkpoint_on_goal_maze_under_preregistered_environment_randomization"
            and claims.get("learning_validated_from_confirmatory_rule") is True
            and claims.get("causal_learning_claim_authorized") is False
            and claims.get("generalization_validated") is False
            and claims.get("behavioral_promotion_authorized") is False
            and claims.get("production_checkpoint_mutated") is False
        ),
    }


def exact_one_sided_sign_p(positive_count: int, n: int) -> float:
    if n < 1 or not 0 <= positive_count <= n:
        raise ValueError("invalid sign-test counts")
    numerator = sum(math.comb(n, k) for k in range(positive_count, n + 1))
    return numerator / (2**n)


def holm_bonferroni(
    pvalues: dict[str, float],
    *,
    alpha: float = 0.05,
) -> dict[str, dict[str, Any]]:
    if not pvalues:
        raise ValueError("pvalues required")
    ordered = sorted(pvalues.items(), key=lambda item: (item[1], item[0]))
    m = len(ordered)
    results: dict[str, dict[str, Any]] = {}
    still_passing = True
    for index, (name, pvalue) in enumerate(ordered):
        threshold = alpha / (m - index)
        passed = still_passing and pvalue <= threshold
        if not passed:
            still_passing = False
        results[name] = {
            "p_value": round(float(pvalue), 12),
            "holm_threshold": round(float(threshold), 12),
            "holm_pass": passed,
        }
    return results


def _state_metrics(states: list[dict[str, Any]]) -> dict[str, Any]:
    if not states:
        raise ValueError("no states")
    actions = Counter(str(state.get("last_action") or "UNKNOWN") for state in states)
    final = states[-1]
    rewards = [float(state.get("last_reward") or 0.0) for state in states]
    spikes = []
    for state in states:
        telemetry = ((state.get("brain") or {}).get("telemetry") or {})
        spikes.append(int(telemetry.get("total_spikes") or 0))
    return {
        "steps": len(states),
        "total_reward": round(sum(rewards), 8),
        "total_food": int(final.get("total_food") or 0),
        "total_clears": int(final.get("total_clears") or 0),
        "total_deaths": int(final.get("total_deaths") or 0),
        "hold_fraction": round(actions.get("HOLD", 0) / len(states), 8),
        "action_counts": dict(sorted(actions.items())),
        "mean_total_spikes": round(mean(spikes), 8),
        "neural_activity_verified": all(
            _neural_decision_verified(state) for state in states
        ),
        "trajectory_sha256": _trajectory_sha256(states),
    }


def _aggregate(per_seed: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "mean_total_reward": round(
            mean(item["metrics"]["total_reward"] for item in per_seed), 8
        ),
        "mean_total_food": round(
            mean(item["metrics"]["total_food"] for item in per_seed), 8
        ),
        "mean_total_clears": round(
            mean(item["metrics"]["total_clears"] for item in per_seed), 8
        ),
        "mean_total_deaths": round(
            mean(item["metrics"]["total_deaths"] for item in per_seed), 8
        ),
        "mean_hold_fraction": round(
            mean(item["metrics"]["hold_fraction"] for item in per_seed), 8
        ),
    }


def _run_steps(
    session: EnvironmentSession,
    audit: AuditBrain,
    *,
    steps: int,
    sensory_mode: str,
) -> tuple[list[dict[str, Any]], bool]:
    states: list[dict[str, Any]] = []
    context_ok = True
    for _ in range(steps):
        state = session.tick()
        if not _neural_decision_verified(state):
            raise RuntimeError("MaleCNS decision lacks verified neural activity")

        delivered_context = audit.last_context
        if sensory_mode == "off":
            if delivered_context != {}:
                context_ok = False
        else:
            if not isinstance(delivered_context, dict):
                context_ok = False
            else:
                try:
                    assert_sensory_only_context(delivered_context)
                except ValueError:
                    context_ok = False
                if delivered_context.get("adapter_schema") != ENVIRONMENT_ADAPTER_SCHEMA:
                    context_ok = False
        states.append(copy.deepcopy(state))
    return states, context_ok


def _build_arm(
    *,
    checkpoint: Path,
    learning: bool,
    sensory_mode: str,
    reinforcement_mode: str,
    scramble_seed: int,
) -> tuple[ControlledBrain, AuditBrain, MaleCNSBrain]:
    real = MaleCNSBrain(checkpoint=checkpoint, learning=learning)
    real.brain.weights_frozen = not learning
    if bool(real.learning) is not bool(learning):
        raise RuntimeError("MaleCNS learning mode mismatch")
    if bool(real.brain.weights_frozen) is not (not learning):
        raise RuntimeError("MaleCNS weight freeze mismatch")

    audit = AuditBrain(real)
    controlled = ControlledBrain(
        audit,
        sensory_mode=sensory_mode,
        reinforcement_mode=reinforcement_mode,
        scramble_seed=scramble_seed,
    )
    return controlled, audit, real


def _run_training_arm(
    *,
    initial_checkpoint: Path,
    arm_checkpoint: Path,
    arm_name: str,
    learning: bool,
    sensory_mode: str,
    reinforcement_mode: str,
    training_seed: int,
    steps: int,
    scramble_seed: int,
) -> dict[str, Any]:
    shutil.copy2(initial_checkpoint, arm_checkpoint)
    initial_sha = _sha256_file(arm_checkpoint)

    controlled, audit, real = _build_arm(
        checkpoint=arm_checkpoint,
        learning=learning,
        sensory_mode=sensory_mode,
        reinforcement_mode=reinforcement_mode,
        scramble_seed=scramble_seed,
    )
    environment = GoalMazeEnvironment(seed=training_seed)
    session = EnvironmentSession(
        controlled,
        MazeChaseAdapter(environment=environment),
        checkpoint=None,
        checkpoint_every=10**12,
    )
    states, context_ok = _run_steps(
        session,
        audit,
        steps=steps,
        sensory_mode=sensory_mode,
    )
    controlled.save(arm_checkpoint)

    return {
        "arm": arm_name,
        "learning": learning,
        "sensory_mode": sensory_mode,
        "reinforcement_mode": reinforcement_mode,
        "training_seed": training_seed,
        "initial_checkpoint_sha256": initial_sha,
        "post_training_checkpoint_sha256": _sha256_file(arm_checkpoint),
        "neural_context_policy_verified": context_ok,
        "weights_frozen_after_training": bool(real.brain.weights_frozen),
        "delivered_reinforcement": dict(
            sorted(controlled.delivered_reinforcement.items())
        ),
        "metrics": _state_metrics(states),
    }


def _evaluate_arm(
    *,
    arm_checkpoint: Path,
    evaluation_seeds: tuple[int, ...],
    steps_per_seed: int,
) -> dict[str, Any]:
    per_seed: list[dict[str, Any]] = []
    for seed in evaluation_seeds:
        controlled, audit, real = _build_arm(
            checkpoint=arm_checkpoint,
            learning=False,
            sensory_mode="normal",
            reinforcement_mode="none",
            scramble_seed=0,
        )
        if real.learning or not real.brain.weights_frozen:
            raise RuntimeError("evaluation brain must be frozen")

        environment = GoalMazeEnvironment(seed=seed)
        session = EnvironmentSession(
            controlled,
            MazeChaseAdapter(environment=environment),
            checkpoint=None,
            checkpoint_every=10**12,
        )
        states, context_ok = _run_steps(
            session,
            audit,
            steps=steps_per_seed,
            sensory_mode="normal",
        )
        per_seed.append(
            {
                "seed": seed,
                "neural_context_policy_verified": context_ok,
                "delivered_reinforcement": dict(
                    sorted(controlled.delivered_reinforcement.items())
                ),
                "metrics": _state_metrics(states),
            }
        )

    return {
        "evaluation_seeds": list(evaluation_seeds),
        "steps_per_seed": steps_per_seed,
        "learning": False,
        "sensory_mode": "normal",
        "reinforcement_mode": "none",
        "per_seed": per_seed,
        "aggregate": _aggregate(per_seed),
    }


def evaluate_confirmatory_rule(
    replicate_results: list[dict[str, Any]],
    *,
    positive_required: int = 9,
    median_minimum: float = 1.0,
    alpha: float = 0.05,
) -> dict[str, Any]:
    if len(replicate_results) != 10:
        raise ValueError("confirmatory rule requires exactly 10 replicates")

    comparisons: dict[str, Any] = {}
    pvalues: dict[str, float] = {}

    control_map = {
        "learning_true_minus_frozen_true": "frozen_true",
        "learning_true_minus_learning_scrambled": "learning_scrambled",
        "learning_true_minus_learning_sensory_off": "learning_sensory_off",
    }

    for comparison, control in control_map.items():
        differences = []
        for replicate in replicate_results:
            treatment = replicate["arms"]["learning_true"]["evaluation"]["aggregate"][
                PRIMARY_ENDPOINT
            ]
            reference = replicate["arms"][control]["evaluation"]["aggregate"][
                PRIMARY_ENDPOINT
            ]
            differences.append(round(float(treatment) - float(reference), 8))

        positive_count = sum(value > 0 for value in differences)
        med = float(median(differences))
        pvalue = exact_one_sided_sign_p(positive_count, len(differences))
        pvalues[comparison] = pvalue
        comparisons[comparison] = {
            "paired_reward_differences": differences,
            "positive_replicates": positive_count,
            "positive_required": positive_required,
            "median_reward_difference": round(med, 8),
            "median_minimum": median_minimum,
            "sign_test_p_value": round(pvalue, 12),
            "positive_count_pass": positive_count >= positive_required,
            "median_pass": med >= median_minimum,
        }

    holm = holm_bonferroni(pvalues, alpha=alpha)
    for name, correction in holm.items():
        comparisons[name].update(correction)
        comparisons[name]["comparison_pass"] = (
            comparisons[name]["positive_count_pass"]
            and comparisons[name]["median_pass"]
            and correction["holm_pass"]
        )

    return {
        "primary_endpoint": PRIMARY_ENDPOINT,
        "comparisons": comparisons,
        "familywise_alpha": alpha,
        "all_comparisons_pass": all(
            item["comparison_pass"] for item in comparisons.values()
        ),
    }


def run_confirmatory_study(
    *,
    contract_path: Path,
    source_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text())
    contract_gates = validate_contract(contract)
    if not all(contract_gates.values()):
        raise ValueError("confirmatory contract failed validation")
    if not source_checkpoint.is_file():
        raise FileNotFoundError(source_checkpoint)

    output_dir.mkdir(parents=True, exist_ok=True)
    base_checkpoint = output_dir / "base-brain.npz"
    source_sha_before = _sha256_file(source_checkpoint)
    shutil.copy2(source_checkpoint, base_checkpoint)
    base_sha = _sha256_file(base_checkpoint)
    if base_sha != source_sha_before:
        raise RuntimeError("isolated baseline differs from source checkpoint")

    execution = contract["execution"]
    train_steps = int(execution["training_steps"])
    eval_steps = int(execution["evaluation_steps_per_seed"])

    replicate_results: list[dict[str, Any]] = []
    arm_paths: list[str] = []
    initial_hashes: list[str] = []

    for replicate_index, training_seed, evaluation_seeds in EXPECTED_REPLICATES:
        replicate_dir = output_dir / f"replicate-{replicate_index:02d}"
        replicate_dir.mkdir(parents=True, exist_ok=True)
        arms: dict[str, Any] = {}

        for arm_index, (
            arm_name,
            learning,
            sensory_mode,
            reinforcement_mode,
        ) in enumerate(EXPECTED_ARMS):
            arm_checkpoint = replicate_dir / f"{arm_name}.npz"
            training = _run_training_arm(
                initial_checkpoint=base_checkpoint,
                arm_checkpoint=arm_checkpoint,
                arm_name=arm_name,
                learning=bool(learning),
                sensory_mode=str(sensory_mode),
                reinforcement_mode=str(reinforcement_mode),
                training_seed=int(training_seed),
                steps=train_steps,
                scramble_seed=50_000 + replicate_index * 100 + arm_index,
            )
            arm_paths.append(str(arm_checkpoint.resolve()))
            initial_hashes.append(training["initial_checkpoint_sha256"])

            evaluation = _evaluate_arm(
                arm_checkpoint=arm_checkpoint,
                evaluation_seeds=tuple(int(seed) for seed in evaluation_seeds),
                steps_per_seed=eval_steps,
            )
            arms[arm_name] = {
                "training": training,
                "evaluation": evaluation,
            }

        replicate_results.append(
            {
                "replicate": replicate_index,
                "training_seed": training_seed,
                "evaluation_seeds": list(evaluation_seeds),
                "arms": arms,
            }
        )

    source_sha_after = _sha256_file(source_checkpoint)

    all_normal_contexts = all(
        result["training"]["neural_context_policy_verified"]
        for replicate in replicate_results
        for name, result in replicate["arms"].items()
        if name != "learning_sensory_off"
    ) and all(
        seed_result["neural_context_policy_verified"]
        for replicate in replicate_results
        for result in replicate["arms"].values()
        for seed_result in result["evaluation"]["per_seed"]
    )
    all_sensory_off_empty = all(
        replicate["arms"]["learning_sensory_off"]["training"][
            "neural_context_policy_verified"
        ]
        for replicate in replicate_results
    )
    all_training_neural = all(
        result["training"]["metrics"]["neural_activity_verified"]
        for replicate in replicate_results
        for result in replicate["arms"].values()
    )
    all_eval_neural = all(
        seed_result["metrics"]["neural_activity_verified"]
        for replicate in replicate_results
        for result in replicate["arms"].values()
        for seed_result in result["evaluation"]["per_seed"]
    )
    all_eval_none = all(
        set(seed_result["delivered_reinforcement"]) <= {"none"}
        for replicate in replicate_results
        for result in replicate["arms"].values()
        for seed_result in result["evaluation"]["per_seed"]
    )

    training_fingerprints = {
        replicate["arms"]["learning_true"]["training"]["metrics"]["trajectory_sha256"]
        for replicate in replicate_results
    }
    evaluation_fingerprints = {
        seed_result["metrics"]["trajectory_sha256"]
        for replicate in replicate_results
        for seed_result in replicate["arms"]["learning_true"]["evaluation"]["per_seed"]
    }

    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "all_replicates_executed": len(replicate_results) == 10,
        "all_four_arms_per_replicate": all(
            tuple(replicate["arms"]) == tuple(arm[0] for arm in EXPECTED_ARMS)
            for replicate in replicate_results
        ),
        "all_training_real_malecns_verified": all_training_neural,
        "all_evaluation_real_malecns_verified": all_eval_neural,
        "all_normal_sensory_contexts_unprivileged": all_normal_contexts,
        "all_sensory_off_contexts_empty": all_sensory_off_empty,
        "synchronous_seeded_enemy_dynamics_used": (
            len(training_fingerprints) > 1 and len(evaluation_fingerprints) > 1
        ),
        "evaluation_learning_disabled": all(
            result["evaluation"]["learning"] is False
            for replicate in replicate_results
            for result in replicate["arms"].values()
        ),
        "evaluation_reinforcement_disabled": all_eval_none,
        "evaluation_normal_sensory_restored": all(
            result["evaluation"]["sensory_mode"] == "normal"
            for replicate in replicate_results
            for result in replicate["arms"].values()
        ),
        "arm_checkpoints_isolated": (
            len(set(arm_paths)) == 40
            and all(Path(path) != source_checkpoint.resolve() for path in arm_paths)
            and all(Path(path) != base_checkpoint.resolve() for path in arm_paths)
        ),
        "exact_preregistered_seeds_used": tuple(
            (
                replicate["replicate"],
                replicate["training_seed"],
                tuple(replicate["evaluation_seeds"]),
            )
            for replicate in replicate_results
        )
        == EXPECTED_REPLICATES,
        "exact_fixed_sample_size_used": len(replicate_results) == 10,
    }
    if set(evidence_gates) != set(contract["required_evidence"]):
        raise RuntimeError("confirmatory evidence gate drifted from preregistration")

    execution_valid = all(contract_gates.values()) and all(evidence_gates.values())
    rule = evaluate_confirmatory_rule(
        replicate_results,
        positive_required=int(contract["confirmatory_rule"]["positive_replicates_required"]),
        median_minimum=float(
            contract["confirmatory_rule"]["median_reward_difference_minimum"]
        ),
        alpha=float(contract["confirmatory_rule"]["familywise_alpha"]),
    )
    learning_validated = execution_valid and rule["all_comparisons_pass"]

    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": (
            "CONFIRMATORY_PASS"
            if learning_validated
            else "CONFIRMATORY_FAIL"
            if execution_valid
            else "INVALID_EXECUTION"
        ),
        "execution_valid": execution_valid,
        "scope": SCOPE,
        "contract_gates": contract_gates,
        "evidence_gates": evidence_gates,
        "source_checkpoint_sha256": source_sha_before,
        "source_checkpoint_sha256_after": source_sha_after,
        "base_checkpoint_sha256": base_sha,
        "replicate_results": replicate_results,
        "confirmatory_rule_result": rule,
        "learning_validated": learning_validated,
        "learning_validation_scope": contract["claim_policy"][
            "learning_validation_scope"
        ],
        "causal_learning_claim_authorized": False,
        "generalization_validated": False,
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
        description="Run preregistered sensory-only confirmatory MaleCNS learning study"
    )
    parser.add_argument(
        "--contract",
        default="data/confirmatory_sensory_learning_v01.json",
    )
    parser.add_argument("--source-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_confirmatory_study(
        contract_path=Path(args.contract),
        source_checkpoint=Path(args.source_checkpoint),
        output_dir=Path(args.output_dir),
        receipt_path=Path(args.receipt),
    )
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "status": result["status"],
                "execution_valid": result["execution_valid"],
                "learning_validated": result["learning_validated"],
                "receipt_sha256": result["receipt_sha256"],
                "confirmatory_rule_result": result["confirmatory_rule_result"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["execution_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
