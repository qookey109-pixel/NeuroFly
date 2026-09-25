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
from .memory_history_expression_bridge import (
    _build_memory_pair,
    _clear_for_recall,
    _population_step,
    _state_difference,
    _terminal_summary,
)
from .memory_trace_reconstruction_audit import _record_three_tau_trajectory
from .smoke import _digest_json


CONFIG_SCHEMA = "neurofly-memory-residual-state-localization-v0.1"
RECEIPT_SCHEMA = "neurofly-memory-residual-state-localization-receipt-v0.1"
STATUS = "PREREGISTERED_EXPLORATORY_EXECUTION"
SCOPE = "real-malecns-reward-memory-residual-state-localization"

PREFIX_DECISIONS = 40
TERMINAL_DECISIONS = 20
FULL_HISTORY_DECISIONS = 60
POST_REWARD_DELAY_DECISIONS = 5
MAX_ACQUISITION_DECISIONS = 300
CHANGED_TOLERANCE = 1e-12

EXPECTED_CONDITIONS = (
    "intact",
    "clear_refractory_delay",
    "clear_luminance",
    "clear_adaptation",
    "clear_kernel_credit",
)
EXPECTED_REPLICATES = (
    ("RL1", 3407),
    ("RL2", 3413),
    ("RL3", 3419),
    ("RL4", 3433),
)
TARGET_FIELDS = {
    "intact": set(),
    "clear_refractory_delay": {"refractory", "queue", "queue_count"},
    "clear_luminance": {"luminance"},
    "clear_adaptation": {"adaptation"},
    "clear_kernel_credit": {
        "eligibility",
        "eligibility_last",
        "modulation",
        "modulation_last",
    },
}
CLAIM_KEYS = {
    "learning_validated",
    "temporal_cue_index_confirmed",
    "prefix_sequence_specificity_confirmed",
    "transient_state_carrier_confirmed",
    "memory_expression_causal",
    "replacement_confirmatory_authorized",
    "behavioral_promotion_authorized",
}


def _normalized_replicates(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (item.get("id"), item.get("trajectory_seed"))
        for item in config.get("replicates", [])
        if isinstance(item, dict)
    )


def validate_config(config: dict[str, Any]) -> dict[str, bool]:
    runtime = config.get("runtime") or {}
    claims = config.get("claim_policy") or {}
    conditions = tuple(
        item.get("id")
        for item in runtime.get("conditions", [])
        if isinstance(item, dict)
    )
    return {
        "schema_exact": config.get("schema") == CONFIG_SCHEMA,
        "status_exact": config.get("status") == STATUS,
        "scope_exact": config.get("scope") == SCOPE,
        "question_frozen": config.get("question") == (
            "Which remaining safely isolatable Stonkfly transient state class carries "
            "the exact three-tau prefix benefit into the identical terminal -20 through "
            "0 memory-expression window after rule traces and wrapper visual history "
            "were excluded and v/g clearing was found to enhance rather than abolish "
            "expression?"
        ),
        "geometry_exact": (
            config["model_clock"]["prefix_decisions"] == PREFIX_DECISIONS
            and config["model_clock"]["terminal_decisions"] == TERMINAL_DECISIONS
            and config["model_clock"]["full_history_decisions"] == FULL_HISTORY_DECISIONS
        ),
        "runtime_exact": (
            runtime.get("event_selection")
            == "first natural reward at or after decision index 60"
            and runtime.get("maximum_acquisition_decisions")
            == MAX_ACQUISITION_DECISIONS
            and runtime.get("post_reward_delay_decisions")
            == POST_REWARD_DELAY_DECISIONS
            and runtime.get("boundary")
            == "after source lag -21 and before source lag -20"
            and runtime.get("primary_comparison_window")
            == "common terminal replay lags -20 through 0 inclusive"
            and runtime.get("recall_plasticity_frozen") is True
            and runtime.get("recall_external_reinforcement") == "none"
            and runtime.get("no_model_parameter_change") is True
            and conditions == EXPECTED_CONDITIONS
        ),
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "claims_locked": (
            set(claims) == CLAIM_KEYS
            and all(value is False for value in claims.values())
        ),
    }


def _array_digest(value: Any) -> str:
    import numpy as np

    a = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(str(a.dtype).encode())
    h.update(json.dumps(list(a.shape)).encode())
    h.update(a.tobytes())
    return h.hexdigest()


