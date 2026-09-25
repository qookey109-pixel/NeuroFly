from __future__ import annotations

import argparse
import copy
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
from .memory_temporal_index_audit import (
    _population_step,
    _prepare_memory_branch,
    _state_difference,
)
from .memory_trace_reconstruction_audit import _record_three_tau_trajectory
from .smoke import _digest_json


CONFIG_SCHEMA = "neurofly-memory-history-expression-bridge-v0.1"
RECEIPT_SCHEMA = "neurofly-memory-history-expression-bridge-receipt-v0.1"
STATUS = "PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE = "real-malecns-reward-memory-history-expression-bridge"

KC_TRACE_SECONDS = 1.0
NEURAL_MS_PER_DECISION = 50
ONE_TAU_DECISIONS = 20
THREE_TAU_DECISIONS = 60
MAX_ACQUISITION_DECISIONS = 300
POST_REWARD_DELAY_DECISIONS = 5
CHANGED_TOLERANCE = 1e-12
STATE_TOLERANCE = 1e-12

EXPECTED_REPLICATES = (
    ("HE1", 3109),
    ("HE2", 3119),
    ("HE3", 3121),
    ("HE4", 3137),
)
PRIOR_SEEDS = {
    2309, 2311, 2333, 2339,
    2609, 2617, 2621, 2633,
    2711, 2713, 2719, 2729,
    2801, 2803, 2819, 2833,
    2903, 2909, 2917, 2927,
    3001, 3011, 3019, 3023,
}
ORIGIN_RUN_ID = 36103039412
ORIGIN_RECEIPT = "fb5538afb4aab6a1f1608e054bf9b5c6852c867945d0e6c198b381b6537be131"
ORIGIN_ARTIFACT = "590d0fd9eae139a8374c93ec314f02b35428a901fed59dfb83907a5b21c31ecd"
ORIGIN_FREEZE = "data/memory_trace_reconstruction_audit_run1_freeze_v01.json"

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
            "Does a three-tau prereward history, which reconstructs more of the "
            "original KC eligibility state, stabilize expression of the persistent "
            "paired reward-memory difference through changed KCs and MBON07 "
            "compared with a one-tau history on the same fresh trajectory?"
        ),
        "origin_exact": (
            origin.get("trace_reconstruction_run_id") == ORIGIN_RUN_ID
            and origin.get("trace_reconstruction_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("trace_reconstruction_artifact_sha256") == ORIGIN_ARTIFACT
            and origin.get("trace_reconstruction_freeze") == ORIGIN_FREEZE
        ),
        "clock_exact": (
            clock.get("kc_trace_seconds") == KC_TRACE_SECONDS
            and clock.get("neural_ms_per_decision") == NEURAL_MS_PER_DECISION
            and clock.get("one_tau_decisions") == ONE_TAU_DECISIONS
            and clock.get("three_tau_decisions") == THREE_TAU_DECISIONS
            and ONE_TAU_DECISIONS
            == round(KC_TRACE_SECONDS * 1000 / NEURAL_MS_PER_DECISION)
            and THREE_TAU_DECISIONS == 3 * ONE_TAU_DECISIONS
        ),
        "runtime_exact": (
            runtime.get("event_selection")
            == "first natural reward at or after decision index 60"
            and runtime.get("maximum_acquisition_decisions")
            == MAX_ACQUISITION_DECISIONS
            and runtime.get("post_reward_delay_decisions")
            == POST_REWARD_DELAY_DECISIONS
            and runtime.get("history_and_delay_external_reinforcement") == "none"
            and runtime.get("state_clear_before_recall") is True
            and runtime.get("recall_plasticity_frozen") is True
            and runtime.get("recall_external_reinforcement") == "none"
            and runtime.get("one_tau_sequence")
            == (
                "exact 20 recorded prereward decisions followed by the exact "
                "reward-event cue"
            )
            and runtime.get("three_tau_sequence")
            == (
                "exact 60 recorded prereward decisions followed by the exact "
                "reward-event cue"
            )
            and runtime.get("primary_comparison_window")
            == "common terminal lags -20 through 0 inclusive"
            and runtime.get("three_tau_context_only_window")
            == (
                "lags -60 through -21 are context warmup only and are excluded "
                "from primary expression counts"
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
            "one_tau_terminal_any_changed_kc_activity",
            "three_tau_terminal_any_changed_kc_activity",
            "one_tau_terminal_any_mbon07_state_difference",
            "three_tau_terminal_any_mbon07_state_difference",
            "one_tau_terminal_any_mbon07_spike_difference",
            "three_tau_terminal_any_mbon07_spike_difference",
            "one_tau_terminal_any_action_divergence",
            "three_tau_terminal_any_action_divergence",
            "one_tau_reward_cue_action_divergence",
            "three_tau_reward_cue_action_divergence",
            "paired_terminal_per_lag_expression_metrics",
        ),
        "interpretation_locked": (
            interpretation.get("no_parameter_tuning") is True
            and interpretation.get("no_posthoc_event_selection") is True
            and interpretation.get("no_posthoc_window_selection") is True
            and interpretation.get("one_tau_and_three_tau_compared_on_same_trajectory")
            is True
            and interpretation.get(
                "changed_edges_defined_before_recall_from_paired_synaptic_difference"
            )
            is True
            and interpretation.get(
                "primary_expression_comparison_uses_identical_terminal_lags"
            )
            is True
            and interpretation.get("three_tau_extra_history_is_context_only")
            is True
            and interpretation.get("no_directional_pass_threshold") is True
            and interpretation.get("result_is_memory_expression_localization_only")
            is True
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims) == CLAIM_KEYS
            and all(value is False for value in claims.values())
        ),
    }


