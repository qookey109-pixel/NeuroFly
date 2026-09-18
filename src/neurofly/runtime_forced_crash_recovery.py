from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .brain_runtime import MaleCNSBrain
from .curriculum import CurriculumMazeEnvironment
from .goal_training import GoalMazeSession
from .smoke import _digest_json, _neural_decision_verified


CONTRACT_SCHEMA = "neurofly-runtime-forced-crash-recovery-v0.1"
RECEIPT_SCHEMA = "neurofly-runtime-forced-crash-recovery-receipt-v0.1"
WORKER_SCHEMA = "neurofly-runtime-forced-crash-worker-v0.1"
STATUS = "EXECUTION_REQUIRED"
SCOPE = "isolated-real-malecns-forced-crash-recovery"
EXPECTED_CRASH_EXIT_CODE = 86

REQUIRED_INVARIANTS = {
    "source_checkpoint_isolated",
    "source_checkpoint_unchanged",
    "crash_process_exits_nonzero",
    "crash_process_neural_activity_verified",
    "checkpoint_pair_unchanged_by_unsaved_crash",
    "recovery_process_is_distinct",
    "recovery_real_malecns_verified",
    "recovery_resumes_persisted_counters",
    "checkpoint_pair_exists_after_recovery",
    "all_cycles_completed",
}

