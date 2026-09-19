from __future__ import annotations

import argparse
import copy
import json
import shutil
from pathlib import Path
from statistics import mean
from typing import Any

from .brain_runtime import MaleCNSBrain
from .dan_baseline_intervention import (
    _baseline_digest,
    _evaluate_checkpoint,
    _memory_snapshot,
    _restore_arm_brain,
)
from .dan_trace_recentering_intervention import (
    BASELINE_DIGEST,
    BASELINE_HZ,
    _configure_source_state,
)
from .goal_training import GoalMazeEnvironment, GoalMazeSession
from .learning_control_study import ControlledBrain, _sha256_file
from .smoke import _digest_json, _neural_decision_verified


CONFIG_SCHEMA = "neurofly-recentered-reinforcement-discrimination-v0.1"
RECEIPT_SCHEMA = "neurofly-recentered-reinforcement-discrimination-receipt-v0.1"
STATUS = "EXPLORATORY_INTERVENTION_ONLY"
SCOPE = "real-malecns-recentered-reinforcement-discrimination"

EXPECTED_TRAINING_STEPS = 60
EXPECTED_EVAL_STEPS = 20
EXPECTED_ARMS = (
    ("learning_true_recentered", True, "true"),
    ("learning_none_recentered", True, "none"),
    ("learning_scrambled_recentered", True, "scrambled"),
    ("frozen_true_recentered", False, "true"),
)
EXPECTED_REPLICATES = (
    ("Q1", 2003, (2011, 2017)),
    ("Q2", 2027, (2029, 2039)),
    ("Q3", 2053, (2063, 2069)),
    ("Q4", 2081, (2083, 2087)),
)
ORIGIN_COUNTERFACTUAL_RECEIPT = (
    "29f704c07380ac615c6e24566fb6ad14539082ce5521f0d8d1a9aec6b4f12581"
)
PREVIOUS_SEEDS = {
    109, 211, 223, 227, 229, 233, 239, 241, 251,
    701, 709, 719,
    1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051, 1061, 1063,
    1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117, 1123, 1129, 1151, 1153, 1163,
    1201, 1213, 1217, 1223, 1301, 1303, 1307, 1319, 1321, 1327, 1361, 1367,
    1409, 1423, 1427, 1451, 1453, 1459, 1471, 1481, 1483,
    1601, 1607, 1609, 1613, 1619, 1621, 1627, 1637, 1657, 1663, 1667, 1669,
    1693, 1697, 1699, 1709, 1721, 1723,
    1801, 1807, 1811, 1823, 1831, 1847, 1861, 1867, 1871, 1873, 1877, 1879,
    1901, 1907, 1913,
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
    origin = config.get("origin") or {}
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
            origin.get("counterfactual_run_id") == 35417521260
            and origin.get("counterfactual_receipt_sha256")
            == ORIGIN_COUNTERFACTUAL_RECEIPT
            and origin.get("recentering_run_id") == 35415979900
            and origin.get("baseline_digest") == BASELINE_DIGEST
        ),
        "runtime_exact": (
            runtime.get("decision_synchronous_world") is True
            and runtime.get("training_steps") == EXPECTED_TRAINING_STEPS
            and runtime.get("evaluation_steps_per_seed") == EXPECTED_EVAL_STEPS
            and runtime.get("sensory_mode") == "normal"
            and runtime.get("baseline_mode") == "calibrated"
            and runtime.get("trace_state_mode") == "subtract_baseline"
        ),
        "arms_exact": _normalized_arms(config) == EXPECTED_ARMS,
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": (
            len(seeds) == len(set(seeds))
            and not (set(seeds) & PREVIOUS_SEEDS)
        ),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ())
        == (
            "final_mean_efficacy_delta",
            "memory_changed_none_steps",
            "memory_changed_reinforced_steps",
            "evaluation_mean_total_reward",
            "evaluation_mean_hold_fraction",
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims)
            == {
                "learning_validated",
                "true_reinforcement_discriminated",
                "causal_learning_claim_authorized",
                "replacement_confirmatory_authorized",
                "behavioral_promotion_authorized",
                "production_checkpoint_mutated",
            }
            and all(value is False for value in claims.values())
        ),
    }


