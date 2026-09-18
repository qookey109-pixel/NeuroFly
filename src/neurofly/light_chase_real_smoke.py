from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from .brain_runtime import MaleCNSBrain
from .environment_adapter import (
    ENVIRONMENT_ADAPTER_SCHEMA,
    EnvironmentSession,
    LightChaseAdapter,
    VALID_ACTIONS,
    assert_sensory_only_context,
)
from .light_chase import LIGHT_CHASE_MODEL
from .preflight import collect_preflight
from .smoke import _digest_json, _neural_decision_verified
from .upstream import STONKFLY_COMMIT


CONTRACT_SCHEMA = "neurofly-light-chase-real-malecns-smoke-v0.1"
RECEIPT_SCHEMA = "neurofly-light-chase-real-malecns-smoke-receipt-v0.1"
STATUS = "EXECUTION_REQUIRED"
SCOPE = "real-malecns-light-chase-sensory-execution"

REQUIRED_INVARIANTS = {
    "source_checkpoint_isolated",
    "source_checkpoint_unchanged",
    "real_malecns_backend",
    "all_steps_neural_activity_verified",
    "all_steps_use_light_chase_environment",
    "all_steps_sensory_context_unprivileged",
    "all_actions_valid",
    "proof_brain_checkpoint_saved",
    "proof_environment_checkpoint_saved",
    "learning_disabled",
}

