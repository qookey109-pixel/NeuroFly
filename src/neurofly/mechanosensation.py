from __future__ import annotations

import math
from typing import Any


MECHANOSENSATION_MODEL = "neurofly-antennal-mechanosensation-v0.1"

# MaleCNS v1.0 uses JO-* cell-type names for Johnston's-organ neurons. Published
# Drosophila physiology broadly associates JO-C / JO-E with tonic antennal
# deflection used for wind/gravity sensing, while JO-A / JO-B are more strongly
# associated with vibration/sound. The exact subtype-to-physics mapping below is
# intentionally not claimed as validated physiology.
WIND_JON_TYPE_PREFIXES = ("JO-C", "JO-E")
JO_C_TYPE_PREFIX = "JO-C"
JO_E_TYPE_PREFIX = "JO-E"

_DIR_VECTORS = {
    "UP": (0.0, -1.0),
    "RIGHT": (1.0, 0.0),
    "DOWN": (0.0, 1.0),
    "LEFT": (-1.0, 0.0),
}


def _finite(value: Any, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _bounded_signed(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def _bounded_unit(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def virtual_antennal_mechanosensation(
    *,
    fly: dict[str, Any],
    airflow: dict[str, Any] | None,
) -> dict[str, Any]:
    """Translate world airflow into bilateral Johnston's-organ-like channels.

    ``airflow`` is a world-frame velocity vector with components ``x`` and ``y``.
    Its magnitude is treated as a normalized engineering stimulus and is clipped
    to 1.0. The vector is first transformed into the fly's body frame, then into
    a deliberately simple bilateral antennal-deflection proxy.

    Positive signed deflection means posterior displacement and feeds the JO-E
    proxy. Negative deflection means anterior displacement and feeds JO-C. A
    frontal headwind therefore drives both JO-E channels; a lateral wind creates
    opposing left/right C/E activation. This mirrors the experimentally observed
    opponent organization at a coarse level, but it is not a validated model of
    Drosophila antennal mechanics.

    The returned object contains diagnostics as well as transduced channels.
    Neural code must use only the bounded C/E channel values, never the world
    vector or body-frame geometry directly.
    """

    direction = str(fly.get("dir", ""))
    if direction not in _DIR_VECTORS:
        raise ValueError("fly.dir must be one of UP, RIGHT, DOWN, LEFT")

    if airflow is None:
        return {
            "model": MECHANOSENSATION_MODEL,
            "engineered_proxy": True,
            "available": False,
            "status": "no-airflow-field",
            "left": {"jo_c": 0.0, "jo_e": 0.0},
            "right": {"jo_c": 0.0, "jo_e": 0.0},
        }

    vx = _finite(airflow.get("x", 0.0), name="airflow.x")
    vy = _finite(airflow.get("y", 0.0), name="airflow.y")
    raw_speed = math.hypot(vx, vy)
    scale = 1.0 if raw_speed <= 1.0 or raw_speed == 0.0 else 1.0 / raw_speed
    vx *= scale
    vy *= scale
    speed = min(1.0, raw_speed)

    heading_x, heading_y = _DIR_VECTORS[direction]
    right_x, right_y = -heading_y, heading_x
    forward = _bounded_signed(vx * heading_x + vy * heading_y)
    rightward = _bounded_signed(vx * right_x + vy * right_y)

    # Air moving against the heading (negative forward component) pushes the
    # receiver posteriorly in this coarse proxy. Crosswind differentially loads
    # the two antennae, preserving an opponent bilateral cue without exposing a
    # solved wind bearing or target action.
    posterior_common = -forward
    crosswind_gain = 0.70
    left_deflection = _bounded_signed(posterior_common - crosswind_gain * rightward)
    right_deflection = _bounded_signed(posterior_common + crosswind_gain * rightward)

    def channels(deflection: float) -> dict[str, float]:
        return {
            "jo_c": round(_bounded_unit(-deflection), 6),
            "jo_e": round(_bounded_unit(deflection), 6),
        }

    return {
        "model": MECHANOSENSATION_MODEL,
        "engineered_proxy": True,
        "available": True,
        "encoding": "bilateral-jon-c-e-deflection-proxy",
        "left": channels(left_deflection),
        "right": channels(right_deflection),
        "diagnostics": {
            "airflow_world": {
                "x": round(vx, 6),
                "y": round(vy, 6),
                "magnitude": round(speed, 6),
            },
            "body_relative": {
                "forward": round(forward, 6),
                "rightward": round(rightward, 6),
            },
            "signed_deflection": {
                "left": round(left_deflection, 6),
                "right": round(right_deflection, 6),
                "positive_direction": "posterior-JO-E-proxy",
                "negative_direction": "anterior-JO-C-proxy",
            },
        },
    }
