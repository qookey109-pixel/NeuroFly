from __future__ import annotations

import gc
import json
from pathlib import Path

import numpy as np

from neurofly.brain_runtime import MaleCNSBrain
from neurofly.olfaction import OLFACTION_MODEL

CANDIDATES = ("DNp09", "DNg97", "DNg100", "DNb02", "DNa01", "DNa02")
CONDITIONS = {
    "no_food": (0.0, 0.0),
    "food_symmetric": (1.0, 1.0),
    "food_left": (1.0, 0.0),
    "food_right": (0.0, 1.0),
}
DECISIONS_PER_CONDITION = 8


def candidate_indices(brain: MaleCNSBrain) -> dict[str, np.ndarray]:
    from stonkfly.neural.common import annotations

    table = annotations(brain.brain.ids)
    types = table.type.fillna("").astype(str)
    return {
        neuron_type: np.flatnonzero(types.eq(neuron_type).to_numpy())
        for neuron_type in CANDIDATES
    }


def summarize(brain: MaleCNSBrain, indices: dict[str, np.ndarray]) -> dict:
    counts = brain.brain.counts
    seconds = brain.neural_ms / 1000.0
    rows = {}
    for neuron_type, idx in indices.items():
        spikes = int(counts[idx].sum()) if len(idx) else 0
        mean_hz = float(np.mean(counts[idx]) / seconds) if len(idx) else 0.0
        rows[neuron_type] = {
            "cell_count": int(len(idx)),
            "spikes": spikes,
            "mean_hz": mean_hz,
            "body_ids": [str(brain.brain.ids[i]) for i in idx],
        }
    return rows


def run_condition(name: str, left: float, right: float) -> dict:
    brain = MaleCNSBrain(learning=False)
    idx = candidate_indices(brain)
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    context = {
        "olfaction": {
            "model": OLFACTION_MODEL,
            "food": {"left": left, "right": right},
            "danger": {"left": 0.0, "right": 0.0},
        }
    }

    decisions = []
    totals = {
        neuron_type: {
            "cell_count": int(len(indices)),
            "spikes": 0,
            "mean_hz_sum": 0.0,
            "active_decisions": 0,
            "body_ids": [str(brain.brain.ids[i]) for i in indices],
        }
        for neuron_type, indices in idx.items()
    }

    for step in range(DECISIONS_PER_CONDITION):
        decision = brain.decide(frame, context=context)
        rows = summarize(brain, idx)
        for neuron_type, row in rows.items():
            totals[neuron_type]["spikes"] += row["spikes"]
            totals[neuron_type]["mean_hz_sum"] += row["mean_hz"]
            if row["spikes"] > 0:
                totals[neuron_type]["active_decisions"] += 1
        decisions.append(
            {
                "step": step + 1,
                "decoder_action": decision.action,
                "food_left": left,
                "food_right": right,
                "candidate_activity": rows,
            }
        )

    for row in totals.values():
        row["mean_hz"] = row.pop("mean_hz_sum") / DECISIONS_PER_CONDITION

    result = {
        "food_left": left,
        "food_right": right,
        "decisions": DECISIONS_PER_CONDITION,
        "totals": totals,
        "per_decision": decisions,
    }
    del brain
    gc.collect()
    return result


def main() -> None:
    payload = {
        "schema": "neurofly-food-to-walking-dn-probe-v1",
        "purpose": "Measure candidate walking-DN activity under sensory food odor only; no direct motor command.",
        "learning": False,
        "decisions_per_condition": DECISIONS_PER_CONDITION,
        "conditions": {},
    }
    for name, (left, right) in CONDITIONS.items():
        print(f"Running {name}: food=({left}, {right})", flush=True)
        payload["conditions"][name] = run_condition(name, left, right)

    out = Path("artifacts/food_to_walking_dn_probe.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
