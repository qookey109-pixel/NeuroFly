from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from neurofly.brain_runtime import MaleCNSBrain
from neurofly.curriculum import CurriculumMazeEnvironment
from neurofly.smoke import _digest_json
from neurofly.upstream import STONKFLY_COMMIT


SCHEMA = "neurofly-tactile-subtype-downstream-screen-v1"
TACTILE_CURRENT = 8.0
NEURAL_MS = 50.0
EXPECTED_TYPES = {
    "SNta20": 156,
    "SNta26": 31,
    "SNta27": 47,
    "SNta28": 74,
    "SNta34": 54,
    "SNta37": 228,
}
EXPECTED_TOTAL = 590
ACCEPTED_SUBCLASSES = {"leg", "mechanosensory bristle"}
EXPECTED_CALIBRATION_RECEIPT = (
    "41592fd805bbfa19f73959af24479d12770e10866ed05e8fc85a86eac198f462"
)
CALIBRATION_PATH = Path("data/tactile_current_calibration_v1.json")
CROSSWALK_PATH = Path("data/tactile_leg_functional_crosswalk_v02.json")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_evidence() -> dict[str, Any]:
    calibration = json.loads(CALIBRATION_PATH.read_text())
    crosswalk = json.loads(CROSSWALK_PATH.read_text())

    if calibration.get("schema") != "neurofly-tactile-current-calibration-selection-v1":
        raise RuntimeError("Unexpected tactile calibration selection schema")
    if int(calibration.get("population_count", 0)) != EXPECTED_TOTAL:
        raise RuntimeError("Tactile calibration population count drifted")
    if calibration.get("type_counts") != EXPECTED_TYPES:
        raise RuntimeError("Tactile calibration type counts drifted")
    selected = calibration.get("selected") or {}
    if float(selected.get("current", 0.0)) != TACTILE_CURRENT:
        raise RuntimeError("Frozen tactile current drifted")
    if selected.get("receipt_sha256") != EXPECTED_CALIBRATION_RECEIPT:
        raise RuntimeError("Frozen tactile calibration receipt drifted")

    if crosswalk.get("schema") != "neurofly-tactile-leg-functional-crosswalk-v0.2":
        raise RuntimeError("Unexpected tactile crosswalk schema")
    if crosswalk.get("stimulation_enabled") is not False:
        raise RuntimeError("Crosswalk must remain non-authorizing")
    if crosswalk.get("runtime_transduction_enabled") is not False:
        raise RuntimeError("Crosswalk runtime flag must remain disabled")
    mapped = [str(item.get("male_cns_type") or "") for item in crosswalk.get("mappings") or []]
    if sorted(mapped) != sorted(EXPECTED_TYPES):
        raise RuntimeError("Tactile crosswalk mapped types drifted")

    return {
        "calibration_sha256": _sha256_file(CALIBRATION_PATH),
        "crosswalk_sha256": _sha256_file(CROSSWALK_PATH),
        "calibration_receipt_sha256": EXPECTED_CALIBRATION_RECEIPT,
        "current": TACTILE_CURRENT,
    }


def _resolve_groups(brain: MaleCNSBrain) -> tuple[dict[str, Any], Any, dict[str, Any]]:
    from stonkfly.neural.common import annotations

    a = annotations(brain.brain.ids)
    types = a.type.fillna("").astype(str)
    classes = a["class"].fillna("").astype(str).str.lower()
    subclasses = a["subclass"].fillna("").astype(str).str.lower()

    groups: dict[str, Any] = {}
    selected_mask = np.zeros(len(a), dtype=bool)
    report: dict[str, Any] = {}

    for neuron_type, expected_count in EXPECTED_TYPES.items():
        type_mask = types.eq(neuron_type)
        valid = (
            type_mask
            & classes.eq("mechanosensory_tactile")
            & subclasses.isin(ACCEPTED_SUBCLASSES)
        )
        invalid_same_type = type_mask & ~valid
        if int(invalid_same_type.sum()) != 0:
            raise RuntimeError(
                f"{neuron_type} includes rows outside the frozen tactile evidence boundary"
            )
        indices = np.flatnonzero(valid.to_numpy())
        if len(indices) != expected_count:
            raise RuntimeError(
                f"{neuron_type} count drifted: expected={expected_count} actual={len(indices)}"
            )
        groups[neuron_type] = indices
        selected_mask |= valid.to_numpy()
        report[neuron_type] = {
            "neurons": int(len(indices)),
            "body_ids_sha256": hashlib.sha256(
                brain.brain.ids[indices].tobytes()
            ).hexdigest(),
        }

    selected = np.flatnonzero(selected_mask)
    if len(selected) != EXPECTED_TOTAL:
        raise RuntimeError(
            f"Full tactile population drifted: expected={EXPECTED_TOTAL} actual={len(selected)}"
        )
    report["full_590"] = {
        "neurons": int(len(selected)),
        "body_ids_sha256": hashlib.sha256(
            brain.brain.ids[selected].tobytes()
        ).hexdigest(),
    }
    return groups, selected, report


def _matched_scene() -> tuple[Any, dict[str, Any]]:
    env = CurriculumMazeEnvironment(seed=109)
    frame = env.render_rgb()
    context = {
        "fly": dict(env.fly),
        "enemies": [dict(item) for item in env.enemies],
    }
    return frame, context


