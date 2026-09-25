from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from statistics import mean, median
from typing import Any

from .brain_runtime import MaleCNSBrain
from .dan_trace_recentering_intervention import (
    BASELINE_DIGEST,
    BASELINE_HZ,
)
from .event_local_reinforcement_pulse import (
    EXPECTED_REPLICATES as EVENT_LOCAL_REPLICATES,
    USED_SEEDS,
    _build_pre_event_checkpoint,
    _restore_recentered,
)
from .full_network_reinforcement_pulse_replay import _record_trajectory
from .learning_control_study import _sha256_file
from .smoke import _digest_json


CONFIG_SCHEMA = "neurofly-compartment-plasticity-diagnostic-v0.1"
RECEIPT_SCHEMA = "neurofly-compartment-plasticity-diagnostic-receipt-v0.1"
STATUS = "PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE = "real-malecns-event-local-compartment-specific-plasticity"

EXPECTED_TRAJECTORY_DECISIONS = 60
EXPECTED_REPLICATES = (
    ("C1", 2309),
    ("C2", 2311),
    ("C3", 2333),
    ("C4", 2339),
)
EDGE_TOLERANCE = 1e-12
ORIGIN_RUN_ID = 35434647150
ORIGIN_RECEIPT = "6d7c7fc8c38106e8ceafb8e0346f87a7a6ae71cbfea59b2b3d9e372203e42712"
USED_WITH_EVENT_LOCAL = set(USED_SEEDS) | {seed for _, seed in EVENT_LOCAL_REPLICATES}

CLAIM_KEYS = {
    "learning_validated",
    "compartment_specificity_causal",
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
    compartments = config.get("compartments") or {}
    interpretation = config.get("interpretation_policy") or {}
    claims = config.get("claim_policy") or {}
    seeds = [seed for _, seed in EXPECTED_REPLICATES]
    return {
        "schema_exact": config.get("schema") == CONFIG_SCHEMA,
        "status_exact": config.get("status") == STATUS,
        "scope_exact": config.get("scope") == SCOPE,
        "question_frozen": config.get("question") == (
            "Does a true task reinforcement pulse produce edge-level efficacy "
            "redistribution concentrated in the anatomically intended KC-to-MBON "
            "memory compartment relative to an identical no-pulse branch?"
        ),
        "origin_exact": (
            origin.get("learning_mechanism_closeout_status")
            == "LEARNING_MECHANISM_DIAGNOSTIC_CLOSED"
            and origin.get("event_local_run_id") == ORIGIN_RUN_ID
            and origin.get("event_local_receipt_sha256") == ORIGIN_RECEIPT
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
            and runtime.get("edge_change_tolerance") == EDGE_TOLERANCE
        ),
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": (
            len(seeds) == len(set(seeds))
            and not (set(seeds) & USED_WITH_EVENT_LOCAL)
        ),
        "compartment_selection_frozen": (
            compartments.get("reward_event_target")
            == "KC-to-MBON07 edges selected by nonzero PAM11 gain"
            and compartments.get("aversive_event_target")
            == "KC-to-MBON11 edges selected by nonzero PPL101 gain"
            and compartments.get("selection_rule")
            == (
                "derive masks only from the frozen Stonkfly circuit gain matrix; "
                "do not select edges by observed effect"
            )
        ),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ())
        == (
            "reward_event_target_l1_fraction",
            "aversive_event_target_l1_fraction",
            "reward_event_target_mean_signed_delta",
            "aversive_event_target_mean_signed_delta",
            "reward_event_target_negative_edge_fraction",
            "aversive_event_target_negative_edge_fraction",
            "off_target_max_abs_delta",
            "event_action_divergence_fraction",
        ),
        "interpretation_locked": (
            interpretation.get("no_posthoc_edge_selection") is True
            and interpretation.get("no_parameter_tuning") is True
            and interpretation.get("no_directional_pass_threshold") is True
            and interpretation.get(
                "global_mean_efficacy_not_used_as_primary_mechanistic_endpoint"
            )
            is True
            and interpretation.get("result_is_descriptive_mechanism_evidence_only")
            is True
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims) == CLAIM_KEYS
            and all(value is False for value in claims.values())
        ),
    }


def _vector_digest(values: Any) -> str:
    import numpy as np

    array = np.asarray(values, dtype=np.float64)
    return hashlib.sha256(array.tobytes()).hexdigest()


