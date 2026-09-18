from __future__ import annotations

import json
from pathlib import Path


EVIDENCE = Path("data/v1_real_execution_evidence_20260918.json")


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text())


def test_real_execution_evidence_snapshot_is_frozen_and_consistent() -> None:
    payload = _evidence()

    assert payload["schema"] == "neurofly-v1-real-execution-evidence-v0.1"
    assert payload["status"] == "EVIDENCE_FROZEN"
    assert payload["workflow_head_sha"] == "35341d96843d846388ace5520569187c0521ade3"
    assert payload["shared_source_checkpoint_sha256"] == (
        "afbe266465e0b14c4a353f2ee7123c4a2cc85835bf3db90b1b8cd9b60e366ddd"
    )

    light = payload["light_chase_real_malecns"]
    assert light["status"] == "PASS"
    assert light["passed"] is True
    assert light["neural_activity_verified"] is True
    assert light["learning_enabled"] is False
    assert light["steps"] == 3
    assert light["action_counts"] == {"TURN_LEFT": 3}

    crash = payload["forced_crash_recovery"]
    assert crash["status"] == "PASS"
    assert crash["passed"] is True
    assert crash["cycles_completed"] == 3
    assert crash["expected_cycles"] == 3
    assert crash["source_checkpoint_unchanged"] is True
    assert crash["checkpoint_pair_unchanged_by_unsaved_crash"] is True
    assert crash["recovery_real_malecns_verified"] is True
    assert crash["production_checkpoint_mutated"] is False

    learning = payload["learning_control_study"]
    assert learning["status"] == "HUMAN_REVIEW_REQUIRED"
    assert learning["passed_execution_gate"] is True
    assert learning["learning_validated"] is False
    assert learning["generalization_validated"] is False
    assert learning["causal_learning_claim_authorized"] is False
    assert learning["behavioral_promotion_authorized"] is False


def test_exploratory_learning_effects_are_preserved_without_promotion() -> None:
    learning = _evidence()["learning_control_study"]
    effects = learning["descriptive_effects"]

    assert effects["learning_true_minus_frozen_true"]["mean_total_reward"] == 3.0
    assert effects["learning_true_minus_frozen_true"]["mean_total_food"] == 3.0
    assert effects["learning_true_minus_learning_scrambled"]["mean_total_reward"] == 3.0
    assert effects["learning_true_minus_learning_scrambled"]["mean_total_food"] == 3.0
    assert effects["learning_true_minus_learning_sensory_off"]["mean_total_reward"] == 2.0
    assert effects["learning_true_minus_learning_sensory_off"]["mean_total_food"] == 2.0

    assert learning["learning_validated"] is False
    assert learning["generalization_validated"] is False


def test_claim_locks_remain_closed() -> None:
    payload = _evidence()
    assert all(value is False for value in payload["claims_still_locked"].values())