CLAIM_LIMITS = {
    "zero_data_loss_claimed",
    "unsaved_work_preserved_claimed",
    "actual_watchdog_dispatch_tested",
    "twenty_four_hour_soak_validated",
    "continuous_single_process_uptime_validated",
    "production_checkpoint_mutated",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _checkpoint_pair_hashes(checkpoint: Path) -> dict[str, str]:
    maze = checkpoint.with_suffix(".maze.json")
    if not checkpoint.is_file() or not maze.is_file():
        raise FileNotFoundError("coordinated checkpoint pair is incomplete")
    return {
        "brain": _sha256_file(checkpoint),
        "maze": _sha256_file(maze),
    }


def _counter(payload: dict[str, Any], key: str) -> int:
    try:
        return int(payload.get(key) or 0)
    except (TypeError, ValueError, OverflowError):
        return -1


def validate_contract(contract: dict[str, Any]) -> dict[str, bool]:
    required = contract.get("required_invariants")
    limits = contract.get("claim_limits")
    return {
        "schema_exact": contract.get("schema") == CONTRACT_SCHEMA,
        "status_exact": contract.get("status") == STATUS,
        "scope_exact": contract.get("scope") == SCOPE,
        "default_cycles_positive": int(contract.get("default_cycles") or 0) > 0,
        "default_crash_steps_positive": int(contract.get("default_crash_steps") or 0) > 0,
        "default_recovery_steps_positive": int(contract.get("default_recovery_steps") or 0) > 0,
        "crash_exit_code_exact": contract.get("expected_crash_exit_code") == EXPECTED_CRASH_EXIT_CODE,
        "required_invariants_exact": (
            isinstance(required, dict)
            and set(required) == REQUIRED_INVARIANTS
            and all(value is True for value in required.values())
        ),
        "claim_limits_exact": (
            isinstance(limits, dict)
            and set(limits) == CLAIM_LIMITS
            and all(value is False for value in limits.values())
        ),
    }


def _verified_crash_receipt(receipt: dict[str, Any]) -> bool:
    supplied = receipt.get("receipt_sha256")
    digest_payload = copy.deepcopy(receipt)
    digest_payload.pop("receipt_sha256", None)
    return (
        receipt.get("schema") == WORKER_SCHEMA
        and receipt.get("neural_activity_verified") is True
        and receipt.get("checkpoint_save_called") is False
        and receipt.get("unsaved_work_expected_to_be_lost") is True
        and isinstance(supplied, str)
        and supplied == _digest_json(digest_payload)
    )


def _verified_training_receipt(receipt: dict[str, Any]) -> bool:
    supplied = receipt.get("receipt_sha256")
    digest_payload = copy.deepcopy(receipt)
    digest_payload.pop("receipt_sha256", None)
    if (
        receipt.get("schema") != "neurofly-self-training-v3"
        or receipt.get("passed") is not True
        or receipt.get("backend") != "malecns"
        or receipt.get("neural_activity_verified") is not True
        or not isinstance(supplied, str)
        or supplied != _digest_json(digest_payload)
    ):
        return False

    trajectory = receipt.get("trajectory")
    if not isinstance(trajectory, list) or not trajectory:
        return False
    return all(_neural_decision_verified(state) for state in trajectory)


def _flush_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    with temporary.open("w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def run_crash_worker(
    *,
    checkpoint: Path,
    receipt_path: Path,
    steps: int,
    exit_code: int = EXPECTED_CRASH_EXIT_CODE,
) -> None:
    if steps < 1:
        raise ValueError("crash worker steps must be >= 1")
    if exit_code == 0:
        raise ValueError("crash worker exit code must be nonzero")

    brain = MaleCNSBrain(checkpoint=checkpoint)
    session = GoalMazeSession(
        brain,
        checkpoint=checkpoint,
        checkpoint_every=10**12,
        world_tick_seconds=3600.0,
        environment=CurriculumMazeEnvironment(seed=109),
    )

    states = []
    for _ in range(steps):
        state = session.tick()
        if not _neural_decision_verified(state):
            raise RuntimeError("Crash worker MaleCNS activity is not verified")
        states.append(copy.deepcopy(state))

    # Deliberately do not call session.save(). Evidence is flushed, then the
    # process terminates immediately. This simulates loss of unsaved work while
    # the last coordinated checkpoint pair must remain authoritative.
    body = {
        "schema": WORKER_SCHEMA,
        "pid": os.getpid(),
        "steps_completed_but_unsaved": steps,
        "neural_activity_verified": True,
        "last_state": states[-1],
        "unsaved_work_expected_to_be_lost": True,
        "checkpoint_save_called": False,
    }
    body["receipt_sha256"] = _digest_json(body)
    _flush_json(receipt_path, body)
    os._exit(int(exit_code))


def _run_process(command: list[str], env: dict[str, str]) -> tuple[int, int]:
    process = subprocess.Popen(command, env=env)
    pid = int(process.pid)
    returncode = int(process.wait())
    return pid, returncode


def evaluate_forced_crash_evidence(
    contract: dict[str, Any],
    *,
    source_hash_before: dict[str, str],
    source_hash_after: dict[str, str],
    source_isolated: bool,
    cycles: list[dict[str, Any]],
    expected_cycles: int,
) -> dict[str, Any]:
    contract_gates = validate_contract(contract)

    crash_nonzero = all(
        int(cycle.get("crash_returncode") or 0) != 0
        and int(cycle.get("crash_returncode") or 0) == EXPECTED_CRASH_EXIT_CODE
        for cycle in cycles
    )
    crash_verified = all(
        _verified_crash_receipt(cycle.get("crash_receipt") or {})
        for cycle in cycles
    )
    unchanged_by_crash = all(
        cycle.get("pre_crash_hashes") == cycle.get("post_crash_hashes")
        for cycle in cycles
    )
    distinct_processes = all(
        int(cycle.get("crash_pid") or 0) > 0
        and int(cycle.get("recovery_pid") or 0) > 0
        and int(cycle.get("crash_pid")) != int(cycle.get("recovery_pid"))
        for cycle in cycles
    )
    recovery_verified = all(
        int(cycle.get("recovery_returncode") or 1) == 0
        and _verified_training_receipt(cycle.get("recovery_receipt") or {})
        for cycle in cycles
    )
    counter_resume = all(
        cycle.get("recovery_receipt", {}).get("clears_before")
        == _counter(cycle.get("persisted_state_before_crash") or {}, "total_clears")
        and _counter(
            cycle.get("recovery_receipt", {}).get("final_state") or {},
            "total_clears",
        )
        >= _counter(cycle.get("persisted_state_before_crash") or {}, "total_clears")
        and _counter(
            cycle.get("recovery_receipt", {}).get("final_state") or {},
            "total_deaths",
        )
        >= _counter(cycle.get("persisted_state_before_crash") or {}, "total_deaths")
        and _counter(
            cycle.get("recovery_receipt", {}).get("final_state") or {},
            "total_world_ticks",
        )
        >= _counter(cycle.get("persisted_state_before_crash") or {}, "total_world_ticks")
        for cycle in cycles
    )
    checkpoint_exists = all(
        set(cycle.get("post_recovery_hashes") or {}) == {"brain", "maze"}
        and all(bool(v) for v in (cycle.get("post_recovery_hashes") or {}).values())
        for cycle in cycles
    )

    invariants = {
        "source_checkpoint_isolated": source_isolated is True,
        "source_checkpoint_unchanged": source_hash_before == source_hash_after,
        "crash_process_exits_nonzero": crash_nonzero,
        "crash_process_neural_activity_verified": crash_verified,
        "checkpoint_pair_unchanged_by_unsaved_crash": unchanged_by_crash,
        "recovery_process_is_distinct": distinct_processes,
        "recovery_real_malecns_verified": recovery_verified,
        "recovery_resumes_persisted_counters": counter_resume,
        "checkpoint_pair_exists_after_recovery": checkpoint_exists,
        "all_cycles_completed": len(cycles) == expected_cycles,
    }

    if set(invariants) != set(contract.get("required_invariants") or {}):
        raise RuntimeError("Runtime recovery evidence gate drifted from preregistration")

    passed = all(contract_gates.values()) and all(invariants.values())
    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "scope": SCOPE,
        "contract_gates": contract_gates,
        "invariants": invariants,
        "cycles_completed": len(cycles),
        "expected_cycles": expected_cycles,
        "cycles": cycles,
        "source_hash_before": source_hash_before,
        "source_hash_after": source_hash_after,
        "forced_crash_recovery_execution_verified": passed,
        "zero_data_loss_claimed": False,
        "unsaved_work_preserved_claimed": False,
        "actual_watchdog_dispatch_tested": False,
        "twenty_four_hour_soak_validated": False,
        "continuous_single_process_uptime_validated": False,
        "production_checkpoint_mutated": False,
    }
    body["receipt_sha256"] = _digest_json(body)
    return body


