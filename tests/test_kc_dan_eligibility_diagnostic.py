from __future__ import annotations

import json
from pathlib import Path

from neurofly.kc_dan_eligibility_diagnostic import (
    BASELINE_DIGEST,
    BASELINE_HZ,
    EXPECTED_ARMS,
    EXPECTED_BINS_PER_DECISION,
    EXPECTED_DECISIONS,
    RuleAdvanceTracer,
    validate_config,
)
from neurofly.smoke import _digest_json


CONFIG = Path("data/kc_dan_eligibility_diagnostic_v01.json")
FREEZE = Path("data/dan_baseline_intervention_run1_freeze_v01.json")
WORKFLOW = Path(".github/workflows/kc-dan-eligibility-diagnostic.yml")


def test_config_is_locked() -> None:
    config = json.loads(CONFIG.read_text())
    gates = validate_config(config)

    assert all(gates.values())
    assert config["status"] == "EXPLORATORY_DIAGNOSTIC_ONLY"
    assert all(value is False for value in config["claim_policy"].values())
    assert len(EXPECTED_ARMS) == 3
    assert EXPECTED_DECISIONS == 60
    assert EXPECTED_BINS_PER_DECISION == 5


def test_intervention_freeze_matches_frozen_baseline() -> None:
    freeze = json.loads(FREEZE.read_text())

    assert freeze["run_id"] == 35348834258
    assert freeze["receipt_sha256"] == (
        "7a679541962dc5cac24b63aeb62a172a71d0875fc9171cc49ac5df29d3eec907"
    )
    assert freeze["execution_valid"] is True
    assert freeze["calibration"]["digest"] == BASELINE_DIGEST
    assert tuple(freeze["calibration"]["values_hz"]) == BASELINE_HZ
    assert _digest_json(list(BASELINE_HZ)) == BASELINE_DIGEST


def test_rule_tracer_restores_monkeypatch_without_execution() -> None:
    import stonkfly.neural.rule as rule

    original = rule.advance
    with RuleAdvanceTracer() as tracer:
        assert rule.advance != original
        assert tracer.rows == []
    assert rule.advance == original


def test_workflow_is_manual_read_only_and_non_promotional() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "kc_dan_eligibility_diagnostic" in workflow
    assert "EXPLORATORY_DIAGNOSTIC_COMPLETE" in workflow
    assert "kc_dan_temporal_drive_causal" in workflow
    assert "dan_trace_state_mismatch_causal" in workflow
    assert "replacement_confirmatory_authorized" in workflow
