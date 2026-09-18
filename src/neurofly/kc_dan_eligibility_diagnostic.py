from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
from collections import Counter
from contextlib import AbstractContextManager
from pathlib import Path
from statistics import mean
from typing import Any

from .brain_runtime import MaleCNSBrain
from .goal_training import GoalMazeEnvironment, GoalMazeSession
from .learning_control_study import ControlledBrain, _sha256_file
from .smoke import _digest_json, _neural_decision_verified


CONFIG_SCHEMA = "neurofly-kc-dan-eligibility-diagnostic-v0.1"
RECEIPT_SCHEMA = "neurofly-kc-dan-eligibility-diagnostic-receipt-v0.1"
STATUS = "EXPLORATORY_DIAGNOSTIC_ONLY"
SCOPE = "real-malecns-kc-dan-temporal-drive-diagnostic"

EXPECTED_DECISIONS = 60
EXPECTED_RATE_BIN_MS = 10
EXPECTED_BINS_PER_DECISION = 5
EXPECTED_ARMS = (
    ("learning_none_zero_baseline", True, "zero"),
    ("learning_none_calibrated_baseline", True, "frozen_intervention_vector"),
    ("frozen_none_zero_baseline", False, "zero"),
)
EXPECTED_REPLICATES = (
    ("E1", 1709),
    ("E2", 1721),
    ("E3", 1723),
)
BASELINE_HZ = (
    0.0, 0.0, 0.11111111, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 123.0, 130.44444444,
)
BASELINE_DIGEST = "1fd69ded16a400e9a00e1265e8264aeafe7d402fa1819fc412df041fa7f205f9"
ORIGIN_RECEIPT = "7a679541962dc5cac24b63aeb62a172a71d0875fc9171cc49ac5df29d3eec907"


