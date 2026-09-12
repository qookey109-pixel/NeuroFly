from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .brain_runtime import MaleCNSBrain
from .curriculum import CurriculumMazeEnvironment
from .olfaction import OLFACTION_MODEL
from .upstream import STONKFLY_COMMIT


SCHEMA = "neurofly-olfaction-calibration-v1"

CONDITIONS: dict[str, dict[str, tuple[float, float]]] = {
    "odor_off": {"food": (0.0, 0.0), "danger": (0.0, 0.0)},
    "food_left": {"food": (1.0, 0.0), "danger": (0.0, 0.0)},
    "food_right": {"food": (0.0, 1.0), "danger": (0.0, 0.0)},
    "danger_left": {"food": (0.0, 0.0), "danger": (1.0, 0.0)},
    "danger_right": {"food": (0.0, 0.0), "danger": (0.0, 1.0)},
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _odor_context(spec: dict[str, tuple[float, float]]) -> dict[str, Any]:
    food_left, food_right = spec["food"]
    danger_left, danger_right = spec["danger"]
    return {
        "olfaction": {
            "model": OLFACTION_MODEL,
            "engineered_proxy": True,
            "food": {"left": food_left, "right": food_right},
            "danger": {"left": danger_left, "right": danger_right},
        }
    }


def _side_metrics(brain: MaleCNSBrain, indices: Any) -> dict[str, float | int]:
    counts = brain.brain.counts[indices]
    total = int(counts.sum())
    neurons = int(len(indices))
    return {
        "neurons": neurons,
        "spikes": total,
        "spikes_per_neuron": 0.0 if neurons == 0 else total / neurons,
    }


def _condition(
    *,
    name: str,
    spec: dict[str, tuple[float, float]],
    checkpoint: Path,
    frame: Any,
    neural_ms: float,
    odor_current: float,
) -> dict[str, Any]:
    brain = MaleCNSBrain(
        checkpoint=checkpoint,
        learning=False,
        neural_ms=neural_ms,
        odor_current=odor_current,
    )
    # Stonkfly checkpoints preserve weights_frozen. Force the calibration state
    # after restore as an additional invariant; decide() also receives
    # learning=False so no plasticity update is permitted.
    brain.brain.weights_frozen = True
    memory_before = brain.brain.memory()
    decision = brain.decide(frame, "none", context=_odor_context(spec))
    memory_after = brain.brain.memory()
    if memory_before["sha256"] != memory_after["sha256"]:
        raise RuntimeError(f"Calibration condition {name} changed plastic weights")

    telemetry = decision.telemetry
    return {
        "condition": name,
        "input": {
            "food_left": spec["food"][0],
            "food_right": spec["food"][1],
            "danger_left": spec["danger"][0],
            "danger_right": spec["danger"][1],
        },
        "action": decision.action,
        "food": {
            "left": _side_metrics(brain, brain.food_orn_left),
            "right": _side_metrics(brain, brain.food_orn_right),
        },
        "danger": {
            "left": _side_metrics(brain, brain.danger_orn_left),
            "right": _side_metrics(brain, brain.danger_orn_right),
        },
        "decoder": {
            "left_hz": telemetry["left_hz"],
            "right_hz": telemetry["right_hz"],
            "difference_hz": telemetry["difference_hz"],
            "gate_spikes": telemetry["gate_spikes"],
        },
        "kc_spikes": telemetry["kc_spikes"],
        "total_spikes": telemetry["total_spikes"],
        "brain_ms": telemetry["brain_ms"],
        "compute_seconds": telemetry["compute_seconds"],
        "memory_sha256_before": memory_before["sha256"],
        "memory_sha256_after": memory_after["sha256"],
        "weights_frozen": bool(brain.brain.weights_frozen),
        "olfaction_report": brain.olfaction_report,
    }


def _channel_gate(
    *,
    results: dict[str, dict[str, Any]],
    condition: str,
    channel: str,
    side: str,
) -> dict[str, Any]:
    other = "right" if side == "left" else "left"
    baseline = float(results["odor_off"][channel][side]["spikes_per_neuron"])
    stimulated = float(results[condition][channel][side]["spikes_per_neuron"])
    contralateral = float(results[condition][channel][other]["spikes_per_neuron"])
    delta = stimulated - baseline
    return {
        "condition": condition,
        "channel": channel,
        "side": side,
        "baseline_spikes_per_neuron": baseline,
        "stimulated_spikes_per_neuron": stimulated,
        "contralateral_spikes_per_neuron": contralateral,
        "delta_vs_baseline": delta,
        "positive_delta": delta > 0.0,
        "ipsilateral_gt_contralateral": stimulated > contralateral,
        "passed": delta > 0.0 and stimulated > contralateral,
    }


def run_calibration(
    *,
    checkpoint: str | Path,
    output: str | Path,
    seed: int = 109,
    neural_ms: float = 500.0,
    odor_current: float = 8.0,
) -> dict[str, Any]:
    checkpoint = Path(checkpoint)
    if not checkpoint.is_file():
        raise FileNotFoundError(f"MaleCNS checkpoint not found: {checkpoint}")
    if neural_ms <= 0:
        raise ValueError("neural_ms must be > 0")
    if odor_current <= 0:
        raise ValueError("odor_current must be > 0")

    environment = CurriculumMazeEnvironment(seed=seed)
    frame = environment.render_rgb()
    checkpoint_sha256 = _sha256_file(checkpoint)

    results = {
        name: _condition(
            name=name,
            spec=spec,
            checkpoint=checkpoint,
            frame=frame,
            neural_ms=neural_ms,
            odor_current=odor_current,
        )
        for name, spec in CONDITIONS.items()
    }

    gates = [
        _channel_gate(results=results, condition="food_left", channel="food", side="left"),
        _channel_gate(results=results, condition="food_right", channel="food", side="right"),
        _channel_gate(results=results, condition="danger_left", channel="danger", side="left"),
        _channel_gate(results=results, condition="danger_right", channel="danger", side="right"),
    ]

    memory_shas = {
        condition["memory_sha256_before"]
        for condition in results.values()
    }
    matched_checkpoint = len(memory_shas) == 1
    all_frozen = all(condition["weights_frozen"] for condition in results.values())
    passed = matched_checkpoint and all_frozen and all(gate["passed"] for gate in gates)

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "passed": passed,
        "stonkfly_commit": STONKFLY_COMMIT,
        "olfaction_model": OLFACTION_MODEL,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": checkpoint_sha256,
        "seed": seed,
        "neural_ms": neural_ms,
        "odor_current": odor_current,
        "plasticity_frozen": all_frozen,
        "matched_checkpoint_memory": matched_checkpoint,
        "conditions": results,
        "gates": gates,
        "interpretation": (
            "This receipt validates engineered odor transduction against a matched "
            "odor-off baseline. It does not demonstrate navigation learning."
        ),
    }
    body["receipt_sha256"] = _digest_json(body)

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".partial")
    temporary.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    temporary.replace(output)
    return body


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run matched-state MaleCNS olfactory calibration")
    parser.add_argument("--checkpoint", default="runs/free-malecns/brain.npz")
    parser.add_argument("--output", default="runs/free-malecns/olfaction-calibration.json")
    parser.add_argument("--seed", type=int, default=109)
    parser.add_argument("--neural-ms", type=float, default=500.0)
    parser.add_argument("--odor-current", type=float, default=8.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_calibration(
        checkpoint=args.checkpoint,
        output=args.output,
        seed=args.seed,
        neural_ms=args.neural_ms,
        odor_current=args.odor_current,
    )
    print(json.dumps({
        "passed": result["passed"],
        "checkpoint_sha256": result["checkpoint_sha256"],
        "receipt_sha256": result["receipt_sha256"],
        "gates": result["gates"],
    }, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
