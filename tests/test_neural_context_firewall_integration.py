from __future__ import annotations

from pathlib import Path
from typing import Any

import neurofly.goal_training as goal_training
from neurofly.brain_runtime import BrainDecision
from neurofly.curriculum import CurriculumMazeEnvironment
from neurofly.goal_training import GoalMazeEnvironment, GoalMazeSession
from neurofly.neural_context import (
    NEURAL_CONTEXT_FIREWALL_SCHEMA,
    NEURAL_CONTEXT_POLICY,
    olfaction_neural_payload,
)
from neurofly.olfaction import OLFACTION_MODEL
from neurofly.vision import VISION_MODEL


class RecordingBrain:
    name = "recording"

    def __init__(self) -> None:
        self.frames: list[Any] = []
        self.contexts: list[dict[str, Any]] = []

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision:
        self.frames.append(frame)
        self.contexts.append({} if context is None else context)
        return BrainDecision(action="HOLD", backend=self.name, telemetry={})

    def save(self, path: str | Path) -> None:
        Path(path).write_text("recording\n")


class MalecnsLikeRecordingBrain(RecordingBrain):
    name = "malecns"

    def decide(
        self,
        frame: Any,
        reinforcement: str = "none",
        *,
        context: dict[str, Any] | None = None,
    ) -> BrainDecision:
        self.frames.append(frame)
        self.contexts.append({} if context is None else context)
        return BrainDecision(
            action="HOLD",
            backend=self.name,
            telemetry={
                "vision": {
                    "available": False,
                    "change": 0.125,
                    "left_change": 0.1,
                    "right_change": 0.15,
                }
            },
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text("malecns-like\n")


class DemoRecordingBrain(RecordingBrain):
    name = "demo"


class CurriculumRecordingEnvironment(CurriculumMazeEnvironment):
    def render_rgb(self, *, width: int = 320, height: int = 180) -> Any:
        return object()


class BasicRecordingEnvironment(GoalMazeEnvironment):
    def render_rgb(self, *, width: int = 320, height: int = 180) -> Any:
        return object()


def _install_fake_visual_firewall(monkeypatch, retinal_frame: Any, captured: dict[str, Any]) -> None:
    def fake_prepare(frame, *, fly, enemies, sensory_context=None):
        captured["raw_frame"] = frame
        captured["fly"] = dict(fly)
        captured["enemies"] = [dict(item) for item in enemies]
        captured["sensory_context"] = dict(sensory_context or {})
        safe = dict(sensory_context or {})
        safe["vision"] = {
            "model": VISION_MODEL,
            "available": True,
            "encoding": "retinal-rgb-proxy",
            "coordinate_frame": "egocentric-retina",
            "world_geometry_exposed": False,
            "engineered_proxy": True,
        }
        return {
            "schema": NEURAL_CONTEXT_FIREWALL_SCHEMA,
            "policy": NEURAL_CONTEXT_POLICY,
            "frame": retinal_frame,
            "context": safe,
            "diagnostics": {
                "vision": {
                    "model": VISION_MODEL,
                    "available": True,
                    "nearest_enemy": {
                        "bearing_degrees": 22.0,
                        "distance_cells": 3.0,
                    },
                }
            },
        }

    monkeypatch.setattr(goal_training, "prepare_firewalled_visual_input", fake_prepare)


def test_diagnostic_olfaction_is_projected_to_bilateral_neural_channels() -> None:
    raw = {
        "model": OLFACTION_MODEL,
        "food": {
            "left": 0.7,
            "right": 0.2,
            "intensity": 0.7,
            "distance_cells": 2.0,
            "source": {"x": 7, "y": 4},
        },
        "danger": {
            "left": 0.1,
            "right": 0.4,
            "intensity": 0.4,
            "distance_cells": 5.0,
            "source": {"x": 11, "y": 9},
        },
    }
    cleaned = olfaction_neural_payload(raw)
    assert cleaned == {
        "model": OLFACTION_MODEL,
        "encoding": "bilateral-orn-current-proxy",
        "food": {"left": 0.7, "right": 0.2, "intensity": 0.7},
        "danger": {"left": 0.1, "right": 0.4, "intensity": 0.4},
    }


def test_normal_neural_session_receives_retina_and_sensory_only_context(monkeypatch) -> None:
    retinal_frame = object()
    captured: dict[str, Any] = {}
    _install_fake_visual_firewall(monkeypatch, retinal_frame, captured)

    env = CurriculumRecordingEnvironment(seed=109)
    brain = RecordingBrain()
    session = GoalMazeSession(brain, environment=env, world_tick_seconds=3600.0)
    session.tick()

    assert brain.frames == [retinal_frame]
    context = brain.contexts[0]
    assert "fly" not in context
    assert "enemies" not in context
    assert "demo_action" not in context
    assert "raw_brain_action" not in context
    assert "applied_action" not in context
    assert set(context) == {
        "vision",
        "olfaction",
        "antennal_mechanosensation",
        "gustation",
        "contact_mechanosensation",
        "proprioception",
    }

    assert "source" not in context["olfaction"]["food"]
    assert "distance_cells" not in context["olfaction"]["food"]
    assert "source" not in context["olfaction"]["danger"]
    assert "distance_cells" not in context["olfaction"]["danger"]
    assert captured["fly"] == env.fly
    assert captured["enemies"] == env.enemies


def test_demo_baseline_remains_explicitly_privileged_and_unretinalized(monkeypatch) -> None:
    def must_not_firewall(*args, **kwargs):
        raise AssertionError("Demo baseline should bypass neural firewall")

    monkeypatch.setattr(goal_training, "prepare_firewalled_visual_input", must_not_firewall)
    env = BasicRecordingEnvironment(seed=109)
    brain = DemoRecordingBrain()
    session = GoalMazeSession(brain, environment=env, world_tick_seconds=3600.0)
    session.tick()

    context = brain.contexts[0]
    assert "fly" in context
    assert "enemies" in context


def test_visual_geometry_returns_only_as_human_telemetry(monkeypatch) -> None:
    retinal_frame = object()
    captured: dict[str, Any] = {}
    _install_fake_visual_firewall(monkeypatch, retinal_frame, captured)

    env = CurriculumRecordingEnvironment(seed=109)
    brain = MalecnsLikeRecordingBrain()
    session = GoalMazeSession(brain, environment=env, world_tick_seconds=3600.0)
    session.tick()

    context = brain.contexts[0]
    assert "nearest_enemy" not in context["vision"]
    telemetry = session.last_decision.telemetry
    assert telemetry["vision"]["nearest_enemy"] == {
        "bearing_degrees": 22.0,
        "distance_cells": 3.0,
    }
    assert telemetry["vision"]["change"] == 0.125
    assert telemetry["visual_change"] == 0.125
    assert telemetry["visual_left_change"] == 0.1
    assert telemetry["visual_right_change"] == 0.15
