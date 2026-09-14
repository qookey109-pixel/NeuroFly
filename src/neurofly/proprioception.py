from __future__ import annotations

from typing import Any


PROPRIOCEPTION_MODEL = "neurofly-feco-motion-proxy-v0.1"
PROPRIOCEPTION_ENCODING = "virtual-joint-motion-only-proxy"


def _bounded_unit(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        number = 0.0
    return max(0.0, min(1.0, number))


def feco_motion_proprioception(
    *,
    joint_delta: float = 0.0,
    vibration: float = 0.0,
) -> dict[str, Any]:
    """Transduce receptor-accessible virtual joint mechanics into FeCO-like channels.

    ``joint_delta`` is an internal virtual joint displacement for one body step,
    not world-space movement. Positive and negative signs are retained only as
    mutually exclusive directional hook-like channels. Magnitude drives the
    club-like motion channel. ``vibration`` is an internal mechanical vibration
    magnitude, also bounded to [0, 1].

    This contract deliberately exposes no joint-position/claw channel because
    the current conservative MaleCNS claw mapping remains unresolved. It also
    does not expose world position, heading, game velocity, routes, reward, or
    desired action. Neural stimulation remains disabled.
    """

    try:
        delta = float(joint_delta)
    except (TypeError, ValueError, OverflowError):
        delta = 0.0

    extension = _bounded_unit(max(0.0, delta))
    flexion = _bounded_unit(max(0.0, -delta))
    motion = _bounded_unit(abs(delta))
    vibration_level = _bounded_unit(vibration)

    return {
        "model": PROPRIOCEPTION_MODEL,
        "available": True,
        "encoding": PROPRIOCEPTION_ENCODING,
        "channels": {
            "hook_extension": extension,
            "hook_flexion": flexion,
            "club_motion": motion,
            "club_vibration": vibration_level,
        },
        "claw_position_available": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "engineering_proxy": True,
    }


def proprioceptive_channel_levels(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the strict pre-runtime proprioceptive receptor contract."""

    if payload.get("model") != PROPRIOCEPTION_MODEL:
        raise ValueError("Unexpected proprioception model")
    if payload.get("available") is not True:
        raise ValueError("Proprioception receptor contract must be available")
    if payload.get("encoding") != PROPRIOCEPTION_ENCODING:
        raise ValueError("Unexpected proprioception encoding")
    if payload.get("claw_position_available") is not False:
        raise ValueError("Claw position must remain unavailable")
    if payload.get("stimulation_enabled") is not False:
        raise ValueError("Proprioceptive stimulation must remain disabled")
    if payload.get("runtime_transduction_enabled") is not False:
        raise ValueError("Proprioceptive runtime transduction must remain disabled")

    channels = payload.get("channels")
    expected = {
        "hook_extension",
        "hook_flexion",
        "club_motion",
        "club_vibration",
    }
    if not isinstance(channels, dict) or set(channels) != expected:
        raise ValueError("Unexpected proprioceptive channel set")

    cleaned: dict[str, float] = {}
    for name in sorted(expected):
        try:
            value = float(channels[name])
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"Proprioceptive channel {name} must be numeric") from exc
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Proprioceptive channel {name} must stay within [0,1]")
        cleaned[name] = value

    if cleaned["hook_extension"] > 0.0 and cleaned["hook_flexion"] > 0.0:
        raise ValueError("Hook extension and flexion channels must be mutually exclusive")
    if cleaned["club_motion"] + 1e-12 < max(
        cleaned["hook_extension"], cleaned["hook_flexion"]
    ):
        raise ValueError("Club motion must cover the directional joint-motion magnitude")

    return {
        "available": True,
        **cleaned,
        "claw_position_available": False,
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
    }
