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
from .goal_training import (
    GoalMazeEnvironment,
    GoalMazeSession,
    _reinforcement_for_reward,
)
from .learning_control_study import ControlledBrain, _evaluate_arm, _sha256_file
from .smoke import _digest_json, _neural_decision_verified


CONFIG_SCHEMA = "neurofly-learning-mechanism-diagnostic-v0.1"
RECEIPT_SCHEMA = "neurofly-learning-mechanism-diagnostic-receipt-v0.1"
STATUS = "EXPLORATORY_DIAGNOSTIC_ONLY"
SCOPE = "real-malecns-temporal-credit-and-plastic-drift-diagnostic"
EXPECTED_TRAINING_STEPS = 60
EXPECTED_EVAL_STEPS = 20
EXPECTED_ARMS = (
    ("learning_true", True, "normal", "true"),
    ("learning_none", True, "normal", "none"),
    ("frozen_true", False, "normal", "true"),
)
EXPECTED_REPLICATES = (
    ("D1", 1409, (1451, 1453)),
    ("D2", 1423, (1459, 1471)),
    ("D3", 1427, (1481, 1483)),
)


def _normalized_replicates(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    rows = []
    for item in config.get("replicates") or []:
        if not isinstance(item, dict):
            return ()
        rows.append(
            (
                item.get("id"),
                item.get("training_seed"),
                tuple(item.get("held_out_seeds") or ()),
            )
        )
    return tuple(rows)


def validate_config(config: dict[str, Any]) -> dict[str, bool]:
    runtime = config.get("fixed_runtime") or {}
    origin = config.get("design_origin") or {}
    claims = config.get("claim_policy") or {}
    expected_arms = [
        {
            "name": name,
            "learning": learning,
            "sensory_mode": sensory_mode,
            "reinforcement_mode": reinforcement_mode,
        }
        for name, learning, sensory_mode, reinforcement_mode in EXPECTED_ARMS
    ]
    required = set(config.get("required_observations") or ())
    expected_required = {
        "per_decision_previous_outcome",
        "per_decision_scheduled_reinforcement",
        "per_decision_delivered_reinforcement",
        "per_decision_frame_digest",
        "per_decision_decoder",
        "per_decision_dan_spikes",
        "per_decision_memory_before_after",
        "post_training_checkpoint_memory_roundtrip",
        "frozen_held_out_evaluation",
    }
    configured_seeds = [
        seed
        for _, train_seed, heldout in EXPECTED_REPLICATES
        for seed in (train_seed, *heldout)
    ]
    return {
        "schema_exact": config.get("schema") == CONFIG_SCHEMA,
        "status_exact": config.get("status") == STATUS,
        "scope_exact": config.get("scope") == SCOPE,
        "origin_exact": (
            origin.get("remediation_run_id") == 35336398252
            and origin.get("remediation_receipt_sha256")
            == "aeccbbdeedc93799d3d97fbf765b4d1b7796e64ff903228835a83015f20f5b23"
            and origin.get("remediation_execution_valid") is True
            and origin.get(
                "observed_learning_true_minus_frozen_true_mean_reward_effect"
            )
            == -4.0
            and origin.get("post_hoc_mechanism_diagnostic") is True
        ),
        "runtime_exact": (
            runtime.get("decision_synchronous_world") is True
            and runtime.get("training_steps") == EXPECTED_TRAINING_STEPS
            and runtime.get("evaluation_steps_per_seed") == EXPECTED_EVAL_STEPS
        ),
        "arms_exact": config.get("arms") == expected_arms,
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "seeds_unique": len(configured_seeds) == len(set(configured_seeds)),
        "required_observations_exact": required == expected_required,
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims)
            == {
                "learning_validated",
                "temporal_credit_defect_confirmed",
                "unreinforced_plastic_drift_causal",
                "causal_learning_claim_authorized",
                "replacement_confirmatory_authorized",
                "behavioral_promotion_authorized",
            }
            and all(value is False for value in claims.values())
        ),
    }


def _frame_digest(frame: Any) -> str:
    try:
        import numpy as np

        array = np.asarray(frame, dtype=np.uint8)
        return hashlib.sha256(array.tobytes()).hexdigest()
    except Exception:
        return _digest_json(frame)


def _memory_snapshot(brain: MaleCNSBrain) -> dict[str, Any]:
    memory = dict(brain.brain.memory())
    return {
        "plastic_edges": int(memory["plastic_edges"]),
        "changed_edges": int(memory["changed_edges"]),
        "mean_efficacy": round(float(memory["mean_efficacy"]), 12),
        "minimum_efficacy": round(float(memory["minimum_efficacy"]), 12),
        "sha256": str(memory["sha256"]),
        "model": str(memory["model"]),
    }


