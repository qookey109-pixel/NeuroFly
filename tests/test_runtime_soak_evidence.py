from __future__ import annotations

import json
from pathlib import Path

from neurofly.runtime_soak_evidence import validate_segmented_soak_evidence


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data" / "v1_segmented_runtime_soak_20260918.json"
WORKFLOW = ROOT / ".github" / "workflows" / "full-malecns-free.yml"


def test_segmented_24h_soak_evidence_recomputes_and_passes() -> None:
    payload = json.loads(EVIDENCE.read_text())
    gates = validate_segmented_soak_evidence(payload)

    assert all(gates.values())
    observed = payload["observed"]
    assert observed["first_run_number"] == 159
    assert observed["last_run_number"] == 461
    assert observed["run_count"] == 303
    assert observed["wall_clock_hours"] == 48.428889
    assert observed["all_runs_success"] is True
    assert observed["consecutive_run_numbers"] is True
    assert observed["maximum_positive_handoff_idle_gap_seconds"] == 0


def test_all_frozen_runs_are_exactly_consecutive_successes() -> None:
    payload = json.loads(EVIDENCE.read_text())
    runs = payload["runs"]

    assert [item["run_number"] for item in runs] == list(range(159, 462))
    assert all(item["event"] == "workflow_dispatch" for item in runs)
    assert all(item["status"] == "completed" for item in runs)
    assert all(item["conclusion"] == "success" for item in runs)


def test_soak_does_not_overclaim_single_process_or_zero_data_loss() -> None:
    payload = json.loads(EVIDENCE.read_text())
    interpretation = payload["interpretation"]

    assert interpretation["segmented_runtime_24h_soak_validated"] is True
    assert interpretation["bounded_runner_checkpoint_chain_validated"] is True
    assert interpretation["continuous_single_process_uptime_validated"] is False
    assert interpretation["zero_data_loss_claimed"] is False
    assert interpretation["storage_corruption_immunity_claimed"] is False
    assert interpretation["every_unsaved_decision_preserved_claimed"] is False


def test_curriculum_workflow_success_depends_on_training_and_state_persistence() -> None:
    workflow = WORKFLOW.read_text()

    assert "name: Let MaleCNS train through staged curriculum" in workflow
    assert "name: Save isolated V0.6 brain and curriculum state" in workflow
    assert "steps.train.outcome == 'success'" in workflow
    assert "uses: actions/cache/save@v4" in workflow
    assert "continue-on-error: true\n        uses: actions/cache/save@v4" not in workflow
    assert "concurrency:" in workflow
    assert "group: neurofly-v06-curriculum-training" in workflow
