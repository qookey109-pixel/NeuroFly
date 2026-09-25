from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from .brain_runtime import MaleCNSBrain
from .compartment_plasticity_diagnostic import _plastic_edge_state
from .dan_baseline_intervention import _memory_snapshot
from .event_local_reinforcement_pulse import (
    _build_pre_event_checkpoint,
    _restore_recentered,
)
from .full_network_reinforcement_pulse_replay import (
    FixedTrajectoryRecorder,
    _trajectory_receipt_rows,
)
from .goal_training import GoalMazeEnvironment, GoalMazeSession
from .learning_control_study import _sha256_file
from .memory_expression_audit import (
    _max_abs_delta,
    _population_state,
    _sum_delta,
)
from .smoke import _digest_json, _neural_decision_verified


CONFIG_SCHEMA = "neurofly-memory-temporal-index-audit-v0.1"
RECEIPT_SCHEMA = "neurofly-memory-temporal-index-audit-receipt-v0.1"
STATUS = "PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE = "real-malecns-reward-memory-temporal-index"

KC_TRACE_SECONDS = 1.0
NEURAL_MS_PER_DECISION = 50
TRACE_WINDOW_DECISIONS = 20
MAX_ACQUISITION_DECISIONS = 300
POST_REWARD_DELAY_DECISIONS = 5
CHANGED_TOLERANCE = 1e-12
STATE_TOLERANCE = 1e-12

EXPECTED_REPLICATES = (
    ("TI1", 2903),
    ("TI2", 2909),
    ("TI3", 2917),
    ("TI4", 2927),
)
PRIOR_SEEDS = {
    2309, 2311, 2333, 2339,
    2609, 2617, 2621, 2633,
    2711, 2713, 2719, 2729,
    2801, 2803, 2819, 2833,
}
ORIGIN_RUN_ID = 36095246269
ORIGIN_RECEIPT = "a44838d604a8f277b877bcd8195ff69604b9d0f35cdb8b45bf1270dff0b9bbca"
ORIGIN_ARTIFACT = "96196df2069176c49c29676a9eac7e1d60e36439a9fa33cfa5260e363a04de13"
ORIGIN_FREEZE = "data/memory_expression_audit_run1_freeze_v01.json"

CLAIM_KEYS = {
    "learning_validated",
    "temporal_cue_index_confirmed",
    "cue_indexing_failure_confirmed",
    "memory_expression_causal",
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
    clock = config.get("model_clock") or {}
    runtime = config.get("runtime") or {}
    interpretation = config.get("interpretation_policy") or {}
    claims = config.get("claim_policy") or {}
    seeds = [seed for _, seed in EXPECTED_REPLICATES]

    return {
        "schema_exact": config.get("schema") == CONFIG_SCHEMA,
        "status_exact": config.get("status") == STATUS,
        "scope_exact": config.get("scope") == SCOPE,
        "question_frozen": config.get("question") == (
            "Does the 1-second frozen KC eligibility history identify and "
            "re-engage the presynaptic KC ensemble carrying the persistent "
            "reward-memory difference when the full prereward sensory sequence "
            "is replayed after transient-state clearing?"
        ),
        "origin_exact": (
            origin.get("memory_expression_run_id") == ORIGIN_RUN_ID
            and origin.get("memory_expression_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("memory_expression_artifact_sha256") == ORIGIN_ARTIFACT
            and origin.get("memory_expression_freeze") == ORIGIN_FREEZE
        ),
        "clock_exact": (
            clock.get("kc_trace_seconds") == KC_TRACE_SECONDS
            and clock.get("neural_ms_per_decision") == NEURAL_MS_PER_DECISION
            and clock.get("trace_window_decisions") == TRACE_WINDOW_DECISIONS
            and TRACE_WINDOW_DECISIONS
            == round(KC_TRACE_SECONDS * 1000 / NEURAL_MS_PER_DECISION)
            and clock.get("trace_window_interpretation")
            == "one frozen KC-trace time constant; not a hard biological cutoff"
        ),
        "runtime_exact": (
            runtime.get("event_selection")
            == "first natural reward at or after decision index 20"
            and runtime.get("maximum_acquisition_decisions")
            == MAX_ACQUISITION_DECISIONS
            and runtime.get("post_reward_delay_decisions")
            == POST_REWARD_DELAY_DECISIONS
            and runtime.get("history_and_delay_external_reinforcement") == "none"
            and runtime.get("state_clear_before_sequence_recall") is True
            and runtime.get("sequence_recall_plasticity_frozen") is True
            and runtime.get("sequence_recall_external_reinforcement") == "none"
            and runtime.get("sequence")
            == (
                "exact 20 recorded decisions preceding reward followed by exact "
                "reward-event cue"
            )
            and runtime.get("changed_edge_tolerance_fraction") == CHANGED_TOLERANCE
            and runtime.get("state_difference_tolerance") == STATE_TOLERANCE
            and runtime.get("no_model_parameter_change") is True
        ),
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": (
            len(seeds) == len(set(seeds))
            and not (set(seeds) & PRIOR_SEEDS)
        ),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ())
        == (
            "changed_reward_edge_count",
            "changed_edge_pre_event_trace_positive_fraction",
            "changed_edge_pre_event_mean_kc_trace_hz",
            "per_lag_changed_presynaptic_kc_active_fraction",
            "per_lag_changed_reward_l1_engaged_fraction",
            "first_lag_with_changed_kc_activity",
            "first_lag_with_mbon07_state_difference",
            "sequence_any_mbon07_spike_difference",
            "reward_cue_action_divergence",
        ),
        "interpretation_locked": (
            interpretation.get("no_parameter_tuning") is True
            and interpretation.get("no_posthoc_event_selection") is True
            and interpretation.get("no_posthoc_lag_selection") is True
            and interpretation.get("all_lags_minus20_through_zero_reported") is True
            and interpretation.get("no_directional_pass_threshold") is True
            and interpretation.get(
                "result_is_temporal_mechanism_localization_only"
            )
            is True
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims) == CLAIM_KEYS
            and all(value is False for value in claims.values())
        ),
    }


