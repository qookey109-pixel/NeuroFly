from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any

from .compartment_plasticity_diagnostic import _plastic_edge_state
from .event_local_reinforcement_pulse import (
    _build_pre_event_checkpoint,
    _restore_recentered,
)
from .learning_control_study import _sha256_file
from .reward_memory_recall import (
    DELAY_DECISIONS,
    EXPECTED_REPLICATES as RECALL_V02_REPLICATES,
    MAX_ACQUISITION_DECISIONS,
    PRIOR_USED_SEEDS,
    _record_reward_anchored_trajectory,
)
from .smoke import _digest_json


CONFIG_SCHEMA = "neurofly-memory-expression-audit-v0.1"
RECEIPT_SCHEMA = "neurofly-memory-expression-audit-receipt-v0.1"
STATUS = "PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE = "real-malecns-reward-memory-expression-path"
CHANGED_TOLERANCE = 1e-12

EXPECTED_REPLICATES = (
    ("ME1", 2801),
    ("ME2", 2803),
    ("ME3", 2819),
    ("ME4", 2833),
)
USED_SEEDS = set(PRIOR_USED_SEEDS) | {seed for _, seed in RECALL_V02_REPLICATES}
ORIGIN_RUN_ID = 36094504041
ORIGIN_RECEIPT = "79eda0b1cf440e7e7bbe99233784b01789d010e16e136128dd8cdbbbe3431ca3"
ORIGIN_ARTIFACT = "be99048d5feb253e65418dbaedd8f3eff49be6f5e5e5abd9c68a937fd13febfc"
ORIGIN_FREEZE = "data/reward_memory_recall_v02_run1_freeze.json"

CLAIM_KEYS = {
    "learning_validated",
    "memory_expression_causal",
    "cue_indexing_failure_confirmed",
    "downstream_readout_failure_confirmed",
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
            "When a reward-pulse-induced KC-to-MBON07 synaptic difference persists "
            "but the state-cleared cue recall action is unchanged, is the stored "
            "difference engaged by cue-active presynaptic KCs, expressed at MBON07, "
            "and propagated toward the current DNp20/DNpe017 decoder?"
        ),
        "origin_exact": (
            origin.get("reward_recall_run_id") == ORIGIN_RUN_ID
            and origin.get("reward_recall_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("reward_recall_artifact_sha256") == ORIGIN_ARTIFACT
            and origin.get("reward_recall_freeze") == ORIGIN_FREEZE
        ),
        "runtime_exact": (
            runtime.get("event_acquisition")
            == "same event-triggered first-natural-reward rule as reward recall v0.2"
            and runtime.get("maximum_acquisition_decisions")
            == MAX_ACQUISITION_DECISIONS
            and runtime.get("post_event_replay_decisions") == DELAY_DECISIONS
            and runtime.get("post_event_external_reinforcement") == "none"
            and runtime.get("transient_state_policy")
            == (
                "brain.reset(keep_memory=true) before recall; "
                "wrapper visual-history state cleared"
            )
            and runtime.get("recall_external_reinforcement") == "none"
            and runtime.get("recall_plasticity_frozen") is True
            and runtime.get("changed_edge_tolerance_fraction") == CHANGED_TOLERANCE
            and runtime.get("no_model_parameter_change") is True
        ),
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": (
            len(seeds) == len(set(seeds)) and not (set(seeds) & USED_SEEDS)
        ),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ())
        == (
            "changed_reward_edge_count",
            "changed_reward_edge_active_presynaptic_fraction",
            "changed_reward_l1_on_active_presynaptic_fraction",
            "changed_presynaptic_kc_active_fraction",
            "mbon07_total_spike_delta",
            "mbon07_max_abs_membrane_delta",
            "mbon07_max_abs_conductance_delta",
            "dnp20_max_abs_membrane_delta",
            "dnpe017_max_abs_membrane_delta",
            "recall_action_divergence",
        ),
        "interpretation_locked": (
            interpretation.get("no_parameter_tuning") is True
            and interpretation.get("no_posthoc_edge_selection") is True
            and interpretation.get(
                "changed_edges_defined_only_by_paired_synaptic_difference"
            )
            is True
            and interpretation.get(
                "reward_compartment_defined_only_by_frozen_gain_topology"
            )
            is True
            and interpretation.get("no_directional_pass_threshold") is True
            and interpretation.get("result_is_mechanistic_localization_only") is True
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims) == CLAIM_KEYS
            and all(value is False for value in claims.values())
        ),
    }


