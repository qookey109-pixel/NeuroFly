from __future__ import annotations

"""Isolated, learning-disabled olfactory causality probe for MaleCNS steering.

Only biologically-inspired ORN channels are stimulated. The simulation's
decoded actions are observed, never executed in a maze. No production state
is saved or modified.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from neurofly.brain_runtime import MaleCNSBrain, OLFACTION_MODEL
from neurofly.smoke import _digest_json
from neurofly.upstream import STONKFLY_COMMIT

SCHEMA = "neurofly-olfaction-steering-causal-screen-v1"
WARMUP_FRAMES = 4
PROBE_FRAMES = 16
ODOUR_HIGH = 0.8
ODOUR_LOW = 0.0
CONDITIONS = (
    "neutral",
    "food_left",
    "food_right",
    "danger_left",
    "danger_right",
    "food_bilateral",
    "danger_bilateral",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _odor_pair(condition: str) -> tuple[dict[str, float], dict[str, float]]:
    if condition not in CONDITIONS:
        raise ValueError(f"unsupported condition: {condition}")
    food = {"left": 0.0, "right": 0.0, "front": 0.0, "back": 0.0}
    danger = dict(food)
    if condition == "food_left":
        food["left"] = ODOUR_HIGH
    elif condition == "food_right":
        food["right"] = ODOUR_HIGH
    elif condition == "danger_left":
        danger["left"] = ODOUR_HIGH
    elif condition == "danger_right":
        danger["right"] = ODOUR_HIGH
    elif condition == "food_bilateral":
        food.update(left=ODOUR_HIGH, right=ODOUR_HIGH)
    elif condition == "danger_bilateral":
        danger.update(left=ODOUR_HIGH, right=ODOUR_HIGH)
    return food, danger


def make_context(condition: str) -> dict[str, Any]:
    food, danger = _odor_pair(condition)
    return {
        "curriculum_stage": 1,  # no Stage 2 wall/loop aversive stimulation
        "olfaction": {"model": OLFACTION_MODEL, "food": food, "danger": danger},
    }


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def run_condition(checkpoint: Path, condition: str) -> dict[str, Any]:
    brain = MaleCNSBrain(checkpoint=checkpoint, learning=False)
    brain.brain.weights_frozen = True
    neutral_frame = np.full((180, 320, 3), 128, dtype=np.uint8)
    for _ in range(WARMUP_FRAMES):
        brain.decide(neutral_frame, reinforcement="none", context=None)

    actions: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    context = make_context(condition)
    for index in range(PROBE_FRAMES):
        decision = brain.decide(
            neutral_frame, reinforcement="none", context=context
        )
        telemetry = decision.telemetry
        actions[str(decision.action)] += 1

        # Check that the experiment did not accidentally add reward/aversive
        # stimulation or control a decoded action.
        if telemetry.get("external_reinforcement") != "none":
            raise RuntimeError("external reinforcement escaped the isolation gate")
        if telemetry.get("frontal_wall_triggered") or telemetry.get("sensory_loop_triggered"):
            raise RuntimeError("non-olfactory aversive cue escaped the isolation gate")
        rows.append({
            "frame": index,
            "action": str(decision.action),
            "dna02_centered_difference_hz": float(telemetry["decoder_difference_hz"]),
            "dna02_raw_difference_hz": float(telemetry["raw_difference_hz"]),
            "dna03_raw_difference_hz": float(
                telemetry["steering_observer_difference_hz"]
            ),
            "dna02_left_hz": float(telemetry["left_hz"]),
            "dna02_right_hz": float(telemetry["right_hz"]),
            "dna03_left_hz": float(telemetry["steering_observer_left_hz"]),
            "dna03_right_hz": float(telemetry["steering_observer_right_hz"]),
            "food_orn_spikes": int(telemetry["food_odor_spikes"]),
            "danger_orn_spikes": int(telemetry["danger_odor_spikes"]),
            "food_olfaction_left": float(telemetry["olfaction"]["food_left"]),
            "food_olfaction_right": float(telemetry["olfaction"]["food_right"]),
            "danger_olfaction_left": float(telemetry["olfaction"]["danger_left"]),
            "danger_olfaction_right": float(telemetry["olfaction"]["danger_right"]),
        })

    return {
        "condition": condition,
        "frames": PROBE_FRAMES,
        "action_counts_observed_only": dict(sorted(actions.items())),
        "mean_dna02_centered_difference_hz": _mean([
            row["dna02_centered_difference_hz"] for row in rows
        ]),
        "mean_dna02_raw_difference_hz": _mean([
            row["dna02_raw_difference_hz"] for row in rows
        ]),
        "mean_dna03_raw_difference_hz": _mean([
            row["dna03_raw_difference_hz"] for row in rows
        ]),
        "mean_food_orn_spikes": _mean([row["food_orn_spikes"] for row in rows]),
        "mean_danger_orn_spikes": _mean([
            row["danger_orn_spikes"] for row in rows
        ]),
        "rows": rows,
    }


def run_probe(checkpoint: Path) -> dict[str, Any]:
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    sha_before = _sha256_file(checkpoint)
    results = {name: run_condition(checkpoint, name) for name in CONDITIONS}
    sha_after = _sha256_file(checkpoint)
    if sha_before != sha_after:
        raise RuntimeError("production checkpoint changed during isolated test")

    def contrast(left: str, right: str, metric: str) -> float:
        return (
            float(results[right][metric]) - float(results[left][metric])
        )

    contrasts = {}
    for odor in ("food", "danger"):
        for channel in (
            "mean_dna02_centered_difference_hz",
            "mean_dna02_raw_difference_hz",
            "mean_dna03_raw_difference_hz",
        ):
            contrasts[f"{odor}_right_minus_left__{channel}"] = contrast(
                f"{odor}_left", f"{odor}_right", channel
            )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "source_checkpoint_sha256": sha_before,
        "source_checkpoint_unchanged": True,
        "learning_enabled": False,
        "production_checkpoint_mutated": False,
        "maze_actions_executed": False,
        "stonkfly_commit": STONKFLY_COMMIT,
        "conditions": results,
        "contrasts": contrasts,
        "claim_limits": {
            "olfactory_steering_causality_validated": False,
            "navigation_improvement_verified": False,
            "decoder_change_authorized": False,
            "behavioral_promotion_authorized": False,
        },
    }
    report["receipt_sha256"] = _digest_json(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-checkpoint", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = run_probe(Path(args.source_checkpoint))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("OLFACTION_STEERING_CAUSAL_SCREEN_PASS", report["receipt_sha256"])
    print(json.dumps(report["contrasts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
