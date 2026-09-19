from __future__ import annotations

import argparse
import copy
import json
import shutil
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from .brain_runtime import MaleCNSBrain
from .dan_baseline_intervention import _baseline_digest, _memory_snapshot, _restore_arm_brain
from .dan_trace_recentering_intervention import BASELINE_DIGEST, BASELINE_HZ, _configure_source_state
from .external_reinforcement_increment import (
    EXPECTED_REPLICATES as EXTERNAL_INCREMENT_REPLICATES,
    PREVIOUS_SEEDS,
)
from .full_network_reinforcement_pulse_replay import (
    EXPECTED_REPLICATES as FULL_NETWORK_REPLICATES,
    _record_trajectory,
)
from .learning_control_study import _sha256_file
from .smoke import _digest_json


CONFIG_SCHEMA = "neurofly-event-local-reinforcement-pulse-v0.1"
RECEIPT_SCHEMA = "neurofly-event-local-reinforcement-pulse-receipt-v0.1"
STATUS = "EXPLORATORY_INTERVENTION_ONLY"
SCOPE = "real-malecns-single-event-paired-full-network-reinforcement-pulse"

EXPECTED_TRAJECTORY_DECISIONS = 60
EXPECTED_REPLICATES = (
    ("E1", 2179),
    ("E2", 2183),
    ("E3", 2203),
    ("E4", 2207),
)
ORIGIN_RUN_ID = 35429987465
ORIGIN_RECEIPT = "b74c77cd32ce848a923f7a548f043c7dd9bc5fe6ad3c611bd44a365d1a05a001"
ORIGIN_ARTIFACT_DIGEST = "sha256:4e7e40ffe8df9f8a83b3b83ba356c0e98c7032bb2aa5c5c1e48c5949179bb207"
USED_SEEDS = (
    set(PREVIOUS_SEEDS)
    | {seed for _, seed in EXTERNAL_INCREMENT_REPLICATES}
    | {seed for _, seed in FULL_NETWORK_REPLICATES}
)


def _normalized_replicates(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (item.get("id"), item.get("trajectory_seed"))
        for item in (config.get("replicates") or [])
        if isinstance(item, dict)
    )


def validate_config(config: dict[str, Any]) -> dict[str, bool]:
    origin = config.get("origin") or {}
    runtime = config.get("runtime") or {}
    claims = config.get("claim_policy") or {}
    seeds = [seed for _, seed in EXPECTED_REPLICATES]
    return {
        "schema_exact": config.get("schema") == CONFIG_SCHEMA,
        "status_exact": config.get("status") == STATUS,
        "scope_exact": config.get("scope") == SCOPE,
        "origin_exact": (
            origin.get("full_network_run_id") == ORIGIN_RUN_ID
            and origin.get("full_network_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("full_network_artifact_digest") == ORIGIN_ARTIFACT_DIGEST
            and origin.get("baseline_digest") == BASELINE_DIGEST
        ),
        "runtime_exact": (
            runtime.get("decision_synchronous_world") is True
            and runtime.get("trajectory_decisions") == EXPECTED_TRAJECTORY_DECISIONS
            and runtime.get("neural_ms_per_decision") == 50
            and runtime.get("pulse_ms") == 20
            and runtime.get("pulse_current") == 20.0
            and runtime.get("pre_event_history_reinforcement") == "none"
            and runtime.get("paired_conditions") == ["none", "true_external"]
            and runtime.get("replay_learning") is True
            and runtime.get("baseline_mode") == "calibrated"
            and runtime.get("trace_state_mode") == "subtract_baseline"
        ),
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": len(seeds) == len(set(seeds)) and not (set(seeds) & USED_SEEDS),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ()) == (
            "event_count",
            "reward_event_true_minus_none_efficacy_delta",
            "aversive_event_true_minus_none_efficacy_delta",
            "reward_event_reward_spike_increment",
            "aversive_event_aversive_spike_increment",
            "event_action_divergence_fraction",
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims) == {
                "learning_validated",
                "single_event_reinforcement_effect_causal",
                "temporal_credit_defect_confirmed",
                "causal_learning_claim_authorized",
                "replacement_confirmatory_authorized",
                "behavioral_promotion_authorized",
            }
            and all(value is False for value in claims.values())
        ),
    }