def _clear_for_recall(inner: Any) -> dict[str, Any]:
    before = _plastic_edge_state(inner)["fraction_digest"]
    inner.brain.reset(keep_memory=True)
    inner._last_visual_rgb = None
    after = _plastic_edge_state(inner)["fraction_digest"]
    if before != after:
        raise RuntimeError("State clear did not preserve synaptic memory")
    inner.learning = False
    inner.brain.weights_frozen = True
    return {
        "memory_fraction_digest": after,
        "memory_preserved": True,
    }


def _replay_pair(
    *,
    none_inner: Any,
    true_inner: Any,
    sequence_rows: list[dict[str, Any]],
    start_lag: int,
    reward_pre: Any,
    changed_mask: Any,
    paired_delta: Any,
) -> dict[str, Any]:
    import numpy as np

    none_reset = _clear_for_recall(none_inner)
    true_reset = _clear_for_recall(true_inner)
    none_memory_before = _plastic_edge_state(none_inner)["fraction_digest"]
    true_memory_before = _plastic_edge_state(true_inner)["fraction_digest"]

    reward_pre = np.asarray(reward_pre, dtype=np.int64)
    changed = np.asarray(changed_mask, dtype=bool)
    delta = np.asarray(paired_delta, dtype=np.float64)
    unique_changed_pre = np.unique(reward_pre[changed])
    changed_l1 = float(np.abs(delta[changed]).sum())

    lags: list[dict[str, Any]] = []
    for offset, row in enumerate(sequence_rows):
        lag = start_lag + offset

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
            raise RuntimeError("Recall replay delivered external reinforcement")

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
        active_l1 = float(np.abs(delta[active_changed_edges]).sum())
        expression = _state_difference(none_state, true_state)

        lags.append(
            {
                "lag": lag,
                "changed_presynaptic_kc_active_count": int(active_changed_kc.sum()),
                "changed_presynaptic_kc_active_fraction": round(
                    float(active_changed_kc.sum()) / float(len(unique_changed_pre)),
                    12,
                ),
                "changed_reward_edge_active_count": int(active_changed_edges.sum()),
                "changed_reward_l1_engaged": round(active_l1, 15),
                "changed_reward_l1_engaged_fraction": (
                    round(active_l1 / changed_l1, 12) if changed_l1 else 0.0
                ),
                "none_action": none_decision.action,
                "true_action": true_decision.action,
                "action_diverged": none_decision.action != true_decision.action,
                **expression,
            }
        )

    none_memory_after = _plastic_edge_state(none_inner)["fraction_digest"]
    true_memory_after = _plastic_edge_state(true_inner)["fraction_digest"]
    if (
        none_memory_before != none_memory_after
        or true_memory_before != true_memory_after
    ):
        raise RuntimeError("Frozen recall mutated synaptic memory")

    expected = list(range(start_lag, 1))
    if [row["lag"] for row in lags] != expected:
        raise RuntimeError("Recall lag grid mismatch")

    return {
        "none_reset": none_reset,
        "true_reset": true_reset,
        "memory_unchanged": True,
        "lags": lags,
    }


