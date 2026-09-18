from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .thermosensation import VirtualThermalSensor


THERMAL_FIELD_MODEL = "neurofly-virtual-thermal-field-v0.1"


def _finite(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True)
class ThermalSource:
    x: float
    y: float
    delta_c: float
    decay_cells: float = 2.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite(self.x, name="x"))
        object.__setattr__(self, "y", _finite(self.y, name="y"))
        object.__setattr__(self, "delta_c", _finite(self.delta_c, name="delta_c"))
        decay = _finite(self.decay_cells, name="decay_cells")
        if decay <= 0.0:
            raise ValueError("decay_cells must be > 0")
        object.__setattr__(self, "decay_cells", decay)


@dataclass
class VirtualThermalField:
    """Private game-world temperature field.

    Source positions and absolute temperatures are environment/control-plane
    state. Only the output of VirtualThermalSensor is eligible for neural input.
    """

    baseline_c: float = 24.0
    sources: list[ThermalSource] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.baseline_c = _finite(self.baseline_c, name="baseline_c")
        self.sources = list(self.sources)

    def temperature_at(self, *, x: float, y: float) -> float:
        px = _finite(x, name="x")
        py = _finite(y, name="y")
        value = self.baseline_c
        for source in self.sources:
            distance = math.hypot(px - source.x, py - source.y)
            value += source.delta_c * math.exp(-distance / source.decay_cells)
        return float(value)

    def observe(
        self,
        sensor: VirtualThermalSensor,
        *,
        x: float,
        y: float,
    ) -> dict[str, Any]:
        local_temperature = self.temperature_at(x=x, y=y)
        return sensor.observe(ambient_temperature_c=local_temperature)

    def private_snapshot(self) -> dict[str, Any]:
        """Return private world configuration; never route this to neural context."""

        return {
            "model": THERMAL_FIELD_MODEL,
            "baseline_c": self.baseline_c,
            "sources": [
                {
                    "x": source.x,
                    "y": source.y,
                    "delta_c": source.delta_c,
                    "decay_cells": source.decay_cells,
                }
                for source in self.sources
            ],
        }

    @classmethod
    def from_private_snapshot(cls, payload: dict[str, Any]) -> "VirtualThermalField":
        if payload.get("model") != THERMAL_FIELD_MODEL:
            raise ValueError("unsupported thermal field model")
        raw_sources = payload.get("sources")
        if not isinstance(raw_sources, list):
            raise ValueError("thermal field sources must be a list")
        sources = []
        for item in raw_sources:
            if not isinstance(item, dict):
                raise ValueError("invalid thermal source")
            sources.append(
                ThermalSource(
                    x=item.get("x"),
                    y=item.get("y"),
                    delta_c=item.get("delta_c"),
                    decay_cells=item.get("decay_cells"),
                )
            )
        return cls(
            baseline_c=payload.get("baseline_c"),
            sources=sources,
        )
