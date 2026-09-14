from __future__ import annotations

from typing import Any

import pytest

import neurofly.neural_context as neural_context
from neurofly.gustation import contact_gustation
from neurofly.neural_context import (
    ALLOWED_NEURAL_CONTEXT_KEYS,
    NEURAL_CONTEXT_FIREWALL_SCHEMA,
    NEURAL_CONTEXT_POLICY,
    assert_firewalled_bundle,
    prepare_firewalled_visual_input,
    sanitize_neural_context,
)
from neurofly.proprioception import feco_motion_proprioception
from neurofly.tactile import contact_mechanosensation
from neurofly.vision import VISION_MODEL


def test_sanitize_accepts_only_transduced_modalities() -> None:
    payload = {
        "gustation": contact_gustation(),
        "contact_mechanosensation": contact_mechanosensation(front=0.0),
        "proprioception": feco_motion_proprioception(joint_delta=0.4),
    }
    cleaned = sanitize_neural_context(payload)
    assert set(cleaned) <= ALLOWED_NEURAL_CONTEXT_KEYS
    assert cleaned == payload
    assert cleaned is not payload


@pytest.mark.parametrize("field", ["fly", "enemies", "demo_action", "route", "reward"])
def test_unknown_or_world_state_top_level_fields_fail_closed(field: str) -> None:
    with pytest.raises(ValueError, match="cannot cross neural context firewall"):
        sanitize_neural_context({field: {"x": 1, "y": 2}})


def test_nested_privileged_geometry_also_fails_closed() -> None:
    with pytest.raises(ValueError, match="Privileged field"):
        sanitize_neural_context(
            {
                "olfaction": {
                    "model": "test",
                    "food": {"left": 0.5, "right": 0.2, "source": {"x": 4, "y": 7}},
                }
            }
        )


def test_visual_world_truth_is_consumed_only_on_transducer_side(monkeypatch: pytest.MonkeyPatch) -> None:
    retinal_frame = object()
    captured: dict[str, Any] = {}

    def fake_retinalize(frame: Any, *, fly: dict[str, Any], enemies: list[dict[str, Any]]):
        captured["frame"] = frame
        captured["fly"] = fly
        captured["enemies"] = enemies
        return retinal_frame, {
            "model": VISION_MODEL,
            "available": True,
            "bearing_degrees": 37.0,
            "distance_cells": 2.5,
            "nearest_enemy": {"bearing_degrees": 37.0, "distance_cells": 2.5},
        }

    monkeypatch.setattr(neural_context, "retinalize_topdown_rgb", fake_retinalize)
    world_frame = object()
    fly = {"x": 3, "y": 4, "dir": "RIGHT"}
    enemies = [{"x": 8, "y": 4}]
    sensory = {
        "gustation": contact_gustation(),
        "proprioception": feco_motion_proprioception(joint_delta=-0.25),
    }

    bundle = prepare_firewalled_visual_input(
        world_frame,
        fly=fly,
        enemies=enemies,
        sensory_context=sensory,
    )
    assert_firewalled_bundle(bundle)

    assert captured == {"frame": world_frame, "fly": fly, "enemies": enemies}
    assert bundle["frame"] is retinal_frame
    assert bundle["schema"] == NEURAL_CONTEXT_FIREWALL_SCHEMA
    assert bundle["policy"] == NEURAL_CONTEXT_POLICY

    safe = bundle["context"]
    assert "fly" not in safe
    assert "enemies" not in safe
    assert safe["vision"] == {
        "model": VISION_MODEL,
        "available": True,
        "encoding": "retinal-rgb-proxy",
        "coordinate_frame": "egocentric-retina",
        "world_geometry_exposed": False,
        "engineered_proxy": True,
    }
    assert "bearing_degrees" not in safe["vision"]
    assert "distance_cells" not in safe["vision"]

    diagnostics = bundle["diagnostics"]["vision"]
    assert diagnostics["nearest_enemy"]["bearing_degrees"] == 37.0
    assert diagnostics["distance_cells"] == 2.5


def test_duplicate_visual_payload_is_rejected_before_crossing_firewall(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        neural_context,
        "retinalize_topdown_rgb",
        lambda frame, *, fly, enemies: (frame, {"available": True}),
    )
    with pytest.raises(ValueError, match="second visual"):
        prepare_firewalled_visual_input(
            object(),
            fly={"x": 1, "y": 1, "dir": "UP"},
            enemies=[],
            sensory_context={"vision": {"model": "caller-supplied"}},
        )


def test_firewall_validator_rejects_world_geometry_exposure() -> None:
    bundle = {
        "schema": NEURAL_CONTEXT_FIREWALL_SCHEMA,
        "policy": NEURAL_CONTEXT_POLICY,
        "frame": object(),
        "context": {
            "vision": {
                "model": VISION_MODEL,
                "available": True,
                "encoding": "retinal-rgb-proxy",
                "coordinate_frame": "egocentric-retina",
                "world_geometry_exposed": True,
                "engineered_proxy": True,
            }
        },
        "diagnostics": {},
    }
    with pytest.raises(ValueError, match="world geometry"):
        assert_firewalled_bundle(bundle)