def _population_state(inner: Any, indices: Any) -> dict[str, Any]:
    import numpy as np

    ix = np.asarray(indices, dtype=np.int64)
    b = inner.brain
    return {
        "indices": [int(x) for x in ix.tolist()],
        "ids": [str(b.ids[x]) for x in ix.tolist()],
        "counts": [int(x) for x in b.counts[ix].tolist()],
        "v": [round(float(x), 12) for x in b.v[ix].tolist()],
        "g": [round(float(x), 12) for x in b.g[ix].tolist()],
    }


def _branch(
    *,
    pre_event_checkpoint: Path,
    event: dict[str, Any],
    delay_rows: list[dict[str, Any]],
    reinforcement: str,
) -> dict[str, Any]:
    import numpy as np

    inner = _restore_recentered(pre_event_checkpoint)

    inner.decide(
        event["frame"],
        reinforcement,
        context=copy.deepcopy(event["context"]),
    )
    for row in delay_rows:
        decision = inner.decide(
            row["frame"],
            "none",
            context=copy.deepcopy(row["context"]),
        )
        if float(decision.telemetry.get("stimulus_ms") or 0.0) != 0.0:
            raise RuntimeError("Delay replay delivered external reinforcement")

    post_delay = _plastic_edge_state(inner)
    memory_before_reset = post_delay["fraction_digest"]

    inner.brain.reset(keep_memory=True)
    inner._last_visual_rgb = None
    post_reset = _plastic_edge_state(inner)
    if post_reset["fraction_digest"] != memory_before_reset:
        raise RuntimeError("State clearing did not preserve synaptic memory")

    inner.learning = False
    inner.brain.weights_frozen = True
    recall_memory_before = _plastic_edge_state(inner)
    recall_decision = inner.decide(
        event["frame"],
        "none",
        context=copy.deepcopy(event["context"]),
    )
    recall_memory_after = _plastic_edge_state(inner)
    if recall_memory_before["fraction_digest"] != recall_memory_after["fraction_digest"]:
        raise RuntimeError("Frozen recall mutated memory")

    b = inner.brain
    c = b.circuit
    reward_count = len(c["reward"])
    reward_edge_mask = np.any(np.abs(c["gain"][:reward_count]) > 0.0, axis=0)
    reward_edges = np.asarray(c["edges"])[reward_edge_mask]
    reward_pre = np.asarray(c["pre"])[reward_edge_mask]
    reward_post = np.asarray(b.post)[reward_edges]
    reward_mbon = np.unique(reward_post).astype(np.int64)

    return {
        "reinforcement": reinforcement,
        "post_delay_fraction": np.asarray(post_delay["fraction"], dtype=np.float64),
        "reward_edge_mask": reward_edge_mask,
        "reward_pre": reward_pre,
        "reward_post": reward_post,
        "reward_weights": np.asarray(b.weight[reward_edges], dtype=np.float64).copy(),
        "counts": np.asarray(b.counts, dtype=np.int64).copy(),
        "reward_mbon": _population_state(inner, reward_mbon),
        "left_decoder": _population_state(inner, inner.left),
        "right_decoder": _population_state(inner, inner.right),
        "gate_decoder": _population_state(inner, inner.gate),
        "action": recall_decision.action,
        "recall_stimulus_ms": float(
            recall_decision.telemetry.get("stimulus_ms") or 0.0
        ),
        "post_delay_fraction_digest": post_delay["fraction_digest"],
        "post_reset_fraction_digest": post_reset["fraction_digest"],
        "recall_memory_unchanged": True,
    }


def _max_abs_delta(a: list[float], b: list[float]) -> float:
    return round(max((abs(x - y) for x, y in zip(a, b, strict=True)), default=0.0), 12)


def _sum_delta(a: list[int], b: list[int]) -> int:
    return int(sum(a) - sum(b))


