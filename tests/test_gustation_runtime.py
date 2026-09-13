from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from neurofly.brain_runtime import BrainDecision, gustatory_channel_levels
from neurofly.curriculum import CurriculumMazeEnvironment
from neurofly.goal_training import GoalMazeSession
from neurofly.gustation import (
    EXPECTED_BITTER_GRNS,
    EXPECTED_SUGAR_WATER_GRNS,
    GUSTATION_CALIBRATED_BITTER_CURRENT,
    GUSTATION_CALIBRATED_SUGAR_WATER_CURRENT,
    GUSTATION_CALIBRATION_RECEIPT_SHA256,
    contact_gustation,
)


class RecordingBrain:
    name = "recording"

    def __init__(self, actions: list[str]) -> None:
        self.actions = list(actions)
        self.contexts: list[dict[str, Any]] = []
        self.reinforcements: list[str] = []

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision:
        self.contexts.append({} if context is None else context)
        self.reinforcements.append(reinforcement)
        action = self.actions.pop(0) if self.actions else "HOLD"
        return BrainDecision(action=action, backend=self.name, telemetry={})

    def save(self, path: str | Path) -> None:
        Path(path).write_text("recording-brain\n")


class RecordingEnvironment(CurriculumMazeEnvironment):
    """Exercise session semantics without optional NumPy/Pillow rendering deps."""

    def render_rgb(self, *, width: int = 320, height: int = 180) -> Any:
        return [[[0, 0, 0]]]


def _food_ahead_environment() -> RecordingEnvironment:
    env = RecordingEnvironment(seed=109)
    env.fly = {"x": 1, "y": 1, "dir": "RIGHT"}
    env.enemies = [{"x": env.cols - 2, "y": env.rows - 2}]
    env.grid[1][1] = " "
    env.grid[1][2] = "."
    # Taste must remain independent from the numerical reward magnitude.
    env.food_reward = 999.0
    return env


def test_strict_gustatory_payload_requires_contact_signal_consistency() -> None:
    levels = gustatory_channel_levels(contact_gustation(event="food"))
    assert levels == {
        "available": True,
        "contact": True,
        "bitter": 0.0,
        "sugar_water": 1.0,
    }

    malformed = contact_gustation(event="food")
    malformed["contact"] = False
    with pytest.raises(ValueError, match="contact flag"):
        gustatory_channel_levels(malformed)

    privileged = contact_gustation(event="food")
    privileged["source"] = {"x": 2, "y": 1}
    with pytest.raises(ValueError, match="Privileged field"):
        gustatory_channel_levels(privileged)


def test_runtime_constants_match_frozen_calibration_evidence() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "gustation_current_calibration_v1.json"
    evidence = json.loads(path.read_text())

    assert evidence["selected"]["bitter"]["current"] == GUSTATION_CALIBRATED_BITTER_CURRENT
    assert (
        evidence["selected"]["sugar_water"]["current"]
        == GUSTATION_CALIBRATED_SUGAR_WATER_CURRENT
    )
    assert evidence["selected"]["bitter"]["receipt_sha256"] == GUSTATION_CALIBRATION_RECEIPT_SHA256
    assert evidence["population_counts"] == {
        "bitter": EXPECTED_BITTER_GRNS,
        "sugar_water": EXPECTED_SUGAR_WATER_GRNS,
    }


def test_food_contact_becomes_exactly_one_next_decision_taste_pulse() -> None:
    env = _food_ahead_environment()
    brain = RecordingBrain(["FORWARD", "HOLD", "HOLD"])
    session = GoalMazeSession(
        brain,
        environment=env,
        world_tick_seconds=3600.0,
    )

    session.tick()
    session.tick()
    session.tick()

    first, second, third = brain.contexts
    assert first["gustation"]["contact"] is False
    assert first["gustation"]["channels"] == {"bitter": 0.0, "sugar_water": 0.0}

    assert second["gustation"]["contact"] is True
    assert second["gustation"]["channels"] == {"bitter": 0.0, "sugar_water": 1.0}

    assert third["gustation"]["contact"] is False
    assert third["gustation"]["channels"] == {"bitter": 0.0, "sugar_water": 0.0}

    # User decision: airflow stays active while taste pulses are delivered.
    assert second["antennal_mechanosensation"]["available"] is True
    assert second["antennal_mechanosensation"]["model"].startswith("neurofly-")

    # The food reward can be extreme without changing the sensory taste amplitude.
    assert brain.reinforcements[1] == "reward"
    assert second["gustation"]["channels"]["sugar_water"] == 1.0


def test_last_pellet_still_queues_taste_when_public_event_becomes_maze_cleared() -> None:
    env = _food_ahead_environment()
    for y, row in enumerate(env.grid):
        for x, cell in enumerate(row):
            if cell in {".", "o"}:
                env.grid[y][x] = " "
    env.grid[1][2] = "."

    brain = RecordingBrain(["FORWARD", "HOLD"])
    session = GoalMazeSession(brain, environment=env, world_tick_seconds=3600.0)

    first_state = session.tick()
    assert first_state["step_event"] == "maze_cleared"
    assert session.pending_gustatory_event == "food"

    session.tick()
    assert brain.contexts[1]["gustation"]["contact"] is True
    assert brain.contexts[1]["gustation"]["channels"]["sugar_water"] == 1.0


def test_pending_taste_survives_checkpoint_and_is_consumed_once(tmp_path: Path) -> None:
    checkpoint = tmp_path / "brain.npz"
    env = _food_ahead_environment()
    first_brain = RecordingBrain(["FORWARD"])
    session = GoalMazeSession(
        first_brain,
        environment=env,
        checkpoint=checkpoint,
        checkpoint_every=999999.0,
        world_tick_seconds=3600.0,
    )
    session.tick()
    assert session.pending_gustatory_event == "food"
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

    restored.tick()
    restored.tick()

    assert restored_brain.contexts[0]["gustation"]["contact"] is True
    assert restored_brain.contexts[0]["gustation"]["channels"]["sugar_water"] == 1.0
    assert restored_brain.contexts[1]["gustation"]["contact"] is False
