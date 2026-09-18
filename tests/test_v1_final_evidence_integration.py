from __future__ import annotations

import json
from pathlib import Path


MANIFEST = Path("data/v1_final_evidence_integration_v01.json")


def test_final_evidence_integration_manifest_is_non_promotional() -> None:
    payload = json.loads(MANIFEST.read_text())

    assert payload["schema"] == "neurofly-v1-final-evidence-integration-v0.1"
    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["source_prs"] == {
        "real_execution_evidence_freeze": 94,
        "confirmatory_learning_validation": 97,
        "segmented_runtime_soak_evidence": 98,
    }

    assert all(payload["verified_now"].values())
    assert payload["pending_after_authority_integration"] == {
        "confirmatory_learning_execution": True
    }
    assert all(
        value is False
        for value in payload["claims_locked_until_confirmatory_receipt"].values()
    )
    assert all(
        value is False
        for value in payload[
            "claims_remaining_false_even_if_confirmatory_passes"
        ].values()
    )
    assert payload["merge_policy"] == {
        "merge_main_authorized": False,
        "confirmatory_workflow_requires_authority_branch": True,
        "final_v1_release_not_yet_authorized": True,
    }


def test_final_integration_contains_all_required_evidence_surfaces() -> None:
    required = [
        "data/v1_real_execution_evidence_20260918.json",
        "docs/experiments/V1_REAL_EXECUTION_EVIDENCE_20260918.md",
        "data/confirmatory_learning_study_v01.json",
        "src/neurofly/confirmatory_learning_study.py",
        "tests/test_confirmatory_learning_study.py",
        ".github/workflows/confirmatory-learning-study.yml",
        "data/v1_segmented_runtime_soak_20260918.json",
        "src/neurofly/runtime_soak_evidence.py",
        "tests/test_runtime_soak_evidence.py",
        "docs/experiments/V1_SEGMENTED_RUNTIME_24H_SOAK.md",
    ]

    assert all(Path(path).is_file() for path in required)