def _paired_expression(none: dict[str, Any], true: dict[str, Any]) -> dict[str, Any]:
    import numpy as np

    if not np.array_equal(none["reward_edge_mask"], true["reward_edge_mask"]):
        raise RuntimeError("Reward edge mask drifted")
    if not np.array_equal(none["reward_pre"], true["reward_pre"]):
        raise RuntimeError("Reward presynaptic topology drifted")
    if not np.array_equal(none["reward_post"], true["reward_post"]):
        raise RuntimeError("Reward postsynaptic topology drifted")

    mask = np.asarray(none["reward_edge_mask"], dtype=bool)
    delta_fraction = (
        np.asarray(true["post_delay_fraction"])[mask]
        - np.asarray(none["post_delay_fraction"])[mask]
    )
    changed = np.abs(delta_fraction) > CHANGED_TOLERANCE
    if not np.any(changed):
        raise RuntimeError("No paired reward-memory edge difference to audit")

    pre = np.asarray(none["reward_pre"], dtype=np.int64)
    changed_pre = pre[changed]
    none_counts = np.asarray(none["counts"], dtype=np.int64)
    true_counts = np.asarray(true["counts"], dtype=np.int64)
    active_edges = changed & (
        (none_counts[pre] > 0) | (true_counts[pre] > 0)
    )

    total_l1 = float(np.abs(delta_fraction[changed]).sum())
    active_l1 = float(np.abs(delta_fraction[active_edges]).sum())

    unique_changed_pre = np.unique(changed_pre)
    active_changed_pre = (
        (none_counts[unique_changed_pre] > 0)
        | (true_counts[unique_changed_pre] > 0)
    )

    delta_weight = np.asarray(true["reward_weights"]) - np.asarray(none["reward_weights"])
    weighted_drive_proxy = float(
        np.sum(delta_weight[changed] * none_counts[pre[changed]])
    )

    nm = none["reward_mbon"]
    tm = true["reward_mbon"]
    return {
        "changed_reward_edge_count": int(changed.sum()),
        "changed_reward_edge_active_presynaptic_count": int(active_edges.sum()),
        "changed_reward_edge_active_presynaptic_fraction": round(
            float(active_edges.sum()) / float(changed.sum()), 12
        ),
        "changed_reward_l1": round(total_l1, 15),
        "changed_reward_l1_on_active_presynaptic": round(active_l1, 15),
        "changed_reward_l1_on_active_presynaptic_fraction": round(
            active_l1 / total_l1, 12
        ) if total_l1 else 0.0,
        "unique_changed_presynaptic_kc_count": int(len(unique_changed_pre)),
        "active_changed_presynaptic_kc_count": int(active_changed_pre.sum()),
        "changed_presynaptic_kc_active_fraction": round(
            float(active_changed_pre.sum()) / float(len(unique_changed_pre)), 12
        ),
        "paired_weighted_presynaptic_drive_proxy": round(weighted_drive_proxy, 12),
        "mbon07_ids": nm["ids"],
        "mbon07_none_counts": nm["counts"],
        "mbon07_true_counts": tm["counts"],
        "mbon07_total_spike_delta": _sum_delta(tm["counts"], nm["counts"]),
        "mbon07_max_abs_membrane_delta": _max_abs_delta(tm["v"], nm["v"]),
        "mbon07_max_abs_conductance_delta": _max_abs_delta(tm["g"], nm["g"]),
        "dnp20_left_total_spike_delta": _sum_delta(
            true["left_decoder"]["counts"], none["left_decoder"]["counts"]
        ),
        "dnp20_right_total_spike_delta": _sum_delta(
            true["right_decoder"]["counts"], none["right_decoder"]["counts"]
        ),
        "dnp20_max_abs_membrane_delta": max(
            _max_abs_delta(true["left_decoder"]["v"], none["left_decoder"]["v"]),
            _max_abs_delta(true["right_decoder"]["v"], none["right_decoder"]["v"]),
        ),
        "dnpe017_total_spike_delta": _sum_delta(
            true["gate_decoder"]["counts"], none["gate_decoder"]["counts"]
        ),
        "dnpe017_max_abs_membrane_delta": _max_abs_delta(
            true["gate_decoder"]["v"], none["gate_decoder"]["v"]
        ),
        "recall_action_diverged": none["action"] != true["action"],
        "none_action": none["action"],
        "true_action": true["action"],
    }


