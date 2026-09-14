from neurofly.tactile_calibration import (
    EXPECTED_TOTAL,
    EXPECTED_TYPE_COUNTS,
    _response_gate,
    _selected_population_gate,
)


def _metrics(neurons: int, spikes: int, active: int) -> dict:
    return {
        "neurons": neurons,
        "spikes": spikes,
        "spikes_per_neuron": 0.0 if neurons == 0 else spikes / neurons,
        "active_neurons": active,
    }


def _condition(type_values: dict[str, tuple[int, int]]) -> dict:
    types = {
        neuron_type: _metrics(
            EXPECTED_TYPE_COUNTS[neuron_type],
            type_values[neuron_type][0],
            type_values[neuron_type][1],
        )
        for neuron_type in EXPECTED_TYPE_COUNTS
    }
    return {
        "types": types,
        "selected_population": _metrics(
            EXPECTED_TOTAL,
            sum(item[0] for item in type_values.values()),
            sum(item[1] for item in type_values.values()),
        ),
    }


def test_each_tactile_type_gate_requires_positive_delta_and_activity() -> None:
    baseline_values = {name: (0, 0) for name in EXPECTED_TYPE_COUNTS}
    stimulated_values = {name: (EXPECTED_TYPE_COUNTS[name], 1) for name in EXPECTED_TYPE_COUNTS}
    results = {
        "contact_off": _condition(baseline_values),
        "front_contact": _condition(stimulated_values),
    }

    for neuron_type in EXPECTED_TYPE_COUNTS:
        gate = _response_gate(results, neuron_type)
        assert gate["positive_delta"] is True
        assert gate["target_population_active"] is True
        assert gate["passed"] is True

    selected = _selected_population_gate(results)
    assert selected["positive_delta"] is True
    assert selected["target_population_active"] is True
    assert selected["passed"] is True


def test_type_gate_fails_without_delta_even_when_population_is_active() -> None:
    baseline_values = {name: (0, 0) for name in EXPECTED_TYPE_COUNTS}
    stimulated_values = {name: (EXPECTED_TYPE_COUNTS[name], 1) for name in EXPECTED_TYPE_COUNTS}
    target = "SNta27"
    baseline_values[target] = (EXPECTED_TYPE_COUNTS[target], 1)
    stimulated_values[target] = (EXPECTED_TYPE_COUNTS[target], 1)

    results = {
        "contact_off": _condition(baseline_values),
        "front_contact": _condition(stimulated_values),
    }

    gate = _response_gate(results, target)
    assert gate["target_population_active"] is True
    assert gate["positive_delta"] is False
    assert gate["passed"] is False


def test_selected_population_gate_fails_without_any_activity() -> None:
    zeros = {name: (0, 0) for name in EXPECTED_TYPE_COUNTS}
    results = {
        "contact_off": _condition(zeros),
        "front_contact": _condition(zeros),
    }
    gate = _selected_population_gate(results)
    assert gate["positive_delta"] is False
    assert gate["target_population_active"] is False
    assert gate["passed"] is False
