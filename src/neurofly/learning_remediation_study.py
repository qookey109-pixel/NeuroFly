from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Any

from .goal_training import GoalMazeEnvironment
from .learning_control_study import (
    EXPECTED_ARMS,
    _evaluate_arm,
    _run_training_arm,
    _sha256_file,
    descriptive_effects,
)
from .smoke import _digest_json


CONFIG_SCHEMA = "neurofly-learning-remediation-study-v0.1"
RECEIPT_SCHEMA = "neurofly-learning-remediation-study-receipt-v0.1"
STATUS = "EXPLORATORY_ONLY"
SCOPE = "real-malecns-seed-effectiveness-remediation"

EXPECTED_TRAINING_STEPS = 60
EXPECTED_EVAL_STEPS = 20
EXPECTED_SEED_PROBE_STEPS = 12
EXPECTED_REPLICATES = (
    ("E1", 1201, (1301, 1303)),
    ("E2", 1213, (1307, 1319)),
    ("E3", 1217, (1321, 1327)),
    ("E4", 1223, (1361, 1367)),
)
V01_USED_SEEDS = {
    109,
    701,
    709,
    719,
    211,
    223,
    227,
    229,
    233,
    239,
    241,
    251,
    1009,
    1013,
    1019,
    1021,
    1031,
    1033,
    1039,
    1049,
    1051,
    1061,
    1063,
    1069,
    1087,
    1091,
    1093,
    1097,
    1103,
    1109,
    1117,
    1123,
    1129,
    1151,
    1153,
    1163,
}


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
    world = config.get("world_mode") or {}
    claims = config.get("claim_policy") or {}
    origin = config.get("design_origin") or {}
    configured = [
        seed
        for _, training_seed, heldout in EXPECTED_REPLICATES
        for seed in (training_seed, *heldout)
    ]
    expected_arms = [
        {
            "name": name,
            "learning": learning,
            "sensory_mode": sensory,
            "reinforcement_mode": reinforcement,
        }
        for name, learning, sensory, reinforcement in EXPECTED_ARMS
    ]
    return {
        "schema_exact": config.get("schema") == CONFIG_SCHEMA,
        "status_exact": config.get("status") == STATUS,
        "scope_exact": config.get("scope") == SCOPE,
        "origin_frozen": (
            origin.get("confirmatory_run_id") == 35323343414
            and origin.get("confirmatory_receipt_sha256")
            == "610b28444c8d3481397b6a56500e9f4cd17f66e059ce4c3c9cb73ba9fe636b8c"
            and origin.get("failure_result_preserved") is True
            and origin.get("seed_effectiveness_issue_discovered_post_run") is True
        ),
        "arms_exact": config.get("arms") == expected_arms,
        "training_steps_exact": config.get("training_steps") == EXPECTED_TRAINING_STEPS,
        "evaluation_steps_exact": (
            config.get("evaluation_steps_per_seed") == EXPECTED_EVAL_STEPS
        ),
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": (
            len(configured) == len(set(configured))
            and not (set(configured) & V01_USED_SEEDS)
        ),
        "decision_synchronous_world_exact": (
            world.get("decision_synchronous_world") is True
            and world.get("seed_probe_steps") == EXPECTED_SEED_PROBE_STEPS
            and world.get("require_unique_probe_digest_for_every_configured_seed")
            is True
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims)
            == {
                "learning_validated",
                "within_task_heldout_generalization_supported",
                "causal_learning_claim_authorized",
                "broad_generalization_validated",
                "behavioral_promotion_authorized",
                "replacement_confirmatory_authorized",
            }
            and all(value is False for value in claims.values())
        ),
    }


def seed_probe(seed: int, *, steps: int = EXPECTED_SEED_PROBE_STEPS) -> dict[str, Any]:
    env = GoalMazeEnvironment(seed=int(seed))
    trace = []
    for index in range(int(steps)):
        result = env.agent_step("HOLD", move_enemies=True)
        trace.append(
            {
                "index": index,
                "episode": env.episode,
                "enemies": [dict(item) for item in env.enemies],
                "event": result.event,
                "terminal": result.terminal,
            }
        )
        if result.terminal:
            env.reset(result.event or "terminal")
    digest = _digest_json({"trace": trace})
    return {
        "seed": int(seed),
        "steps": int(steps),
        "trace_digest": digest,
        "trace": trace,
    }


def _aggregate_descriptive_effects(
    replicate_results: list[dict[str, Any]],
) -> dict[str, Any]:
    controls = (
        "frozen_true",
        "learning_scrambled",
        "learning_sensory_off",
    )
    metrics = (
        "mean_total_reward",
        "mean_total_clears",
        "mean_total_food",
        "mean_total_deaths",
        "mean_hold_fraction",
    )
    summary: dict[str, Any] = {}
    for control in controls:
        key = f"learning_true_minus_{control}"
        summary[key] = {
            metric: round(
                mean(
                    float(item["descriptive_effects"][key][metric])
                    for item in replicate_results
                ),
                8,
            )
            for metric in metrics
        }
    return summary