def _checkpoint_field_snapshot(inner: Any) -> dict[str, str]:
    b = inner.brain
    return {name: _array_digest(getattr(b, name)) for name in b.fields}


def _apply_intervention(inner: Any, condition: str) -> dict[str, Any]:
    b = inner.brain
    if condition not in TARGET_FIELDS:
        raise ValueError(condition)

    before = _checkpoint_field_snapshot(inner)
    memory_before = _plastic_edge_state(inner)["fraction_digest"]

    for field in TARGET_FIELDS[condition]:
        getattr(b, field)[:] = b.initial[field]

    after = _checkpoint_field_snapshot(inner)
    memory_after = _plastic_edge_state(inner)["fraction_digest"]
    if memory_before != memory_after:
        raise RuntimeError("Residual-state intervention mutated synaptic memory")

    changed = {name for name in before if before[name] != after[name]}
    if not changed.issubset(TARGET_FIELDS[condition]):
        raise RuntimeError(
            f"Residual-state intervention changed non-target fields: "
            f"{sorted(changed - TARGET_FIELDS[condition])}"
        )

    return {
        "condition": condition,
        "allowed_fields": sorted(TARGET_FIELDS[condition]),
        "changed_fields": sorted(changed),
        "null_clear": not bool(changed),
        "memory_preserved": True,
        "before": before,
        "after": after,
    }


def _replay_rows(
    *,
    none_inner: Any,
    true_inner: Any,
    rows: list[dict[str, Any]],
    start_lag: int,
    reward_pre: Any,
    changed_mask: Any,
    paired_delta: Any,
) -> list[dict[str, Any]]:
    import numpy as np

    reward_pre = np.asarray(reward_pre, dtype=np.int64)
    changed = np.asarray(changed_mask, dtype=bool)
    delta = np.asarray(paired_delta, dtype=np.float64)
    unique_changed_pre = np.unique(reward_pre[changed])
    changed_l1 = float(np.abs(delta[changed]).sum())

    output = []
    for offset, row in enumerate(rows):
        lag = start_lag + offset
        none_decision = none_inner.decide(
            row["frame"], "none", context=copy.deepcopy(row["context"])
        )
        true_decision = true_inner.decide(
            row["frame"], "none", context=copy.deepcopy(row["context"])
        )
        if (
            float(none_decision.telemetry.get("stimulus_ms") or 0.0) != 0.0
            or float(true_decision.telemetry.get("stimulus_ms") or 0.0) != 0.0
        ):
            raise RuntimeError("Recall delivered external reinforcement")

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

        output.append(
            {
                "lag": lag,
                "changed_presynaptic_kc_active_count": int(active_changed_kc.sum()),
                "changed_presynaptic_kc_active_fraction": round(
                    float(active_changed_kc.sum()) / len(unique_changed_pre), 12
                ),
                "changed_reward_l1_engaged_fraction": (
                    round(active_l1 / changed_l1, 12) if changed_l1 else 0.0
                ),
                "none_action": none_decision.action,
                "true_action": true_decision.action,
                "action_diverged": none_decision.action != true_decision.action,
                **_state_difference(none_state, true_state),
            }
        )
    return output