def _trace_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    none_rows = [row for row in rows if row["delivered_reinforcement"] == "none"]
    reinforced_rows = [
        row for row in rows if row["delivered_reinforcement"] != "none"
    ]
    return {
        "steps": len(rows),
        "memory_changed_steps": sum(row["memory_changed"] for row in rows),
        "memory_changed_none_steps": sum(
            row["memory_changed"] and row["delivered_reinforcement"] == "none"
            for row in rows
        ),
        "memory_changed_reinforced_steps": sum(
            row["memory_changed"] and row["delivered_reinforcement"] != "none"
            for row in rows
        ),
        "none_steps": len(none_rows),
        "reinforced_steps": len(reinforced_rows),
        "mean_efficacy_delta_on_none_steps": round(
            mean(row["efficacy_delta"] for row in none_rows), 12
        )
        if none_rows
        else 0.0,
        "mean_efficacy_delta_on_reinforced_steps": round(
            mean(row["efficacy_delta"] for row in reinforced_rows), 12
        )
        if reinforced_rows
        else 0.0,
        "hold_fraction": round(
            sum(row["action"] == "HOLD" for row in rows) / len(rows), 8
        ),
        "gate_zero_fraction": round(
            sum(row["gate_spikes"] == 0 for row in rows) / len(rows), 8
        ),
    }


