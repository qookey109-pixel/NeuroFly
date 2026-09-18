from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .sensory_contract import assert_unprivileged_agent_input
from .smoke import _digest_json


CONTRACT_SCHEMA = "neurofly-proprioception-real-malecns-restart-proof-v0.1"
RECEIPT_SCHEMA = "neurofly-proprioception-real-malecns-restart-receipt-v0.1"
STATUS = "EXECUTION_REQUIRED"
SCOPE = "real-malecns-process-restart-proprioception-continuity"
UPSTREAM_PR = 84
UPSTREAM_HEAD = "84489b1c732fa53591c936183a8db6947f753611"
EXPECTED_REQUIRED_INVARIANTS = {
    "phase_a_real_malecns_receipt_verified",
    "phase_b_real_malecns_receipt_verified",
    "two_separate_python_processes_observed",
    "phase_a_checkpoint_exists",
    "checkpoint_unchanged_between_processes",
    "pending_proprioception_matches_phase_b_first_handoff",
    "phase_b_first_handoff_unprivileged",
    "clears_resume_monotonically",
    "deaths_resume_monotonically",
    "world_ticks_resume_monotonically",
    "production_checkpoint_copy_isolated",
}
EXPECTED_CLAIM_LIMITS = {
    "snpp39_snpp41_polarity_resolved",
    "biological_current_calibrated",
    "biological_latency_resolved",
    "biological_memory_equivalence_proven",
    "continuous_single_process_24_7_claimed",
}
EXPECTED_HARD_LOCKS = {
    "systematic_type_mapping_exposed",
    "current_calibration_authorized",
    "stimulation_enabled",
    "runtime_transduction_enabled",
    "runtime_gating_authorized",
    "neural_payload_promotion_authorized",
}


def _all_true_exact(payload: Any, keys: set[str]) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload) == keys
        and all(payload[key] is True for key in keys)
    )


