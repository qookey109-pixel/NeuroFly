from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

from .brain_runtime import MaleCNSBrain
from .goal_training import GoalMazeEnvironment, GoalMazeSession
from .learning_control_study import (
    ControlledBrain,
    _aggregate_evaluations,
    _run_steps,
    _sha256_file,
    _state_metrics,
)
from .smoke import _digest_json, _neural_decision_verified


CONFIG_SCHEMA = "neurofly-dan-baseline-intervention-v0.1"
RECEIPT_SCHEMA = "neurofly-dan-baseline-intervention-receipt-v0.1"
STATUS = "EXPLORATORY_INTERVENTION_ONLY"
SCOPE = "real-malecns-task-conditioned-dan-baseline-intervention"

EXPECTED_CALIBRATION_SEEDS = (1601, 1607, 1609)
EXPECTED_CALIBRATION_STEPS = 60
EXPECTED_TRAINING_STEPS = 60
EXPECTED_EVAL_STEPS = 20
EXPECTED_ARMS = (
    ("learning_none_zero_baseline", True, "none", "zero"),
    ("learning_none_calibrated_baseline", True, "none", "task_conditioned"),
    ("frozen_none_zero_baseline", False, "none", "zero"),
)
EXPECTED_REPLICATES = (
    ("B1", 1613, (1619, 1621)),
    ("B2", 1627, (1637, 1657)),
    ("B3", 1663, (1667, 1669)),
    ("B4", 1693, (1697, 1699)),
)
PREVIOUSLY_USED_SEEDS = {
    109, 211, 223, 227, 229, 233, 239, 241, 251,
    701, 709, 719,
    1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051, 1061, 1063,
    1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117, 1123, 1129, 1151, 1153, 1163,
    1201, 1213, 1217, 1223, 1301, 1303, 1307, 1319, 1321, 1327, 1361, 1367,
    1409, 1423, 1427, 1451, 1453, 1459, 1471, 1481, 1483,
}


def _normalized_arms(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    rows = []
    for item in config.get("arms") or []:
        if not isinstance(item, dict):
            return ()
        rows.append(
            (
                item.get("name"),
                item.get("learning"),
                item.get("reinforcement_mode"),
                item.get("dan_baseline_mode"),
            )
        )
    return tuple(rows)


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
    origin = config.get("design_origin") or {}
    calibration = config.get("calibration") or {}
    runtime = config.get("runtime") or {}
    claims = config.get("claim_policy") or {}
    configured = [
        *EXPECTED_CALIBRATION_SEEDS,
        *[
            seed
            for _, training_seed, heldout in EXPECTED_REPLICATES
            for seed in (training_seed, *heldout)
        ],
    ]
    return {
        "schema_exact": config.get("schema") == CONFIG_SCHEMA,
        "status_exact": config.get("status") == STATUS,
        "scope_exact": config.get("scope") == SCOPE,
        "origin_exact": (
            origin.get("diagnostic_run_id") == 35343487907
            and origin.get("diagnostic_receipt_sha256")
            == "8f1e34f5fd4795869c8d4251eccd12a196e2c14e5d56118fb810078972142db2"
            and origin.get("diagnostic_execution_valid") is True
            and origin.get("observed_learning_none_memory_changed_steps_per_replicate") == 60
            and origin.get("observed_learning_none_mean_efficacy_delta") == -0.009343703588
            and origin.get("observed_learning_none_minus_frozen_eval_reward") == -2.83333334
        ),
        "calibration_exact": (
            calibration.get("interpretation")
            == "task-conditioned endogenous DAN firing baseline; not a biological resting-rate claim"
            and tuple(calibration.get("seeds") or ()) == EXPECTED_CALIBRATION_SEEDS
            and calibration.get("steps_per_seed") == EXPECTED_CALIBRATION_STEPS
            and calibration.get("reinforcement_mode") == "none"
            and calibration.get("learning") is False
            and calibration.get("sensory_mode") == "normal"
            and calibration.get("estimator")
            == "per-cell mean firing rate in Hz across all 50 ms decisions"
        ),
        "arms_exact": _normalized_arms(config) == EXPECTED_ARMS,
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "runtime_exact": (
            runtime.get("decision_synchronous_world") is True
            and runtime.get("training_steps") == EXPECTED_TRAINING_STEPS
            and runtime.get("evaluation_steps_per_seed") == EXPECTED_EVAL_STEPS
        ),
        "fresh_disjoint_seeds": (
            len(configured) == len(set(configured))
            and not (set(configured) & PREVIOUSLY_USED_SEEDS)
        ),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ())
        == (
            "memory_changed_steps",
            "final_mean_efficacy_delta",
            "evaluation_mean_total_reward",
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims)
            == {
                "learning_validated",
                "task_conditioned_dan_baseline_causal",
                "biological_dan_resting_rate_established",
                "causal_learning_claim_authorized",
                "replacement_confirmatory_authorized",
                "behavioral_promotion_authorized",
            }
            and all(value is False for value in claims.values())
        ),
    }


