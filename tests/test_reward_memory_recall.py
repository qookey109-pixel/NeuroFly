import json
from pathlib import Path

from neurofly.reward_memory_recall import _receipt_plastic_state, validate_config


def test_reward_memory_recall_contract_is_frozen():
    config = json.loads(Path("data/reward_memory_recall_v02.json").read_text())
    gates = validate_config(config)
    assert gates
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())


def test_reward_memory_receipt_state_is_json_serializable():
    state = {
        "fraction": object(),
        "reward_mask": object(),
        "aversive_mask": object(),
        "fraction_digest": "abc",
        "reward_mask_digest": "reward",
        "aversive_mask_digest": "aversive",
    }
    cleaned = _receipt_plastic_state(state)
    assert "fraction" not in cleaned
    assert "reward_mask" not in cleaned
    assert "aversive_mask" not in cleaned
    assert cleaned["fraction_digest"] == "abc"
    json.dumps(cleaned)


def test_reward_memory_v01_is_frozen_invalid():
    frozen = json.loads(
        Path("data/reward_memory_recall_v01_invalid_freeze.json").read_text()
    )
    assert frozen["status"] == "INVALID_DESIGN_FEASIBILITY_NO_SCIENTIFIC_RESULT"
    assert frozen["interpretation"]["seed_replacement_after_failure_allowed"] is False
    assert frozen["interpretation"]["v01_endpoint_result_exists"] is False
