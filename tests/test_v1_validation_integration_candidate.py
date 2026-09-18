from __future__ import annotations

import json
from pathlib import Path


MANIFEST = Path("data/v1_validation_integration_candidate_v01.json")


def test_v1_validation_integration_candidate_is_non_promotional() -> None:
    payload = json.loads(MANIFEST.read_text())

    assert payload["schema"] == "neurofly-v1-validation-integration-candidate-v0.1"
    assert payload["status"] == "REVIEW_REQUIRED"
    assert all(payload["validated_now"].values())
    assert payload["confirmatory_pending"] == {
        "confirmatory_learning_workflow_integrated": True,
        "confirmatory_learning_real_execution_completed": False,
        "learning_validated": False,
        "within_task_heldout_generalization_supported": False,
        "causal_learning_claim_authorized": False,
    }
    assert all(value is False for value in payload["claims_locked_false"].values())
    assert payload["release_gate"] == {
        "authority_merge_authorized": False,
        "confirmatory_execution_required_before_final_v1_release": True,
        "readme_version_consolidation_pending": True,
    }


def test_v1_validation_candidate_contains_frozen_evidence_and_confirmatory_workflow() -> None:
    required = [
        Path("data/v1_real_execution_evidence_20260918.json"),
        Path("data/v1_segmented_runtime_soak_20260918.json"),
        Path("data/confirmatory_learning_study_v01.json"),
        Path(".github/workflows/confirmatory-learning-study.yml"),
        Path("src/neurofly/confirmatory_learning_study.py"),
        Path("src/neurofly/runtime_soak_evidence.py"),
    ]
    assert all(path.is_file() for path in required)