CLAIM_LIMITS = {
    "light_seeking_behavior_validated",
    "light_chase_learning_validated",
    "generalization_validated",
    "production_checkpoint_mutated",
    "behavioral_promotion_authorized",
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


def validate_contract(contract: dict[str, Any]) -> dict[str, bool]:
    required = contract.get("required_invariants")
    limits = contract.get("claim_limits")
    return {
        "schema_exact": contract.get("schema") == CONTRACT_SCHEMA,
        "status_exact": contract.get("status") == STATUS,
        "scope_exact": contract.get("scope") == SCOPE,
        "environment_exact": contract.get("environment_model") == LIGHT_CHASE_MODEL,
        "default_steps_positive": int(contract.get("default_steps") or 0) > 0,
        "learning_disabled": contract.get("learning_enabled") is False,
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


def _observation_is_safe(state: dict[str, Any]) -> bool:
    context = state.get("sensory_contract")
    if not isinstance(context, dict):
        return False
    try:
        assert_sensory_only_context(context)
    except ValueError:
        return False
    return (
        context.get("adapter_schema") == ENVIRONMENT_ADAPTER_SCHEMA
        and context.get("environment_model") == LIGHT_CHASE_MODEL
    )


def evaluate_light_smoke_evidence(
    contract: dict[str, Any],
    *,
    source_sha_before: str,
    source_sha_after: str,
    source_isolated: bool,
    proof_brain_exists: bool,
    proof_environment_exists: bool,
    learning_enabled: bool,
    states: list[dict[str, Any]],
) -> dict[str, Any]:
    contract_gates = validate_contract(contract)

    invariants = {
        "source_checkpoint_isolated": source_isolated is True,
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "real_malecns_backend": bool(states)
        and all((state.get("brain") or {}).get("backend") == "malecns" for state in states),
        "all_steps_neural_activity_verified": bool(states)
        and all(_neural_decision_verified(state) for state in states),
        "all_steps_use_light_chase_environment": bool(states)
        and all(state.get("environment_model") == LIGHT_CHASE_MODEL for state in states),
        "all_steps_sensory_context_unprivileged": bool(states)
        and all(_observation_is_safe(state) for state in states),
        "all_actions_valid": bool(states)
        and all(state.get("last_action") in VALID_ACTIONS for state in states),
        "proof_brain_checkpoint_saved": proof_brain_exists is True,
        "proof_environment_checkpoint_saved": proof_environment_exists is True,
        "learning_disabled": learning_enabled is False,
    }

    if set(invariants) != set(contract.get("required_invariants") or {}):
        raise RuntimeError("Light Chase evidence gate drifted from preregistration")

    passed = all(contract_gates.values()) and all(invariants.values())
    actions = Counter(str(state.get("last_action")) for state in states)
    total_reward = round(sum(float(state.get("last_reward") or 0.0) for state in states), 8)
    final = states[-1] if states else {}

    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "scope": SCOPE,
        "environment_model": LIGHT_CHASE_MODEL,
        "contract_gates": contract_gates,
        "invariants": invariants,
        "steps": len(states),
        "action_counts": dict(sorted(actions.items())),
        "total_reward": total_reward,
        "total_lights": int(final.get("total_lights") or 0),
        "neural_activity_verified": invariants["all_steps_neural_activity_verified"],
        "learning_enabled": learning_enabled,
        "light_seeking_behavior_validated": False,
        "light_chase_learning_validated": False,
        "generalization_validated": False,
        "production_checkpoint_mutated": False,
        "behavioral_promotion_authorized": False,
        "stonkfly_commit": STONKFLY_COMMIT,
    }
    body["receipt_sha256"] = _digest_json(body)
    return body


def run_real_light_chase_smoke(
    *,
    contract_path: Path,
    source_checkpoint: Path,
    proof_checkpoint: Path,
    receipt_path: Path,
    steps: int | None = None,
    seed: int = 109,
    allow_low_memory: bool = False,
) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text())
    contract_gates = validate_contract(contract)
    if not all(contract_gates.values()):
        raise ValueError("Light Chase real-smoke contract failed validation")

    steps = int(steps or contract["default_steps"])
    if steps < 1:
        raise ValueError("steps must be >= 1")
    if not source_checkpoint.is_file():
        raise FileNotFoundError(source_checkpoint)

    preflight = collect_preflight()
    if not preflight["ready"]:
        failed = [
            item["name"]
            for item in preflight["checks"]
            if item["required"] and not item["ok"]
        ]
        raise RuntimeError("MaleCNS preflight failed: " + ", ".join(failed))
    if preflight["low_memory_guard"] and not allow_low_memory:
        raise RuntimeError(
            "Host memory is below the 12 GiB low-memory guard. "
            "Use a larger host or explicitly pass --allow-low-memory."
        )

    proof_checkpoint.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)

    source_sha_before = _sha256_file(source_checkpoint)
    source_isolated = proof_checkpoint.resolve() != source_checkpoint.resolve()
    if not source_isolated:
        raise ValueError("proof checkpoint must be isolated from production source")

    shutil.copy2(source_checkpoint, proof_checkpoint)
    if _sha256_file(proof_checkpoint) != source_sha_before:
        raise RuntimeError("isolated proof checkpoint differs from source")

    brain = MaleCNSBrain(
        checkpoint=proof_checkpoint,
        learning=False,
    )
    brain.brain.weights_frozen = True
    adapter = LightChaseAdapter(seed=seed)
    session = EnvironmentSession(
        brain,
        adapter,
        checkpoint=proof_checkpoint,
        checkpoint_every=10**12,
    )

    states: list[dict[str, Any]] = []
    for _ in range(steps):
        state = session.tick()
        if not _neural_decision_verified(state):
            raise RuntimeError("Light Chase MaleCNS decision lacks verified neural activity")
        if not _observation_is_safe(state):
            raise RuntimeError("Light Chase neural context violated sensory-only boundary")
        states.append(copy.deepcopy(state))

    session.save()
    source_sha_after = _sha256_file(source_checkpoint)
    environment_checkpoint = proof_checkpoint.with_suffix(
        adapter.state_suffix
    )

    report = evaluate_light_smoke_evidence(
        contract,
        source_sha_before=source_sha_before,
        source_sha_after=source_sha_after,
        source_isolated=source_isolated,
        proof_brain_exists=proof_checkpoint.is_file(),
        proof_environment_exists=environment_checkpoint.is_file(),
        learning_enabled=brain.learning,
        states=states,
    )
    report["source_checkpoint_sha256"] = source_sha_before
    report["proof_checkpoint_sha256"] = _sha256_file(proof_checkpoint)
    report["proof_environment_checkpoint_sha256"] = _sha256_file(
        environment_checkpoint
    )
    report["preflight"] = preflight
    report["observations"] = [
        {
            "step": index,
            "action": state.get("last_action"),
            "reward": state.get("last_reward"),
            "event": state.get("step_event") or state.get("last_event"),
            "total_lights": state.get("total_lights"),
            "brain_ms": ((state.get("brain") or {}).get("telemetry") or {}).get("brain_ms"),
            "total_spikes": ((state.get("brain") or {}).get("telemetry") or {}).get("total_spikes"),
            "sensory_contract": state.get("sensory_contract"),
        }
        for index, state in enumerate(states, start=1)
    ]
    unsigned = {key: value for key, value in report.items() if key != "receipt_sha256"}
    report["receipt_sha256"] = _digest_json(unsigned)

    temporary = receipt_path.with_suffix(receipt_path.suffix + ".partial")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    temporary.replace(receipt_path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run real MaleCNS through the Light Chase sensory adapter"
    )
    parser.add_argument(
        "--contract",
        default="data/light_chase_real_malecns_smoke_v01.json",
    )
    parser.add_argument("--source-checkpoint", required=True)
    parser.add_argument("--proof-checkpoint", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--steps", type=int)
    parser.add_argument("--seed", type=int, default=109)
    parser.add_argument("--allow-low-memory", action="store_true")
    args = parser.parse_args(argv)

    report = run_real_light_chase_smoke(
        contract_path=Path(args.contract),
        source_checkpoint=Path(args.source_checkpoint),
        proof_checkpoint=Path(args.proof_checkpoint),
        receipt_path=Path(args.receipt),
        steps=args.steps,
        seed=args.seed,
        allow_low_memory=args.allow_low_memory,
    )
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "status": report["status"],
                "passed": report["passed"],
                "steps": report["steps"],
                "action_counts": report["action_counts"],
                "total_reward": report["total_reward"],
                "total_lights": report["total_lights"],
                "receipt_sha256": report["receipt_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