def _run_arm(
    *,
    name: str,
    learning: bool,
    reinforcement_mode: str,
    base_checkpoint: Path,
    arm_checkpoint: Path,
    training_seed: int,
    held_out_seeds: tuple[int, ...],
    scramble_seed: int,
) -> dict[str, Any]:
    shutil.copy2(base_checkpoint, arm_checkpoint)
    source_sha = _sha256_file(base_checkpoint)

    inner = MaleCNSBrain(checkpoint=arm_checkpoint, learning=learning)
    transform = _configure_source_state(
        inner,
        baseline_mode="calibrated",
        trace_state_mode="subtract_baseline",
    )
    inner.brain.weights_frozen = not learning

    initial_memory = _memory_snapshot(inner)
    controlled = ControlledBrain(
        inner,
        sensory_mode="normal",
        reinforcement_mode=reinforcement_mode,
        scramble_seed=scramble_seed,
    )
    session = GoalMazeSession(
        controlled,
        environment=GoalMazeEnvironment(seed=training_seed),
        checkpoint=None,
        world_tick_seconds=3600.0,
        decision_synchronous_world=True,
    )

    rows = []
    for step in range(EXPECTED_TRAINING_STEPS):
        before = _memory_snapshot(inner)
        state = session.tick()
        if not _neural_decision_verified(state):
            raise RuntimeError("Reinforcement discrimination decision lacks neural evidence")
        after = _memory_snapshot(inner)
        telemetry = copy.deepcopy(((state.get("brain") or {}).get("telemetry") or {}))
        rows.append(
            {
                "step": step,
                "action": str(state.get("decision_action") or "UNKNOWN"),
                "gate_spikes": int(telemetry.get("gate_spikes") or 0),
                "delivered_reinforcement": str(
                    telemetry.get("reinforcement") or "none"
                ),
                "reward_spikes": int(telemetry.get("reward_spikes") or 0),
                "aversive_spikes": int(telemetry.get("aversive_spikes") or 0),
                "memory_changed": before["sha256"] != after["sha256"],
                "efficacy_delta": round(
                    after["mean_efficacy"] - before["mean_efficacy"], 12
                ),
            }
        )

    final_memory = _memory_snapshot(inner)
    controlled.save(arm_checkpoint)
    checkpoint_sha = _sha256_file(arm_checkpoint)

    restored = _restore_arm_brain(
        checkpoint=arm_checkpoint,
        learning=False,
        baseline_hz=list(BASELINE_HZ),
        checkpoint_is_source_zero_baseline=False,
    )
    restored_memory = _memory_snapshot(restored)

    evaluation = _evaluate_checkpoint(
        arm_checkpoint=arm_checkpoint,
        baseline_hz=list(BASELINE_HZ),
        held_out_seeds=held_out_seeds,
    )

    return {
        "arm": name,
        "learning": learning,
        "reinforcement_mode": reinforcement_mode,
        "initial_checkpoint_sha256": source_sha,
        "post_training_checkpoint_sha256": checkpoint_sha,
        "baseline_digest": _baseline_digest(
            [float(value) for value in inner.brain.dan_baseline_hz]
        ),
        "trace_transform": transform,
        "initial_memory": initial_memory,
        "final_memory": final_memory,
        "restored_memory": restored_memory,
        "checkpoint_memory_roundtrip_exact": final_memory == restored_memory,
        "training_delivered_reinforcement": dict(
            sorted(controlled.delivered_reinforcement.items())
        ),
        "trace_summary": _trace_summary(rows),
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
            "mean_final_efficacy_delta": round(
                mean(row["final_mean_efficacy_delta"] for row in rows), 12
            ),
            "mean_memory_changed_steps": round(
                mean(row["trace_summary"]["memory_changed_steps"] for row in rows), 8
            ),
            "mean_memory_changed_none_steps": round(
                mean(
                    row["trace_summary"]["memory_changed_none_steps"]
                    for row in rows
                ),
                8,
            ),
            "mean_memory_changed_reinforced_steps": round(
                mean(
                    row["trace_summary"]["memory_changed_reinforced_steps"]
                    for row in rows
                ),
                8,
            ),
            "mean_eval_reward": round(
                mean(
                    row["evaluation"]["aggregate"]["mean_total_reward"]
                    for row in rows
                ),
                8,
            ),
            "mean_eval_hold_fraction": round(
                mean(
                    row["evaluation"]["aggregate"]["mean_hold_fraction"]
                    for row in rows
                ),
                8,
            ),
            "mean_training_hold_fraction": round(
                mean(row["trace_summary"]["hold_fraction"] for row in rows), 8
            ),
            "mean_gate_zero_fraction": round(
                mean(row["trace_summary"]["gate_zero_fraction"] for row in rows), 8
            ),
        }

    t = out["learning_true_recentered"]
    n = out["learning_none_recentered"]
    s = out["learning_scrambled_recentered"]
    f = out["frozen_true_recentered"]
    out["descriptive_contrasts"] = {
        "true_minus_none_eval_reward": round(
            t["mean_eval_reward"] - n["mean_eval_reward"], 8
        ),
        "true_minus_scrambled_eval_reward": round(
            t["mean_eval_reward"] - s["mean_eval_reward"], 8
        ),
        "true_minus_frozen_eval_reward": round(
            t["mean_eval_reward"] - f["mean_eval_reward"], 8
        ),
        "true_minus_none_final_efficacy_delta": round(
            t["mean_final_efficacy_delta"] - n["mean_final_efficacy_delta"], 12
        ),
        "true_minus_scrambled_final_efficacy_delta": round(
            t["mean_final_efficacy_delta"] - s["mean_final_efficacy_delta"], 12
        ),
    }
    return out