def _memory_snapshot(inner: MaleCNSBrain) -> dict[str, Any]:
    memory = dict(inner.brain.memory())
    return {
        "plastic_edges": int(memory["plastic_edges"]),
        "changed_edges": int(memory["changed_edges"]),
        "mean_efficacy": round(float(memory["mean_efficacy"]), 12),
        "minimum_efficacy": round(float(memory["minimum_efficacy"]), 12),
        "sha256": str(memory["sha256"]),
        "model": str(memory["model"]),
    }


def _baseline_digest(values: list[float]) -> str:
    return _digest_json([round(float(value), 8) for value in values])


def _estimate_task_conditioned_dan_baseline(
    *,
    base_checkpoint: Path,
) -> dict[str, Any]:
    import numpy as np

    all_rates = []
    seed_results = []
    source_sha = _sha256_file(base_checkpoint)
    dan_ids: list[str] | None = None
    reward_count: int | None = None
    aversive_count: int | None = None

    for seed in EXPECTED_CALIBRATION_SEEDS:
        inner = MaleCNSBrain(checkpoint=base_checkpoint, learning=False)
        inner.brain.weights_frozen = True
        controlled = ControlledBrain(
            inner,
            sensory_mode="normal",
            reinforcement_mode="none",
            scramble_seed=0,
        )
        session = GoalMazeSession(
            controlled,
            environment=GoalMazeEnvironment(seed=seed),
            checkpoint=None,
            world_tick_seconds=3600.0,
            decision_synchronous_world=True,
        )

        rows = []
        decision_seconds = inner.neural_ms / 1000.0
        for step in range(EXPECTED_CALIBRATION_STEPS):
            state = session.tick()
            if not _neural_decision_verified(state):
                raise RuntimeError("Calibration decision lacks verifiable neural activity")
            indices = inner.brain.circuit["dan"]
            rates = inner.brain.counts[indices].astype(float) / decision_seconds
            if not np.isfinite(rates).all():
                raise RuntimeError("Non-finite DAN calibration rate")
            all_rates.append(rates.copy())
            telemetry = copy.deepcopy(
                ((state.get("brain") or {}).get("telemetry") or {})
            )
            rows.append(
                {
                    "step": step,
                    "reward_spikes": int(telemetry.get("reward_spikes") or 0),
                    "aversive_spikes": int(telemetry.get("aversive_spikes") or 0),
                    "total_dan_spikes": int(inner.brain.counts[indices].sum()),
                    "action": str(state.get("decision_action") or "UNKNOWN"),
                    "gate_spikes": int(telemetry.get("gate_spikes") or 0),
                }
            )

        if set(controlled.delivered_reinforcement) - {"none"}:
            raise RuntimeError("Calibration delivered external reinforcement")

        if dan_ids is None:
            dan_ids = [str(inner.brain.ids[i]) for i in inner.brain.circuit["dan"]]
            reward_count = len(inner.brain.circuit["reward"])
            aversive_count = len(inner.brain.circuit["aversive"])

        seed_results.append(
            {
                "seed": seed,
                "steps": EXPECTED_CALIBRATION_STEPS,
                "source_checkpoint_sha256": source_sha,
                "delivered_reinforcement": dict(
                    sorted(controlled.delivered_reinforcement.items())
                ),
                "mean_total_dan_spikes_per_decision": round(
                    mean(row["total_dan_spikes"] for row in rows), 8
                ),
                "mean_reward_spikes_per_decision": round(
                    mean(row["reward_spikes"] for row in rows), 8
                ),
                "mean_aversive_spikes_per_decision": round(
                    mean(row["aversive_spikes"] for row in rows), 8
                ),
                "neural_activity_verified": True,
            }
        )

    matrix = np.vstack(all_rates)
    baseline = matrix.mean(axis=0)
    if dan_ids is None or reward_count is None or aversive_count is None:
        raise RuntimeError("DAN calibration produced no data")
    if baseline.shape != (len(dan_ids),):
        raise RuntimeError("DAN baseline shape mismatch")
    if not np.isfinite(baseline).all() or np.any(baseline < 0):
        raise RuntimeError("Invalid DAN baseline")

    values = [round(float(value), 8) for value in baseline]
    return {
        "interpretation": (
            "task-conditioned endogenous DAN firing baseline; "
            "not a biological resting-rate claim"
        ),
        "dan_ids": dan_ids,
        "dan_count": len(dan_ids),
        "reward_cell_count": reward_count,
        "aversive_cell_count": aversive_count,
        "values_hz": values,
        "digest": _baseline_digest(values),
        "mean_reward_cell_baseline_hz": round(
            mean(values[:reward_count]), 8
        ),
        "mean_aversive_cell_baseline_hz": round(
            mean(values[reward_count:]), 8
        ),
        "nonzero_cells": sum(value > 0 for value in values),
        "seed_results": seed_results,
    }


