from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
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
from .memory_temporal_index_audit import _prepare_memory_branch
from .smoke import _digest_json, _neural_decision_verified


CONFIG_SCHEMA = "neurofly-memory-trace-reconstruction-audit-v0.1"
RECEIPT_SCHEMA = "neurofly-memory-trace-reconstruction-audit-receipt-v0.1"
STATUS = "PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE = "real-malecns-reward-memory-trace-reconstruction"

KC_TRACE_SECONDS = 1.0
NEURAL_MS_PER_DECISION = 50
ONE_TAU_DECISIONS = 20
THREE_TAU_DECISIONS = 60
MAX_ACQUISITION_DECISIONS = 300
POST_REWARD_DELAY_DECISIONS = 5
CHANGED_TOLERANCE = 1e-12
TRACE_ZERO_TOLERANCE = 1e-12
THREE_TAU_RESIDUAL = round(math.exp(-3.0), 12)

EXPECTED_REPLICATES = (
    ("TR1", 3001),
    ("TR2", 3011),
    ("TR3", 3019),
    ("TR4", 3023),
)
PRIOR_SEEDS = {
    2309, 2311, 2333, 2339,
    2609, 2617, 2621, 2633,
    2711, 2713, 2719, 2729,
    2801, 2803, 2819, 2833,
    2903, 2909, 2917, 2927,
}
ORIGIN_RUN_ID = 36095883843
ORIGIN_RECEIPT = "573c10a5f52a03fa7a04226979c14594b59eb56da763a150057ff2137289ed72"
ORIGIN_ARTIFACT = "947633623b5a8f6071833abf7f04283e6a0f3a7c147183f79a199ce9b90c16ba"
ORIGIN_FREEZE = "data/memory_temporal_index_audit_run1_freeze_v01.json"

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
            "How much of the original reward-time KC eligibility vector is "
            "reconstructed after transient-state clearing by replaying one versus "
            "three frozen KC-trace time constants of prereward sensory history?"
        ),
        "origin_exact": (
            origin.get("temporal_index_run_id") == ORIGIN_RUN_ID
            and origin.get("temporal_index_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("temporal_index_artifact_sha256") == ORIGIN_ARTIFACT
            and origin.get("temporal_index_freeze") == ORIGIN_FREEZE
        ),
        "clock_exact": (
            clock.get("kc_trace_seconds") == KC_TRACE_SECONDS
            and clock.get("neural_ms_per_decision") == NEURAL_MS_PER_DECISION
            and clock.get("one_tau_decisions") == ONE_TAU_DECISIONS
            and clock.get("three_tau_decisions") == THREE_TAU_DECISIONS
            and ONE_TAU_DECISIONS
            == round(KC_TRACE_SECONDS * 1000 / NEURAL_MS_PER_DECISION)
            and THREE_TAU_DECISIONS == 3 * ONE_TAU_DECISIONS
            and clock.get("three_tau_older_history_residual_fraction")
            == THREE_TAU_RESIDUAL
        ),
        "runtime_exact": (
            runtime.get("event_selection")
            == "first natural reward at or after decision index 60"
            and runtime.get("maximum_acquisition_decisions")
            == MAX_ACQUISITION_DECISIONS
            and runtime.get("post_reward_delay_decisions")
            == POST_REWARD_DELAY_DECISIONS
            and runtime.get("history_and_delay_external_reinforcement") == "none"
            and runtime.get("state_clear_before_trace_replay") is True
            and runtime.get("trace_replay_plasticity_frozen") is True
            and runtime.get("trace_replay_external_reinforcement") == "none"
            and runtime.get("one_tau_sequence")
            == "exact 20 recorded prereward decisions ending immediately before reward"
            and runtime.get("three_tau_sequence")
            == "exact 60 recorded prereward decisions ending immediately before reward"
            and runtime.get("target_vector")
            == "original pre-event reward-edge rate_kc vector immediately before reward"
            and runtime.get("changed_edge_tolerance_fraction") == CHANGED_TOLERANCE
            and runtime.get("trace_zero_tolerance") == TRACE_ZERO_TOLERANCE
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
            "target_changed_edge_trace_positive_fraction",
            "one_tau_final_changed_trace_cosine_similarity",
            "three_tau_final_changed_trace_cosine_similarity",
            "one_tau_final_changed_trace_l1_overlap_fraction",
            "three_tau_final_changed_trace_l1_overlap_fraction",
            "three_tau_minus_one_tau_l1_overlap_delta",
            "one_tau_final_target_positive_edge_recovery_fraction",
            "three_tau_final_target_positive_edge_recovery_fraction",
            "per_lag_three_tau_changed_trace_metrics",
        ),
        "interpretation_locked": (
            interpretation.get("no_parameter_tuning") is True
            and interpretation.get("no_posthoc_event_selection") is True
            and interpretation.get("no_posthoc_window_selection") is True
            and interpretation.get("one_tau_and_three_tau_compared_on_same_trajectory")
            is True
            and interpretation.get("all_replayed_lags_reported") is True
            and interpretation.get("no_directional_pass_threshold") is True
            and interpretation.get(
                "result_is_eligibility_reconstruction_localization_only"
            )
            is True
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims) == CLAIM_KEYS
            and all(value is False for value in claims.values())
        ),
    }