def _run_condition(
    *,
    condition: str,
    pre_event_checkpoint: Path,
    event: dict[str, Any],
    delay_rows: list[dict[str, Any]],
    prefix_rows: list[dict[str, Any]],
    terminal_rows: list[dict[str, Any]],
    reward_pre: Any,
    changed_mask: Any,
    paired_delta: Any,
) -> dict[str, Any]:
    none_inner, none, true_inner, true = _build_memory_pair(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        delay_rows=delay_rows,
    )
    _clear_for_recall(none_inner)
    _clear_for_recall(true_inner)

    none_memory_before = _plastic_edge_state(none_inner)["fraction_digest"]
    true_memory_before = _plastic_edge_state(true_inner)["fraction_digest"]

    prefix = _replay_rows(
        none_inner=none_inner,
        true_inner=true_inner,
        rows=prefix_rows,
        start_lag=-FULL_HISTORY_DECISIONS,
        reward_pre=reward_pre,
        changed_mask=changed_mask,
        paired_delta=paired_delta,
    )

    none_intervention = _apply_intervention(none_inner, condition)
    true_intervention = _apply_intervention(true_inner, condition)

    terminal_rows_out = _replay_rows(
        none_inner=none_inner,
        true_inner=true_inner,
        rows=terminal_rows,
        start_lag=-TERMINAL_DECISIONS,
        reward_pre=reward_pre,
        changed_mask=changed_mask,
        paired_delta=paired_delta,
    )
    terminal = _terminal_summary(terminal_rows_out)

    if none_memory_before != _plastic_edge_state(none_inner)["fraction_digest"]:
        raise RuntimeError("None memory changed during frozen recall")
    if true_memory_before != _plastic_edge_state(true_inner)["fraction_digest"]:
        raise RuntimeError("True memory changed during frozen recall")

    return {
        "condition": condition,
        "none_intervention": none_intervention,
        "true_intervention": true_intervention,
        "prefix_lags": [row["lag"] for row in prefix],
        "terminal": terminal,
        "memory_unchanged": True,
        "post_delay_fraction_digests": {
            "none": none["fraction_digest"],
            "true": true["fraction_digest"],
        },
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
    if event_index < FULL_HISTORY_DECISIONS:
        raise RuntimeError("Event lacks full history")

    event = trajectory[event_index]
    prefix_rows = trajectory[
        event_index - FULL_HISTORY_DECISIONS : event_index - TERMINAL_DECISIONS
    ]
    terminal_rows = trajectory[
        event_index - TERMINAL_DECISIONS : event_index + 1
    ]
    delay_rows = trajectory[
        event_index + 1 : event_index + 1 + POST_REWARD_DELAY_DECISIONS
    ]
    if len(prefix_rows) != PREFIX_DECISIONS:
        raise RuntimeError("Prefix length mismatch")
    if len(terminal_rows) != TERMINAL_DECISIONS + 1:
        raise RuntimeError("Terminal length mismatch")
    if len(delay_rows) != POST_REWARD_DELAY_DECISIONS:
        raise RuntimeError("Delay length mismatch")

    pre_event_checkpoint = rep_dir / "pre-event.npz"
    pre = _build_pre_event_checkpoint(
        trajectory=trajectory,
        event_index=event_index,
        base_checkpoint=base_checkpoint,
        pre_event_checkpoint=pre_event_checkpoint,
    )

    ref_none_inner, ref_none, ref_true_inner, ref_true = _build_memory_pair(
        pre_event_checkpoint=pre_event_checkpoint,
        event=event,
        delay_rows=delay_rows,
    )
    pre_inner = _restore_recentered(pre_event_checkpoint)
    circuit = pre_inner.brain.circuit
    reward_count = len(circuit["reward"])
    reward_mask = np.any(np.abs(circuit["gain"][:reward_count]) > 0.0, axis=0)
    reward_pre = np.asarray(circuit["pre"], dtype=np.int64)[reward_mask]
    paired_delta = (
        np.asarray(ref_true["post_delay_fraction"])[reward_mask]
        - np.asarray(ref_none["post_delay_fraction"])[reward_mask]
    )
    changed = np.abs(paired_delta) > CHANGED_TOLERANCE
    if not np.any(changed):
        raise RuntimeError("No changed reward edges")

    reference_pair = {
        "none": ref_none["fraction_digest"],
        "true": ref_true["fraction_digest"],
    }
    conditions = {}
    for condition in EXPECTED_CONDITIONS:
        result = _run_condition(
            condition=condition,
            pre_event_checkpoint=pre_event_checkpoint,
            event=event,
            delay_rows=delay_rows,
            prefix_rows=prefix_rows,
            terminal_rows=terminal_rows,
            reward_pre=reward_pre,
            changed_mask=changed,
            paired_delta=paired_delta,
        )
        if result["post_delay_fraction_digests"] != reference_pair:
            raise RuntimeError("Paired memory differs across conditions")
        conditions[condition] = result

    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "event_index": event_index,
        "acquisition_decisions": len(trajectory),
        "trajectory_digest": driver["trajectory_digest"],
        "driver_frozen_memory_unchanged": driver["driver_frozen_memory_unchanged"],
        "pre_event_checkpoint_sha256": pre["pre_event_checkpoint_sha256"],
        "changed_reward_edge_count": int(changed.sum()),
        "conditions": conditions,
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "replicate_count": len(replicates),
        "mean_changed_reward_edge_count": round(
            mean(rep["changed_reward_edge_count"] for rep in replicates), 8
        ),
        "conditions": {},
    }
    for condition in EXPECTED_CONDITIONS:
        terminals = [rep["conditions"][condition]["terminal"] for rep in replicates]
        per_lag = []
        for lag in range(-TERMINAL_DECISIONS, 1):
            rows = [
                next(item for item in terminal["per_lag"] if item["lag"] == lag)
                for terminal in terminals
            ]
            per_lag.append({
                "lag": lag,
                "mean_changed_kc_active_fraction": round(
                    mean(row["changed_presynaptic_kc_active_fraction"] for row in rows), 12
                ),
                "mean_changed_l1_engaged_fraction": round(
                    mean(row["changed_reward_l1_engaged_fraction"] for row in rows), 12
                ),
                "mbon07_state_difference_fraction": round(
                    sum(row["any_mbon07_state_difference"] for row in rows) / len(rows), 12
                ),
                "mbon07_spike_difference_fraction": round(
                    sum(row["mbon07_total_spike_delta"] != 0 for row in rows) / len(rows), 12
                ),
                "action_divergence_fraction": round(
                    sum(row["action_diverged"] for row in rows) / len(rows), 12
                ),
            })

        result["conditions"][condition] = {
            "replicates_with_changed_kc_activity": sum(
                terminal["any_changed_kc_activity"] for terminal in terminals
            ),
            "replicates_with_mbon07_state_difference": sum(
                terminal["any_mbon07_state_difference"] for terminal in terminals
            ),
            "replicates_with_mbon07_spike_difference": sum(
                terminal["any_mbon07_spike_difference"] for terminal in terminals
            ),
            "replicates_with_action_divergence": sum(
                terminal["any_action_divergence"] for terminal in terminals
            ),
            "reward_cue_action_divergence_fraction": round(
                sum(terminal["reward_cue_action_divergence"] for terminal in terminals)
                / len(terminals),
                12,
            ),
            "mean_changed_kc_active_fraction": round(
                mean(row["mean_changed_kc_active_fraction"] for row in per_lag), 12
            ),
            "mean_changed_l1_engaged_fraction": round(
                mean(row["mean_changed_l1_engaged_fraction"] for row in per_lag), 12
            ),
            "mean_mbon07_state_difference_fraction": round(
                mean(row["mbon07_state_difference_fraction"] for row in per_lag), 12
            ),
            "mean_mbon07_spike_difference_fraction": round(
                mean(row["mbon07_spike_difference_fraction"] for row in per_lag), 12
            ),
            "mean_action_divergence_fraction": round(
                mean(row["action_divergence_fraction"] for row in per_lag), 12
            ),
            "per_lag": per_lag,
        }
    return result


