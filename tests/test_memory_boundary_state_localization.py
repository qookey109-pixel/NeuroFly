import json
from pathlib import Path

from neurofly.memory_boundary_state_localization import (
    EXPECTED_CONDITIONS,
    FULL_HISTORY_DECISIONS,
    PREFIX_DECISIONS,
    TERMINAL_DECISIONS,
    validate_config,
)


def test_boundary_state_contract_is_frozen():
    config = json.loads(
        Path("data/memory_boundary_state_localization_v01.json").read_text()
    )
    gates = validate_config(config)
    assert gates
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())


def test_boundary_geometry_is_frozen():
    assert PREFIX_DECISIONS == 40
    assert TERMINAL_DECISIONS == 20
    assert FULL_HISTORY_DECISIONS == 60
    assert EXPECTED_CONDITIONS == (
        "intact",
        "clear_rule_traces",
        "clear_membrane_conductance",
        "clear_wrapper_visual_history",
    )