def _plastic_edge_state(inner: MaleCNSBrain) -> dict[str, Any]:
    import numpy as np

    brain = inner.brain
    circuit = brain.circuit
    edges = np.asarray(circuit["edges"])
    baseline = np.asarray(brain.baseline_plastic, dtype=np.float64)
    fraction = np.asarray(brain.weight[edges], dtype=np.float64) / baseline
    memory_w = np.asarray(brain.memory_w, dtype=np.float64)

    if fraction.shape != memory_w.shape:
        raise RuntimeError("Plastic edge state shape mismatch")
    reconstruction_error = float(np.max(np.abs((fraction - 1.0) - memory_w)))
    if reconstruction_error > 1e-10:
        raise RuntimeError("Weight fraction and memory_w disagree")

    reward_count = len(circuit["reward"])
    gain = np.asarray(circuit["gain"], dtype=np.float64)
    reward_mask = np.any(np.abs(gain[:reward_count]) > 0.0, axis=0)
    aversive_mask = np.any(np.abs(gain[reward_count:]) > 0.0, axis=0)

    if np.any(reward_mask & aversive_mask):
        raise RuntimeError("Reward and aversive plastic compartments overlap")
    if not np.all(reward_mask | aversive_mask):
        raise RuntimeError("Plastic edge found outside frozen reward/aversive compartments")

    return {
        "fraction": fraction,
        "reward_mask": reward_mask,
        "aversive_mask": aversive_mask,
        "plastic_edges": int(len(edges)),
        "reward_edges": int(reward_mask.sum()),
        "aversive_edges": int(aversive_mask.sum()),
        "edge_index_digest": _digest_json([int(x) for x in edges.tolist()]),
        "reward_mask_digest": _digest_json([bool(x) for x in reward_mask.tolist()]),
        "aversive_mask_digest": _digest_json([bool(x) for x in aversive_mask.tolist()]),
        "fraction_digest": _vector_digest(fraction),
        "memory_w_reconstruction_max_abs_error": round(reconstruction_error, 15),
    }


def _summarize_difference(
    differences: list[float],
    target_mask: list[bool],
    *,
    tolerance: float = EDGE_TOLERANCE,
) -> dict[str, Any]:
    if len(differences) != len(target_mask) or not differences:
        raise ValueError("Difference vector and target mask must be non-empty and aligned")

    target = [float(v) for v, selected in zip(differences, target_mask) if selected]
    off = [float(v) for v, selected in zip(differences, target_mask) if not selected]
    if not target or not off:
        raise ValueError("Both target and off-target compartments must be populated")

    target_abs = [abs(v) for v in target]
    off_abs = [abs(v) for v in off]
    target_l1 = sum(target_abs)
    off_l1 = sum(off_abs)
    total_l1 = target_l1 + off_l1

    changed_target = [v for v in target if abs(v) > tolerance]
    changed_off = [v for v in off if abs(v) > tolerance]

    return {
        "target_edge_count": len(target),
        "off_target_edge_count": len(off),
        "target_changed_edge_count": len(changed_target),
        "off_target_changed_edge_count": len(changed_off),
        "target_positive_edge_count": sum(v > tolerance for v in target),
        "target_negative_edge_count": sum(v < -tolerance for v in target),
        "off_target_positive_edge_count": sum(v > tolerance for v in off),
        "off_target_negative_edge_count": sum(v < -tolerance for v in off),
        "target_mean_signed_delta": round(mean(target), 15),
        "off_target_mean_signed_delta": round(mean(off), 15),
        "target_mean_abs_delta": round(mean(target_abs), 15),
        "off_target_mean_abs_delta": round(mean(off_abs), 15),
        "target_median_abs_delta": round(median(target_abs), 15),
        "off_target_median_abs_delta": round(median(off_abs), 15),
        "target_l1": round(target_l1, 15),
        "off_target_l1": round(off_l1, 15),
        "target_l1_fraction": round(target_l1 / total_l1, 12) if total_l1 else 0.0,
        "target_dominant": target_l1 > off_l1,
        "target_negative_edge_fraction": round(
            sum(v < -tolerance for v in target) / len(target), 12
        ),
        "target_positive_edge_fraction": round(
            sum(v > tolerance for v in target) / len(target), 12
        ),
        "off_target_max_abs_delta": round(max(off_abs), 15),
    }


