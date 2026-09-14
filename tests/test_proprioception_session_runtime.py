from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neurofly.brain_runtime import BrainDecision
from neurofly.goal_training import GoalMazeEnvironment, GoalMazeSession
from neurofly.maze_runtime import StepResult
from neurofly.proprioception import proprioceptive_channel_levels
from neurofly.sensory_contract import assert_unprivileged_agent_input


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


class OverrideToHoldEnvironment(RecordingEnvironment):
    def agent_step(self, action: str, *, move_enemies: bool) -> StepResult:
        self.last_applied_action = "HOLD"
        return super().agent_step("HOLD", move_enemies=move_enemies)


class ForcedTerminalEnvironment(RecordingEnvironment):
    def agent_step(self, action: str, *, move_enemies: bool) -> StepResult:
        result = super().agent_step(action, move_enemies=move_enemies)
        return StepResult(reward=result.reward, event="forced_terminal", terminal=True)


class ResetDuringDecisionBrain(RecordingBrain):
    def __init__(self, environment: RecordingEnvironment) -> None:
        super().__init__(["FORWARD"])
        self.environment = environment

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision:
        decision = super().decide(frame, reinforcement, context=context)
        self.environment.reset("async-reset")
        return decision


def _neutral_channels(context: dict[str, Any]) -> dict[str, Any]:
    levels = proprioceptive_channel_levels(context["proprioception"])
    return {
        "hook_extension": levels["hook_extension"],
        "hook_flexion": levels["hook_flexion"],
        "club_motion": levels["club_motion"],
        "club_vibration": levels["club_vibration"],
    }


def _open_environment() -> RecordingEnvironment:
    env = RecordingEnvironment(seed=109)
    env.fly = {"x": 1, "y": 1, "dir": "RIGHT"}
    env.enemies = [{"x": env.cols - 2, "y": env.rows - 2}]
    env.grid[1][1] = " "
    env.grid[1][2] = " "
    return env


def _blocked_environment() -> RecordingEnvironment:
    env = _open_environment()
    env.grid[1][2] = "#"
    return env


def test_first_decision_is_neutral_and_forward_motion_arrives_one_decision_later() -> None:
    env = _open_environment()
    brain = RecordingBrain(["FORWARD", "HOLD"])
    session = GoalMazeSession(brain, environment=env, world_tick_seconds=3600.0)

    session.tick()
    session.tick()

    first, second = brain.contexts
    assert _neutral_channels(first) == {
        "hook_extension": 0.0,
        "hook_flexion": 0.0,
        "club_motion": 0.0,
        "club_vibration": 0.0,
    }
    assert _neutral_channels(second) == {
        "hook_extension": 1.0,
        "hook_flexion": 0.0,
        "club_motion": 1.0,
        "club_vibration": 0.0,
    }
    assert second["proprioception"]["stimulation_enabled"] is False
    assert second["proprioception"]["runtime_transduction_enabled"] is False


def test_blocked_and_open_forward_have_same_proprioception_but_different_touch() -> None:
    open_brain = RecordingBrain(["FORWARD", "HOLD"])
    open_session = GoalMazeSession(
        open_brain,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )
    open_session.tick()
    open_session.tick()

    blocked_brain = RecordingBrain(["FORWARD", "HOLD"])
    blocked_session = GoalMazeSession(
        blocked_brain,
        environment=_blocked_environment(),
        world_tick_seconds=3600.0,
    )
    blocked_session.tick()
    blocked_session.tick()

    assert (
        blocked_brain.contexts[1]["proprioception"]
        == open_brain.contexts[1]["proprioception"]
    )
    assert open_brain.contexts[1]["contact_mechanosensation"]["contact"] is False
    assert blocked_brain.contexts[1]["contact_mechanosensation"]["contact"] is True


def test_controller_override_uses_actual_applied_execution_not_requested_action() -> None:
    env = OverrideToHoldEnvironment(seed=109)
    brain = RecordingBrain(["FORWARD", "HOLD"])
    session = GoalMazeSession(brain, environment=env, world_tick_seconds=3600.0)

    session.tick()
    session.tick()

    assert _neutral_channels(brain.contexts[1]) == {
        "hook_extension": 0.0,
        "hook_flexion": 0.0,
        "club_motion": 0.0,
        "club_vibration": 0.0,
    }
    assert session.virtual_body.last_motor_execution == "HOLD"


