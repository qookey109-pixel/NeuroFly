from neurofly.gustation_calibration import EXPECTED_CLASS_COUNTS, _response_gate


def _condition(bitter: tuple[int, int], sugar_water: tuple[int, int]) -> dict:
    return {
        "groups": {
            "bitter": {
                "neurons": EXPECTED_CLASS_COUNTS["bitter"],
                "spikes": bitter[0],
                "spikes_per_neuron": bitter[0] / EXPECTED_CLASS_COUNTS["bitter"],
                "active_neurons": bitter[1],
            },
            "sugar_water": {
                "neurons": EXPECTED_CLASS_COUNTS["sugar_water"],
                "spikes": sugar_water[0],
                "spikes_per_neuron": sugar_water[0] / EXPECTED_CLASS_COUNTS["sugar_water"],
                "active_neurons": sugar_water[1],
            },
        }
    }


def test_bitter_gate_requires_positive_target_delta_and_activity() -> None:
    results = {
        "contact_off": _condition((0, 0), (0, 0)),
        "bitter": _condition((12, 4), (3, 2)),
        "sugar_water": _condition((1, 1), (80, 60)),
    }
    gate = _response_gate(results, "bitter")
    assert gate["positive_delta"] is True
    assert gate["target_population_active"] is True
    assert gate["passed"] is True


def test_sugar_water_gate_does_not_depend_on_bitter_crosstalk() -> None:
    results = {
        "contact_off": _condition((2, 1), (10, 5)),
        "bitter": _condition((20, 6), (100, 70)),
        "sugar_water": _condition((0, 0), (120, 70)),
    }
    gate = _response_gate(results, "sugar_water")
    assert gate["delta_spikes_per_neuron"] > 0
    assert gate["passed"] is True


def test_gate_fails_when_target_does_not_exceed_matched_baseline() -> None:
    results = {
        "contact_off": _condition((6, 3), (77, 40)),
        "bitter": _condition((6, 3), (0, 0)),
        "sugar_water": _condition((0, 0), (77, 40)),
    }
    assert _response_gate(results, "bitter")["passed"] is False
    assert _response_gate(results, "sugar_water")["passed"] is False
