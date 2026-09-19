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
from .counterfactual_rule_replay import BASELINE_DIGEST, BASELINE_HZ, _summary
from .dan_baseline_intervention import _baseline_digest, _memory_snapshot
from .goal_training import GoalMazeEnvironment, GoalMazeSession, _reinforcement_for_reward
from .learning_control_study import ControlledBrain, _sha256_file
from .smoke import _digest_json, _neural_decision_verified


CONFIG_SCHEMA = "neurofly-external-reinforcement-increment-diagnostic-v0.1"
RECEIPT_SCHEMA = "neurofly-external-reinforcement-increment-diagnostic-receipt-v0.1"
STATUS = "EXPLORATORY_DIAGNOSTIC_ONLY"
SCOPE = "real-malecns-frozen-trajectory-external-reinforcement-increment"
EXPECTED_DECISIONS = 60
EXPECTED_BINS_PER_DECISION = 5
EXPECTED_RATE_BIN_MS = 10
EXPECTED_CONDITIONS = (
    ("endogenous_only", "none"),
    ("true_external", "recorded_true_task_signal"),
)
EXPECTED_REPLICATES = (
    ("R1", 2111),
    ("R2", 2113),
    ("R3", 2129),
    ("R4", 2131),
)
ORIGIN_RECEIPT = "fad3e8a132ef13e474d7656a99027c41fa068f8d2108174beba9f7684759400d"
PREVIOUS_SEEDS = {
    109, 211, 223, 227, 229, 233, 239, 241, 251, 701, 709, 719,
    1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051, 1061, 1063,
    1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117, 1123, 1129, 1151, 1153, 1163,
    1201, 1213, 1217, 1223, 1301, 1303, 1307, 1319, 1321, 1327, 1361, 1367,
    1409, 1423, 1427, 1451, 1453, 1459, 1471, 1481, 1483,
    1601, 1607, 1609, 1613, 1619, 1621, 1627, 1637, 1657, 1663, 1667, 1669,
    1693, 1697, 1699, 1709, 1721, 1723,
    1801, 1807, 1811, 1823, 1831, 1847, 1861, 1867, 1871, 1873, 1877, 1879,
    1901, 1907, 1913, 2003, 2011, 2017, 2027, 2029, 2039, 2053, 2063, 2069,
    2081, 2083, 2087,
}


def _normalized_conditions(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    return tuple(
        (item.get("name"), item.get("external_reinforcement"))
        for item in (config.get("shadow_conditions") or [])
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
            origin.get("recentered_discrimination_run_id") == 35419000124
            and origin.get("recentered_discrimination_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("baseline_digest") == BASELINE_DIGEST
        ),
        "runtime_exact": (
            runtime.get("decision_synchronous_world") is True
            and runtime.get("decisions_per_replicate") == EXPECTED_DECISIONS
            and runtime.get("neural_ms_per_decision") == 50
            and runtime.get("rate_bin_ms") == EXPECTED_RATE_BIN_MS
            and runtime.get("expected_bins_per_decision") == EXPECTED_BINS_PER_DECISION
            and runtime.get("live_neural_weights_frozen") is True
            and runtime.get("live_external_reinforcement") == "none"
            and runtime.get("baseline_mode") == "calibrated"
            and runtime.get("trace_state_mode") == "subtract_baseline"
        ),
        "conditions_exact": _normalized_conditions(config) == EXPECTED_CONDITIONS,
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "fresh_disjoint_seeds": len(seeds) == len(set(seeds)) and not (set(seeds) & PREVIOUS_SEEDS),
        "endpoints_exact": tuple(config.get("primary_descriptive_endpoints") or ()) == (
            "external_reinforced_decisions",
            "true_minus_endogenous_first_5_decision_mean_efficacy_delta",
            "true_minus_endogenous_final_mean_efficacy_delta",
            "true_minus_endogenous_reward_net_drive",
            "true_minus_endogenous_aversive_net_drive",
            "live_frozen_memory_delta",
        ),
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims) == {
                "learning_validated",
                "external_reinforcement_increment_causal",
                "temporal_credit_defect_confirmed",
                "causal_learning_claim_authorized",
                "replacement_confirmatory_authorized",
                "behavioral_promotion_authorized",
            }
            and all(value is False for value in claims.values())
        ),
    }


