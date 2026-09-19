from __future__ import annotations

import json
from pathlib import Path

from neurofly.external_reinforcement_increment import (
    EXPECTED_CONDITIONS,
    EXPECTED_REPLICATES,
    validate_config,
)

CONFIG=Path("data/external_reinforcement_increment_diagnostic_v01.json")
FREEZE=Path("data/recentered_reinforcement_discrimination_run1_freeze_v01.json")
WORKFLOW=Path(".github/workflows/external-reinforcement-increment-diagnostic.yml")


def test_config_locked_fresh_and_counterfactual() -> None:
    c=json.loads(CONFIG.read_text())
    assert all(validate_config(c).values())
    assert len(EXPECTED_CONDITIONS)==2
    assert len(EXPECTED_REPLICATES)==4
    assert all(v is False for v in c["claim_policy"].values())


def test_run1_freeze_preserves_limits() -> None:
    f=json.loads(FREEZE.read_text())
    assert f["run_id"]==35419000124
    assert f["receipt_sha256"]=="fad3e8a132ef13e474d7656a99027c41fa068f8d2108174beba9f7684759400d"
    assert f["execution_valid"] is True
    assert f["interpretation_limits"]["aggregate_true_above_none_scrambled_and_frozen"] is True
    assert f["interpretation_limits"]["replicate_consistency_insufficient"] is True
    assert f["interpretation_limits"]["learning_validated"] is False


def test_workflow_manual_artifact_only() -> None:
    w=WORKFLOW.read_text()
    assert "workflow_dispatch:" in w
    assert "schedule:" not in w
    assert "push:" not in w
    assert "actions/cache/restore@v4" in w
    assert "actions/cache/save@v4" not in w
    assert "git push" not in w
    assert "external_reinforcement_increment" in w
    assert "replacement_confirmatory_authorized" in w


def test_external_current_matches_compact_dan_rate_shape() -> None:
    import numpy as np
    from neurofly.external_reinforcement_increment import ExternalIncrementTracer

    tracer=object.__new__(ExternalIncrementTracer)
    tracer.dan_count=17
    tracer.reward_count=15
    tracer.pulse_current=20.0

    reward=tracer._external_current("reward",0)
    aversive=tracer._external_current("aversive",0)
    none=tracer._external_current("none",0)

    assert reward.shape==(17,)
    assert aversive.shape==(17,)
    assert np.all(reward[:15]==20.0) and np.all(reward[15:]==0.0)
    assert np.all(aversive[:15]==0.0) and np.all(aversive[15:]==20.0)
    assert np.all(none==0.0)
