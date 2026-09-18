from __future__ import annotations

import json
from pathlib import Path

from neurofly.dan_baseline_intervention import (
    EXPECTED_CALIBRATION_SEEDS,
    EXPECTED_REPLICATES,
    _baseline_digest,
    _trace_summary,
    validate_config,
)


CONFIG = Path("data/dan_baseline_intervention_v01.json")
WORKFLOW = Path(".github/workflows/dan-baseline-intervention.yml")
FREEZE = Path("data/learning_mechanism_diagnostic_run1_freeze_v01.json")


def test_intervention_config_is_locked_and_uses_fresh_disjoint_seeds() -> None:
    config = json.loads(CONFIG.read_text())
    gates = validate_config(config)

    assert all(gates.values())
    assert config["status"] == "EXPLORATORY_INTERVENTION_ONLY"
    assert all(value is False for value in config["claim_policy"].values())

    seeds = [
        *EXPECTED_CALIBRATION_SEEDS,
        *[
            seed
            for _, training_seed, heldout in EXPECTED_REPLICATES
            for seed in (training_seed, *heldout)
        ],
    ]
    assert len(seeds) == len(set(seeds))


def test_diagnostic_freeze_preserves_observed_unreinforced_drift() -> None:
    freeze = json.loads(FREEZE.read_text())

    assert freeze["run_id"] == 35343487907
    assert freeze["receipt_sha256"] == (
        "8f1e34f5fd4795869c8d4251eccd12a196e2c14e5d56118fb810078972142db2"
    )
    assert freeze["execution_valid"] is True
    assert freeze["aggregate"]["learning_none"]["mean_memory_changed_steps"] == 60
    assert (
        freeze["aggregate"]["learning_none"]["mean_memory_changed_none_steps"]
        == 60
    )
    assert (
        freeze["interpretation_limits"]["unreinforced_plastic_drift_observed"]
        is True
    )
    assert (
        freeze["interpretation_limits"]["unreinforced_plastic_drift_causal"]
        is False
    )


def test_baseline_digest_is_order_and_value_sensitive() -> None:
    a = _baseline_digest([0.0, 1.0, 2.0])
    b = _baseline_digest([0.0, 1.0, 2.0])
    c = _baseline_digest([0.0, 2.0, 1.0])
    d = _baseline_digest([0.0, 1.0, 2.1])

    assert a == b
    assert a != c
    assert a != d


def test_trace_summary_counts_memory_drift_and_gate_zero() -> None:
    rows = [
        {
            "action": "HOLD",
            "gate_spikes": 0,
            "memory_changed": True,
            "reward_spikes": 0,
            "aversive_spikes": 12,
        },
        {
            "action": "FORWARD",
            "gate_spikes": 2,
            "memory_changed": False,
            "reward_spikes": 1,
            "aversive_spikes": 10,
        },
    ]

    summary = _trace_summary(rows)

    assert summary["steps"] == 2
    assert summary["hold_fraction"] == 0.5
    assert summary["gate_zero_fraction"] == 0.5
    assert summary["memory_changed_steps"] == 1
    assert summary["mean_reward_spikes"] == 0.5
    assert summary["mean_aversive_spikes"] == 11.0


def test_workflow_is_manual_isolated_and_non_promotional() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "dan_baseline_intervention" in workflow
    assert "EXPLORATORY_INTERVENTION_COMPLETE" in workflow
    assert "learning_validated" in workflow
    assert "task_conditioned_dan_baseline_causal" in workflow
    assert "biological_dan_resting_rate_established" in workflow
    assert "replacement_confirmatory_authorized" in workflow