class ExternalIncrementTracer(AbstractContextManager["ExternalIncrementTracer"]):
    def __init__(self, inner: MaleCNSBrain) -> None:
        import numpy as np

        brain = inner.brain
        baseline = np.asarray(BASELINE_HZ, dtype=np.float64)
        if baseline.shape != brain.rate_dan.shape:
            raise RuntimeError("Frozen baseline shape mismatch")
        self.reward_count = len(brain.circuit["reward"])
        self.reward_indices = np.asarray(brain.circuit["reward"], dtype=np.int64)
        self.aversive_indices = np.asarray(brain.circuit["aversive"], dtype=np.int64)
        self.dan_count = int(brain.rate_dan.shape[0])
        self.pulse_current = float(inner.pulse_current)
        self.dt = float(brain.dt)
        self.initial_w = brain.memory_w.copy()
        self.initial_u = brain.memory_u.copy()
        y_dan = brain.rate_dan.copy() - baseline
        base = {
            "y_kc": brain.rate_kc.copy(),
            "y_dan": y_dan,
            "u": brain.memory_u.copy(),
            "w": brain.memory_w.copy(),
        }
        self.conditions = {
            "endogenous_only": copy.deepcopy(base),
            "true_external": copy.deepcopy(base),
        }
        for state in self.conditions.values():
            state.update({
                "decision_efficacy_delta": [],
                "reward_drive_means": [],
                "aversive_drive_means": [],
                "bins": 0,
            })
        self.current_reinforcement = "none"
        self.current_bin = 0
        self.total_bins = 0
        self._module: Any | None = None
        self._original: Any | None = None

    def __enter__(self) -> "ExternalIncrementTracer":
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

    def begin_decision(self, reinforcement: str) -> None:
        if reinforcement not in {"none", "reward", "aversive"}:
            raise ValueError(reinforcement)
        self.current_reinforcement = reinforcement
        self.current_bin = 0

    def end_decision(self) -> None:
        import numpy as np
        for state in self.conditions.values():
            state["decision_efficacy_delta"].append(
                round(float(np.mean(state["w"] - self.initial_w)), 12)
            )

    def _external_current(self, reinforcement: str, bin_index: int) -> Any:
        import numpy as np
        current = np.zeros(self.dan_count, dtype=np.float64)
        if reinforcement == "none" or bin_index >= 2:
            return current
        # rule.advance() receives a compact 17-element DAN-rate vector ordered
        # exactly as reward compartments followed by aversive compartments.
        # The previous implementation incorrectly allocated a whole-brain
        # 166,700-element vector and therefore could not be added to dan_hz.
        if reinforcement == "reward":
            current[: self.reward_count] = self.pulse_current
        else:
            current[self.reward_count :] = self.pulse_current
        return current

    def _wrapped(
        self, y_kc: Any, y_dan: Any, u: Any, w: Any,
        kc_hz: Any, dan_hz: Any, gain: Any, dt_seconds: float, eta: float,
        learning: bool = True, frozen: bool = False,
    ) -> None:
        import numpy as np
        from stonkfly.neural.rule import PARAMETERS

        if self._original is None:
            raise RuntimeError("Original rule missing")
        if abs(float(dt_seconds) - 0.01) > 1e-12:
            raise RuntimeError("Expected 10 ms bins")

        reward_edges = np.any(np.abs(gain[: self.reward_count]) > 0, axis=0)
        aversive_edges = np.any(np.abs(gain[self.reward_count :]) > 0, axis=0)
        raw_dan_hz = np.asarray(dan_hz, dtype=np.float64)
        baseline = np.asarray(BASELINE_HZ, dtype=np.float64)
        endogenous_residual = raw_dan_hz - baseline

        for name, state in self.conditions.items():
            residual_dan = endogenous_residual.copy()
            if name == "true_external" and self.current_reinforcement != "none" and self.current_bin < 2:
                # The live trajectory is frozen and receives no external pulse. For the
                # counterfactual shadow only, add the exact 20 ms task pulse as an
                # equivalent per-bin DAN-rate increment. Stonkfly's LIF response to
                # current injection is nonlinear, so this is explicitly a rule-input
                # increment diagnostic, not a full-network pulse replay.
                ext = self._external_current(self.current_reinforcement, self.current_bin)
                residual_dan = residual_dan + ext

            ak = math.exp(-dt_seconds / PARAMETERS["trace_kc_seconds"])
            ad = math.exp(-dt_seconds / PARAMETERS["trace_dan_seconds"])
            kmid = state["y_kc"] * math.sqrt(ak) + kc_hz * (1 - math.sqrt(ak))
            dmid = state["y_dan"] * math.sqrt(ad) + residual_dan * (1 - math.sqrt(ad))
            term_a = kc_hz * (gain.T @ dmid)
            term_b = (gain.T @ residual_dan) * kmid
            drive = eta * (term_a - term_b)
            state["reward_drive_means"].append(float(drive[reward_edges].mean()))
            state["aversive_drive_means"].append(float(drive[aversive_edges].mean()))

            self._original(
                state["y_kc"], state["y_dan"], state["u"], state["w"],
                kc_hz, residual_dan, gain, dt_seconds, eta, True, False,
            )
            state["bins"] += 1

        self._original(
            y_kc, y_dan, u, w, kc_hz, dan_hz, gain,
            dt_seconds, eta, learning, frozen,
        )
        self.current_bin += 1
        self.total_bins += 1

    def report(self) -> dict[str, Any]:
        import numpy as np
        out = {}
        for name, state in self.conditions.items():
            d = state["decision_efficacy_delta"]
            out[name] = {
                "first_5_decision_mean_efficacy_delta": round(mean(d[:5]), 12),
                "final_mean_efficacy_delta": round(float(np.mean(state["w"] - self.initial_w)), 12),
                "final_mean_u_delta": round(float(np.mean(state["u"] - self.initial_u)), 12),
                "mean_reward_net_drive": round(mean(state["reward_drive_means"]), 12),
                "mean_aversive_net_drive": round(mean(state["aversive_drive_means"]), 12),
                "decision_efficacy_delta": d,
                "bins": state["bins"],
            }
        return out