def _record_three_tau_trajectory(
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
            and decision_index >= THREE_TAU_DECISIONS
            and row["true_reinforcement"] == "reward"
        ):
            reward_index = decision_index

        if (
            reward_index is not None
            and decision_index >= reward_index + POST_REWARD_DELAY_DECISIONS
        ):
            break

    if reward_index is None:
        raise RuntimeError(
            "No qualifying natural reward after the frozen three-tau warmup"
        )
    expected = reward_index + POST_REWARD_DELAY_DECISIONS + 1
    if len(recorder.rows) != expected:
        raise RuntimeError("Three-tau acquisition stop boundary mismatch")

    final_memory = _memory_snapshot(driver)
    receipt_rows = _trajectory_receipt_rows(recorder.rows)
    reinforcements = Counter(row["true_reinforcement"] for row in recorder.rows)
    report = {
        "decisions": len(recorder.rows),
        "maximum_acquisition_decisions": MAX_ACQUISITION_DECISIONS,
        "reward_event_index": reward_index,
        "one_tau_decisions": ONE_TAU_DECISIONS,
        "three_tau_decisions": THREE_TAU_DECISIONS,
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


def _vector_digest(values: Any) -> str:
    import numpy as np

    vector = np.asarray(values, dtype=np.float64)
    return hashlib.sha256(vector.tobytes()).hexdigest()


def _trace_metrics(
    target: Any,
    replay: Any,
    *,
    zero_tolerance: float = TRACE_ZERO_TOLERANCE,
) -> dict[str, Any]:
    import numpy as np

    target_vector = np.asarray(target, dtype=np.float64)
    replay_vector = np.asarray(replay, dtype=np.float64)
    if target_vector.shape != replay_vector.shape:
        raise ValueError("Trace vector shape mismatch")

    target_abs = np.abs(target_vector)
    replay_abs = np.abs(replay_vector)
    target_l1 = float(target_abs.sum())
    replay_l1 = float(replay_abs.sum())
    target_norm = float(np.linalg.norm(target_vector))
    replay_norm = float(np.linalg.norm(replay_vector))

    if target_norm > zero_tolerance and replay_norm > zero_tolerance:
        cosine = float(
            np.dot(target_vector, replay_vector) / (target_norm * replay_norm)
        )
    else:
        cosine = 0.0

    if target_l1 > zero_tolerance:
        overlap = float(np.minimum(target_abs, replay_abs).sum() / target_l1)
        normalized_l1_error = float(
            np.abs(replay_vector - target_vector).sum() / target_l1
        )
        replay_target_l1_ratio = replay_l1 / target_l1
    else:
        overlap = 0.0
        normalized_l1_error = 0.0 if replay_l1 <= zero_tolerance else math.inf
        replay_target_l1_ratio = 0.0 if replay_l1 <= zero_tolerance else math.inf

    target_positive = target_abs > zero_tolerance
    target_positive_count = int(target_positive.sum())
    recovered = target_positive & (replay_abs > zero_tolerance)
    positive_recovery = (
        float(recovered.sum()) / float(target_positive_count)
        if target_positive_count
        else 0.0
    )

    return {
        "edge_count": int(target_vector.size),
        "target_l1": round(target_l1, 12),
        "replay_l1": round(replay_l1, 12),
        "cosine_similarity": round(cosine, 12),
        "l1_overlap_fraction": round(overlap, 12),
        "normalized_l1_error": round(normalized_l1_error, 12)
        if math.isfinite(normalized_l1_error)
        else "inf",
        "replay_target_l1_ratio": round(replay_target_l1_ratio, 12)
        if math.isfinite(replay_target_l1_ratio)
        else "inf",
        "target_positive_edge_count": target_positive_count,
        "target_positive_edge_recovery_count": int(recovered.sum()),
        "target_positive_edge_recovery_fraction": round(positive_recovery, 12),
    }


def _prepare_trace_replay(
    *,
    pre_event_checkpoint: Path,
    reward_mask: Any,
) -> tuple[MaleCNSBrain, dict[str, Any]]:
    import numpy as np

    inner = _restore_recentered(pre_event_checkpoint)
    memory_before_reset = _plastic_edge_state(inner)["fraction_digest"]
    inner.brain.reset(keep_memory=True)
    inner._last_visual_rgb = None
    memory_after_reset = _plastic_edge_state(inner)["fraction_digest"]
    if memory_before_reset != memory_after_reset:
        raise RuntimeError("Trace-replay state clear did not preserve synaptic memory")

    inner.learning = False
    inner.brain.weights_frozen = True
    reward_trace = np.asarray(inner.brain.rate_kc, dtype=np.float64)[reward_mask]
    reset_trace_l1 = float(np.abs(reward_trace).sum())
    if reset_trace_l1 > TRACE_ZERO_TOLERANCE:
        raise RuntimeError("State clear did not clear reward-edge KC eligibility trace")

    return inner, {
        "memory_fraction_digest": memory_after_reset,
        "reset_reward_trace_l1": round(reset_trace_l1, 15),
    }


def _replay_window(
    *,
    pre_event_checkpoint: Path,
    sequence_rows: list[dict[str, Any]],
    start_lag: int,
    reward_mask: Any,
    changed_mask: Any,
    target_reward_trace: Any,
) -> dict[str, Any]:
    import numpy as np

    inner, reset = _prepare_trace_replay(
        pre_event_checkpoint=pre_event_checkpoint,
        reward_mask=reward_mask,
    )
    memory_before = _plastic_edge_state(inner)["fraction_digest"]
    target_reward = np.asarray(target_reward_trace, dtype=np.float64)
    target_changed = target_reward[changed_mask]

    lag_rows: list[dict[str, Any]] = []
    for offset, row in enumerate(sequence_rows):
        lag = start_lag + offset
        decision = inner.decide(
            row["frame"],
            "none",
            context=copy.deepcopy(row["context"]),
        )
        if float(decision.telemetry.get("stimulus_ms") or 0.0) != 0.0:
            raise RuntimeError("Trace replay delivered external reinforcement")

        replay_reward = np.asarray(inner.brain.rate_kc, dtype=np.float64)[reward_mask]
        replay_changed = replay_reward[changed_mask]
        lag_rows.append(
            {
                "lag": lag,
                "frame_sha256": hashlib.sha256(row["frame"].tobytes()).hexdigest(),
                "context_sha256": _digest_json(row["context"]),
                "changed_trace": _trace_metrics(target_changed, replay_changed),
                "reward_edge_trace": _trace_metrics(target_reward, replay_reward),
            }
        )

    memory_after = _plastic_edge_state(inner)["fraction_digest"]
    if memory_before != memory_after:
        raise RuntimeError("Frozen trace replay mutated synaptic memory")

    expected_lags = list(range(start_lag, 0))
    if [row["lag"] for row in lag_rows] != expected_lags:
        raise RuntimeError("Trace replay lag grid mismatch")

    return {
        "start_lag": start_lag,
        "decision_count": len(sequence_rows),
        "reset_reward_trace_l1": reset["reset_reward_trace_l1"],
        "memory_unchanged": True,
        "lags": lag_rows,
        "final_changed_trace": lag_rows[-1]["changed_trace"],
        "final_reward_edge_trace": lag_rows[-1]["reward_edge_trace"],
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
    trajectory, driver, event_index = _record_three_tau_trajectory(
        base_checkpoint=base_checkpoint,
        driver_checkpoint=rep_dir / "trajectory-driver.npz",
        trajectory_seed=trajectory_seed,
    )
    event = trajectory[event_index]
    if event["true_reinforcement"] != "reward":
        raise RuntimeError("Selected trace-reconstruction event is not reward")
    if event_index < THREE_TAU_DECISIONS:
        raise RuntimeError("Selected event lacks complete three-tau history")

    three_tau_rows = trajectory[
        event_index - THREE_TAU_DECISIONS : event_index
    ]
    one_tau_rows = trajectory[
        event_index - ONE_TAU_DECISIONS : event_index
    ]
    delay_rows = trajectory[
        event_index + 1 : event_index + 1 + POST_REWARD_DELAY_DECISIONS
    ]
    if len(three_tau_rows) != THREE_TAU_DECISIONS:
        raise RuntimeError("Incomplete three-tau prereward sequence")
    if len(one_tau_rows) != ONE_TAU_DECISIONS:
        raise RuntimeError("Incomplete one-tau prereward sequence")
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
    circuit = pre_inner.brain.circuit
    reward_count = len(circuit["reward"])
    reward_mask = np.any(
        np.abs(circuit["gain"][:reward_count]) > 0.0,
        axis=0,
    )

    paired_delta = (
        np.asarray(true["post_delay_fraction"])[reward_mask]
        - np.asarray(none["post_delay_fraction"])[reward_mask]
    )
    changed = np.abs(paired_delta) > CHANGED_TOLERANCE
    if not np.any(changed):
        raise RuntimeError("No changed reward edges for trace reconstruction")

    target_reward_trace = np.asarray(
        pre_inner.brain.rate_kc, dtype=np.float64
    )[reward_mask].copy()
    target_changed_trace = target_reward_trace[changed]
    target_positive = np.abs(target_changed_trace) > TRACE_ZERO_TOLERANCE

    one_tau = _replay_window(
        pre_event_checkpoint=pre_event_checkpoint,
        sequence_rows=one_tau_rows,
        start_lag=-ONE_TAU_DECISIONS,
        reward_mask=reward_mask,
        changed_mask=changed,
        target_reward_trace=target_reward_trace,
    )
    three_tau = _replay_window(
        pre_event_checkpoint=pre_event_checkpoint,
        sequence_rows=three_tau_rows,
        start_lag=-THREE_TAU_DECISIONS,
        reward_mask=reward_mask,
        changed_mask=changed,
        target_reward_trace=target_reward_trace,
    )

    one_final = one_tau["final_changed_trace"]
    three_final = three_tau["final_changed_trace"]
    overlap_delta = (
        float(three_final["l1_overlap_fraction"])
        - float(one_final["l1_overlap_fraction"])
    )
    cosine_delta = (
        float(three_final["cosine_similarity"])
        - float(one_final["cosine_similarity"])
    )
    one_error = one_final["normalized_l1_error"]
    three_error = three_final["normalized_l1_error"]
    error_reduction = (
        float(one_error) - float(three_error)
        if isinstance(one_error, (int, float))
        and isinstance(three_error, (int, float))
        else None
    )

    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "acquisition_decisions": len(trajectory),
        "event_index": event_index,
        "trajectory_digest": driver["trajectory_digest"],
        "driver_frozen_memory_unchanged": driver["driver_frozen_memory_unchanged"],
        "pre_event_checkpoint_sha256": pre_sha,
        "changed_reward_edge_count": int(changed.sum()),
        "target_reward_edge_trace_sha256": _vector_digest(target_reward_trace),
        "target_changed_edge_trace_sha256": _vector_digest(target_changed_trace),
        "target_changed_edge_trace_positive_count": int(target_positive.sum()),
        "target_changed_edge_trace_positive_fraction": round(
            float(target_positive.sum()) / float(changed.sum()),
            12,
        ),
        "target_changed_edge_trace_l1": round(
            float(np.abs(target_changed_trace).sum()),
            12,
        ),
        "one_tau": one_tau,
        "three_tau": three_tau,
        "three_tau_minus_one_tau_l1_overlap_delta": round(overlap_delta, 12),
        "three_tau_minus_one_tau_cosine_delta": round(cosine_delta, 12),
        "three_tau_minus_one_tau_normalized_l1_error_reduction": (
            round(error_reduction, 12) if error_reduction is not None else None
        ),
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    three_tau_per_lag: list[dict[str, Any]] = []
    for lag in range(-THREE_TAU_DECISIONS, 0):
        metrics = [
            next(row for row in rep["three_tau"]["lags"] if row["lag"] == lag)[
                "changed_trace"
            ]
            for rep in replicates
        ]
        three_tau_per_lag.append(
            {
                "lag": lag,
                "mean_cosine_similarity": round(
                    mean(float(row["cosine_similarity"]) for row in metrics),
                    12,
                ),
                "mean_l1_overlap_fraction": round(
                    mean(float(row["l1_overlap_fraction"]) for row in metrics),
                    12,
                ),
                "mean_normalized_l1_error": round(
                    mean(float(row["normalized_l1_error"]) for row in metrics),
                    12,
                ),
                "mean_target_positive_edge_recovery_fraction": round(
                    mean(
                        float(row["target_positive_edge_recovery_fraction"])
                        for row in metrics
                    ),
                    12,
                ),
            }
        )

    return {
        "replicate_count": len(replicates),
        "mean_changed_reward_edge_count": round(
            mean(row["changed_reward_edge_count"] for row in replicates),
            8,
        ),
        "mean_target_changed_edge_trace_positive_fraction": round(
            mean(
                row["target_changed_edge_trace_positive_fraction"]
                for row in replicates
            ),
            12,
        ),
        "mean_one_tau_final_changed_trace_cosine_similarity": round(
            mean(
                float(row["one_tau"]["final_changed_trace"]["cosine_similarity"])
                for row in replicates
            ),
            12,
        ),
        "mean_three_tau_final_changed_trace_cosine_similarity": round(
            mean(
                float(row["three_tau"]["final_changed_trace"]["cosine_similarity"])
                for row in replicates
            ),
            12,
        ),
        "mean_one_tau_final_changed_trace_l1_overlap_fraction": round(
            mean(
                float(row["one_tau"]["final_changed_trace"]["l1_overlap_fraction"])
                for row in replicates
            ),
            12,
        ),
        "mean_three_tau_final_changed_trace_l1_overlap_fraction": round(
            mean(
                float(row["three_tau"]["final_changed_trace"]["l1_overlap_fraction"])
                for row in replicates
            ),
            12,
        ),
        "mean_three_tau_minus_one_tau_l1_overlap_delta": round(
            mean(
                row["three_tau_minus_one_tau_l1_overlap_delta"]
                for row in replicates
            ),
            12,
        ),
        "mean_one_tau_final_target_positive_edge_recovery_fraction": round(
            mean(
                float(
                    row["one_tau"]["final_changed_trace"][
                        "target_positive_edge_recovery_fraction"
                    ]
                )
                for row in replicates
            ),
            12,
        ),
        "mean_three_tau_final_target_positive_edge_recovery_fraction": round(
            mean(
                float(
                    row["three_tau"]["final_changed_trace"][
                        "target_positive_edge_recovery_fraction"
                    ]
                )
                for row in replicates
            ),
            12,
        ),
        "replicates_with_three_tau_higher_l1_overlap": sum(
            row["three_tau_minus_one_tau_l1_overlap_delta"] > 0.0
            for row in replicates
        ),
        "per_lag_three_tau_changed_trace_metrics": three_tau_per_lag,
    }


def run_memory_trace_reconstruction_audit(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Trace reconstruction config failed validation")
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
        )
        == len(replicates),
        "driver_memory_frozen": all(
            row["driver_frozen_memory_unchanged"] is True
            for row in replicates
        ),
        "all_events_have_full_three_tau_history": all(
            row["event_index"] >= THREE_TAU_DECISIONS for row in replicates
        ),
        "all_acquisitions_within_max": all(
            1 <= row["acquisition_decisions"] <= MAX_ACQUISITION_DECISIONS
            for row in replicates
        ),
        "all_have_changed_reward_edges": all(
            row["changed_reward_edge_count"] > 0 for row in replicates
        ),
        "all_state_clears_zero_reward_trace": all(
            row["one_tau"]["reset_reward_trace_l1"] <= TRACE_ZERO_TOLERANCE
            and row["three_tau"]["reset_reward_trace_l1"] <= TRACE_ZERO_TOLERANCE
            for row in replicates
        ),
        "all_replays_preserve_memory": all(
            row["one_tau"]["memory_unchanged"]
            and row["three_tau"]["memory_unchanged"]
            for row in replicates
        ),
        "all_one_tau_lags_reported": all(
            [item["lag"] for item in row["one_tau"]["lags"]]
            == list(range(-ONE_TAU_DECISIONS, 0))
            for row in replicates
        ),
        "all_three_tau_lags_reported": all(
            [item["lag"] for item in row["three_tau"]["lags"]]
            == list(range(-THREE_TAU_DECISIONS, 0))
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
            "EXPLORATORY_TRACE_RECONSTRUCTION_AUDIT_COMPLETE"
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
        description="Audit reconstruction of the reward-time KC eligibility trace"
    )
    parser.add_argument(
        "--config",
        default="data/memory_trace_reconstruction_audit_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_memory_trace_reconstruction_audit(
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
