from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.confirmatory_learning_study import (
    EXPECTED_REPLICATES,
    RECEIPT_SCHEMA,
    evaluate_confirmatory_evidence,
    validate_contract,
)


CONTRACT = Path("data/confirmatory_learning_study_v01.json")
WORKFLOW = Path(".github/workflows/confirmatory-learning-study.yml")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text())


def _arm(
    *,
    path: str,
    initial_sha: str,
    reward: float,
    food: float,
) -> dict:
    per_seed = []
    for seed in (1, 2, 3):
        per_seed.append(
            {
                "seed": seed,
                "metrics": {
                    "neural_activity_verified": True,
                    "total_reward": reward,
                    "total_food": food,
                },
                "delivered_reinforcement": {"none": 20},
            }
        )
    return {
        "training": {
            "arm_checkpoint_path": path,
            "initial_checkpoint_sha256": initial_sha,
            "training_metrics": {"neural_activity_verified": True},
        },
        "evaluation": {
            "learning": False,
            "reinforcement_mode": "none",
            "sensory_mode": "normal",
            "per_seed": per_seed,
            "aggregate": {
                "mean_total_reward": reward,
                "mean_total_food": food,
            },
        },
    }


def _replicates(
    *,
    frozen_reward: float = 1.0,
    scrambled_reward: float = 1.0,
    sensory_reward: float = 2.0,
    treatment_reward: float = 3.0,
) -> list[dict]:
    source = "a" * 64
    results = []
    for index, (replicate_id, training_seed, heldout) in enumerate(EXPECTED_REPLICATES):
        prefix = f"/tmp/{replicate_id}"
        results.append(
            {
                "replicate_id": replicate_id,
                "training_seed": training_seed,
                "held_out_seeds": list(heldout),
                "arm_results": {
                    "learning_true": _arm(
                        path=f"{prefix}/learning_true.npz",
                        initial_sha=source,
                        reward=treatment_reward,
                        food=3.0,
                    ),
                    "frozen_true": _arm(
                        path=f"{prefix}/frozen_true.npz",
                        initial_sha=source,
                        reward=frozen_reward,
                        food=1.0,
                    ),
                    "learning_scrambled": _arm(
                        path=f"{prefix}/learning_scrambled.npz",
                        initial_sha=source,
                        reward=scrambled_reward,
                        food=1.0,
                    ),
                    "learning_sensory_off": _arm(
                        path=f"{prefix}/learning_sensory_off.npz",
                        initial_sha=source,
                        reward=sensory_reward,
                        food=2.0,
                    ),
                },
            }
        )
    return results


def _evaluate(replicates: list[dict]) -> dict:
    return evaluate_confirmatory_evidence(
        _contract(),
        replicate_results=replicates,
        source_sha_before="a" * 64,
        source_sha_after="a" * 64,
        base_checkpoint=Path("/tmp/base-brain.npz"),
    )


def test_contract_is_fully_preregistered_and_uses_fresh_disjoint_seeds() -> None:
    contract = _contract()
    gates = validate_contract(contract)

    assert all(gates.values())
    assert contract["training_steps"] == 60
    assert contract["evaluation_steps_per_seed"] == 20
    assert len(contract["replicates"]) == 8
    assert contract["primary_endpoint"] == "mean_total_reward"

    seeds = []
    for replicate in contract["replicates"]:
        seeds.append(replicate["training_seed"])
        seeds.extend(replicate["held_out_seeds"])
    assert len(seeds) == len(set(seeds))
    assert not ({109, 701, 709, 719} & set(seeds))


def test_confirmatory_pass_requires_both_co_primary_contrasts() -> None:
    report = _evaluate(_replicates())

    assert report["schema"] == RECEIPT_SCHEMA
    assert report["status"] == "CONFIRMATORY_PASS"
    assert report["execution_valid"] is True
    assert report["confirmatory_primary_pass"] is True
    assert report["learning_validated"] is True
    assert report["within_task_heldout_generalization_supported"] is True
    assert report["sensory_dependence_supported"] is True
    assert report["causal_learning_claim_authorized"] is True
    assert report["generalization_validated"] is False
    assert report["behavioral_promotion_authorized"] is False


def test_confirmatory_fails_if_mean_effect_is_below_practical_threshold() -> None:
    report = _evaluate(
        _replicates(
            treatment_reward=1.8,
            frozen_reward=1.0,
            scrambled_reward=1.0,
            sensory_reward=1.2,
        )
    )

    assert report["execution_valid"] is True
    assert report["status"] == "CONFIRMATORY_FAIL"
    assert report["confirmatory_primary_pass"] is False
    assert report["learning_validated"] is False
    assert report["causal_learning_claim_authorized"] is False


def test_confirmatory_fails_if_only_six_of_eight_replicates_are_positive() -> None:
    replicates = _replicates()
    for index in (0, 1):
        replicates[index]["arm_results"]["learning_true"]["evaluation"]["aggregate"][
            "mean_total_reward"
        ] = 0.0

    report = _evaluate(replicates)

    frozen = report["co_primary_results"]["learning_true_minus_frozen_true"]
    scrambled = report["co_primary_results"][
        "learning_true_minus_learning_scrambled"
    ]
    assert frozen["positive_reward_replicates"] == 6
    assert scrambled["positive_reward_replicates"] == 6
    assert frozen["passed"] is False
    assert scrambled["passed"] is False
    assert report["learning_validated"] is False


def test_sensory_support_controls_causal_claim_but_not_primary_learning_verdict() -> None:
    replicates = _replicates(sensory_reward=4.0)
    report = _evaluate(replicates)

    assert report["confirmatory_primary_pass"] is True
    assert report["learning_validated"] is True
    assert report["sensory_dependence_supported"] is False
    assert report["causal_learning_claim_authorized"] is False


def test_execution_invalid_if_source_checkpoint_changes() -> None:
    report = evaluate_confirmatory_evidence(
        _contract(),
        replicate_results=_replicates(),
        source_sha_before="a" * 64,
        source_sha_after="b" * 64,
        base_checkpoint=Path("/tmp/base-brain.npz"),
    )

    assert report["execution_valid"] is False
    assert report["status"] == "INVALID_EXECUTION"
    assert report["learning_validated"] is False


def test_contract_drift_cannot_open_behavioral_promotion() -> None:
    contract = copy.deepcopy(_contract())
    contract["claim_policy"]["behavioral_promotion_authorized"] = True

    gates = validate_contract(contract)

    assert gates["claim_policy_exact"] is False


def test_manual_workflow_has_no_tunable_confirmatory_inputs() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "inputs:" not in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "confirmatory_learning_study" in workflow
    assert "behavioral_promotion_authorized" in workflow