def _run_replicate(*, replicate_id: str, trajectory_seed: int, base_checkpoint: Path, work_checkpoint: Path) -> dict[str, Any]:
    shutil.copy2(base_checkpoint, work_checkpoint)
    source_sha = _sha256_file(base_checkpoint)
    inner = MaleCNSBrain(checkpoint=work_checkpoint, learning=False)
    inner.brain.weights_frozen = True
    inner.brain.dan_baseline_hz[:] = 0.0
    live_initial = _memory_snapshot(inner)

    controlled = ControlledBrain(inner, sensory_mode="normal", reinforcement_mode="none", scramble_seed=0)
    session = GoalMazeSession(
        controlled,
        environment=GoalMazeEnvironment(seed=trajectory_seed),
        checkpoint=None,
        world_tick_seconds=3600.0,
        decision_synchronous_world=True,
    )

    decisions = []
    pending_true = "none"
    with ExternalIncrementTracer(inner) as tracer:
        for i in range(EXPECTED_DECISIONS):
            tracer.begin_decision(pending_true)
            state = session.tick()
            if not _neural_decision_verified(state):
                raise RuntimeError("Trajectory lacks verifiable neural activity")
            tracer.end_decision()
            reward = float(state.get("last_reward", 0.0))
            next_true = _reinforcement_for_reward(reward)
            decisions.append({
                "decision_index": i,
                "action": str(state.get("decision_action") or "UNKNOWN"),
                "task_reward": reward,
                "true_reinforcement_delivered_to_shadow": pending_true,
                "true_reinforcement_generated_for_next_decision": next_true,
            })
            pending_true = next_true
        report = tracer.report()
        total_bins = tracer.total_bins

    live_final = _memory_snapshot(inner)
    reinforced = sum(row["true_reinforcement_delivered_to_shadow"] != "none" for row in decisions)
    return {
        "replicate_id": replicate_id,
        "trajectory_seed": trajectory_seed,
        "source_checkpoint_sha256": source_sha,
        "trajectory_digest": _digest_json(decisions),
        "decisions": len(decisions),
        "bins": total_bins,
        "external_reinforced_decisions": reinforced,
        "decision_trace": decisions,
        "live_initial_memory": live_initial,
        "live_final_memory": live_final,
        "live_frozen_memory_unchanged": live_initial["sha256"] == live_final["sha256"],
        "live_delivered_reinforcement": dict(sorted(controlled.delivered_reinforcement.items())),
        "conditions": report,
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    out = {}
    for name, *_ in EXPECTED_CONDITIONS:
        rows = [r["conditions"][name] for r in replicates]
        out[name] = {
            "mean_first_5_decision_efficacy_delta": round(mean(x["first_5_decision_mean_efficacy_delta"] for x in rows), 12),
            "mean_final_efficacy_delta": round(mean(x["final_mean_efficacy_delta"] for x in rows), 12),
            "mean_final_u_delta": round(mean(x["final_mean_u_delta"] for x in rows), 12),
            "mean_reward_net_drive": round(mean(x["mean_reward_net_drive"] for x in rows), 12),
            "mean_aversive_net_drive": round(mean(x["mean_aversive_net_drive"] for x in rows), 12),
        }
    e, t = out["endogenous_only"], out["true_external"]
    out["descriptive_contrasts"] = {
        "mean_external_reinforced_decisions": round(mean(r["external_reinforced_decisions"] for r in replicates), 8),
        "true_minus_endogenous_first_5_decision_mean_efficacy_delta": round(t["mean_first_5_decision_efficacy_delta"] - e["mean_first_5_decision_efficacy_delta"], 12),
        "true_minus_endogenous_final_mean_efficacy_delta": round(t["mean_final_efficacy_delta"] - e["mean_final_efficacy_delta"], 12),
        "true_minus_endogenous_reward_net_drive": round(t["mean_reward_net_drive"] - e["mean_reward_net_drive"], 12),
        "true_minus_endogenous_aversive_net_drive": round(t["mean_aversive_net_drive"] - e["mean_aversive_net_drive"], 12),
    }
    return out


def run_external_reinforcement_increment(*, config_path: Path, base_checkpoint: Path, output_dir: Path, receipt_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("External reinforcement increment config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)
    if _baseline_digest(list(BASELINE_HZ)) != BASELINE_DIGEST:
        raise RuntimeError("Frozen baseline digest mismatch")

    output_dir.mkdir(parents=True, exist_ok=True)
    before = _sha256_file(base_checkpoint)
    reps = []
    for rid, seed in EXPECTED_REPLICATES:
        repdir = output_dir / rid
        repdir.mkdir(parents=True, exist_ok=True)
        reps.append(_run_replicate(
            replicate_id=rid, trajectory_seed=seed, base_checkpoint=base_checkpoint,
            work_checkpoint=repdir / "frozen-trajectory.npz",
        ))
    after = _sha256_file(base_checkpoint)
    expected_bins = EXPECTED_DECISIONS * EXPECTED_BINS_PER_DECISION
    evidence_gates = {
        "source_checkpoint_unchanged": before == after,
        "all_replicates_executed": len(reps) == len(EXPECTED_REPLICATES),
        "all_replicates_start_from_source_checkpoint": all(r["source_checkpoint_sha256"] == before for r in reps),
        "live_frozen_memory_unchanged": all(r["live_frozen_memory_unchanged"] for r in reps),
        "live_external_reinforcement_suppressed": all(set(r["live_delivered_reinforcement"]) <= {"none"} for r in reps),
        "all_decisions_executed": all(r["decisions"] == EXPECTED_DECISIONS for r in reps),
        "all_expected_rule_bins_replayed": all(
            r["bins"] == expected_bins and all(c["bins"] == expected_bins for c in r["conditions"].values())
            for r in reps
        ),
        "frozen_baseline_exact": _baseline_digest(list(BASELINE_HZ)) == BASELINE_DIGEST,
        "at_least_one_true_external_event_observed": any(r["external_reinforced_decisions"] > 0 for r in reps),
        "claims_remain_locked": all(value is False for value in config["claim_policy"].values()),
    }
    valid = all(config_gates.values()) and all(evidence_gates.values())
    body = {
        "schema": RECEIPT_SCHEMA,
        "status": "EXPLORATORY_DIAGNOSTIC_COMPLETE" if valid else "INVALID_EXECUTION",
        "scope": SCOPE,
        "execution_valid": valid,
        "config_gates": config_gates,
        "evidence_gates": evidence_gates,
        "source_checkpoint_sha256": before,
        "source_checkpoint_sha256_after": after,
        "frozen_baseline_digest": BASELINE_DIGEST,
        "replicates": reps,
        "aggregate": _aggregate(reps),
        "learning_validated": False,
        "external_reinforcement_increment_causal": False,
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
    p = argparse.ArgumentParser(description="Counterfactual external reinforcement increment on one frozen neural trajectory")
    p.add_argument("--config", default="data/external_reinforcement_increment_diagnostic_v01.json")
    p.add_argument("--base-checkpoint", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--receipt", required=True)
    a = p.parse_args(argv)
    r = run_external_reinforcement_increment(
        config_path=Path(a.config), base_checkpoint=Path(a.base_checkpoint),
        output_dir=Path(a.output_dir), receipt_path=Path(a.receipt),
    )
    print(json.dumps({"status":r["status"],"execution_valid":r["execution_valid"],"aggregate":r["aggregate"],"receipt_sha256":r["receipt_sha256"]},indent=2,sort_keys=True))
    return 0 if r["execution_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