def _restore_recentered(checkpoint: Path) -> MaleCNSBrain:
    return _restore_arm_brain(
        checkpoint=checkpoint,
        learning=True,
        baseline_hz=list(BASELINE_HZ),
        checkpoint_is_source_zero_baseline=False,
    )


def _build_pre_event_checkpoint(
    *,
    trajectory: list[dict[str, Any]],
    event_index: int,
    base_checkpoint: Path,
    pre_event_checkpoint: Path,
) -> dict[str, Any]:
    shutil.copy2(base_checkpoint, pre_event_checkpoint)
    inner = MaleCNSBrain(checkpoint=pre_event_checkpoint, learning=True)
    transform = _configure_source_state(
        inner,
        baseline_mode="calibrated",
        trace_state_mode="subtract_baseline",
    )
    inner.brain.weights_frozen = False

    initial_memory = _memory_snapshot(inner)
    for prior in trajectory[:event_index]:
        inner.decide(
            prior["frame"],
            "none",
            context=copy.deepcopy(prior["context"]),
        )
    pre_memory = _memory_snapshot(inner)
    inner.save(pre_event_checkpoint)
    return {
        "trace_transform": transform,
        "history_decisions": event_index,
        "history_initial_memory": initial_memory,
        "pre_event_memory": pre_memory,
        "pre_event_checkpoint_sha256": _sha256_file(pre_event_checkpoint),
    }


def _branch_event(
    *,
    pre_event_checkpoint: Path,
    event: dict[str, Any],
    reinforcement: str,
) -> dict[str, Any]:
    inner = _restore_recentered(pre_event_checkpoint)
    before = _memory_snapshot(inner)
    before_u = float(inner.brain.memory_u.mean())
    decision = inner.decide(
        event["frame"],
        reinforcement,
        context=copy.deepcopy(event["context"]),
    )
    after = _memory_snapshot(inner)
    after_u = float(inner.brain.memory_u.mean())
    telemetry = copy.deepcopy(decision.telemetry)
    return {
        "reinforcement": reinforcement,
        "pre_memory": before,
        "post_memory": after,
        "action": decision.action,
        "reward_spikes": int(telemetry.get("reward_spikes") or 0),
        "aversive_spikes": int(telemetry.get("aversive_spikes") or 0),
        "kc_spikes": int(telemetry.get("kc_spikes") or 0),
        "total_spikes": int(telemetry.get("total_spikes") or 0),
        "stimulus_ms": float(telemetry.get("stimulus_ms") or 0.0),
        "efficacy_delta": round(
            after["mean_efficacy"] - before["mean_efficacy"],
            12,
        ),
        "u_delta": round(after_u - before_u, 12),
    }


def _event_pair(
    *,
    replicate_id: str,
    event_ordinal: int,
    event_index: int,
    trajectory: list[dict[str, Any]],
    base_checkpoint: Path,
    event_dir: Path,
) -> dict[str, Any]:
    event = trajectory[event_index]
    true_reinforcement = str(event["true_reinforcement"])
    if true_reinforcement not in {"reward", "aversive"}:
        raise RuntimeError("Event-local pair requires a reinforced decision")

    event_dir.mkdir(parents=True, exist_ok=True)
    pre_event_checkpoint = event_dir / "pre-event.npz"
    pre = _build_pre_event_checkpoint(
        trajectory=trajectory,
        event_index=event_index,
        base_checkpoint=base_checkpoint,
        pre_event_checkpoint=pre_event_checkpoint,
    )
    source_sha = pre["pre_event_checkpoint_sha256"]

    none = _branch_event(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        reinforcement="none",
    )
    true = _branch_event(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        reinforcement=true_reinforcement,
    )
    after_sha = _sha256_file(pre_event_checkpoint)
    if source_sha != after_sha:
        raise RuntimeError("Pre-event checkpoint mutated during paired branches")
    if none["pre_memory"] != true["pre_memory"]:
        raise RuntimeError("Paired branches did not start from identical memory")

    return {
        "replicate_id": replicate_id,
        "event_ordinal": event_ordinal,
        "decision_index": event_index,
        "event_type": true_reinforcement,
        "frame_sha256": __import__("hashlib").sha256(event["frame"].tobytes()).hexdigest(),
        "context_sha256": _digest_json(event["context"]),
        "pre_event_checkpoint_sha256": source_sha,
        "pre_event": pre,
        "none": none,
        "true_external": true,
        "paired": {
            "true_minus_none_efficacy_delta": round(
                true["efficacy_delta"] - none["efficacy_delta"],
                12,
            ),
            "true_minus_none_u_delta": round(
                true["u_delta"] - none["u_delta"],
                12,
            ),
            "reward_spike_increment": true["reward_spikes"] - none["reward_spikes"],
            "aversive_spike_increment": true["aversive_spikes"] - none["aversive_spikes"],
            "action_diverged": true["action"] != none["action"],
        },
    }