def run_forced_crash_recovery(
    *,
    contract_path: Path,
    source_checkpoint: Path,
    proof_checkpoint: Path,
    output_dir: Path,
    output_receipt: Path,
    cycles: int | None = None,
    crash_steps: int | None = None,
    recovery_steps: int | None = None,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text())
    gates = validate_contract(contract)
    if not all(gates.values()):
        raise ValueError("Forced-crash recovery contract failed validation")

    cycles = int(cycles or contract["default_cycles"])
    crash_steps = int(crash_steps or contract["default_crash_steps"])
    recovery_steps = int(recovery_steps or contract["default_recovery_steps"])
    if min(cycles, crash_steps, recovery_steps) < 1:
        raise ValueError("cycles and step counts must be >= 1")

    source_maze = source_checkpoint.with_suffix(".maze.json")
    if not source_checkpoint.is_file() or not source_maze.is_file():
        raise FileNotFoundError("source coordinated checkpoint pair is incomplete")

    output_dir.mkdir(parents=True, exist_ok=True)
    proof_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    proof_maze = proof_checkpoint.with_suffix(".maze.json")

    source_hash_before = _checkpoint_pair_hashes(source_checkpoint)
    shutil.copy2(source_checkpoint, proof_checkpoint)
    shutil.copy2(source_maze, proof_maze)

    source_isolated = (
        proof_checkpoint.resolve() != source_checkpoint.resolve()
        and proof_maze.resolve() != source_maze.resolve()
    )
    if _checkpoint_pair_hashes(proof_checkpoint) != source_hash_before:
        raise RuntimeError("isolated proof copy differs from source checkpoint")

    env = dict(os.environ)
    env.pop("NEUROFLY_LIVE_RELAY_URL", None)
    env["PYTHONUNBUFFERED"] = "1"

    cycle_reports: list[dict[str, Any]] = []
    for cycle_index in range(1, cycles + 1):
        persisted_state = json.loads(proof_maze.read_text())
        pre_crash_hashes = _checkpoint_pair_hashes(proof_checkpoint)
        crash_receipt_path = output_dir / f"cycle-{cycle_index}-crash.json"

        crash_command = [
            sys.executable,
            "-m",
            "neurofly.runtime_forced_crash_recovery",
            "crash-worker",
            "--checkpoint",
            str(proof_checkpoint),
            "--receipt",
            str(crash_receipt_path),
            "--steps",
            str(crash_steps),
            "--exit-code",
            str(EXPECTED_CRASH_EXIT_CODE),
        ]
        crash_pid, crash_returncode = _run_process(crash_command, env)
        if not crash_receipt_path.is_file():
            raise RuntimeError("forced crash worker did not flush its evidence receipt")
        crash_receipt = json.loads(crash_receipt_path.read_text())
        post_crash_hashes = _checkpoint_pair_hashes(proof_checkpoint)

        recovery_receipt_path = output_dir / f"cycle-{cycle_index}-recovery.json"
        recovery_command = [
            sys.executable,
            "-m",
            "neurofly.training",
            "--curriculum",
            "--steps",
            str(recovery_steps),
            "--playback-steps",
            str(max(1, recovery_steps)),
            "--world-tick-seconds",
            "3600",
            "--checkpoint",
            str(proof_checkpoint),
            "--receipt",
            str(recovery_receipt_path),
        ]
        recovery_pid, recovery_returncode = _run_process(recovery_command, env)
        if recovery_returncode != 0 or not recovery_receipt_path.is_file():
            raise RuntimeError(
                f"recovery process failed in cycle {cycle_index}: {recovery_returncode}"
            )
        recovery_receipt = json.loads(recovery_receipt_path.read_text())
        post_recovery_hashes = _checkpoint_pair_hashes(proof_checkpoint)

        cycle_reports.append(
            {
                "cycle": cycle_index,
                "persisted_state_before_crash": {
                    "total_clears": _counter(persisted_state, "total_clears"),
                    "total_deaths": _counter(persisted_state, "total_deaths"),
                    "total_world_ticks": _counter(persisted_state, "total_world_ticks"),
                },
                "pre_crash_hashes": pre_crash_hashes,
                "post_crash_hashes": post_crash_hashes,
                "post_recovery_hashes": post_recovery_hashes,
                "crash_pid": crash_pid,
                "crash_returncode": crash_returncode,
                "crash_receipt": crash_receipt,
                "recovery_pid": recovery_pid,
                "recovery_returncode": recovery_returncode,
                "recovery_receipt": recovery_receipt,
            }
        )

    source_hash_after = _checkpoint_pair_hashes(source_checkpoint)
    report = evaluate_forced_crash_evidence(
        contract,
        source_hash_before=source_hash_before,
        source_hash_after=source_hash_after,
        source_isolated=source_isolated,
        cycles=cycle_reports,
        expected_cycles=cycles,
    )
    _flush_json(output_receipt, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run isolated real MaleCNS forced-crash recovery evidence"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    crash = subparsers.add_parser("crash-worker")
    crash.add_argument("--checkpoint", required=True)
    crash.add_argument("--receipt", required=True)
    crash.add_argument("--steps", type=int, default=1)
    crash.add_argument("--exit-code", type=int, default=EXPECTED_CRASH_EXIT_CODE)

    run = subparsers.add_parser("run")
    run.add_argument(
        "--contract",
        default="data/runtime_forced_crash_recovery_v01.json",
    )
    run.add_argument("--source-checkpoint", required=True)
    run.add_argument("--proof-checkpoint", required=True)
    run.add_argument("--output-dir", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--cycles", type=int)
    run.add_argument("--crash-steps", type=int)
    run.add_argument("--recovery-steps", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "crash-worker":
        run_crash_worker(
            checkpoint=Path(args.checkpoint),
            receipt_path=Path(args.receipt),
            steps=args.steps,
            exit_code=args.exit_code,
        )
        return 99

    report = run_forced_crash_recovery(
        contract_path=Path(args.contract),
        source_checkpoint=Path(args.source_checkpoint),
        proof_checkpoint=Path(args.proof_checkpoint),
        output_dir=Path(args.output_dir),
        output_receipt=Path(args.output),
        cycles=args.cycles,
        crash_steps=args.crash_steps,
        recovery_steps=args.recovery_steps,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
