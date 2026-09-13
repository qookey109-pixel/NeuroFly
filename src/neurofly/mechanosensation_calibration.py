from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .brain_runtime import MaleCNSBrain
from .curriculum import CurriculumMazeEnvironment
from .mechanosensation import MECHANOSENSATION_MODEL, virtual_antennal_mechanosensation
from .upstream import STONKFLY_COMMIT


CALIBRATION_SCHEMA = "neurofly-mechanosensation-calibration-v1"

# The fly faces RIGHT in the matched calibration scene. These are world-frame air
# velocity vectors, not 'wind-from' compass bearings.
CONDITIONS: dict[str, dict[str, float]] = {
    "airflow_off": {"x": 0.0, "y": 0.0},
    "headwind": {"x": -1.0, "y": 0.0},
    "tailwind": {"x": 1.0, "y": 0.0},
    "crosswind_right": {"x": 0.0, "y": 1.0},
    "crosswind_left": {"x": 0.0, "y": -1.0},
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


def _bounded_level(payload: dict[str, Any], side: str, channel: str) -> float:
    try:
        value = float((payload.get(side) or {}).get(channel, 0.0))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid mechanosensation level: {side}.{channel}") from exc
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"Mechanosensation level {side}.{channel} must be within [0, 1]")
    return value


