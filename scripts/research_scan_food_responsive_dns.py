from __future__ import annotations

import gc
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from neurofly.brain_runtime import MaleCNSBrain
from neurofly.olfaction import OLFACTION_MODEL

CONDITIONS = {
    "no_food": (0.0, 0.0),
    "food_symmetric": (1.0, 1.0),
    "food_left": (1.0, 0.0),
    "food_right": (0.0, 1.0),
}
DECISIONS_PER_CONDITION = 12


def dn_groups(brain: MaleCNSBrain) -> dict[str, np.ndarray]:
    from stonkfly.neural.common import annotations

    table = annotations(brain.brain.ids)
    types = table.type.fillna("").astype(str)
    groups: dict[str, np.ndarray] = {}
    for neuron_type in sorted({t for t in types.tolist() if t.startswith("DN")}):
        idx = np.flatnonzero(types.eq(neuron_type).to_numpy())
        if len(idx):
            groups[neuron_type] = idx
    return groups


def run_condition(left: float, right: float) -> dict:
    brain = MaleCNSBrain(learning=False)
    groups = dn_groups(brain)
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    context = {
        "olfaction": {
            "model": OLFACTION_MODEL,
            "food": {"left": left, "right": right},
            "danger": {"left": 0.0, "right": 0.0},
        }
    }

    totals = {
        neuron_type: {
            "cell_count": int(len(indices)),
            "spikes": 0,
            "active_decisions": 0,
            "mean_hz_sum": 0.0,
            "body_ids": [str(brain.brain.ids[i]) for i in indices],
        }
        for neuron_type, indices in groups.items()
    }

    actions = defaultdict(int)
    seconds = brain.neural_ms / 1000.0
    for _ in range(DECISIONS_PER_CONDITION):
        decision = brain.decide(frame, context=context)
        actions[decision.action] += 1
        counts = brain.brain.counts
        for neuron_type, indices in groups.items():
            spikes = int(counts[indices].sum())
            hz = float(np.mean(counts[indices]) / seconds)
            totals[neuron_type]["spikes"] += spikes
            totals[neuron_type]["mean_hz_sum"] += hz
            if spikes > 0:
                totals[neuron_type]["active_decisions"] += 1

    for row in totals.values():
        row["mean_hz"] = row.pop("mean_hz_sum") / DECISIONS_PER_CONDITION

    result = {
        "food_left": left,
        "food_right": right,
        "decisions": DECISIONS_PER_CONDITION,
        "actions": dict(actions),
        "dn_type_count": len(groups),
        "types": totals,
    }
    del brain
    gc.collect()
    return result


def main() -> None:
    conditions = {
        name: run_condition(left, right)
        for name, (left, right) in CONDITIONS.items()
    }
    baseline = conditions["no_food"]["types"]

    comparison = []
    all_types = sorted(
        set().union(*(set(c["types"]) for c in conditions.values()))
    )
    for neuron_type in all_types:
        base = baseline.get(neuron_type, {"spikes": 0, "active_decisions": 0, "mean_hz": 0.0})
        row = {
            "type": neuron_type,
            "cell_count": conditions["food_symmetric"]["types"].get(neuron_type, {}).get("cell_count", 0),
            "baseline_spikes": base["spikes"],
            "baseline_active_decisions": base["active_decisions"],
            "food_symmetric_spikes": conditions["food_symmetric"]["types"].get(neuron_type, {}).get("spikes", 0),
            "food_left_spikes": conditions["food_left"]["types"].get(neuron_type, {}).get("spikes", 0),
            "food_right_spikes": conditions["food_right"]["types"].get(neuron_type, {}).get("spikes", 0),
        }
        row["food_symmetric_delta_spikes"] = row["food_symmetric_spikes"] - row["baseline_spikes"]
        row["food_left_delta_spikes"] = row["food_left_spikes"] - row["baseline_spikes"]
        row["food_right_delta_spikes"] = row["food_right_spikes"] - row["baseline_spikes"]
        row["max_food_delta_spikes"] = max(
            row["food_symmetric_delta_spikes"],
            row["food_left_delta_spikes"],
            row["food_right_delta_spikes"],
        )
        body_ids = conditions["food_symmetric"]["types"].get(neuron_type, {}).get("body_ids", [])
        row["body_ids"] = body_ids
        comparison.append(row)

    comparison.sort(
        key=lambda x: (
            x["max_food_delta_spikes"],
            x["food_symmetric_delta_spikes"],
            x["food_symmetric_spikes"],
        ),
        reverse=True,
    )

    payload = {
        "schema": "neurofly-food-responsive-dn-scan-v1",
        "purpose": "Discover MaleCNS descending-neuron types whose activity increases under sensory food odor; no direct motor command.",
        "learning": False,
        "decisions_per_condition": DECISIONS_PER_CONDITION,
        "conditions": conditions,
        "ranked_food_response": comparison,
        "top_positive": [row for row in comparison if row["max_food_delta_spikes"] > 0][:40],
    }
    out = Path("artifacts/food_responsive_dn_scan.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "schema": payload["schema"],
        "decisions_per_condition": DECISIONS_PER_CONDITION,
        "top_positive": payload["top_positive"][:20],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
