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


SCHEMA = "neurofly-visual-steering-projection-probe-v2"
WIDTH = 320
HEIGHT = 180
WARMUP_FRAMES = 4
PROBE_FRAMES = 12
OUTER_LEFT_END = 0.38
OUTER_RIGHT_START = 0.62
GRATING_CYCLES = 8.0
GRATING_AMPLITUDE = 90.0
BASE_LUMINANCE = 128.0

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


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return float(sum(values) / len(values)) if values else 0.0


def run_condition(source_checkpoint: Path, condition: str) -> dict[str, Any]:
    brain = MaleCNSBrain(
        checkpoint=source_checkpoint,
        learning=False,
    )
    brain.brain.weights_frozen = True

    from stonkfly.neural.common import annotations

    annotations_table = annotations(brain.brain.ids)
    dna01_left, dna01_right, dna01_report = _bilateral_type_indices(
        brain.np,
        annotations_table,
        "DNa01",
    )
    if not len(dna01_left) or not len(dna01_right):
        raise RuntimeError(f"DNa01 is not bilaterally resolvable: {dna01_report}")

    uniform = make_probe_frame("uniform_control", 0)
    for _ in range(WARMUP_FRAMES):
        brain.decide(uniform, reinforcement="none", context=None)

    rows: list[dict[str, Any]] = []
    actions: Counter[str] = Counter()
    for frame_index in range(PROBE_FRAMES):
        frame = make_probe_frame(condition, frame_index)
        decision = brain.decide(frame, reinforcement="none", context=None)
        telemetry = decision.telemetry
        actions[str(decision.action)] += 1
        seconds = brain.neural_ms / 1000.0
        counts = brain.brain.counts
        dna01_left_hz = float(brain.np.mean(counts[dna01_left]) / seconds)
        dna01_right_hz = float(brain.np.mean(counts[dna01_right]) / seconds)
        rows.append(
            {
                "frame": frame_index,
                "action": decision.action,
                "dNa02_left_hz": telemetry.get("left_hz"),
                "dNa02_right_hz": telemetry.get("right_hz"),
                "dNa01_left_hz": dna01_left_hz,
                "dNa01_right_hz": dna01_right_hz,
                "dNa01_raw_difference_hz": dna01_right_hz - dna01_left_hz,
                "raw_difference_hz": telemetry.get("raw_difference_hz"),
                "decoder_difference_hz": telemetry.get("decoder_difference_hz"),
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
            }
        )

    return {
        "condition": condition,
        "frames": PROBE_FRAMES,
        "action_counts": dict(sorted(actions.items())),
        "dNa02_left_hz_mean": _mean(rows, "dNa02_left_hz"),
        "dNa02_right_hz_mean": _mean(rows, "dNa02_right_hz"),
        "dNa02_raw_difference_hz_mean": _mean(rows, "raw_difference_hz"),
        "dNa02_decoder_difference_hz_mean": _mean(rows, "decoder_difference_hz"),
        "dNa01_left_hz_mean": _mean(rows, "dNa01_left_hz"),
        "dNa01_right_hz_mean": _mean(rows, "dNa01_right_hz"),
        "dNa01_raw_difference_hz_mean": _mean(rows, "dNa01_raw_difference_hz"),
        "dNa01_bilateral_report": dna01_report,
        "visual_change_mean": _mean(rows, "visual_change"),
        "retinal_eye_left_luminance_mean": _mean(
            rows, "retinal_eye_left_luminance_mean"
        ),
        "retinal_eye_right_luminance_mean": _mean(
            rows, "retinal_eye_right_luminance_mean"
        ),
        "retinal_eye_luminance_asymmetry_mean": _mean(
            rows, "retinal_eye_luminance_asymmetry"
        ),
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

    dNa02_left = results["motion_left_outer"]["dNa02_raw_difference_hz_mean"]
    dNa02_right = results["motion_right_outer"]["dNa02_raw_difference_hz_mean"]
    dNa02_full = results["motion_full"]["dNa02_raw_difference_hz_mean"]
    dNa02_static = results["static_full_grating"]["dNa02_raw_difference_hz_mean"]
    dNa01_left = results["motion_left_outer"]["dNa01_raw_difference_hz_mean"]
    dNa01_right = results["motion_right_outer"]["dNa01_raw_difference_hz_mean"]
    dNa01_full = results["motion_full"]["dNa01_raw_difference_hz_mean"]
    dNa01_static = results["static_full_grating"]["dNa01_raw_difference_hz_mean"]

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "source_checkpoint_sha256": source_sha_before,
        "source_checkpoint_unchanged": True,
        "learning_enabled": False,
        "production_checkpoint_mutated": False,
        "stonkfly_commit": STONKFLY_COMMIT,
        "conditions": results,
        "contrasts": {
            "dNa02_right_minus_left_motion_raw_difference_hz": dNa02_right - dNa02_left,
            "dNa02_full_motion_minus_static_raw_difference_hz": dNa02_full - dNa02_static,
            "dNa02_left_motion_minus_static_raw_difference_hz": dNa02_left - dNa02_static,
            "dNa02_right_motion_minus_static_raw_difference_hz": dNa02_right - dNa02_static,
            "dNa01_right_minus_left_motion_raw_difference_hz": dNa01_right - dNa01_left,
            "dNa01_full_motion_minus_static_raw_difference_hz": dNa01_full - dNa01_static,
            "dNa01_left_motion_minus_static_raw_difference_hz": dNa01_left - dNa01_static,
            "dNa01_right_motion_minus_static_raw_difference_hz": dNa01_right - dNa01_static,
        },
        "claim_limits": {
            "retinal_projection_calibrated": False,
            "visual_steering_validated": False,
            "dNa01_decoder_authorized": False,
            "multi_dn_decoder_authorized": False,
            "behavioral_promotion_authorized": False,
        },
    }
    body["receipt_sha256"] = _digest_json(body)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Probe retinal motion projection to DNa01 and DNa02 without learning"
    )
    parser.add_argument("--source-checkpoint", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    report = run_probe(Path(args.source_checkpoint))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        "VISUAL_STEERING_PROJECTION_PROBE_V2_PASS",
        report["receipt_sha256"],
        json.dumps(report["contrasts"], sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
