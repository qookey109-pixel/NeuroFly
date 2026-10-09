from __future__ import annotations

"""Isolated danger-ORN gain sweep; does not authorize production tuning."""

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

import neurofly.brain_runtime as runtime
from neurofly.brain_runtime import MaleCNSBrain
from neurofly.smoke import _digest_json
from neurofly.upstream import STONKFLY_COMMIT
from olfaction_steering_causal_probe import _sha256_file, make_context

SCHEMA = "neurofly-danger-orn-gain-sweep-v1"
WARMUP_FRAMES = 4
PROBE_FRAMES = 24
DANGER_GAINS = (1.6, 2.4, 3.2)
FOOD_GAIN = 1.0
NEUTRAL_FRAME = np.full((180, 320, 3), 128, dtype=np.uint8)


def _mean(values: list[float]) -> float:
    return float(sum(values) / len(values))


def run_condition(
    checkpoint: Path,
    *,
    condition: str,
    danger_gain: float,
) -> dict[str, Any]:
    if condition not in {"neutral", "food_left", "food_right", "danger_left", "danger_right"}:
        raise ValueError("Unsupported isolated odor condition")
    if float(danger_gain) not in DANGER_GAINS:
        raise ValueError("Danger gain must be a preregistered sweep setting")
    brain = MaleCNSBrain(checkpoint=checkpoint, learning=False)
    brain.brain.weights_frozen = True
    for _ in range(WARMUP_FRAMES):
        brain.decide(NEUTRAL_FRAME, reinforcement="none", context=None)

    # Patch only this isolated interpreter's engineered sensory current gain;
    # never modify production code, production caches or the checkpoint.
    baseline_gain = runtime.DANGER_ODOR_CURRENT_GAIN
    rows: list[dict[str, float]] = []
    try:
        runtime.DANGER_ODOR_CURRENT_GAIN = float(danger_gain)
        context = make_context(condition)
        for _ in range(PROBE_FRAMES):
            decision = brain.decide(
                NEUTRAL_FRAME, reinforcement="none", context=context
            )
            t = decision.telemetry
            if t.get("external_reinforcement") != "none":
                raise RuntimeError("Unexpected external reinforcement")
            if t.get("frontal_wall_triggered") or t.get("sensory_loop_triggered"):
                raise RuntimeError("Unexpected wall or loop stimulus")
            rows.append({
                "dna02_centered_difference_hz": float(t["decoder_difference_hz"]),
                "dna02_raw_difference_hz": float(t["raw_difference_hz"]),
                "dna03_raw_difference_hz": float(t["steering_observer_difference_hz"]),
                "food_orn_spikes": float(t["food_odor_spikes"]),
                "danger_orn_spikes": float(t["danger_odor_spikes"]),
                "total_spikes": float(t["total_spikes"]),
            })
    finally:
        runtime.DANGER_ODOR_CURRENT_GAIN = baseline_gain

    return {
        "condition": condition,
        "gain": float(danger_gain),
        "frames": PROBE_FRAMES,
        "mean_dna02_centered_difference_hz": _mean([
            r["dna02_centered_difference_hz"] for r in rows
        ]),
        "mean_dna02_raw_difference_hz": _mean([
            r["dna02_raw_difference_hz"] for r in rows
        ]),
        "mean_dna03_raw_difference_hz": _mean([
            r["dna03_raw_difference_hz"] for r in rows
        ]),
        "mean_food_orn_spikes": _mean([r["food_orn_spikes"] for r in rows]),
        "mean_danger_orn_spikes": _mean([
            r["danger_orn_spikes"] for r in rows
        ]),
        "rows": rows,
    }


def run_sweep(checkpoint: Path) -> dict[str, Any]:
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    checkpoint_sha_before = _sha256_file(checkpoint)
    references = {
        condition: run_condition(checkpoint, condition=condition, danger_gain=DANGER_GAINS[0])
        for condition in ("neutral", "food_left", "food_right")
    }
    results = {
        str(gain): {
            condition: run_condition(checkpoint, condition=condition, danger_gain=gain)
            for condition in ("danger_left", "danger_right")
        }
        for gain in DANGER_GAINS
    }

    metrics = (
        "mean_dna02_centered_difference_hz",
        "mean_dna02_raw_difference_hz",
        "mean_dna03_raw_difference_hz",
    )
    contrasts = {
        "food_reference": {
            key: (
                references["food_right"][key] - references["food_left"][key]
            ) for key in metrics
        }
    }
    for gain in DANGER_GAINS:
        pair = results[str(gain)]
        contrasts[str(gain)] = {
            key: pair["danger_right"][key] - pair["danger_left"][key]
            for key in metrics
        }

    if _sha256_file(checkpoint) != checkpoint_sha_before:
        raise RuntimeError("Read-only source checkpoint was mutated")

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "source_checkpoint_sha256": checkpoint_sha_before,
        "source_checkpoint_unchanged": True,
        "learning_enabled": False,
        "production_code_modified": False,
        "production_checkpoint_mutated": False,
        "maze_actions_executed": False,
        "stonkfly_commit": STONKFLY_COMMIT,
        "sweep_gains": list(DANGER_GAINS),
        "food_gain_fixed": FOOD_GAIN,
        "reference_conditions": references,
        "danger_conditions": results,
        "signed_contrasts": contrasts,
        "claim_limits": {
            "danger_gain_validated": False,
            "production_gain_change_authorized": False,
            "behavioral_improvement_verified": False,
        },
    }
    report["receipt_sha256"] = _digest_json(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-checkpoint", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    result = run_sweep(Path(args.source_checkpoint))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("DANGER_ORN_GAIN_SWEEP_PASS", result["receipt_sha256"])
    print(json.dumps(result["signed_contrasts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