def test_left_and_right_turns_are_not_encoded_as_hidden_direction_labels() -> None:
    left_brain = RecordingBrain(["TURN_LEFT", "HOLD"])
    left_session = GoalMazeSession(
        left_brain,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )
    left_session.tick()
    left_session.tick()

    right_brain = RecordingBrain(["TURN_RIGHT", "HOLD"])
    right_session = GoalMazeSession(
        right_brain,
        environment=_open_environment(),
        world_tick_seconds=3600.0,
    )
    right_session.tick()
    right_session.tick()

    assert (
        left_brain.contexts[1]["proprioception"]
        == right_brain.contexts[1]["proprioception"]
    )


def test_context_contains_only_receptor_domain_proprioception() -> None:
    env = _open_environment()
    brain = RecordingBrain(["FORWARD", "HOLD"])
    session = GoalMazeSession(brain, environment=env, world_tick_seconds=3600.0)
    session.tick()
    session.tick()

    payload = brain.contexts[1]["proprioception"]
    assert_unprivileged_agent_input({"proprioception": payload})
    forbidden = {
        "motor_execution",
        "joint_phase",
        "joint_position",
        "joint_delta",
        "mechanical_vibration",
        "heading",
        "world_velocity",
        "world_displacement",
        "reward",
        "desired_action",
        "x",
        "y",
    }

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                assert key not in forbidden
                walk(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                walk(nested)

    walk(payload)


def test_terminal_reset_neutralizes_body_before_next_episode() -> None:
    env = ForcedTerminalEnvironment(seed=109)
    brain = RecordingBrain(["FORWARD", "HOLD"])
    session = GoalMazeSession(brain, environment=env, world_tick_seconds=3600.0)

    session.tick()
    assert session.virtual_body.step_index == 0
    session.tick()

    assert _neutral_channels(brain.contexts[1]) == {
        "hook_extension": 0.0,
        "hook_flexion": 0.0,
        "club_motion": 0.0,
        "club_vibration": 0.0,
    }


def test_stale_decision_does_not_advance_virtual_body() -> None:
    env = _open_environment()
    brain = ResetDuringDecisionBrain(env)
    session = GoalMazeSession(brain, environment=env, world_tick_seconds=3600.0)

    state = session.tick()

    assert state["state_kind"] == "stale_decision"
    assert state["decision_applied"] is False
    assert session.virtual_body.step_index == 0
    assert proprioceptive_channel_levels(session.pending_proprioception)[
        "club_motion"
    ] == 0.0


def test_checkpoint_preserves_private_body_and_pending_receptor_pulse(tmp_path: Path) -> None:
    checkpoint = tmp_path / "brain.npz"
    first_brain = RecordingBrain(["FORWARD"])
    first = GoalMazeSession(
        first_brain,
        environment=_open_environment(),
        checkpoint=checkpoint,
        checkpoint_every=999999.0,
        world_tick_seconds=3600.0,
    )
    first.tick()
    expected_pending = first.pending_proprioception
    expected_body = first.virtual_body.persistence_snapshot()
    first.save()

    state_payload = json.loads(checkpoint.with_suffix(".maze.json").read_text())
    assert state_payload["_pending_proprioception"] == expected_pending
    assert state_payload["_virtual_body_state"] == expected_body

    restored_brain = RecordingBrain(["HOLD", "HOLD"])
    restored = GoalMazeSession(
        restored_brain,
        environment=RecordingEnvironment(seed=999),
        checkpoint=checkpoint,
        checkpoint_every=999999.0,
        world_tick_seconds=3600.0,
    )
    assert restored.virtual_body.persistence_snapshot() == expected_body

    restored.tick()
    assert restored_brain.contexts[0]["proprioception"] == expected_pending
    restored.tick()
    assert restored_brain.contexts[1]["proprioception"]["channels"][
        "hook_flexion"
    ] > 0.0
