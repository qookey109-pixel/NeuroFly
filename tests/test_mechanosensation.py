import pytest

from neurofly.mechanosensation import (
    MECHANOSENSATION_MODEL,
    virtual_antennal_mechanosensation,
)


def test_headwind_drives_bilateral_jo_e_proxy() -> None:
    state = virtual_antennal_mechanosensation(
        fly={"x": 3, "y": 4, "dir": "RIGHT"},
        airflow={"x": -1.0, "y": 0.0},
    )

    assert state["model"] == MECHANOSENSATION_MODEL
    assert state["available"] is True
    assert state["left"]["jo_e"] == 1.0
    assert state["right"]["jo_e"] == 1.0
    assert state["left"]["jo_c"] == 0.0
    assert state["right"]["jo_c"] == 0.0


def test_tailwind_drives_bilateral_jo_c_proxy() -> None:
    state = virtual_antennal_mechanosensation(
        fly={"x": 3, "y": 4, "dir": "RIGHT"},
        airflow={"x": 1.0, "y": 0.0},
    )

    assert state["left"]["jo_c"] == 1.0
    assert state["right"]["jo_c"] == 1.0
    assert state["left"]["jo_e"] == 0.0
    assert state["right"]["jo_e"] == 0.0


def test_crosswind_creates_opponent_bilateral_channels() -> None:
    state = virtual_antennal_mechanosensation(
        fly={"x": 3, "y": 4, "dir": "RIGHT"},
        airflow={"x": 0.0, "y": 1.0},
    )

    assert state["left"]["jo_c"] > 0.0
    assert state["left"]["jo_e"] == 0.0
    assert state["right"]["jo_e"] > 0.0
    assert state["right"]["jo_c"] == 0.0


def test_mechanosensation_is_egocentric() -> None:
    world_airflow = {"x": -1.0, "y": 0.0}
    facing_right = virtual_antennal_mechanosensation(
        fly={"x": 1, "y": 1, "dir": "RIGHT"},
        airflow=world_airflow,
    )
    facing_up = virtual_antennal_mechanosensation(
        fly={"x": 1, "y": 1, "dir": "UP"},
        airflow=world_airflow,
    )

    assert facing_right["left"] != facing_up["left"]
    assert facing_right["right"] != facing_up["right"]


def test_no_airflow_field_is_explicitly_unavailable() -> None:
    state = virtual_antennal_mechanosensation(
        fly={"x": 1, "y": 1, "dir": "UP"},
        airflow=None,
    )

    assert state["available"] is False
    assert state["status"] == "no-airflow-field"
    assert state["left"] == {"jo_c": 0.0, "jo_e": 0.0}
    assert state["right"] == {"jo_c": 0.0, "jo_e": 0.0}


def test_nonfinite_airflow_is_rejected() -> None:
    with pytest.raises(ValueError, match="airflow.x must be finite"):
        virtual_antennal_mechanosensation(
            fly={"x": 1, "y": 1, "dir": "UP"},
            airflow={"x": float("nan"), "y": 0.0},
        )
