from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from typing import Any

from .event_local_reinforcement_pulse import (
    _build_pre_event_checkpoint,
    _restore_recentered,
)
from .learning_control_study import _sha256_file
from .memory_history_expression_bridge import (
    _build_memory_pair,
    _replay_pair,
    _terminal_summary,
)
from .memory_trace_reconstruction_audit import _record_three_tau_trajectory
from .smoke import _digest_json


CONFIG_SCHEMA = "neurofly-memory-prefix-specificity-control-v0.1"
RECEIPT_SCHEMA = "neurofly-memory-prefix-specificity-control-receipt-v0.1"
STATUS = "PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE = "real-malecns-reward-memory-prefix-specificity"

KC_TRACE_SECONDS = 1.0
NEURAL_MS_PER_DECISION = 50
TERMINAL_DECISIONS = 20
PREFIX_DECISIONS = 40
FULL_HISTORY_DECISIONS = 60
PREFIX_ROTATION_POSITIONS = 20
MAX_ACQUISITION_DECISIONS = 300
POST_REWARD_DELAY_DECISIONS = 5
CHANGED_TOLERANCE = 1e-12
STATE_TOLERANCE = 1e-12

EXPECTED_REPLICATES = (
    ("PS1", 3203),
    ("PS2", 3209),
    ("PS3", 3217),
    ("PS4", 3221),
)
PRIOR_SEEDS = {
    2309, 2311, 2333, 2339,
    2609, 2617, 2621, 2633,
    2711, 2713, 2719, 2729,
    2801, 2803, 2819, 2833,
    2903, 2909, 2917, 2927,
    3001, 3011, 3019, 3023,
    3109, 3119, 3121, 3137,
}
ORIGIN_RUN_ID = 36104612747
ORIGIN_RECEIPT = "f61d6b9078cb43e80fdcf2bace26034cdb2b362739fd91119c450d54bf14162a"
ORIGIN_ARTIFACT = "45cf654bcceda452564a731b60ef84bdcc1b7f51c8ffa72cd26bdbb8f9bbc863"
ORIGIN_FREEZE = "data/memory_history_expression_bridge_run1_freeze_v01.json"