def _terminal_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    terminal = [row for row in rows if -ONE_TAU_DECISIONS <= row["lag"] <= 0]
    expected = list(range(-ONE_TAU_DECISIONS, 1))
    if [row["lag"] for row in terminal] != expected:
        raise RuntimeError("Terminal comparison window mismatch")

    reward_cue = terminal[-1]
    if reward_cue["lag"] != 0:
        raise RuntimeError("Terminal window does not end at reward cue")

    return {
        "terminal_lags": expected,
        "any_changed_kc_activity": any(
            row["changed_presynaptic_kc_active_count"] > 0 for row in terminal
        ),
        "max_changed_kc_active_fraction": round(
            max(row["changed_presynaptic_kc_active_fraction"] for row in terminal),
            12,
        ),
        "max_changed_reward_l1_engaged_fraction": round(
            max(row["changed_reward_l1_engaged_fraction"] for row in terminal),
            12,
        ),
        "any_mbon07_state_difference": any(
            row["any_mbon07_state_difference"] for row in terminal
        ),
        "any_mbon07_spike_difference": any(
            row["mbon07_total_spike_delta"] != 0 for row in terminal
        ),
        "max_mbon07_membrane_delta": round(
            max(row["mbon07_max_abs_membrane_delta"] for row in terminal),
            12,
        ),
        "max_mbon07_conductance_delta": round(
            max(row["mbon07_max_abs_conductance_delta"] for row in terminal),
            12,
        ),
        "max_dnp20_membrane_delta": round(
            max(row["dnp20_max_abs_membrane_delta"] for row in terminal),
            12,
        ),
        "max_dnpe017_membrane_delta": round(
            max(row["dnpe017_max_abs_membrane_delta"] for row in terminal),
            12,
        ),
        "any_action_divergence": any(row["action_diverged"] for row in terminal),
        "action_divergence_lags": [
            row["lag"] for row in terminal if row["action_diverged"]
        ],
        "reward_cue_action_divergence": reward_cue["action_diverged"],
        "reward_cue_changed_kc_active_fraction": reward_cue[
            "changed_presynaptic_kc_active_fraction"
        ],
        "reward_cue_changed_l1_engaged_fraction": reward_cue[
            "changed_reward_l1_engaged_fraction"
        ],
        "reward_cue_mbon07_state_difference": reward_cue[
            "any_mbon07_state_difference"
        ],
        "per_lag": terminal,
    }


