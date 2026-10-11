from __future__ import annotations

"""Run isolated Stage 2 predator-odor gain A/B from one frozen checkpoint.

The production checkpoint and runtime code are never modified. All three arms
use the unchanged neural decoder and apply only the brain's decoded actions.
Exploratory differences are NOT proof of improved navigation.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any
from unittest.mock import patch

from neurofly import brain_runtime, training
from neurofly.behavior_diagnostics import summarize_receipt
from neurofly.odor_stage2_evidence import compare_candidate
from neurofly.smoke import _digest_json

SCHEMA = "neurofly-danger-orn-stage2-ab-v1"
GAINS = (1.6, 2.4, 3.2)
STEPS = 600
PLAYBACK_STEPS = 240
SOURCE_FILES = ("brain.npz", "brain.maze.json", "brain.decoder.json")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _source_state(source_dir: Path) -> tuple[dict[str, str], dict[str, Any]]:
    paths = [source_dir / name for name in SOURCE_FILES]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Missing source checkpoint component: {path}")
    hashes = {path.name: _sha256(path) for path in paths}
    world = json.loads((source_dir / "brain.maze.json").read_text())
    if int(world.get("curriculum_stage", 0)) != 2:
        raise RuntimeError("Stage 2 A/B requires a Stage 2 production checkpoint")
    if world.get("direct_action_override_enabled", False):
        raise RuntimeError("Source checkpoint must not enable direct actions")
    return hashes, world


def _run_arm(
    *,
    source_dir: Path,
    work_root: Path,
    gain: float,
    source_sha256: str,
    initial_stage2_clears: int,
    initial_world_ticks: int,
    steps: int,
) -> dict[str, Any]:
    name = f"gain-{gain:.1f}"
    arm_dir = work_root / name
    if arm_dir.exists():
        shutil.rmtree(arm_dir)
    shutil.copytree(source_dir, arm_dir)

    original_gain = brain_runtime.DANGER_ODOR_CURRENT_GAIN
    try:
        brain_runtime.DANGER_ODOR_CURRENT_GAIN = gain
        # Prevent any accidental live relay publication from a diagnostic.
        with patch.object(
            training.GitHubOIDCLivePublisher, "from_environment", return_value=None
        ):
            receipt = training.run_self_training(
                steps=steps,
                checkpoint=arm_dir / "brain.npz",
                receipt=arm_dir / "self-training-receipt.json",
                seed=109,
                playback_steps=min(PLAYBACK_STEPS, steps),
                curriculum=True,
            )
    finally:
        brain_runtime.DANGER_ODOR_CURRENT_GAIN = original_gain

    if int(receipt["steps"]) != steps:
        raise RuntimeError("Decision count drifted during Stage 2 A/B")
    if int(receipt.get("live_published", -1)) != 0:
        raise RuntimeError("Isolated A/B unexpectedly published live telemetry")
    if any(row.get("action_overridden") for row in receipt["observations"]):
        raise RuntimeError("The neural action-autonomy boundary was violated")

    telemetry = (receipt["final_state"]["brain"].get("telemetry") or {})
    measured_gain = (telemetry.get("olfaction_report") or {}).get("danger_current_gain")
    if measured_gain is None or abs(float(measured_gain) - gain) > 1e-9:
        raise RuntimeError("Arm odor gain is not reflected in neural telemetry")

    summary = summarize_receipt(receipt)
    (arm_dir / "behavior-summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n"
    )
    final_maze = json.loads((arm_dir / "brain.maze.json").read_text())
    final_stage2_clears = int((final_maze.get("stage_clear_counts") or {}).get("2", 0))
    world_tick_delta = int(final_maze.get("total_world_ticks", 0)) - initial_world_ticks
    if world_tick_delta < 0:
        raise RuntimeError("World tick counter went backwards in an isolated arm")
    applied_decisions = sum(
        row.get("decision_applied") is True for row in receipt["observations"]
    )
    discarded_decisions = steps - applied_decisions

    return {
        "name": name,
        "gain": gain,
        "source_sha256": source_sha256,
        "initial_stage": 2,
        "final_stage": int(final_maze.get("curriculum_stage", 0)),
        "steps": steps,
        "stage2_clear_delta": final_stage2_clears - initial_stage2_clears,
        "world_tick_delta": world_tick_delta,
        "applied_decision_count": applied_decisions,
        "discarded_decision_count": discarded_decisions,
        "blocked_forward_fraction": summary["playback_blocked_forward_fraction"],
        "near_wall_forward_fraction": summary["playback_near_wall_forward_fraction"],
        "revisit_fraction_mean": summary["playback_revisit_fraction_mean"],
        "deaths_per_1000_decisions": summary["deaths_per_1000_decisions"],
        "food_events": summary["food_events"],
        "best_episode_food_progress": summary["best_observed_episode_food_progress"],
        "turn_left_to_right_ratio": summary["turn_left_to_right_ratio"],
        "live_published": receipt["live_published"],
        "action_overridden": False,
        "receipt_sha256": receipt["receipt_sha256"],
        "wall_seconds": receipt["wall_seconds"],
    }


def run_probe(source_dir: Path, work_root: Path, *, steps: int = STEPS) -> dict[str, Any]:
    if steps < 240:
        raise ValueError("At least 240 steps are required for comparable playback")
    before, world = _source_state(source_dir)
    if abs(float(brain_runtime.DANGER_ODOR_CURRENT_GAIN) - GAINS[0]) > 1e-9:
        raise RuntimeError("Baseline production danger odor gain is not frozen at 1.6")
    initial_stage2_clears = int((world.get("stage_clear_counts") or {}).get("2", 0))
    initial_world_ticks = int(world.get("total_world_ticks", 0))
    source_sha256 = _digest_json(before)

    results: dict[str, dict[str, Any]] = {}
    for gain in GAINS:
        arm = _run_arm(
            source_dir=source_dir,
            work_root=work_root,
            gain=gain,
            source_sha256=source_sha256,
            initial_stage2_clears=initial_stage2_clears,
            initial_world_ticks=initial_world_ticks,
            steps=steps,
        )
        results[str(gain)] = arm
        current, _ = _source_state(source_dir)
        if current != before:
            raise RuntimeError(f"Production checkpoint mutated during gain={gain}")

    baseline = results[str(GAINS[0])]
    comparisons = {
        str(gain): compare_candidate(baseline, results[str(gain)])
        for gain in GAINS[1:]
    }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS",
        "source_state_sha256": before,
        "source_checkpoint_unchanged": True,
        "baseline_gain": GAINS[0],
        "gains": list(GAINS),
        "steps_per_arm": steps,
        "starting_curriculum_stage": 2,
        "initial_stage2_clears": initial_stage2_clears,
        "initial_total_world_ticks": initial_world_ticks,
        "arms": results,
        "comparisons": comparisons,
        "limitations": {
            "neural_learning_active_in_isolated_arms": True,
            "world_clock_time_depends_on_runtime": True,
            "matched_predator_exposure_required_for_exploratory_signal": True,
            "single_run_not_causal_proof": True,
        },
        "claim_limits": {
            "runtime_code_modified": False,
            "production_checkpoint_mutated": False,
            "live_telemetry_published": False,
            "decoder_change_authorized": False,
            "production_gain_change_authorized": False,
            "stage2_improvement_verified": False,
        },
    }
    report["receipt_sha256"] = _digest_json(report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True)
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--steps", type=int, default=STEPS)
    args = parser.parse_args(argv)

    report = run_probe(Path(args.source_dir), Path(args.work_root), steps=args.steps)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        "DANGER_ORN_STAGE2_AB_EVIDENCE_PASS",
        report["receipt_sha256"],
        json.dumps(report["comparisons"], sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
