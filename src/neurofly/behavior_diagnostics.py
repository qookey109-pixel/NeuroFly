from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCHEMA = "neurofly-behavior-summary-v3"


def _fraction(numerator: int | float, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return float(numerator) / float(denominator)


def summarize_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    observations = receipt.get("observations") or []
    trajectory = receipt.get("trajectory") or []
    if not isinstance(observations, list):
        raise ValueError("receipt observations must be a list")
    if not isinstance(trajectory, list):
        raise ValueError("receipt trajectory must be a list")

    action_counts: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    food_saturation = 0
    loop_triggers = 0
    frontal_wall_triggers = 0
    food_contrasts: list[float] = []
    danger_contrasts: list[float] = []
    episodes: dict[int, dict[str, int | None]] = defaultdict(
        lambda: {"start_food": None, "min_food": None}
    )

    for row in observations:
        if not isinstance(row, dict):
            continue
        action = str(row.get("applied_action") or row.get("action") or "UNKNOWN")
        action_counts[action] += 1
        event_counts[str(row.get("event") or "none")] += 1
        if bool(row.get("sensory_loop_triggered", False)):
            loop_triggers += 1
        if bool(row.get("frontal_wall_triggered", False)):
            frontal_wall_triggers += 1

        food_left_odor = float(row.get("food_odor_left", 0.0) or 0.0)
        food_right_odor = float(row.get("food_odor_right", 0.0) or 0.0)
        danger_left_odor = float(row.get("danger_odor_left", 0.0) or 0.0)
        danger_right_odor = float(row.get("danger_odor_right", 0.0) or 0.0)
        food_contrasts.append(abs(food_left_odor - food_right_odor))
        danger_contrasts.append(abs(danger_left_odor - danger_right_odor))
        if food_left_odor >= 0.999999 and food_right_odor >= 0.999999:
            food_saturation += 1

        episode = int(row.get("episode", 0) or 0)
        food_left = row.get("food_left")
        if food_left is not None:
            remaining = int(food_left)
            entry = episodes[episode]
            if entry["start_food"] is None:
                entry["start_food"] = remaining
            current_min = entry["min_food"]
            entry["min_food"] = remaining if current_min is None else min(current_min, remaining)

    steps = len(observations)
    first_deaths = int(observations[0].get("total_deaths", 0)) if observations else 0
    last_deaths = int(observations[-1].get("total_deaths", first_deaths)) if observations else first_deaths
    first_clears = int(observations[0].get("total_clears", 0)) if observations else 0
    last_clears = int(observations[-1].get("total_clears", first_clears)) if observations else first_clears

    positions_by_episode: dict[int, list[tuple[int, int]]] = defaultdict(list)
    max_stationary_steps = 0
    playback_forward_decisions = 0
    playback_blocked_forward = 0
    previous_sample: dict[str, Any] | None = None
    for sample in trajectory:
        if not isinstance(sample, dict):
            continue
        fly = sample.get("fly") or {}
        if isinstance(fly, dict) and "x" in fly and "y" in fly:
            positions_by_episode[int(sample.get("episode", 0) or 0)].append(
                (int(fly["x"]), int(fly["y"]))
            )
        max_stationary_steps = max(
            max_stationary_steps,
            int(sample.get("anti_stall_stationary_steps", 0) or 0),
        )

        if previous_sample is not None and sample.get("episode") == previous_sample.get("episode"):
            action = str(sample.get("applied_action") or sample.get("last_action") or "")
            if action == "FORWARD":
                playback_forward_decisions += 1
                previous_fly = previous_sample.get("fly") or {}
                if (
                    isinstance(previous_fly, dict)
                    and isinstance(fly, dict)
                    and "x" in previous_fly
                    and "y" in previous_fly
                    and "x" in fly
                    and "y" in fly
                    and (int(previous_fly["x"]), int(previous_fly["y"]))
                    == (int(fly["x"]), int(fly["y"]))
                ):
                    playback_blocked_forward += 1
        previous_sample = sample

    revisit_fractions = [
        1.0 - len(set(positions)) / len(positions)
        for positions in positions_by_episode.values()
        if positions
    ]
    episode_progress = [
        int(entry["start_food"]) - int(entry["min_food"])
        for entry in episodes.values()
        if entry["start_food"] is not None and entry["min_food"] is not None
    ]
    death_delta = last_deaths - first_deaths
    clear_delta = last_clears - first_clears

    return {
        "schema": SCHEMA,
        "receipt_sha256": receipt.get("receipt_sha256"),
        "curriculum_version": receipt.get("curriculum_version"),
        "olfaction_model": receipt.get("olfaction_model"),
        "steps_observed": steps,
        "curriculum_stage": int(observations[-1].get("curriculum_stage", 0)) if observations else None,
        "curriculum_stage_name": observations[-1].get("curriculum_stage_name") if observations else None,
        "action_counts": dict(sorted(action_counts.items())),
        "action_fractions": {action: _fraction(count, steps) for action, count in sorted(action_counts.items())},
        "turn_left_to_right_ratio": (
            None if action_counts["TURN_RIGHT"] == 0
            else float(action_counts["TURN_LEFT"]) / float(action_counts["TURN_RIGHT"])
        ),
        "event_counts": dict(sorted(event_counts.items())),
        "food_events": int(event_counts["food"] + event_counts["energy_food"]),
        "death_delta": death_delta,
        "deaths_per_1000_decisions": None if steps == 0 else death_delta * 1000.0 / steps,
        "clear_delta": clear_delta,
        "sensory_loop_trigger_count": loop_triggers,
        "sensory_loop_trigger_fraction": _fraction(loop_triggers, steps),
        "frontal_wall_trigger_count": frontal_wall_triggers,
        "frontal_wall_trigger_fraction": _fraction(frontal_wall_triggers, steps),
        "food_bilateral_saturation_fraction": _fraction(food_saturation, steps),
        "food_abs_contrast_mean": None if not food_contrasts else sum(food_contrasts) / len(food_contrasts),
        "danger_abs_contrast_mean": None if not danger_contrasts else sum(danger_contrasts) / len(danger_contrasts),
        "best_observed_episode_food_progress": max(episode_progress, default=0),
        "playback_episode_count": len(positions_by_episode),
        "playback_revisit_fraction_mean": None if not revisit_fractions else sum(revisit_fractions) / len(revisit_fractions),
        "playback_revisit_fraction_max": None if not revisit_fractions else max(revisit_fractions),
        "playback_max_stationary_steps": max_stationary_steps,
        "playback_forward_decisions": playback_forward_decisions,
        "playback_blocked_forward_count": playback_blocked_forward,
        "playback_blocked_forward_fraction": _fraction(
            playback_blocked_forward, playback_forward_decisions
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize NeuroFly behavioral evidence from a training receipt.")
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    receipt = json.loads(Path(args.receipt).read_text())
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be a JSON object")
    summary = summarize_receipt(receipt)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(
        "BEHAVIOR_SUMMARY_V3",
        "stage=", summary["curriculum_stage"],
        "deaths_per_1000=", summary["deaths_per_1000_decisions"],
        "food_events=", summary["food_events"],
        "clear_delta=", summary["clear_delta"],
        "loop_triggers=", summary["sensory_loop_trigger_count"],
        "wall_triggers=", summary["frontal_wall_trigger_count"],
        "blocked_forward=", summary["playback_blocked_forward_fraction"],
        "revisit_mean=", summary["playback_revisit_fraction_mean"],
        "turn_lr_ratio=", summary["turn_left_to_right_ratio"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
