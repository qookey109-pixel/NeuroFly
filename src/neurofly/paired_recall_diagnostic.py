from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from statistics import mean, median
from typing import Any

from .compartment_plasticity_diagnostic import (
    EXPECTED_REPLICATES as COMPARTMENT_REPLICATES,
    USED_WITH_EVENT_LOCAL,
    _plastic_edge_state,
    _summarize_difference,
)
from .dan_trace_recentering_intervention import BASELINE_DIGEST, BASELINE_HZ
from .event_local_reinforcement_pulse import (
    _build_pre_event_checkpoint,
    _restore_recentered,
)
from .full_network_reinforcement_pulse_replay import _record_trajectory
from .learning_control_study import _sha256_file
from .smoke import _digest_json


CONFIG_SCHEMA = "neurofly-paired-recall-diagnostic-v0.1"
RECEIPT_SCHEMA = "neurofly-paired-recall-diagnostic-receipt-v0.1"
STATUS = "PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE = "real-malecns-post-reinforcement-paired-cue-recall"

EXPECTED_TRAJECTORY_DECISIONS = 60
DELAY_DECISIONS = 8
EXPECTED_REPLICATES = (
    ("RCL1", 2459),
    ("RCL2", 2467),
    ("RCL3", 2473),
    ("RCL4", 2477),
)
ORIGIN_RUN_ID = 36090134339
ORIGIN_RECEIPT = "19802e5a95243b55f1712b313e6e844637a85eff4c35e405d8d4b8a936e71308"
ORIGIN_ARTIFACT = "5e7c347af0adc0d4dad1b94812012413423d5ac34d48e319eb9920b61c25f8be"
USED_SEEDS = set(USED_WITH_EVENT_LOCAL) | {seed for _, seed in COMPARTMENT_REPLICATES}

CLAIM_KEYS = {
    "learning_validated",
    "paired_recall_effect_causal",
    "cue_conditioned_behavior_validated",
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
            "Does the compartment-local efficacy difference caused by one true task "
            "reinforcement pulse persist through identical reinforcement-free replay "
            "and alter the later neural/action response to the same cue?"
        ),
        "origin_exact": (
            origin.get("compartment_run_id") == ORIGIN_RUN_ID
            and origin.get("compartment_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("compartment_artifact_sha256") == ORIGIN_ARTIFACT
            and origin.get("observed_target_l1_fraction") == 1.0
            and origin.get("observed_off_target_effect") == 0.0
        ),
        "runtime_exact": (
            runtime.get("decision_synchronous_world") is True
            and runtime.get("trajectory_decisions") == EXPECTED_TRAJECTORY_DECISIONS
            and runtime.get("delay_decisions") == DELAY_DECISIONS
            and runtime.get("neural_ms_per_decision") == 50
            and runtime.get("pulse_ms") == 20
            and runtime.get("pulse_current") == 20.0
            and runtime.get("pre_event_history_reinforcement") == "none"
            and runtime.get("post_event_replay_reinforcement") == "none"
            and runtime.get("recall_reinforcement") == "none"
            and runtime.get("paired_conditions") == ["none", "true_external"]
            and runtime.get("baseline_mode") == "calibrated"
            and runtime.get("trace_state_mode") == "subtract_baseline"
            and runtime.get("replay_source") == "frozen recorded frames and contexts"
            and runtime.get("recall_cue") == "exact original event frame and context"
        ),
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": (
            len(seeds) == len(set(seeds))
            and not (set(seeds) & USED_SEEDS)
        ),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ())
        == (
            "immediate_target_l1",
            "delayed_target_l1",
            "target_l1_persistence_ratio",
            "delayed_target_mean_signed_delta",
            "recall_action_divergence_fraction",
            "recall_difference_hz_delta",
            "recall_gate_spike_delta",
            "recall_total_spike_delta",
        ),
        "interpretation_locked": (
            interpretation.get("no_parameter_tuning") is True
            and interpretation.get("no_posthoc_event_selection") is True
            and interpretation.get("all_eligible_reinforced_events_used") is True
            and interpretation.get("no_directional_pass_threshold") is True
            and interpretation.get("fixed_delay_before_execution") is True
            and interpretation.get("result_is_descriptive_mechanism_evidence_only")
            is True
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims) == CLAIM_KEYS
            and all(value is False for value in claims.values())
        ),
    }


