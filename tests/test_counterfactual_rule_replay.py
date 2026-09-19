from __future__ import annotations

import json
from pathlib import Path

from neurofly.counterfactual_rule_replay import (
    BASELINE_DIGEST,
    BASELINE_HZ,
    EXPECTED_REPLAYS,
    EXPECTED_REPLICATES,
    validate_config,
)
from neurofly.dan_baseline_intervention import _baseline_digest


CONFIG = Path("data/counterfactual_rule_replay_diagnostic_v01.json")
FREEZE = Path("data/dan_trace_recentering_run1_freeze_v01.json")
WORKFLOW = Path(".github/workflows/counterfactual-rule-replay-diagnostic.yml")


def test_config_is_locked_and_fresh() -> None:
    config = json.loads(CONFIG.read_text())
    gates = validate_config(config)

    assert all(gates.values())
    assert config["status"] == "EXPLORATORY_DIAGNOSTIC_ONLY"
    assert len(EXPECTED_REPLAYS) == 3
    assert len(EXPECTED_REPLICATES) == 3
    assert all(value is False for value in config["claim_policy"].values())


def test_recentering_freeze_preserves_robust_drift_reduction() -> None:
    freeze = json.loads(FREEZE.read_text())

    assert freeze["run_id"] == 35415979900
    assert freeze["receipt_sha256"] == (
        "e31b82a1649ee9c4e8d3ac584fc2910d1152f5980ba75116392894184576a589"
    )
    assert freeze["execution_valid"] is True
    assert freeze["replicate_consistency"]["unrecentered_final_positive_replicates"] == "4/4"
    assert freeze["replicate_consistency"]["recentered_final_small_negative_replicates"] == "4/4"
    assert freeze["interpretation_limits"]["heldout_behavioral_improvement_not_established"] is True


def test_frozen_baseline_digest_matches() -> None:
    assert _baseline_digest(list(BASELINE_HZ)) == BASELINE_DIGEST


def test_workflow_is_manual_frozen_and_non_promotional() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "counterfactual_rule_replay" in workflow
    assert "EXPLORATORY_DIAGNOSTIC_COMPLETE" in workflow
    assert "baseline_shift_rule_effect_causal" in workflow
    assert "replacement_confirmatory_authorized" in workflow
