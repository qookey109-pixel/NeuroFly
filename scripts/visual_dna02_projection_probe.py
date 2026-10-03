from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from neurofly.brain_runtime import MaleCNSBrain, _bilateral_type_indices
from neurofly.smoke import _digest_json
from neurofly.upstream import STONKFLY_COMMIT


SCHEMA = "neurofly-visual-steering-dn-screen-v3"
WIDTH = 320
HEIGHT = 180
WARMUP_FRAMES = 4
PROBE_FRAMES = 12
OUTER_LEFT_END = 0.38
OUTER_RIGHT_START = 0.62
GRATING_CYCLES = 8.0
GRATING_AMPLITUDE = 90.0
BASE_LUMINANCE = 128.0

# Steering-related descending neuron types reported across recent walking studies.
# The screen does not assume any of them are valid decoder channels in MaleCNS;
# unresolved or silent populations are evidence, not failures.
STEERING_TYPES = (
    "DNa01",
    "DNa02",
    "DNa03",
    "DNa11",
    "DNae003",
    "DNae014",
    "DNb02",
    "DNb05",
    "DNb06",
    "DNg13",
)

CONDITIONS = (
    "uniform_control",
    "static_full_grating",
    "motion_left_outer",
    "motion_right_outer",
    "motion_full",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _grating(width: int, phase_cycles: float) -> np.ndarray:
    x = np.arange(width, dtype=np.float32)
    phase = 2.0 * math.pi * (GRATING_CYCLES * x / float(width) + phase_cycles)
    values = BASE_LUMINANCE + GRATING_AMPLITUDE * np.sin(phase)
    return np.clip(values, 0.0, 255.0).astype(np.uint8)


def make_probe_frame(
    condition: str,
    frame_index: int,
    *,
    width: int = WIDTH,
    height: int = HEIGHT,
) -> np.ndarray:
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown probe condition: {condition}")
    frame = np.full((height, width, 3), int(BASE_LUMINANCE), dtype=np.uint8)
    if condition == "uniform_control":
        return frame

    moving = condition.startswith("motion_")
    phase_cycles = (frame_index * 0.125) if moving else 0.0
    stripe = _grating(width, phase_cycles)
    rgb_stripe = np.repeat(stripe[:, None], 3, axis=1)

    if condition in {"static_full_grating", "motion_full"}:
        frame[:, :, :] = rgb_stripe[None, :, :]
    elif condition == "motion_left_outer":
        end = max(1, int(width * OUTER_LEFT_END))
        frame[:, :end, :] = rgb_stripe[None, :end, :]
    elif condition == "motion_right_outer":
        start = min(width - 1, int(width * OUTER_RIGHT_START))
        frame[:, start:, :] = rgb_stripe[None, start:, :]
    return frame


def _mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def _resolve_steering_populations(
    brain: MaleCNSBrain,
) -> tuple[dict[str, tuple[Any, Any]], dict[str, dict[str, Any]]]:
    from stonkfly.neural.common import annotations

    table = annotations(brain.brain.ids)
    resolved: dict[str, tuple[Any, Any]] = {}
    reports: dict[str, dict[str, Any]] = {}
    for cell_type in STEERING_TYPES:
        left, right, report = _bilateral_type_indices(brain.np, table, cell_type)
        reports[cell_type] = {
            **report,
            "bilaterally_resolved": bool(len(left) and len(right)),
        }
        if len(left) and len(right):
            resolved[cell_type] = (left, right)
    return resolved, reports


def run_condition(source_checkpoint: Path, condition: str) -> dict[str, Any]:
    brain = MaleCNSBrain(
        checkpoint=source_checkpoint,
        learning=False,
    )
    brain.brain.weights_frozen = True
    populations, population_reports = _resolve_steering_populations(brain)

    uniform = make_probe_frame("uniform_control", 0)
    for _ in range(WARMUP_FRAMES):
        brain.decide(uniform, reinforcement="none", context=None)

    rows: list[dict[str, Any]] = []
    actions: Counter[str] = Counter()
    population_samples: dict[str, dict[str, list[float]]] = {
        cell_type: {"left": [], "right": [], "difference": []}
        for cell_type in populations
    }

    for frame_index in range(PROBE_FRAMES):
        frame = make_probe_frame(condition, frame_index)
        decision = brain.decide(frame, reinforcement="none", context=None)
        telemetry = decision.telemetry
        actions[str(decision.action)] += 1
        seconds = brain.neural_ms / 1000.0
        counts = brain.brain.counts

        population_row: dict[str, dict[str, float]] = {}
        for cell_type, (left_indices, right_indices) in populations.items():
            left_hz = float(brain.np.mean(counts[left_indices]) / seconds)
            right_hz = float(brain.np.mean(counts[right_indices]) / seconds)
            difference = right_hz - left_hz
            population_row[cell_type] = {
                "left_hz": left_hz,
                "right_hz": right_hz,
                "raw_difference_hz": difference,
            }
            population_samples[cell_type]["left"].append(left_hz)
            population_samples[cell_type]["right"].append(right_hz)
            population_samples[cell_type]["difference"].append(difference)

        rows.append(
            {
                "frame": frame_index,
                "action": decision.action,
                "dNa02_decoder_difference_hz": telemetry.get("decoder_difference_hz"),
                "visual_change": telemetry.get("visual_change"),
                "retinal_eye_left_luminance_mean": telemetry.get(
                    "retinal_eye_left_luminance_mean"
                ),
                "retinal_eye_right_luminance_mean": telemetry.get(
                    "retinal_eye_right_luminance_mean"
                ),
                "retinal_eye_luminance_asymmetry": telemetry.get(
                    "retinal_eye_luminance_asymmetry"
                ),
                "total_spikes": telemetry.get("total_spikes"),
                "steering_populations": population_row,
            }
        )

    population_summary = {
        cell_type: {
            "left_hz_mean": _mean(values["left"]),
            "right_hz_mean": _mean(values["right"]),
            "raw_difference_hz_mean": _mean(values["difference"]),
            "report": population_reports[cell_type],
        }
        for cell_type, values in population_samples.items()
    }

    return {
        "condition": condition,
        "frames": PROBE_FRAMES,
        "action_counts": dict(sorted(actions.items())),
        "dNa02_decoder_difference_hz_mean": _mean(
            [
                float(row["dNa02_decoder_difference_hz"])
                for row in rows
                if row.get("dNa02_decoder_difference_hz") is not None
            ]
        ),
        "visual_change_mean": _mean(
            [float(row["visual_change"]) for row in rows if row.get("visual_change") is not None]
        ),
        "retinal_eye_luminance_asymmetry_mean": _mean(
            [
                float(row["retinal_eye_luminance_asymmetry"])
                for row in rows
                if row.get("retinal_eye_luminance_asymmetry") is not None
            ]
        ),
        "steering_populations": population_summary,
        "population_reports": population_reports,
        "rows": rows,
    }


def run_probe(source_checkpoint: Path) -> dict[str, Any]:
    if not source_checkpoint.is_file():
        raise FileNotFoundError(source_checkpoint)

    source_sha_before = _sha256_file(source_checkpoint)
    results = {
        condition: run_condition(source_checkpoint, condition)
        for condition in CONDITIONS
    }
    source_sha_after = _sha256_file(source_checkpoint)
    if source_sha_after != source_sha_before:
        raise RuntimeError("Visual probe mutated the production source checkpoint")

    resolved_types = sorted(
        set.intersection(
            *[
                set(result["steering_populations"])
                for result in results.values()
            ]
        )
    )
    contrasts: dict[str, dict[str, float]] = {}
    for cell_type in resolved_types:
        left_motion = results["motion_left_outer"]["steering_populations"][cell_type][
            "raw_difference_hz_mean"
        ]
        right_motion = results["motion_right_outer"]["steering_populations"][cell_type][
            "raw_difference_hz_mean"
        ]
        full_motion = results["motion_full"]["steering_populations"][cell_type][
            "raw_difference_hz_mean"
        ]
        static = results["static_full_grating"]["steering_populations"][cell_type][
            "raw_difference_hz_mean"
        ]
        contrasts[cell_type] = {
            "right_minus_left_motion_raw_difference_hz": right_motion - left_motion,
            "left_motion_minus_static_raw_difference_hz": left_motion - static,
            "right_motion_minus_static_raw_difference_hz": right_motion - static,
            "full_motion_minus_static_raw_difference_hz": full_motion - static,
        }

    first_reports = results["uniform_control"]["population_reports"]
    unresolved_types = sorted(
        cell_type
        for cell_type, report in first_reports.items()
        if not report["bilaterally_resolved"]
    )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "source_checkpoint_sha256": source_sha_before,
        "source_checkpoint_unchanged": True,
        "learning_enabled": False,
        "production_checkpoint_mutated": False,
        "stonkfly_commit": STONKFLY_COMMIT,
        "screened_types": list(STEERING_TYPES),
        "resolved_types": resolved_types,
        "unresolved_types": unresolved_types,
        "conditions": results,
        "population_contrasts": contrasts,
        "claim_limits": {
            "retinal_projection_calibrated": False,
            "visual_steering_validated": False,
            "steering_dn_decoder_authorized": False,
            "multi_dn_decoder_authorized": False,
            "behavioral_promotion_authorized": False,
        },
    }
    body["receipt_sha256"] = _digest_json(body)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Screen known steering DNs under isolated retinal motion without learning"
    )
    parser.add_argument("--source-checkpoint", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    report = run_probe(Path(args.source_checkpoint))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        "VISUAL_STEERING_DN_SCREEN_V3_PASS",
        report["receipt_sha256"],
        "resolved=", report["resolved_types"],
        "unresolved=", report["unresolved_types"],
        json.dumps(report["population_contrasts"], sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