def _fraction_digest(values: Any) -> str:
    import numpy as np

    return hashlib.sha256(
        np.asarray(values, dtype=np.float64).tobytes()
    ).hexdigest()


def _sanitized_state(state: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in state.items()
        if key not in {"fraction", "reward_mask", "aversive_mask"}
    }


def _target_mask(state: dict[str, Any], event_type: str) -> Any:
    if event_type == "reward":
        return state["reward_mask"]
    if event_type == "aversive":
        return state["aversive_mask"]
    raise ValueError(event_type)


def _persistence_ratio(immediate_l1: float, delayed_l1: float) -> float | None:
    if immediate_l1 <= 0:
        return None
    return round(float(delayed_l1) / float(immediate_l1), 12)


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


def _run_branch(
    *,
    pre_event_checkpoint: Path,
    event: dict[str, Any],
    delay_items: list[dict[str, Any]],
    reinforcement: str,
) -> dict[str, Any]:
    inner = _restore_recentered(pre_event_checkpoint)

    pre = _plastic_edge_state(inner)
    event_decision = inner.decide(
        event["frame"],
        reinforcement,
        context=copy.deepcopy(event["context"]),
    )
    immediate = _plastic_edge_state(inner)

    delay_rows = []
    for delay_index, item in enumerate(delay_items, start=1):
        decision = inner.decide(
            item["frame"],
            "none",
            context=copy.deepcopy(item["context"]),
        )
        row = _telemetry(decision)
        if row["stimulus_ms"] != 0.0:
            raise RuntimeError("Delay replay delivered external reinforcement")
        delay_rows.append(
            {
                "delay_index": delay_index,
                "frame_sha256": hashlib.sha256(item["frame"].tobytes()).hexdigest(),
                "context_sha256": _digest_json(item["context"]),
                **row,
            }
        )

    delayed = _plastic_edge_state(inner)
    recall_decision = inner.decide(
        event["frame"],
        "none",
        context=copy.deepcopy(event["context"]),
    )
    recall = _telemetry(recall_decision)
    if recall["stimulus_ms"] != 0.0:
        raise RuntimeError("Recall cue delivered external reinforcement")

    return {
        "pre": pre,
        "immediate": immediate,
        "delayed": delayed,
        "event": _telemetry(event_decision),
        "delay_rows": delay_rows,
        "recall": recall,
    }


