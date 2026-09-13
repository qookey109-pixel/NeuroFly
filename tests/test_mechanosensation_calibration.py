from neurofly.mechanosensation import virtual_antennal_mechanosensation
from neurofly.mechanosensation_calibration import CONDITIONS, evaluate_response_gates


def test_predeclared_airflow_conditions_map_to_expected_opponent_channels() -> None:
    fly = {"x": 1, "y": 1, "dir": "RIGHT"}
    states = {
        name: virtual_antennal_mechanosensation(fly=fly, airflow=airflow)
        for name, airflow in CONDITIONS.items()
    }

    off = states["airflow_off"]
    assert off["left"] == {"jo_c": 0.0, "jo_e": 0.0}
    assert off["right"] == {"jo_c": 0.0, "jo_e": 0.0}

    assert states["headwind"]["left"]["jo_e"] == 1.0
    assert states["headwind"]["right"]["jo_e"] == 1.0
    assert states["tailwind"]["left"]["jo_c"] == 1.0
    assert states["tailwind"]["right"]["jo_c"] == 1.0

    right_crosswind = states["crosswind_right"]
    assert right_crosswind["left"]["jo_c"] > 0.0
    assert right_crosswind["right"]["jo_e"] > 0.0
    assert right_crosswind["right"]["jo_c"] == 0.0
    assert right_crosswind["left"]["jo_e"] == 0.0

    left_crosswind = states["crosswind_left"]
    assert left_crosswind["right"]["jo_c"] > 0.0
    assert left_crosswind["left"]["jo_e"] > 0.0
    assert left_crosswind["left"]["jo_c"] == 0.0
    assert left_crosswind["right"]["jo_e"] == 0.0


def _metric(value: float) -> dict[str, float | int]:
    return {"neurons": 10, "spikes": int(value * 10), "spikes_per_neuron": value}


def _condition(*, c_left: float = 0, c_right: float = 0, e_left: float = 0, e_right: float = 0):
    return {
        "jo_c": {"left": _metric(c_left), "right": _metric(c_right)},
        "jo_e": {"left": _metric(e_left), "right": _metric(e_right)},
    }


def test_response_gates_cover_bilateral_and_crosswind_selectivity() -> None:
    results = {
        "airflow_off": _condition(),
        "headwind": _condition(e_left=2, e_right=2),
        "tailwind": _condition(c_left=2, c_right=2),
        "crosswind_right": _condition(c_left=2, c_right=0.2, e_left=0.2, e_right=2),
        "crosswind_left": _condition(c_left=0.2, c_right=2, e_left=2, e_right=0.2),
    }

    gates = evaluate_response_gates(results)
    assert len(gates) == 8
    assert all(gate["passed"] for gate in gates)


def test_response_gate_rejects_wrong_crosswind_laterality() -> None:
    results = {
        "airflow_off": _condition(),
        "headwind": _condition(e_left=2, e_right=2),
        "tailwind": _condition(c_left=2, c_right=2),
        "crosswind_right": _condition(c_left=0.2, c_right=2, e_left=2, e_right=0.2),
        "crosswind_left": _condition(c_left=0.2, c_right=2, e_left=2, e_right=0.2),
    }

    gates = evaluate_response_gates(results)
    assert any(not gate["passed"] for gate in gates)
