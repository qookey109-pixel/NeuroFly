from __future__ import annotations

import inspect
import json
from pathlib import Path

from neurofly.learning_control_study import _evaluate_arm, _run_training_arm
from neurofly.learning_remediation_study import (
    EXPECTED_REPLICATES,
    EXPECTED_SEED_PROBE_STEPS,
    seed_probe,
    validate_config,
)


CONFIG = Path("data/learning_remediation_study_v01.json")
FREEZE = Path("data/confirmatory_learning_run1_freeze_v01.json")
WORKFLOW = Path(".github/workflows/exploratory-learning-remediation.yml")


def test_run1_negative_result_is_frozen_without_rewriting_history() -> None:
    freeze = json.loads(FREEZE.read_text())

    assert freeze["schema"] == "neurofly-confirmatory-run-freeze-v0.1"
    assert freeze["source"]["workflow_run_id"] == 35323343414
    assert (
        freeze["source"]["receipt_sha256"]
        == "610b28444c8d3481397b6a56500e9f4cd17f66e059ce4c3c9cb73ba9fe636b8c"
    )
    assert freeze["raw_result"]["execution_valid"] is True
    assert freeze["raw_result"]["status"] == "CONFIRMATORY_FAIL"
    assert freeze["raw_result"]["confirmatory_primary_pass"] is False
    assert freeze["raw_result"]["learning_validated"] is False

    diagnostic = freeze["post_run_diagnostic"]
    assert diagnostic["historical_receipt_mutated"] is False
    assert diagnostic["replicate_independence_supported"] is False
    assert diagnostic["held_out_seed_effectiveness_supported"] is False
    assert (
        diagnostic["observed_uniqueness_across_8_replicates"]["learning_true"][
            "unique_post_training_checkpoint_shas"
        ]
        == 1
    )


def test_exploratory_remediation_config_is_locked_and_uses_fresh_seeds() -> None:
    config = json.loads(CONFIG.read_text())
    gates = validate_config(config)

    assert all(gates.values())
    configured = [
        seed
        for _, training_seed, heldout in EXPECTED_REPLICATES
        for seed in (training_seed, *heldout)
    ]
    assert len(configured) == len(set(configured))
    assert config["world_mode"]["decision_synchronous_world"] is True
    assert config["world_mode"]["seed_probe_steps"] == EXPECTED_SEED_PROBE_STEPS
    assert all(value is False for value in config["claim_policy"].values())


def test_seed_probe_materially_changes_trajectory_for_each_configured_seed() -> None:
    configured = [
        seed
        for _, training_seed, heldout in EXPECTED_REPLICATES
        for seed in (training_seed, *heldout)
    ]
    digests = [
        seed_probe(seed, steps=EXPECTED_SEED_PROBE_STEPS)["trace_digest"]
        for seed in configured
    ]

    assert len(digests) == len(set(digests))


def test_v01_learning_helpers_keep_legacy_world_mode_by_default() -> None:
    train_default = inspect.signature(_run_training_arm).parameters[
        "decision_synchronous_world"
    ].default
    eval_default = inspect.signature(_evaluate_arm).parameters[
        "decision_synchronous_world"
    ].default

    assert train_default is False
    assert eval_default is False


def test_remediation_workflow_is_manual_isolated_and_non_promotional() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "learning_remediation_study" in workflow
    assert "replacement_confirmatory_authorized" in workflow
    assert "EXPLORATORY_REMEDIATION_COMPLETE" in workflow
