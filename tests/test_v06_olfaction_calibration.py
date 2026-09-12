from __future__ import annotations

from neurofly.olfaction_calibration import CONDITIONS, SCHEMA, _channel_gate


def _condition(food_left: float, food_right: float, danger_left: float, danger_right: float):
    return {
        "food": {
            "left": {"spikes_per_neuron": food_left},
            "right": {"spikes_per_neuron": food_right},
        },
        "danger": {
            "left": {"spikes_per_neuron": danger_left},
            "right": {"spikes_per_neuron": danger_right},
        },
    }


def test_calibration_contract_has_matched_unilateral_conditions() -> None:
    assert SCHEMA == "neurofly-olfaction-calibration-v1"
    assert CONDITIONS["odor_off"] == {"food": (0.0, 0.0), "danger": (0.0, 0.0)}
    assert CONDITIONS["food_left"]["food"] == (1.0, 0.0)
    assert CONDITIONS["food_right"]["food"] == (0.0, 1.0)
    assert CONDITIONS["danger_left"]["danger"] == (1.0, 0.0)
    assert CONDITIONS["danger_right"]["danger"] == (0.0, 1.0)


def test_channel_gate_requires_baseline_delta_and_lateralization() -> None:
    results = {
        "odor_off": _condition(2.0, 2.2, 1.0, 1.1),
        "food_left": _condition(8.0, 2.5, 1.1, 1.2),
        "food_right": _condition(2.1, 8.5, 1.0, 1.2),
        "danger_left": _condition(2.1, 2.3, 7.0, 1.3),
        "danger_right": _condition(2.0, 2.4, 1.2, 7.5),
    }

    gate = _channel_gate(
        results=results,
        condition="food_left",
        channel="food",
        side="left",
    )
    assert gate["positive_delta"] is True
    assert gate["ipsilateral_gt_contralateral"] is True
    assert gate["passed"] is True

    # A response can rise above baseline but still fail if it is not lateralized.
    results["food_left"] = _condition(3.0, 4.0, 1.1, 1.2)
    gate = _channel_gate(
        results=results,
        condition="food_left",
        channel="food",
        side="left",
    )
    assert gate["positive_delta"] is True
    assert gate["ipsilateral_gt_contralateral"] is False
    assert gate["passed"] is False