def _record_trace_window_trajectory(
    *,
    base_checkpoint: Path,
    driver_checkpoint: Path,
    trajectory_seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    shutil.copy2(base_checkpoint, driver_checkpoint)
    driver = MaleCNSBrain(checkpoint=driver_checkpoint, learning=False)
    driver.brain.weights_frozen = True
    initial_memory = _memory_snapshot(driver)
    recorder = FixedTrajectoryRecorder(driver)
    session = GoalMazeSession(
        recorder,
        environment=GoalMazeEnvironment(seed=trajectory_seed),
        checkpoint=None,
        world_tick_seconds=3600.0,
        decision_synchronous_world=True,
    )

    states: list[dict[str, Any]] = []
    reward_index: int | None = None
    for decision_index in range(MAX_ACQUISITION_DECISIONS):
        state = session.tick()
        if not _neural_decision_verified(state):
            raise RuntimeError("Trajectory driver lacks verifiable neural activity")
        states.append(
            {
                "action": str(state.get("decision_action") or "UNKNOWN"),
                "task_reward": float(state.get("last_reward") or 0.0),
            }
        )
        row = recorder.rows[-1]
        if (
            reward_index is None
            and decision_index >= TRACE_WINDOW_DECISIONS
            and row["true_reinforcement"] == "reward"
        ):
            reward_index = decision_index

        if (
            reward_index is not None
            and decision_index
            >= reward_index + POST_REWARD_DELAY_DECISIONS
        ):
            break

    if reward_index is None:
        raise RuntimeError(
            "No qualifying natural reward after the frozen trace-window warmup"
        )
    expected = reward_index + POST_REWARD_DELAY_DECISIONS + 1
    if len(recorder.rows) != expected:
        raise RuntimeError("Trace-window acquisition stop boundary mismatch")

    final_memory = _memory_snapshot(driver)
    receipt_rows = _trajectory_receipt_rows(recorder.rows)
    reinforcements = Counter(row["true_reinforcement"] for row in recorder.rows)
    report = {
        "decisions": len(recorder.rows),
        "maximum_acquisition_decisions": MAX_ACQUISITION_DECISIONS,
        "reward_event_index": reward_index,
        "trace_window_decisions": TRACE_WINDOW_DECISIONS,
        "post_reward_delay_decisions": POST_REWARD_DELAY_DECISIONS,
        "trajectory_digest": _digest_json(receipt_rows),
        "trajectory_receipt_rows": receipt_rows,
        "true_reinforcement_counts": dict(sorted(reinforcements.items())),
        "driver_delivered_reinforcement": dict(
            sorted(recorder.delivered_to_driver.items())
        ),
        "driver_initial_memory": initial_memory,
        "driver_final_memory": final_memory,
        "driver_frozen_memory_unchanged": (
            initial_memory["sha256"] == final_memory["sha256"]
        ),
        "driver_state_digest": _digest_json(states),
    }
    return recorder.rows, report, reward_index


def _prepare_memory_branch(
    *,
    pre_event_checkpoint: Path,
    event: dict[str, Any],
    delay_rows: list[dict[str, Any]],
    reinforcement: str,
) -> tuple[MaleCNSBrain, dict[str, Any]]:
    inner = _restore_recentered(pre_event_checkpoint)

    event_decision = inner.decide(
        event["frame"],
        reinforcement,
        context=copy.deepcopy(event["context"]),
    )
    if reinforcement == "none":
        expected_event_stimulus = 0.0
    else:
        expected_event_stimulus = 20.0
    if float(event_decision.telemetry.get("stimulus_ms") or 0.0) != expected_event_stimulus:
        raise RuntimeError("Event stimulus did not match frozen paired condition")

    for row in delay_rows:
        decision = inner.decide(
            row["frame"],
            "none",
            context=copy.deepcopy(row["context"]),
        )
        if float(decision.telemetry.get("stimulus_ms") or 0.0) != 0.0:
            raise RuntimeError("Delay replay delivered external reinforcement")

    post_delay = _plastic_edge_state(inner)
    return inner, {
        "post_delay_fraction": inner.np.asarray(
            post_delay["fraction"], dtype=inner.np.float64
        ).copy(),
        "fraction_digest": post_delay["fraction_digest"],
        "event_stimulus_ms": float(
            event_decision.telemetry.get("stimulus_ms") or 0.0
        ),
    }


def _population_step(inner: MaleCNSBrain) -> dict[str, Any]:
    import numpy as np

    b = inner.brain
    c = b.circuit
    reward_count = len(c["reward"])
    reward_edge_mask = np.any(
        np.abs(c["gain"][:reward_count]) > 0.0,
        axis=0,
    )
    reward_edges = np.asarray(c["edges"])[reward_edge_mask]
    reward_mbon = np.unique(np.asarray(b.post)[reward_edges]).astype(np.int64)

    return {
        "counts": np.asarray(b.counts, dtype=np.int64).copy(),
        "mbon07": _population_state(inner, reward_mbon),
        "left_decoder": _population_state(inner, inner.left),
        "right_decoder": _population_state(inner, inner.right),
        "gate_decoder": _population_state(inner, inner.gate),
    }


def _state_difference(none: dict[str, Any], true: dict[str, Any]) -> dict[str, Any]:
    nm = none["mbon07"]
    tm = true["mbon07"]
    mbon_spike_delta = _sum_delta(tm["counts"], nm["counts"])
    mbon_v_delta = _max_abs_delta(tm["v"], nm["v"])
    mbon_g_delta = _max_abs_delta(tm["g"], nm["g"])
    dnp_v_delta = max(
        _max_abs_delta(
            true["left_decoder"]["v"],
            none["left_decoder"]["v"],
        ),
        _max_abs_delta(
            true["right_decoder"]["v"],
            none["right_decoder"]["v"],
        ),
    )
    gate_v_delta = _max_abs_delta(
        true["gate_decoder"]["v"],
        none["gate_decoder"]["v"],
    )
    any_mbon_state_difference = (
        mbon_spike_delta != 0
        or mbon_v_delta > STATE_TOLERANCE
        or mbon_g_delta > STATE_TOLERANCE
    )
    return {
        "mbon07_total_spike_delta": mbon_spike_delta,
        "mbon07_max_abs_membrane_delta": mbon_v_delta,
        "mbon07_max_abs_conductance_delta": mbon_g_delta,
        "dnp20_max_abs_membrane_delta": dnp_v_delta,
        "dnpe017_max_abs_membrane_delta": gate_v_delta,
        "any_mbon07_state_difference": any_mbon_state_difference,
    }


def _run_replicate(
    *,
    replicate_id: str,
    trajectory_seed: int,
    base_checkpoint: Path,
    rep_dir: Path,
) -> dict[str, Any]:
    import numpy as np

    rep_dir.mkdir(parents=True, exist_ok=True)
    trajectory, driver, event_index = _record_trace_window_trajectory(
        base_checkpoint=base_checkpoint,
        driver_checkpoint=rep_dir / "trajectory-driver.npz",
        trajectory_seed=trajectory_seed,
    )
    event = trajectory[event_index]
    if event["true_reinforcement"] != "reward":
        raise RuntimeError("Selected trace-window event is not reward")
    if event_index < TRACE_WINDOW_DECISIONS:
        raise RuntimeError("Selected event lacks frozen trace history")

    sequence_rows = trajectory[
        event_index - TRACE_WINDOW_DECISIONS : event_index + 1
    ]
    delay_rows = trajectory[
        event_index + 1 : event_index + 1 + POST_REWARD_DELAY_DECISIONS
    ]
    if len(sequence_rows) != TRACE_WINDOW_DECISIONS + 1:
        raise RuntimeError("Incomplete temporal-index sequence")
    if len(delay_rows) != POST_REWARD_DELAY_DECISIONS:
        raise RuntimeError("Incomplete post-reward delay")

    pre_event_checkpoint = rep_dir / "pre-event.npz"
    pre_report = _build_pre_event_checkpoint(
        trajectory=trajectory,
        event_index=event_index,
        base_checkpoint=base_checkpoint,
        pre_event_checkpoint=pre_event_checkpoint,
    )
    pre_sha = pre_report["pre_event_checkpoint_sha256"]

    none_inner, none = _prepare_memory_branch(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        delay_rows=delay_rows,
        reinforcement="none",
    )
    true_inner, true = _prepare_memory_branch(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        delay_rows=delay_rows,
        reinforcement="reward",
    )
    if _sha256_file(pre_event_checkpoint) != pre_sha:
        raise RuntimeError("Pre-event checkpoint mutated")

    pre_inner = _restore_recentered(pre_event_checkpoint)
    c = pre_inner.brain.circuit
    reward_count = len(c["reward"])
    reward_mask = np.any(np.abs(c["gain"][:reward_count]) > 0.0, axis=0)
    reward_pre = np.asarray(c["pre"], dtype=np.int64)[reward_mask]

    paired_delta = (
        np.asarray(true["post_delay_fraction"])[reward_mask]
        - np.asarray(none["post_delay_fraction"])[reward_mask]
    )
    changed = np.abs(paired_delta) > CHANGED_TOLERANCE
    if not np.any(changed):
        raise RuntimeError("No changed reward edges for temporal-index audit")

    changed_pre = reward_pre[changed]
    unique_changed_pre = np.unique(changed_pre)
    changed_l1 = float(np.abs(paired_delta[changed]).sum())

    pre_trace = np.asarray(pre_inner.brain.rate_kc, dtype=np.float64)[reward_mask]
    changed_pre_trace = pre_trace[changed]
    pre_trace_positive = changed_pre_trace > CHANGED_TOLERANCE

    for inner in (none_inner, true_inner):
        before_reset = _plastic_edge_state(inner)["fraction_digest"]
        inner.brain.reset(keep_memory=True)
        inner._last_visual_rgb = None
        after_reset = _plastic_edge_state(inner)["fraction_digest"]
        if before_reset != after_reset:
            raise RuntimeError("State clearing did not preserve branch memory")
        inner.learning = False
        inner.brain.weights_frozen = True

    none_recall_memory_before = _plastic_edge_state(none_inner)["fraction_digest"]
    true_recall_memory_before = _plastic_edge_state(true_inner)["fraction_digest"]

    lags: list[dict[str, Any]] = []
    for sequence_offset, row in enumerate(sequence_rows):
        lag = sequence_offset - TRACE_WINDOW_DECISIONS

        none_decision = none_inner.decide(
            row["frame"],
            "none",
            context=copy.deepcopy(row["context"]),
        )
        true_decision = true_inner.decide(
            row["frame"],
            "none",
            context=copy.deepcopy(row["context"]),
        )
        if (
            float(none_decision.telemetry.get("stimulus_ms") or 0.0) != 0.0
            or float(true_decision.telemetry.get("stimulus_ms") or 0.0) != 0.0
        ):
            raise RuntimeError("Sequence recall delivered external reinforcement")

        none_state = _population_step(none_inner)
        true_state = _population_step(true_inner)

        none_counts = none_state["counts"]
        true_counts = true_state["counts"]
        active_changed_kc = (
            (none_counts[unique_changed_pre] > 0)
            | (true_counts[unique_changed_pre] > 0)
        )
        active_changed_edges = changed & (
            (none_counts[reward_pre] > 0)
            | (true_counts[reward_pre] > 0)
        )
        active_l1 = float(np.abs(paired_delta[active_changed_edges]).sum())
        expression = _state_difference(none_state, true_state)

        lags.append(
            {
                "lag": lag,
                "frame_sha256": hashlib.sha256(row["frame"].tobytes()).hexdigest(),
                "context_sha256": _digest_json(row["context"]),
                "changed_presynaptic_kc_active_count": int(
                    active_changed_kc.sum()
                ),
                "changed_presynaptic_kc_active_fraction": round(
                    float(active_changed_kc.sum())
                    / float(len(unique_changed_pre)),
                    12,
                ),
                "changed_reward_edge_active_count": int(
                    active_changed_edges.sum()
                ),
                "changed_reward_l1_engaged": round(active_l1, 15),
                "changed_reward_l1_engaged_fraction": round(
                    active_l1 / changed_l1,
                    12,
                )
                if changed_l1
                else 0.0,
                "none_action": none_decision.action,
                "true_action": true_decision.action,
                "action_diverged": none_decision.action != true_decision.action,
                **expression,
            }
        )

    none_recall_memory_after = _plastic_edge_state(none_inner)["fraction_digest"]
    true_recall_memory_after = _plastic_edge_state(true_inner)["fraction_digest"]
    if (
        none_recall_memory_before != none_recall_memory_after
        or true_recall_memory_before != true_recall_memory_after
    ):
        raise RuntimeError("Frozen sequence recall mutated memory")

    first_active = next(
        (
            row["lag"]
            for row in lags
            if row["changed_presynaptic_kc_active_count"] > 0
        ),
        None,
    )
    first_mbon = next(
        (
            row["lag"]
            for row in lags
            if row["any_mbon07_state_difference"]
        ),
        None,
    )
    reward_cue = lags[-1]
    if reward_cue["lag"] != 0:
        raise RuntimeError("Final sequence row is not reward cue")

    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "acquisition_decisions": len(trajectory),
        "event_index": event_index,
        "trajectory_digest": driver["trajectory_digest"],
        "driver_frozen_memory_unchanged": driver["driver_frozen_memory_unchanged"],
        "pre_event_checkpoint_sha256": pre_sha,
        "changed_reward_edge_count": int(changed.sum()),
        "unique_changed_presynaptic_kc_count": int(len(unique_changed_pre)),
        "changed_reward_l1": round(changed_l1, 15),
        "changed_edge_pre_event_trace_positive_count": int(
            pre_trace_positive.sum()
        ),
        "changed_edge_pre_event_trace_positive_fraction": round(
            float(pre_trace_positive.sum()) / float(changed.sum()),
            12,
        ),
        "changed_edge_pre_event_mean_kc_trace_hz": round(
            float(changed_pre_trace.mean()),
            12,
        ),
        "changed_edge_pre_event_max_kc_trace_hz": round(
            float(changed_pre_trace.max()),
            12,
        ),
        "first_lag_with_changed_kc_activity": first_active,
        "first_lag_with_mbon07_state_difference": first_mbon,
        "sequence_any_mbon07_spike_difference": any(
            row["mbon07_total_spike_delta"] != 0 for row in lags
        ),
        "sequence_any_action_divergence": any(
            row["action_diverged"] for row in lags
        ),
        "reward_cue_action_divergence": reward_cue["action_diverged"],
        "reward_cue_changed_kc_active_fraction": reward_cue[
            "changed_presynaptic_kc_active_fraction"
        ],
        "reward_cue_changed_l1_engaged_fraction": reward_cue[
            "changed_reward_l1_engaged_fraction"
        ],
        "lags": lags,
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    lag_values = list(range(-TRACE_WINDOW_DECISIONS, 1))
    per_lag: list[dict[str, Any]] = []
    for lag in lag_values:
        rows = [
            next(item for item in rep["lags"] if item["lag"] == lag)
            for rep in replicates
        ]
        per_lag.append(
            {
                "lag": lag,
                "mean_changed_presynaptic_kc_active_fraction": round(
                    mean(
                        row["changed_presynaptic_kc_active_fraction"]
                        for row in rows
                    ),
                    12,
                ),
                "mean_changed_reward_l1_engaged_fraction": round(
                    mean(
                        row["changed_reward_l1_engaged_fraction"]
                        for row in rows
                    ),
                    12,
                ),
                "mean_mbon07_max_abs_membrane_delta": round(
                    mean(
                        row["mbon07_max_abs_membrane_delta"]
                        for row in rows
                    ),
                    12,
                ),
                "mean_mbon07_max_abs_conductance_delta": round(
                    mean(
                        row["mbon07_max_abs_conductance_delta"]
                        for row in rows
                    ),
                    12,
                ),
                "mbon07_spike_difference_fraction": round(
                    sum(row["mbon07_total_spike_delta"] != 0 for row in rows)
                    / len(rows),
                    12,
                ),
                "action_divergence_fraction": round(
                    sum(row["action_diverged"] for row in rows) / len(rows),
                    12,
                ),
            }
        )

    return {
        "replicate_count": len(replicates),
        "mean_changed_reward_edge_count": round(
            mean(row["changed_reward_edge_count"] for row in replicates), 8
        ),
        "mean_changed_edge_pre_event_trace_positive_fraction": round(
            mean(
                row["changed_edge_pre_event_trace_positive_fraction"]
                for row in replicates
            ),
            12,
        ),
        "mean_changed_edge_pre_event_mean_kc_trace_hz": round(
            mean(
                row["changed_edge_pre_event_mean_kc_trace_hz"]
                for row in replicates
            ),
            12,
        ),
        "replicates_with_any_changed_kc_sequence_activity": sum(
            row["first_lag_with_changed_kc_activity"] is not None
            for row in replicates
        ),
        "replicates_with_any_mbon07_state_difference": sum(
            row["first_lag_with_mbon07_state_difference"] is not None
            for row in replicates
        ),
        "replicates_with_any_mbon07_spike_difference": sum(
            row["sequence_any_mbon07_spike_difference"] for row in replicates
        ),
        "replicates_with_any_action_divergence": sum(
            row["sequence_any_action_divergence"] for row in replicates
        ),
        "reward_cue_action_divergence_fraction": round(
            sum(row["reward_cue_action_divergence"] for row in replicates)
            / len(replicates),
            12,
        ),
        "per_lag": per_lag,
    }


def run_memory_temporal_index_audit(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Temporal-index config failed validation")
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
            row["driver_frozen_memory_unchanged"] is True
            for row in replicates
        ),
        "all_events_have_full_trace_history": all(
            row["event_index"] >= TRACE_WINDOW_DECISIONS
            for row in replicates
        ),
        "all_acquisitions_within_max": all(
            1 <= row["acquisition_decisions"] <= MAX_ACQUISITION_DECISIONS
            for row in replicates
        ),
        "all_have_changed_reward_edges": all(
            row["changed_reward_edge_count"] > 0 for row in replicates
        ),
        "all_report_complete_lag_grid": all(
            [item["lag"] for item in row["lags"]]
            == list(range(-TRACE_WINDOW_DECISIONS, 1))
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
            "EXPLORATORY_TEMPORAL_INDEX_AUDIT_COMPLETE"
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
        "temporal_cue_index_confirmed": False,
        "cue_indexing_failure_confirmed": False,
        "memory_expression_causal": False,
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
        description="Audit the temporal cue index for persistent reward memory"
    )
    parser.add_argument(
        "--config",
        default="data/memory_temporal_index_audit_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_memory_temporal_index_audit(
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