CLAIM_KEYS = {
    "learning_validated",
    "temporal_cue_index_confirmed",
    "prefix_sequence_specificity_confirmed",
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
            "Does the exact -60 through -21 prereward prefix contribute "
            "sequence-specific causal context to persistent reward-memory "
            "expression beyond generic extra runtime, when compared against "
            "the same 40 frame/context pairs circularly rotated by 20 positions "
            "while the terminal -20 through 0 sequence remains identical?"
        ),
        "origin_exact": (
            origin.get("history_expression_run_id") == ORIGIN_RUN_ID
            and origin.get("history_expression_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("history_expression_artifact_sha256") == ORIGIN_ARTIFACT
            and origin.get("history_expression_freeze") == ORIGIN_FREEZE
        ),
        "clock_exact": (
            clock.get("kc_trace_seconds") == KC_TRACE_SECONDS
            and clock.get("neural_ms_per_decision") == NEURAL_MS_PER_DECISION
            and clock.get("terminal_decisions") == TERMINAL_DECISIONS
            and clock.get("prefix_decisions") == PREFIX_DECISIONS
            and clock.get("full_history_decisions") == FULL_HISTORY_DECISIONS
            and TERMINAL_DECISIONS
            == round(KC_TRACE_SECONDS * 1000 / NEURAL_MS_PER_DECISION)
            and PREFIX_DECISIONS == 2 * TERMINAL_DECISIONS
            and FULL_HISTORY_DECISIONS
            == PREFIX_DECISIONS + TERMINAL_DECISIONS
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
            and runtime.get("exact_condition")
            == (
                "exact lags -60 through -1 followed by exact reward cue at lag 0"
            )
            and runtime.get("rotated_prefix_condition")
            == (
                "the same 40 frame/context pairs from source lags -60 through "
                "-21 circularly rotated left by 20 positions, followed by exact "
                "source lags -20 through -1 and exact reward cue at lag 0"
            )
            and runtime.get("prefix_rotation_positions")
            == PREFIX_ROTATION_POSITIONS
            and runtime.get("primary_comparison_window")
            == "common terminal replay lags -20 through 0 inclusive"
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
            "exact_terminal_any_changed_kc_activity",
            "rotated_terminal_any_changed_kc_activity",
            "exact_terminal_any_mbon07_state_difference",
            "rotated_terminal_any_mbon07_state_difference",
            "exact_terminal_any_mbon07_spike_difference",
            "rotated_terminal_any_mbon07_spike_difference",
            "exact_terminal_any_action_divergence",
            "rotated_terminal_any_action_divergence",
            "exact_reward_cue_action_divergence",
            "rotated_reward_cue_action_divergence",
            "paired_terminal_per_lag_expression_metrics",
        ),
        "interpretation_locked": (
            interpretation.get("no_parameter_tuning") is True
            and interpretation.get("no_posthoc_event_selection") is True
            and interpretation.get("no_posthoc_control_selection") is True
            and interpretation.get("exact_and_rotated_conditions_use_same_trajectory")
            is True
            and interpretation.get("prefix_frame_context_multiset_identical")
            is True
            and interpretation.get("terminal_sequence_identical") is True
            and interpretation.get(
                "changed_edges_defined_before_recall_from_paired_synaptic_difference"
            )
            is True
            and interpretation.get("primary_comparison_uses_identical_terminal_lags")
            is True
            and interpretation.get("no_directional_pass_threshold") is True
            and interpretation.get("result_is_prefix_specificity_localization_only")
            is True
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims) == CLAIM_KEYS
            and all(value is False for value in claims.values())
        ),
    }


def _row_identity(row: dict[str, Any]) -> str:
    frame_digest = hashlib.sha256(row["frame"].tobytes()).hexdigest()
    return _digest_json(
        {
            "frame_sha256": frame_digest,
            "context_sha256": _digest_json(row["context"]),
        }
    )


