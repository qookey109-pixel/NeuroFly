from __future__ import annotations

from typing import Any

from .olfaction import OLFACTION_MODEL, virtual_olfaction
from .vision import VISION_MODEL, fly_vision_state


SENSORY_CONTRACT = "neurofly-sensory-contract-v0.1"
SENSORY_POLICY = "egocentric-no-privileged-world-state"

# These fields may be useful to human diagnostics, but they must never appear in
# the machine-readable neural input payload. The nervous system should receive
# sensory transduction, not solved geometry or game-state truth.
PRIVILEGED_AGENT_KEYS = frozenset(
    {
        "x",
        "y",
        "source",
        "distance_cells",
        "bearing_degrees",
        "target",
        "target_action",
        "action",
        "demo_action",
        "grid",
        "enemies",
        "route",
        "path",
    }
)


def _bounded_unit(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        number = 0.0
    return max(0.0, min(1.0, number))


def _olfactory_agent_input(olfaction: dict[str, Any]) -> dict[str, Any]:
    """Strip diagnostic geometry from the bilateral odor stimulus."""

    def channel(name: str) -> dict[str, Any]:
        payload = olfaction.get(name) or {}
        return {
            "left": _bounded_unit(payload.get("left", 0.0)),
            "right": _bounded_unit(payload.get("right", 0.0)),
            "intensity": _bounded_unit(payload.get("intensity", 0.0)),
        }

    return {
        "model": OLFACTION_MODEL,
        "encoding": "bilateral-orn-current-proxy",
        "food": channel("food"),
        "danger": channel("danger"),
    }


def _reserved_modality(model: str) -> dict[str, Any]:
    return {
        "model": model,
        "available": False,
        "status": "pending-biological-mapping",
    }


def assert_unprivileged_agent_input(payload: Any) -> None:
    """Raise when neural input accidentally contains world-truth fields."""

    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in PRIVILEGED_AGENT_KEYS:
                raise ValueError(f"Privileged field is forbidden in neural input: {key}")
            assert_unprivileged_agent_input(value)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            assert_unprivileged_agent_input(item)


def build_sensory_contract(
    *,
    grid: list[list[str]],
    fly: dict[str, Any],
    enemies: list[dict[str, int]],
) -> dict[str, Any]:
    """Build a strict boundary between fly-accessible input and diagnostics.

    ``agent_input`` is the only JSON payload eligible to influence neural
    transduction. ``diagnostics`` may contain exact geometry for humans/tests and
    must never be passed into the connectome as sensory evidence.

    Vision pixels themselves travel separately through the retinal RGB adapter;
    the JSON contract only declares that transport and its policy.
    """

    olfaction = virtual_olfaction(grid=grid, fly=fly, enemies=enemies)
    vision = fly_vision_state(grid=grid, fly=fly, enemies=enemies)

    agent_input = {
        "vision": {
            "model": VISION_MODEL,
            "available": True,
            "encoding": "retinal-rgb-proxy",
            "coordinate_frame": "egocentric-retina",
            "world_geometry_exposed": False,
        },
        "olfaction": _olfactory_agent_input(olfaction),
        "antennal_mechanosensation": _reserved_modality(
            "neurofly-antennal-mechanosensation-v0"
        ),
        "proprioception": _reserved_modality("neurofly-proprioception-v0"),
        "contact_mechanosensation": _reserved_modality(
            "neurofly-contact-mechanosensation-v0"
        ),
        "gustation": _reserved_modality("neurofly-gustation-v0"),
        "thermo_hygrosensation": _reserved_modality(
            "neurofly-thermo-hygrosensation-v0"
        ),
        "polarized_light": _reserved_modality("neurofly-polarized-light-v0"),
    }
    assert_unprivileged_agent_input(agent_input)

    return {
        "schema": SENSORY_CONTRACT,
        "policy": SENSORY_POLICY,
        "agent_input": agent_input,
        "diagnostics": {
            "vision": vision,
            "olfaction": olfaction,
        },
    }
