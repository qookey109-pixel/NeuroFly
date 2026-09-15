from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neurofly.brain_runtime import BrainDecision
from neurofly.goal_training import GoalMazeEnvironment, GoalMazeSession
from neurofly.proprioception import proprioceptive_channel_levels


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


def _diagnostic(state: dict[str, Any]) -> dict[str, Any]:
    record = state["human_diagnostics"]["proprioception"]
    assert record["source"] == "latest-neural-handoff-receptor-domain"
    assert record["model"] == "neurofly-feco-motion-proxy-v0.1"
    assert record["encoding"] == "virtual-joint-motion-only-proxy"
    assert record["stimulation_enabled"] is False
    assert record["runtime_transduction_enabled"] is False
    assert record["systematic_type_mapping_exposed"] is False
    return record


def test_live_diagnostic_matches_exact_neural_handoff_not_next_pending_pulse() -> None:
    brain = RecordingBrain(["FORWARD", "HOLD"])
    session = GoalMazeSession(
        brain,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )

    first_state = session.tick()
    first_record = _diagnostic(first_state)
    first_context = brain.contexts[0]["proprioception"]

    assert first_record["channels"] == first_context["channels"]
    assert first_record["channels"] == {
        "hook_extension": 0.0,
        "hook_flexion": 0.0,
        "club_motion": 0.0,
        "club_vibration": 0.0,
    }

    pending_after_forward = proprioceptive_channel_levels(session.pending_proprioception)
    assert pending_after_forward["hook_extension"] == 1.0
    assert first_record["channels"]["hook_extension"] == 0.0

    second_state = session.tick()
    second_record = _diagnostic(second_state)
    second_context = brain.contexts[1]["proprioception"]

    assert second_record["channels"] == second_context["channels"]
    assert second_record["channels"]["hook_extension"] == 1.0
    assert second_record["channels"]["hook_flexion"] == 0.0
    assert second_record["channels"]["club_motion"] == 1.0


def test_human_diagnostic_does_not_cross_back_into_neural_context() -> None:
    brain = RecordingBrain(["FORWARD"])
    session = GoalMazeSession(
        brain,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )

    state = session.tick()

    assert "human_diagnostics" in state
    assert "human_diagnostics" not in brain.contexts[0]
    assert "proprioception_semantics" not in brain.contexts[0]


def test_live_diagnostic_exposes_no_private_body_or_systematic_type_mapping() -> None:
    brain = RecordingBrain(["FORWARD", "HOLD"])
    session = GoalMazeSession(
        brain,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )

    session.tick()
    record = _diagnostic(session.tick())
    encoded = json.dumps(record, sort_keys=True)

    for forbidden in (
        "joint_position",
        "joint_phase",
        "joint_delta",
        "motor_execution",
        "world_velocity",
        "world_displacement",
        "desired_action",
        "SNpp39",
        "SNpp41",
        "candidate_function",
        "systematic_type_binding",
    ):
        assert forbidden not in encoded

    assert set(record["channels"]) == {
        "hook_extension",
        "hook_flexion",
        "club_motion",
        "club_vibration",
    }