def _trace_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    delivered = Counter(row["delivered_reinforcement"] for row in rows)
    generated = Counter(
        _reinforcement_for_reward(float(row["generated_reward"])) for row in rows
    )
    actions = Counter(row["decision_action"] for row in rows)
    memory_changed = [row for row in rows if row["memory_changed"]]
    none_rows = [
        row for row in rows if row["delivered_reinforcement"] == "none"
    ]
    reinforced_rows = [
        row for row in rows if row["delivered_reinforcement"] != "none"
    ]
    none_with_dan_spikes = [
        row
        for row in none_rows
        if int(row["reward_spikes"]) > 0 or int(row["aversive_spikes"]) > 0
    ]
    lag_rows = rows[1:]
    return {
        "steps": len(rows),
        "action_counts": dict(sorted(actions.items())),
        "hold_fraction": round(actions.get("HOLD", 0) / len(rows), 8),
        "delivered_reinforcement": dict(sorted(delivered.items())),
        "generated_outcome_reinforcement": dict(sorted(generated.items())),
        "memory_changed_steps": len(memory_changed),
        "memory_changed_none_steps": sum(
            row["delivered_reinforcement"] == "none" for row in memory_changed
        ),
        "memory_changed_reinforced_steps": sum(
            row["delivered_reinforcement"] != "none" for row in memory_changed
        ),
        "none_steps_with_endogenous_dan_spikes": len(none_with_dan_spikes),
        "none_steps": len(none_rows),
        "reinforced_steps": len(reinforced_rows),
        "mean_reward_spikes_on_none_steps": (
            round(mean(int(row["reward_spikes"]) for row in none_rows), 8)
            if none_rows
            else 0.0
        ),
        "mean_aversive_spikes_on_none_steps": (
            round(mean(int(row["aversive_spikes"]) for row in none_rows), 8)
            if none_rows
            else 0.0
        ),
        "mean_gate_spikes": round(
            mean(int(row["gate_spikes"]) for row in rows),
            8,
        ),
        "gate_zero_fraction": round(
            sum(int(row["gate_spikes"]) == 0 for row in rows) / len(rows),
            8,
        ),
        "mean_abs_difference_hz": round(
            mean(abs(float(row["difference_hz"])) for row in rows),
            8,
        ),
        "scheduled_reinforcement_matches_previous_outcome": all(
            row["scheduled_reinforcement"]
            == row["expected_from_previous_outcome"]
            for row in lag_rows
        ),
        "lagged_rows_checked": len(lag_rows),
    }