def _resolve_jon_indices(brain: MaleCNSBrain) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve broad bilateral JO-C/JO-E candidates from exact retained annotations."""

    from stonkfly.neural.common import annotations

    np = brain.np
    a = annotations(brain.brain.ids)
    types = a.type.fillna("").astype(str)
    sides = a.somaSide.fillna("").astype(str).str.upper()
    instances = (
        a["instance"].fillna("").astype(str)
        if "instance" in a.columns
        else types.map(lambda _: "")
    )

    groups: dict[str, Any] = {}
    report: dict[str, Any] = {}
    for key, prefix in (("jo_c", "JO-C"), ("jo_e", "JO-E")):
        family = types.str.startswith(prefix)
        left_by_soma = family & sides.eq("L")
        right_by_soma = family & sides.eq("R")
        left_by_instance = family & instances.str.endswith("_L")
        right_by_instance = family & instances.str.endswith("_R")
        left_mask = left_by_soma | left_by_instance
        right_mask = right_by_soma | right_by_instance
        unresolved = family & ~(left_mask | right_mask)

        left = np.flatnonzero(left_mask.to_numpy())
        right = np.flatnonzero(right_mask.to_numpy())
        if len(left) == 0 or len(right) == 0 or int(unresolved.sum()) != 0:
            raise RuntimeError(
                f"Mechanosensation annotation gate failed for {prefix}: "
                f"left={len(left)} right={len(right)} unresolved={int(unresolved.sum())}"
            )

        groups[f"{key}_left"] = left
        groups[f"{key}_right"] = right
        report[key] = {
            "prefix": prefix,
            "total": int(family.sum()),
            "left": int(len(left)),
            "right": int(len(right)),
            "unresolved": int(unresolved.sum()),
            "types": sorted(set(types[family].tolist())),
            "side_policy": "somaSide_then_curated_instance_suffix",
        }
    return groups, report


def _side_metrics(brain: MaleCNSBrain, indices: Any) -> dict[str, float | int]:
    counts = brain.brain.counts[indices]
    total = int(counts.sum())
    neurons = int(len(indices))
    return {
        "neurons": neurons,
        "spikes": total,
        "spikes_per_neuron": 0.0 if neurons == 0 else total / neurons,
    }


def _mechanosensory_pulses(
    *,
    groups: dict[str, Any],
    sensory: dict[str, Any],
    current: float,
) -> tuple[list[tuple[Any, float]], dict[str, float]]:
    levels = {
        "jo_c_left": _bounded_level(sensory, "left", "jo_c"),
        "jo_c_right": _bounded_level(sensory, "right", "jo_c"),
        "jo_e_left": _bounded_level(sensory, "left", "jo_e"),
        "jo_e_right": _bounded_level(sensory, "right", "jo_e"),
    }
    pulses: list[tuple[Any, float]] = []
    for name, level in levels.items():
        if level > 0.0 and current > 0.0:
            pulses.append((groups[name], current * level))
    return pulses, levels


def _condition(
    *,
    name: str,
    airflow: dict[str, float],
    baseline_checkpoint: Path,
    frame: Any,
    fly: dict[str, Any],
    enemies: list[dict[str, int]],
    neural_ms: float,
    current: float,
) -> dict[str, Any]:
    brain = MaleCNSBrain(
        checkpoint=baseline_checkpoint,
        learning=False,
        neural_ms=neural_ms,
    )
    brain.brain.weights_frozen = True
    groups, annotation_report = _resolve_jon_indices(brain)

    sensory = virtual_antennal_mechanosensation(fly=fly, airflow=airflow)
    if not sensory.get("available"):
        raise RuntimeError(f"Calibration condition {name} did not produce mechanosensory input")
    pulses, levels = _mechanosensory_pulses(
        groups=groups,
        sensory=sensory,
        current=current,
    )

    visual_context = {"fly": dict(fly), "enemies": [dict(item) for item in enemies]}
    rgb, _ = brain._visual_input(frame, visual_context)
    b = brain.brain
    np = brain.np
    counts = np.zeros(b.n, dtype=np.int32)
    remaining = round(brain.neural_ms / b.dt)
    compute_seconds = 0.0
    memory_before = b.memory()

    while remaining:
        n = min(remaining, round(brain.neural_bin_ms / b.dt))
        current_counts, elapsed = b.rgb_step(
            rgb,
            n * b.dt,
            learning=False,
            stimulation=pulses or None,
        )
        counts += current_counts
        compute_seconds += elapsed
        remaining -= n

    b.counts[:] = counts
    action, decoder = brain._decode(counts)
    memory_after = b.memory()
    if memory_before["sha256"] != memory_after["sha256"]:
        raise RuntimeError(f"Mechanosensation calibration condition {name} changed plastic weights")

    return {
        "condition": name,
        "airflow": {"x": float(airflow["x"]), "y": float(airflow["y"])},
        "transduced_levels": levels,
        "action": action,
        "jo_c": {
            "left": _side_metrics(brain, groups["jo_c_left"]),
            "right": _side_metrics(brain, groups["jo_c_right"]),
        },
        "jo_e": {
            "left": _side_metrics(brain, groups["jo_e_left"]),
            "right": _side_metrics(brain, groups["jo_e_right"]),
        },
        "decoder": decoder,
        "total_spikes": int(counts.sum()),
        "compute_seconds": compute_seconds,
        "memory_sha256_before": memory_before["sha256"],
        "memory_sha256_after": memory_after["sha256"],
        "weights_frozen": bool(b.weights_frozen),
        "annotation_report": annotation_report,
    }


def _positive_gate(
    *,
    results: dict[str, dict[str, Any]],
    condition: str,
    family: str,
    side: str,
    compare_side: str | None = None,
) -> dict[str, Any]:
    baseline = float(results["airflow_off"][family][side]["spikes_per_neuron"])
    stimulated = float(results[condition][family][side]["spikes_per_neuron"])
    delta = stimulated - baseline
    comparison = None
    side_selective = True
    if compare_side is not None:
        comparison = float(results[condition][family][compare_side]["spikes_per_neuron"])
        side_selective = stimulated > comparison
    return {
        "condition": condition,
        "family": family,
        "side": side,
        "baseline_spikes_per_neuron": baseline,
        "stimulated_spikes_per_neuron": stimulated,
        "delta_vs_baseline": delta,
        "compare_side": compare_side,
        "compare_spikes_per_neuron": comparison,
        "positive_delta": delta > 0.0,
        "side_selective": side_selective,
        "passed": delta > 0.0 and side_selective,
    }


def evaluate_response_gates(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Evaluate the predeclared response expectations for the five airflow conditions."""

    return [
        _positive_gate(results=results, condition="headwind", family="jo_e", side="left"),
        _positive_gate(results=results, condition="headwind", family="jo_e", side="right"),
        _positive_gate(results=results, condition="tailwind", family="jo_c", side="left"),
        _positive_gate(results=results, condition="tailwind", family="jo_c", side="right"),
        _positive_gate(
            results=results,
            condition="crosswind_right",
            family="jo_c",
            side="left",
            compare_side="right",
        ),
        _positive_gate(
            results=results,
            condition="crosswind_right",
            family="jo_e",
            side="right",
            compare_side="left",
        ),
        _positive_gate(
            results=results,
            condition="crosswind_left",
            family="jo_c",
            side="right",
            compare_side="left",
        ),
        _positive_gate(
            results=results,
            condition="crosswind_left",
            family="jo_e",
            side="left",
            compare_side="right",
        ),
    ]


