from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.environment_adapter import MazeChaseAdapter, assert_sensory_only_context
from neurofly.goal_training import GoalMazeEnvironment
from neurofly.learning_confirmatory_study import (
    COMPARISONS,
    EXPECTED_REPLICATES,
    PRIMARY_ENDPOINT,
    evaluate_confirmatory_rule,
    exact_one_sided_sign_p,
    holm_bonferroni,
    validate_contract,
)


CONTRACT = Path("data/confirmatory_sensory_learning_v01.json")
WORKFLOW = Path(".github/workflows/confirmatory-sensory-learning.yml")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text())


def _replicate(
    *,
    treatment: float,
    frozen: float,
    scrambled: float,
    sensory_off: float,
) -> dict:
    def arm(value: float) -> dict:
        return {
            "evaluation": {
                "aggregate": {
                    PRIMARY_ENDPOINT: value,
                }
            }
        }

    return {
        "arms": {
            "learning_true": arm(treatment),
            "frozen_true": arm(frozen),
            "learning_scrambled": arm(scrambled),
            "learning_sensory_off": arm(sensory_off),
        }
    }


def test_confirmatory_contract_is_exact_and_fixed_before_execution() -> None:
    contract = _contract()
    gates = validate_contract(contract)

    assert all(gates.values())
    assert tuple(
        (
            item["replicate"],
            item["training_seed"],
            tuple(item["evaluation_seeds"]),
        )
        for item in contract["replicates"]
    ) == EXPECTED_REPLICATES
    assert contract["primary_endpoint"] == PRIMARY_ENDPOINT
    assert tuple(contract["confirmatory_rule"]["comparisons"]) == COMPARISONS
    assert contract["confirmatory_rule"]["replicate_count_fixed"] == 10
    assert contract["confirmatory_rule"]["positive_replicates_required"] == 9
    assert contract["confirmatory_rule"]["median_reward_difference_minimum"] == 1.0
    assert contract["confirmatory_rule"]["no_optional_stopping"] is True
    assert (
        contract["confirmatory_rule"]["no_data_dependent_replicate_extension"]
        is True
    )


def test_exact_sign_test_requires_nine_of_ten_for_familywise_design() -> None:
    assert exact_one_sided_sign_p(10, 10) == 1 / 1024
    assert exact_one_sided_sign_p(9, 10) == 11 / 1024
    assert exact_one_sided_sign_p(8, 10) == 56 / 1024

    nine = exact_one_sided_sign_p(9, 10)
    corrected = holm_bonferroni(
        {
            "a": nine,
            "b": nine,
            "c": nine,
        },
        alpha=0.05,
    )
    assert all(item["holm_pass"] for item in corrected.values())

    eight = exact_one_sided_sign_p(8, 10)
    failed = holm_bonferroni(
        {
            "a": eight,
            "b": eight,
            "c": eight,
        },
        alpha=0.05,
    )
    assert not any(item["holm_pass"] for item in failed.values())


def test_confirmatory_rule_passes_only_with_preregistered_strength() -> None:
    results = [
        _replicate(treatment=4.0, frozen=1.0, scrambled=1.5, sensory_off=2.0)
        for _ in range(9)
    ]
    results.append(
        _replicate(treatment=0.0, frozen=1.0, scrambled=1.0, sensory_off=1.0)
    )

    decision = evaluate_confirmatory_rule(results)

    assert decision["all_comparisons_pass"] is True
    for result in decision["comparisons"].values():
        assert result["positive_replicates"] == 9
        assert result["median_reward_difference"] >= 1.0
        assert result["holm_pass"] is True
        assert result["comparison_pass"] is True


def test_confirmatory_rule_fails_at_eight_of_ten() -> None:
    results = [
        _replicate(treatment=4.0, frozen=1.0, scrambled=1.0, sensory_off=1.0)
        for _ in range(8)
    ]
    results.extend(
        [
            _replicate(treatment=0.0, frozen=1.0, scrambled=1.0, sensory_off=1.0),
            _replicate(treatment=0.0, frozen=1.0, scrambled=1.0, sensory_off=1.0),
        ]
    )

    decision = evaluate_confirmatory_rule(results)

    assert decision["all_comparisons_pass"] is False
    assert all(
        result["positive_replicates"] == 8
        for result in decision["comparisons"].values()
    )


def test_confirmatory_rule_fails_if_practical_effect_is_too_small() -> None:
    results = [
        _replicate(treatment=1.4, frozen=0.6, scrambled=0.7, sensory_off=0.8)
        for _ in range(10)
    ]

    decision = evaluate_confirmatory_rule(results)

    assert decision["all_comparisons_pass"] is False
    assert all(
        result["positive_count_pass"] is True
        for result in decision["comparisons"].values()
    )
    assert all(
        result["median_pass"] is False
        for result in decision["comparisons"].values()
    )


def test_preregistered_seeds_actually_change_goal_maze_enemy_dynamics() -> None:
    trajectories = set()
    for seed in (811, 821, 823, 827):
        environment = GoalMazeEnvironment(seed=seed)
        adapter = MazeChaseAdapter(environment=environment)
        trace = []
        for action in ("HOLD", "FORWARD", "TURN_LEFT", "HOLD", "TURN_RIGHT", "HOLD"):
            observation = adapter.observe()
            assert_sensory_only_context(observation.context)
            step = adapter.apply_action(action)
            trace.append(
                tuple((enemy["x"], enemy["y"]) for enemy in step.public_state["enemies"])
            )
        trajectories.add(tuple(trace))

    assert len(trajectories) > 1


def test_contract_fails_closed_if_seed_or_threshold_changes() -> None:
    contract = _contract()
    changed = copy.deepcopy(contract)
    changed["replicates"][0]["training_seed"] = 109
    assert validate_contract(changed)["replicates_exact"] is False

    changed = copy.deepcopy(contract)
    changed["confirmatory_rule"]["positive_replicates_required"] = 8
    assert validate_contract(changed)["positive_count_exact"] is False

    changed = copy.deepcopy(contract)
    changed["confirmatory_rule"]["median_reward_difference_minimum"] = 0.0
    assert validate_contract(changed)["median_threshold_exact"] is False


def test_manual_workflow_has_no_result_tunable_inputs_and_is_non_promotional() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "inputs:" not in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "learning_validated" in workflow
    assert "behavioral_promotion_authorized" in workflow
    assert "retention-days: 30" in workflow
