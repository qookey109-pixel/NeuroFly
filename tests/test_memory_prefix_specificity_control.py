import json
from pathlib import Path

from neurofly.memory_prefix_specificity_control import (
    FULL_HISTORY_DECISIONS,
    PREFIX_DECISIONS,
    PREFIX_ROTATION_POSITIONS,
    TERMINAL_DECISIONS,
    validate_config,
)


def test_prefix_specificity_contract_is_frozen():
    config = json.loads(
        Path("data/memory_prefix_specificity_control_v01.json").read_text()
    )
    gates = validate_config(config)
    assert gates
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())


def test_prefix_geometry_is_frozen():
    assert TERMINAL_DECISIONS == 20
    assert PREFIX_DECISIONS == 40
    assert FULL_HISTORY_DECISIONS == 60
    assert PREFIX_ROTATION_POSITIONS == 20
    assert PREFIX_ROTATION_POSITIONS == PREFIX_DECISIONS // 2


def test_control_preserves_terminal_comparison_window():
    config = json.loads(
        Path("data/memory_prefix_specificity_control_v01.json").read_text()
    )
    runtime = config["runtime"]
    assert runtime["primary_comparison_window"] == (
        "common terminal replay lags -20 through 0 inclusive"
    )
    assert runtime["prefix_rotation_positions"] == 20