def run_calibration(
    *,
    output: str | Path,
    seed: int = 109,
    neural_ms: float = 200.0,
    mechanosensation_current: float = 8.0,
) -> dict[str, Any]:
    if neural_ms <= 0:
        raise ValueError("neural_ms must be > 0")
    if not math.isfinite(float(mechanosensation_current)) or mechanosensation_current <= 0:
        raise ValueError("mechanosensation_current must be finite and > 0")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    baseline_checkpoint = output.parent / "mechanosensation-calibration-baseline.npz"

    environment = CurriculumMazeEnvironment(seed=seed)
    environment.fly = {"x": int(environment.fly["x"]), "y": int(environment.fly["y"]), "dir": "RIGHT"}
    frame = environment.render_rgb()
    fly = dict(environment.fly)
    enemies = [dict(item) for item in environment.enemies]

    baseline_brain = MaleCNSBrain(learning=False, neural_ms=neural_ms)
    baseline_brain.brain.weights_frozen = True
    baseline_brain.brain.checkpoint(baseline_checkpoint)
    baseline_checkpoint_sha256 = _sha256_file(baseline_checkpoint)

    try:
        results = {
            name: _condition(
                name=name,
                airflow=airflow,
                baseline_checkpoint=baseline_checkpoint,
                frame=frame,
                fly=fly,
                enemies=enemies,
                neural_ms=neural_ms,
                current=mechanosensation_current,
            )
            for name, airflow in CONDITIONS.items()
        }

        gates = evaluate_response_gates(results)
        memory_shas = {
            condition["memory_sha256_before"]
            for condition in results.values()
        }
        matched_state = len(memory_shas) == 1
        all_frozen = all(condition["weights_frozen"] for condition in results.values())
        passed = matched_state and all_frozen and all(gate["passed"] for gate in gates)

        body: dict[str, Any] = {
            "schema": CALIBRATION_SCHEMA,
            "passed": passed,
            "runtime_stimulation_enabled": False,
            "stonkfly_commit": STONKFLY_COMMIT,
            "mechanosensation_model": MECHANOSENSATION_MODEL,
            "baseline_checkpoint_sha256": baseline_checkpoint_sha256,
            "seed": seed,
            "neural_ms": neural_ms,
            "mechanosensation_current": mechanosensation_current,
            "plasticity_frozen": all_frozen,
            "matched_baseline_memory": matched_state,
            "conditions": results,
            "gates": gates,
            "interpretation": (
                "PASS validates the engineered JO-C/JO-E current-routing response under "
                "matched frozen-weight conditions. It does not validate antennal biomechanics, "
                "natural wind tuning, navigation learning, or behavioral benefit."
            ),
        }
        body["receipt_sha256"] = _digest_json(body)

        temporary = output.with_suffix(output.suffix + ".partial")
        temporary.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
        temporary.replace(output)
        return body
    finally:
        baseline_checkpoint.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run matched frozen-weight MaleCNS mechanosensation calibration"
    )
    parser.add_argument(
        "--output",
        default="runs/mechanosensation/mechanosensation-calibration.json",
    )
    parser.add_argument("--seed", type=int, default=109)
    parser.add_argument("--neural-ms", type=float, default=200.0)
    parser.add_argument("--current", type=float, default=8.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_calibration(
        output=args.output,
        seed=args.seed,
        neural_ms=args.neural_ms,
        mechanosensation_current=args.current,
    )
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "receipt_sha256": result["receipt_sha256"],
                "gates": result["gates"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
