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

from .brain_runtime import BrainDecision, MaleCNSBrain
from .dan_baseline_intervention import _baseline_digest, _memory_snapshot
from .dan_trace_recentering_intervention import (
    BASELINE_DIGEST,
    BASELINE_HZ,
    _configure_source_state,
)
from .external_reinforcement_increment import (
    EXPECTED_REPLICATES as EXTERNAL_INCREMENT_REPLICATES,
    PREVIOUS_SEEDS,
)
from .goal_training import GoalMazeEnvironment, GoalMazeSession
from .learning_control_study import _sha256_file
from .smoke import _digest_json, _neural_decision_verified


CONFIG_SCHEMA = "neurofly-full-network-reinforcement-pulse-replay-v0.1"
RECEIPT_SCHEMA = "neurofly-full-network-reinforcement-pulse-replay-receipt-v0.1"
STATUS = "EXPLORATORY_INTERVENTION_ONLY"
SCOPE = "real-malecns-fixed-sensory-trajectory-full-network-reinforcement-pulse"

EXPECTED_DECISIONS = 60
EXPECTED_CONDITIONS = (
    ("endogenous_only", "none"),
    ("true_external", "recorded_true_task_signal"),
)
EXPECTED_REPLICATES = (
    ("P1", 2141),
    ("P2", 2143),
    ("P3", 2153),
    ("P4", 2161),
)
ORIGIN_RUN_ID = 35426688269
ORIGIN_RECEIPT = "d0f685da13ebcfc805fb954bfd4567d9d41b86932649d31635f5d6c436f63a2f"
ORIGIN_ARTIFACT_DIGEST = "sha256:5870157934a95b89bb1a2f5ec249b49d3dfbbf1d7875161df057108e4fdcecf8"
USED_SEEDS = set(PREVIOUS_SEEDS) | {seed for _, seed in EXTERNAL_INCREMENT_REPLICATES}


def _normalized_conditions(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (item.get("name"), item.get("full_network_reinforcement"))
        for item in (config.get("conditions") or [])
        if isinstance(item, dict)
    )


def _normalized_replicates(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (item.get("id"), item.get("trajectory_seed"))
        for item in (config.get("replicates") or [])
        if isinstance(item, dict)
    )


def validate_config(config: dict[str, Any]) -> dict[str, bool]:
    origin = config.get("origin") or {}
    runtime = config.get("runtime") or {}
    claims = config.get("claim_policy") or {}
    seeds = [seed for _, seed in EXPECTED_REPLICATES]
    return {
        "schema_exact": config.get("schema") == CONFIG_SCHEMA,
        "status_exact": config.get("status") == STATUS,
        "scope_exact": config.get("scope") == SCOPE,
        "origin_exact": (
            origin.get("external_increment_run_id") == ORIGIN_RUN_ID
            and origin.get("external_increment_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("external_increment_artifact_digest") == ORIGIN_ARTIFACT_DIGEST
            and origin.get("baseline_digest") == BASELINE_DIGEST
        ),
        "runtime_exact": (
            runtime.get("decision_synchronous_world") is True
            and runtime.get("decisions_per_replicate") == EXPECTED_DECISIONS
            and runtime.get("neural_ms_per_decision") == 50
            and runtime.get("pulse_ms") == 20
            and runtime.get("pulse_current") == 20.0
            and runtime.get("trajectory_driver_learning") is False
            and runtime.get("trajectory_driver_external_reinforcement") == "none"
            and runtime.get("replay_learning") is True
            and runtime.get("baseline_mode") == "calibrated"
            and runtime.get("trace_state_mode") == "subtract_baseline"
        ),
        "conditions_exact": _normalized_conditions(config) == EXPECTED_CONDITIONS,
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": len(seeds) == len(set(seeds)) and not (set(seeds) & USED_SEEDS),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ()) == (
            "external_reinforced_decisions",
            "true_minus_endogenous_final_mean_efficacy_delta",
            "reward_event_mean_reward_spike_increment",
            "aversive_event_mean_aversive_spike_increment",
            "paired_action_divergence_fraction",
            "trajectory_driver_frozen_memory_delta",
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims) == {
                "learning_validated",
                "full_network_reinforcement_pulse_causal",
                "temporal_credit_defect_confirmed",
                "causal_learning_claim_authorized",
                "replacement_confirmatory_authorized",
                "behavioral_promotion_authorized",
            }
            and all(value is False for value in claims.values())
        ),
    }