def _run_replicate(
    *,
    replicate_id: str,
    trajectory_seed: int,
    base_checkpoint: Path,
    rep_dir: Path,
) -> dict[str, Any]:
    rep_dir.mkdir(parents=True, exist_ok=True)
    trajectory, driver, event_index = _record_reward_anchored_trajectory(
        base_checkpoint=base_checkpoint,
        driver_checkpoint=rep_dir / "trajectory-driver.npz",
        trajectory_seed=trajectory_seed,
    )
    event = trajectory[event_index]
    delay_rows = trajectory[event_index + 1 : event_index + 1 + DELAY_DECISIONS]
    if event["true_reinforcement"] != "reward":
        raise RuntimeError("Frozen event is not the first natural reward")
    if len(delay_rows) != DELAY_DECISIONS:
        raise RuntimeError("Incomplete delay window")

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

    expression = _paired_expression(none, true)
    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "acquisition_decisions": len(trajectory),
        "event_index": event_index,
        "trajectory_digest": driver["trajectory_digest"],
        "driver_frozen_memory_unchanged": driver["driver_frozen_memory_unchanged"],
        "event_frame_sha256": hashlib.sha256(event["frame"].tobytes()).hexdigest(),
        "event_context_sha256": _digest_json(event["context"]),
        "none_post_delay_fraction_digest": none["post_delay_fraction_digest"],
        "true_post_delay_fraction_digest": true["post_delay_fraction_digest"],
        "none_state_clear_preserved_memory": (
            none["post_delay_fraction_digest"] == none["post_reset_fraction_digest"]
        ),
        "true_state_clear_preserved_memory": (
            true["post_delay_fraction_digest"] == true["post_reset_fraction_digest"]
        ),
        "none_recall_memory_unchanged": none["recall_memory_unchanged"],
        "true_recall_memory_unchanged": true["recall_memory_unchanged"],
        "none_recall_stimulus_ms": none["recall_stimulus_ms"],
        "true_recall_stimulus_ms": true["recall_stimulus_ms"],
        "expression": expression,
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    e = [row["expression"] for row in replicates]
    return {
        "replicate_count": len(e),
        "mean_changed_reward_edge_count": round(
            mean(row["changed_reward_edge_count"] for row in e), 8
        ),
        "mean_changed_reward_edge_active_presynaptic_fraction": round(
            mean(row["changed_reward_edge_active_presynaptic_fraction"] for row in e),
            12,
        ),
        "mean_changed_reward_l1_on_active_presynaptic_fraction": round(
            mean(row["changed_reward_l1_on_active_presynaptic_fraction"] for row in e),
            12,
        ),
        "mean_changed_presynaptic_kc_active_fraction": round(
            mean(row["changed_presynaptic_kc_active_fraction"] for row in e), 12
        ),
        "mean_paired_weighted_presynaptic_drive_proxy": round(
            mean(row["paired_weighted_presynaptic_drive_proxy"] for row in e), 12
        ),
        "mean_mbon07_total_spike_delta": round(
            mean(row["mbon07_total_spike_delta"] for row in e), 12
        ),
        "mean_mbon07_max_abs_membrane_delta": round(
            mean(row["mbon07_max_abs_membrane_delta"] for row in e), 12
        ),
        "mean_mbon07_max_abs_conductance_delta": round(
            mean(row["mbon07_max_abs_conductance_delta"] for row in e), 12
        ),
        "mean_dnp20_max_abs_membrane_delta": round(
            mean(row["dnp20_max_abs_membrane_delta"] for row in e), 12
        ),
        "mean_dnpe017_max_abs_membrane_delta": round(
            mean(row["dnpe017_max_abs_membrane_delta"] for row in e), 12
        ),
        "recall_action_divergence_fraction": round(
            sum(row["recall_action_diverged"] for row in e) / len(e), 12
        ),
    }


def run_memory_expression_audit(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Memory expression config failed validation")
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
        "trajectory_digests_unique": len(
            {row["trajectory_digest"] for row in replicates}
        ) == len(replicates),
        "driver_memory_frozen": all(
            row["driver_frozen_memory_unchanged"] is True for row in replicates
        ),
        "all_acquisitions_within_max": all(
            1 <= row["acquisition_decisions"] <= MAX_ACQUISITION_DECISIONS
            for row in replicates
        ),
        "all_state_clears_preserve_memory": all(
            row["none_state_clear_preserved_memory"]
            and row["true_state_clear_preserved_memory"]
            for row in replicates
        ),
        "all_recall_memory_frozen": all(
            row["none_recall_memory_unchanged"]
            and row["true_recall_memory_unchanged"]
            for row in replicates
        ),
        "all_recall_external_stimulus_zero": all(
            row["none_recall_stimulus_ms"] == 0.0
            and row["true_recall_stimulus_ms"] == 0.0
            for row in replicates
        ),
        "all_have_changed_reward_edges": all(
            row["expression"]["changed_reward_edge_count"] > 0
            for row in replicates
        ),
        "claims_remain_locked": all(
            value is False for value in config["claim_policy"].values()
        ),
    }
    execution_valid = all(config_gates.values()) and all(evidence_gates.values())

    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": (
            "EXPLORATORY_EXPRESSION_AUDIT_COMPLETE"
            if execution_valid
            else "INVALID_EXECUTION"
        ),
        "scope": SCOPE,
        "execution_valid": execution_valid,
        "config_gates": config_gates,
        "evidence_gates": evidence_gates,
        "source_checkpoint_sha256": source_before,
        "source_checkpoint_sha256_after": source_after,
        "replicates": replicates,
        "aggregate": _aggregate(replicates),
        "learning_validated": False,
        "memory_expression_causal": False,
        "cue_indexing_failure_confirmed": False,
        "downstream_readout_failure_confirmed": False,
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
    parser = argparse.ArgumentParser(description="Audit reward-memory expression path")
    parser.add_argument("--config", default="data/memory_expression_audit_v01.json")
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_memory_expression_audit(
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
