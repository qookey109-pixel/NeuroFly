from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from neurofly.brain_runtime import BrainDecision
from neurofly.cli import build_parser
from neurofly.environment_adapter import (
    ENVIRONMENT_ADAPTER_SCHEMA,
    EnvironmentSession,
    LightChaseAdapter,
    MazeChaseAdapter,
    assert_sensory_only_context,
    make_environment_adapter,
)
from neurofly.light_chase import LightChaseEnvironment
from neurofly.maze_runtime import MazeEnvironment
from neurofly.olfaction import OLFACTION_MODEL


CONTRACT = Path("data/environment_adapter_contract_v01.json")


class CaptureBrain:
    name = "capture"

    def __init__(self, actions: list[str] | None = None) -> None:
        self.actions = list(actions or ["HOLD"])
        self.calls: list[dict[str, Any]] = []

    def decide(self, frame, reinforcement="none", *, context=None) -> BrainDecision:
        self.calls.append(
            {
                "frame": frame,
                "reinforcement": reinforcement,
                "context": json.loads(json.dumps(context or {})),
            }
        )
        action = self.actions.pop(0) if self.actions else "HOLD"
        return BrainDecision(
            action=action,
            backend=self.name,
            telemetry={"capture": True},
        )

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("capture-brain\n")


class NoVisualMaze(MazeEnvironment):
    def render_rgb(self, *, width: int = 320, height: int = 180):
        raise RuntimeError("optional visual dependencies unavailable in unit test")


def _all_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys |= _all_keys(item)
    elif isinstance(value, list):
        for item in value:
            keys |= _all_keys(item)
    return keys


def test_contract_declares_two_real_environment_adapters() -> None:
    contract = json.loads(CONTRACT.read_text())

    assert contract["schema"] == "neurofly-environment-adapter-contract-v0.1"
    assert contract["status"] == "PLATFORM_CONTRACT"
    assert contract["adapter_schema"] == ENVIRONMENT_ADAPTER_SCHEMA
    assert contract["required_environments"] == [
        "neurofly-maze-chase-v0.1",
        "neurofly-light-chase-v0.1",
    ]
    assert contract["required_actions"] == [
        "TURN_LEFT",
        "TURN_RIGHT",
        "FORWARD",
        "HOLD",
    ]
    assert all(contract["required_properties"].values())


def test_context_firewall_rejects_privileged_world_geometry() -> None:
    with pytest.raises(ValueError):
        assert_sensory_only_context(
            {
                "vision": {"model": "example"},
                "target": {"x": 1, "y": 2},
            }
        )

    with pytest.raises(ValueError):
        assert_sensory_only_context(
            {
                "olfaction": {
                    "food": {
                        "left": 0.1,
                        "right": 0.2,
                        "source": {"x": 3, "y": 4},
                    }
                }
            }
        )


def test_maze_adapter_strips_world_truth_from_neural_context() -> None:
    environment = NoVisualMaze(seed=109)
    adapter = MazeChaseAdapter(environment=environment)

    observation = adapter.observe()
    context = observation.context
    keys = _all_keys(context)

    assert observation.frame is None
    assert context["environment_model"] == "neurofly-maze-chase-v0.1"
    assert context["vision"]["frame_is_egocentric"] is True
    assert context["vision"]["privileged_geometry_exposed"] is False
    assert context["olfaction"]["model"] == OLFACTION_MODEL

    for forbidden in {
        "grid",
        "fly",
        "enemies",
        "target",
        "agent",
        "x",
        "y",
        "source",
        "distance_cells",
        "bearing_degrees",
        "demo_action",
        "recommended_action",
    }:
        assert forbidden not in keys

    # Public state may still contain world truth for UI/evaluation.
    public_state = adapter.public_snapshot()
    assert "fly" in public_state
    assert "enemies" in public_state
    assert "grid" in public_state


