from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.runtime_forced_crash_recovery import (
    EXPECTED_CRASH_EXIT_CODE,
    RECEIPT_SCHEMA,
    evaluate_forced_crash_evidence,
    validate_contract,
)
from neurofly.smoke import _digest_json


CONTRACT = Path("data/runtime_forced_crash_recovery_v01.json")
WORKFLOW = Path(".github/workflows/runtime-forced-crash-recovery.yml")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text())


def _state(*, clears: int, deaths: int, world_ticks: int) -> dict:
    return {
        "last_action": "HOLD",
        "total_clears": clears,
        "total_deaths": deaths,
        "total_world_ticks": world_ticks,
        "brain": {
            "backend": "malecns",
            "telemetry": {
                "brain_ms": 50.0,
                "total_spikes": 1,
            },
        },
    }


def _training_receipt(*, clears_before: int, clears_after: int, deaths: int, world_ticks: int) -> dict:
    state = _state(clears=clears_after, deaths=deaths, world_ticks=world_ticks)
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


def _crash_receipt() -> dict:
    body = {
        "schema": "neurofly-runtime-forced-crash-worker-v0.1",
        "pid": 101,
        "steps_completed_but_unsaved": 1,
        "neural_activity_verified": True,
        "last_state": _state(clears=2, deaths=1, world_ticks=11),
        "unsaved_work_expected_to_be_lost": True,
        "checkpoint_save_called": False,
    }
    body["receipt_sha256"] = _digest_json(body)
    return body


def _cycle(index: int = 1) -> dict:
    pre = {"brain": "a" * 64, "maze": "b" * 64}
    recovery = _training_receipt(
        clears_before=1,
        clears_after=1,
        deaths=1,
        world_ticks=11,
    )
    return {
        "cycle": index,
        "persisted_state_before_crash": {
            "total_clears": 1,
            "total_deaths": 1,
            "total_world_ticks": 10,
        },
        "pre_crash_hashes": pre,
        "post_crash_hashes": copy.deepcopy(pre),
        "post_recovery_hashes": {
            "brain": "c" * 64,
            "maze": "d" * 64,
        },
        "crash_pid": 101 + index,
        "crash_returncode": EXPECTED_CRASH_EXIT_CODE,
        "crash_receipt": _crash_receipt(),
        "recovery_pid": 201 + index,
        "recovery_returncode": 0,
        "recovery_receipt": recovery,
    }


def _report(cycles: list[dict] | None = None) -> dict:
    cycles = cycles or [_cycle(1), _cycle(2), _cycle(3)]
    return evaluate_forced_crash_evidence(
        _contract(),
        source_hash_before={"brain": "e" * 64, "maze": "f" * 64},
        source_hash_after={"brain": "e" * 64, "maze": "f" * 64},
        source_isolated=True,
        cycles=cycles,
        expected_cycles=3,
    )


def test_contract_is_exact_and_claim_limits_stay_closed() -> None:
    contract = _contract()
    gates = validate_contract(contract)

    assert all(gates.values())
    assert all(contract["required_invariants"].values())
    assert all(value is False for value in contract["claim_limits"].values())


def test_structurally_valid_forced_crash_recovery_evidence_passes() -> None:
    report = _report()

    assert report["schema"] == RECEIPT_SCHEMA
    assert report["status"] == "PASS"
    assert report["passed"] is True
    assert report["forced_crash_recovery_execution_verified"] is True
    assert all(report["contract_gates"].values())
    assert all(report["invariants"].values())


def test_gate_fails_if_crash_process_exits_cleanly() -> None:
    cycles = [_cycle(1), _cycle(2), _cycle(3)]
    cycles[1]["crash_returncode"] = 0

    report = _report(cycles)

    assert report["passed"] is False
    assert report["invariants"]["crash_process_exits_nonzero"] is False


def test_gate_fails_if_unsaved_crash_changes_checkpoint_bytes() -> None:
    cycles = [_cycle(1), _cycle(2), _cycle(3)]
    cycles[0]["post_crash_hashes"]["brain"] = "9" * 64

    report = _report(cycles)

    assert report["passed"] is False
    assert report["invariants"]["checkpoint_pair_unchanged_by_unsaved_crash"] is False


def test_gate_fails_if_source_checkpoint_changes() -> None:
    report = evaluate_forced_crash_evidence(
        _contract(),
        source_hash_before={"brain": "e" * 64, "maze": "f" * 64},
        source_hash_after={"brain": "0" * 64, "maze": "f" * 64},
        source_isolated=True,
        cycles=[_cycle(1), _cycle(2), _cycle(3)],
        expected_cycles=3,
    )

    assert report["passed"] is False
    assert report["invariants"]["source_checkpoint_unchanged"] is False


def test_gate_explicitly_does_not_claim_unsaved_work_or_24h_uptime() -> None:
    report = _report()

    assert report["zero_data_loss_claimed"] is False
    assert report["unsaved_work_preserved_claimed"] is False
    assert report["actual_watchdog_dispatch_tested"] is False
    assert report["twenty_four_hour_soak_validated"] is False
    assert report["continuous_single_process_uptime_validated"] is False
    assert report["production_checkpoint_mutated"] is False


def test_manual_workflow_is_isolated_and_never_saves_proof_state_to_production() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "runs/forced-crash-recovery" in workflow
    assert "SOURCE_STATE: runs/free-malecns" in workflow
    assert "twenty_four_hour_soak_validated" in workflow