def _run_replicate(
    *,
    replicate_id: str,
    trajectory_seed: int,
    base_checkpoint: Path,
    rep_dir: Path,
) -> dict[str, Any]:
    rep_dir.mkdir(parents=True, exist_ok=True)
    source_sha = _sha256_file(base_checkpoint)
    trajectory, driver = _record_trajectory(
        base_checkpoint=base_checkpoint,
        driver_checkpoint=rep_dir / "trajectory-driver.npz",
        trajectory_seed=trajectory_seed,
    )
    if len(trajectory) != EXPECTED_TRAJECTORY_DECISIONS:
        raise RuntimeError("Unexpected trajectory length")

    event_indices = [
        index
        for index, item in enumerate(trajectory)
        if item["true_reinforcement"] in {"reward", "aversive"}
    ]
    events = [
        _event_pair(
            replicate_id=replicate_id,
            event_ordinal=ordinal,
            event_index=event_index,
            trajectory=trajectory,
            base_checkpoint=base_checkpoint,
            event_dir=rep_dir / f"event-{ordinal:02d}",
        )
        for ordinal, event_index in enumerate(event_indices, start=1)
    ]
    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "source_checkpoint_sha256": source_sha,
        "driver": driver,
        "event_indices": event_indices,
        "event_count": len(events),
        "event_type_counts": dict(sorted(Counter(row["event_type"] for row in events).items())),
        "events": events,
    }


def _mean_or_zero(values: list[float]) -> float:
    return round(mean(values), 12) if values else 0.0


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    events = [event for rep in replicates for event in rep["events"]]
    reward = [event for event in events if event["event_type"] == "reward"]
    aversive = [event for event in events if event["event_type"] == "aversive"]
    reward_eff = [event["paired"]["true_minus_none_efficacy_delta"] for event in reward]
    aversive_eff = [event["paired"]["true_minus_none_efficacy_delta"] for event in aversive]
    return {
        "event_count": len(events),
        "reward_event_count": len(reward),
        "aversive_event_count": len(aversive),
        "reward_event_true_minus_none_efficacy_delta": _mean_or_zero(reward_eff),
        "aversive_event_true_minus_none_efficacy_delta": _mean_or_zero(aversive_eff),
        "all_event_true_minus_none_efficacy_delta": _mean_or_zero(
            [event["paired"]["true_minus_none_efficacy_delta"] for event in events]
        ),
        "reward_event_positive_efficacy_events": sum(value > 0 for value in reward_eff),
        "reward_event_negative_efficacy_events": sum(value < 0 for value in reward_eff),
        "aversive_event_positive_efficacy_events": sum(value > 0 for value in aversive_eff),
        "aversive_event_negative_efficacy_events": sum(value < 0 for value in aversive_eff),
        "reward_event_reward_spike_increment": round(
            mean(event["paired"]["reward_spike_increment"] for event in reward), 8
        )
        if reward
        else 0.0,
        "aversive_event_aversive_spike_increment": round(
            mean(event["paired"]["aversive_spike_increment"] for event in aversive), 8
        )
        if aversive
        else 0.0,
        "event_action_divergence_fraction": round(
            sum(event["paired"]["action_diverged"] for event in events) / len(events),
            8,
        )
        if events
        else 0.0,
    }


