from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
from pathlib import Path
from statistics import mean
from typing import Any

from .brain_runtime import MaleCNSBrain
from .dan_baseline_intervention import (
    _baseline_digest,
    _evaluate_checkpoint,
    _memory_snapshot,
)
from .goal_training import GoalMazeEnvironment, GoalMazeSession
from .learning_control_study import ControlledBrain, _sha256_file
from .smoke import _digest_json, _neural_decision_verified


CONFIG_SCHEMA = "neurofly-dan-trace-recentering-intervention-v0.1"
RECEIPT_SCHEMA = "neurofly-dan-trace-recentering-intervention-receipt-v0.1"
STATUS = "EXPLORATORY_INTERVENTION_ONLY"
SCOPE = "real-malecns-dan-trace-state-recentering-intervention"

BASELINE_HZ = (
    0.0, 0.0, 0.11111111, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 123.0, 130.44444444,
)
BASELINE_DIGEST = "1fd69ded16a400e9a00e1265e8264aeafe7d402fa1819fc412df041fa7f205f9"
DIAGNOSTIC_RECEIPT = "9726a534447246c6de42c33a029132d47dcbcfbcb200a25e5e1c52b0d5060456"
INTERVENTION_RECEIPT = "7a679541962dc5cac24b63aeb62a172a71d0875fc9171cc49ac5df29d3eec907"

EXPECTED_TRAINING_STEPS = 60
EXPECTED_EVAL_STEPS = 20
EXPECTED_ARMS = (
    ("learning_none_calibrated_unrecentered", True, "calibrated", "unchanged"),
    ("learning_none_calibrated_recentered", True, "calibrated", "subtract_baseline"),
    ("learning_none_zero_baseline", True, "zero", "unchanged"),
    ("frozen_none_calibrated_recentered", False, "calibrated", "subtract_baseline"),
)
EXPECTED_REPLICATES = (
    ("R1", 1801, (1807, 1811)),
    ("R2", 1823, (1831, 1847)),
    ("R3", 1861, (1867, 1871)),
    ("R4", 1873, (1877, 1879)),
)
PREVIOUS_STUDY_SEEDS = {
    109, 211, 223, 227, 229, 233, 239, 241, 251,
    701, 709, 719,
    1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051, 1061, 1063,
    1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117, 1123, 1129, 1151, 1153, 1163,
    1201, 1213, 1217, 1223, 1301, 1303, 1307, 1319, 1321, 1327, 1361, 1367,
    1409, 1423, 1427, 1451, 1453, 1459, 1471, 1481, 1483,
    1601, 1607, 1609, 1613, 1619, 1621, 1627, 1637, 1657, 1663, 1667, 1669,
    1693, 1697, 1699, 1709, 1721, 1723,
}