def _paired_event(
    *,
    replicate_id: str,
    event_ordinal: int,
    event_index: int,
    trajectory: list[dict[str, Any]],
    base_checkpoint: Path,
    event_dir: Path,
) -> dict[str, Any]:
    import numpy as np

    event = trajectory[event_index]
    event_type = str(event["true_reinforcement"])
    if event_type not in {"reward", "aversive"}:
        raise RuntimeError("Recall diagnostic requires a reinforced event")

    delay_items = trajectory[
        event_index + 1 : event_index + 1 + DELAY_DECISIONS
    ]
    if len(delay_items) != DELAY_DECISIONS:
        raise RuntimeError("Eligible recall event lacks frozen delay frames")

    event_dir.mkdir(parents=True, exist_ok=True)
    pre_event_checkpoint = event_dir / "pre-event.npz"
    pre_info = _build_pre_event_checkpoint(
        trajectory=trajectory,
        event_index=event_index,
        base_checkpoint=base_checkpoint,
        pre_event_checkpoint=pre_event_checkpoint,
    )
    source_sha = pre_info["pre_event_checkpoint_sha256"]

    none = _run_branch(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        delay_items=delay_items,
        reinforcement="none",
    )
    true = _run_branch(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        delay_items=delay_items,
        reinforcement=event_type,
    )

    if source_sha != _sha256_file(pre_event_checkpoint):
        raise RuntimeError("Pre-event checkpoint mutated during paired recall branches")

    for key in ("edge_index_digest", "reward_mask_digest", "aversive_mask_digest"):
        for phase in ("pre", "immediate", "delayed"):
            if none[phase][key] != true[phase][key]:
                raise RuntimeError(f"Paired recall topology drifted: {phase}/{key}")

    if not np.array_equal(none["pre"]["fraction"], true["pre"]["fraction"]):
        raise RuntimeError("Paired recall branches did not start from identical memory")

    target_mask = _target_mask(none["pre"], event_type)
    immediate_diff = true["immediate"]["fraction"] - none["immediate"]["fraction"]
    delayed_diff = true["delayed"]["fraction"] - none["delayed"]["fraction"]
    immediate_summary = _summarize_difference(
        immediate_diff.tolist(), target_mask.tolist()
    )
    delayed_summary = _summarize_difference(
        delayed_diff.tolist(), target_mask.tolist()
    )

    persistence = _persistence_ratio(
        immediate_summary["target_l1"],
        delayed_summary["target_l1"],
    )
    recall_none = none["recall"]
    recall_true = true["recall"]

    return {
        "replicate_id": replicate_id,
        "event_ordinal": event_ordinal,
        "decision_index": event_index,
        "event_type": event_type,
        "frame_sha256": hashlib.sha256(event["frame"].tobytes()).hexdigest(),
        "context_sha256": _digest_json(event["context"]),
        "delay_decisions": DELAY_DECISIONS,
        "delay_frame_digests": [
            hashlib.sha256(item["frame"].tobytes()).hexdigest()
            for item in delay_items
        ],
        "pre_event_checkpoint_sha256": source_sha,
        "topology": _sanitized_state(none["pre"]),
        "none_event": none["event"],
        "true_event": true["event"],
        "immediate_difference_digest": _fraction_digest(immediate_diff),
        "delayed_difference_digest": _fraction_digest(delayed_diff),
        "immediate_target_summary": immediate_summary,
        "delayed_target_summary": delayed_summary,
        "target_l1_persistence_ratio": persistence,
        "recall": {
            "none": recall_none,
            "true_external_history": recall_true,
            "action_diverged": recall_none["action"] != recall_true["action"],
            "left_hz_delta": round(
                recall_true["left_hz"] - recall_none["left_hz"], 12
            ),
            "right_hz_delta": round(
                recall_true["right_hz"] - recall_none["right_hz"], 12
            ),
            "difference_hz_delta": round(
                recall_true["difference_hz"] - recall_none["difference_hz"], 12
            ),
            "gate_spike_delta": recall_true["gate_spikes"] - recall_none["gate_spikes"],
            "reward_spike_delta": (
                recall_true["reward_spikes"] - recall_none["reward_spikes"]
            ),
            "aversive_spike_delta": (
                recall_true["aversive_spikes"] - recall_none["aversive_spikes"]
            ),
            "kc_spike_delta": recall_true["kc_spikes"] - recall_none["kc_spikes"],
            "total_spike_delta": (
                recall_true["total_spikes"] - recall_none["total_spikes"]
            ),
        },
        "delay_replay_exact_count": (
            len(none["delay_rows"]) == DELAY_DECISIONS
            and len(true["delay_rows"]) == DELAY_DECISIONS
        ),
        "all_post_event_stimulus_zero": (
            all(row["stimulus_ms"] == 0.0 for row in none["delay_rows"])
            and all(row["stimulus_ms"] == 0.0 for row in true["delay_rows"])
            and recall_none["stimulus_ms"] == 0.0
            and recall_true["stimulus_ms"] == 0.0
        ),
    }


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
    if len(trajectory) != EXPECTED_TRAJECTORY_DECISIONS:
        raise RuntimeError("Unexpected trajectory length")

    eligible = [
        index
        for index, item in enumerate(trajectory)
        if item["true_reinforcement"] in {"reward", "aversive"}
        and index + DELAY_DECISIONS < len(trajectory)
    ]
    events = [
        _paired_event(
            replicate_id=replicate_id,
            event_ordinal=ordinal,
            event_index=event_index,
            trajectory=trajectory,
            base_checkpoint=base_checkpoint,
            event_dir=rep_dir / f"event-{ordinal:02d}",
        )
        for ordinal, event_index in enumerate(eligible, start=1)
    ]
    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "driver": driver,
        "eligible_event_indices": eligible,
        "eligible_event_count": len(events),
        "events": events,
    }