def _build_memory_pair(
    *,
    pre_event_checkpoint: Path,
    event: dict[str, Any],
    delay_rows: list[dict[str, Any]],
) -> tuple[Any, dict[str, Any], Any, dict[str, Any]]:
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
    return none_inner, none, true_inner, true


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
        raise RuntimeError("Selected history-expression event is not reward")
    if event_index < THREE_TAU_DECISIONS:
        raise RuntimeError("Selected event lacks complete three-tau history")

    one_tau_rows = trajectory[
        event_index - ONE_TAU_DECISIONS : event_index + 1
    ]
    three_tau_rows = trajectory[
        event_index - THREE_TAU_DECISIONS : event_index + 1
    ]
    delay_rows = trajectory[
        event_index + 1 : event_index + 1 + POST_REWARD_DELAY_DECISIONS
    ]
    if len(one_tau_rows) != ONE_TAU_DECISIONS + 1:
        raise RuntimeError("Incomplete one-tau recall sequence")
    if len(three_tau_rows) != THREE_TAU_DECISIONS + 1:
        raise RuntimeError("Incomplete three-tau recall sequence")
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

    one_none_inner, one_none, one_true_inner, one_true = _build_memory_pair(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        delay_rows=delay_rows,
    )
    three_none_inner, three_none, three_true_inner, three_true = _build_memory_pair(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        delay_rows=delay_rows,
    )
    if _sha256_file(pre_event_checkpoint) != pre_sha:
        raise RuntimeError("Pre-event checkpoint mutated")

    if (
        one_none["fraction_digest"] != three_none["fraction_digest"]
        or one_true["fraction_digest"] != three_true["fraction_digest"]
    ):
        raise RuntimeError("Stored-memory pair differs between 1 tau and 3 tau")

    pre_inner = _restore_recentered(pre_event_checkpoint)
    circuit = pre_inner.brain.circuit
    reward_count = len(circuit["reward"])
    reward_mask = np.any(
        np.abs(circuit["gain"][:reward_count]) > 0.0,
        axis=0,
    )
    reward_pre = np.asarray(circuit["pre"], dtype=np.int64)[reward_mask]

    one_delta = (
        np.asarray(one_true["post_delay_fraction"])[reward_mask]
        - np.asarray(one_none["post_delay_fraction"])[reward_mask]
    )
    three_delta = (
        np.asarray(three_true["post_delay_fraction"])[reward_mask]
        - np.asarray(three_none["post_delay_fraction"])[reward_mask]
    )
    if not np.allclose(one_delta, three_delta, rtol=0.0, atol=0.0):
        raise RuntimeError("Paired synaptic delta differs between replay windows")

    changed = np.abs(one_delta) > CHANGED_TOLERANCE
    if not np.any(changed):
        raise RuntimeError("No changed reward edges for history-expression bridge")

    one_replay = _replay_pair(
        none_inner=one_none_inner,
        true_inner=one_true_inner,
        sequence_rows=one_tau_rows,
        start_lag=-ONE_TAU_DECISIONS,
        reward_pre=reward_pre,
        changed_mask=changed,
        paired_delta=one_delta,
    )
    three_replay = _replay_pair(
        none_inner=three_none_inner,
        true_inner=three_true_inner,
        sequence_rows=three_tau_rows,
        start_lag=-THREE_TAU_DECISIONS,
        reward_pre=reward_pre,
        changed_mask=changed,
        paired_delta=three_delta,
    )

    one_terminal = _terminal_summary(one_replay["lags"])
    three_terminal = _terminal_summary(three_replay["lags"])

    three_context = [
        row for row in three_replay["lags"] if row["lag"] < -ONE_TAU_DECISIONS
    ]
    if [row["lag"] for row in three_context] != list(
        range(-THREE_TAU_DECISIONS, -ONE_TAU_DECISIONS)
    ):
        raise RuntimeError("Three-tau context-only lag grid mismatch")

    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "acquisition_decisions": len(trajectory),
        "event_index": event_index,
        "trajectory_digest": driver["trajectory_digest"],
        "driver_frozen_memory_unchanged": driver["driver_frozen_memory_unchanged"],
        "pre_event_checkpoint_sha256": pre_sha,
        "none_post_delay_fraction_digest": one_none["fraction_digest"],
        "true_post_delay_fraction_digest": one_true["fraction_digest"],
        "memory_pair_identical_across_windows": True,
        "changed_reward_edge_count": int(changed.sum()),
        "unique_changed_presynaptic_kc_count": int(
            len(np.unique(reward_pre[changed]))
        ),
        "changed_reward_l1": round(float(np.abs(one_delta[changed]).sum()), 15),
        "one_tau": {
            "full_replay": one_replay,
            "terminal": one_terminal,
        },
        "three_tau": {
            "context_only_lags": three_context,
            "full_replay": three_replay,
            "terminal": three_terminal,
        },
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    lag_rows: list[dict[str, Any]] = []
    for lag in range(-ONE_TAU_DECISIONS, 1):
        one_rows = [
            next(
                item
                for item in rep["one_tau"]["terminal"]["per_lag"]
                if item["lag"] == lag
            )
            for rep in replicates
        ]
        three_rows = [
            next(
                item
                for item in rep["three_tau"]["terminal"]["per_lag"]
                if item["lag"] == lag
            )
            for rep in replicates
        ]
        lag_rows.append(
            {
                "lag": lag,
                "one_tau_mean_changed_kc_active_fraction": round(
                    mean(
                        row["changed_presynaptic_kc_active_fraction"]
                        for row in one_rows
                    ),
                    12,
                ),
                "three_tau_mean_changed_kc_active_fraction": round(
                    mean(
                        row["changed_presynaptic_kc_active_fraction"]
                        for row in three_rows
                    ),
                    12,
                ),
                "one_tau_mean_changed_l1_engaged_fraction": round(
                    mean(
                        row["changed_reward_l1_engaged_fraction"]
                        for row in one_rows
                    ),
                    12,
                ),
                "three_tau_mean_changed_l1_engaged_fraction": round(
                    mean(
                        row["changed_reward_l1_engaged_fraction"]
                        for row in three_rows
                    ),
                    12,
                ),
                "one_tau_mbon07_state_difference_fraction": round(
                    sum(row["any_mbon07_state_difference"] for row in one_rows)
                    / len(one_rows),
                    12,
                ),
                "three_tau_mbon07_state_difference_fraction": round(
                    sum(row["any_mbon07_state_difference"] for row in three_rows)
                    / len(three_rows),
                    12,
                ),
                "one_tau_mbon07_spike_difference_fraction": round(
                    sum(row["mbon07_total_spike_delta"] != 0 for row in one_rows)
                    / len(one_rows),
                    12,
                ),
                "three_tau_mbon07_spike_difference_fraction": round(
                    sum(row["mbon07_total_spike_delta"] != 0 for row in three_rows)
                    / len(three_rows),
                    12,
                ),
                "one_tau_action_divergence_fraction": round(
                    sum(row["action_diverged"] for row in one_rows) / len(one_rows),
                    12,
                ),
                "three_tau_action_divergence_fraction": round(
                    sum(row["action_diverged"] for row in three_rows)
                    / len(three_rows),
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
        "one_tau_terminal_replicates_with_changed_kc_activity": sum(
            row["one_tau"]["terminal"]["any_changed_kc_activity"]
            for row in replicates
        ),
        "three_tau_terminal_replicates_with_changed_kc_activity": sum(
            row["three_tau"]["terminal"]["any_changed_kc_activity"]
            for row in replicates
        ),
        "one_tau_terminal_replicates_with_mbon07_state_difference": sum(
            row["one_tau"]["terminal"]["any_mbon07_state_difference"]
            for row in replicates
        ),
        "three_tau_terminal_replicates_with_mbon07_state_difference": sum(
            row["three_tau"]["terminal"]["any_mbon07_state_difference"]
            for row in replicates
        ),
        "one_tau_terminal_replicates_with_mbon07_spike_difference": sum(
            row["one_tau"]["terminal"]["any_mbon07_spike_difference"]
            for row in replicates
        ),
        "three_tau_terminal_replicates_with_mbon07_spike_difference": sum(
            row["three_tau"]["terminal"]["any_mbon07_spike_difference"]
            for row in replicates
        ),
        "one_tau_terminal_replicates_with_action_divergence": sum(
            row["one_tau"]["terminal"]["any_action_divergence"]
            for row in replicates
        ),
        "three_tau_terminal_replicates_with_action_divergence": sum(
            row["three_tau"]["terminal"]["any_action_divergence"]
            for row in replicates
        ),
        "one_tau_reward_cue_action_divergence_fraction": round(
            sum(
                row["one_tau"]["terminal"]["reward_cue_action_divergence"]
                for row in replicates
            )
            / len(replicates),
            12,
        ),
        "three_tau_reward_cue_action_divergence_fraction": round(
            sum(
                row["three_tau"]["terminal"]["reward_cue_action_divergence"]
                for row in replicates
            )
            / len(replicates),
            12,
        ),
        "paired_terminal_per_lag_expression_metrics": lag_rows,
    }


def run_memory_history_expression_bridge(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Memory history-expression config failed validation")
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
        "all_events_have_three_tau_history": all(
            row["event_index"] >= THREE_TAU_DECISIONS for row in replicates
        ),
        "all_acquisitions_within_max": all(
            1 <= row["acquisition_decisions"] <= MAX_ACQUISITION_DECISIONS
            for row in replicates
        ),
        "all_memory_pairs_identical_across_windows": all(
            row["memory_pair_identical_across_windows"] is True
            for row in replicates
        ),
        "all_have_changed_reward_edges": all(
            row["changed_reward_edge_count"] > 0 for row in replicates
        ),
        "all_replays_preserve_memory": all(
            row["one_tau"]["full_replay"]["memory_unchanged"]
            and row["three_tau"]["full_replay"]["memory_unchanged"]
            for row in replicates
        ),
        "all_one_tau_lags_reported": all(
            [item["lag"] for item in row["one_tau"]["full_replay"]["lags"]]
            == list(range(-ONE_TAU_DECISIONS, 1))
            for row in replicates
        ),
        "all_three_tau_lags_reported": all(
            [item["lag"] for item in row["three_tau"]["full_replay"]["lags"]]
            == list(range(-THREE_TAU_DECISIONS, 1))
            for row in replicates
        ),
        "all_primary_windows_identical": all(
            row["one_tau"]["terminal"]["terminal_lags"]
            == row["three_tau"]["terminal"]["terminal_lags"]
            == list(range(-ONE_TAU_DECISIONS, 1))
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
            "EXPLORATORY_MEMORY_HISTORY_EXPRESSION_BRIDGE_COMPLETE"
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
        description="Compare one- versus three-tau stored reward-memory expression"
    )
    parser.add_argument(
        "--config",
        default="data/memory_history_expression_bridge_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_memory_history_expression_bridge(
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
