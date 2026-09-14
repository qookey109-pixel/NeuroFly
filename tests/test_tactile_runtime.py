from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from neurofly.brain_runtime import BrainDecision
from neurofly.goal_training import GoalMazeEnvironment, GoalMazeSession
from neurofly.tactile import (
    TACTILE_MODEL,
    blocked_forward_contact,
    contact_mechanosensation,
    tactile_channel_levels,
)


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
    """Exercise contact routing without optional image-rendering dependencies."""

    def render_rgb(self, *, width: int = 320, height: int = 180) -> Any:
        return [[[0, 0, 0]]]


def _wall_ahead_environment() -> RecordingEnvironment:
    env = RecordingEnvironment(seed=109)
    env.fly = {"x": 1, "y": 1, "dir": "RIGHT"}
    env.enemies = [{"x": env.cols - 2, "y": env.rows - 2}]
    env.grid[1][1] = " "
    env.grid[1][2] = "#"
    return env


def _open_ahead_environment() -> RecordingEnvironment:
    env = RecordingEnvironment(seed=109)
    env.fly = {"x": 1, "y": 1, "dir": "RIGHT"}
    env.enemies = [{"x": env.cols - 2, "y": env.rows - 2}]
    env.grid[1][1] = " "
    env.grid[1][2] = " "
    return env


def test_tactile_contract_is_contact_only_and_current_disabled() -> None:
    idle = contact_mechanosensation(front=0.0)
    assert idle == {
        "model": TACTILE_MODEL,
        "available": True,
        "encoding": "blocked-forward-external-touch-proxy",
        "contact": False,
        "channels": {"front": 0.0},
        "stimulation_enabled": False,
    }

    touch = contact_mechanosensation(front=1.0)
    assert tactile_channel_levels(touch) == {
        "available": True,
        "contact": True,
        "front": 1.0,
    }

    malformed = dict(touch)
    malformed["contact"] = False
    with pytest.raises(ValueError, match="contact flag"):
        tactile_channel_levels(malformed)

    current_enabled = dict(touch)
    current_enabled["stimulation_enabled"] = True
    with pytest.raises(ValueError, match="stimulation"):
        tactile_channel_levels(current_enabled)


def test_blocked_forward_is_contact_but_other_immobility_is_not() -> None:
    assert blocked_forward_contact(
        applied_action="FORWARD",
        before_position=(1, 1),
        after_position=(1, 1),
        terminal=False,
    )["contact"] is True

    for action in ("HOLD", "TURN_LEFT", "TURN_RIGHT"):
        assert blocked_forward_contact(
            applied_action=action,
            before_position=(1, 1),
            after_position=(1, 1),
            terminal=False,
        )["contact"] is False

    assert blocked_forward_contact(
        applied_action="FORWARD",
        before_position=(1, 1),
        after_position=(2, 1),
        terminal=False,
    )["contact"] is False

    # Predator/body terminal events are outside tactile v1 and cannot be
    # inferred merely because the body did not translate.
    assert blocked_forward_contact(
        applied_action="FORWARD",
        before_position=(1, 1),
        after_position=(1, 1),
        terminal=True,
    )["contact"] is False


def test_blocked_forward_becomes_exactly_one_next_decision_touch_pulse() -> None:
    env = _wall_ahead_environment()
    brain = RecordingBrain(["FORWARD", "HOLD", "HOLD"])
    session = GoalMazeSession(
        brain,
        environment=env,
        world_tick_seconds=3600.0,
    )

    session.tick()
    assert session.pending_tactile_contact is True
    session.tick()
    assert session.pending_tactile_contact is False
    session.tick()

    first, second, third = brain.contexts
    assert first["contact_mechanosensation"]["contact"] is False
    assert first["contact_mechanosensation"]["channels"] == {"front": 0.0}

    assert second["contact_mechanosensation"]["contact"] is True
    assert second["contact_mechanosensation"]["channels"] == {"front": 1.0}
    assert second["contact_mechanosensation"]["stimulation_enabled"] is False

    assert third["contact_mechanosensation"]["contact"] is False
    assert third["contact_mechanosensation"]["channels"] == {"front": 0.0}


def test_hold_and_successful_forward_do_not_create_false_touch() -> None:
    hold_env = _wall_ahead_environment()
    hold_brain = RecordingBrain(["HOLD", "HOLD"])
    hold_session = GoalMazeSession(
        hold_brain,
        environment=hold_env,
        world_tick_seconds=3600.0,
    )
    hold_session.tick()
    hold_session.tick()
    assert hold_brain.contexts[1]["contact_mechanosensation"]["contact"] is False

    move_env = _open_ahead_environment()
    move_brain = RecordingBrain(["FORWARD", "HOLD"])
    move_session = GoalMazeSession(
        move_brain,
        environment=move_env,
        world_tick_seconds=3600.0,
    )
    move_session.tick()
    move_session.tick()
    assert move_brain.contexts[1]["contact_mechanosensation"]["contact"] is False


def test_pending_touch_survives_checkpoint_and_is_consumed_once(tmp_path: Path) -> None:
    checkpoint = tmp_path / "brain.npz"
    env = _wall_ahead_environment()
    first_brain = RecordingBrain(["FORWARD"])
    session = GoalMazeSession(
        first_brain,
        environment=env,
        checkpoint=checkpoint,
        checkpoint_every=999999.0,
        world_tick_seconds=3600.0,
    )
    session.tick()
    assert session.pending_tactile_contact is True
    session.save()

    restored_brain = RecordingBrain(["HOLD", "HOLD"])
    restored_env = RecordingEnvironment(seed=999)
    restored = GoalMazeSession(
        restored_brain,
        environment=restored_env,
        checkpoint=checkpoint,
        checkpoint_every=999999.0,
        world_tick_seconds=3600.0,
    )

    assert restored.pending_tactile_contact is True
    restored.tick()
    restored.tick()

    assert restored_brain.contexts[0]["contact_mechanosensation"]["contact"] is True
    assert restored_brain.contexts[1]["contact_mechanosensation"]["contact"] is False
    assert restored.pending_tactile_contact is False