def _aggregate_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "event_count": 0,
            "mean_immediate_target_l1": 0.0,
            "mean_delayed_target_l1": 0.0,
            "mean_persistence_ratio": None,
            "median_persistence_ratio": None,
            "mean_delayed_target_signed_delta": 0.0,
            "recall_action_divergence_fraction": 0.0,
            "mean_recall_difference_hz_delta": 0.0,
            "mean_recall_gate_spike_delta": 0.0,
            "mean_recall_total_spike_delta": 0.0,
        }

    ratios = [
        event["target_l1_persistence_ratio"]
        for event in events
        if event["target_l1_persistence_ratio"] is not None
    ]
    return {
        "event_count": len(events),
        "mean_immediate_target_l1": round(
            mean(event["immediate_target_summary"]["target_l1"] for event in events),
            15,
        ),
        "mean_delayed_target_l1": round(
            mean(event["delayed_target_summary"]["target_l1"] for event in events),
            15,
        ),
        "mean_persistence_ratio": (
            round(mean(ratios), 12) if ratios else None
        ),
        "median_persistence_ratio": (
            round(median(ratios), 12) if ratios else None
        ),
        "mean_delayed_target_signed_delta": round(
            mean(
                event["delayed_target_summary"]["target_mean_signed_delta"]
                for event in events
            ),
            15,
        ),
        "recall_action_divergence_fraction": round(
            sum(event["recall"]["action_diverged"] for event in events)
            / len(events),
            12,
        ),
        "mean_recall_difference_hz_delta": round(
            mean(event["recall"]["difference_hz_delta"] for event in events),
            12,
        ),
        "mean_recall_gate_spike_delta": round(
            mean(event["recall"]["gate_spike_delta"] for event in events),
            12,
        ),
        "mean_recall_total_spike_delta": round(
            mean(event["recall"]["total_spike_delta"] for event in events),
            12,
        ),
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    events = [event for rep in replicates for event in rep["events"]]
    reward = [event for event in events if event["event_type"] == "reward"]
    aversive = [event for event in events if event["event_type"] == "aversive"]
    return {
        "all_events": _aggregate_events(events),
        "reward_events": _aggregate_events(reward),
        "aversive_events": _aggregate_events(aversive),
    }


def run_paired_recall_diagnostic(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Paired recall config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)

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
    all_events = [event for rep in replicates for event in rep["events"]]

    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "all_replicates_executed": len(replicates) == len(EXPECTED_REPLICATES),
        "all_trajectories_complete": all(
            rep["driver"]["decisions"] == EXPECTED_TRAJECTORY_DECISIONS
            for rep in replicates
        ),
        "trajectory_driver_frozen_memory_unchanged": all(
            rep["driver"]["driver_frozen_memory_unchanged"] is True
            for rep in replicates
        ),
        "at_least_one_eligible_event_total": len(all_events) > 0,
        "all_eligible_events_used": sum(
            rep["eligible_event_count"] for rep in replicates
        )
        == len(all_events),
        "all_delay_replay_counts_exact": all(
            event["delay_replay_exact_count"] for event in all_events
        ),
        "all_post_event_external_reinforcement_suppressed": all(
            event["all_post_event_stimulus_zero"] for event in all_events
        ),
        "none_event_branches_have_no_stimulus": all(
            event["none_event"]["stimulus_ms"] == 0.0 for event in all_events
        ),
        "true_event_branches_deliver_20ms_stimulus": all(
            event["true_event"]["stimulus_ms"] == 20.0 for event in all_events
        ),
        "claims_remain_locked": all(
            value is False for value in config["claim_policy"].values()
        ),
    }
    execution_valid = all(config_gates.values()) and all(evidence_gates.values())

    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": (
            "EXPLORATORY_DIAGNOSTIC_COMPLETE"
            if execution_valid
            else "INVALID_EXECUTION"
        ),
        "scope": SCOPE,
        "execution_valid": execution_valid,
        "config_gates": config_gates,
        "evidence_gates": evidence_gates,
        "source_checkpoint_sha256": source_sha_before,
        "source_checkpoint_sha256_after": source_sha_after,
        "frozen_baseline_hz": list(BASELINE_HZ),
        "frozen_baseline_digest": BASELINE_DIGEST,
        "replicates": replicates,
        "aggregate": _aggregate(replicates),
        "learning_validated": False,
        "paired_recall_effect_causal": False,
        "cue_conditioned_behavior_validated": False,
        "reinforcement_mechanism_validated": False,
        "causal_learning_claim_authorized": False,
        "replacement_confirmatory_authorized": False,
        "behavioral_promotion_authorized": False,
        "production_checkpoint_mutated": False,
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
        description="Run paired post-reinforcement cue recall on frozen MaleCNS trajectories"
    )
    parser.add_argument(
        "--config",
        default="data/paired_recall_diagnostic_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_paired_recall_diagnostic(
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