def _run_diagnostic_arm(
    *,
    arm_name: str,
    learning: bool,
    reinforcement_mode: str,
    initial_checkpoint: Path,
    arm_checkpoint: Path,
    train_seed: int,
    held_out_seeds: tuple[int, ...],
    scramble_seed: int,
) -> dict[str, Any]:
    shutil.copy2(initial_checkpoint, arm_checkpoint)
    start_sha = _sha256_file(arm_checkpoint)

    inner = MaleCNSBrain(checkpoint=arm_checkpoint, learning=learning)
    inner.brain.weights_frozen = not learning
    controlled = ControlledBrain(
        inner,
        sensory_mode="normal",
        reinforcement_mode=reinforcement_mode,
        scramble_seed=scramble_seed,
    )
    session = GoalMazeSession(
        controlled,
        environment=GoalMazeEnvironment(seed=train_seed),
        checkpoint=None,
        world_tick_seconds=3600.0,
        decision_synchronous_world=True,
    )

    initial_memory = _memory_snapshot(inner)
    rows: list[dict[str, Any]] = []
    previous_outcome: dict[str, Any] | None = None

    for decision_index in range(EXPECTED_TRAINING_STEPS):
        pre_context = session.environment.snapshot(include_grid=False)
        pre_frame = session.environment.render_rgb()
        scheduled = session.pending_reinforcement
        if scheduled == "none":
            scheduled = session.environment.reinforcement()
        expected_from_previous = (
            "none"
            if previous_outcome is None
            else _reinforcement_for_reward(float(previous_outcome["reward"]))
        )
        memory_before = _memory_snapshot(inner)

        state = session.tick()
        if not _neural_decision_verified(state):
            raise RuntimeError("Diagnostic decision lacks verifiable neural activity")
        memory_after = _memory_snapshot(inner)
        telemetry = copy.deepcopy((state.get("brain") or {}).get("telemetry") or {})

        row = {
            "decision_index": decision_index,
            "previous_outcome": copy.deepcopy(previous_outcome),
            "expected_from_previous_outcome": expected_from_previous,
            "scheduled_reinforcement": scheduled,
            "delivered_reinforcement": str(telemetry.get("reinforcement") or "none"),
            "pre_context_last_reward": float(pre_context.get("last_reward") or 0.0),
            "pre_context_last_event": pre_context.get("last_event"),
            "frame_digest": _frame_digest(pre_frame),
            "decision_action": str(state.get("decision_action") or "UNKNOWN"),
            "gate_spikes": int(telemetry.get("gate_spikes") or 0),
            "difference_hz": round(float(telemetry.get("difference_hz") or 0.0), 8),
            "left_hz": round(float(telemetry.get("left_hz") or 0.0), 8),
            "right_hz": round(float(telemetry.get("right_hz") or 0.0), 8),
            "reward_spikes": int(telemetry.get("reward_spikes") or 0),
            "aversive_spikes": int(telemetry.get("aversive_spikes") or 0),
            "kc_spikes": int(telemetry.get("kc_spikes") or 0),
            "generated_reward": float(state.get("last_reward") or 0.0),
            "generated_event": state.get("step_event"),
            "memory_before": memory_before,
            "memory_after": memory_after,
            "memory_changed": memory_before["sha256"] != memory_after["sha256"],
        }
        rows.append(row)
        previous_outcome = {
            "reward": row["generated_reward"],
            "event": row["generated_event"],
            "action": row["decision_action"],
            "frame_digest": row["frame_digest"],
        }

    memory_before_save = _memory_snapshot(inner)
    controlled.save(arm_checkpoint)
    checkpoint_sha = _sha256_file(arm_checkpoint)

    restored = MaleCNSBrain(checkpoint=arm_checkpoint, learning=False)
    restored.brain.weights_frozen = True
    memory_after_restore = _memory_snapshot(restored)
    checkpoint_roundtrip_exact = memory_before_save == memory_after_restore

    evaluation = _evaluate_arm(
        arm_checkpoint=arm_checkpoint,
        held_out_seeds=held_out_seeds,
        eval_steps=EXPECTED_EVAL_STEPS,
        decision_synchronous_world=True,
    )

    return {
        "arm": arm_name,
        "learning": learning,
        "sensory_mode": "normal",
        "reinforcement_mode": reinforcement_mode,
        "initial_checkpoint_sha256": start_sha,
        "post_training_checkpoint_sha256": checkpoint_sha,
        "initial_memory": initial_memory,
        "trace": rows,
        "trace_summary": _trace_summary(rows),
        "memory_before_save": memory_before_save,
        "memory_after_restore": memory_after_restore,
        "checkpoint_memory_roundtrip_exact": checkpoint_roundtrip_exact,
        "evaluation": evaluation,
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    arms = {name for name, *_ in EXPECTED_ARMS}
    out: dict[str, Any] = {}
    for arm_name in sorted(arms):
        rows = [rep["arm_results"][arm_name] for rep in replicates]
        out[arm_name] = {
            "mean_memory_changed_steps": round(
                mean(item["trace_summary"]["memory_changed_steps"] for item in rows),
                8,
            ),
            "mean_memory_changed_none_steps": round(
                mean(
                    item["trace_summary"]["memory_changed_none_steps"]
                    for item in rows
                ),
                8,
            ),
            "mean_none_steps_with_endogenous_dan_spikes": round(
                mean(
                    item["trace_summary"]["none_steps_with_endogenous_dan_spikes"]
                    for item in rows
                ),
                8,
            ),
            "mean_gate_zero_fraction": round(
                mean(item["trace_summary"]["gate_zero_fraction"] for item in rows),
                8,
            ),
            "mean_training_hold_fraction": round(
                mean(item["trace_summary"]["hold_fraction"] for item in rows),
                8,
            ),
            "mean_eval_reward": round(
                mean(item["evaluation"]["aggregate"]["mean_total_reward"] for item in rows),
                8,
            ),
            "mean_eval_hold_fraction": round(
                mean(
                    item["evaluation"]["aggregate"]["mean_hold_fraction"]
                    for item in rows
                ),
                8,
            ),
            "mean_final_efficacy_delta": round(
                mean(
                    item["memory_before_save"]["mean_efficacy"]
                    - item["initial_memory"]["mean_efficacy"]
                    for item in rows
                ),
                12,
            ),
            "memory_sha_changed_replicates": sum(
                item["memory_before_save"]["sha256"]
                != item["initial_memory"]["sha256"]
                for item in rows
            ),
        }

    out["descriptive_contrasts"] = {
        "learning_true_minus_frozen_true_eval_reward": round(
            out["learning_true"]["mean_eval_reward"]
            - out["frozen_true"]["mean_eval_reward"],
            8,
        ),
        "learning_none_minus_frozen_true_eval_reward": round(
            out["learning_none"]["mean_eval_reward"]
            - out["frozen_true"]["mean_eval_reward"],
            8,
        ),
        "learning_true_minus_learning_none_eval_reward": round(
            out["learning_true"]["mean_eval_reward"]
            - out["learning_none"]["mean_eval_reward"],
            8,
        ),
    }
    return out


def run_learning_mechanism_diagnostic(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Learning mechanism diagnostic config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)

    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha_before = _sha256_file(base_checkpoint)
    replicate_results: list[dict[str, Any]] = []

    for replicate_index, (replicate_id, train_seed, heldout) in enumerate(
        EXPECTED_REPLICATES
    ):
        rep_dir = output_dir / replicate_id
        rep_dir.mkdir(parents=True, exist_ok=True)
        arm_results: dict[str, Any] = {}

        for arm_index, (name, learning, _sensory_mode, reinforcement_mode) in enumerate(
            EXPECTED_ARMS
        ):
            arm_results[name] = _run_diagnostic_arm(
                arm_name=name,
                learning=bool(learning),
                reinforcement_mode=str(reinforcement_mode),
                initial_checkpoint=base_checkpoint,
                arm_checkpoint=rep_dir / f"{name}.npz",
                train_seed=train_seed,
                held_out_seeds=heldout,
                scramble_seed=80_000 + replicate_index * 100 + arm_index,
            )

        replicate_results.append(
            {
                "replicate_id": replicate_id,
                "training_seed": train_seed,
                "held_out_seeds": list(heldout),
                "arm_results": arm_results,
            }
        )

    source_sha_after = _sha256_file(base_checkpoint)

    true_and_frozen = [
        arm
        for rep in replicate_results
        for name, arm in rep["arm_results"].items()
        if name in {"learning_true", "frozen_true"}
    ]
    learning_arms = [
        arm
        for rep in replicate_results
        for name, arm in rep["arm_results"].items()
        if name in {"learning_true", "learning_none"}
    ]
    frozen_arms = [
        rep["arm_results"]["frozen_true"] for rep in replicate_results
    ]

    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "all_replicates_executed": (
            len(replicate_results) == len(EXPECTED_REPLICATES)
            and tuple(rep["replicate_id"] for rep in replicate_results)
            == tuple(row[0] for row in EXPECTED_REPLICATES)
        ),
        "all_arms_start_from_source_checkpoint": all(
            arm["initial_checkpoint_sha256"] == source_sha_before
            for rep in replicate_results
            for arm in rep["arm_results"].values()
        ),
        "all_decisions_real_malecns_verified": all(
            len(arm["trace"]) == EXPECTED_TRAINING_STEPS
            for rep in replicate_results
            for arm in rep["arm_results"].values()
        ),
        "true_and_frozen_schedule_matches_previous_outcome": all(
            arm["trace_summary"][
                "scheduled_reinforcement_matches_previous_outcome"
            ]
            for arm in true_and_frozen
        ),
        "learning_none_delivers_no_external_reinforcement": all(
            set(rep["arm_results"]["learning_none"]["trace_summary"][
                "delivered_reinforcement"
            ])
            <= {"none"}
            for rep in replicate_results
        ),
        "checkpoint_memory_roundtrip_exact": all(
            arm["checkpoint_memory_roundtrip_exact"]
            for rep in replicate_results
            for arm in rep["arm_results"].values()
        ),
        "frozen_memory_unchanged": all(
            arm["trace_summary"]["memory_changed_steps"] == 0
            and arm["memory_before_save"]["sha256"]
            == arm["initial_memory"]["sha256"]
            for arm in frozen_arms
        ),
        "learning_arm_memory_observed": all(
            "memory_before_save" in arm and "memory_after_restore" in arm
            for arm in learning_arms
        ),
        "evaluation_frozen_and_reinforcement_disabled": all(
            arm["evaluation"]["learning"] is False
            and arm["evaluation"]["reinforcement_mode"] == "none"
            for rep in replicate_results
            for arm in rep["arm_results"].values()
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
        "replicates": replicate_results,
        "aggregate": _aggregate(replicate_results),
        "learning_validated": False,
        "temporal_credit_defect_confirmed": False,
        "unreinforced_plastic_drift_causal": False,
        "causal_learning_claim_authorized": False,
        "replacement_confirmatory_authorized": False,
        "behavioral_promotion_authorized": False,
        "human_science_review_required": True,
    }
    body["receipt_sha256"] = _digest_json(body)

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = receipt_path.with_suffix(receipt_path.suffix + ".partial")
    temporary.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    temporary.replace(receipt_path)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run NeuroFly temporal-credit and plastic-drift diagnostic"
    )
    parser.add_argument(
        "--config",
        default="data/learning_mechanism_diagnostic_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_learning_mechanism_diagnostic(
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
                "evidence_gates": result["evidence_gates"],
                "aggregate": result["aggregate"],
                "receipt_sha256": result["receipt_sha256"],
                "learning_validated": result["learning_validated"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["execution_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
