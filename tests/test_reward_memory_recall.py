import json
from pathlib import Path

from neurofly.reward_memory_recall import validate_config


def test_reward_memory_recall_contract_is_frozen():
    config = json.loads(Path("data/reward_memory_recall_v01.json").read_text())
    gates = validate_config(config)
    assert gates
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())
