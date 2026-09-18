from __future__ import annotations

import json

import pytest

from neurofly.thermal_field import (
    THERMAL_FIELD_MODEL,
    ThermalSource,
    VirtualThermalField,
)
from neurofly.thermosensation import VirtualThermalSensor, thermosensory_channel_levels


def _levels(field: VirtualThermalField, sensor: VirtualThermalSensor, x: float, y: float):
    return thermosensory_channel_levels(field.observe(sensor, x=x, y=y))


def test_moving_toward_heat_source_produces_warming_without_leaking_world_state() -> None:
    field = VirtualThermalField(
        baseline_c=24.0,
        sources=[ThermalSource(x=5.0, y=0.0, delta_c=6.0, decay_cells=2.0)],
    )
    sensor = VirtualThermalSensor(step_scale_c=1.0)

    first = _levels(field, sensor, 0.0, 0.0)
    warming = field.observe(sensor, x=1.0, y=0.0)
    levels = thermosensory_channel_levels(warming)
    encoded = json.dumps(warming, sort_keys=True).lower()

    assert first == {"warming": 0.0, "cooling": 0.0, "thermal_change": 0.0}
    assert levels["warming"] > 0.0
    assert levels["cooling"] == 0.0
    assert warming["source_location_exposed"] is False
    assert all(
        token not in encoded
        for token in (
            "baseline_c",
            "delta_c",
            "decay_cells",
            '"x":',
            '"y":',
            "ambient_temperature_c",
            "previous_temperature_c",
            "_previous_temperature_c",
        )
    )


def test_moving_away_from_heat_source_produces_cooling() -> None:
    field = VirtualThermalField(
        baseline_c=24.0,
        sources=[ThermalSource(x=0.0, y=0.0, delta_c=5.0, decay_cells=2.0)],
    )
    sensor = VirtualThermalSensor(step_scale_c=1.0)

    _levels(field, sensor, 0.5, 0.0)
    cooling = _levels(field, sensor, 1.5, 0.0)

    assert cooling["warming"] == 0.0
    assert cooling["cooling"] > 0.0


def test_moving_toward_cold_source_produces_cooling() -> None:
    field = VirtualThermalField(
        baseline_c=24.0,
        sources=[ThermalSource(x=5.0, y=0.0, delta_c=-6.0, decay_cells=2.0)],
    )
    sensor = VirtualThermalSensor(step_scale_c=1.0)

    _levels(field, sensor, 0.0, 0.0)
    cooling = _levels(field, sensor, 1.0, 0.0)

    assert cooling["warming"] == 0.0
    assert cooling["cooling"] > 0.0


def test_remaining_stationary_after_initial_sample_is_neutral() -> None:
    field = VirtualThermalField(
        baseline_c=24.0,
        sources=[ThermalSource(x=3.0, y=3.0, delta_c=4.0, decay_cells=2.0)],
    )
    sensor = VirtualThermalSensor(step_scale_c=0.5)

    _levels(field, sensor, 1.0, 1.0)
    stationary = _levels(field, sensor, 1.0, 1.0)

    assert stationary == {"warming": 0.0, "cooling": 0.0, "thermal_change": 0.0}


def test_field_is_deterministic_and_private_snapshot_round_trips() -> None:
    original = VirtualThermalField(
        baseline_c=23.5,
        sources=[
            ThermalSource(x=2.0, y=1.0, delta_c=4.0, decay_cells=1.5),
            ThermalSource(x=7.0, y=4.0, delta_c=-3.0, decay_cells=3.0),
        ],
    )
    private = original.private_snapshot()

    assert private["model"] == THERMAL_FIELD_MODEL
    restored = VirtualThermalField.from_private_snapshot(private)

    for x, y in ((0.0, 0.0), (2.0, 1.0), (5.0, 2.0), (7.0, 4.0)):
        assert restored.temperature_at(x=x, y=y) == pytest.approx(
            original.temperature_at(x=x, y=y)
        )


def test_field_rejects_invalid_source_parameters() -> None:
    with pytest.raises(ValueError):
        ThermalSource(x=0.0, y=0.0, delta_c=1.0, decay_cells=0.0)

    with pytest.raises(ValueError):
        VirtualThermalField.from_private_snapshot(
            {
                "model": "wrong",
                "baseline_c": 24.0,
                "sources": [],
            }
        )
