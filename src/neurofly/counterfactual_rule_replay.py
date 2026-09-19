from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
from contextlib import AbstractContextManager
from pathlib import Path
from statistics import mean
from typing import Any

from .brain_runtime import MaleCNSBrain
from .dan_baseline_intervention import _baseline_digest, _memory_snapshot
from .goal_training import GoalMazeEnvironment, GoalMazeSession
from .learning_control_study import ControlledBrain, _sha256_file
from .smoke import _digest_json, _neural_decision_verified


CONFIG_SCHEMA = "neurofly-counterfactual-rule-replay-diagnostic-v0.1"
RECEIPT_SCHEMA = "neurofly-counterfactual-rule-replay-diagnostic-receipt-v0.1"
STATUS = "EXPLORATORY_DIAGNOSTIC_ONLY"
SCOPE = "real-malecns-frozen-trajectory-counterfactual-plasticity-replay"

EXPECTED_DECISIONS = 60
EXPECTED_BINS_PER_DECISION = 5
EXPECTED_RATE_BIN_MS = 10
EXPECTED_REPLAYS = (
    ("zero_baseline", "zero", "unchanged"),
    ("calibrated_unrecentered", "calibrated", "unchanged"),
    ("calibrated_recentered", "calibrated", "subtract_baseline"),
)
EXPECTED_REPLICATES = (
    ("C1", 1901),
    ("C2", 1907),
    ("C3", 1913),
)
BASELINE_HZ = (
    0.0, 0.0, 0.11111111, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 123.0, 130.44444444,
)
BASELINE_DIGEST = "1fd69ded16a400e9a00e1265e8264aeafe7d402fa1819fc412df041fa7f205f9"
ORIGIN_RECEIPT = "e31b82a1649ee9c4e8d3ac584fc2910d1152f5980ba75116392894184576a589"
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
}


def _normalized_replays(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    rows = []
    for item in config.get("replay_conditions") or []:
        if not isinstance(item, dict):
            return ()
        rows.append(
            (
                item.get("name"),
                item.get("baseline_mode"),
                item.get("trace_state_mode"),
            )
        )
    return tuple(rows)


def _normalized_replicates(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    rows = []
    for item in config.get("replicates") or []:
        if not isinstance(item, dict):
            return ()
        rows.append((item.get("id"), item.get("trajectory_seed")))
    return tuple(rows)


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
            origin.get("recentering_run_id") == 35415979900
            and origin.get("recentering_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("baseline_digest") == BASELINE_DIGEST
        ),
        "runtime_exact": (
            runtime.get("decision_synchronous_world") is True
            and runtime.get("decisions_per_replicate") == EXPECTED_DECISIONS
            and runtime.get("neural_ms_per_decision") == 50
            and runtime.get("rate_bin_ms") == EXPECTED_RATE_BIN_MS
            and runtime.get("expected_bins_per_decision") == EXPECTED_BINS_PER_DECISION
            and runtime.get("external_reinforcement") == "none"
            and runtime.get("neural_weights_frozen") is True
        ),
        "replays_exact": _normalized_replays(config) == EXPECTED_REPLAYS,
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": len(seeds) == len(set(seeds)) and not (set(seeds) & PREVIOUS_SEEDS),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ())
        == (
            "first_5_decision_mean_efficacy_delta",
            "final_mean_efficacy_delta",
            "mean_aversive_net_drive",
            "mean_reward_net_drive",
            "live_frozen_memory_delta",
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims)
            == {
                "learning_validated",
                "dan_trace_state_mismatch_causal",
                "trace_recentering_remediation_validated",
                "baseline_shift_rule_effect_causal",
                "kc_dan_temporal_drive_causal",
                "causal_learning_claim_authorized",
                "replacement_confirmatory_authorized",
                "behavioral_promotion_authorized",
            }
            and all(value is False for value in claims.values())
        ),
    }


def _summary(values: Any) -> dict[str, float]:
    import numpy as np

    a = np.asarray(values, dtype=np.float64)
    return {
        "mean": round(float(a.mean()), 12),
        "mean_abs": round(float(np.abs(a).mean()), 12),
        "minimum": round(float(a.min()), 12),
        "maximum": round(float(a.max()), 12),
    }