def _frame_sha256(frame: Any) -> str:
    import numpy as np

    array = np.asarray(frame, dtype=np.uint8)
    return hashlib.sha256(array.tobytes()).hexdigest()


class FixedTrajectoryRecorder:
    """Record exact sensory inputs while suppressing reinforcement in the driver."""

    name = "malecns"

    def __init__(self, inner: MaleCNSBrain) -> None:
        self.inner = inner
        self.rows: list[dict[str, Any]] = []
        self.delivered_to_driver = Counter()

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision:
        import numpy as np

        if reinforcement not in {"none", "reward", "aversive"}:
            raise ValueError(reinforcement)
        frame_copy = np.asarray(frame, dtype=np.uint8).copy()
        context_copy = copy.deepcopy(context)
        decision = self.inner.decide(frame_copy, "none", context=context_copy)
        self.delivered_to_driver["none"] += 1
        self.rows.append(
            {
                "frame": frame_copy,
                "context": context_copy,
                "true_reinforcement": reinforcement,
                "driver_action": decision.action,
                "driver_telemetry": copy.deepcopy(decision.telemetry),
            }
        )
        return decision

    def save(self, path: str | Path) -> None:
        self.inner.save(path)


def _trajectory_receipt_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "decision_index": i,
            "frame_sha256": _frame_sha256(row["frame"]),
            "context_sha256": _digest_json(row["context"]),
            "true_reinforcement": row["true_reinforcement"],
            "driver_action": row["driver_action"],
        }
        for i, row in enumerate(rows)
    ]


