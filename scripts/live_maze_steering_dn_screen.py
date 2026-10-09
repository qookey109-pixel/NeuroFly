from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from neurofly import training as training_module
from neurofly.behavior_diagnostics import summarize_receipt
from neurofly.brain_runtime import MaleCNSBrain, _bilateral_type_indices
from neurofly.smoke import _digest_json


SCHEMA = "neurofly-live-maze-steering-dn-screen-v1"
CANDIDATES = ("DNa03", "DNb06", "DNg13", "DNa11")
STEPS_PER_CANDIDATE = 400
PLAYBACK_STEPS = 240


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


class ProbeObserverBrain(MaleCNSBrain):
    observer_type = "DNa03"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        from stonkfly.neural.common import annotations

        table = annotations(self.brain.ids)
        left, right, report = _bilateral_type_indices(
            self.np,
            table,
            self.observer_type,
        )
        if not len(left) or not len(right):
            raise RuntimeError(
                f"{self.observer_type} is not bilaterally resolvable: {report}"
            )
        self._probe_observer_left = left
        self._probe_observer_right = right
        self._probe_observer_report = report

    def _decode(self, counts: Any) -> tuple[str, dict[str, Any]]:
        action, telemetry = super()._decode(counts)
        seconds = self.neural_ms / 1000.0
        left_hz = float(
            self.np.mean(counts[self._probe_observer_left]) / seconds
        )
        right_hz = float(
            self.np.mean(counts[self._probe_observer_right]) / seconds
        )
        updated = dict(telemetry)
        updated.update(
            {
                "steering_observer_type": self.observer_type,
                "steering_observer_left_hz": left_hz,
                "steering_observer_right_hz": right_hz,
                "steering_observer_difference_hz": right_hz - left_hz,
                "steering_observer_used_for_action": False,
            }
        )
        return action, updated


def _candidate_result(
    source_dir: Path,
    work_root: Path,
    candidate: str,
) -> dict[str, Any]:
    candidate_dir = work_root / candidate
    if candidate_dir.exists():
        shutil.rmtree(candidate_dir)
    shutil.copytree(source_dir, candidate_dir)

    ProbeObserverBrain.observer_type = candidate
    original_brain_class = training_module.MaleCNSBrain
    training_module.MaleCNSBrain = ProbeObserverBrain
    try:
        receipt_path = candidate_dir / "self-training-receipt.json"
        receipt = training_module.run_self_training(
            steps=STEPS_PER_CANDIDATE,
            checkpoint=candidate_dir / "brain.npz",
            receipt=receipt_path,
            seed=109,
            playback_steps=PLAYBACK_STEPS,
            curriculum=True,
        )
    finally:
        training_module.MaleCNSBrain = original_brain_class

    summary = summarize_receipt(receipt)
    (candidate_dir / "behavior-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )

    observations = receipt.get("observations") or []
    observer_differences = [
        float(row["steering_observer_difference_hz"])
        for row in observations
        if row.get("steering_observer_difference_hz") is not None
    ]
    absolute_observer_differences = [abs(value) for value in observer_differences]

    return {
        "observer_type": candidate,
        "observer_used_for_action": False,
        "action_decoder_type": "DNa02",
        "steps": STEPS_PER_CANDIDATE,
        "clear_delta": summary.get("clear_delta"),
        "deaths_per_1000_decisions": summary.get("deaths_per_1000_decisions"),
        "food_events": summary.get("food_events"),
        "best_observed_episode_food_progress": summary.get(
            "best_observed_episode_food_progress"
        ),
        "blocked_forward_fraction": summary.get(
            "playback_blocked_forward_fraction"
        ),
        "near_wall_forward_fraction": summary.get(
            "playback_near_wall_forward_fraction"
        ),
        "revisit_fraction_mean": summary.get("playback_revisit_fraction_mean"),
        "opening_to_observer_correlation": summary.get(
            "playback_near_wall_opening_to_dNa03_correlation"
        ),
        "eye_luminance_to_observer_correlation": summary.get(
            "playback_near_wall_eye_luminance_to_dNa03_correlation"
        ),
        "dNa02_to_observer_correlation": summary.get(
            "playback_near_wall_dNa02_to_dNa03_correlation"
        ),
        "observer_difference_hz_mean": _mean(observer_differences),
        "observer_abs_difference_hz_mean": _mean(
            absolute_observer_differences
        ),
        "receipt_sha256": receipt.get("receipt_sha256"),
    }


def run_screen(source_dir: Path, work_root: Path) -> dict[str, Any]:
    source_brain = source_dir / "brain.npz"
    if not source_brain.is_file():
        raise FileNotFoundError(source_brain)

    source_sha_before = _sha256_file(source_brain)
    results = {
        candidate: _candidate_result(source_dir, work_root, candidate)
        for candidate in CANDIDATES
    }
    source_sha_after = _sha256_file(source_brain)
    if source_sha_after != source_sha_before:
        raise RuntimeError("Live-maze screen mutated the production source brain")

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "source_brain_sha256": source_sha_before,
        "source_checkpoint_unchanged": True,
        "steps_per_candidate": STEPS_PER_CANDIDATE,
        "candidates": list(CANDIDATES),
        "results": results,
        "claim_limits": {
            "observer_only": True,
            "decoder_change_authorized": False,
            "behavioral_promotion_authorized": False,
        },
    }
    body["receipt_sha256"] = _digest_json(body)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare steering DN observers in identical isolated live-maze runs"
    )
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    report = run_screen(Path(args.source_dir), Path(args.work_root))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        "LIVE_MAZE_STEERING_DN_SCREEN_PASS",
        report["receipt_sha256"],
        json.dumps(report["results"], sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