class CounterfactualReplayTracer(AbstractContextManager["CounterfactualReplayTracer"]):
    def __init__(self, inner: MaleCNSBrain) -> None:
        import numpy as np

        brain = inner.brain
        if len(brain.circuit["reward"]) != 15 or len(brain.circuit["aversive"]) != 2:
            raise RuntimeError("Unexpected DAN compartment counts")
        baseline = np.asarray(BASELINE_HZ, dtype=np.float64)
        if baseline.shape != brain.rate_dan.shape:
            raise RuntimeError("Frozen baseline shape mismatch")

        self.reward_count = len(brain.circuit["reward"])
        self.initial_w = brain.memory_w.copy()
        self.initial_u = brain.memory_u.copy()
        self.baseline = baseline
        self.conditions: dict[str, dict[str, Any]] = {}
        for name, baseline_mode, trace_mode in EXPECTED_REPLAYS:
            y_dan = brain.rate_dan.copy()
            condition_baseline = (
                np.zeros_like(baseline)
                if baseline_mode == "zero"
                else baseline.copy()
            )
            if trace_mode == "subtract_baseline":
                y_dan = y_dan - condition_baseline
            self.conditions[name] = {
                "baseline": condition_baseline,
                "y_kc": brain.rate_kc.copy(),
                "y_dan": y_dan,
                "initial_y_dan": y_dan.copy(),
                "u": brain.memory_u.copy(),
                "w": brain.memory_w.copy(),
                "decision_efficacy_delta": [],
                "reward_drive_means": [],
                "aversive_drive_means": [],
                "reward_term_a_means": [],
                "reward_term_b_means": [],
                "aversive_term_a_means": [],
                "aversive_term_b_means": [],
            }

        self.current_decision = -1
        self.current_bin = 0
        self.total_bins = 0
        self._module: Any | None = None
        self._original: Any | None = None

    def __enter__(self) -> "CounterfactualReplayTracer":
        import stonkfly.neural.rule as rule

        self._module = rule
        self._original = rule.advance
        rule.advance = self._wrapped
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._module is not None and self._original is not None:
            self._module.advance = self._original
        self._module = None
        self._original = None

    def begin_decision(self, decision_index: int) -> None:
        self.current_decision = int(decision_index)
        self.current_bin = 0

    def end_decision(self) -> None:
        import numpy as np

        for state in self.conditions.values():
            state["decision_efficacy_delta"].append(
                round(float(np.mean(state["w"] - self.initial_w)), 12)
            )

    def _wrapped(
        self,
        y_kc: Any,
        y_dan: Any,
        u: Any,
        w: Any,
        kc_hz: Any,
        dan_hz: Any,
        gain: Any,
        dt_seconds: float,
        eta: float,
        learning: bool = True,
        frozen: bool = False,
    ) -> None:
        import numpy as np
        from stonkfly.neural.rule import PARAMETERS

        if self._original is None:
            raise RuntimeError("Original rule missing")
        if abs(float(dt_seconds) - 0.01) > 1e-12:
            raise RuntimeError("Counterfactual replay expects 10 ms bins")

        reward_edges = np.any(np.abs(gain[: self.reward_count]) > 0, axis=0)
        aversive_edges = np.any(np.abs(gain[self.reward_count :]) > 0, axis=0)
        if np.any(reward_edges & aversive_edges) or not np.all(reward_edges | aversive_edges):
            raise RuntimeError("Plastic edge compartment mask invalid")

        # The live network runs with zero baseline and frozen memory. Therefore
        # dan_hz is the raw per-bin DAN rate sequence shared by every replay.
        raw_dan_hz = np.asarray(dan_hz, dtype=np.float64)

        for state in self.conditions.values():
            residual_dan = raw_dan_hz - state["baseline"]
            ak = math.exp(-dt_seconds / PARAMETERS["trace_kc_seconds"])
            ad = math.exp(-dt_seconds / PARAMETERS["trace_dan_seconds"])
            kmid = state["y_kc"] * math.sqrt(ak) + kc_hz * (1 - math.sqrt(ak))
            dmid = state["y_dan"] * math.sqrt(ad) + residual_dan * (1 - math.sqrt(ad))
            term_a = kc_hz * (gain.T @ dmid)
            term_b = (gain.T @ residual_dan) * kmid
            drive = eta * (term_a - term_b)

            state["reward_drive_means"].append(float(drive[reward_edges].mean()))
            state["aversive_drive_means"].append(float(drive[aversive_edges].mean()))
            state["reward_term_a_means"].append(float(term_a[reward_edges].mean()))
            state["reward_term_b_means"].append(float(term_b[reward_edges].mean()))
            state["aversive_term_a_means"].append(float(term_a[aversive_edges].mean()))
            state["aversive_term_b_means"].append(float(term_b[aversive_edges].mean()))

            self._original(
                state["y_kc"],
                state["y_dan"],
                state["u"],
                state["w"],
                kc_hz,
                residual_dan,
                gain,
                dt_seconds,
                eta,
                True,
                False,
            )

        # Preserve the exact live frozen network semantics.
        self._original(
            y_kc,
            y_dan,
            u,
            w,
            kc_hz,
            dan_hz,
            gain,
            dt_seconds,
            eta,
            learning,
            frozen,
        )
        self.current_bin += 1
        self.total_bins += 1

    def report(self) -> dict[str, Any]:
        import numpy as np

        result = {}
        for name, state in self.conditions.items():
            decision = state["decision_efficacy_delta"]
            result[name] = {
                "initial_y_dan": _summary(state["initial_y_dan"]),
                "first_5_decision_mean_efficacy_delta": round(
                    mean(decision[:5]), 12
                ),
                "final_mean_efficacy_delta": round(
                    float(np.mean(state["w"] - self.initial_w)), 12
                ),
                "final_mean_u_delta": round(
                    float(np.mean(state["u"] - self.initial_u)), 12
                ),
                "mean_reward_net_drive": round(
                    mean(state["reward_drive_means"]), 12
                ),
                "mean_aversive_net_drive": round(
                    mean(state["aversive_drive_means"]), 12
                ),
                "mean_reward_kc_x_dan_trace_term": round(
                    mean(state["reward_term_a_means"]), 12
                ),
                "mean_reward_dan_x_kc_trace_term": round(
                    mean(state["reward_term_b_means"]), 12
                ),
                "mean_aversive_kc_x_dan_trace_term": round(
                    mean(state["aversive_term_a_means"]), 12
                ),
                "mean_aversive_dan_x_kc_trace_term": round(
                    mean(state["aversive_term_b_means"]), 12
                ),
                "decision_efficacy_delta": decision,
                "bins": len(state["aversive_drive_means"]),
            }
        return result


