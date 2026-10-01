from __future__ import annotations

from neurofly.behavior_diagnostics import SCHEMA, summarize_receipt


def _row(*, step: int, episode: int, action: str, event: str | None, food_left: int,
         deaths: int, clears: int, loop: bool, wall: bool, food_lr: tuple[float, float],
         danger_lr: tuple[float, float]) -> dict:
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
        "sensory_loop_triggered": loop,
        "frontal_wall_triggered": wall,
        "food_odor_left": food_lr[0],
        "food_odor_right": food_lr[1],
        "danger_odor_left": danger_lr[0],
        "danger_odor_right": danger_lr[1],
    }


def test_behavior_summary_v3_tracks_loop_wall_and_turn_metrics() -> None:
    receipt = {
        "receipt_sha256": "abc",
        "curriculum_version": "neurofly-curriculum-v4",
        "olfaction_model": "neurofly-virtual-olfaction-v4",
        "observations": [
            _row(step=1, episode=10, action="FORWARD", event="food", food_left=10,
                 deaths=5, clears=2, loop=False, wall=True, food_lr=(1.0, 1.0), danger_lr=(0.2, 0.4)),
            _row(step=2, episode=10, action="TURN_LEFT", event=None, food_left=9,
                 deaths=5, clears=2, loop=True, wall=False, food_lr=(0.8, 1.0), danger_lr=(0.3, 0.4)),
            _row(step=3, episode=11, action="TURN_RIGHT", event="captured", food_left=12,
                 deaths=6, clears=2, loop=False, wall=False, food_lr=(0.4, 0.7), danger_lr=(0.7, 0.2)),
        ],
        "trajectory": [
            {"episode": 10, "fly": {"x": 1, "y": 1}, "applied_action": "HOLD", "anti_stall_stationary_steps": 0},
            {"episode": 10, "fly": {"x": 1, "y": 1}, "applied_action": "FORWARD", "anti_stall_stationary_steps": 2},
            {"episode": 10, "fly": {"x": 2, "y": 1}, "applied_action": "FORWARD", "anti_stall_stationary_steps": 0},
        ],
    }

    summary = summarize_receipt(receipt)

    assert summary["schema"] == SCHEMA
    assert summary["steps_observed"] == 3
    assert summary["action_counts"] == {"FORWARD": 1, "TURN_LEFT": 1, "TURN_RIGHT": 1}
    assert summary["turn_left_to_right_ratio"] == 1.0
    assert summary["sensory_loop_trigger_count"] == 1
    assert summary["sensory_loop_trigger_fraction"] == 1 / 3
    assert summary["frontal_wall_trigger_count"] == 1
    assert summary["frontal_wall_trigger_fraction"] == 1 / 3
    assert summary["food_events"] == 1
    assert summary["death_delta"] == 1
    assert summary["deaths_per_1000_decisions"] == 1000 / 3
    assert summary["clear_delta"] == 0
    assert summary["food_bilateral_saturation_fraction"] == 1 / 3
    assert summary["best_observed_episode_food_progress"] == 1
    assert abs(summary["playback_revisit_fraction_mean"] - 1 / 3) < 1e-12
    assert summary["playback_max_stationary_steps"] == 2
    assert summary["playback_forward_decisions"] == 2
    assert summary["playback_blocked_forward_count"] == 1
    assert summary["playback_blocked_forward_fraction"] == 0.5


def test_behavior_summary_v3_handles_empty_receipt() -> None:
    summary = summarize_receipt({"observations": [], "trajectory": []})
    assert summary["steps_observed"] == 0
    assert summary["deaths_per_1000_decisions"] is None
    assert summary["turn_left_to_right_ratio"] is None
    assert summary["sensory_loop_trigger_fraction"] is None
    assert summary["frontal_wall_trigger_fraction"] is None
    assert summary["playback_blocked_forward_fraction"] is None
    assert summary["playback_revisit_fraction_mean"] is None