def run_recentered_reinforcement_discrimination(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Recentered reinforcement config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)
    if _baseline_digest(list(BASELINE_HZ)) != BASELINE_DIGEST:
        raise RuntimeError("Frozen baseline digest mismatch")

    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha_before = _sha256_file(base_checkpoint)
    replicates = []

    for rep_index, (replicate_id, training_seed, heldout) in enumerate(
        EXPECTED_REPLICATES
    ):
        rep_dir = output_dir / replicate_id
        rep_dir.mkdir(parents=True, exist_ok=True)
        arm_results = {}
        for arm_index, (name, learning, reinforcement_mode) in enumerate(
            EXPECTED_ARMS
        ):
            arm_results[name] = _run_arm(
                name=name,
                learning=bool(learning),
                reinforcement_mode=str(reinforcement_mode),
                base_checkpoint=base_checkpoint,
                arm_checkpoint=rep_dir / f"{name}.npz",
                training_seed=training_seed,
                held_out_seeds=heldout,
                scramble_seed=90_000 + rep_index * 100 + arm_index,
            )
        replicates.append(
            {
                "replicate_id": replicate_id,
                "training_seed": training_seed,
                "held_out_seeds": list(heldout),
                "arm_results": arm_results,
            }
        )

    source_sha_after = _sha256_file(base_checkpoint)
    learning_names = {
        "learning_true_recentered",
        "learning_none_recentered",
        "learning_scrambled_recentered",
    }
    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "all_replicates_executed": len(replicates) == len(EXPECTED_REPLICATES),
        "all_arms_start_from_source_checkpoint": all(
            arm["initial_checkpoint_sha256"] == source_sha_before
            for rep in replicates
            for arm in rep["arm_results"].values()
        ),
        "calibrated_baseline_exact": all(
            arm["baseline_digest"] == BASELINE_DIGEST
            for rep in replicates
            for arm in rep["arm_results"].values()
        ),
        "recenter_transform_exact": all(
            arm["trace_transform"]["max_abs_transform_error_hz"] == 0.0
            for rep in replicates
            for arm in rep["arm_results"].values()
        ),
        "learning_none_external_reinforcement_suppressed": all(
            set(
                rep["arm_results"]["learning_none_recentered"][
                    "training_delivered_reinforcement"
                ]
            )
            <= {"none"}
            for rep in replicates
        ),
        "true_reinforcement_uses_task_signal": all(
            rep["arm_results"]["learning_true_recentered"]["reinforcement_mode"]
            == "true"
            and rep["arm_results"]["frozen_true_recentered"]["reinforcement_mode"]
            == "true"
            for rep in replicates
        ),
        "scrambled_reinforcement_enabled": all(
            rep["arm_results"]["learning_scrambled_recentered"][
                "reinforcement_mode"
            ]
            == "scrambled"
            for rep in replicates
        ),
        "learning_arms_memory_may_change": all(
            rep["arm_results"][name]["learning"] is True
            for rep in replicates
            for name in learning_names
        ),
        "frozen_memory_unchanged": all(
            rep["arm_results"]["frozen_true_recentered"]["initial_memory"]["sha256"]
            == rep["arm_results"]["frozen_true_recentered"]["final_memory"]["sha256"]
            and rep["arm_results"]["frozen_true_recentered"]["trace_summary"][
                "memory_changed_steps"
            ]
            == 0
            for rep in replicates
        ),
        "checkpoint_memory_roundtrip_exact": all(
            arm["checkpoint_memory_roundtrip_exact"]
            for rep in replicates
            for arm in rep["arm_results"].values()
        ),
        "evaluation_frozen_normal_and_reinforcement_disabled": all(
            arm["evaluation"]["learning"] is False
            and arm["evaluation"]["sensory_mode"] == "normal"
            and arm["evaluation"]["reinforcement_mode"] == "none"
            for rep in replicates
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
        "frozen_baseline_hz": list(BASELINE_HZ),
        "frozen_baseline_digest": BASELINE_DIGEST,
        "replicates": replicates,
        "aggregate": _aggregate(replicates),
        "learning_validated": False,
        "true_reinforcement_discriminated": False,
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
        description="Compare true, none, scrambled and frozen reinforcement after DAN trace recentering"
    )
    parser.add_argument(
        "--config",
        default="data/recentered_reinforcement_discrimination_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_recentered_reinforcement_discrimination(
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
