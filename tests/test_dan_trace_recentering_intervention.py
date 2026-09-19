from __future__ import annotations

import json
from pathlib import Path

from neurofly.dan_trace_recentering_intervention import (
    BASELINE_DIGEST,
    BASELINE_HZ,
    EXPECTED_ARMS,
    EXPECTED_REPLICATES,
    validate_config,
)
from neurofly.dan_baseline_intervention import _baseline_digest


CONFIG = Path("data/dan_trace_recentering_intervention_v01.json")
FREEZE = Path("data/kc_dan_eligibility_run1_freeze_v01.json")
WORKFLOW = Path(".github/workflows/dan-trace-recentering-intervention.yml")


def test_config_is_locked_and_fresh() -> None:
    config = json.loads(CONFIG.read_text())
    gates = validate_config(config)

    assert all(gates.values())
    assert config["status"] == "EXPLORATORY_INTERVENTION_ONLY"
    assert all(value is False for value in config["claim_policy"].values())
    assert len(EXPECTED_ARMS) == 4
    assert len(EXPECTED_REPLICATES) == 4


def test_diagnostic_freeze_supports_trace_mismatch_candidate_only() -> None:
    freeze = json.loads(FREEZE.read_text())

    assert freeze["run_id"] == 35413358900
    assert freeze["receipt_sha256"] == (
        "9726a534447246c6de42c33a029132d47dcbcfbcb200a25e5e1c52b0d5060456"
    )
    assert freeze["execution_valid"] is True
    assert freeze["interpretation_limits"]["checkpoint_trace_state_mismatch_observed"] is True
    assert freeze["interpretation_limits"]["mismatch_is_not_sufficient_to_explain_full_run"] is True
    assert freeze["interpretation_limits"]["dan_trace_state_mismatch_causal"] is False


def test_frozen_baseline_digest_matches_previous_intervention() -> None:
    assert _baseline_digest(list(BASELINE_HZ)) == BASELINE_DIGEST


def test_workflow_is_manual_read_only_and_non_promotional() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "dan_trace_recentering_intervention" in workflow
    assert "EXPLORATORY_INTERVENTION_COMPLETE" in workflow
    assert "dan_trace_state_mismatch_causal" in workflow
    assert "trace_recentering_remediation_validated" in workflow
    assert "replacement_confirmatory_authorized" in workflow
