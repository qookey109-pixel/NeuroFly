import json
from pathlib import Path

from neurofly.memory_expression_audit import validate_config


def test_memory_expression_contract_is_frozen():
    config = json.loads(Path("data/memory_expression_audit_v01.json").read_text())
    gates = validate_config(config)
    assert gates
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())
