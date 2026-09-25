from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any

from .brain_runtime import MaleCNSBrain
from .compartment_plasticity_diagnostic import (
    _plastic_edge_state,
    _vector_digest,
)
from .event_local_reinforcement_pulse import (
    USED_SEEDS as EVENT_LOCAL_USED_SEEDS,
    _build_pre_event_checkpoint,
    _restore_recentered,
)
from .full_network_reinforcement_pulse_replay import _record_trajectory
from .learning_control_study import _sha256_file
from .smoke import _digest_json


CONFIG_SCHEMA = "neurofly-reward-memory-recall-v0.1"
RECEIPT_SCHEMA = "neurofly-reward-memory-recall-receipt-v0.1"
STATUS = "PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE = "real-malecns-single-reward-event-state-cleared-cue-recall"

EXPECTED_DECISIONS = 60
DELAY_DECISIONS = 5
EXPECTED_REPLICATES = (
    ("R1", 2609),
    ("R2", 2617),
    ("R3", 2621),
    ("R4", 2633),
)
PRIOR_COMPARTMENT_SEEDS = {2309, 2311, 2333, 2339}
PRIOR_USED_SEEDS = set(EVENT_LOCAL_USED_SEEDS) | PRIOR_COMPARTMENT_SEEDS
ORIGIN_RUN_ID = 36090134339
ORIGIN_RECEIPT = "19802e5a95243b55f1712b313e6e844637a85eff4c35e405d8d4b8a936e71308"
ORIGIN_ARTIFACT = "5e7c347af0adc0d4dad1b94812012413423d5ac34d48e319eb9920b61c25f8be"

CLAIM_KEYS = {
    "learning_validated",
    "reward_memory_persistence_causal",
    "cue_conditioned_behavior_effect_causal",
    "reinforcement_mechanism_validated",
    "causal_learning_claim_authorized",
    "replacement_confirmatory_authorized",
    "behavioral_promotion_authorized",
}


def _normalized_replicates(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (item.get("id"), item.get("trajectory_seed"))
        for item in (config.get("replicates") or [])
        if isinstance(item, dict)
    )


def validate_config(config: dict[str, Any]) -> dict[str, bool]:
    origin = config.get("origin") or {}
    runtime = config.get("runtime") or {}
    interpretation = config.get("interpretation_policy") or {}
    claims = config.get("claim_policy") or {}
    seeds = [seed for _, seed in EXPECTED_REPLICATES]
    return {
        "schema_exact": config.get("schema") == CONFIG_SCHEMA,
        "status_exact": config.get("status") == STATUS,
        "scope_exact": config.get("scope") == SCOPE,
        "question_frozen": config.get("question") == (
            "After one natural reward event, does the compartment-local synaptic "
            "difference produced by true external reinforcement survive five "
            "identical no-reinforcement replay decisions and, after clearing "
            "transient neural state, change the response to the identical reward cue?"
        ),
        "origin_exact": (
            origin.get("compartment_plasticity_run_id") == ORIGIN_RUN_ID
            and origin.get("compartment_plasticity_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("compartment_plasticity_artifact_sha256") == ORIGIN_ARTIFACT
        ),
        "runtime_exact": (
            runtime.get("decision_synchronous_world") is True
            and runtime.get("trajectory_decisions") == EXPECTED_DECISIONS
            and runtime.get("event_selection")
            == "first natural reward event with at least 5 subsequent recorded decisions"
            and runtime.get("post_event_replay_decisions") == DELAY_DECISIONS
            and runtime.get("post_event_replay_external_reinforcement") == "none"
            and runtime.get("recall_cue") == "exact original reward-event frame and context"
            and runtime.get("recall_external_reinforcement") == "none"
            and runtime.get("recall_plasticity_frozen") is True
            and runtime.get("transient_state_policy")
            == "brain.reset(keep_memory=true) before recall; wrapper visual-history state cleared"
            and runtime.get("pulse_ms") == 20
            and runtime.get("pulse_current") == 20.0
            and runtime.get("baseline_mode") == "calibrated"
            and runtime.get("trace_state_mode") == "subtract_baseline"
        ),
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": (
            len(seeds) == len(set(seeds))
            and not (set(seeds) & PRIOR_USED_SEEDS)
        ),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ())
        == (
            "post_event_reward_compartment_l1",
            "post_delay_reward_compartment_l1",
            "reward_compartment_l1_retention_ratio",
            "recall_action_divergence",
            "recall_difference_hz_delta",
            "recall_gate_spike_delta",
            "recall_total_spike_delta",
            "recall_kc_spike_delta",
        ),
        "interpretation_locked": (
            interpretation.get("no_posthoc_event_selection") is True
            and interpretation.get("no_parameter_tuning") is True
            and interpretation.get("no_behavioral_pass_threshold") is True
            and interpretation.get("same_cue_same_context_required") is True
            and interpretation.get("recall_memory_frozen_required") is True
            and interpretation.get(
                "result_is_exploratory_memory_function_evidence_only"
            )
            is True
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims) == CLAIM_KEYS
            and all(value is False for value in claims.values())
        ),
    }


