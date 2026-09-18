from __future__ import annotations

import copy
import json
import math
from pathlib import Path

import pytest

from neurofly.thermosensation import (
    THERMOSENSATION_ENCODING,
    THERMOSENSATION_MODEL,
    THERMOSENSATION_STATE_SCHEMA,
    VirtualThermalSensor,
    thermal_change_sensation,
    thermosensory_channel_levels,
)


CONTRACT = Path("data/thermosensation_engineering_proxy_v01.json")


def _levels(delta: float) -> dict[str, float]:
    return thermosensory_channel_levels(
        thermal_change_sensation(temperature_delta_c=delta, step_scale_c=1.0)
    )


def test_contract_matches_runtime_identity() -> None:
    contract = json.loads(CONTRACT.read_text())

    assert contract["schema"] == "neurofly-thermosensation-engineering-proxy-v0.1"
    assert contract["status"] == "ENGINEERING_PROXY_ONLY"
    assert contract["model"] == THERMOSENSATION_MODEL
    assert contract["encoding"] == THERMOSENSATION_ENCODING
    assert contract["required_channels"] == ["warming", "cooling", "thermal_change"]
    assert all(contract["required_properties"].values())
    assert all(value is False for value in contract["biological_claims"].values())
    assert all(value is False for value in contract["runtime_authority"].values())


def test_directional_proxy_is_symmetric_bounded_and_mutually_exclusive() -> None:
    for magnitude in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 2.0):
        warm = _levels(magnitude)
        cool = _levels(-magnitude)

        assert 0.0 <= warm["warming"] <= 1.0
        assert 0.0 <= warm["cooling"] <= 1.0
        assert 0.0 <= cool["warming"] <= 1.0
        assert 0.0 <= cool["cooling"] <= 1.0

        assert warm["warming"] == cool["cooling"]
        assert warm["cooling"] == 0.0
        assert cool["warming"] == 0.0
        assert warm["thermal_change"] == warm["warming"]
        assert cool["thermal_change"] == cool["cooling"]


def test_proxy_is_monotonic_and_saturates_at_scale() -> None:
    magnitudes = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0, 2.0)
    warm_curve = [_levels(value)["warming"] for value in magnitudes]
    cool_curve = [_levels(-value)["cooling"] for value in magnitudes]

    assert all(a <= b for a, b in zip(warm_curve, warm_curve[1:]))
    assert all(a <= b for a, b in zip(cool_curve, cool_curve[1:]))
    assert warm_curve[-2:] == [1.0, 1.0]
    assert cool_curve[-2:] == [1.0, 1.0]


def test_neural_payload_does_not_expose_private_temperature_or_game_semantics() -> None:
    payload = thermal_change_sensation(
        temperature_delta_c=0.4,
        step_scale_c=1.0,
    )
    encoded = json.dumps(payload, sort_keys=True).lower()

    assert payload["engineering_proxy"] is True
    assert payload["absolute_temperature_exposed"] is False
    assert payload["target_temperature_exposed"] is False
    assert payload["source_location_exposed"] is False
    assert payload["reward_exposed"] is False
    assert payload["action_exposed"] is False
    assert payload["biological_current_calibrated"] is False

    forbidden = (
        "ambient_temperature_c",
        "previous_temperature_c",
        "_previous_temperature_c",
        "target_temperature_c",
        "heat_source",
        "cold_source",
        "goal_direction",
        "recommended_action",
    )
    assert all(token not in encoded for token in forbidden)


def test_stateful_sensor_first_observation_is_neutral_then_encodes_change() -> None:
    sensor = VirtualThermalSensor(step_scale_c=1.0)

    first = thermosensory_channel_levels(sensor.observe(ambient_temperature_c=24.0))
    warming = thermosensory_channel_levels(sensor.observe(ambient_temperature_c=24.4))
    cooling = thermosensory_channel_levels(sensor.observe(ambient_temperature_c=24.1))

    assert first == {"warming": 0.0, "cooling": 0.0, "thermal_change": 0.0}
    assert warming["warming"] == pytest.approx(0.4)
    assert warming["cooling"] == 0.0
    assert cooling["warming"] == 0.0
    assert cooling["cooling"] == pytest.approx(0.3)


def test_private_state_round_trip_preserves_next_receptor_sample() -> None:
    sensor = VirtualThermalSensor(step_scale_c=0.5)
    sensor.observe(ambient_temperature_c=22.0)
    sensor.observe(ambient_temperature_c=22.2)

    private = sensor.persistence_snapshot()
    assert private["schema"] == THERMOSENSATION_STATE_SCHEMA
    assert private["_previous_temperature_c"] == pytest.approx(22.2)

    expected = sensor.observe(ambient_temperature_c=22.4)

    restored = VirtualThermalSensor()
    restored.restore(copy.deepcopy(private))
    observed = restored.observe(ambient_temperature_c=22.4)

    assert observed == expected


def test_invalid_values_fail_closed() -> None:
    for bad in (math.nan, math.inf, -math.inf):
        with pytest.raises(ValueError):
            thermal_change_sensation(temperature_delta_c=bad)
        with pytest.raises(ValueError):
            VirtualThermalSensor().observe(ambient_temperature_c=bad)

    with pytest.raises(ValueError):
        thermal_change_sensation(temperature_delta_c=0.1, step_scale_c=0.0)
    with pytest.raises(ValueError):
        VirtualThermalSensor(step_scale_c=-1.0)

    with pytest.raises(ValueError):
        VirtualThermalSensor().restore(
            {
                "schema": "wrong",
                "step_scale_c": 1.0,
                "_previous_temperature_c": 20.0,
            }
        )
