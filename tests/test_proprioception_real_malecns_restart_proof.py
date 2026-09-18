from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.proprioception import neutral_proprioception
from neurofly.proprioception_real_malecns_restart_proof import (
    RECEIPT_SCHEMA,
    evaluate_restart_evidence,
)
from neurofly.smoke import _digest_json


CONTRACT = Path("data/proprioception_real_malecns_restart_proof_v01.json")
WORKFLOW = Path(".github/workflows/proprioception-real-malecns-restart-proof.yml")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text())


def _training_receipt(*, clears_before: int, clears_after: int, ticks: int) -> dict:
    proprioception = neutral_proprioception()
    state = {
        "total_clears": clears_after,
        "total_deaths": 2,
        "total_world_ticks": ticks,
        "human_diagnostics": {
            "proprioception": proprioception,
            "proprioception_temporal": {
                "sample_count": 1,
                "samples": [{"sequence": 1, "channels": proprioception["channels"]}],
            },
        },
        "brain": {
            "backend": "malecns",
            "telemetry": {
                "brain_ms": 1.0,
                "total_spikes": 1,
            },
        },
    }
    receipt = {
        "schema": "neurofly-self-training-v3",
        "passed": True,
        "backend": "malecns",
        "neural_activity_verified": True,
        "clears_before": clears_before,
        "clears_after": clears_after,
        "trajectory": [state],
        "final_state": state,
    }
    receipt["receipt_sha256"] = _digest_json(receipt)
    return receipt


def _report(contract: dict | None = None) -> dict:
    a = _training_receipt(clears_before=3, clears_after=4, ticks=20)
    b = _training_receipt(clears_before=4, clears_after=4, ticks=21)
    pending = a["trajectory"][0]["human_diagnostics"]["proprioception"]
    return evaluate_restart_evidence(
        contract or _contract(),
        phase_a_receipt=a,
        phase_b_receipt=b,
        phase_a_checkpoint_hashes={"brain": "a" * 64, "maze": "b" * 64},
        pre_b_checkpoint_hashes={"brain": "a" * 64, "maze": "b" * 64},
        post_b_checkpoint_hashes={"brain": "c" * 64, "maze": "d" * 64},
        phase_a_pending_proprioception=pending,
        phase_a_pid=101,
        phase_b_pid=202,
        phase_a_returncode=0,
        phase_b_returncode=0,
        source_checkpoint_isolated=True,
    )


def test_structurally_valid_real_restart_evidence_passes() -> None:
    report = _report()

    assert report["schema"] == RECEIPT_SCHEMA
    assert report["status"] == "PASS"
    assert report["passed"] is True
    assert all(report["contract_gates"].values())
    assert all(report["invariants"].values())
    assert report["actual_malecns_process_restart_executed"] is True
    assert report["malecns_checkpoint_file_continuity_verified"] is True
    assert report["proprioception_first_handoff_continuity_verified"] is True


def test_gate_does_not_promote_biological_claims() -> None:
    report = _report()

    assert report["biological_memory_equivalence_proven"] is False
    assert report["snpp39_snpp41_polarity_resolved"] is False
    assert report["biological_current_calibrated"] is False
    assert report["biological_latency_resolved"] is False
    assert report["continuous_single_process_24_7_claimed"] is False
    assert report["systematic_type_mapping_exposed"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["runtime_gating_authorized"] is False
    assert report["neural_payload_promotion_authorized"] is False


def test_gate_fails_if_checkpoint_changes_before_process_b() -> None:
    a = _training_receipt(clears_before=3, clears_after=4, ticks=20)
    b = _training_receipt(clears_before=4, clears_after=4, ticks=21)
    pending = a["trajectory"][0]["human_diagnostics"]["proprioception"]
    report = evaluate_restart_evidence(
        _contract(),
        phase_a_receipt=a,
        phase_b_receipt=b,
        phase_a_checkpoint_hashes={"brain": "a" * 64, "maze": "b" * 64},
        pre_b_checkpoint_hashes={"brain": "f" * 64, "maze": "b" * 64},
        post_b_checkpoint_hashes={"brain": "c" * 64, "maze": "d" * 64},
        phase_a_pending_proprioception=pending,
        phase_a_pid=101,
        phase_b_pid=202,
        phase_a_returncode=0,
        phase_b_returncode=0,
        source_checkpoint_isolated=True,
    )
    assert report["passed"] is False
    assert report["invariants"]["checkpoint_unchanged_between_processes"] is False


def test_gate_fails_if_first_handoff_does_not_match_pending_receptor() -> None:
    a = _training_receipt(clears_before=3, clears_after=4, ticks=20)
    b = _training_receipt(clears_before=4, clears_after=4, ticks=21)
    pending = copy.deepcopy(a["trajectory"][0]["human_diagnostics"]["proprioception"])
    pending["channels"]["hook_extension"]["level"] = 0.5

    report = evaluate_restart_evidence(
        _contract(),
        phase_a_receipt=a,
        phase_b_receipt=b,
        phase_a_checkpoint_hashes={"brain": "a" * 64, "maze": "b" * 64},
        pre_b_checkpoint_hashes={"brain": "a" * 64, "maze": "b" * 64},
        post_b_checkpoint_hashes={"brain": "c" * 64, "maze": "d" * 64},
        phase_a_pending_proprioception=pending,
        phase_a_pid=101,
        phase_b_pid=202,
        phase_a_returncode=0,
        phase_b_returncode=0,
        source_checkpoint_isolated=True,
    )
    assert report["passed"] is False
    assert (
        report["invariants"]["pending_proprioception_matches_phase_b_first_handoff"]
        is False
    )


def test_gate_fails_if_contract_opens_runtime_lock() -> None:
    contract = copy.deepcopy(_contract())
    contract["hard_locks"]["runtime_gating_authorized"] = True

    report = _report(contract)
    assert report["passed"] is False
    assert report["contract_gates"]["hard_locks_exact"] is False


def test_manual_workflow_is_isolated_and_does_not_mutate_production_state() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "push:" not in workflow
    assert "schedule:" not in workflow
    assert "runs-on: ubuntu-latest" in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "Continue NeuroFly" not in workflow
    assert "runs/restart-proof" in workflow
    assert "runs/free-malecns/brain.npz" in workflow