def _normalized_arms(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    rows = []
    for item in config.get("arms") or []:
        if not isinstance(item, dict):
            return ()
        rows.append((item.get("name"), item.get("learning"), item.get("baseline_mode")))
    return tuple(rows)


def _normalized_replicates(config: dict[str, Any]) -> tuple[tuple[Any, ...], ...]:
    rows = []
    for item in config.get("replicates") or []:
        if not isinstance(item, dict):
            return ()
        rows.append((item.get("id"), item.get("training_seed")))
    return tuple(rows)


def validate_config(config: dict[str, Any]) -> dict[str, bool]:
    origin = config.get("origin") or {}
    runtime = config.get("runtime") or {}
    claims = config.get("claim_policy") or {}
    required = tuple(config.get("required_observations") or ())
    expected_required = (
        "per_bin_kc_rate",
        "per_bin_dan_residual",
        "per_bin_kc_trace_midpoint",
        "per_bin_dan_trace_midpoint",
        "per_bin_kc_x_dan_trace_term",
        "per_bin_dan_x_kc_trace_term",
        "per_bin_net_drive",
        "per_bin_delta_u",
        "per_bin_delta_w",
        "initial_rate_traces",
        "decision_memory_drift",
    )
    return {
        "schema_exact": config.get("schema") == CONFIG_SCHEMA,
        "status_exact": config.get("status") == STATUS,
        "scope_exact": config.get("scope") == SCOPE,
        "origin_exact": (
            origin.get("intervention_run_id") == 35348834258
            and origin.get("intervention_receipt_sha256") == ORIGIN_RECEIPT
            and origin.get("baseline_digest") == BASELINE_DIGEST
        ),
        "runtime_exact": (
            runtime.get("decision_synchronous_world") is True
            and runtime.get("decisions_per_arm") == EXPECTED_DECISIONS
            and runtime.get("neural_ms_per_decision") == 50
            and runtime.get("rate_bin_ms") == EXPECTED_RATE_BIN_MS
            and runtime.get("expected_bins_per_decision") == EXPECTED_BINS_PER_DECISION
            and runtime.get("external_reinforcement") == "none"
        ),
        "arms_exact": _normalized_arms(config) == EXPECTED_ARMS,
        "replicates_exact": _normalized_replicates(config) == EXPECTED_REPLICATES,
        "seeds_unique": len({seed for _, seed in EXPECTED_REPLICATES}) == len(EXPECTED_REPLICATES),
        "required_observations_exact": required == expected_required,
        "claims_locked": (
            isinstance(claims, dict)
            and set(claims)
            == {
                "learning_validated",
                "kc_dan_temporal_drive_causal",
                "dan_trace_state_mismatch_causal",
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
        "changed_edges": int(memory["changed_edges"]),
        "mean_efficacy": round(float(memory["mean_efficacy"]), 12),
        "minimum_efficacy": round(float(memory["minimum_efficacy"]), 12),
        "sha256": str(memory["sha256"]),
    }


def _array_summary(values: Any) -> dict[str, float]:
    import numpy as np

    a = np.asarray(values, dtype=np.float64)
    return {
        "mean": round(float(a.mean()), 12),
        "mean_abs": round(float(np.abs(a).mean()), 12),
        "sum": round(float(a.sum()), 12),
        "minimum": round(float(a.min()), 12),
        "maximum": round(float(a.max()), 12),
        "positive_fraction": round(float(np.mean(a > 0)), 8),
        "negative_fraction": round(float(np.mean(a < 0)), 8),
    }


class RuleAdvanceTracer(AbstractContextManager["RuleAdvanceTracer"]):
    def __init__(self, reward_count: int = 15) -> None:
        self.reward_count = int(reward_count)
        self.rows: list[dict[str, Any]] = []
        self.current_decision = -1
        self.current_bin = 0
        self._module: Any | None = None
        self._original: Any | None = None

    def __enter__(self) -> "RuleAdvanceTracer":
        import stonkfly.neural.rule as rule

        if self._module is not None:
            raise RuntimeError("Tracer already active")
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
            raise RuntimeError("Tracer original rule missing")

        ak = math.exp(-dt_seconds / PARAMETERS["trace_kc_seconds"])
        ad = math.exp(-dt_seconds / PARAMETERS["trace_dan_seconds"])
        kmid = y_kc * math.sqrt(ak) + kc_hz * (1 - math.sqrt(ak))
        dmid = y_dan * math.sqrt(ad) + dan_hz * (1 - math.sqrt(ad))
        term_kc_x_dan_trace = kc_hz * (gain.T @ dmid)
        term_dan_x_kc_trace = (gain.T @ dan_hz) * kmid
        net = term_kc_x_dan_trace - term_dan_x_kc_trace
        drive = eta * net if learning else np.zeros_like(net)

        reward_edges = np.any(np.abs(gain[: self.reward_count]) > 0, axis=0)
        aversive_edges = np.any(np.abs(gain[self.reward_count :]) > 0, axis=0)
        if np.any(reward_edges & aversive_edges) or not np.all(reward_edges | aversive_edges):
            raise RuntimeError("Plastic edge compartment mask is not disjoint/exhaustive")

        old_u = u.copy()
        old_w = w.copy()
        old_y_kc = y_kc.copy()
        old_y_dan = y_dan.copy()

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

        def edge_groups(values: Any) -> dict[str, Any]:
            return {
                "reward": _array_summary(values[reward_edges]),
                "aversive": _array_summary(values[aversive_edges]),
            }

        row = {
            "decision_index": self.current_decision,
            "bin_index": self.current_bin,
            "dt_seconds": float(dt_seconds),
            "learning": bool(learning),
            "frozen": bool(frozen),
            "eta": float(eta),
            "kc_hz": _array_summary(kc_hz),
            "dan_residual_hz": {
                "reward": _array_summary(dan_hz[: self.reward_count]),
                "aversive": _array_summary(dan_hz[self.reward_count :]),
            },
            "kc_trace_pre": _array_summary(old_y_kc),
            "kc_trace_midpoint": _array_summary(kmid),
            "dan_trace_pre": {
                "reward": _array_summary(old_y_dan[: self.reward_count]),
                "aversive": _array_summary(old_y_dan[self.reward_count :]),
            },
            "dan_trace_midpoint": {
                "reward": _array_summary(dmid[: self.reward_count]),
                "aversive": _array_summary(dmid[self.reward_count :]),
            },
            "kc_x_dan_trace_term": edge_groups(term_kc_x_dan_trace),
            "dan_x_kc_trace_term": edge_groups(term_dan_x_kc_trace),
            "net_antihebbian_term": edge_groups(net),
            "drive": edge_groups(drive),
            "delta_u": edge_groups(u - old_u),
            "delta_w": edge_groups(w - old_w),
        }
        self.rows.append(row)
        self.current_bin += 1


def _set_baseline(inner: MaleCNSBrain, baseline_mode: str) -> None:
    import numpy as np

    if baseline_mode == "zero":
        inner.brain.dan_baseline_hz[:] = 0.0
        return
    if baseline_mode != "frozen_intervention_vector":
        raise ValueError("Unknown baseline mode")
    values = np.asarray(BASELINE_HZ, dtype=np.float64)
    if values.shape != inner.brain.dan_baseline_hz.shape:
        raise RuntimeError("Frozen intervention baseline shape mismatch")
    inner.brain.dan_baseline_hz[:] = values


def _initial_trace_state(inner: MaleCNSBrain) -> dict[str, Any]:
    b = inner.brain
    reward_count = len(b.circuit["reward"])
    baseline = b.dan_baseline_hz
    return {
        "rate_kc": _array_summary(b.rate_kc),
        "rate_dan": {
            "reward": _array_summary(b.rate_dan[:reward_count]),
            "aversive": _array_summary(b.rate_dan[reward_count:]),
        },
        "dan_baseline_hz": {
            "reward": _array_summary(baseline[:reward_count]),
            "aversive": _array_summary(baseline[reward_count:]),
        },
        "rate_dan_minus_baseline": {
            "reward": _array_summary(b.rate_dan[:reward_count] - baseline[:reward_count]),
            "aversive": _array_summary(b.rate_dan[reward_count:] - baseline[reward_count:]),
        },
        "memory_u": _array_summary(b.memory_u),
        "memory_w": _array_summary(b.memory_w),
    }


def _phase_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("No bin rows")

    metrics = (
        "kc_x_dan_trace_term",
        "dan_x_kc_trace_term",
        "net_antihebbian_term",
        "drive",
        "delta_u",
        "delta_w",
    )
    out: dict[str, Any] = {"bins": len(rows)}
    for metric in metrics:
        out[metric] = {}
        for compartment in ("reward", "aversive"):
            means = [float(row[metric][compartment]["mean"]) for row in rows]
            sums = [float(row[metric][compartment]["sum"]) for row in rows]
            mean_abs = [float(row[metric][compartment]["mean_abs"]) for row in rows]
            out[metric][compartment] = {
                "mean_of_edge_means": round(mean(means), 12),
                "sum_across_bins_and_edges": round(sum(sums), 12),
                "mean_edge_abs": round(mean(mean_abs), 12),
                "positive_bin_fraction": round(sum(value > 0 for value in means) / len(means), 8),
                "negative_bin_fraction": round(sum(value < 0 for value in means) / len(means), 8),
            }

    for metric in ("dan_residual_hz", "dan_trace_midpoint"):
        out[metric] = {}
        for compartment in ("reward", "aversive"):
            values = [float(row[metric][compartment]["mean"]) for row in rows]
            out[metric][compartment] = {
                "mean": round(mean(values), 12),
                "positive_bin_fraction": round(sum(value > 0 for value in values) / len(values), 8),
                "negative_bin_fraction": round(sum(value < 0 for value in values) / len(values), 8),
            }
    return out


def _trace_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected_bins = EXPECTED_DECISIONS * EXPECTED_BINS_PER_DECISION
    early = rows[: min(10, len(rows))]
    late = rows[-min(50, len(rows)) :]
    return {
        "bins": len(rows),
        "expected_bins": expected_bins,
        "all_bins_10ms": all(abs(float(row["dt_seconds"]) - 0.01) < 1e-12 for row in rows),
        "full": _phase_summary(rows),
        "first_100ms": _phase_summary(early),
        "last_500ms": _phase_summary(late),
    }


def _run_arm(
    *,
    name: str,
    learning: bool,
    baseline_mode: str,
    base_checkpoint: Path,
    arm_checkpoint: Path,
    train_seed: int,
) -> dict[str, Any]:
    shutil.copy2(base_checkpoint, arm_checkpoint)
    start_sha = _sha256_file(arm_checkpoint)

    inner = MaleCNSBrain(checkpoint=arm_checkpoint, learning=learning)
    inner.brain.weights_frozen = not learning
    _set_baseline(inner, baseline_mode)
    reward_count = len(inner.brain.circuit["reward"])
    if reward_count != 15 or len(inner.brain.circuit["aversive"]) != 2:
        raise RuntimeError("Unexpected DAN compartment counts")

    initial_memory = _memory_snapshot(inner)
    initial_traces = _initial_trace_state(inner)
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

    decisions = []
    with RuleAdvanceTracer(reward_count=reward_count) as tracer:
        for decision_index in range(EXPECTED_DECISIONS):
            before_bins = len(tracer.rows)
            before_memory = _memory_snapshot(inner)
            tracer.begin_decision(decision_index)
            state = session.tick()
            if not _neural_decision_verified(state):
                raise RuntimeError("Diagnostic decision lacks verifiable neural activity")
            after_memory = _memory_snapshot(inner)
            bins_used = len(tracer.rows) - before_bins
            telemetry = copy.deepcopy(((state.get("brain") or {}).get("telemetry") or {}))
            decisions.append(
                {
                    "decision_index": decision_index,
                    "bins_used": bins_used,
                    "action": str(state.get("decision_action") or "UNKNOWN"),
                    "gate_spikes": int(telemetry.get("gate_spikes") or 0),
                    "reward_spikes": int(telemetry.get("reward_spikes") or 0),
                    "aversive_spikes": int(telemetry.get("aversive_spikes") or 0),
                    "memory_changed": before_memory["sha256"] != after_memory["sha256"],
                    "mean_efficacy_before": before_memory["mean_efficacy"],
                    "mean_efficacy_after": after_memory["mean_efficacy"],
                }
            )
        bin_rows = tracer.rows

    if set(controlled.delivered_reinforcement) - {"none"}:
        raise RuntimeError("Diagnostic delivered external reinforcement")

    final_memory = _memory_snapshot(inner)
    action_counts = Counter(item["action"] for item in decisions)
    return {
        "arm": name,
        "learning": learning,
        "baseline_mode": baseline_mode,
        "initial_checkpoint_sha256": start_sha,
        "initial_memory": initial_memory,
        "final_memory": final_memory,
        "initial_trace_state": initial_traces,
        "training_delivered_reinforcement": dict(sorted(controlled.delivered_reinforcement.items())),
        "decision_summary": {
            "decisions": len(decisions),
            "memory_changed_decisions": sum(item["memory_changed"] for item in decisions),
            "all_decisions_expected_bins": all(item["bins_used"] == EXPECTED_BINS_PER_DECISION for item in decisions),
            "hold_fraction": round(action_counts.get("HOLD", 0) / len(decisions), 8),
            "gate_zero_fraction": round(sum(item["gate_spikes"] == 0 for item in decisions) / len(decisions), 8),
            "mean_efficacy_delta": round(final_memory["mean_efficacy"] - initial_memory["mean_efficacy"], 12),
        },
        "bin_trace_summary": _trace_summary(bin_rows),
        "bin_trace": bin_rows,
    }


def _aggregate(replicates: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, *_ in EXPECTED_ARMS:
        rows = [rep["arm_results"][name] for rep in replicates]
        out[name] = {
            "mean_memory_changed_decisions": round(mean(row["decision_summary"]["memory_changed_decisions"] for row in rows), 8),
            "mean_efficacy_delta": round(mean(row["decision_summary"]["mean_efficacy_delta"] for row in rows), 12),
            "mean_initial_aversive_rate_trace_hz": round(mean(row["initial_trace_state"]["rate_dan"]["aversive"]["mean"] for row in rows), 12),
            "mean_initial_aversive_baseline_hz": round(mean(row["initial_trace_state"]["dan_baseline_hz"]["aversive"]["mean"] for row in rows), 12),
            "mean_initial_aversive_trace_minus_baseline_hz": round(mean(row["initial_trace_state"]["rate_dan_minus_baseline"]["aversive"]["mean"] for row in rows), 12),
            "mean_full_aversive_net_drive": round(mean(row["bin_trace_summary"]["full"]["drive"]["aversive"]["mean_of_edge_means"] for row in rows), 12),
            "mean_first_100ms_aversive_net_drive": round(mean(row["bin_trace_summary"]["first_100ms"]["drive"]["aversive"]["mean_of_edge_means"] for row in rows), 12),
            "mean_last_500ms_aversive_net_drive": round(mean(row["bin_trace_summary"]["last_500ms"]["drive"]["aversive"]["mean_of_edge_means"] for row in rows), 12),
            "mean_full_reward_net_drive": round(mean(row["bin_trace_summary"]["full"]["drive"]["reward"]["mean_of_edge_means"] for row in rows), 12),
        }
    return out


def run_kc_dan_eligibility_diagnostic(
    *,
    config_path: Path,
    base_checkpoint: Path,
    output_dir: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text())
    config_gates = validate_config(config)
    if not all(config_gates.values()):
        raise ValueError("KC-DAN diagnostic config failed validation")
    if not base_checkpoint.is_file():
        raise FileNotFoundError(base_checkpoint)

    output_dir.mkdir(parents=True, exist_ok=True)
    source_sha_before = _sha256_file(base_checkpoint)
    replicates = []
    for replicate_id, train_seed in EXPECTED_REPLICATES:
        rep_dir = output_dir / replicate_id
        rep_dir.mkdir(parents=True, exist_ok=True)
        arm_results = {}
        for name, learning, baseline_mode in EXPECTED_ARMS:
            arm_results[name] = _run_arm(
                name=name,
                learning=bool(learning),
                baseline_mode=str(baseline_mode),
                base_checkpoint=base_checkpoint,
                arm_checkpoint=rep_dir / f"{name}.npz",
                train_seed=train_seed,
            )
        replicates.append({
            "replicate_id": replicate_id,
            "training_seed": train_seed,
            "arm_results": arm_results,
        })

    source_sha_after = _sha256_file(base_checkpoint)
    evidence_gates = {
        "source_checkpoint_unchanged": source_sha_before == source_sha_after,
        "all_replicates_executed": len(replicates) == len(EXPECTED_REPLICATES),
        "all_arms_start_from_source_checkpoint": all(
            arm["initial_checkpoint_sha256"] == source_sha_before
            for rep in replicates
            for arm in rep["arm_results"].values()
        ),
        "all_external_reinforcement_suppressed": all(
            set(arm["training_delivered_reinforcement"]) <= {"none"}
            for rep in replicates
            for arm in rep["arm_results"].values()
        ),
        "all_decisions_expected_bins": all(
            arm["decision_summary"]["all_decisions_expected_bins"]
            for rep in replicates
            for arm in rep["arm_results"].values()
        ),
        "all_rule_bins_10ms": all(
            arm["bin_trace_summary"]["all_bins_10ms"]
            and arm["bin_trace_summary"]["bins"] == EXPECTED_DECISIONS * EXPECTED_BINS_PER_DECISION
            for rep in replicates
            for arm in rep["arm_results"].values()
        ),
        "frozen_memory_unchanged": all(
            rep["arm_results"]["frozen_none_zero_baseline"]["decision_summary"]["memory_changed_decisions"] == 0
            and rep["arm_results"]["frozen_none_zero_baseline"]["initial_memory"]["sha256"]
            == rep["arm_results"]["frozen_none_zero_baseline"]["final_memory"]["sha256"]
            for rep in replicates
        ),
        "calibrated_baseline_digest_frozen": _digest_json(list(BASELINE_HZ)) == BASELINE_DIGEST,
        "claims_remain_locked": all(value is False for value in config["claim_policy"].values()),
    }
    execution_valid = all(config_gates.values()) and all(evidence_gates.values())

    body: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "status": "EXPLORATORY_DIAGNOSTIC_COMPLETE" if execution_valid else "INVALID_EXECUTION",
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
        "kc_dan_temporal_drive_causal": False,
        "dan_trace_state_mismatch_causal": False,
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
    parser = argparse.ArgumentParser(description="Trace KC-DAN centered-rule drive per 10 ms bin")
    parser.add_argument("--config", default="data/kc_dan_eligibility_diagnostic_v01.json")
    parser.add_argument("--base-checkpoint", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)

    result = run_kc_dan_eligibility_diagnostic(
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
