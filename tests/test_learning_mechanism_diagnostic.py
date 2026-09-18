from __future__ import annotations

import json
from pathlib import Path

from neurofly.learning_mechanism_diagnostic import (
    EXPECTED_REPLICATES,
    _trace_summary,
    validate_config,
)


CONFIG = Path("data/learning_mechanism_diagnostic_v01.json")
WORKFLOW = Path(".github/workflows/learning-mechanism-diagnostic.yml")


def _row(
    *,
    delivered: str,
    generated_reward: float,
    action: str = "HOLD",
    memory_changed: bool = False,
    reward_spikes: int = 0,
    aversive_spikes: int = 0,
    gate_spikes: int = 0,
    difference_hz: float = 0.0,
    scheduled: str = "none",
    expected: str = "none",
) -> dict:
    return {
        "delivered_reinforcement": delivered,
        "generated_reward": generated_reward,
        "decision_action": action,
        "memory_changed": memory_changed,
        "reward_spikes": reward_spikes,
        "aversive_spikes": aversive_spikes,
        "gate_spikes": gate_spikes,
        "difference_hz": difference_hz,
        "scheduled_reinforcement": scheduled,
        "expected_from_previous_outcome": expected,
    }


def test_diagnostic_config_is_locked_and_fresh() -> None:
    config = json.loads(CONFIG.read_text())
    gates = validate_config(config)

    assert all(gates.values())
    assert config["status"] == "EXPLORATORY_DIAGNOSTIC_ONLY"
    assert all(value is False for value in config["claim_policy"].values())

    seeds = [
        seed
        for _, train_seed, heldout in EXPECTED_REPLICATES
        for seed in (train_seed, *heldout)
    ]
    assert len(seeds) == len(set(seeds))


def test_trace_summary_separates_unreinforced_dan_activity_from_external_pulses() -> None:
    rows = [
        _row(
            delivered="none",
            generated_reward=1.0,
            memory_changed=True,
            reward_spikes=3,
        ),
        _row(
            delivered="reward",
            generated_reward=-10.0,
            action="FORWARD",
            memory_changed=True,
            gate_spikes=2,
            difference_hz=4.0,
            scheduled="reward",
            expected="reward",
        ),
        _row(
            delivered="aversive",
            generated_reward=-0.01,
            action="TURN_LEFT",
            aversive_spikes=2,
            scheduled="aversive",
            expected="aversive",
        ),
    ]

    summary = _trace_summary(rows)

    assert summary["memory_changed_steps"] == 2
    assert summary["memory_changed_none_steps"] == 1
    assert summary["memory_changed_reinforced_steps"] == 1
    assert summary["none_steps_with_endogenous_dan_spikes"] == 1
    assert summary["delivered_reinforcement"] == {
        "aversive": 1,
        "none": 1,
        "reward": 1,
    }
    assert summary["scheduled_reinforcement_matches_previous_outcome"] is True


def test_trace_summary_detects_temporal_schedule_mismatch() -> None:
    rows = [
        _row(delivered="none", generated_reward=1.0),
        _row(
            delivered="none",
            generated_reward=-0.01,
            scheduled="none",
            expected="reward",
        ),
    ]

    summary = _trace_summary(rows)

    assert summary["scheduled_reinforcement_matches_previous_outcome"] is False


def test_manual_diagnostic_workflow_is_isolated_and_non_promotional() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "learning_mechanism_diagnostic" in workflow
    assert "learning_validated" in workflow
    assert "replacement_confirmatory_authorized" in workflow
    assert "EXPLORATORY_DIAGNOSTIC_COMPLETE" in workflow