def _branch(
    *,
    pre_event_checkpoint: Path,
    event: dict[str, Any],
    reinforcement: str,
) -> dict[str, Any]:
    inner = _restore_recentered(pre_event_checkpoint)
    pre = _plastic_edge_state(inner)
    decision = inner.decide(
        event["frame"],
        reinforcement,
        context=copy.deepcopy(event["context"]),
    )
    post = _plastic_edge_state(inner)
    telemetry = copy.deepcopy(decision.telemetry)
    return {
        "action": decision.action,
        "reward_spikes": int(telemetry.get("reward_spikes") or 0),
        "aversive_spikes": int(telemetry.get("aversive_spikes") or 0),
        "stimulus_ms": float(telemetry.get("stimulus_ms") or 0.0),
        "pre": pre,
        "post": post,
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
        raise RuntimeError("Compartment diagnostic requires a reinforced event")

    event_dir.mkdir(parents=True, exist_ok=True)
    pre_event_checkpoint = event_dir / "pre-event.npz"
    pre = _build_pre_event_checkpoint(
        trajectory=trajectory,
        event_index=event_index,
        base_checkpoint=base_checkpoint,
        pre_event_checkpoint=pre_event_checkpoint,
    )
    source_sha = pre["pre_event_checkpoint_sha256"]

    none = _branch(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        reinforcement="none",
    )
    true = _branch(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        reinforcement=event_type,
    )

    if source_sha != _sha256_file(pre_event_checkpoint):
        raise RuntimeError("Pre-event checkpoint mutated during edge-level branches")

    for key in ("edge_index_digest", "reward_mask_digest", "aversive_mask_digest"):
        if none["pre"][key] != true["pre"][key] or none["post"][key] != true["post"][key]:
            raise RuntimeError(f"Plastic edge topology drifted: {key}")

    if not np.array_equal(none["pre"]["fraction"], true["pre"]["fraction"]):
        raise RuntimeError("Paired branches did not start from identical edge efficacies")

    difference = true["post"]["fraction"] - none["post"]["fraction"]
    reward_mask = none["pre"]["reward_mask"]
    aversive_mask = none["pre"]["aversive_mask"]
    target_mask = reward_mask if event_type == "reward" else aversive_mask

    target_summary = _summarize_difference(
        difference.tolist(),
        target_mask.tolist(),
    )
    reward_summary = _summarize_difference(
        difference.tolist(),
        reward_mask.tolist(),
    )
    aversive_summary = _summarize_difference(
        difference.tolist(),
        aversive_mask.tolist(),
    )

    return {
        "replicate_id": replicate_id,
        "event_ordinal": event_ordinal,
        "decision_index": event_index,
        "event_type": event_type,
        "frame_sha256": hashlib.sha256(event["frame"].tobytes()).hexdigest(),
        "context_sha256": _digest_json(event["context"]),
        "pre_event_checkpoint_sha256": source_sha,
        "plastic_edges": none["pre"]["plastic_edges"],
        "reward_edges": none["pre"]["reward_edges"],
        "aversive_edges": none["pre"]["aversive_edges"],
        "edge_index_digest": none["pre"]["edge_index_digest"],
        "reward_mask_digest": none["pre"]["reward_mask_digest"],
        "aversive_mask_digest": none["pre"]["aversive_mask_digest"],
        "none_post_fraction_digest": none["post"]["fraction_digest"],
        "true_post_fraction_digest": true["post"]["fraction_digest"],
        "paired_difference_digest": _vector_digest(difference),
        "memory_w_reconstruction_max_abs_error": max(
            none["pre"]["memory_w_reconstruction_max_abs_error"],
            none["post"]["memory_w_reconstruction_max_abs_error"],
            true["pre"]["memory_w_reconstruction_max_abs_error"],
            true["post"]["memory_w_reconstruction_max_abs_error"],
        ),
        "none": {
            "action": none["action"],
            "reward_spikes": none["reward_spikes"],
            "aversive_spikes": none["aversive_spikes"],
            "stimulus_ms": none["stimulus_ms"],
        },
        "true_external": {
            "action": true["action"],
            "reward_spikes": true["reward_spikes"],
            "aversive_spikes": true["aversive_spikes"],
            "stimulus_ms": true["stimulus_ms"],
        },
        "target_summary": target_summary,
        "reward_compartment_summary": reward_summary,
        "aversive_compartment_summary": aversive_summary,
        "action_diverged": none["action"] != true["action"],
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

    event_indices = [
        index
        for index, item in enumerate(trajectory)
        if item["true_reinforcement"] in {"reward", "aversive"}
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
        for ordinal, event_index in enumerate(event_indices, start=1)
    ]
    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "driver": driver,
        "event_indices": event_indices,
        "event_count": len(events),
        "events": events,
    }


def _aggregate_event_type(events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        return {
            "event_count": 0,
            "mean_target_l1_fraction": 0.0,
            "median_target_l1_fraction": 0.0,
            "target_dominant_event_fraction": 0.0,
            "mean_target_signed_delta": 0.0,
            "mean_target_abs_delta": 0.0,
            "mean_off_target_abs_delta": 0.0,
            "mean_target_negative_edge_fraction": 0.0,
            "mean_target_positive_edge_fraction": 0.0,
            "maximum_off_target_abs_delta": 0.0,
        }

    summaries = [event["target_summary"] for event in events]
    return {
        "event_count": len(events),
        "mean_target_l1_fraction": round(
            mean(row["target_l1_fraction"] for row in summaries), 12
        ),
        "median_target_l1_fraction": round(
            median(row["target_l1_fraction"] for row in summaries), 12
        ),
        "target_dominant_event_fraction": round(
            sum(row["target_dominant"] for row in summaries) / len(summaries), 12
        ),
        "mean_target_signed_delta": round(
            mean(row["target_mean_signed_delta"] for row in summaries), 15
        ),
        "mean_target_abs_delta": round(
            mean(row["target_mean_abs_delta"] for row in summaries), 15
        ),
        "mean_off_target_abs_delta": round(
            mean(row["off_target_mean_abs_delta"] for row in summaries), 15
        ),
        "mean_target_negative_edge_fraction": round(
            mean(row["target_negative_edge_fraction"] for row in summaries), 12
        ),
        "mean_target_positive_edge_fraction": round(
            mean(row["target_positive_edge_fraction"] for row in summaries), 12
        ),
        "maximum_off_target_abs_delta": round(
            max(row["off_target_max_abs_delta"] for row in summaries), 15
        ),
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    events = [event for rep in replicates for event in rep["events"]]
    reward = [event for event in events if event["event_type"] == "reward"]
    aversive = [event for event in events if event["event_type"] == "aversive"]
    return {
        "event_count": len(events),
        "reward": _aggregate_event_type(reward),
        "aversive": _aggregate_event_type(aversive),
        "event_action_divergence_fraction": round(
            sum(event["action_diverged"] for event in events) / len(events), 12
        )
        if events
        else 0.0,
        "mean_memory_w_reconstruction_max_abs_error": round(
            mean(event["memory_w_reconstruction_max_abs_error"] for event in events),
            15,
        )
        if events
        else 0.0,
    }


def run_compartment_plasticity_diagnostic(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Compartment plasticity config failed validation")
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
        "at_least_one_event_per_replicate": all(
            rep["event_count"] > 0 for rep in replicates
        ),
        "reward_and_aversive_events_observed": (
            any(event["event_type"] == "reward" for event in all_events)
            and any(event["event_type"] == "aversive" for event in all_events)
        ),
        "paired_edge_topology_exact": len(
            {
                (
                    event["edge_index_digest"],
                    event["reward_mask_digest"],
                    event["aversive_mask_digest"],
                )
                for event in all_events
            }
        )
        == 1,
        "memory_w_reconstruction_exact": all(
            event["memory_w_reconstruction_max_abs_error"] <= 1e-10
            for event in all_events
        ),
        "none_branches_have_no_stimulus": all(
            event["none"]["stimulus_ms"] == 0.0 for event in all_events
        ),
        "true_branches_deliver_20ms_stimulus": all(
            event["true_external"]["stimulus_ms"] == 20.0 for event in all_events
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
        "compartment_specificity_causal": False,
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
        description="Measure event-local edge redistribution by frozen KC-to-MBON compartment"
    )
    parser.add_argument(
        "--config",
        default="data/compartment_plasticity_diagnostic_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_compartment_plasticity_diagnostic(
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