def _normalized_arms(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    rows = []
    for item in config.get("arms") or []:
        if not isinstance(item, dict):
            return ()
        rows.append((
            item.get("name"),
            item.get("learning"),
            item.get("baseline_mode"),
            item.get("trace_state_mode"),
        ))
    return tuple(rows)


def _normalized_replicates(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    rows = []
    for item in config.get("replicates") or []:
        if not isinstance(item, dict):
            return ()
        rows.append((
            item.get("id"),
            item.get("training_seed"),
            tuple(item.get("held_out_seeds") or ()),
        ))
    return tuple(rows)


def validate_config(config: dict[str, Any]) -> dict[str, bool]:
    origin = config.get("design_origin") or {}
    baseline = config.get("baseline") or {}
    runtime = config.get("runtime") or {}
    claims = config.get("claim_policy") or {}
    seeds = [
        seed
        for _, training_seed, heldout in EXPECTED_REPLICATES
        for seed in (training_seed, *heldout)
    ]
    return {
        "schema_exact": config.get("schema") == CONFIG_SCHEMA,
        "status_exact": config.get("status") == STATUS,
        "scope_exact": config.get("scope") == SCOPE,
        "origin_exact": (
            origin.get("diagnostic_run_id") == 35413358900
            and origin.get("diagnostic_receipt_sha256") == DIAGNOSTIC_RECEIPT
            and origin.get("intervention_run_id") == 35348834258
            and origin.get("intervention_receipt_sha256") == INTERVENTION_RECEIPT
            and origin.get("observed_initial_aversive_rate_trace_hz") == 165.718050548575
            and origin.get("calibrated_aversive_baseline_hz") == 126.72222222
            and origin.get("observed_trace_minus_baseline_hz") == 38.995828328575
            and origin.get("observed_calibrated_mean_efficacy_delta") == 0.157144904137
        ),
        "baseline_exact": (
            baseline.get("digest") == BASELINE_DIGEST
            and baseline.get("interpretation")
            == "task-conditioned endogenous DAN firing baseline; not a biological resting-rate claim"
            and baseline.get("transform_rule")
            == (
                "For calibrated recentered arms only: after restoring the zero-baseline "
                "source checkpoint, set dan_baseline_hz to the frozen vector and transform "
                "rate_dan := rate_dan - dan_baseline_hz exactly once."
            )
        ),
        "runtime_exact": (
            runtime.get("decision_synchronous_world") is True
            and runtime.get("training_steps") == EXPECTED_TRAINING_STEPS
            and runtime.get("evaluation_steps_per_seed") == EXPECTED_EVAL_STEPS
            and runtime.get("reinforcement_mode") == "none"
            and runtime.get("sensory_mode") == "normal"
        ),
        "arms_exact": _normalized_arms(config) == EXPECTED_ARMS,
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": (
            len(seeds) == len(set(seeds))
            and not (set(seeds) & PREVIOUS_STUDY_SEEDS)
        ),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ())
        == (
            "memory_changed_steps",
            "final_mean_efficacy_delta",
            "first_5_step_mean_efficacy_delta",
            "evaluation_mean_total_reward",
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims)
            == {
                "learning_validated",
                "dan_trace_state_mismatch_causal",
                "trace_recentering_remediation_validated",
                "kc_dan_temporal_drive_causal",
                "causal_learning_claim_authorized",
                "replacement_confirmatory_authorized",
                "behavioral_promotion_authorized",
            }
            and all(value is False for value in claims.values())
        ),
    }


def _array_digest(values: Any) -> str:
    return _digest_json([round(float(x), 8) for x in values])


def _trace_state_summary(inner: MaleCNSBrain) -> dict[str, Any]:
    reward_count = len(inner.brain.circuit["reward"])
    values = inner.brain.rate_dan
    baseline = inner.brain.dan_baseline_hz
    return {
        "rate_dan_digest": _array_digest(values),
        "baseline_digest": _array_digest(baseline),
        "reward_rate_dan_mean_hz": round(float(values[:reward_count].mean()), 12),
        "aversive_rate_dan_mean_hz": round(float(values[reward_count:].mean()), 12),
        "reward_baseline_mean_hz": round(float(baseline[:reward_count].mean()), 12),
        "aversive_baseline_mean_hz": round(float(baseline[reward_count:].mean()), 12),
    }


def _configure_source_state(
    inner: MaleCNSBrain,
    *,
    baseline_mode: str,
    trace_state_mode: str,
) -> dict[str, Any]:
    import numpy as np

    before = inner.brain.rate_dan.copy()
    if baseline_mode == "zero":
        inner.brain.dan_baseline_hz[:] = 0.0
    elif baseline_mode == "calibrated":
        baseline = np.asarray(BASELINE_HZ, dtype=np.float64)
        if baseline.shape != inner.brain.dan_baseline_hz.shape:
            raise RuntimeError("Frozen DAN baseline shape mismatch")
        inner.brain.dan_baseline_hz[:] = baseline
    else:
        raise ValueError("Unknown baseline mode")

    if trace_state_mode == "unchanged":
        pass
    elif trace_state_mode == "subtract_baseline":
        inner.brain.rate_dan[:] = before - inner.brain.dan_baseline_hz
    else:
        raise ValueError("Unknown trace state mode")

    expected = (
        before
        if trace_state_mode == "unchanged"
        else before - inner.brain.dan_baseline_hz
    )
    error = float(np.max(np.abs(inner.brain.rate_dan - expected)))
    return {
        "before": {
            "digest": _array_digest(before),
            "reward_mean_hz": round(float(before[:15].mean()), 12),
            "aversive_mean_hz": round(float(before[15:].mean()), 12),
        },
        "after": _trace_state_summary(inner),
        "max_abs_transform_error_hz": round(error, 12),
    }


