from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from neurofly.brain_runtime import BrainDecision
from neurofly.learning_control_study import (
    EXPECTED_ARMS,
    EXPECTED_HELD_OUT_SEEDS,
    ControlledBrain,
    descriptive_effects,
    validate_contract,
)


CONTRACT = Path("data/learning_control_study_v01.json")
WORKFLOW = Path(".github/workflows/learning-control-study.yml")


class CaptureBrain:
    name = "malecns"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def decide(self, frame, reinforcement="none", *, context=None) -> BrainDecision:
        self.calls.append(
            {
                "frame": copy.deepcopy(frame),
                "reinforcement": reinforcement,
                "context": copy.deepcopy(context),
            }
        )
        return BrainDecision(
            action="HOLD",
            backend="malecns",
            telemetry={"total_spikes": 1},
        )

    def save(self, path) -> None:
        Path(path).write_text("capture\n")


def _contract() -> dict[str, Any]:
    return json.loads(CONTRACT.read_text())


def test_preregistered_contract_is_exact_and_claims_stay_locked() -> None:
    contract = _contract()
    gates = validate_contract(contract)

    assert all(gates.values())
    assert tuple(
        (
            arm["name"],
            arm["learning"],
            arm["sensory_mode"],
            arm["reinforcement_mode"],
        )
        for arm in contract["arms"]
    ) == EXPECTED_ARMS
    assert tuple(contract["evaluation"]["held_out_seeds"]) == EXPECTED_HELD_OUT_SEEDS
    assert all(value is False for value in contract["claim_limits"].values())


def test_true_control_passes_sensory_and_reinforcement_through() -> None:
    inner = CaptureBrain()
    brain = ControlledBrain(
        inner,
        sensory_mode="normal",
        reinforcement_mode="true",
        scramble_seed=1,
    )
    frame = [[[10, 20, 30]]]
    context = {"olfaction": {"model": "example"}, "fly": {"x": 1, "y": 2}}

    brain.decide(frame, "reward", context=context)

    call = inner.calls[0]
    assert call["frame"] == frame
    assert call["reinforcement"] == "reward"
    assert call["context"] == context


def test_sensory_off_blanks_frame_and_strips_context() -> None:
    inner = CaptureBrain()
    brain = ControlledBrain(
        inner,
        sensory_mode="off",
        reinforcement_mode="true",
        scramble_seed=2,
    )

    brain.decide(
        [[[10, 20, 30], [40, 50, 60]]],
        "aversive",
        context={"secret": 1},
    )

    call = inner.calls[0]
    assert call["frame"] == [[[0, 0, 0], [0, 0, 0]]]
    assert call["context"] == {}
    assert call["reinforcement"] == "aversive"


def test_evaluation_none_mode_suppresses_incoming_reinforcement() -> None:
    inner = CaptureBrain()
    brain = ControlledBrain(
        inner,
        sensory_mode="normal",
        reinforcement_mode="none",
        scramble_seed=3,
    )

    brain.decide([[[0, 0, 0]]], "reward", context={})
    brain.decide([[[0, 0, 0]]], "aversive", context={})

    assert [call["reinforcement"] for call in inner.calls] == ["none", "none"]
    assert brain.delivered_reinforcement == {"none": 2}


def test_scrambled_reinforcement_is_deterministic_and_outcome_independent() -> None:
    sequence = ["reward", "aversive", "none", "reward"] * 8

    def delivered(incoming):
        inner = CaptureBrain()
        brain = ControlledBrain(
            inner,
            sensory_mode="normal",
            reinforcement_mode="scrambled",
            scramble_seed=109,
        )
        for item in incoming:
            brain.decide([[[0, 0, 0]]], item, context={})
        return [call["reinforcement"] for call in inner.calls]

    a = delivered(sequence)
    b = delivered(list(reversed(sequence)))

    assert a == b
    assert set(a) <= {"none", "reward", "aversive"}
    assert len(set(a)) >= 2


def test_descriptive_effects_report_deltas_without_auto_verdict() -> None:
    def arm(reward, clears, food, deaths, hold):
        return {
            "evaluation": {
                "aggregate": {
                    "mean_total_reward": reward,
                    "mean_total_clears": clears,
                    "mean_total_food": food,
                    "mean_total_deaths": deaths,
                    "mean_hold_fraction": hold,
                }
            }
        }

    results = {
        "learning_true": arm(5.0, 2.0, 8.0, 1.0, 0.1),
        "frozen_true": arm(3.0, 1.0, 5.0, 2.0, 0.2),
        "learning_scrambled": arm(4.0, 1.0, 7.0, 1.0, 0.15),
        "learning_sensory_off": arm(0.0, 0.0, 1.0, 3.0, 0.8),
    }
    effects = descriptive_effects(results)

    assert effects["learning_true_minus_frozen_true"]["mean_total_reward"] == 2.0
    assert (
        effects["learning_true_minus_learning_sensory_off"]["mean_hold_fraction"]
        == -0.7
    )
    encoded = json.dumps(effects).lower()
    assert "winner" not in encoded
    assert "validated" not in encoded


def test_contract_fails_closed_if_arm_is_removed_or_claim_is_opened() -> None:
    contract = _contract()
    contract["arms"] = contract["arms"][:-1]
    assert validate_contract(contract)["arms_exact"] is False

    contract = _contract()
    contract["claim_limits"]["learning_validated"] = True
    assert validate_contract(contract)["claim_limits_all_false"] is False


def test_manual_workflow_is_isolated_and_non_promotional() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "learning_validated" in workflow
    assert "HUMAN_REVIEW_REQUIRED" in workflow
