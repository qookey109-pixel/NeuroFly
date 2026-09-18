from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


THERMOSENSATION_MODEL = "neurofly-thermal-change-proxy-v0.1"
THERMOSENSATION_ENCODING = "virtual-ambient-temperature-change-only-proxy"
THERMOSENSATION_STATE_SCHEMA = "neurofly-virtual-thermal-sensor-state-v0.1"
DEFAULT_STEP_SCALE_C = 1.0


def _finite(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def thermal_change_sensation(
    *,
    temperature_delta_c: float,
    step_scale_c: float = DEFAULT_STEP_SCALE_C,
) -> dict[str, Any]:
    """Encode a private ambient temperature change as receptor-domain channels.

    The returned payload deliberately contains no absolute temperature, target
    temperature, source coordinate, game semantic, reward signal or action
    recommendation.

    Positive engineering delta drives only the warming channel. Negative
    engineering delta drives only the cooling channel. thermal_change contains
    unsigned change magnitude.

    The mapping is inspired by opposing warm/cool thermoreceptor populations in
    adult Drosophila but is not a calibrated electrophysiology model.
    """

    delta = _finite(temperature_delta_c, name="temperature_delta_c")
    scale = _finite(step_scale_c, name="step_scale_c")
    if scale <= 0.0:
        raise ValueError("step_scale_c must be > 0")

    warming = _bounded(max(0.0, delta) / scale)
    cooling = _bounded(max(0.0, -delta) / scale)
    magnitude = _bounded(abs(delta) / scale)

    return {
        "model": THERMOSENSATION_MODEL,
        "encoding": THERMOSENSATION_ENCODING,
        "engineering_proxy": True,
        "absolute_temperature_exposed": False,
        "target_temperature_exposed": False,
        "source_location_exposed": False,
        "reward_exposed": False,
        "action_exposed": False,
        "biological_current_calibrated": False,
        "channels": {
            "warming": round(warming, 6),
            "cooling": round(cooling, 6),
            "thermal_change": round(magnitude, 6),
        },
    }


def thermosensory_channel_levels(payload: dict[str, Any]) -> dict[str, float]:
    channels = payload.get("channels")
    if not isinstance(channels, dict):
        raise ValueError("thermosensation payload lacks channels")
    required = {"warming", "cooling", "thermal_change"}
    if set(channels) != required:
        raise ValueError("thermosensation channel set is not exact")
    levels = {name: float(channels[name]) for name in required}
    if any(
        not math.isfinite(value) or value < 0.0 or value > 1.0
        for value in levels.values()
    ):
        raise ValueError("thermosensation channel levels must be finite and bounded")
    if levels["warming"] > 0.0 and levels["cooling"] > 0.0:
        raise ValueError("warming and cooling channels must be mutually exclusive")
    if abs(
        levels["thermal_change"] - max(levels["warming"], levels["cooling"])
    ) > 1e-9:
        raise ValueError("thermal_change must equal directional magnitude")
    return levels


@dataclass
class VirtualThermalSensor:
    """Stateful private adapter for sequential ambient temperature observations."""

    step_scale_c: float = DEFAULT_STEP_SCALE_C
    previous_temperature_c: float | None = None

    def __post_init__(self) -> None:
        self.step_scale_c = _finite(self.step_scale_c, name="step_scale_c")
        if self.step_scale_c <= 0.0:
            raise ValueError("step_scale_c must be > 0")
        if self.previous_temperature_c is not None:
            self.previous_temperature_c = _finite(
                self.previous_temperature_c,
                name="previous_temperature_c",
            )

    def observe(self, *, ambient_temperature_c: float) -> dict[str, Any]:
        current = _finite(ambient_temperature_c, name="ambient_temperature_c")
        if self.previous_temperature_c is None:
            delta = 0.0
        else:
            delta = current - self.previous_temperature_c
        self.previous_temperature_c = current
        return thermal_change_sensation(
            temperature_delta_c=delta,
            step_scale_c=self.step_scale_c,
        )

    def persistence_snapshot(self) -> dict[str, Any]:
        """Return private restart state; this is never a neural payload."""

        return {
            "schema": THERMOSENSATION_STATE_SCHEMA,
            "step_scale_c": self.step_scale_c,
            "_previous_temperature_c": self.previous_temperature_c,
        }

    def restore(self, payload: dict[str, Any]) -> None:
        if payload.get("schema") != THERMOSENSATION_STATE_SCHEMA:
            raise ValueError("unsupported thermal sensor state schema")
        scale = _finite(payload.get("step_scale_c"), name="step_scale_c")
        if scale <= 0.0:
            raise ValueError("step_scale_c must be > 0")
        previous = payload.get("_previous_temperature_c")
        if previous is not None:
            previous = _finite(previous, name="_previous_temperature_c")
        self.step_scale_c = scale
        self.previous_temperature_c = previous

    def reset(self) -> None:
        self.previous_temperature_c = None