def _run_replicate(
    *,
    replicate_id: str,
    trajectory_seed: int,
    base_checkpoint: Path,
    work_checkpoint: Path,
) -> dict[str, Any]:
    shutil.copy2(base_checkpoint, work_checkpoint)
    source_sha = _sha256_file(base_checkpoint)
    inner = MaleCNSBrain(checkpoint=work_checkpoint, learning=False)
    inner.brain.weights_frozen = True
    inner.brain.dan_baseline_hz[:] = 0.0

    live_initial_memory = _memory_snapshot(inner)
    initial_trace = {
        "rate_kc": _summary(inner.brain.rate_kc),
        "rate_dan_reward": _summary(inner.brain.rate_dan[:15]),
        "rate_dan_aversive": _summary(inner.brain.rate_dan[15:]),
    }

    controlled = ControlledBrain(
        inner,
        sensory_mode="normal",
        reinforcement_mode="none",
        scramble_seed=0,
    )
    session = GoalMazeSession(
        controlled,
        environment=GoalMazeEnvironment(seed=trajectory_seed),
        checkpoint=None,
        world_tick_seconds=3600.0,
        decision_synchronous_world=True,
    )

    decisions = []
    with CounterfactualReplayTracer(inner) as tracer:
        for decision_index in range(EXPECTED_DECISIONS):
            tracer.begin_decision(decision_index)
            state = session.tick()
            if not _neural_decision_verified(state):
                raise RuntimeError("Replay trajectory lacks verifiable neural activity")
            tracer.end_decision()
            telemetry = copy.deepcopy(((state.get("brain") or {}).get("telemetry") or {}))
            decisions.append({
                "decision_index": decision_index,
                "action": str(state.get("decision_action") or "UNKNOWN"),
                "gate_spikes": int(telemetry.get("gate_spikes") or 0),
                "reward_spikes": int(telemetry.get("reward_spikes") or 0),
                "aversive_spikes": int(telemetry.get("aversive_spikes") or 0),
            })
        replay_report = tracer.report()
        total_bins = tracer.total_bins

    if set(controlled.delivered_reinforcement) - {"none"}:
        raise RuntimeError("Replay trajectory delivered external reinforcement")

    live_final_memory = _memory_snapshot(inner)
    trajectory_digest = _digest_json(decisions)
    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "source_checkpoint_sha256": source_sha,
        "trajectory_digest": trajectory_digest,
        "decisions": len(decisions),
        "bins": total_bins,
        "initial_trace": initial_trace,
        "live_initial_memory": live_initial_memory,
        "live_final_memory": live_final_memory,
        "live_frozen_memory_unchanged": (
            live_initial_memory["sha256"] == live_final_memory["sha256"]
        ),
        "training_delivered_reinforcement": dict(
            sorted(controlled.delivered_reinforcement.items())
        ),
        "replays": replay_report,
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, *_ in EXPECTED_REPLAYS:
        rows = [rep["replays"][name] for rep in replicates]
        out[name] = {
            "mean_first_5_decision_efficacy_delta": round(
                mean(row["first_5_decision_mean_efficacy_delta"] for row in rows),
                12,
            ),
            "mean_final_efficacy_delta": round(
                mean(row["final_mean_efficacy_delta"] for row in rows), 12
            ),
            "mean_final_u_delta": round(
                mean(row["final_mean_u_delta"] for row in rows), 12
            ),
            "mean_reward_net_drive": round(
                mean(row["mean_reward_net_drive"] for row in rows), 12
            ),
            "mean_aversive_net_drive": round(
                mean(row["mean_aversive_net_drive"] for row in rows), 12
            ),
        }

    z = out["zero_baseline"]
    u = out["calibrated_unrecentered"]
    r = out["calibrated_recentered"]
    out["descriptive_contrasts"] = {
        "recentered_minus_unrecentered_final_efficacy_delta": round(
            r["mean_final_efficacy_delta"] - u["mean_final_efficacy_delta"], 12
        ),
        "recentered_minus_zero_final_efficacy_delta": round(
            r["mean_final_efficacy_delta"] - z["mean_final_efficacy_delta"], 12
        ),
        "unrecentered_minus_zero_final_efficacy_delta": round(
            u["mean_final_efficacy_delta"] - z["mean_final_efficacy_delta"], 12
        ),
        "recentered_minus_zero_aversive_net_drive": round(
            r["mean_aversive_net_drive"] - z["mean_aversive_net_drive"], 12
        ),
        "unrecentered_minus_recentered_aversive_net_drive": round(
            u["mean_aversive_net_drive"] - r["mean_aversive_net_drive"], 12
        ),
    }
    return out


