from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from neurofly.brain_runtime import BrainDecision
from neurofly.cli import build_parser
from neurofly.light_chase import (
    LIGHT_CHASE_MODEL,
    LIGHT_CHASE_VISION_MODEL,
    LightChaseEnvironment,
    LightChaseSession,
)


class ScriptBrain:
    name = "script"

    def __init__(self, actions: list[str]) -> None:
        self.actions = list(actions)
        self.frames: list[Any] = []
        self.contexts: list[dict[str, Any]] = []
        self.reinforcements: list[str] = []

    def decide(self, frame, reinforcement="none", *, context=None) -> BrainDecision:
        self.frames.append(frame)
        self.contexts.append({} if context is None else json.loads(json.dumps(context)))
        self.reinforcements.append(reinforcement)
        action = self.actions.pop(0) if self.actions else "HOLD"
        return BrainDecision(
            action=action,
            backend=self.name,
            telemetry={"scripted": True},
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text("script-brain\n")


def test_light_chase_context_contains_no_privileged_target_geometry() -> None:
    brain = ScriptBrain(["HOLD"])
    env = LightChaseEnvironment(seed=7)
    session = LightChaseSession(brain, environment=env)

    state = session.tick()
    context = brain.contexts[0]
    encoded = json.dumps(context, sort_keys=True).lower()

    assert context["environment_model"] == LIGHT_CHASE_MODEL
    assert context["vision"]["model"] == LIGHT_CHASE_VISION_MODEL
    assert context["vision"]["target_coordinates_exposed"] is False
    assert context["vision"]["target_bearing_exposed"] is False
    assert context["vision"]["target_distance_exposed"] is False
    assert context["vision"]["recommended_action_exposed"] is False

    for token in (
        '"target":',
        '"x":',
        '"y":',
        "bearing_degrees",
        "distance_cells",
    ):
        assert token not in encoded
    assert "recommended_action" not in context["vision"]

    assert state["target"] == env.target
    assert len(brain.frames[0]) == 90
    assert len(brain.frames[0][0]) == 160


def test_render_is_egocentric_and_bright_target_moves_with_heading() -> None:
    env = LightChaseEnvironment(seed=9)
    env.agent = {"x": 5, "y": 5, "dir": "RIGHT"}
    env.target = {"x": 8, "y": 5}

    facing = env.render_rgb(width=80, height=40)
    brightest_facing = max(
        (sum(pixel), x)
        for row in facing
        for x, pixel in enumerate(row)
    )[1]

    env.agent["dir"] = "UP"
    turned = env.render_rgb(width=80, height=40)
    brightest_turned = max(
        (sum(pixel), x)
        for row in turned
        for x, pixel in enumerate(row)
    )[1]

    assert brightest_facing != brightest_turned


def test_forward_toward_light_receives_progress_reward() -> None:
    env = LightChaseEnvironment(seed=11)
    env.agent = {"x": 3, "y": 5, "dir": "RIGHT"}
    env.target = {"x": 8, "y": 5}

    state = env.step("FORWARD")

    assert state["agent"]["x"] == 4
    assert state["last_reward"] > 0.0
    assert state["last_event"] == "move"


def test_reaching_light_increments_goal_and_relocates_target() -> None:
    env = LightChaseEnvironment(seed=13)
    env.agent = {"x": 3, "y": 5, "dir": "RIGHT"}
    env.target = {"x": 4, "y": 5}
    old_target = dict(env.target)

    state = env.step("FORWARD")

    assert state["total_lights"] == 1
    assert state["episode"] == 2
    assert state["last_event"] == "light_reached"
    assert state["last_reward"] > env.reach_reward - 1.0
    assert state["target"] != old_target
    assert state["target"] != state["agent"]


def test_environment_checkpoint_round_trip_is_exact_and_rng_resumable() -> None:
    env = LightChaseEnvironment(seed=17)
    env.step("TURN_LEFT")
    env.step("FORWARD")
    payload = env.persistence_snapshot()

    restored = LightChaseEnvironment(seed=999, cols=env.cols, rows=env.rows)
    restored.restore(json.loads(json.dumps(payload)))

    assert restored.persistence_snapshot() == payload

    env.agent = {"x": 1, "y": 1, "dir": "RIGHT"}
    restored.agent = {"x": 1, "y": 1, "dir": "RIGHT"}
    env.target = {"x": 2, "y": 1}
    restored.target = {"x": 2, "y": 1}

    a = env.step("FORWARD")
    b = restored.step("FORWARD")
    assert a["target"] == b["target"]


def test_session_checkpoint_restores_world_and_pending_reinforcement(tmp_path: Path) -> None:
    checkpoint = tmp_path / "light-brain.npz"
    brain = ScriptBrain(["FORWARD"])
    env = LightChaseEnvironment(seed=21)
    env.agent = {"x": 3, "y": 5, "dir": "RIGHT"}
    env.target = {"x": 4, "y": 5}
    session = LightChaseSession(
        brain,
        checkpoint=checkpoint,
        checkpoint_every=9999.0,
        environment=env,
    )

    state = session.tick()
    assert state["last_event"] == "light_reached"
    assert session.pending_reinforcement == "reward"
    session.save()

    restored_brain = ScriptBrain(["HOLD"])
    restored = LightChaseSession(
        restored_brain,
        checkpoint=checkpoint,
        checkpoint_every=9999.0,
        environment=LightChaseEnvironment(seed=21),
    )

    assert restored.environment.persistence_snapshot() == session.environment.persistence_snapshot()
    assert restored.pending_reinforcement == "reward"
    restored.tick()
    assert restored_brain.reinforcements[0] == "reward"


def test_invalid_action_fails_closed() -> None:
    env = LightChaseEnvironment(seed=31)
    with pytest.raises(ValueError):
        env.step("TELEPORT")


def test_cli_exposes_light_run_without_privileged_options() -> None:
    args = build_parser().parse_args(
        ["light-run", "--brain", "demo", "--steps", "3", "--interval", "0"]
    )

    assert args.command == "light-run"
    assert args.brain == "demo"
    assert args.steps == 3
    assert args.interval == 0.0
    assert not hasattr(args, "target_x")
    assert not hasattr(args, "target_y")