def _run_condition(
    source_checkpoint: Path,
    *,
    condition: str,
    neuron_type: str | None,
) -> dict[str, Any]:
    brain = MaleCNSBrain(
        checkpoint=source_checkpoint,
        learning=False,
        neural_ms=NEURAL_MS,
    )
    brain.brain.weights_frozen = True
    groups, selected, annotation_report = _resolve_groups(brain)

    if neuron_type is None:
        indices = np.asarray([], dtype=np.int64)
    elif neuron_type == "full_590":
        indices = selected
    else:
        indices = groups[neuron_type]

    frame, context = _matched_scene()
    rgb, _ = brain._visual_input(frame, context)
    b = brain.brain
    counts = np.zeros(b.n, dtype=np.int32)
    remaining = round(brain.neural_ms / b.dt)
    stimulation = (
        [(indices, TACTILE_CURRENT)]
        if len(indices)
        else None
    )
    memory_before = b.memory()

    while remaining:
        n = min(remaining, round(brain.neural_bin_ms / b.dt))
        current_counts, _ = b.rgb_step(
            rgb,
            n * b.dt,
            learning=False,
            stimulation=stimulation,
        )
        counts += current_counts
        remaining -= n

    b.counts[:] = counts
    action, decoder = brain._decode(counts)
    memory_after = b.memory()
    if memory_before["sha256"] != memory_after["sha256"]:
        raise RuntimeError(f"{condition} changed plastic weights")

    selected_spikes = int(counts[indices].sum()) if len(indices) else 0
    active_selected = int((counts[indices] > 0).sum()) if len(indices) else 0

    return {
        "condition": condition,
        "neuron_type": neuron_type,
        "stimulated_neurons": int(len(indices)),
        "selected_spikes": selected_spikes,
        "selected_active_neurons": active_selected,
        "action": action,
        "dNa02_left_hz": float(decoder["left_hz"]),
        "dNa02_right_hz": float(decoder["right_hz"]),
        "dNa02_raw_difference_hz": float(decoder["raw_difference_hz"]),
        "dNa02_decoder_difference_hz": float(decoder["decoder_difference_hz"]),
        "dNa03_left_hz": float(decoder["steering_observer_left_hz"]),
        "dNa03_right_hz": float(decoder["steering_observer_right_hz"]),
        "dNa03_difference_hz": float(decoder["steering_observer_difference_hz"]),
        "dNb05_drive_hz": float(decoder["walking_drive_hz"]),
        "total_spikes": int(counts.sum()),
        "weights_frozen": bool(b.weights_frozen),
        "annotation_report": annotation_report,
    }


def _delta(value: float, baseline: float) -> float:
    return float(value) - float(baseline)


def run_screen(source_checkpoint: Path) -> dict[str, Any]:
    if not source_checkpoint.is_file():
        raise FileNotFoundError(source_checkpoint)

    evidence = _load_evidence()
    source_before = _sha256_file(source_checkpoint)

    baseline = _run_condition(
        source_checkpoint,
        condition="contact_off",
        neuron_type=None,
    )
    conditions: dict[str, dict[str, Any]] = {"contact_off": baseline}

    for neuron_type in EXPECTED_TYPES:
        conditions[neuron_type] = _run_condition(
            source_checkpoint,
            condition=f"stimulate_{neuron_type}",
            neuron_type=neuron_type,
        )
    conditions["full_590"] = _run_condition(
        source_checkpoint,
        condition="stimulate_full_590",
        neuron_type="full_590",
    )

    source_after = _sha256_file(source_checkpoint)
    if source_before != source_after:
        raise RuntimeError("Tactile subtype screen mutated the production checkpoint")

    deltas: dict[str, dict[str, Any]] = {}
    for name, result in conditions.items():
        if name == "contact_off":
            continue
        deltas[name] = {
            "stimulated_neurons": result["stimulated_neurons"],
            "selected_spikes": result["selected_spikes"],
            "selected_active_neurons": result["selected_active_neurons"],
            "action": result["action"],
            "dNa02_raw_difference_delta_hz": _delta(
                result["dNa02_raw_difference_hz"],
                baseline["dNa02_raw_difference_hz"],
            ),
            "dNa02_abs_difference_delta_hz": (
                abs(result["dNa02_raw_difference_hz"])
                - abs(baseline["dNa02_raw_difference_hz"])
            ),
            "dNa03_difference_delta_hz": _delta(
                result["dNa03_difference_hz"],
                baseline["dNa03_difference_hz"],
            ),
            "dNa03_abs_difference_delta_hz": (
                abs(result["dNa03_difference_hz"])
                - abs(baseline["dNa03_difference_hz"])
            ),
            "dNb05_drive_delta_hz": _delta(
                result["dNb05_drive_hz"],
                baseline["dNb05_drive_hz"],
            ),
            "total_spikes_delta": int(
                result["total_spikes"] - baseline["total_spikes"]
            ),
        }

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "source_checkpoint_sha256": source_before,
        "source_checkpoint_unchanged": True,
        "learning_enabled": False,
        "neural_ms": NEURAL_MS,
        "tactile_current": TACTILE_CURRENT,
        "stonkfly_commit": STONKFLY_COMMIT,
        "evidence": evidence,
        "conditions": conditions,
        "downstream_deltas": deltas,
        "claim_limits": {
            "production_runtime_authorized": False,
            "tactile_subtype_selected": False,
            "decoder_change_authorized": False,
            "behavioral_benefit_established": False,
        },
    }
    body["receipt_sha256"] = _digest_json(body)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Screen exact tactile subtypes for downstream steering/drive effects"
    )
    parser.add_argument("--source-checkpoint", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    report = run_screen(Path(args.source_checkpoint))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        "TACTILE_SUBTYPE_DOWNSTREAM_SCREEN_PASS",
        report["receipt_sha256"],
        json.dumps(report["downstream_deltas"], sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