def run_learning_remediation_study(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Learning remediation config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)

    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha_before = _sha256_file(base_checkpoint)
    configured_seeds = [
        seed
        for _, training_seed, heldout in EXPECTED_REPLICATES
        for seed in (training_seed, *heldout)
    ]
    probes = {
        str(seed): seed_probe(seed, steps=EXPECTED_SEED_PROBE_STEPS)
        for seed in configured_seeds
    }
    probe_digests = [item["trace_digest"] for item in probes.values()]

    replicate_results: list[dict[str, Any]] = []
    for replicate_index, (replicate_id, training_seed, heldout_seeds) in enumerate(
        EXPECTED_REPLICATES
    ):
        replicate_dir = output_dir / replicate_id
        replicate_dir.mkdir(parents=True, exist_ok=True)
        arm_results: dict[str, Any] = {}
        for arm_index, (name, learning, sensory_mode, reinforcement_mode) in enumerate(
            EXPECTED_ARMS
        ):
            arm_checkpoint = replicate_dir / f"{name}.npz"
            training_result = _run_training_arm(
                arm_name=name,
                learning=bool(learning),
                sensory_mode=str(sensory_mode),
                reinforcement_mode=str(reinforcement_mode),
                initial_checkpoint=base_checkpoint,
                arm_checkpoint=arm_checkpoint,
                train_seed=training_seed,
                train_steps=EXPECTED_TRAINING_STEPS,
                scramble_seed=70_000 + replicate_index * 100 + arm_index,
                decision_synchronous_world=True,
            )
            arm_results[name] = {
                "training": training_result,
                "evaluation": _evaluate_arm(
                    arm_checkpoint=arm_checkpoint,
                    held_out_seeds=heldout_seeds,
                    eval_steps=EXPECTED_EVAL_STEPS,
                    decision_synchronous_world=True,
                ),
            }
        replicate_results.append(
            {
                "replicate_id": replicate_id,
                "training_seed": training_seed,
                "held_out_seeds": list(heldout_seeds),
                "arm_results": arm_results,
                "descriptive_effects": descriptive_effects(arm_results),
            }
        )

    source_sha_after = _sha256_file(base_checkpoint)
    arm_paths = [
        arm["training"]["arm_checkpoint_path"]
        for replicate in replicate_results
        for arm in replicate["arm_results"].values()
    ]

    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "all_replicates_executed": (
            len(replicate_results) == len(EXPECTED_REPLICATES)
            and tuple(item["replicate_id"] for item in replicate_results)
            == tuple(item[0] for item in EXPECTED_REPLICATES)
        ),
        "all_arms_start_from_source_checkpoint": all(
            arm["training"]["initial_checkpoint_sha256"] == source_sha_before
            for replicate in replicate_results
            for arm in replicate["arm_results"].values()
        ),
        "all_arm_checkpoints_isolated": (
            len(arm_paths) == len(set(arm_paths))
            and all(
                Path(path).resolve() != base_checkpoint.resolve()
                for path in arm_paths
            )
        ),
        "training_real_malecns_verified": all(
            arm["training"]["training_metrics"]["neural_activity_verified"]
            for replicate in replicate_results
            for arm in replicate["arm_results"].values()
        ),
        "evaluation_real_malecns_verified": all(
            seed_result["metrics"]["neural_activity_verified"]
            for replicate in replicate_results
            for arm in replicate["arm_results"].values()
            for seed_result in arm["evaluation"]["per_seed"]
        ),
        "evaluation_learning_disabled": all(
            arm["evaluation"]["learning"] is False
            for replicate in replicate_results
            for arm in replicate["arm_results"].values()
        ),
        "evaluation_reinforcement_disabled": all(
            arm["evaluation"]["reinforcement_mode"] == "none"
            and all(
                set(seed_result["delivered_reinforcement"]) <= {"none"}
                for seed_result in arm["evaluation"]["per_seed"]
            )
            for replicate in replicate_results
            for arm in replicate["arm_results"].values()
        ),
        "evaluation_normal_sensory_restored": all(
            arm["evaluation"]["sensory_mode"] == "normal"
            for replicate in replicate_results
            for arm in replicate["arm_results"].values()
        ),
        "decision_synchronous_world_used": True,
        "all_configured_seed_probes_unique": (
            len(probe_digests) == len(set(probe_digests))
        ),
        "claims_remain_locked": all(
            value is False for value in config["claim_policy"].values()
        ),
    }
    execution_valid = all(config_gates.values()) and all(evidence_gates.values())

    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": (
            "EXPLORATORY_REMEDIATION_COMPLETE"
            if execution_valid
            else "INVALID_EXECUTION"
        ),
        "scope": SCOPE,
        "execution_valid": execution_valid,
        "config_gates": config_gates,
        "evidence_gates": evidence_gates,
        "source_checkpoint_sha256": source_sha_before,
        "source_checkpoint_sha256_after": source_sha_after,
        "seed_probes": probes,
        "replicates": replicate_results,
        "aggregate_descriptive_effects": _aggregate_descriptive_effects(
            replicate_results
        ),
        "learning_validated": False,
        "within_task_heldout_generalization_supported": False,
        "causal_learning_claim_authorized": False,
        "broad_generalization_validated": False,
        "behavioral_promotion_authorized": False,
        "replacement_confirmatory_authorized": False,
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
        description="Run exploratory NeuroFly learning seed-effectiveness remediation"
    )
    parser.add_argument(
        "--config",
        default="data/learning_remediation_study_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_learning_remediation_study(
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
                "aggregate_descriptive_effects": result[
                    "aggregate_descriptive_effects"
                ],
                "receipt_sha256": result["receipt_sha256"],
                "learning_validated": result["learning_validated"],
                "replacement_confirmatory_authorized": result[
                    "replacement_confirmatory_authorized"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["execution_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
