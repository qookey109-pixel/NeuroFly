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


SCHEMA = "neurofly-tactile-subtype-latency-screen-v1"
TACTILE_CURRENT = 8.0
WINDOW_MS = 50.0
WINDOWS = 5
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


def _validate_frozen_evidence() -> dict[str, Any]:
    calibration = json.loads(CALIBRATION_PATH.read_text())
    crosswalk = json.loads(CROSSWALK_PATH.read_text())
    if calibration.get("schema") != "neurofly-tactile-current-calibration-selection-v1":
        raise RuntimeError("Unexpected tactile calibration schema")
    if calibration.get("type_counts") != EXPECTED_TYPES:
        raise RuntimeError("Tactile type counts drifted")
    selected = calibration.get("selected") or {}
    if float(selected.get("current", 0.0)) != TACTILE_CURRENT:
        raise RuntimeError("Frozen tactile current drifted")
    if selected.get("receipt_sha256") != EXPECTED_CALIBRATION_RECEIPT:
        raise RuntimeError("Frozen tactile receipt drifted")
    if crosswalk.get("schema") != "neurofly-tactile-leg-functional-crosswalk-v0.2":
        raise RuntimeError("Unexpected tactile crosswalk schema")
    if crosswalk.get("stimulation_enabled") is not False:
        raise RuntimeError("Crosswalk must remain non-authorizing")
    if crosswalk.get("runtime_transduction_enabled") is not False:
        raise RuntimeError("Crosswalk runtime flag must remain disabled")
    return {
        "calibration_sha256": _sha256_file(CALIBRATION_PATH),
        "crosswalk_sha256": _sha256_file(CROSSWALK_PATH),
        "calibration_receipt_sha256": EXPECTED_CALIBRATION_RECEIPT,
    }


def _resolve_groups(brain: MaleCNSBrain) -> tuple[dict[str, Any], Any]:
    from stonkfly.neural.common import annotations

    a = annotations(brain.brain.ids)
    types = a.type.fillna("").astype(str)
    classes = a["class"].fillna("").astype(str).str.lower()
    subclasses = a["subclass"].fillna("").astype(str).str.lower()
    selected_mask = np.zeros(len(a), dtype=bool)
    groups: dict[str, Any] = {}
    for neuron_type, expected_count in EXPECTED_TYPES.items():
        type_mask = types.eq(neuron_type)
        valid = (
            type_mask
            & classes.eq("mechanosensory_tactile")
            & subclasses.isin(ACCEPTED_SUBCLASSES)
        )
        invalid = type_mask & ~valid
        if int(invalid.sum()) != 0:
            raise RuntimeError(f"{neuron_type} left frozen tactile boundary")
        indices = np.flatnonzero(valid.to_numpy())
        if len(indices) != expected_count:
            raise RuntimeError(
                f"{neuron_type} count drifted expected={expected_count} actual={len(indices)}"
            )
        groups[neuron_type] = indices
        selected_mask |= valid.to_numpy()
    selected = np.flatnonzero(selected_mask)
    if len(selected) != EXPECTED_TOTAL:
        raise RuntimeError("Full tactile population count drifted")
    return groups, selected


def _scene() -> tuple[Any, dict[str, Any]]:
    env = CurriculumMazeEnvironment(seed=109)
    return env.render_rgb(), {
        "fly": dict(env.fly),
        "enemies": [dict(item) for item in env.enemies],
    }


def _window_metrics(
    brain: MaleCNSBrain,
    counts: Any,
    target_indices: Any,
    *,
    window_index: int,
) -> dict[str, Any]:
    decoder_action, decoder = brain._decode(counts)
    return {
        "window_index": window_index,
        "start_ms": window_index * WINDOW_MS,
        "end_ms": (window_index + 1) * WINDOW_MS,
        "action": decoder_action,
        "target_spikes": int(counts[target_indices].sum()) if len(target_indices) else 0,
        "target_active_neurons": (
            int((counts[target_indices] > 0).sum()) if len(target_indices) else 0
        ),
        "dNa02_left_hz": float(decoder["left_hz"]),
        "dNa02_right_hz": float(decoder["right_hz"]),
        "dNa02_raw_difference_hz": float(decoder["raw_difference_hz"]),
        "dNa02_decoder_difference_hz": float(decoder["decoder_difference_hz"]),
        "dNa03_left_hz": float(decoder["steering_observer_left_hz"]),
        "dNa03_right_hz": float(decoder["steering_observer_right_hz"]),
        "dNa03_difference_hz": float(decoder["steering_observer_difference_hz"]),
        "dNb05_drive_hz": float(decoder["walking_drive_hz"]),
        "total_spikes": int(counts.sum()),
    }