def _set_baseline(inner: MaleCNSBrain, baseline_hz: list[float] | None) -> None:
    import numpy as np

    if baseline_hz is None:
        inner.brain.dan_baseline_hz[:] = 0.0
        return
    values = np.asarray(baseline_hz, dtype=np.float64)
    if values.shape != inner.brain.dan_baseline_hz.shape:
        raise RuntimeError("DAN baseline vector shape mismatch")
    if not np.isfinite(values).all() or np.any(values < 0):
        raise RuntimeError("Invalid DAN baseline vector")
    inner.brain.dan_baseline_hz[:] = values


def _restore_arm_brain(
    *,
    checkpoint: Path,
    learning: bool,
    baseline_hz: list[float] | None,
    checkpoint_is_source_zero_baseline: bool,
) -> MaleCNSBrain:
    if checkpoint_is_source_zero_baseline:
        inner = MaleCNSBrain(checkpoint=checkpoint, learning=learning)
        _set_baseline(inner, baseline_hz)
    else:
        inner = MaleCNSBrain(checkpoint=None, learning=learning)
        _set_baseline(inner, baseline_hz)
        inner.brain.restore(checkpoint)
    inner.brain.weights_frozen = not learning
    return inner


def _trace_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    actions = Counter(row["action"] for row in rows)
    return {
        "steps": len(rows),
        "action_counts": dict(sorted(actions.items())),
        "hold_fraction": round(actions.get("HOLD", 0) / len(rows), 8),
        "gate_zero_fraction": round(
            sum(int(row["gate_spikes"]) == 0 for row in rows) / len(rows),
            8,
        ),
        "memory_changed_steps": sum(bool(row["memory_changed"]) for row in rows),
        "mean_reward_spikes": round(
            mean(int(row["reward_spikes"]) for row in rows), 8
        ),
        "mean_aversive_spikes": round(
            mean(int(row["aversive_spikes"]) for row in rows), 8
        ),
    }