def run_memory_residual_state_localization(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Residual-state localization config failed validation")
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
        "all_events_have_full_history": all(
            rep["event_index"] >= FULL_HISTORY_DECISIONS for rep in replicates
        ),
        "all_conditions_preserve_memory": all(
            rep["conditions"][condition]["memory_unchanged"]
            for rep in replicates
            for condition in EXPECTED_CONDITIONS
        ),
        "all_interventions_pure": all(
            set(rep["conditions"][condition]["none_intervention"]["changed_fields"])
            .issubset(TARGET_FIELDS[condition])
            and set(rep["conditions"][condition]["true_intervention"]["changed_fields"])
            .issubset(TARGET_FIELDS[condition])
            for rep in replicates
            for condition in EXPECTED_CONDITIONS
        ),
        "all_prefix_lags_exact": all(
            rep["conditions"][condition]["prefix_lags"] == list(range(-60, -20))
            for rep in replicates
            for condition in EXPECTED_CONDITIONS
        ),
        "all_terminal_lags_exact": all(
            rep["conditions"][condition]["terminal"]["terminal_lags"]
            == list(range(-20, 1))
            for rep in replicates
            for condition in EXPECTED_CONDITIONS
        ),
        "claims_remain_locked": all(
            value is False for value in config["claim_policy"].values()
        ),
    }
    execution_valid = all(config_gates.values()) and all(evidence_gates.values())

    body = {
        "schema": RECEIPT_SCHEMA,
        "status": (
            "EXPLORATORY_MEMORY_RESIDUAL_STATE_LOCALIZATION_COMPLETE"
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
        "transient_state_carrier_confirmed": False,
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="data/memory_residual_state_localization_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_memory_residual_state_localization(
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