def _record_trajectory(
    *,
    base_checkpoint: Path,
    driver_checkpoint: Path,
    trajectory_seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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

    states = []
    for _ in range(EXPECTED_DECISIONS):
        state = session.tick()
        if not _neural_decision_verified(state):
            raise RuntimeError("Trajectory driver lacks verifiable neural activity")
        states.append(
            {
                "action": str(state.get("decision_action") or "UNKNOWN"),
                "task_reward": float(state.get("last_reward") or 0.0),
            }
        )

    final_memory = _memory_snapshot(driver)
    if len(recorder.rows) != EXPECTED_DECISIONS:
        raise RuntimeError("Trajectory recorder decision count mismatch")
    receipt_rows = _trajectory_receipt_rows(recorder.rows)
    reinforcements = Counter(row["true_reinforcement"] for row in recorder.rows)
    report = {
        "decisions": len(recorder.rows),
        "trajectory_digest": _digest_json(receipt_rows),
        "trajectory_receipt_rows": receipt_rows,
        "true_reinforcement_counts": dict(sorted(reinforcements.items())),
        "external_reinforced_decisions": sum(
            value for key, value in reinforcements.items() if key != "none"
        ),
        "driver_delivered_reinforcement": dict(sorted(recorder.delivered_to_driver.items())),
        "driver_initial_memory": initial_memory,
        "driver_final_memory": final_memory,
        "driver_frozen_memory_unchanged": initial_memory["sha256"] == final_memory["sha256"],
        "driver_state_digest": _digest_json(states),
    }
    return recorder.rows, report


def _run_condition(
    *,
    condition: str,
    trajectory: list[dict[str, Any]],
    base_checkpoint: Path,
    checkpoint: Path,
) -> dict[str, Any]:
    if condition not in {"endogenous_only", "true_external"}:
        raise ValueError(condition)
    shutil.copy2(base_checkpoint, checkpoint)
    inner = MaleCNSBrain(checkpoint=checkpoint, learning=True)
    transform = _configure_source_state(
        inner,
        baseline_mode="calibrated",
        trace_state_mode="subtract_baseline",
    )
    inner.brain.weights_frozen = False
    initial_memory = _memory_snapshot(inner)
    initial_u_mean = float(inner.brain.memory_u.mean())
    rows = []

    for decision_index, item in enumerate(trajectory):
        reinforcement = (
            str(item["true_reinforcement"])
            if condition == "true_external"
            else "none"
        )
        before = _memory_snapshot(inner)
        decision = inner.decide(
            item["frame"],
            reinforcement,
            context=copy.deepcopy(item["context"]),
        )
        after = _memory_snapshot(inner)
        telemetry = copy.deepcopy(decision.telemetry)
        rows.append(
            {
                "decision_index": decision_index,
                "reinforcement": reinforcement,
                "action": decision.action,
                "reward_spikes": int(telemetry.get("reward_spikes") or 0),
                "aversive_spikes": int(telemetry.get("aversive_spikes") or 0),
                "kc_spikes": int(telemetry.get("kc_spikes") or 0),
                "total_spikes": int(telemetry.get("total_spikes") or 0),
                "stimulus_ms": float(telemetry.get("stimulus_ms") or 0.0),
                "memory_changed": before["sha256"] != after["sha256"],
                "efficacy_delta": round(
                    after["mean_efficacy"] - before["mean_efficacy"], 12
                ),
            }
        )

    final_memory = _memory_snapshot(inner)
    final_u_mean = float(inner.brain.memory_u.mean())
    inner.save(checkpoint)
    return {
        "condition": condition,
        "trace_transform": transform,
        "initial_memory": initial_memory,
        "final_memory": final_memory,
        "post_replay_checkpoint_sha256": _sha256_file(checkpoint),
        "final_mean_efficacy_delta": round(
            final_memory["mean_efficacy"] - initial_memory["mean_efficacy"], 12
        ),
        "final_mean_u_delta": round(final_u_mean - initial_u_mean, 12),
        "memory_changed_steps": sum(row["memory_changed"] for row in rows),
        "rows": rows,
    }


def _paired_report(
    *,
    trajectory: list[dict[str, Any]],
    endogenous: dict[str, Any],
    true_external: dict[str, Any],
) -> dict[str, Any]:
    reward_spike_deltas = []
    aversive_spike_deltas = []
    action_divergences = 0
    for item, none_row, true_row in zip(
        trajectory, endogenous["rows"], true_external["rows"], strict=True
    ):
        if none_row["action"] != true_row["action"]:
            action_divergences += 1
        reinforcement = item["true_reinforcement"]
        if reinforcement == "reward":
            reward_spike_deltas.append(
                true_row["reward_spikes"] - none_row["reward_spikes"]
            )
        elif reinforcement == "aversive":
            aversive_spike_deltas.append(
                true_row["aversive_spikes"] - none_row["aversive_spikes"]
            )

    return {
        "true_minus_endogenous_final_mean_efficacy_delta": round(
            true_external["final_mean_efficacy_delta"]
            - endogenous["final_mean_efficacy_delta"],
            12,
        ),
        "true_minus_endogenous_final_mean_u_delta": round(
            true_external["final_mean_u_delta"] - endogenous["final_mean_u_delta"],
            12,
        ),
        "reward_event_mean_reward_spike_increment": round(
            mean(reward_spike_deltas), 8
        )
        if reward_spike_deltas
        else 0.0,
        "aversive_event_mean_aversive_spike_increment": round(
            mean(aversive_spike_deltas), 8
        )
        if aversive_spike_deltas
        else 0.0,
        "paired_action_divergence_fraction": round(
            action_divergences / len(trajectory), 8
        ),
        "reward_event_count": len(reward_spike_deltas),
        "aversive_event_count": len(aversive_spike_deltas),
    }


def _run_replicate(
    *,
    replicate_id: str,
    trajectory_seed: int,
    base_checkpoint: Path,
    rep_dir: Path,
) -> dict[str, Any]:
    rep_dir.mkdir(parents=True, exist_ok=True)
    source_sha = _sha256_file(base_checkpoint)
    trajectory, driver = _record_trajectory(
        base_checkpoint=base_checkpoint,
        driver_checkpoint=rep_dir / "trajectory-driver.npz",
        trajectory_seed=trajectory_seed,
    )
    endogenous = _run_condition(
        condition="endogenous_only",
        trajectory=trajectory,
        base_checkpoint=base_checkpoint,
        checkpoint=rep_dir / "endogenous-only.npz",
    )
    true_external = _run_condition(
        condition="true_external",
        trajectory=trajectory,
        base_checkpoint=base_checkpoint,
        checkpoint=rep_dir / "true-external.npz",
    )
    paired = _paired_report(
        trajectory=trajectory,
        endogenous=endogenous,
        true_external=true_external,
    )
    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "source_checkpoint_sha256": source_sha,
        "driver": driver,
        "conditions": {
            "endogenous_only": endogenous,
            "true_external": true_external,
        },
        "paired": paired,
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    e = [rep["conditions"]["endogenous_only"] for rep in replicates]
    t = [rep["conditions"]["true_external"] for rep in replicates]
    p = [rep["paired"] for rep in replicates]
    return {
        "endogenous_only": {
            "mean_final_efficacy_delta": round(
                mean(row["final_mean_efficacy_delta"] for row in e), 12
            ),
            "mean_final_u_delta": round(
                mean(row["final_mean_u_delta"] for row in e), 12
            ),
            "mean_memory_changed_steps": round(
                mean(row["memory_changed_steps"] for row in e), 8
            ),
        },
        "true_external": {
            "mean_final_efficacy_delta": round(
                mean(row["final_mean_efficacy_delta"] for row in t), 12
            ),
            "mean_final_u_delta": round(
                mean(row["final_mean_u_delta"] for row in t), 12
            ),
            "mean_memory_changed_steps": round(
                mean(row["memory_changed_steps"] for row in t), 8
            ),
        },
        "descriptive_contrasts": {
            "mean_external_reinforced_decisions": round(
                mean(rep["driver"]["external_reinforced_decisions"] for rep in replicates),
                8,
            ),
            "true_minus_endogenous_final_mean_efficacy_delta": round(
                mean(row["true_minus_endogenous_final_mean_efficacy_delta"] for row in p),
                12,
            ),
            "true_minus_endogenous_final_mean_u_delta": round(
                mean(row["true_minus_endogenous_final_mean_u_delta"] for row in p),
                12,
            ),
            "reward_event_mean_reward_spike_increment": round(
                mean(row["reward_event_mean_reward_spike_increment"] for row in p), 8
            ),
            "aversive_event_mean_aversive_spike_increment": round(
                mean(row["aversive_event_mean_aversive_spike_increment"] for row in p), 8
            ),
            "paired_action_divergence_fraction": round(
                mean(row["paired_action_divergence_fraction"] for row in p), 8
            ),
        },
    }


def run_full_network_reinforcement_pulse_replay(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Full-network pulse replay config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)
    if _baseline_digest(list(BASELINE_HZ)) != BASELINE_DIGEST:
        raise RuntimeError("Frozen baseline digest mismatch")

    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha_before = _sha256_file(base_checkpoint)
    replicates = [
        _run_replicate(
            replicate_id=replicate_id,
            trajectory_seed=trajectory_seed,
            base_checkpoint=base_checkpoint,
            rep_dir=output_dir / replicate_id,
        )
        for replicate_id, trajectory_seed in EXPECTED_REPLICATES
    ]
    source_sha_after = _sha256_file(base_checkpoint)

    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "all_replicates_executed": len(replicates) == len(EXPECTED_REPLICATES),
        "all_replicates_start_from_source_checkpoint": all(
            rep["source_checkpoint_sha256"] == source_sha_before for rep in replicates
        ),
        "all_decisions_executed": all(
            rep["driver"]["decisions"] == EXPECTED_DECISIONS for rep in replicates
        ),
        "trajectory_driver_frozen_memory_unchanged": all(
            rep["driver"]["driver_frozen_memory_unchanged"] is True for rep in replicates
        ),
        "trajectory_driver_external_reinforcement_suppressed": all(
            set(rep["driver"]["driver_delivered_reinforcement"]) <= {"none"}
            for rep in replicates
        ),
        "at_least_one_true_external_event_observed": all(
            rep["driver"]["external_reinforced_decisions"] > 0 for rep in replicates
        ),
        "paired_fixed_sensory_trajectory": all(
            len(rep["conditions"]["endogenous_only"]["rows"]) == EXPECTED_DECISIONS
            and len(rep["conditions"]["true_external"]["rows"]) == EXPECTED_DECISIONS
            for rep in replicates
        ),
        "true_condition_delivered_recorded_schedule": all(
            sum(
                row["reinforcement"] != "none"
                for row in rep["conditions"]["true_external"]["rows"]
            )
            == rep["driver"]["external_reinforced_decisions"]
            for rep in replicates
        ),
        "endogenous_condition_has_no_external_reinforcement": all(
            all(
                row["reinforcement"] == "none"
                for row in rep["conditions"]["endogenous_only"]["rows"]
            )
            for rep in replicates
        ),
        "frozen_baseline_exact": _baseline_digest(list(BASELINE_HZ)) == BASELINE_DIGEST,
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
        "frozen_baseline_digest": BASELINE_DIGEST,
        "replicates": replicates,
        "aggregate": _aggregate(replicates),
        "learning_validated": False,
        "full_network_reinforcement_pulse_causal": False,
        "temporal_credit_defect_confirmed": False,
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
        description="Replay true task reinforcement through paired full MaleCNS networks on one fixed sensory trajectory"
    )
    parser.add_argument(
        "--config",
        default="data/full_network_reinforcement_pulse_replay_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_full_network_reinforcement_pulse_replay(
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
