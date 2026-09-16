from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neurofly.brain_runtime import BrainDecision
from neurofly.goal_training import GoalMazeEnvironment
from neurofly.proprioception_temporal_runtime import TemporalGoalMazeSession
from neurofly.training import _public_goal_state


class RecordingBrain:
    name = "recording"

    def __init__(self, actions: list[str]) -> None:
        self.actions = list(actions)
        self.contexts: list[dict[str, Any]] = []

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision:
        self.contexts.append({} if context is None else context)
        action = self.actions.pop(0) if self.actions else "HOLD"
        return BrainDecision(action=action, backend=self.name, telemetry={})

    def save(self, path: str | Path) -> None:
        Path(path).write_text("recording-brain\n")


class RecordingEnvironment(GoalMazeEnvironment):
    def render_rgb(self, *, width: int = 320, height: int = 180) -> Any:
        return [[[0, 0, 0]]]


def _open_environment() -> RecordingEnvironment:
    env = RecordingEnvironment(seed=109)
    env.fly = {"x": 1, "y": 1, "dir": "RIGHT"}
    env.enemies = [{"x": env.cols - 2, "y": env.rows - 2}]
    env.grid[1][1] = " "
    env.grid[1][2] = " "
    return env


def _history(state: dict[str, Any]) -> dict[str, Any]:
    history = state["human_diagnostics"]["proprioception_temporal"]
    assert history["schema"] == "neurofly-proprioception-temporal-observability-v0.1"
    assert history["source"] == "verified-neural-handoff-receptor-domain"
    assert history["human_only"] is True
    assert history["capacity"] == 36
    assert history["history_persistence_enabled"] is False
    assert history["systematic_type_mapping_exposed"] is False
    assert history["current_calibration_authorized"] is False
    assert history["stimulation_enabled"] is False
    assert history["runtime_transduction_enabled"] is False
    assert history["neural_payload_eligible"] is False
    return history


def test_temporal_history_records_exact_post_firewall_handoff_in_order() -> None:
    brain = RecordingBrain(["FORWARD", "HOLD"])
    session = TemporalGoalMazeSession(
        brain,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )

    first_state = session.tick()
    first = _history(first_state)
    assert first["sample_count"] == 1
    assert first["samples"][0]["sequence"] == 1
    assert first["samples"][0]["channels"] == brain.contexts[0]["proprioception"]["channels"]
    assert first["samples"][0]["channels"] == {
        "hook_extension": 0.0,
        "hook_flexion": 0.0,
        "club_motion": 0.0,
        "club_vibration": 0.0,
    }

    second_state = session.tick()
    second = _history(second_state)
    assert second["sample_count"] == 2
    assert [sample["sequence"] for sample in second["samples"]] == [1, 2]
    assert second["samples"][1]["channels"] == brain.contexts[1]["proprioception"]["channels"]
    assert second["samples"][1]["channels"]["hook_extension"] == 1.0
    assert second["samples"][1]["channels"]["hook_flexion"] == 0.0
    assert second["samples"][1]["channels"]["club_motion"] == 1.0


def test_temporal_history_is_bounded_to_last_36_verified_handoffs() -> None:
    brain = RecordingBrain(["HOLD"] * 40)
    session = TemporalGoalMazeSession(
        brain,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )

    state: dict[str, Any] = {}
    for _ in range(40):
        state = session.tick()

    history = _history(state)
    assert history["sample_count"] == 36
    assert [sample["sequence"] for sample in history["samples"]] == list(range(5, 41))


def test_temporal_history_never_reenters_neural_context_or_exposes_private_state() -> None:
    brain = RecordingBrain(["FORWARD", "HOLD"])
    session = TemporalGoalMazeSession(
        brain,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )

    session.tick()
    state = session.tick()
    history = _history(state)

    assert "human_diagnostics" not in brain.contexts[0]
    assert "human_diagnostics" not in brain.contexts[1]
    assert "proprioception_temporal" not in brain.contexts[0]
    assert "proprioception_temporal" not in brain.contexts[1]

    encoded = json.dumps(history, sort_keys=True)
    for forbidden in (
        "joint_position",
        "joint_phase",
        "joint_delta",
        "motor_execution",
        "world_velocity",
        "world_displacement",
        "desired_action",
        "reward",
        "SNpp39",
        "SNpp41",
        "candidate_function",
        "systematic_type_binding",
    ):
        assert forbidden not in encoded


def test_temporal_history_is_not_checkpoint_persistent(tmp_path: Path) -> None:
    checkpoint = tmp_path / "brain.npz"
    brain = RecordingBrain(["FORWARD"])
    session = TemporalGoalMazeSession(
        brain,
        checkpoint=checkpoint,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )
    session.tick()
    assert session.proprioception_temporal_recorder.snapshot()["sample_count"] == 1
    session.save()

    maze_payload = json.loads(checkpoint.with_suffix(".maze.json").read_text())
    encoded = json.dumps(maze_payload, sort_keys=True)
    assert "proprioception_temporal" not in encoded
    assert "temporal_history" not in encoded

    restored = TemporalGoalMazeSession(
        RecordingBrain(["HOLD"]),
        checkpoint=checkpoint,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )
    assert restored.proprioception_temporal_recorder.snapshot()["sample_count"] == 0


def test_public_state_whitelists_only_safe_proprioception_diagnostics() -> None:
    brain = RecordingBrain(["HOLD"])
    session = TemporalGoalMazeSession(
        brain,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )
    state = session.tick()
    state["human_diagnostics"]["private_body_debug"] = {
        "joint_position": 0.75,
        "world_displacement": 99,
    }

    public = _public_goal_state(state)
    diagnostics = public["human_diagnostics"]

    assert set(diagnostics) == {"proprioception", "proprioception_temporal"}
    assert diagnostics["proprioception"] == state["human_diagnostics"]["proprioception"]
    assert diagnostics["proprioception_temporal"] == state["human_diagnostics"]["proprioception_temporal"]
    assert "private_body_debug" not in diagnostics
    assert "joint_position" not in json.dumps(diagnostics, sort_keys=True)