def _evaluate_checkpoint(
    *,
    arm_checkpoint: Path,
    baseline_hz: list[float] | None,
    held_out_seeds: tuple[int, ...],
) -> dict[str, Any]:
    per_seed = []
    for seed in held_out_seeds:
        inner = _restore_arm_brain(
            checkpoint=arm_checkpoint,
            learning=False,
            baseline_hz=baseline_hz,
            checkpoint_is_source_zero_baseline=False,
        )
        if inner.learning or not inner.brain.weights_frozen:
            raise RuntimeError("Held-out evaluation must be frozen")
        controlled = ControlledBrain(
            inner,
            sensory_mode="normal",
            reinforcement_mode="none",
            scramble_seed=0,
        )
        session = GoalMazeSession(
            controlled,
            environment=GoalMazeEnvironment(seed=seed),
            checkpoint=None,
            world_tick_seconds=3600.0,
            decision_synchronous_world=True,
        )
        states = _run_steps(session, EXPECTED_EVAL_STEPS)
        per_seed.append(
            {
                "seed": seed,
                "metrics": _state_metrics(states),
                "delivered_reinforcement": dict(
                    sorted(controlled.delivered_reinforcement.items())
                ),
            }
        )
    return {
        "held_out_seeds": list(held_out_seeds),
        "steps_per_seed": EXPECTED_EVAL_STEPS,
        "learning": False,
        "reinforcement_mode": "none",
        "sensory_mode": "normal",
        "per_seed": per_seed,
        "aggregate": _aggregate_evaluations(per_seed),
    }


