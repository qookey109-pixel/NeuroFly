from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

from .learning_control_study import (
    EXPECTED_ARMS,
    _evaluate_arm,
    _run_training_arm,
    _sha256_file,
)
from .smoke import _digest_json


CONTRACT_SCHEMA = "neurofly-confirmatory-learning-study-v0.1"
RECEIPT_SCHEMA = "neurofly-confirmatory-learning-study-receipt-v0.1"
STATUS = "PREREGISTERED_EXECUTION_REQUIRED"
SCOPE = "real-malecns-confirmatory-learning-validation"

EXPECTED_TRAINING_STEPS = 60
EXPECTED_EVAL_STEPS = 20
EXPECTED_REPLICATES = (
    ("R1", 211, (1009, 1013, 1019)),
    ("R2", 223, (1021, 1031, 1033)),
    ("R3", 227, (1039, 1049, 1051)),
    ("R4", 229, (1061, 1063, 1069)),
    ("R5", 233, (1087, 1091, 1093)),
    ("R6", 239, (1097, 1103, 1109)),
    ("R7", 241, (1117, 1123, 1129)),
    ("R8", 251, (1151, 1153, 1163)),
)
CO_PRIMARY = (
    "learning_true_minus_frozen_true",
    "learning_true_minus_learning_scrambled",
)
SUPPORTIVE_CONTRAST = "learning_true_minus_learning_sensory_off"
MINIMUM_MEAN_REWARD_EFFECT = 1.0
MINIMUM_POSITIVE_REPLICATES = 7
SUPPORTIVE_MINIMUM_POSITIVE_REPLICATES = 5

REQUIRED_EVIDENCE = {
    "source_checkpoint_unchanged",
    "all_replicates_executed",
    "all_arms_start_from_same_sha_within_replicate",
    "all_arm_checkpoints_isolated",
    "training_real_malecns_verified",
    "evaluation_real_malecns_verified",
    "evaluation_learning_disabled",
    "evaluation_reinforcement_disabled",
    "evaluation_normal_sensory_restored",
    "exploratory_seeds_not_reused",
    "replicate_seed_sets_disjoint",
    "decision_rule_applied_without_mutation",
}


