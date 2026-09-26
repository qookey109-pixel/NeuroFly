from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

from neurofly.brain_runtime import MaleCNSBrain, _bilateral_type_indices
from neurofly.olfaction import OLFACTION_MODEL

CONDITIONS = {
    "no_food": (0.0, 0.0),
    "food_symmetric": (1.0, 1.0),
    "food_left": (1.0, 0.0),
    "food_right": (0.0, 1.0),
}
THRESHOLDS_HZ = (2.0, 20.0, 30.0, 40.0, 60.0)
DECISIONS = 20
DRIVE_TYPE = "DNb05"


def candidate_action(
    *,
    steering_left_hz: float,
    steering_right_hz: float,
    steering_spikes: int,
    drive_spikes: int,
    threshold_hz: float,
) -> str:
    if drive_spikes <= 0 and steering_spikes <= 0:
        return "HOLD"
    difference = steering_right_hz - steering_left_hz
    if steering_spikes > 0 and difference >= threshold_hz:
        return "TURN_RIGHT"
    if steering_spikes > 0 and difference <= -threshold_hz:
        return "TURN_LEFT"
    if drive_spikes > 0:
        return "FORWARD"
    return "HOLD"


def main() -> None:
    results = {}
    for condition, (food_left, food_right) in CONDITIONS.items():
        brain = MaleCNSBrain(learning=False)
        table = __import__("stonkfly.neural.common", fromlist=["annotations"]).annotations(brain.brain.ids)
        drive_left, drive_right, report = _bilateral_type_indices(np, table, DRIVE_TYPE)
        drive = np.unique(np.concatenate((drive_left, drive_right)))
        if not len(drive):
            raise RuntimeError(f"{DRIVE_TYPE} is missing: {report}")

        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        context = {
            "olfaction": {
                "model": OLFACTION_MODEL,
                "food": {"left": food_left, "right": food_right},
                "danger": {"left": 0.0, "right": 0.0},
            }
        }
        threshold_actions = {str(t): Counter() for t in THRESHOLDS_HZ}
        samples = []
        seconds = brain.neural_ms / 1000.0
        for step in range(DECISIONS):
            current = brain.decide(frame, context=context)
            counts = brain.brain.counts
            left_hz = float(np.mean(counts[brain.steering_left]) / seconds)
            right_hz = float(np.mean(counts[brain.steering_right]) / seconds)
            steering_spikes = int(
                counts[brain.steering_left].sum() + counts[brain.steering_right].sum()
            )
            drive_spikes = int(counts[drive].sum())
            for threshold in THRESHOLDS_HZ:
                action = candidate_action(
                    steering_left_hz=left_hz,
                    steering_right_hz=right_hz,
                    steering_spikes=steering_spikes,
                    drive_spikes=drive_spikes,
                    threshold_hz=threshold,
                )
                threshold_actions[str(threshold)][action] += 1
            samples.append(
                {
                    "step": step + 1,
                    "v2_action": current.action,
                    "dna02_left_hz": left_hz,
                    "dna02_right_hz": right_hz,
                    "dna02_difference_hz": right_hz - left_hz,
                    "dna02_spikes": steering_spikes,
                    "dnb05_spikes": drive_spikes,
                }
            )

        results[condition] = {
            "food_left": food_left,
            "food_right": food_right,
            "drive_type": DRIVE_TYPE,
            "drive_report": report,
            "threshold_actions": {k: dict(v) for k, v in threshold_actions.items()},
            "samples": samples,
        }

    payload = {
        "schema": "neurofly-walking-decoder-v3-threshold-scan-v1",
        "decisions_per_condition": DECISIONS,
        "thresholds_hz": list(THRESHOLDS_HZ),
        "results": results,
    }
    out = Path("artifacts/walking_decoder_v3_threshold_scan.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        c: r["threshold_actions"] for c, r in results.items()
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
