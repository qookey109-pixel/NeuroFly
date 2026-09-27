from __future__ import annotations

from neurofly.behavior_diagnostics import SCHEMA, summarize_receipt


def _row(
    *,
    step: int,
    episode: int,
    action: str,
    event: str | None,
    food_left: int,
    deaths: int,
    clears: int,
    food_lr: tuple[float, float],
    danger_lr: tuple[float, float],
):
    return {
        "step": step,
        "episode": episode,
        "applied_action": action,
        "event": event,
        "food_left": food_left,
        "total_deaths": deaths,
        "total_clears": clears,
        "curriculum_stage": 2,
        "curriculum_stage_name": "full-maze-slow-predator",
        "food_odor_left": food_lr[0],
        "food_odor_right": food_lr[1],
        "danger_odor_left": danger_lr[0],
        "danger_odor_right": danger_lr[1],
    }


def test_behavior_summary_freezes_stage2_metrics() -> None:
    receipt = {
        "receipt_sha256": "abc",
        "curriculum_version": "neurofly-curriculum-v4",
        "olfaction_model": "neurofly-virtual-olfaction-v4",
        "observations": [
            _row(
                step=1,
                episode=10,
                action="FORWARD",
                event="food",
                food_left=10,
                deaths=5,
                clears=2,
                food_lr=(1.0, 1.0),
                danger_lr=(0.2, 0.4),
            ),
            _row(
                step=2,
                episode=10,
                action="TURN_LEFT",
                event=None,
                food_left=9,
                deaths=5,
                clears=2,
                food_lr=(0.8, 1.0),
                danger_lr=(0.3, 0.4),
            ),
            _row(
                step=3,
                episode=11,
                action="FORWARD",
                event="captured",
                food_left=12,
                deaths=6,
                clears=2,
                food_lr=(0.4, 0.7),
                danger_lr=(0.7, 0.2),
            ),
        ],
        "trajectory": [
            {
                "episode": 10,
                "fly": {"x": 1, "y": 1},
                "anti_stall_stationary_steps": 0,
            },
            {
                "episode": 10,
                "fly": {"x": 1, "y": 1},
                "anti_stall_stationary_steps": 2,
            },
            {
                "episode": 10,
                "fly": {"x": 2, "y": 1},
                "anti_stall_stationary_steps": 0,
            },
        ],
    }

    summary = summarize_receipt(receipt)

    assert summary["schema"] == SCHEMA
    assert summary["steps_observed"] == 3
    assert summary["curriculum_stage"] == 2
    assert summary["action_counts"] == {"FORWARD": 2, "TURN_LEFT": 1}
    assert summary["food_events"] == 1
    assert summary["death_delta"] == 1
    assert summary["deaths_per_1000_decisions"] == 1000 / 3
    assert summary["clear_delta"] == 0
    assert summary["food_bilateral_saturation_fraction"] == 1 / 3
    assert abs(summary["food_abs_contrast_mean"] - (0.0 + 0.2 + 0.3) / 3) < 1e-12
    assert abs(summary["danger_abs_contrast_mean"] - (0.2 + 0.1 + 0.5) / 3) < 1e-12
    assert summary["best_observed_episode_food_progress"] == 1
    assert summary["playback_episode_count"] == 1
    assert abs(summary["playback_revisit_fraction_mean"] - 1 / 3) < 1e-12
    assert summary["playback_max_stationary_steps"] == 2


def test_behavior_summary_handles_empty_receipt() -> None:
    summary = summarize_receipt({"observations": [], "trajectory": []})

    assert summary["steps_observed"] == 0
    assert summary["death_delta"] == 0
    assert summary["deaths_per_1000_decisions"] is None
    assert summary["food_bilateral_saturation_fraction"] is None
    assert summary["playback_revisit_fraction_mean"] is None