def run_counterfactual_rule_replay(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("Counterfactual replay config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)
    if _baseline_digest(list(BASELINE_HZ)) != BASELINE_DIGEST:
        raise RuntimeError("Frozen baseline digest mismatch")

    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha_before = _sha256_file(base_checkpoint)
    replicates = []
    for replicate_id, trajectory_seed in EXPECTED_REPLICATES:
        rep_dir = output_dir / replicate_id
        rep_dir.mkdir(parents=True, exist_ok=True)
        replicates.append(
            _run_replicate(
                replicate_id=replicate_id,
                trajectory_seed=trajectory_seed,
                base_checkpoint=base_checkpoint,
                work_checkpoint=rep_dir / "frozen-trajectory.npz",
            )
        )
    source_sha_after = _sha256_file(base_checkpoint)

    expected_bins = EXPECTED_DECISIONS * EXPECTED_BINS_PER_DECISION
    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "all_replicates_executed": len(replicates) == len(EXPECTED_REPLICATES),
        "all_replicates_start_from_source_checkpoint": all(
            rep["source_checkpoint_sha256"] == source_sha_before for rep in replicates
        ),
        "single_frozen_trajectory_per_replicate": all(
            rep["live_frozen_memory_unchanged"] is True for rep in replicates
        ),
        "all_external_reinforcement_suppressed": all(
            set(rep["training_delivered_reinforcement"]) <= {"none"}
            for rep in replicates
        ),
        "all_decisions_executed": all(
            rep["decisions"] == EXPECTED_DECISIONS for rep in replicates
        ),
        "all_expected_rule_bins_replayed": all(
            rep["bins"] == expected_bins
            and all(
                rep["replays"][name]["bins"] == expected_bins
                for name, *_ in EXPECTED_REPLAYS
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
        "frozen_baseline_hz": list(BASELINE_HZ),
        "frozen_baseline_digest": BASELINE_DIGEST,
        "replicates": replicates,
        "aggregate": _aggregate(replicates),
        "learning_validated": False,
        "dan_trace_state_mismatch_causal": False,
        "trace_recentering_remediation_validated": False,
        "baseline_shift_rule_effect_causal": False,
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
        description="Replay the pinned plasticity rule on one frozen neural trajectory"
    )
    parser.add_argument(
        "--config",
        default="data/counterfactual_rule_replay_diagnostic_v01.json",
    )
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_counterfactual_rule_replay(
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