def _build_recall_sequences(
    trajectory: list[dict[str, Any]],
    event_index: int,
) -> dict[str, Any]:
    exact_prefix = trajectory[
        event_index - FULL_HISTORY_DECISIONS : event_index - TERMINAL_DECISIONS
    ]
    terminal = trajectory[
        event_index - TERMINAL_DECISIONS : event_index + 1
    ]
    if len(exact_prefix) != PREFIX_DECISIONS:
        raise RuntimeError("Incomplete exact early prefix")
    if len(terminal) != TERMINAL_DECISIONS + 1:
        raise RuntimeError("Incomplete terminal sequence")

    rotated_prefix = (
        exact_prefix[PREFIX_ROTATION_POSITIONS:]
        + exact_prefix[:PREFIX_ROTATION_POSITIONS]
    )
    exact = exact_prefix + terminal
    rotated = rotated_prefix + terminal
    if len(exact) != FULL_HISTORY_DECISIONS + 1:
        raise RuntimeError("Exact recall length mismatch")
    if len(rotated) != FULL_HISTORY_DECISIONS + 1:
        raise RuntimeError("Rotated recall length mismatch")

    exact_prefix_ids = [_row_identity(row) for row in exact_prefix]
    rotated_prefix_ids = [_row_identity(row) for row in rotated_prefix]
    if sorted(exact_prefix_ids) != sorted(rotated_prefix_ids):
        raise RuntimeError("Rotated prefix changed the frame/context multiset")

    exact_terminal_ids = [_row_identity(row) for row in exact[-21:]]
    rotated_terminal_ids = [_row_identity(row) for row in rotated[-21:]]
    if exact_terminal_ids != rotated_terminal_ids:
        raise RuntimeError("Terminal sequence drifted between conditions")

    exact_source_lags = list(range(-FULL_HISTORY_DECISIONS, 1))
    rotated_source_lags = (
        list(range(-40, -20))
        + list(range(-60, -40))
        + list(range(-20, 1))
    )
    if len(rotated_source_lags) != len(rotated):
        raise RuntimeError("Rotated source-lag mapping mismatch")

    return {
        "exact": exact,
        "rotated": rotated,
        "exact_prefix_multiset_digest": _digest_json(sorted(exact_prefix_ids)),
        "rotated_prefix_multiset_digest": _digest_json(sorted(rotated_prefix_ids)),
        "terminal_sequence_digest": _digest_json(exact_terminal_ids),
        "exact_source_lags": exact_source_lags,
        "rotated_source_lags": rotated_source_lags,
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
        raise RuntimeError("Selected prefix-specificity event is not reward")
    if event_index < FULL_HISTORY_DECISIONS:
        raise RuntimeError("Selected event lacks complete full history")

    sequences = _build_recall_sequences(trajectory, event_index)
    delay_rows = trajectory[
        event_index + 1 : event_index + 1 + POST_REWARD_DELAY_DECISIONS
    ]
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

    exact_none_inner, exact_none, exact_true_inner, exact_true = _build_memory_pair(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        delay_rows=delay_rows,
    )
    rotated_none_inner, rotated_none, rotated_true_inner, rotated_true = (
        _build_memory_pair(
            pre_event_checkpoint=pre_event_checkpoint,
            event=event,
            delay_rows=delay_rows,
        )
    )
    if _sha256_file(pre_event_checkpoint) != pre_sha:
        raise RuntimeError("Pre-event checkpoint mutated")

    if (
        exact_none["fraction_digest"] != rotated_none["fraction_digest"]
        or exact_true["fraction_digest"] != rotated_true["fraction_digest"]
    ):
        raise RuntimeError("Stored-memory pair differs between conditions")

    pre_inner = _restore_recentered(pre_event_checkpoint)
    circuit = pre_inner.brain.circuit
    reward_count = len(circuit["reward"])
    reward_mask = np.any(
        np.abs(circuit["gain"][:reward_count]) > 0.0,
        axis=0,
    )
    reward_pre = np.asarray(circuit["pre"], dtype=np.int64)[reward_mask]

    exact_delta = (
        np.asarray(exact_true["post_delay_fraction"])[reward_mask]
        - np.asarray(exact_none["post_delay_fraction"])[reward_mask]
    )
    rotated_delta = (
        np.asarray(rotated_true["post_delay_fraction"])[reward_mask]
        - np.asarray(rotated_none["post_delay_fraction"])[reward_mask]
    )
    if not np.allclose(exact_delta, rotated_delta, rtol=0.0, atol=0.0):
        raise RuntimeError("Paired synaptic delta differs between conditions")

    changed = np.abs(exact_delta) > CHANGED_TOLERANCE
    if not np.any(changed):
        raise RuntimeError("No changed reward edges for prefix specificity control")

    exact_replay = _replay_pair(
        none_inner=exact_none_inner,
        true_inner=exact_true_inner,
        sequence_rows=sequences["exact"],
        start_lag=-FULL_HISTORY_DECISIONS,
        reward_pre=reward_pre,
        changed_mask=changed,
        paired_delta=exact_delta,
    )
    rotated_replay = _replay_pair(
        none_inner=rotated_none_inner,
        true_inner=rotated_true_inner,
        sequence_rows=sequences["rotated"],
        start_lag=-FULL_HISTORY_DECISIONS,
        reward_pre=reward_pre,
        changed_mask=changed,
        paired_delta=rotated_delta,
    )

    exact_terminal = _terminal_summary(exact_replay["lags"])
    rotated_terminal = _terminal_summary(rotated_replay["lags"])

    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "acquisition_decisions": len(trajectory),
        "event_index": event_index,
        "trajectory_digest": driver["trajectory_digest"],
        "driver_frozen_memory_unchanged": driver["driver_frozen_memory_unchanged"],
        "pre_event_checkpoint_sha256": pre_sha,
        "memory_pair_identical_across_conditions": True,
        "prefix_frame_context_multiset_identical": (
            sequences["exact_prefix_multiset_digest"]
            == sequences["rotated_prefix_multiset_digest"]
        ),
        "terminal_sequence_identical": True,
        "exact_prefix_multiset_digest": sequences["exact_prefix_multiset_digest"],
        "rotated_prefix_multiset_digest": sequences[
            "rotated_prefix_multiset_digest"
        ],
        "terminal_sequence_digest": sequences["terminal_sequence_digest"],
        "exact_source_lags": sequences["exact_source_lags"],
        "rotated_source_lags": sequences["rotated_source_lags"],
        "changed_reward_edge_count": int(changed.sum()),
        "unique_changed_presynaptic_kc_count": int(
            len(np.unique(reward_pre[changed]))
        ),
        "changed_reward_l1": round(float(np.abs(exact_delta[changed]).sum()), 15),
        "exact": {
            "full_replay": exact_replay,
            "terminal": exact_terminal,
        },
        "rotated": {
            "full_replay": rotated_replay,
            "terminal": rotated_terminal,
        },
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    per_lag: list[dict[str, Any]] = []
    for lag in range(-TERMINAL_DECISIONS, 1):
        exact_rows = [
            next(
                item
                for item in rep["exact"]["terminal"]["per_lag"]
                if item["lag"] == lag
            )
            for rep in replicates
        ]
        rotated_rows = [
            next(
                item
                for item in rep["rotated"]["terminal"]["per_lag"]
                if item["lag"] == lag
            )
            for rep in replicates
        ]
        per_lag.append(
            {
                "lag": lag,
                "exact_mean_changed_kc_active_fraction": round(
                    mean(
                        row["changed_presynaptic_kc_active_fraction"]
                        for row in exact_rows
                    ),
                    12,
                ),
                "rotated_mean_changed_kc_active_fraction": round(
                    mean(
                        row["changed_presynaptic_kc_active_fraction"]
                        for row in rotated_rows
                    ),
                    12,
                ),
                "exact_mean_changed_l1_engaged_fraction": round(
                    mean(
                        row["changed_reward_l1_engaged_fraction"]
                        for row in exact_rows
                    ),
                    12,
                ),
                "rotated_mean_changed_l1_engaged_fraction": round(
                    mean(
                        row["changed_reward_l1_engaged_fraction"]
                        for row in rotated_rows
                    ),
                    12,
                ),
                "exact_mbon07_state_difference_fraction": round(
                    sum(row["any_mbon07_state_difference"] for row in exact_rows)
                    / len(exact_rows),
                    12,
                ),
                "rotated_mbon07_state_difference_fraction": round(
                    sum(
                        row["any_mbon07_state_difference"] for row in rotated_rows
                    )
                    / len(rotated_rows),
                    12,
                ),
                "exact_mbon07_spike_difference_fraction": round(
                    sum(row["mbon07_total_spike_delta"] != 0 for row in exact_rows)
                    / len(exact_rows),
                    12,
                ),
                "rotated_mbon07_spike_difference_fraction": round(
                    sum(
                        row["mbon07_total_spike_delta"] != 0
                        for row in rotated_rows
                    )
                    / len(rotated_rows),
                    12,
                ),
                "exact_action_divergence_fraction": round(
                    sum(row["action_diverged"] for row in exact_rows)
                    / len(exact_rows),
                    12,
                ),
                "rotated_action_divergence_fraction": round(
                    sum(row["action_diverged"] for row in rotated_rows)
                    / len(rotated_rows),
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
        "exact_terminal_replicates_with_changed_kc_activity": sum(
            row["exact"]["terminal"]["any_changed_kc_activity"]
            for row in replicates
        ),
        "rotated_terminal_replicates_with_changed_kc_activity": sum(
            row["rotated"]["terminal"]["any_changed_kc_activity"]
            for row in replicates
        ),
        "exact_terminal_replicates_with_mbon07_state_difference": sum(
            row["exact"]["terminal"]["any_mbon07_state_difference"]
            for row in replicates
        ),
        "rotated_terminal_replicates_with_mbon07_state_difference": sum(
            row["rotated"]["terminal"]["any_mbon07_state_difference"]
            for row in replicates
        ),
        "exact_terminal_replicates_with_mbon07_spike_difference": sum(
            row["exact"]["terminal"]["any_mbon07_spike_difference"]
            for row in replicates
        ),
        "rotated_terminal_replicates_with_mbon07_spike_difference": sum(
            row["rotated"]["terminal"]["any_mbon07_spike_difference"]
            for row in replicates
        ),
        "exact_terminal_replicates_with_action_divergence": sum(
            row["exact"]["terminal"]["any_action_divergence"]
            for row in replicates
        ),
        "rotated_terminal_replicates_with_action_divergence": sum(
            row["rotated"]["terminal"]["any_action_divergence"]
            for row in replicates
        ),
        "exact_reward_cue_action_divergence_fraction": round(
            sum(
                row["exact"]["terminal"]["reward_cue_action_divergence"]
                for row in replicates
            )
            / len(replicates),
            12,
        ),
        "rotated_reward_cue_action_divergence_fraction": round(
            sum(
                row["rotated"]["terminal"]["reward_cue_action_divergence"]
                for row in replicates
            )
            / len(replicates),
            12,
        ),
        "paired_terminal_per_lag_expression_metrics": per_lag,
    }


def run_memory_prefix_specificity_control(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Memory prefix-specificity config failed validation")
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
        "all_events_have_full_history": all(
            row["event_index"] >= FULL_HISTORY_DECISIONS for row in replicates
        ),
        "all_acquisitions_within_max": all(
            1 <= row["acquisition_decisions"] <= MAX_ACQUISITION_DECISIONS
            for row in replicates
        ),
        "all_memory_pairs_identical_across_conditions": all(
            row["memory_pair_identical_across_conditions"] is True
            for row in replicates
        ),
        "all_prefix_multisets_identical": all(
            row["prefix_frame_context_multiset_identical"] is True
            for row in replicates
        ),
        "all_terminal_sequences_identical": all(
            row["terminal_sequence_identical"] is True
            for row in replicates
        ),
        "all_have_changed_reward_edges": all(
            row["changed_reward_edge_count"] > 0 for row in replicates
        ),
        "all_replays_preserve_memory": all(
            row["exact"]["full_replay"]["memory_unchanged"]
            and row["rotated"]["full_replay"]["memory_unchanged"]
            for row in replicates
        ),
        "all_full_lags_reported": all(
            [item["lag"] for item in row["exact"]["full_replay"]["lags"]]
            == list(range(-FULL_HISTORY_DECISIONS, 1))
            and [item["lag"] for item in row["rotated"]["full_replay"]["lags"]]
            == list(range(-FULL_HISTORY_DECISIONS, 1))
            for row in replicates
        ),
        "all_primary_windows_identical": all(
            row["exact"]["terminal"]["terminal_lags"]
            == row["rotated"]["terminal"]["terminal_lags"]
            == list(range(-TERMINAL_DECISIONS, 1))
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
            "EXPLORATORY_MEMORY_PREFIX_SPECIFICITY_CONTROL_COMPLETE"
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
        "prefix_sequence_specificity_confirmed": False,
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
        description="Test sequence specificity of the early prereward prefix"
    )
    parser.add_argument(
        "--config",
        default="data/memory_prefix_specificity_control_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_memory_prefix_specificity_control(
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