def _normalized_replicates(contract: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    rows = []
    for item in contract.get("replicates") or []:
        if not isinstance(item, dict):
            return ()
        rows.append(
            (
                item.get("id"),
                item.get("training_seed"),
                tuple(item.get("held_out_seeds") or ()),
            )
        )
    return tuple(rows)


def validate_contract(contract: dict[str, Any]) -> dict[str, bool]:
    evaluation = contract.get("evaluation") or {}
    rule = contract.get("confirmatory_decision_rule") or {}
    support = contract.get("supportive_sensory_dependence_rule") or {}
    required = contract.get("required_evidence") or {}
    claims = contract.get("claim_policy") or {}
    origin = contract.get("design_origin") or {}

    expected_arms = [
        {
            "name": name,
            "learning": learning,
            "sensory_mode": sensory,
            "reinforcement_mode": reinforcement,
        }
        for name, learning, sensory, reinforcement in EXPECTED_ARMS
    ]

    return {
        "schema_exact": contract.get("schema") == CONTRACT_SCHEMA,
        "status_exact": contract.get("status") == STATUS,
        "scope_exact": contract.get("scope") == SCOPE,
        "exploratory_anchor_exact": (
            origin.get("exploratory_run_id") == 35315263154
            and origin.get("exploratory_receipt_sha256")
            == "d14be40f2dc3f589548e9e36e453090a2db0605124b5b690d8779b1ff1d958bc"
            and origin.get("exploratory_result_used_for_design_only") is True
        ),
        "arms_exact": contract.get("arms") == expected_arms,
        "training_steps_exact": contract.get("training_steps") == EXPECTED_TRAINING_STEPS,
        "evaluation_steps_exact": (
            contract.get("evaluation_steps_per_seed") == EXPECTED_EVAL_STEPS
        ),
        "replicates_exact": _normalized_replicates(contract) == EXPECTED_REPLICATES,
        "evaluation_frozen_exact": (
            evaluation.get("learning") is False
            and evaluation.get("weights_frozen") is True
            and evaluation.get("reinforcement_mode") == "none"
            and evaluation.get("sensory_mode") == "normal"
        ),
        "primary_endpoint_exact": contract.get("primary_endpoint") == "mean_total_reward",
        "co_primary_exact": tuple(contract.get("co_primary_contrasts") or ())
        == CO_PRIMARY,
        "decision_rule_exact": (
            rule.get("minimum_mean_reward_effect") == MINIMUM_MEAN_REWARD_EFFECT
            and rule.get("minimum_positive_replicates")
            == MINIMUM_POSITIVE_REPLICATES
            and rule.get("total_replicates") == len(EXPECTED_REPLICATES)
            and rule.get("both_co_primary_contrasts_must_pass") is True
            and rule.get("rule_locked_before_execution") is True
        ),
        "supportive_rule_exact": (
            support.get("contrast") == SUPPORTIVE_CONTRAST
            and support.get("minimum_mean_reward_effect") == 0.0
            and support.get("minimum_positive_replicates")
            == SUPPORTIVE_MINIMUM_POSITIVE_REPLICATES
            and support.get("total_replicates") == len(EXPECTED_REPLICATES)
            and support.get("required_for_learning_validated") is False
            and support.get("required_for_causal_learning_claim") is True
        ),
        "required_evidence_exact": (
            isinstance(required, dict)
            and set(required) == REQUIRED_EVIDENCE
            and all(value is True for value in required.values())
        ),
        "claim_policy_exact": (
            claims.get("learning_validated_only_if_confirmatory_rule_passes") is True
            and claims.get(
                "causal_learning_claim_only_if_primary_and_sensory_support_pass"
            )
            is True
            and claims.get(
                "within_task_heldout_generalization_supported_only_if_primary_passes"
            )
            is True
            and claims.get("broad_generalization_validated") is False
            and claims.get("behavioral_promotion_authorized") is False
            and claims.get("production_checkpoint_mutated") is False
        ),
    }


def _reward_effect(arm_results: dict[str, Any], control: str) -> float:
    treatment = arm_results["learning_true"]["evaluation"]["aggregate"][
        "mean_total_reward"
    ]
    reference = arm_results[control]["evaluation"]["aggregate"][
        "mean_total_reward"
    ]
    return round(float(treatment) - float(reference), 8)


def _food_effect(arm_results: dict[str, Any], control: str) -> float:
    treatment = arm_results["learning_true"]["evaluation"]["aggregate"][
        "mean_total_food"
    ]
    reference = arm_results[control]["evaluation"]["aggregate"]["mean_total_food"]
    return round(float(treatment) - float(reference), 8)


def _contrast_summary(
    replicate_results: list[dict[str, Any]],
    *,
    control: str,
    minimum_mean_effect: float,
    minimum_positive_replicates: int,
) -> dict[str, Any]:
    reward_effects = [
        _reward_effect(item["arm_results"], control) for item in replicate_results
    ]
    food_effects = [
        _food_effect(item["arm_results"], control) for item in replicate_results
    ]
    positive = sum(effect > 0.0 for effect in reward_effects)
    mean_reward_effect = round(mean(reward_effects), 8)
    mean_food_effect = round(mean(food_effects), 8)
    passed = (
        mean_reward_effect >= minimum_mean_effect
        and positive >= minimum_positive_replicates
    )
    return {
        "control": control,
        "reward_effects_by_replicate": reward_effects,
        "food_effects_by_replicate": food_effects,
        "mean_reward_effect": mean_reward_effect,
        "mean_food_effect": mean_food_effect,
        "positive_reward_replicates": positive,
        "total_replicates": len(reward_effects),
        "minimum_mean_reward_effect": minimum_mean_effect,
        "minimum_positive_replicates": minimum_positive_replicates,
        "passed": passed,
    }


def evaluate_confirmatory_evidence(
    contract: dict[str, Any],
    *,
    replicate_results: list[dict[str, Any]],
    source_sha_before: str,
    source_sha_after: str,
    base_checkpoint: Path,
) -> dict[str, Any]:
    contract_gates = validate_contract(contract)

    all_paths = [
        result["training"]["arm_checkpoint_path"]
        for replicate in replicate_results
        for result in replicate["arm_results"].values()
    ]
    exploratory_seeds = {109, 701, 709, 719}
    configured_seeds = [
        seed
        for _, training_seed, heldout in EXPECTED_REPLICATES
        for seed in (training_seed, *heldout)
    ]

    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "all_replicates_executed": (
            len(replicate_results) == len(EXPECTED_REPLICATES)
            and tuple(item["replicate_id"] for item in replicate_results)
            == tuple(item[0] for item in EXPECTED_REPLICATES)
        ),
        "all_arms_start_from_same_sha_within_replicate": all(
            len(
                {
                    arm["training"]["initial_checkpoint_sha256"]
                    for arm in replicate["arm_results"].values()
                }
            )
            == 1
            and next(
                iter(
                    {
                        arm["training"]["initial_checkpoint_sha256"]
                        for arm in replicate["arm_results"].values()
                    }
                )
            )
            == source_sha_before
            for replicate in replicate_results
        ),
        "all_arm_checkpoints_isolated": (
            len(all_paths) == len(set(all_paths))
            and all(Path(path).resolve() != base_checkpoint.resolve() for path in all_paths)
        ),
        "training_real_malecns_verified": all(
            arm["training"]["training_metrics"]["neural_activity_verified"]
            for replicate in replicate_results
            for arm in replicate["arm_results"].values()
        ),
        "evaluation_real_malecns_verified": all(
            seed_result["metrics"]["neural_activity_verified"]
            for replicate in replicate_results
            for arm in replicate["arm_results"].values()
            for seed_result in arm["evaluation"]["per_seed"]
        ),
        "evaluation_learning_disabled": all(
            arm["evaluation"]["learning"] is False
            for replicate in replicate_results
            for arm in replicate["arm_results"].values()
        ),
        "evaluation_reinforcement_disabled": all(
            arm["evaluation"]["reinforcement_mode"] == "none"
            and all(
                set(seed_result["delivered_reinforcement"]) <= {"none"}
                for seed_result in arm["evaluation"]["per_seed"]
            )
            for replicate in replicate_results
            for arm in replicate["arm_results"].values()
        ),
        "evaluation_normal_sensory_restored": all(
            arm["evaluation"]["sensory_mode"] == "normal"
            for replicate in replicate_results
            for arm in replicate["arm_results"].values()
        ),
        "exploratory_seeds_not_reused": not (
            set(configured_seeds) & exploratory_seeds
        ),
        "replicate_seed_sets_disjoint": len(configured_seeds)
        == len(set(configured_seeds)),
        "decision_rule_applied_without_mutation": all(contract_gates.values()),
    }

    if set(evidence_gates) != set(contract["required_evidence"]):
        raise RuntimeError("Confirmatory evidence gate drifted from preregistration")

    frozen = _contrast_summary(
        replicate_results,
        control="frozen_true",
        minimum_mean_effect=MINIMUM_MEAN_REWARD_EFFECT,
        minimum_positive_replicates=MINIMUM_POSITIVE_REPLICATES,
    )
    scrambled = _contrast_summary(
        replicate_results,
        control="learning_scrambled",
        minimum_mean_effect=MINIMUM_MEAN_REWARD_EFFECT,
        minimum_positive_replicates=MINIMUM_POSITIVE_REPLICATES,
    )
    sensory = _contrast_summary(
        replicate_results,
        control="learning_sensory_off",
        minimum_mean_effect=0.0,
        minimum_positive_replicates=SUPPORTIVE_MINIMUM_POSITIVE_REPLICATES,
    )

    execution_valid = all(contract_gates.values()) and all(evidence_gates.values())
    primary_pass = execution_valid and frozen["passed"] and scrambled["passed"]
    sensory_support = execution_valid and sensory["passed"]

    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": (
            "CONFIRMATORY_PASS"
            if primary_pass
            else "CONFIRMATORY_FAIL"
            if execution_valid
            else "INVALID_EXECUTION"
        ),
        "scope": SCOPE,
        "execution_valid": execution_valid,
        "contract_gates": contract_gates,
        "evidence_gates": evidence_gates,
        "replicates": replicate_results,
        "co_primary_results": {
            "learning_true_minus_frozen_true": frozen,
            "learning_true_minus_learning_scrambled": scrambled,
        },
        "supportive_sensory_dependence": sensory,
        "confirmatory_primary_pass": primary_pass,
        "sensory_dependence_supported": sensory_support,
        "learning_validated": primary_pass,
        "within_task_heldout_generalization_supported": primary_pass,
        "causal_learning_claim_authorized": primary_pass and sensory_support,
        "generalization_validated": False,
        "behavioral_promotion_authorized": False,
        "production_checkpoint_mutated": False,
        "source_checkpoint_sha256": source_sha_before,
        "source_checkpoint_sha256_after": source_sha_after,
    }
    body["receipt_sha256"] = _digest_json(body)
    return body