def _run_condition(
    source_checkpoint: Path,
    *,
    condition: str,
    neuron_type: str | None,
) -> dict[str, Any]:
    brain = MaleCNSBrain(
        checkpoint=source_checkpoint,
        learning=False,
        neural_ms=WINDOW_MS,
    )
    brain.brain.weights_frozen = True
    groups, full_population = _resolve_groups(brain)
    if neuron_type is None:
        target = np.asarray([], dtype=np.int64)
    elif neuron_type == "full_590":
        target = full_population
    else:
        target = groups[neuron_type]

    frame, context = _scene()
    rgb, _ = brain._visual_input(frame, context)
    b = brain.brain
    memory_before = b.memory()
    windows: list[dict[str, Any]] = []

    for window_index in range(WINDOWS):
        counts = np.zeros(b.n, dtype=np.int32)
        remaining = round(WINDOW_MS / b.dt)
        # One 50-ms tactile event only in window 0. Windows 1..4 test propagation
        # after external tactile current has stopped.
        stimulation = (
            [(target, TACTILE_CURRENT)]
            if window_index == 0 and len(target)
            else None
        )
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
        windows.append(
            _window_metrics(
                brain,
                counts,
                target,
                window_index=window_index,
            )
        )

    memory_after = b.memory()
    if memory_before["sha256"] != memory_after["sha256"]:
        raise RuntimeError(f"{condition} changed plastic weights")
    return {
        "condition": condition,
        "neuron_type": neuron_type,
        "stimulated_neurons": int(len(target)),
        "windows": windows,
    }


def _delta(stim: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "dNa02_raw_difference_hz",
        "dNa02_decoder_difference_hz",
        "dNa03_difference_hz",
        "dNb05_drive_hz",
        "total_spikes",
    )
    result: dict[str, Any] = {
        "window_index": stim["window_index"],
        "start_ms": stim["start_ms"],
        "end_ms": stim["end_ms"],
        "action": stim["action"],
        "target_spikes": stim["target_spikes"],
        "target_active_neurons": stim["target_active_neurons"],
    }
    for key in keys:
        result[f"{key}_delta"] = float(stim[key]) - float(base[key])
    return result


def run_screen(source_checkpoint: Path) -> dict[str, Any]:
    if not source_checkpoint.is_file():
        raise FileNotFoundError(source_checkpoint)
    evidence = _validate_frozen_evidence()
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
            condition=f"pulse_{neuron_type}",
            neuron_type=neuron_type,
        )
    conditions["full_590"] = _run_condition(
        source_checkpoint,
        condition="pulse_full_590",
        neuron_type="full_590",
    )

    source_after = _sha256_file(source_checkpoint)
    if source_before != source_after:
        raise RuntimeError("Latency screen mutated production checkpoint")

    deltas = {
        name: [
            _delta(stim_window, base_window)
            for stim_window, base_window in zip(
                condition["windows"],
                baseline["windows"],
            )
        ]
        for name, condition in conditions.items()
        if name != "contact_off"
    }

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "source_checkpoint_sha256": source_before,
        "source_checkpoint_unchanged": True,
        "learning_enabled": False,
        "window_ms": WINDOW_MS,
        "windows": WINDOWS,
        "tactile_current": TACTILE_CURRENT,
        "pulse_policy": "one-50ms-contact-pulse-then-four-50ms-no-current-windows",
        "stonkfly_commit": STONKFLY_COMMIT,
        "evidence": evidence,
        "conditions": conditions,
        "window_deltas": deltas,
        "claim_limits": {
            "production_runtime_authorized": False,
            "tactile_subtype_selected": False,
            "temporal_kernel_selected": False,
            "decoder_change_authorized": False,
            "behavioral_benefit_established": False,
        },
    }
    body["receipt_sha256"] = _digest_json(body)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Measure delayed locomotor propagation after one tactile subtype pulse"
    )
    parser.add_argument("--source-checkpoint", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = run_screen(Path(args.source_checkpoint))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        "TACTILE_SUBTYPE_LATENCY_SCREEN_PASS",
        report["receipt_sha256"],
        json.dumps(report["window_deltas"], sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
