from __future__ import annotations

from typing import Any

from .gustation import GUSTATION_MODEL, contact_gustation
from .mechanosensation import (
    MECHANOSENSATION_MODEL,
    virtual_antennal_mechanosensation,
)
from .olfaction import OLFACTION_MODEL, virtual_olfaction
from .tactile import TACTILE_MODEL, contact_mechanosensation
from .vision import VISION_MODEL, fly_vision_state


SENSORY_CONTRACT = "neurofly-sensory-contract-v0.4"
SENSORY_POLICY = "egocentric-no-privileged-world-state"

# These fields may be useful to human diagnostics or internal body simulation,
# but they must never appear in the machine-readable neural input payload. The
# nervous system should receive sensory transduction, not solved geometry,
# motor-command labels, raw world kinematics, reward, or untransduced joint state.
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
        "desired_action",
        "demo_action",
        "grid",
        "enemies",
        "route",
        "path",
        "heading",
        "world_velocity",
        "world_displacement",
        "reward",
        "airflow_world",
        "body_relative",
        "signed_deflection",
        "object_id",
        "collision_normal",
        "wall_coordinates",
        "joint_delta",
        "joint_position",
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


def _mechanosensory_agent_input(mechanosensation: dict[str, Any]) -> dict[str, Any]:
    """Expose only bounded Johnston's-organ-like channels to neural code."""

    if not mechanosensation.get("available"):
        return {
            "model": MECHANOSENSATION_MODEL,
            "available": False,
            "status": str(mechanosensation.get("status") or "unavailable"),
        }

    def antenna(name: str) -> dict[str, float]:
        payload = mechanosensation.get(name) or {}
        return {
            "jo_c": _bounded_unit(payload.get("jo_c", 0.0)),
            "jo_e": _bounded_unit(payload.get("jo_e", 0.0)),
        }

    return {
        "model": MECHANOSENSATION_MODEL,
        "available": True,
        "encoding": "bilateral-jon-c-e-deflection-proxy",
        "left": antenna("left"),
        "right": antenna("right"),
    }


def _tactile_agent_input(tactile: dict[str, Any]) -> dict[str, Any]:
    """Expose only the bounded contact channel, never collision geometry."""

    channels = tactile.get("channels") or {}
    front = _bounded_unit(channels.get("front", 0.0))
    return {
        "model": TACTILE_MODEL,
        "available": bool(tactile.get("available", True)),
        "encoding": "blocked-forward-external-touch-proxy",
        "contact": bool(tactile.get("contact", False)),
        "channels": {"front": front},
        "stimulation_enabled": False,
    }


def _gustatory_agent_input(gustation: dict[str, Any]) -> dict[str, Any]:
    """Expose only contact-gated functional taste channels."""

    channels = gustation.get("channels") or {}
    return {
        "model": GUSTATION_MODEL,
        "available": bool(gustation.get("available", True)),
        "encoding": "contact-only-functional-class-proxy",
        "contact": bool(gustation.get("contact", False)),
        "channels": {
            "bitter": _bounded_unit(channels.get("bitter", 0.0)),
            "sugar_water": _bounded_unit(channels.get("sugar_water", 0.0)),
        },
        "stimulation_enabled": False,
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
    airflow: dict[str, Any] | None = None,
    gustatory_event: str | None = None,
    tactile_contact: bool = False,
) -> dict[str, Any]:
    """Build a strict boundary between fly-accessible input and diagnostics.

    ``agent_input`` is the only JSON payload eligible to influence neural
    transduction. ``diagnostics`` may contain exact geometry for humans/tests and
    must never be passed into the connectome as sensory evidence.

    Vision pixels themselves travel separately through the retinal RGB adapter;
    the JSON contract only declares that transport and its policy. Gustation is
    contact-gated: a distant visible or smellable food does not create a taste
    channel. Contact mechanosensation is also contact-gated and exposes only a
    bounded front-contact channel; it never exposes wall or collision geometry.
    Neither taste nor tactile current is enabled by this contract.
    """

    olfaction = virtual_olfaction(grid=grid, fly=fly, enemies=enemies)
    vision = fly_vision_state(grid=grid, fly=fly, enemies=enemies)
    mechanosensation = virtual_antennal_mechanosensation(fly=fly, airflow=airflow)
    gustation = contact_gustation(event=gustatory_event)
    tactile = contact_mechanosensation(front=1.0 if tactile_contact else 0.0)

    agent_input = {
        "vision": {
            "model": VISION_MODEL,
            "available": True,
            "encoding": "retinal-rgb-proxy",
            "coordinate_frame": "egocentric-retina",
            "world_geometry_exposed": False,
        },
        "olfaction": _olfactory_agent_input(olfaction),
        "antennal_mechanosensation": _mechanosensory_agent_input(mechanosensation),
        "proprioception": _reserved_modality("neurofly-proprioception-v0"),
        "contact_mechanosensation": _tactile_agent_input(tactile),
        "gustation": _gustatory_agent_input(gustation),
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
            "antennal_mechanosensation": mechanosensation,
            "gustation": gustation,
            "contact_mechanosensation": tactile,
        },
    }