def run_confirmatory_learning_study(
    *,
    contract_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text())
    contract_gates = validate_contract(contract)
    if not all(contract_gates.values()):
        raise ValueError("Confirmatory learning contract failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)

    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha_before = _sha256_file(base_checkpoint)
    replicate_results: list[dict[str, Any]] = []

    for replicate_index, (replicate_id, training_seed, heldout_seeds) in enumerate(
        EXPECTED_REPLICATES
    ):
        replicate_dir = output_dir / replicate_id
        replicate_dir.mkdir(parents=True, exist_ok=True)
        arm_results: dict[str, Any] = {}

        for arm_index, (name, learning, sensory_mode, reinforcement_mode) in enumerate(
            EXPECTED_ARMS
        ):
            arm_checkpoint = replicate_dir / f"{name}.npz"
            training_result = _run_training_arm(
                arm_name=name,
                learning=bool(learning),
                sensory_mode=str(sensory_mode),
                reinforcement_mode=str(reinforcement_mode),
                initial_checkpoint=base_checkpoint,
                arm_checkpoint=arm_checkpoint,
                train_seed=training_seed,
                train_steps=EXPECTED_TRAINING_STEPS,
                scramble_seed=50_000 + replicate_index * 100 + arm_index,
            )
            arm_results[name] = {
                "training": training_result,
                "evaluation": _evaluate_arm(
                    arm_checkpoint=arm_checkpoint,
                    held_out_seeds=heldout_seeds,
                    eval_steps=EXPECTED_EVAL_STEPS,
                ),
            }

        replicate_results.append(
            {
                "replicate_id": replicate_id,
                "training_seed": training_seed,
                "held_out_seeds": list(heldout_seeds),
                "arm_results": arm_results,
            }
        )

    source_sha_after = _sha256_file(base_checkpoint)
    report = evaluate_confirmatory_evidence(
        contract,
        replicate_results=replicate_results,
        source_sha_before=source_sha_before,
        source_sha_after=source_sha_after,
        base_checkpoint=base_checkpoint,
    )

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt_path.with_suffix(receipt_path.suffix + ".partial")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    temporary.replace(receipt_path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the preregistered NeuroFly confirmatory learning study"
    )
    parser.add_argument(
        "--contract",
        default="data/confirmatory_learning_study_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_confirmatory_learning_study(
        contract_path=Path(args.contract),
        base_checkpoint=Path(args.base_checkpoint),
        output_dir=Path(args.output_dir),
        receipt_path=Path(args.receipt),
    )
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "status": result["status"],
                "execution_valid": result["execution_valid"],
                "confirmatory_primary_pass": result["confirmatory_primary_pass"],
                "sensory_dependence_supported": result[
                    "sensory_dependence_supported"
                ],
                "learning_validated": result["learning_validated"],
                "causal_learning_claim_authorized": result[
                    "causal_learning_claim_authorized"
                ],
                "co_primary_results": result["co_primary_results"],
                "supportive_sensory_dependence": result[
                    "supportive_sensory_dependence"
                ],
                "receipt_sha256": result["receipt_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["execution_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