def _all_false_exact(payload: Any, keys: set[str]) -> bool:
    return (
        isinstance(payload, dict)
        and set(payload) == keys
        and all(payload[key] is False for key in keys)
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _verified_training_receipt(receipt: dict[str, Any]) -> bool:
    supplied_digest = receipt.get("receipt_sha256")
    digest_payload = copy.deepcopy(receipt)
    digest_payload.pop("receipt_sha256", None)

    if (
        receipt.get("schema") != "neurofly-self-training-v3"
        or receipt.get("passed") is not True
        or receipt.get("backend") != "malecns"
        or receipt.get("neural_activity_verified") is not True
        or not isinstance(supplied_digest, str)
        or supplied_digest != _digest_json(digest_payload)
    ):
        return False

    trajectory = receipt.get("trajectory")
    if not isinstance(trajectory, list) or not trajectory:
        return False
    first = trajectory[0]
    brain = first.get("brain") if isinstance(first, dict) else None
    telemetry = brain.get("telemetry") if isinstance(brain, dict) else None
    try:
        return (
            isinstance(brain, dict)
            and brain.get("backend") == "malecns"
            and isinstance(telemetry, dict)
            and int(telemetry.get("total_spikes") or 0) > 0
        )
    except (TypeError, ValueError, OverflowError):
        return False


def _first_public_proprioception(receipt: dict[str, Any]) -> dict[str, Any] | None:
    trajectory = receipt.get("trajectory")
    if not isinstance(trajectory, list) or not trajectory:
        return None
    first = trajectory[0]
    if not isinstance(first, dict):
        return None
    diagnostics = first.get("human_diagnostics")
    if not isinstance(diagnostics, dict):
        return None
    payload = diagnostics.get("proprioception")
    return copy.deepcopy(payload) if isinstance(payload, dict) else None


def _counter(state: dict[str, Any], name: str) -> int:
    try:
        return int(state.get(name) or 0)
    except (TypeError, ValueError, OverflowError):
        return -1


def evaluate_restart_evidence(
    contract: dict[str, Any],
    *,
    phase_a_receipt: dict[str, Any],
    phase_b_receipt: dict[str, Any],
    phase_a_checkpoint_hashes: dict[str, str],
    pre_b_checkpoint_hashes: dict[str, str],
    post_b_checkpoint_hashes: dict[str, str],
    phase_a_pending_proprioception: dict[str, Any] | None,
    phase_a_pid: int,
    phase_b_pid: int,
    phase_a_returncode: int,
    phase_b_returncode: int,
    source_checkpoint_isolated: bool,
) -> dict[str, Any]:
    upstream = contract.get("upstream", {})
    contract_gates = {
        "schema_exact": contract.get("schema") == CONTRACT_SCHEMA,
        "status_exact": contract.get("status") == STATUS,
        "scope_exact": contract.get("scope") == SCOPE,
        "upstream_pr_exact": upstream.get("pull_request") == UPSTREAM_PR,
        "upstream_head_exact": upstream.get("head_sha") == UPSTREAM_HEAD,
        "proof_mode_exact": contract.get("proof_mode")
        == "two-sequential-real-malecns-python-processes",
        "production_state_not_mutated": contract.get("production_state_mutated") is False,
        "required_invariants_exact": _all_true_exact(
            contract.get("required_invariants"), EXPECTED_REQUIRED_INVARIANTS
        ),
        "claim_limits_exact": _all_false_exact(
            contract.get("claim_limits"), EXPECTED_CLAIM_LIMITS
        ),
        "hard_locks_exact": _all_false_exact(
            contract.get("hard_locks"), EXPECTED_HARD_LOCKS
        ),
    }

    phase_a_verified = (
        phase_a_returncode == 0 and _verified_training_receipt(phase_a_receipt)
    )
    phase_b_verified = (
        phase_b_returncode == 0 and _verified_training_receipt(phase_b_receipt)
    )
    first_b_proprioception = _first_public_proprioception(phase_b_receipt)

    first_handoff_unprivileged = False
    if isinstance(first_b_proprioception, dict):
        try:
            assert_unprivileged_agent_input(
                {"proprioception": first_b_proprioception}
            )
            first_handoff_unprivileged = True
        except ValueError:
            first_handoff_unprivileged = False

    a_final = phase_a_receipt.get("final_state")
    b_final = phase_b_receipt.get("final_state")
    if not isinstance(a_final, dict):
        a_final = {}
    if not isinstance(b_final, dict):
        b_final = {}

    invariants = {
        "phase_a_real_malecns_receipt_verified": phase_a_verified,
        "phase_b_real_malecns_receipt_verified": phase_b_verified,
        "two_separate_python_processes_observed": (
            phase_a_pid > 0 and phase_b_pid > 0 and phase_a_pid != phase_b_pid
        ),
        "phase_a_checkpoint_exists": (
            set(phase_a_checkpoint_hashes) == {"brain", "maze"}
            and all(bool(value) for value in phase_a_checkpoint_hashes.values())
        ),
        "checkpoint_unchanged_between_processes": (
            phase_a_checkpoint_hashes == pre_b_checkpoint_hashes
        ),
        "pending_proprioception_matches_phase_b_first_handoff": (
            isinstance(phase_a_pending_proprioception, dict)
            and phase_a_pending_proprioception == first_b_proprioception
        ),
        "phase_b_first_handoff_unprivileged": first_handoff_unprivileged,
        "clears_resume_monotonically": (
            phase_b_receipt.get("clears_before") == phase_a_receipt.get("clears_after")
            and _counter(b_final, "total_clears") >= _counter(a_final, "total_clears")
        ),
        "deaths_resume_monotonically": (
            _counter(b_final, "total_deaths") >= _counter(a_final, "total_deaths")
        ),
        "world_ticks_resume_monotonically": (
            _counter(b_final, "total_world_ticks")
            >= _counter(a_final, "total_world_ticks")
        ),
        "production_checkpoint_copy_isolated": source_checkpoint_isolated is True,
    }

    passed = all(contract_gates.values()) and all(invariants.values())
    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "scope": SCOPE,
        "contract_gates": contract_gates,
        "invariants": invariants,
        "phase_processes": {
            "phase_a_pid": phase_a_pid,
            "phase_b_pid": phase_b_pid,
            "phase_a_returncode": phase_a_returncode,
            "phase_b_returncode": phase_b_returncode,
        },
        "checkpoint_hashes": {
            "phase_a_post_save": phase_a_checkpoint_hashes,
            "phase_b_pre_restore": pre_b_checkpoint_hashes,
            "phase_b_post_save": post_b_checkpoint_hashes,
        },
        "source_receipts": {
            "phase_a_receipt_sha256": phase_a_receipt.get("receipt_sha256"),
            "phase_b_receipt_sha256": phase_b_receipt.get("receipt_sha256"),
        },
        "phase_a_pending_proprioception": phase_a_pending_proprioception,
        "actual_malecns_process_restart_executed": passed,
        "malecns_checkpoint_file_continuity_verified": passed,
        "proprioception_first_handoff_continuity_verified": passed,
        "biological_memory_equivalence_proven": False,
        "snpp39_snpp41_polarity_resolved": False,
        "biological_current_calibrated": False,
        "biological_latency_resolved": False,
        "continuous_single_process_24_7_claimed": False,
        "systematic_type_mapping_exposed": False,
        "current_calibration_authorized": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "runtime_gating_authorized": False,
        "neural_payload_promotion_authorized": False,
    }
    body["receipt_sha256"] = _digest_json(body)
    return body


def _run_training_process(command: list[str], env: dict[str, str]) -> tuple[int, int]:
    process = subprocess.Popen(command, env=env)
    pid = int(process.pid)
    returncode = int(process.wait())
    return pid, returncode


