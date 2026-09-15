from __future__ import annotations

import copy
import math
from typing import Any, Mapping

from .olfaction import OLFACTION_MODEL
from .proprioception import proprioceptive_channel_levels
from .sensory_contract import assert_unprivileged_agent_input
from .vision import VISION_MODEL
from .vision_adapter import retinalize_topdown_rgb


NEURAL_CONTEXT_FIREWALL_SCHEMA = "neurofly-neural-context-firewall-v0.1"
NEURAL_CONTEXT_POLICY = "world-truth-stops-at-sensory-transducer"

ALLOWED_NEURAL_CONTEXT_KEYS = frozenset(
    {
        "vision",
        "olfaction",
        "antennal_mechanosensation",
        "proprioception",
        "contact_mechanosensation",
        "gustation",
        "thermo_hygrosensation",
        "polarized_light",
    }
)


def _vision_declaration(diagnostics: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "model": VISION_MODEL,
        "available": bool(diagnostics.get("available", True)),
        "encoding": "retinal-rgb-proxy",
        "coordinate_frame": "egocentric-retina",
        "world_geometry_exposed": False,
        "engineered_proxy": True,
    }


def _bounded_level(value: Any, *, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid sensory intensity: {field}") from exc
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"Sensory intensity must stay within [0,1]: {field}")
    return number


def olfaction_neural_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Project diagnostic virtual olfaction onto bilateral neural-safe channels."""

    if payload.get("model") != OLFACTION_MODEL:
        raise ValueError("Unsupported olfaction model at neural firewall")

    def channel(name: str) -> dict[str, float]:
        source = payload.get(name)
        if not isinstance(source, Mapping):
            source = {}
        return {
            "left": _bounded_level(source.get("left", 0.0), field=f"{name}.left"),
            "right": _bounded_level(source.get("right", 0.0), field=f"{name}.right"),
            "intensity": _bounded_level(
                source.get("intensity", 0.0), field=f"{name}.intensity"
            ),
        }

    cleaned = {
        "model": OLFACTION_MODEL,
        "encoding": "bilateral-orn-current-proxy",
        "food": channel("food"),
        "danger": channel("danger"),
    }
    assert_unprivileged_agent_input({"olfaction": cleaned})
    return cleaned


def sanitize_neural_context(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed unless every field is a recognized sensory modality."""

    unexpected = sorted(str(key) for key in payload if key not in ALLOWED_NEURAL_CONTEXT_KEYS)
    if unexpected:
        raise ValueError(f"Non-sensory fields cannot cross neural context firewall: {unexpected}")

    cleaned = {str(key): copy.deepcopy(value) for key, value in payload.items()}

    proprioception = cleaned.get("proprioception")
    if proprioception is not None:
        if not isinstance(proprioception, Mapping):
            raise ValueError("Proprioception neural payload must be a mapping")
        # Systematic-type polarity/evidence metadata belongs to the control plane,
        # not the neural sensory plane. Only the strict FeCO receptor-domain
        # contract may cross under the proprioception modality key.
        proprioceptive_channel_levels(dict(proprioception))

    assert_unprivileged_agent_input(cleaned)
    return cleaned


def prepare_firewalled_visual_input(
    frame: Any,
    *,
    fly: Mapping[str, Any],
    enemies: list[Mapping[str, Any]],
    sensory_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Consume visual world truth on the transducer side and return safe input.

    Production MaleCNS paths install the visual/Stonkfly dependencies and must
    receive the retinalized frame. Lightweight unit-test backends intentionally
    do not depend on NumPy/Pillow; if those optional packages are absent, the
    firewall still strips world truth but marks vision unavailable and leaves the
    opaque test frame unchanged. A malformed frame with visual deps present still
    fails normally and is never hidden by this compatibility path.
    """

    try:
        retinal_rgb, visual_diagnostics = retinalize_topdown_rgb(
            frame,
            fly=dict(fly),
            enemies=[dict(item) for item in enemies],
        )
    except RuntimeError as exc:
        if "requires Pillow and NumPy" not in str(exc):
            raise
        retinal_rgb = frame
        visual_diagnostics = {
            "model": VISION_MODEL,
            "engineered_proxy": True,
            "available": False,
            "status": "visual-optional-dependencies-unavailable",
            "firewall_identity_frame_fallback": True,
        }

    candidate = dict(sensory_context or {})
    if "vision" in candidate:
        raise ValueError("Caller must not supply a second visual neural payload")
    candidate["vision"] = _vision_declaration(visual_diagnostics)
    neural_context = sanitize_neural_context(candidate)

    return {
        "schema": NEURAL_CONTEXT_FIREWALL_SCHEMA,
        "policy": NEURAL_CONTEXT_POLICY,
        "frame": retinal_rgb,
        "context": neural_context,
        "diagnostics": {"vision": copy.deepcopy(dict(visual_diagnostics))},
    }


def assert_firewalled_bundle(bundle: Mapping[str, Any]) -> None:
    if bundle.get("schema") != NEURAL_CONTEXT_FIREWALL_SCHEMA:
        raise ValueError("Unsupported neural context firewall schema")
    if bundle.get("policy") != NEURAL_CONTEXT_POLICY:
        raise ValueError("Unsupported neural context firewall policy")
    context = bundle.get("context")
    if not isinstance(context, Mapping):
        raise ValueError("Firewalled neural context must be a mapping")
    cleaned = sanitize_neural_context(context)
    if dict(context) != cleaned:
        raise ValueError("Firewalled neural context changed during validation")

    vision = context.get("vision")
    if not isinstance(vision, Mapping):
        raise ValueError("Firewalled context requires a visual transport declaration")
    if vision.get("model") != VISION_MODEL:
        raise ValueError("Unexpected visual model at neural firewall")
    if vision.get("encoding") != "retinal-rgb-proxy":
        raise ValueError("Neural firewall requires retinal RGB encoding")
    if vision.get("coordinate_frame") != "egocentric-retina":
        raise ValueError("Neural firewall requires egocentric retinal coordinates")
    if vision.get("world_geometry_exposed") is not False:
        raise ValueError("Visual world geometry must remain outside neural context")
