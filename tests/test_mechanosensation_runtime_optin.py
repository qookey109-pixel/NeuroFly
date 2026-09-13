import pytest

from neurofly.brain_runtime import (
    MaleCNSBrain,
    mechanosensory_channel_levels,
    validated_mechanosensation_current,
)
from neurofly.mechanosensation import (
    MECHANOSENSATION_CALIBRATED_CURRENT,
    MECHANOSENSATION_MODEL,
)


def _strict_payload() -> dict[str, object]:
    return {
        "model": MECHANOSENSATION_MODEL,
        "available": True,
        "encoding": "bilateral-jon-c-e-deflection-proxy",
        "left": {"jo_c": 0.7, "jo_e": 0.0},
        "right": {"jo_c": 0.0, "jo_e": 0.7},
    }


def test_runtime_current_is_disabled_by_zero_or_exact_calibrated_value() -> None:
    assert validated_mechanosensation_current(0) == 0.0
    assert (
        validated_mechanosensation_current(MECHANOSENSATION_CALIBRATED_CURRENT)
        == MECHANOSENSATION_CALIBRATED_CURRENT
    )

    for invalid in (-1, float("nan"), 5.6, 8.0, 12.0, 16.0):
        with pytest.raises(ValueError):
            validated_mechanosensation_current(invalid)


def test_strict_runtime_levels_accept_only_bounded_jo_channels() -> None:
    levels = mechanosensory_channel_levels(_strict_payload())

    assert levels == {
        "available": True,
        "jo_c_left": 0.7,
        "jo_c_right": 0.0,
        "jo_e_left": 0.0,
        "jo_e_right": 0.7,
    }


def test_runtime_levels_reject_privileged_airflow_diagnostics() -> None:
    payload = _strict_payload()
    payload["airflow_world"] = {"x": 0.0, "y": 1.0}

    with pytest.raises(ValueError, match="Privileged field"):
        mechanosensory_channel_levels(payload)


def test_runtime_levels_reject_wrong_model_and_out_of_bounds_channels() -> None:
    payload = _strict_payload()
    payload["model"] = "unknown-model"
    with pytest.raises(ValueError, match="Unsupported NeuroFly mechanosensation model"):
        mechanosensory_channel_levels(payload)

    payload = _strict_payload()
    payload["left"] = {"jo_c": 1.1, "jo_e": 0.0}
    with pytest.raises(ValueError, match=r"within \[0, 1\]"):
        mechanosensory_channel_levels(payload)


def test_unavailable_modality_is_zero_input() -> None:
    levels = mechanosensory_channel_levels(
        {
            "model": MECHANOSENSATION_MODEL,
            "available": False,
            "status": "no-airflow-field",
        }
    )

    assert levels["available"] is False
    assert levels["status"] == "no-airflow-field"
    assert levels["jo_c_left"] == 0.0
    assert levels["jo_e_right"] == 0.0


def test_disabled_runtime_never_builds_pulses() -> None:
    brain = object.__new__(MaleCNSBrain)
    brain.mechanosensation_current = 0.0
    brain.jo_c_left = [101]
    brain.jo_c_right = [102]
    brain.jo_e_left = [103]
    brain.jo_e_right = [104]

    pulses, levels = brain._mechanosensory_stimulation(
        {"antennal_mechanosensation": _strict_payload()}
    )

    assert pulses == []
    assert levels["runtime_enabled"] is False
    assert levels["available"] is True


def test_calibrated_runtime_routes_four_channels_to_candidate_groups() -> None:
    brain = object.__new__(MaleCNSBrain)
    brain.mechanosensation_current = MECHANOSENSATION_CALIBRATED_CURRENT
    brain.jo_c_left = [101]
    brain.jo_c_right = [102]
    brain.jo_e_left = [103]
    brain.jo_e_right = [104]

    pulses, levels = brain._mechanosensory_stimulation(
        {"antennal_mechanosensation": _strict_payload()}
    )

    assert levels["runtime_enabled"] is True
    assert pulses == [
        ([101], 7.0),
        ([104], 7.0),
    ]