def _training_summary(rows: list[dict[str, Any]], initial_efficacy: float) -> dict[str, Any]:
    first = rows[:5]
    return {
        "steps": len(rows),
        "memory_changed_steps": sum(bool(row["memory_changed"]) for row in rows),
        "hold_fraction": round(
            sum(row["action"] == "HOLD" for row in rows) / len(rows), 8
        ),
        "gate_zero_fraction": round(
            sum(int(row["gate_spikes"]) == 0 for row in rows) / len(rows), 8
        ),
        "first_5_step_mean_efficacy_delta": round(
            mean(float(row["mean_efficacy_after"]) - initial_efficacy for row in first),
            12,
        ),
        "last_5_step_mean_efficacy_delta": round(
            mean(float(row["mean_efficacy_after"]) - initial_efficacy for row in rows[-5:]),
            12,
        ),
    }


def _run_arm(
    *,
    name: str,
    learning: bool,
    baseline_mode: str,
    trace_state_mode: str,
    base_checkpoint: Path,
    arm_checkpoint: Path,
    train_seed: int,
    held_out_seeds: tuple[int, ...],
) -> dict[str, Any]:
    shutil.copy2(base_checkpoint, arm_checkpoint)
    source_sha = _sha256_file(base_checkpoint)

    # Restore under the source checkpoint's original zero-baseline provenance.
    inner = MaleCNSBrain(checkpoint=arm_checkpoint, learning=learning)
    transform = _configure_source_state(
        inner,
        baseline_mode=baseline_mode,
        trace_state_mode=trace_state_mode,
    )
    inner.brain.weights_frozen = not learning
    initial_memory = _memory_snapshot(inner)
    initial_trace_state = _trace_state_summary(inner)

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
        before_memory = _memory_snapshot(inner)
        state = session.tick()
        if not _neural_decision_verified(state):
            raise RuntimeError("Trace-recentering decision lacks verifiable neural activity")
        after_memory = _memory_snapshot(inner)
        telemetry = copy.deepcopy(((state.get("brain") or {}).get("telemetry") or {}))
        rows.append({
            "step": step,
            "action": str(state.get("decision_action") or "UNKNOWN"),
            "gate_spikes": int(telemetry.get("gate_spikes") or 0),
            "reward_spikes": int(telemetry.get("reward_spikes") or 0),
            "aversive_spikes": int(telemetry.get("aversive_spikes") or 0),
            "memory_changed": before_memory["sha256"] != after_memory["sha256"],
            "mean_efficacy_after": after_memory["mean_efficacy"],
        })

    if set(controlled.delivered_reinforcement) - {"none"}:
        raise RuntimeError("Trace-recentering arm delivered external reinforcement")

    final_memory = _memory_snapshot(inner)
    controlled.save(arm_checkpoint)
    checkpoint_sha = _sha256_file(arm_checkpoint)

    # Restore with matching baseline provenance. The checkpoint itself carries
    # the transformed rate_dan state when recentering was used.
    restored = MaleCNSBrain(checkpoint=None, learning=False)
    if baseline_mode == "zero":
        restored.brain.dan_baseline_hz[:] = 0.0
    else:
        import numpy as np

        restored.brain.dan_baseline_hz[:] = np.asarray(BASELINE_HZ, dtype=np.float64)
    restored.brain.restore(arm_checkpoint)
    restored.brain.weights_frozen = True
    restored_memory = _memory_snapshot(restored)

    baseline_for_eval = None if baseline_mode == "zero" else list(BASELINE_HZ)
    evaluation = _evaluate_checkpoint(
        arm_checkpoint=arm_checkpoint,
        baseline_hz=baseline_for_eval,
        held_out_seeds=held_out_seeds,
    )

    return {
        "arm": name,
        "learning": learning,
        "baseline_mode": baseline_mode,
        "trace_state_mode": trace_state_mode,
        "initial_checkpoint_sha256": source_sha,
        "post_training_checkpoint_sha256": checkpoint_sha,
        "baseline_digest": _baseline_digest(
            [float(value) for value in inner.brain.dan_baseline_hz]
        ),
        "trace_transform": transform,
        "initial_trace_state": initial_trace_state,
        "initial_memory": initial_memory,
        "final_memory": final_memory,
        "restored_memory": restored_memory,
        "checkpoint_memory_roundtrip_exact": final_memory == restored_memory,
        "training_delivered_reinforcement": dict(
            sorted(controlled.delivered_reinforcement.items())
        ),
        "training_summary": _training_summary(
            rows, float(initial_memory["mean_efficacy"])
        ),
        "final_mean_efficacy_delta": round(
            float(final_memory["mean_efficacy"])
            - float(initial_memory["mean_efficacy"]),
            12,
        ),
        "evaluation": evaluation,
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, *_ in EXPECTED_ARMS:
        rows = [rep["arm_results"][name] for rep in replicates]
        out[name] = {
            "mean_memory_changed_steps": round(
                mean(row["training_summary"]["memory_changed_steps"] for row in rows), 8
            ),
            "mean_first_5_step_efficacy_delta": round(
                mean(
                    row["training_summary"]["first_5_step_mean_efficacy_delta"]
                    for row in rows
                ),
                12,
            ),
            "mean_final_efficacy_delta": round(
                mean(row["final_mean_efficacy_delta"] for row in rows), 12
            ),
            "mean_eval_reward": round(
                mean(
                    row["evaluation"]["aggregate"]["mean_total_reward"]
                    for row in rows
                ),
                8,
            ),
            "mean_training_hold_fraction": round(
                mean(row["training_summary"]["hold_fraction"] for row in rows), 8
            ),
            "mean_gate_zero_fraction": round(
                mean(row["training_summary"]["gate_zero_fraction"] for row in rows), 8
            ),
        }

    legacy = out["learning_none_calibrated_unrecentered"]
    recentered = out["learning_none_calibrated_recentered"]
    zero = out["learning_none_zero_baseline"]
    out["descriptive_contrasts"] = {
        "recentered_minus_unrecentered_final_efficacy_delta": round(
            recentered["mean_final_efficacy_delta"]
            - legacy["mean_final_efficacy_delta"],
            12,
        ),
        "absolute_drift_reduction_vs_unrecentered": round(
            abs(legacy["mean_final_efficacy_delta"])
            - abs(recentered["mean_final_efficacy_delta"]),
            12,
        ),
        "early_drift_reduction_vs_unrecentered": round(
            abs(legacy["mean_first_5_step_efficacy_delta"])
            - abs(recentered["mean_first_5_step_efficacy_delta"]),
            12,
        ),
        "recentered_minus_unrecentered_eval_reward": round(
            recentered["mean_eval_reward"] - legacy["mean_eval_reward"], 8
        ),
        "recentered_minus_zero_final_efficacy_delta": round(
            recentered["mean_final_efficacy_delta"]
            - zero["mean_final_efficacy_delta"],
            12,
        ),
    }
    return out


def run_dan_trace_recentering_intervention(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("DAN trace-recentering config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)
    if _baseline_digest(list(BASELINE_HZ)) != BASELINE_DIGEST:
        raise RuntimeError("Frozen baseline digest mismatch")

    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha_before = _sha256_file(base_checkpoint)
    replicate_results = []

    for replicate_id, train_seed, heldout in EXPECTED_REPLICATES:
        rep_dir = output_dir / replicate_id
        rep_dir.mkdir(parents=True, exist_ok=True)
        arm_results = {}
        for name, learning, baseline_mode, trace_state_mode in EXPECTED_ARMS:
            arm_results[name] = _run_arm(
                name=name,
                learning=bool(learning),
                baseline_mode=str(baseline_mode),
                trace_state_mode=str(trace_state_mode),
                base_checkpoint=base_checkpoint,
                arm_checkpoint=rep_dir / f"{name}.npz",
                train_seed=train_seed,
                held_out_seeds=heldout,
            )
        replicate_results.append({
            "replicate_id": replicate_id,
            "training_seed": train_seed,
            "held_out_seeds": list(heldout),
            "arm_results": arm_results,
        })

    source_sha_after = _sha256_file(base_checkpoint)
    zero_digest = _baseline_digest([0.0] * len(BASELINE_HZ))

    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "all_replicates_executed": len(replicate_results) == len(EXPECTED_REPLICATES),
        "all_arms_start_from_source_checkpoint": all(
            arm["initial_checkpoint_sha256"] == source_sha_before
            for rep in replicate_results
            for arm in rep["arm_results"].values()
        ),
        "all_external_reinforcement_suppressed": all(
            set(arm["training_delivered_reinforcement"]) <= {"none"}
            and all(
                set(seed_result["delivered_reinforcement"]) <= {"none"}
                for seed_result in arm["evaluation"]["per_seed"]
            )
            for rep in replicate_results
            for arm in rep["arm_results"].values()
        ),
        "calibrated_baseline_exact": all(
            rep["arm_results"][name]["baseline_digest"] == BASELINE_DIGEST
            for rep in replicate_results
            for name in (
                "learning_none_calibrated_unrecentered",
                "learning_none_calibrated_recentered",
                "frozen_none_calibrated_recentered",
            )
        ),
        "zero_baseline_exact": all(
            rep["arm_results"]["learning_none_zero_baseline"]["baseline_digest"]
            == zero_digest
            for rep in replicate_results
        ),
        "recenter_transform_exact": all(
            rep["arm_results"][name]["trace_transform"]["max_abs_transform_error_hz"]
            == 0.0
            for rep in replicate_results
            for name in (
                "learning_none_calibrated_recentered",
                "frozen_none_calibrated_recentered",
            )
        ),
        "unrecentered_trace_unchanged": all(
            rep["arm_results"][name]["trace_transform"]["before"]["digest"]
            == rep["arm_results"][name]["trace_transform"]["after"]["rate_dan_digest"]
            for rep in replicate_results
            for name in (
                "learning_none_calibrated_unrecentered",
                "learning_none_zero_baseline",
            )
        ),
        "checkpoint_memory_roundtrip_exact": all(
            arm["checkpoint_memory_roundtrip_exact"]
            for rep in replicate_results
            for arm in rep["arm_results"].values()
        ),
        "frozen_memory_unchanged": all(
            rep["arm_results"]["frozen_none_calibrated_recentered"][
                "training_summary"
            ]["memory_changed_steps"] == 0
            and rep["arm_results"]["frozen_none_calibrated_recentered"][
                "initial_memory"
            ]["sha256"]
            == rep["arm_results"]["frozen_none_calibrated_recentered"][
                "final_memory"
            ]["sha256"]
            for rep in replicate_results
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
        "frozen_baseline_hz": list(BASELINE_HZ),
        "frozen_baseline_digest": BASELINE_DIGEST,
        "replicates": replicate_results,
        "aggregate": _aggregate(replicate_results),
        "learning_validated": False,
        "dan_trace_state_mismatch_causal": False,
        "trace_recentering_remediation_validated": False,
        "kc_dan_temporal_drive_causal": False,
        "causal_learning_claim_authorized": False,
        "replacement_confirmatory_authorized": False,
        "behavioral_promotion_authorized": False,
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
        description="Run exploratory DAN trace-state recentering intervention"
    )
    parser.add_argument(
        "--config",
        default="data/dan_trace_recentering_intervention_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_dan_trace_recentering_intervention(
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
