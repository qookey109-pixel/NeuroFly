from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .brain_runtime import MaleCNSBrain
from .curriculum import CurriculumMazeEnvironment
from .tactile import TACTILE_MODEL
from .upstream import STONKFLY_COMMIT


CALIBRATION_SCHEMA = "neurofly-tactile-current-calibration-v1"
TACTILE_CROSSWALK_SCHEMA = "neurofly-tactile-leg-functional-crosswalk-v0.2"
EXPECTED_TYPE_COUNTS = {
    "SNta20": 156,
    "SNta26": 31,
    "SNta27": 47,
    "SNta28": 74,
    "SNta34": 54,
    "SNta37": 228,
}
EXPECTED_TOTAL = 590
ACCEPTED_SUBCLASSES = {"leg", "mechanosensory bristle"}
DEFAULT_CROSSWALK = (
    Path(__file__).resolve().parents[2] / "data" / "tactile_leg_functional_crosswalk_v02.json"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest_json(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _load_crosswalk(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    if payload.get("schema") != TACTILE_CROSSWALK_SCHEMA:
        raise RuntimeError("Unexpected tactile functional crosswalk schema")
    if payload.get("source_population_class") != "mechanosensory_tactile":
        raise RuntimeError("Tactile calibration requires mechanosensory_tactile source class")
    if payload.get("stimulation_enabled") is not False:
        raise RuntimeError("Crosswalk must remain non-authorizing during calibration")
    if payload.get("runtime_transduction_enabled") is not False:
        raise RuntimeError("Crosswalk runtime transduction flag must remain false during calibration")

    mappings = payload.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise RuntimeError("Tactile crosswalk has no mappings")
    mapped_types = [str(item.get("male_cns_type") or "") for item in mappings]
    if set(mapped_types) != set(EXPECTED_TYPE_COUNTS) or len(mapped_types) != len(EXPECTED_TYPE_COUNTS):
        raise RuntimeError(f"Unexpected tactile crosswalk types: {mapped_types}")
    for mapping in mappings:
        if mapping.get("functional_class") != "leg_external_touch_candidate":
            raise RuntimeError(f"Unexpected tactile functional class: {mapping}")
        if mapping.get("stimulation_authorized") is not False:
            raise RuntimeError("Tactile crosswalk mapping unexpectedly authorizes stimulation")
    return payload


def _resolve_groups(
    brain: MaleCNSBrain,
    crosswalk: dict[str, Any],
) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    """Resolve the exact six-type / 590-neuron tactile population from pinned annotations."""

    from stonkfly.neural.common import annotations

    np = brain.np
    a = annotations(brain.brain.ids)
    types = a.type.fillna("").astype(str)
    classes = a["class"].fillna("").astype(str).str.lower()
    subclasses = a["subclass"].fillna("").astype(str).str.lower()

    groups: dict[str, Any] = {}
    report: dict[str, Any] = {}
    selected_mask = np.zeros(len(a), dtype=bool)

    for neuron_type in sorted(EXPECTED_TYPE_COUNTS):
        type_mask = types.eq(neuron_type)
        non_tactile = type_mask & ~classes.eq("mechanosensory_tactile")
        if int(non_tactile.sum()) != 0:
            raise RuntimeError(
                f"Mapped tactile type {neuron_type} has non-tactile retained rows: "
                f"{int(non_tactile.sum())}"
            )

        tactile_rows = type_mask & classes.eq("mechanosensory_tactile")
        disallowed_subclass = tactile_rows & ~subclasses.isin(ACCEPTED_SUBCLASSES)
        if int(disallowed_subclass.sum()) != 0:
            raise RuntimeError(
                f"Mapped tactile type {neuron_type} has disallowed subclasses: "
                f"{int(disallowed_subclass.sum())}"
            )

        indices = np.flatnonzero(tactile_rows.to_numpy())
        expected = EXPECTED_TYPE_COUNTS[neuron_type]
        if len(indices) != expected:
            raise RuntimeError(
                f"Prepared MaleCNS {neuron_type} count changed: expected={expected} actual={len(indices)}"
            )

        groups[neuron_type] = indices
        selected_mask |= tactile_rows.to_numpy()
        report[neuron_type] = {
            "neurons": int(len(indices)),
            "subclasses": sorted(set(subclasses[tactile_rows].tolist())),
            "body_ids_sha256": hashlib.sha256(brain.brain.ids[indices].tobytes()).hexdigest(),
        }

    selected = np.flatnonzero(selected_mask)
    if len(selected) != EXPECTED_TOTAL:
        raise RuntimeError(
            f"Prepared MaleCNS selected tactile population changed: "
            f"expected={EXPECTED_TOTAL} actual={len(selected)}"
        )
    if sum(len(indices) for indices in groups.values()) != EXPECTED_TOTAL:
        raise RuntimeError("Tactile per-type groups do not sum to expected selected total")

    report["selected_total"] = {
        "neurons": int(len(selected)),
        "body_ids_sha256": hashlib.sha256(brain.brain.ids[selected].tobytes()).hexdigest(),
        "crosswalk_types": sorted(EXPECTED_TYPE_COUNTS),
    }
    return groups, selected, report


def _metrics(brain: MaleCNSBrain, indices: Any) -> dict[str, float | int]:
    counts = brain.brain.counts[indices]
    total = int(counts.sum())
    neurons = int(len(indices))
    return {
        "neurons": neurons,
        "spikes": total,
        "spikes_per_neuron": 0.0 if neurons == 0 else total / neurons,
        "active_neurons": int((counts > 0).sum()),
    }


def _condition(
    *,
    name: str,
    stimulate_contact: bool,
    current: float,
    baseline_checkpoint: Path,
    frame: Any,
    fly: dict[str, Any],
    enemies: list[dict[str, int]],
    neural_ms: float,
    crosswalk: dict[str, Any],
) -> dict[str, Any]:
    brain = MaleCNSBrain(
        checkpoint=baseline_checkpoint,
        learning=False,
        neural_ms=neural_ms,
    )
    brain.brain.weights_frozen = True
    groups, selected, annotation_report = _resolve_groups(brain, crosswalk)

    pulses: list[tuple[Any, float]] = []
    if stimulate_contact:
        pulses.append((selected, current))

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
        raise RuntimeError(f"Tactile calibration condition {name} changed plastic weights")

    return {
        "condition": name,
        "contact": bool(stimulate_contact),
        "external_current": current if stimulate_contact else 0.0,
        "selected_population": _metrics(brain, selected),
        "types": {
            neuron_type: _metrics(brain, indices)
            for neuron_type, indices in sorted(groups.items())
        },
        "action": action,
        "decoder": decoder,
        "total_spikes": int(counts.sum()),
        "compute_seconds": compute_seconds,
        "memory_sha256_before": memory_before["sha256"],
        "memory_sha256_after": memory_after["sha256"],
        "weights_frozen": bool(b.weights_frozen),
        "annotation_report": annotation_report,
    }


def _response_gate(
    results: dict[str, dict[str, Any]],
    neuron_type: str,
) -> dict[str, Any]:
    baseline = results["contact_off"]["types"][neuron_type]
    stimulated = results["front_contact"]["types"][neuron_type]
    baseline_rate = float(baseline["spikes_per_neuron"])
    stimulated_rate = float(stimulated["spikes_per_neuron"])
    delta = stimulated_rate - baseline_rate
    active = int(stimulated["active_neurons"])
    return {
        "neuron_type": neuron_type,
        "neurons": int(stimulated["neurons"]),
        "baseline_spikes": int(baseline["spikes"]),
        "stimulated_spikes": int(stimulated["spikes"]),
        "baseline_spikes_per_neuron": baseline_rate,
        "stimulated_spikes_per_neuron": stimulated_rate,
        "delta_spikes_per_neuron": delta,
        "stimulated_active_neurons": active,
        "positive_delta": delta > 0.0,
        "target_population_active": active > 0,
        "passed": delta > 0.0 and active > 0,
    }


def _selected_population_gate(results: dict[str, dict[str, Any]]) -> dict[str, Any]:
    baseline = results["contact_off"]["selected_population"]
    stimulated = results["front_contact"]["selected_population"]
    baseline_rate = float(baseline["spikes_per_neuron"])
    stimulated_rate = float(stimulated["spikes_per_neuron"])
    delta = stimulated_rate - baseline_rate
    active = int(stimulated["active_neurons"])
    return {
        "neurons": int(stimulated["neurons"]),
        "baseline_spikes": int(baseline["spikes"]),
        "stimulated_spikes": int(stimulated["spikes"]),
        "baseline_spikes_per_neuron": baseline_rate,
        "stimulated_spikes_per_neuron": stimulated_rate,
        "delta_spikes_per_neuron": delta,
        "stimulated_active_neurons": active,
        "positive_delta": delta > 0.0,
        "target_population_active": active > 0,
        "passed": delta > 0.0 and active > 0,
    }


def run_calibration(
    *,
    output: str | Path,
    seed: int = 109,
    neural_ms: float = 200.0,
    tactile_current: float = 6.0,
    crosswalk_path: str | Path = DEFAULT_CROSSWALK,
) -> dict[str, Any]:
    if neural_ms <= 0:
        raise ValueError("neural_ms must be > 0")
    if not math.isfinite(float(tactile_current)) or tactile_current <= 0:
        raise ValueError("tactile_current must be finite and > 0")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    baseline_checkpoint = output.parent / "tactile-calibration-baseline.npz"
    crosswalk_path = Path(crosswalk_path)
    crosswalk = _load_crosswalk(crosswalk_path)

    environment = CurriculumMazeEnvironment(seed=seed)
    environment.fly = {
        "x": int(environment.fly["x"]),
        "y": int(environment.fly["y"]),
        "dir": "RIGHT",
    }
    frame = environment.render_rgb()
    fly = dict(environment.fly)
    enemies = [dict(item) for item in environment.enemies]

    baseline_brain = MaleCNSBrain(learning=False, neural_ms=neural_ms)
    baseline_brain.brain.weights_frozen = True
    _, selected, annotation_report = _resolve_groups(baseline_brain, crosswalk)
    if len(selected) != EXPECTED_TOTAL:
        raise RuntimeError("Tactile selected population changed before calibration")
    baseline_brain.brain.checkpoint(baseline_checkpoint)
    baseline_checkpoint_sha256 = _sha256_file(baseline_checkpoint)

    try:
        results = {
            "contact_off": _condition(
                name="contact_off",
                stimulate_contact=False,
                current=tactile_current,
                baseline_checkpoint=baseline_checkpoint,
                frame=frame,
                fly=fly,
                enemies=enemies,
                neural_ms=neural_ms,
                crosswalk=crosswalk,
            ),
            "front_contact": _condition(
                name="front_contact",
                stimulate_contact=True,
                current=tactile_current,
                baseline_checkpoint=baseline_checkpoint,
                frame=frame,
                fly=fly,
                enemies=enemies,
                neural_ms=neural_ms,
                crosswalk=crosswalk,
            ),
        }

        type_gates = {
            neuron_type: _response_gate(results, neuron_type)
            for neuron_type in sorted(EXPECTED_TYPE_COUNTS)
        }
        selected_gate = _selected_population_gate(results)
        memory_shas = {
            condition["memory_sha256_before"]
            for condition in results.values()
        }
        matched_state = len(memory_shas) == 1
        all_frozen = all(condition["weights_frozen"] for condition in results.values())
        counts_match = (
            int(annotation_report["selected_total"]["neurons"]) == EXPECTED_TOTAL
            and all(
                int(annotation_report[name]["neurons"]) == EXPECTED_TYPE_COUNTS[name]
                for name in EXPECTED_TYPE_COUNTS
            )
        )
        passed = (
            matched_state
            and all_frozen
            and counts_match
            and selected_gate["passed"]
            and all(gate["passed"] for gate in type_gates.values())
        )

        body: dict[str, Any] = {
            "schema": CALIBRATION_SCHEMA,
            "passed": passed,
            "runtime_stimulation_enabled": False,
            "stonkfly_commit": STONKFLY_COMMIT,
            "tactile_model": TACTILE_MODEL,
            "crosswalk_schema": TACTILE_CROSSWALK_SCHEMA,
            "crosswalk_sha256": _sha256_file(crosswalk_path),
            "baseline_checkpoint_sha256": baseline_checkpoint_sha256,
            "seed": seed,
            "neural_ms": neural_ms,
            "tactile_current": tactile_current,
            "plasticity_frozen": all_frozen,
            "matched_baseline_memory": matched_state,
            "population_counts_match_audit": counts_match,
            "annotation_report": annotation_report,
            "conditions": results,
            "selected_population_gate": selected_gate,
            "type_gates": type_gates,
            "interpretation": (
                "PASS validates only frozen-weight engineered current routing into the "
                "six-type / 590-neuron evidence-backed MaleCNS tactile candidate population. "
                "It does not validate natural bristle mechanics, receptor gain, laterality, "
                "touch localization, motor benefit, or biological tactile behavior."
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
        description="Run matched frozen-weight MaleCNS tactile current calibration"
    )
    parser.add_argument(
        "--output",
        default="runs/tactile/tactile-calibration.json",
    )
    parser.add_argument("--seed", type=int, default=109)
    parser.add_argument("--neural-ms", type=float, default=200.0)
    parser.add_argument("--current", type=float, default=6.0)
    parser.add_argument("--crosswalk", default=str(DEFAULT_CROSSWALK))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_calibration(
        output=args.output,
        seed=args.seed,
        neural_ms=args.neural_ms,
        tactile_current=args.current,
        crosswalk_path=args.crosswalk,
    )
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "receipt_sha256": result["receipt_sha256"],
                "selected_population_gate": result["selected_population_gate"],
                "type_gates": result["type_gates"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
