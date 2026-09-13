from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .brain_runtime import MaleCNSBrain
from .curriculum import CurriculumMazeEnvironment
from .gustation import GUSTATION_CROSSWALK_SCHEMA, GUSTATION_MODEL
from .upstream import STONKFLY_COMMIT


CALIBRATION_SCHEMA = "neurofly-gustation-calibration-v1"
EXPECTED_CLASS_COUNTS = {"bitter": 6, "sugar_water": 77}
DEFAULT_CROSSWALK = (
    Path(__file__).resolve().parents[2] / "data" / "gustation_functional_crosswalk_v01.json"
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
    if payload.get("schema") != GUSTATION_CROSSWALK_SCHEMA:
        raise RuntimeError("Unexpected gustation functional crosswalk schema")
    if payload.get("stimulation_enabled") is not False:
        raise RuntimeError("Crosswalk must remain non-authorizing during calibration")
    mappings = payload.get("mappings")
    if not isinstance(mappings, list) or not mappings:
        raise RuntimeError("Gustation functional crosswalk has no mappings")
    return payload


def _resolve_groups(brain: MaleCNSBrain, crosswalk: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Resolve only exact curated gustatory types from the v0.1 crosswalk."""

    from stonkfly.neural.common import annotations

    np = brain.np
    a = annotations(brain.brain.ids)
    types = a.type.fillna("").astype(str)
    classes = a["class"].fillna("").astype(str).str.lower()

    mapped_types: dict[str, list[str]] = {"bitter": [], "sugar_water": []}
    for mapping in crosswalk["mappings"]:
        functional_class = str(mapping.get("functional_class") or "")
        neuron_type = str(mapping.get("male_cns_type") or "")
        if functional_class not in mapped_types or not neuron_type:
            raise RuntimeError(f"Unsupported crosswalk mapping: {mapping}")
        if mapping.get("stimulation_authorized") is not False:
            raise RuntimeError("Crosswalk mapping unexpectedly authorizes stimulation")
        mapped_types[functional_class].append(neuron_type)

    groups: dict[str, Any] = {}
    report: dict[str, Any] = {}
    all_mapped = np.zeros(len(a), dtype=bool)
    for functional_class, class_types in mapped_types.items():
        type_mask = types.isin(class_types)
        non_gustatory = type_mask & ~classes.eq("gustatory")
        if int(non_gustatory.sum()) != 0:
            raise RuntimeError(
                f"Mapped {functional_class} types include non-gustatory rows: "
                f"{int(non_gustatory.sum())}"
            )
        mask = type_mask & classes.eq("gustatory")
        indices = np.flatnonzero(mask.to_numpy())
        found_types = sorted(set(types[mask].tolist()))
        missing_types = sorted(set(class_types) - set(found_types))
        if missing_types:
            raise RuntimeError(
                f"Mapped {functional_class} types missing from prepared MaleCNS: {missing_types}"
            )
        if len(indices) != EXPECTED_CLASS_COUNTS[functional_class]:
            raise RuntimeError(
                f"Prepared MaleCNS {functional_class} count changed: "
                f"expected={EXPECTED_CLASS_COUNTS[functional_class]} actual={len(indices)}"
            )
        groups[functional_class] = indices
        all_mapped |= mask.to_numpy()
        report[functional_class] = {
            "types": sorted(class_types),
            "neurons": int(len(indices)),
            "body_ids_sha256": hashlib.sha256(
                brain.brain.ids[indices].tobytes()
            ).hexdigest(),
        }

    if bool(all_mapped[groups["bitter"]].all()) is not True:
        raise RuntimeError("Bitter mapping internal consistency failure")
    if bool(all_mapped[groups["sugar_water"]].all()) is not True:
        raise RuntimeError("Sugar/water mapping internal consistency failure")
    return groups, report


def _group_metrics(brain: MaleCNSBrain, indices: Any) -> dict[str, float | int]:
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
    stimulated_class: str | None,
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
    groups, annotation_report = _resolve_groups(brain, crosswalk)

    pulses: list[tuple[Any, float]] = []
    if stimulated_class is not None:
        pulses.append((groups[stimulated_class], current))

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
        raise RuntimeError(f"Gustation calibration condition {name} changed plastic weights")

    return {
        "condition": name,
        "stimulated_class": stimulated_class,
        "external_current": 0.0 if stimulated_class is None else current,
        "groups": {
            class_name: _group_metrics(brain, indices)
            for class_name, indices in groups.items()
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
    functional_class: str,
) -> dict[str, Any]:
    baseline = results["contact_off"]["groups"][functional_class]
    stimulated = results[functional_class]["groups"][functional_class]
    baseline_rate = float(baseline["spikes_per_neuron"])
    stimulated_rate = float(stimulated["spikes_per_neuron"])
    delta = stimulated_rate - baseline_rate
    active = int(stimulated["active_neurons"])
    return {
        "functional_class": functional_class,
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
    gustation_current: float = 6.0,
    crosswalk_path: str | Path = DEFAULT_CROSSWALK,
) -> dict[str, Any]:
    if neural_ms <= 0:
        raise ValueError("neural_ms must be > 0")
    if not math.isfinite(float(gustation_current)) or gustation_current <= 0:
        raise ValueError("gustation_current must be finite and > 0")

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    baseline_checkpoint = output.parent / "gustation-calibration-baseline.npz"
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
    groups, annotation_report = _resolve_groups(baseline_brain, crosswalk)
    baseline_brain.brain.checkpoint(baseline_checkpoint)
    baseline_checkpoint_sha256 = _sha256_file(baseline_checkpoint)

    try:
        results = {
            "contact_off": _condition(
                name="contact_off",
                stimulated_class=None,
                current=gustation_current,
                baseline_checkpoint=baseline_checkpoint,
                frame=frame,
                fly=fly,
                enemies=enemies,
                neural_ms=neural_ms,
                crosswalk=crosswalk,
            ),
            "bitter": _condition(
                name="bitter",
                stimulated_class="bitter",
                current=gustation_current,
                baseline_checkpoint=baseline_checkpoint,
                frame=frame,
                fly=fly,
                enemies=enemies,
                neural_ms=neural_ms,
                crosswalk=crosswalk,
            ),
            "sugar_water": _condition(
                name="sugar_water",
                stimulated_class="sugar_water",
                current=gustation_current,
                baseline_checkpoint=baseline_checkpoint,
                frame=frame,
                fly=fly,
                enemies=enemies,
                neural_ms=neural_ms,
                crosswalk=crosswalk,
            ),
        }

        gates = {
            class_name: _response_gate(results, class_name)
            for class_name in ("bitter", "sugar_water")
        }
        memory_shas = {
            condition["memory_sha256_before"]
            for condition in results.values()
        }
        matched_state = len(memory_shas) == 1
        all_frozen = all(condition["weights_frozen"] for condition in results.values())
        counts_match = all(
            int(annotation_report[name]["neurons"]) == EXPECTED_CLASS_COUNTS[name]
            for name in EXPECTED_CLASS_COUNTS
        )
        passed = (
            matched_state
            and all_frozen
            and counts_match
            and all(gate["passed"] for gate in gates.values())
        )

        body: dict[str, Any] = {
            "schema": CALIBRATION_SCHEMA,
            "passed": passed,
            "runtime_stimulation_enabled": False,
            "stonkfly_commit": STONKFLY_COMMIT,
            "gustation_model": GUSTATION_MODEL,
            "crosswalk_schema": GUSTATION_CROSSWALK_SCHEMA,
            "crosswalk_sha256": _sha256_file(crosswalk_path),
            "baseline_checkpoint_sha256": baseline_checkpoint_sha256,
            "seed": seed,
            "neural_ms": neural_ms,
            "gustation_current": gustation_current,
            "plasticity_frozen": all_frozen,
            "matched_baseline_memory": matched_state,
            "population_counts_match_audit": counts_match,
            "annotation_report": annotation_report,
            "conditions": results,
            "class_gates": gates,
            "interpretation": (
                "PASS validates only frozen-weight engineered current routing into the "
                "evidence-backed MaleCNS gustatory groups. It does not validate natural "
                "taste transduction, feeding preference, reward value, or behavioral benefit."
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
        description="Run matched frozen-weight MaleCNS gustation current calibration"
    )
    parser.add_argument(
        "--output",
        default="runs/gustation/gustation-calibration.json",
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
        gustation_current=args.current,
        crosswalk_path=args.crosswalk,
    )
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "receipt_sha256": result["receipt_sha256"],
                "class_gates": result["class_gates"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