def _reward_difference(none_state: dict[str, Any], true_state: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    if none_state["reward_mask_digest"] != true_state["reward_mask_digest"]:
        raise RuntimeError("Reward compartment mask drifted")
    if none_state["edge_index_digest"] != true_state["edge_index_digest"]:
        raise RuntimeError("Plastic edge topology drifted")

    delta = np.asarray(true_state["fraction"]) - np.asarray(none_state["fraction"])
    mask = np.asarray(none_state["reward_mask"], dtype=bool)
    target = delta[mask]
    off = delta[~mask]
    target_l1 = float(np.abs(target).sum())
    off_l1 = float(np.abs(off).sum())
    return {
        "difference_digest": _vector_digest(delta),
        "reward_compartment_l1": round(target_l1, 15),
        "off_target_l1": round(off_l1, 15),
        "reward_compartment_l1_fraction": round(
            target_l1 / (target_l1 + off_l1), 12
        )
        if target_l1 + off_l1
        else 0.0,
        "reward_mean_signed_delta": round(float(target.mean()), 15),
        "off_target_max_abs_delta": round(float(np.abs(off).max()), 15),
    }


def _receipt_plastic_state(state: dict[str, Any]) -> dict[str, Any]:
    """Remove runtime-only ndarray fields before JSON evidence serialization."""
    return {
        key: value
        for key, value in state.items()
        if key not in {"fraction", "reward_mask", "aversive_mask"}
    }


def _receipt_branch(branch: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(branch)
    for key in ("pre", "post_event", "post_delay", "post_reset"):
        cleaned[key] = _receipt_plastic_state(branch[key])
    return cleaned


def _telemetry(decision: Any) -> dict[str, Any]:
    t = copy.deepcopy(decision.telemetry)
    return {
        "action": decision.action,
        "left_hz": round(float(t.get("left_hz") or 0.0), 12),
        "right_hz": round(float(t.get("right_hz") or 0.0), 12),
        "difference_hz": round(float(t.get("difference_hz") or 0.0), 12),
        "gate_spikes": int(t.get("gate_spikes") or 0),
        "reward_spikes": int(t.get("reward_spikes") or 0),
        "aversive_spikes": int(t.get("aversive_spikes") or 0),
        "kc_spikes": int(t.get("kc_spikes") or 0),
        "total_spikes": int(t.get("total_spikes") or 0),
        "stimulus_ms": float(t.get("stimulus_ms") or 0.0),
    }


def _branch(
    *,
    pre_event_checkpoint: Path,
    event: dict[str, Any],
    delay_rows: list[dict[str, Any]],
    reinforcement: str,
) -> dict[str, Any]:
    inner = _restore_recentered(pre_event_checkpoint)
    pre = _plastic_edge_state(inner)

    event_decision = inner.decide(
        event["frame"],
        reinforcement,
        context=copy.deepcopy(event["context"]),
    )
    post_event = _plastic_edge_state(inner)

    delay_telemetry = []
    for row in delay_rows:
        decision = inner.decide(
            row["frame"],
            "none",
            context=copy.deepcopy(row["context"]),
        )
        delay_telemetry.append(_telemetry(decision))
    post_delay = _plastic_edge_state(inner)

    memory_before_reset = post_delay["fraction_digest"]
    inner.brain.reset(keep_memory=True)
    inner._last_visual_rgb = None
    post_reset = _plastic_edge_state(inner)
    if post_reset["fraction_digest"] != memory_before_reset:
        raise RuntimeError("State-clearing reset did not preserve synaptic efficacy")

    inner.learning = False
    inner.brain.weights_frozen = True
    recall_memory_before = _plastic_edge_state(inner)
    recall = inner.decide(
        event["frame"],
        "none",
        context=copy.deepcopy(event["context"]),
    )
    recall_memory_after = _plastic_edge_state(inner)
    if recall_memory_before["fraction_digest"] != recall_memory_after["fraction_digest"]:
        raise RuntimeError("Frozen recall mutated memory")

    return {
        "reinforcement": reinforcement,
        "pre": pre,
        "event": _telemetry(event_decision),
        "post_event": post_event,
        "delay": delay_telemetry,
        "post_delay": post_delay,
        "post_reset": post_reset,
        "recall": _telemetry(recall),
        "recall_memory_unchanged": True,
    }


def _first_eligible_reward_event(trajectory: list[dict[str, Any]]) -> int:
    last = len(trajectory) - DELAY_DECISIONS - 1
    for index, row in enumerate(trajectory):
        if index <= last and row["true_reinforcement"] == "reward":
            return index
    raise RuntimeError("No eligible reward event with sufficient post-event replay window")


def _run_replicate(
    *,
    replicate_id: str,
    trajectory_seed: int,
    base_checkpoint: Path,
    rep_dir: Path,
) -> dict[str, Any]:
    rep_dir.mkdir(parents=True, exist_ok=True)
    trajectory, driver = _record_trajectory(
        base_checkpoint=base_checkpoint,
        driver_checkpoint=rep_dir / "trajectory-driver.npz",
        trajectory_seed=trajectory_seed,
    )
    if len(trajectory) != EXPECTED_DECISIONS:
        raise RuntimeError("Unexpected trajectory length")

    event_index = _first_eligible_reward_event(trajectory)
    event = trajectory[event_index]
    delay_rows = trajectory[event_index + 1 : event_index + 1 + DELAY_DECISIONS]
    if len(delay_rows) != DELAY_DECISIONS:
        raise RuntimeError("Incomplete replay delay window")

    pre_path = rep_dir / "pre-event.npz"
    pre_report = _build_pre_event_checkpoint(
        trajectory=trajectory,
        event_index=event_index,
        base_checkpoint=base_checkpoint,
        pre_event_checkpoint=pre_path,
    )
    pre_sha = pre_report["pre_event_checkpoint_sha256"]

    none = _branch(
        pre_event_checkpoint=pre_path,
        event=event,
        delay_rows=delay_rows,
        reinforcement="none",
    )
    true = _branch(
        pre_event_checkpoint=pre_path,
        event=event,
        delay_rows=delay_rows,
        reinforcement="reward",
    )
    if _sha256_file(pre_path) != pre_sha:
        raise RuntimeError("Pre-event checkpoint mutated")
    if none["pre"]["fraction_digest"] != true["pre"]["fraction_digest"]:
        raise RuntimeError("Paired branches did not start from identical memory")

    post_event_diff = _reward_difference(none["post_event"], true["post_event"])
    post_delay_diff = _reward_difference(none["post_delay"], true["post_delay"])
    initial_l1 = post_event_diff["reward_compartment_l1"]
    delayed_l1 = post_delay_diff["reward_compartment_l1"]

    nr = none["recall"]
    tr = true["recall"]
    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "driver": driver,
        "event_index": event_index,
        "event_frame_sha256": hashlib.sha256(event["frame"].tobytes()).hexdigest(),
        "event_context_sha256": _digest_json(event["context"]),
        "delay_frame_sha256": [
            hashlib.sha256(row["frame"].tobytes()).hexdigest()
            for row in delay_rows
        ],
        "delay_context_sha256": [
            _digest_json(row["context"]) for row in delay_rows
        ],
        "pre_event_checkpoint_sha256": pre_sha,
        "none": _receipt_branch(none),
        "true_external": _receipt_branch(true),
        "post_event_difference": post_event_diff,
        "post_delay_difference": post_delay_diff,
        "reward_compartment_l1_retention_ratio": round(
            delayed_l1 / initial_l1, 12
        )
        if initial_l1
        else None,
        "recall_pair": {
            "action_diverged": nr["action"] != tr["action"],
            "none_action": nr["action"],
            "true_action": tr["action"],
            "difference_hz_delta": round(tr["difference_hz"] - nr["difference_hz"], 12),
            "left_hz_delta": round(tr["left_hz"] - nr["left_hz"], 12),
            "right_hz_delta": round(tr["right_hz"] - nr["right_hz"], 12),
            "gate_spike_delta": tr["gate_spikes"] - nr["gate_spikes"],
            "reward_spike_delta": tr["reward_spikes"] - nr["reward_spikes"],
            "aversive_spike_delta": tr["aversive_spikes"] - nr["aversive_spikes"],
            "kc_spike_delta": tr["kc_spikes"] - nr["kc_spikes"],
            "total_spike_delta": tr["total_spikes"] - nr["total_spikes"],
        },
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    pairs = [row["recall_pair"] for row in replicates]
    ratios = [
        row["reward_compartment_l1_retention_ratio"]
        for row in replicates
        if row["reward_compartment_l1_retention_ratio"] is not None
    ]
    return {
        "replicate_count": len(replicates),
        "mean_post_event_reward_compartment_l1": round(
            mean(row["post_event_difference"]["reward_compartment_l1"] for row in replicates),
            15,
        ),
        "mean_post_delay_reward_compartment_l1": round(
            mean(row["post_delay_difference"]["reward_compartment_l1"] for row in replicates),
            15,
        ),
        "mean_reward_compartment_l1_retention_ratio": round(mean(ratios), 12)
        if ratios
        else None,
        "recall_action_divergence_fraction": round(
            sum(row["action_diverged"] for row in pairs) / len(pairs), 12
        ),
        "mean_recall_difference_hz_delta": round(
            mean(row["difference_hz_delta"] for row in pairs), 12
        ),
        "mean_abs_recall_difference_hz_delta": round(
            mean(abs(row["difference_hz_delta"]) for row in pairs), 12
        ),
        "mean_recall_gate_spike_delta": round(
            mean(row["gate_spike_delta"] for row in pairs), 12
        ),
        "mean_recall_total_spike_delta": round(
            mean(row["total_spike_delta"] for row in pairs), 12
        ),
        "mean_recall_kc_spike_delta": round(
            mean(row["kc_spike_delta"] for row in pairs), 12
        ),
        "nonzero_recall_difference_hz_fraction": round(
            sum(abs(row["difference_hz_delta"]) > 1e-12 for row in pairs) / len(pairs),
            12,
        ),
        "nonzero_recall_total_spike_fraction": round(
            sum(row["total_spike_delta"] != 0 for row in pairs) / len(pairs),
            12,
        ),
    }


def run_reward_memory_recall(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Reward memory recall config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)

    source_before = _sha256_file(base_checkpoint)
    output_dir.mkdir(parents=True, exist_ok=True)
    replicates = [
        _run_replicate(
            replicate_id=replicate_id,
            trajectory_seed=seed,
            base_checkpoint=base_checkpoint,
            rep_dir=output_dir / replicate_id,
        )
        for replicate_id, seed in EXPECTED_REPLICATES
    ]
    source_after = _sha256_file(base_checkpoint)

    evidence_gates = {
        "source_checkpoint_unchanged": source_before == source_after,
        "all_replicates_executed": len(replicates) == len(EXPECTED_REPLICATES),
        "all_trajectories_complete": all(
            row["driver"]["decisions"] == EXPECTED_DECISIONS for row in replicates
        ),
        "trajectory_digests_unique": len(
            {row["driver"]["trajectory_digest"] for row in replicates}
        )
        == len(replicates),
        "driver_memory_frozen": all(
            row["driver"]["driver_frozen_memory_unchanged"] is True
            for row in replicates
        ),
        "all_events_are_reward": all(
            row["none"]["reinforcement"] == "none"
            and row["true_external"]["reinforcement"] == "reward"
            for row in replicates
        ),
        "all_delay_windows_exact": all(
            len(row["none"]["delay"]) == DELAY_DECISIONS
            and len(row["true_external"]["delay"]) == DELAY_DECISIONS
            for row in replicates
        ),
        "same_cue_pairing_exact": all(
            row["event_frame_sha256"] and row["event_context_sha256"]
            for row in replicates
        ),
        "post_event_effect_reward_local": all(
            row["post_event_difference"]["off_target_l1"] == 0.0
            for row in replicates
        ),
        "state_clear_preserved_memory": all(
            row["none"]["post_delay"]["fraction_digest"]
            == row["none"]["post_reset"]["fraction_digest"]
            and row["true_external"]["post_delay"]["fraction_digest"]
            == row["true_external"]["post_reset"]["fraction_digest"]
            for row in replicates
        ),
        "recall_memory_frozen": all(
            row["none"]["recall_memory_unchanged"] is True
            and row["true_external"]["recall_memory_unchanged"] is True
            for row in replicates
        ),
        "no_recall_stimulus": all(
            row["none"]["recall"]["stimulus_ms"] == 0.0
            and row["true_external"]["recall"]["stimulus_ms"] == 0.0
            for row in replicates
        ),
        "claims_remain_locked": all(
            value is False for value in config["claim_policy"].values()
        ),
    }
    execution_valid = all(config_gates.values()) and all(evidence_gates.values())

    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": "EXPLORATORY_RECALL_COMPLETE" if execution_valid else "INVALID_EXECUTION",
        "scope": SCOPE,
        "execution_valid": execution_valid,
        "config_gates": config_gates,
        "evidence_gates": evidence_gates,
        "source_checkpoint_sha256": source_before,
        "source_checkpoint_sha256_after": source_after,
        "replicates": replicates,
        "aggregate": _aggregate(replicates),
        "learning_validated": False,
        "reward_memory_persistence_causal": False,
        "cue_conditioned_behavior_effect_causal": False,
        "reinforcement_mechanism_validated": False,
        "causal_learning_claim_authorized": False,
        "replacement_confirmatory_authorized": False,
        "behavioral_promotion_authorized": False,
        "production_checkpoint_mutated": False,
        "human_science_review_required": True
    }
    body["receipt_sha256"] = _digest_json(body)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = receipt_path.with_suffix(receipt_path.suffix + ".partial")
    tmp.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    tmp.replace(receipt_path)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preregistered reward-memory cue recall diagnostic")
    parser.add_argument("--config", default="data/reward_memory_recall_v01.json")
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_reward_memory_recall(
        config_path=Path(args.config),
        base_checkpoint=Path(args.base_checkpoint),
        output_dir=Path(args.output_dir),
        receipt_path=Path(args.receipt),
    )
    print(json.dumps({
        "schema": result["schema"],
        "status": result["status"],
        "execution_valid": result["execution_valid"],
        "aggregate": result["aggregate"],
        "receipt_sha256": result["receipt_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if result["execution_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