def _run_arm(
    *,
    name: str,
    learning: bool,
    baseline_mode: str,
    baseline_hz: list[float],
    base_checkpoint: Path,
    arm_checkpoint: Path,
    train_seed: int,
    held_out_seeds: tuple[int, ...],
) -> dict[str, Any]:
    shutil.copy2(base_checkpoint, arm_checkpoint)
    source_sha = _sha256_file(base_checkpoint)
    baseline = baseline_hz if baseline_mode == "task_conditioned" else None

    inner = _restore_arm_brain(
        checkpoint=arm_checkpoint,
        learning=learning,
        baseline_hz=baseline,
        checkpoint_is_source_zero_baseline=True,
    )
    initial_memory = _memory_snapshot(inner)
    baseline_digest = _baseline_digest(
        [float(value) for value in inner.brain.dan_baseline_hz]
    )

    controlled = ControlledBrain(
        inner,
        sensory_mode="normal",
        reinforcement_mode="none",
        scramble_seed=0,
    )
    session = GoalMazeSession(
        controlled,
        environment=GoalMazeEnvironment(seed=train_seed),
        checkpoint=None,
        world_tick_seconds=3600.0,
        decision_synchronous_world=True,
    )

    rows = []
    for step in range(EXPECTED_TRAINING_STEPS):
        before = _memory_snapshot(inner)
        state = session.tick()
        if not _neural_decision_verified(state):
            raise RuntimeError("Intervention decision lacks verifiable neural activity")
        after = _memory_snapshot(inner)
        telemetry = copy.deepcopy(((state.get("brain") or {}).get("telemetry") or {}))
        rows.append(
            {
                "step": step,
                "action": str(state.get("decision_action") or "UNKNOWN"),
                "gate_spikes": int(telemetry.get("gate_spikes") or 0),
                "reward_spikes": int(telemetry.get("reward_spikes") or 0),
                "aversive_spikes": int(telemetry.get("aversive_spikes") or 0),
                "memory_before_sha256": before["sha256"],
                "memory_after_sha256": after["sha256"],
                "memory_changed": before["sha256"] != after["sha256"],
                "mean_efficacy_after": after["mean_efficacy"],
            }
        )

    if set(controlled.delivered_reinforcement) - {"none"}:
        raise RuntimeError("Intervention arm delivered external reinforcement")

    final_memory = _memory_snapshot(inner)
    controlled.save(arm_checkpoint)
    checkpoint_sha = _sha256_file(arm_checkpoint)

    restored = _restore_arm_brain(
        checkpoint=arm_checkpoint,
        learning=False,
        baseline_hz=baseline,
        checkpoint_is_source_zero_baseline=False,
    )
    restored_memory = _memory_snapshot(restored)
    roundtrip_exact = final_memory == restored_memory

    evaluation = _evaluate_checkpoint(
        arm_checkpoint=arm_checkpoint,
        baseline_hz=baseline,
        held_out_seeds=held_out_seeds,
    )

    return {
        "arm": name,
        "learning": learning,
        "reinforcement_mode": "none",
        "dan_baseline_mode": baseline_mode,
        "dan_baseline_digest": baseline_digest,
        "initial_checkpoint_sha256": source_sha,
        "post_training_checkpoint_sha256": checkpoint_sha,
        "initial_memory": initial_memory,
        "final_memory": final_memory,
        "restored_memory": restored_memory,
        "checkpoint_memory_roundtrip_exact": roundtrip_exact,
        "trace_summary": _trace_summary(rows),
        "trace": rows,
        "final_mean_efficacy_delta": round(
            final_memory["mean_efficacy"] - initial_memory["mean_efficacy"], 12
        ),
        "evaluation": evaluation,
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, *_ in EXPECTED_ARMS:
        rows = [rep["arm_results"][name] for rep in replicates]
        out[name] = {
            "mean_memory_changed_steps": round(
                mean(row["trace_summary"]["memory_changed_steps"] for row in rows), 8
            ),
            "mean_final_efficacy_delta": round(
                mean(row["final_mean_efficacy_delta"] for row in rows), 12
            ),
            "mean_eval_reward": round(
                mean(row["evaluation"]["aggregate"]["mean_total_reward"] for row in rows),
                8,
            ),
            "mean_eval_hold_fraction": round(
                mean(row["evaluation"]["aggregate"]["mean_hold_fraction"] for row in rows),
                8,
            ),
            "mean_training_hold_fraction": round(
                mean(row["trace_summary"]["hold_fraction"] for row in rows), 8
            ),
            "mean_gate_zero_fraction": round(
                mean(row["trace_summary"]["gate_zero_fraction"] for row in rows), 8
            ),
        }

    zero = out["learning_none_zero_baseline"]
    corrected = out["learning_none_calibrated_baseline"]
    frozen = out["frozen_none_zero_baseline"]
    out["descriptive_contrasts"] = {
        "corrected_minus_zero_memory_changed_steps": round(
            corrected["mean_memory_changed_steps"] - zero["mean_memory_changed_steps"],
            8,
        ),
        "absolute_efficacy_drift_reduction": round(
            abs(zero["mean_final_efficacy_delta"])
            - abs(corrected["mean_final_efficacy_delta"]),
            12,
        ),
        "corrected_minus_zero_eval_reward": round(
            corrected["mean_eval_reward"] - zero["mean_eval_reward"], 8
        ),
        "corrected_minus_frozen_eval_reward": round(
            corrected["mean_eval_reward"] - frozen["mean_eval_reward"], 8
        ),
    }
    return out


def run_dan_baseline_intervention(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("DAN baseline intervention config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)

    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha_before = _sha256_file(base_checkpoint)
    calibration = _estimate_task_conditioned_dan_baseline(
        base_checkpoint=base_checkpoint
    )
    baseline_hz = list(calibration["values_hz"])

    replicate_results = []
    for replicate_id, train_seed, heldout in EXPECTED_REPLICATES:
        rep_dir = output_dir / replicate_id
        rep_dir.mkdir(parents=True, exist_ok=True)
        arm_results = {}
        for name, learning, _reinforcement_mode, baseline_mode in EXPECTED_ARMS:
            arm_results[name] = _run_arm(
                name=name,
                learning=bool(learning),
                baseline_mode=str(baseline_mode),
                baseline_hz=baseline_hz,
                base_checkpoint=base_checkpoint,
                arm_checkpoint=rep_dir / f"{name}.npz",
                train_seed=train_seed,
                held_out_seeds=heldout,
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
    expected_baseline_digest = calibration["digest"]

    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "calibration_real_malecns_and_frozen": all(
            item["neural_activity_verified"] is True
            and set(item["delivered_reinforcement"]) <= {"none"}
            and item["source_checkpoint_sha256"] == source_sha_before
            for item in calibration["seed_results"]
        ),
        "calibration_baseline_finite_nonnegative": (
            calibration["dan_count"] == len(baseline_hz)
            and calibration["nonzero_cells"] > 0
            and all(math.isfinite(float(value)) and float(value) >= 0 for value in baseline_hz)
        ),
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
        "all_external_reinforcement_suppressed": all(
            set(arm["evaluation"]["per_seed"][0]["delivered_reinforcement"]) <= {"none"}
            and set(arm["evaluation"]["per_seed"][1]["delivered_reinforcement"]) <= {"none"}
            for rep in replicate_results
            for arm in rep["arm_results"].values()
        ),
        "corrected_baseline_applied_exactly": all(
            rep["arm_results"]["learning_none_calibrated_baseline"][
                "dan_baseline_digest"
            ]
            == expected_baseline_digest
            for rep in replicate_results
        ),
        "zero_baseline_arms_zero_exactly": all(
            rep["arm_results"][name]["dan_baseline_digest"]
            == _baseline_digest([0.0] * calibration["dan_count"])
            for rep in replicate_results
            for name in (
                "learning_none_zero_baseline",
                "frozen_none_zero_baseline",
            )
        ),
        "checkpoint_memory_roundtrip_exact": all(
            arm["checkpoint_memory_roundtrip_exact"]
            for rep in replicate_results
            for arm in rep["arm_results"].values()
        ),
        "frozen_memory_unchanged": all(
            rep["arm_results"]["frozen_none_zero_baseline"]["final_memory"]["sha256"]
            == rep["arm_results"]["frozen_none_zero_baseline"]["initial_memory"]["sha256"]
            and rep["arm_results"]["frozen_none_zero_baseline"]["trace_summary"][
                "memory_changed_steps"
            ]
            == 0
            for rep in replicate_results
        ),
        "evaluation_frozen_and_reinforcement_disabled": all(
            arm["evaluation"]["learning"] is False
            and arm["evaluation"]["reinforcement_mode"] == "none"
            and all(
                set(seed_result["delivered_reinforcement"]) <= {"none"}
                for seed_result in arm["evaluation"]["per_seed"]
            )
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
            "EXPLORATORY_INTERVENTION_COMPLETE"
            if execution_valid
            else "INVALID_EXECUTION"
        ),
        "scope": SCOPE,
        "execution_valid": execution_valid,
        "config_gates": config_gates,
        "evidence_gates": evidence_gates,
        "source_checkpoint_sha256": source_sha_before,
        "source_checkpoint_sha256_after": source_sha_after,
        "calibration": calibration,
        "replicates": replicate_results,
        "aggregate": _aggregate(replicate_results),
        "learning_validated": False,
        "task_conditioned_dan_baseline_causal": False,
        "biological_dan_resting_rate_established": False,
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
        description="Run exploratory task-conditioned DAN baseline intervention"
    )
    parser.add_argument(
        "--config",
        default="data/dan_baseline_intervention_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_dan_baseline_intervention(
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
                "calibration": {
                    "digest": result["calibration"]["digest"],
                    "dan_count": result["calibration"]["dan_count"],
                    "mean_reward_cell_baseline_hz": result["calibration"][
                        "mean_reward_cell_baseline_hz"
                    ],
                    "mean_aversive_cell_baseline_hz": result["calibration"][
                        "mean_aversive_cell_baseline_hz"
                    ],
                },
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