def run_event_local_reinforcement_pulse(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Event-local pulse config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)
    if _baseline_digest(list(BASELINE_HZ)) != BASELINE_DIGEST:
        raise RuntimeError("Frozen baseline digest mismatch")

    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha_before = _sha256_file(base_checkpoint)
    replicates = [
        _run_replicate(
            replicate_id=replicate_id,
            trajectory_seed=trajectory_seed,
            base_checkpoint=base_checkpoint,
            rep_dir=output_dir / replicate_id,
        )
        for replicate_id, trajectory_seed in EXPECTED_REPLICATES
    ]
    source_sha_after = _sha256_file(base_checkpoint)

    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "all_replicates_executed": len(replicates) == len(EXPECTED_REPLICATES),
        "all_replicates_start_from_source_checkpoint": all(
            rep["source_checkpoint_sha256"] == source_sha_before for rep in replicates
        ),
        "all_trajectories_complete": all(
            rep["driver"]["decisions"] == EXPECTED_TRAJECTORY_DECISIONS for rep in replicates
        ),
        "trajectory_driver_frozen_memory_unchanged": all(
            rep["driver"]["driver_frozen_memory_unchanged"] is True for rep in replicates
        ),
        "at_least_one_event_per_replicate": all(rep["event_count"] > 0 for rep in replicates),
        "all_event_pairs_identical_pre_memory": all(
            event["none"]["pre_memory"] == event["true_external"]["pre_memory"]
            for rep in replicates
            for event in rep["events"]
        ),
        "all_event_pair_checkpoints_immutable": all(
            event["pre_event_checkpoint_sha256"] == event["pre_event"]["pre_event_checkpoint_sha256"]
            for rep in replicates
            for event in rep["events"]
        ),
        "none_branches_have_no_stimulus": all(
            event["none"]["stimulus_ms"] == 0.0
            for rep in replicates
            for event in rep["events"]
        ),
        "true_branches_deliver_20ms_stimulus": all(
            event["true_external"]["stimulus_ms"] == 20.0
            for rep in replicates
            for event in rep["events"]
        ),
        "frozen_baseline_exact": _baseline_digest(list(BASELINE_HZ)) == BASELINE_DIGEST,
        "claims_remain_locked": all(
            value is False for value in config["claim_policy"].values()
        ),
    }
    execution_valid = all(config_gates.values()) and all(evidence_gates.values())
    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": (
            "EXPLORATORY_INTERVENTION_COMPLETE"
            if execution_valid
            else "INVALID_EXECUTION"
        ),
        "scope": SCOPE,
        "execution_valid": execution_valid,
        "config_gates": config_gates,
        "evidence_gates": evidence_gates,
        "source_checkpoint_sha256": source_sha_before,
        "source_checkpoint_sha256_after": source_sha_after,
        "replicates": replicates,
        "aggregate": _aggregate(replicates),
        "learning_validated": False,
        "single_event_reinforcement_effect_causal": False,
        "temporal_credit_defect_confirmed": False,
        "causal_learning_claim_authorized": False,
        "replacement_confirmatory_authorized": False,
        "behavioral_promotion_authorized": False,
        "human_science_review_required": True,
    }
    body["receipt_sha256"] = _digest_json(body)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = receipt_path.with_suffix(receipt_path.suffix + ".partial")
    tmp.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    tmp.replace(receipt_path)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure each true task reinforcement event from an identical pre-event MaleCNS checkpoint"
    )
    parser.add_argument(
        "--config",
        default="data/event_local_reinforcement_pulse_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)
    result = run_event_local_reinforcement_pulse(
        config_path=Path(args.config),
        base_checkpoint=Path(args.base_checkpoint),
        output_dir=Path(args.output_dir),
        receipt_path=Path(args.receipt),
    )
    print(
        json.dumps(
            {
                "schema": result["schema"],
                "status": result["status"],
                "execution_valid": result["execution_valid"],
                "aggregate": result["aggregate"],
                "receipt_sha256": result["receipt_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["execution_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