def test_light_adapter_keeps_target_geometry_out_of_neural_context() -> None:
    environment = LightChaseEnvironment(seed=109)
    adapter = LightChaseAdapter(environment=environment)

    observation = adapter.observe()
    keys = _all_keys(observation.context)

    assert len(observation.frame) == 90
    assert len(observation.frame[0]) == 160
    assert observation.context["environment_model"] == "neurofly-light-chase-v0.1"
    assert observation.context["vision"]["target_coordinates_exposed"] is False
    assert observation.context["vision"]["target_bearing_exposed"] is False
    assert observation.context["vision"]["target_distance_exposed"] is False

    for forbidden in {
        "target",
        "agent",
        "x",
        "y",
        "bearing_degrees",
        "distance_cells",
        "recommended_action",
    }:
        assert forbidden not in keys

    public_state = adapter.public_snapshot()
    assert "target" in public_state
    assert "agent" in public_state


def test_same_environment_session_runs_maze_and_light() -> None:
    maze_brain = CaptureBrain(["HOLD"])
    maze = EnvironmentSession(
        maze_brain,
        MazeChaseAdapter(environment=NoVisualMaze(seed=7)),
    )
    maze_state = maze.tick()

    light_brain = CaptureBrain(["HOLD"])
    light = EnvironmentSession(
        light_brain,
        LightChaseAdapter(environment=LightChaseEnvironment(seed=7)),
    )
    light_state = light.tick()

    assert maze_state["environment_model"] == "neurofly-maze-chase-v0.1"
    assert light_state["environment_model"] == "neurofly-light-chase-v0.1"
    assert maze_state["brain"]["backend"] == "capture"
    assert light_state["brain"]["backend"] == "capture"

    assert maze_brain.calls[0]["context"]["environment_model"] == maze_state["environment_model"]
    assert light_brain.calls[0]["context"]["environment_model"] == light_state["environment_model"]
    assert maze_brain.calls[0]["reinforcement"] == "none"
    assert light_brain.calls[0]["reinforcement"] == "none"


def test_generic_session_checkpoint_restores_environment_and_pending_reinforcement(
    tmp_path: Path,
) -> None:
    checkpoint = tmp_path / "brain.npz"

    environment = LightChaseEnvironment(seed=31)
    environment.agent = {"x": 3, "y": 5, "dir": "RIGHT"}
    environment.target = {"x": 4, "y": 5}

    first_brain = CaptureBrain(["FORWARD"])
    first = EnvironmentSession(
        first_brain,
        LightChaseAdapter(environment=environment),
        checkpoint=checkpoint,
        checkpoint_every=9999.0,
    )
    state = first.tick()
    assert state["last_event"] == "light_reached"
    assert first.pending_reinforcement == "reward"
    first.save()

    restored_brain = CaptureBrain(["HOLD"])
    restored = EnvironmentSession(
        restored_brain,
        LightChaseAdapter(environment=LightChaseEnvironment(seed=999)),
        checkpoint=checkpoint,
        checkpoint_every=9999.0,
    )

    assert restored.pending_reinforcement == "reward"
    assert restored.adapter.persistence_snapshot() == first.adapter.persistence_snapshot()

    restored.tick()
    assert restored_brain.calls[0]["reinforcement"] == "reward"


def test_factory_exposes_supported_environment_names_and_fails_closed() -> None:
    assert make_environment_adapter("maze").model == "neurofly-maze-chase-v0.1"
    assert make_environment_adapter("maze-chase").model == "neurofly-maze-chase-v0.1"
    assert make_environment_adapter("light").model == "neurofly-light-chase-v0.1"
    assert make_environment_adapter("light_chase").model == "neurofly-light-chase-v0.1"

    with pytest.raises(ValueError):
        make_environment_adapter("teleport-arena")


def test_generic_cli_exposes_environment_choice_without_world_truth_options() -> None:
    args = build_parser().parse_args(
        [
            "env-run",
            "--environment",
            "light",
            "--brain",
            "demo",
            "--steps",
            "2",
            "--interval",
            "0",
        ]
    )

    assert args.command == "env-run"
    assert args.environment == "light"
    assert args.brain == "demo"
    assert args.steps == 2
    assert not hasattr(args, "target_x")
    assert not hasattr(args, "target_y")
    assert not hasattr(args, "goal_direction")
