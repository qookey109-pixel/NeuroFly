from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from neurofly import training as training_module
from neurofly.behavior_diagnostics import summarize_receipt
from neurofly.brain_runtime import MaleCNSBrain
from neurofly.smoke import _digest_json
from neurofly.tactile_runtime import TACTILE_CALIBRATED_CURRENT


SCHEMA = "neurofly-tactile-maze-ab-probe-v2"
STEPS = 600
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


def _source_digests(source_dir: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for suffix in (".npz", ".maze.json", ".decoder.json"):
        path = source_dir / f"brain{suffix}"
        if path.is_file():
            result[path.name] = _sha256_file(path)
    if "brain.npz" not in result:
        raise FileNotFoundError(source_dir / "brain.npz")
    return result


class TactileOffBrain(MaleCNSBrain):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["tactile_current"] = 0.0
        super().__init__(*args, **kwargs)


class TactileOnBrain(MaleCNSBrain):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["tactile_current"] = TACTILE_CALIBRATED_CURRENT
        super().__init__(*args, **kwargs)


def _run_arm(
    *,
    source_dir: Path,
    work_root: Path,
    name: str,
    brain_class: type[MaleCNSBrain],
) -> dict[str, Any]:
    arm_dir = work_root / name
    if arm_dir.exists():
        shutil.rmtree(arm_dir)
    shutil.copytree(source_dir, arm_dir)

    original = training_module.MaleCNSBrain
    training_module.MaleCNSBrain = brain_class
    try:
        receipt = training_module.run_self_training(
            steps=STEPS,
            checkpoint=arm_dir / "brain.npz",
            receipt=arm_dir / "self-training-receipt.json",
            seed=109,
            playback_steps=PLAYBACK_STEPS,
            curriculum=True,
        )
    finally:
        training_module.MaleCNSBrain = original

    summary = summarize_receipt(receipt)
    (arm_dir / "behavior-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    final_telemetry = ((receipt.get("final_state") or {}).get("brain") or {}).get(
        "telemetry"
    ) or {}
    tactile_report = final_telemetry.get("tactile_report") or {}
    tactile_levels = final_telemetry.get("contact_mechanosensation") or {}

    return {
        "arm": name,
        "steps": STEPS,
        "tactile_current": tactile_report.get("external_current"),
        "tactile_model": final_telemetry.get("tactile_model"),
        "tactile_encoding": tactile_levels.get("encoding"),
        "tactile_runtime_enabled": bool(
            (final_telemetry.get("contact_mechanosensation") or {}).get(
                "runtime_enabled", False
            )
        ),
        "tactile_population_count": (
            (tactile_report.get("population") or {}).get("neurons")
        ),
        "tactile_contact_count": summary.get("tactile_contact_count"),
        "tactile_contact_fraction": summary.get("tactile_contact_fraction"),
        "tactile_spikes_total": summary.get("tactile_spikes_total"),
        "tactile_spikes_per_contact_mean": summary.get(
            "tactile_spikes_per_contact_mean"
        ),
        "blocked_forward_fraction": summary.get(
            "playback_blocked_forward_fraction"
        ),
        "near_wall_forward_fraction": summary.get(
            "playback_near_wall_forward_fraction"
        ),
        "revisit_fraction_mean": summary.get("playback_revisit_fraction_mean"),
        "deaths_per_1000_decisions": summary.get("deaths_per_1000_decisions"),
        "food_events": summary.get("food_events"),
        "best_observed_episode_food_progress": summary.get(
            "best_observed_episode_food_progress"
        ),
        "clear_delta": summary.get("clear_delta"),
        "turn_left_to_right_ratio": summary.get("turn_left_to_right_ratio"),
        "receipt_sha256": receipt.get("receipt_sha256"),
    }


def _delta(on: Any, off: Any) -> float | None:
    if on is None or off is None:
        return None
    return float(on) - float(off)


def run_probe(source_dir: Path, work_root: Path) -> dict[str, Any]:
    source_before = _source_digests(source_dir)

    off = _run_arm(
        source_dir=source_dir,
        work_root=work_root,
        name="off",
        brain_class=TactileOffBrain,
    )
    on = _run_arm(
        source_dir=source_dir,
        work_root=work_root,
        name="on",
        brain_class=TactileOnBrain,
    )

    source_after = _source_digests(source_dir)
    if source_before != source_after:
        raise RuntimeError("Tactile A/B probe mutated the production source state")

    metrics = (
        "blocked_forward_fraction",
        "near_wall_forward_fraction",
        "revisit_fraction_mean",
        "deaths_per_1000_decisions",
        "food_events",
        "best_observed_episode_food_progress",
        "clear_delta",
    )
    deltas = {key: _delta(on.get(key), off.get(key)) for key in metrics}

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "source_state_sha256": source_before,
        "source_checkpoint_unchanged": True,
        "steps_per_arm": STEPS,
        "arms": {"off": off, "on": on},
        "on_minus_off": deltas,
        "mechanics": {
            "off_has_zero_tactile_spikes": int(off.get("tactile_spikes_total") or 0) == 0,
            "on_has_contact_events": int(on.get("tactile_contact_count") or 0) > 0,
            "on_has_tactile_spikes": int(on.get("tactile_spikes_total") or 0) > 0,
            "on_population_is_590": int(on.get("tactile_population_count") or 0) == 590,
            "on_current_is_calibrated": float(on.get("tactile_current") or 0.0)
            == TACTILE_CALIBRATED_CURRENT,
        },
        "claim_limits": {
            "production_merge_authorized": False,
            "decoder_change_authorized": False,
            "behavioral_benefit_established": False,
        },
    }
    body["receipt_sha256"] = _digest_json(body)
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare tactile OFF vs ON from the same production maze state"
    )
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    report = run_probe(Path(args.source_dir), Path(args.work_root))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        "TACTILE_MAZE_AB_PROBE_PASS",
        report["receipt_sha256"],
        json.dumps(report["mechanics"], sort_keys=True),
        json.dumps(report["on_minus_off"], sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
