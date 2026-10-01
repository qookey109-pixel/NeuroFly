import json
from pathlib import Path

from neurofly.memory_scheduler_canonicalization import (
    ALLOWED_SCHEDULER_FIELDS,
    EXPECTED_CONDITIONS,
    EXPECTED_REPLICATES,
    validate_config,
)


def test_scheduler_contract_is_frozen():
    config = json.loads(
        Path("data/memory_scheduler_canonicalization_v01.json").read_text()
    )
    gates = validate_config(config)
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())


def test_scheduler_intervention_scope_is_frozen():
    assert EXPECTED_CONDITIONS == ("intact", "canonical_scheduler")
    assert EXPECTED_REPLICATES == (
        ("SC1", 3503), ("SC2", 3511), ("SC3", 3517), ("SC4", 3527)
    )
    assert ALLOWED_SCHEDULER_FIELDS == {
        "previous_drive", "last", "active", "active_flag", "nactive"
    }
