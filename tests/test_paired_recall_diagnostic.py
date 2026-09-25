import json
from pathlib import Path

from neurofly.paired_recall_diagnostic import (
    _persistence_ratio,
    validate_config,
)


def test_paired_recall_contract_is_frozen():
    config = json.loads(Path("data/paired_recall_diagnostic_v01.json").read_text())
    gates = validate_config(config)
    assert gates
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())


def test_persistence_ratio_is_descriptive_only():
    assert _persistence_ratio(2.0, 1.0) == 0.5
    assert _persistence_ratio(1.0, 1.25) == 1.25
    assert _persistence_ratio(0.0, 0.0) is None
