from __future__ import annotations

import json
from pathlib import Path

from neurofly.dan_baseline_intervention import _baseline_digest
from neurofly.dan_trace_recentering_intervention import BASELINE_DIGEST, BASELINE_HZ
from neurofly.recentered_reinforcement_discrimination import (
    EXPECTED_ARMS,
    EXPECTED_REPLICATES,
    validate_config,
)


CONFIG = Path("data/recentered_reinforcement_discrimination_v01.json")
FREEZE = Path("data/counterfactual_rule_replay_run1_freeze_v01.json")
WORKFLOW = Path(".github/workflows/recentered-reinforcement-discrimination.yml")


def test_config_is_locked_and_fresh() -> None:
    config = json.loads(CONFIG.read_text())
    gates = validate_config(config)

    assert all(gates.values())
    assert config["status"] == "EXPLORATORY_INTERVENTION_ONLY"
    assert len(EXPECTED_ARMS) == 4
    assert len(EXPECTED_REPLICATES) == 4
    assert all(value is False for value in config["claim_policy"].values())


def test_counterfactual_freeze_preserves_rule_level_result() -> None:
    freeze = json.loads(FREEZE.read_text())

    assert freeze["run_id"] == 35417521260
    assert freeze["receipt_sha256"] == (
        "29f704c07380ac615c6e24566fb6ad14539082ce5521f0d8d1a9aec6b4f12581"
    )
    assert freeze["execution_valid"] is True
    assert freeze["replicate_consistency"]["live_frozen_memory_unchanged"] == "3/3"
    assert (
        freeze["interpretation_limits"][
            "trace_coordinate_mismatch_dominates_large_positive_rule_drift"
        ]
        is True
    )
    assert freeze["interpretation_limits"]["learning_validated"] is False


def test_frozen_baseline_digest_matches() -> None:
    assert _baseline_digest(list(BASELINE_HZ)) == BASELINE_DIGEST


def test_workflow_is_manual_isolated_and_non_promotional() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "recentered_reinforcement_discrimination" in workflow
    assert "EXPLORATORY_INTERVENTION_COMPLETE" in workflow
    assert "true_reinforcement_discriminated" in workflow
    assert "replacement_confirmatory_authorized" in workflow