def run_real_restart_probe(
    *,
    contract_path: Path,
    checkpoint: Path,
    phase_a_receipt_path: Path,
    phase_b_receipt_path: Path,
    output_path: Path,
    phase_a_steps: int,
    phase_b_steps: int,
    curriculum: bool,
    allow_low_memory: bool,
    production_checkpoint_source: Path | None,
) -> dict[str, Any]:
    if phase_a_steps < 1 or phase_b_steps < 1:
        raise ValueError("phase steps must be >= 1")

    contract = json.loads(contract_path.read_text())
    maze_path = checkpoint.with_suffix(".maze.json")
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    phase_a_receipt_path.parent.mkdir(parents=True, exist_ok=True)
    phase_b_receipt_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    source_isolated = True
    if production_checkpoint_source is not None:
        try:
            source_isolated = checkpoint.resolve() != production_checkpoint_source.resolve()
        except FileNotFoundError:
            source_isolated = checkpoint != production_checkpoint_source

    base_command = [
        sys.executable,
        "-m",
        "neurofly.training",
    ]
    common = [
        "--checkpoint",
        str(checkpoint),
        "--playback-steps",
        "8",
    ]
    if curriculum:
        common.append("--curriculum")
    if allow_low_memory:
        common.append("--allow-low-memory")

    env = dict(os.environ)
    env["PYTHONUNBUFFERED"] = "1"

    phase_a_command = base_command + [
        "--steps",
        str(phase_a_steps),
        "--receipt",
        str(phase_a_receipt_path),
    ] + common
    phase_a_started = time.time()
    phase_a_pid, phase_a_returncode = _run_training_process(phase_a_command, env)
    phase_a_finished = time.time()
    if phase_a_returncode != 0:
        raise RuntimeError(f"Phase A training failed with exit code {phase_a_returncode}")
    if not checkpoint.is_file() or not maze_path.is_file():
        raise RuntimeError("Phase A did not produce the coordinated checkpoint pair")

    phase_a_receipt = json.loads(phase_a_receipt_path.read_text())
    phase_a_maze = json.loads(maze_path.read_text())
    pending = phase_a_maze.get("_pending_proprioception")
    if not isinstance(pending, dict):
        raise RuntimeError("Phase A maze checkpoint lacks _pending_proprioception")
    assert_unprivileged_agent_input({"proprioception": pending})

    phase_a_hashes = {
        "brain": _sha256_file(checkpoint),
        "maze": _sha256_file(maze_path),
    }

    # This is intentionally a separate point after process A has exited and
    # immediately before process B is created.
    pre_b_hashes = {
        "brain": _sha256_file(checkpoint),
        "maze": _sha256_file(maze_path),
    }

    phase_b_command = base_command + [
        "--steps",
        str(phase_b_steps),
        "--receipt",
        str(phase_b_receipt_path),
    ] + common
    phase_b_started = time.time()
    phase_b_pid, phase_b_returncode = _run_training_process(phase_b_command, env)
    phase_b_finished = time.time()
    if phase_b_returncode != 0:
        raise RuntimeError(f"Phase B training failed with exit code {phase_b_returncode}")

    phase_b_receipt = json.loads(phase_b_receipt_path.read_text())
    post_b_hashes = {
        "brain": _sha256_file(checkpoint),
        "maze": _sha256_file(maze_path),
    }

    report = evaluate_restart_evidence(
        contract,
        phase_a_receipt=phase_a_receipt,
        phase_b_receipt=phase_b_receipt,
        phase_a_checkpoint_hashes=phase_a_hashes,
        pre_b_checkpoint_hashes=pre_b_hashes,
        post_b_checkpoint_hashes=post_b_hashes,
        phase_a_pending_proprioception=pending,
        phase_a_pid=phase_a_pid,
        phase_b_pid=phase_b_pid,
        phase_a_returncode=phase_a_returncode,
        phase_b_returncode=phase_b_returncode,
        source_checkpoint_isolated=source_isolated,
    )
    report["timing"] = {
        "phase_a_started_unix": phase_a_started,
        "phase_a_finished_unix": phase_a_finished,
        "phase_b_started_unix": phase_b_started,
        "phase_b_finished_unix": phase_b_finished,
        "phase_a_exited_before_phase_b_started": phase_a_finished <= phase_b_started,
    }
    report["receipt_sha256"] = _digest_json(
        {key: value for key, value in report.items() if key != "receipt_sha256"}
    )
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a two-process real MaleCNS restart continuity proof"
    )
    parser.add_argument(
        "--contract",
        default="data/proprioception_real_malecns_restart_proof_v01.json",
    )
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--phase-a-receipt", required=True)
    parser.add_argument("--phase-b-receipt", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--phase-a-steps", type=int, default=1)
    parser.add_argument("--phase-b-steps", type=int, default=1)
    parser.add_argument("--curriculum", action="store_true")
    parser.add_argument("--allow-low-memory", action="store_true")
    parser.add_argument("--production-checkpoint-source")
    args = parser.parse_args(argv)

    report = run_real_restart_probe(
        contract_path=Path(args.contract),
        checkpoint=Path(args.checkpoint),
        phase_a_receipt_path=Path(args.phase_a_receipt),
        phase_b_receipt_path=Path(args.phase_b_receipt),
        output_path=Path(args.output),
        phase_a_steps=args.phase_a_steps,
        phase_b_steps=args.phase_b_steps,
        curriculum=args.curriculum,
        allow_low_memory=args.allow_low_memory,
        production_checkpoint_source=(
            Path(args.production_checkpoint_source)
            if args.production_checkpoint_source
            else None
        ),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
