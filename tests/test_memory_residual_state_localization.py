import json
from pathlib import Path

from neurofly.memory_residual_state_localization import (
    EXPECTED_CONDITIONS,
    FULL_HISTORY_DECISIONS,
    PREFIX_DECISIONS,
    TARGET_FIELDS,
    TERMINAL_DECISIONS,
    validate_config,
)


def test_residual_state_contract_is_frozen():
    config = json.loads(
        Path("data/memory_residual_state_localization_v01.json").read_text()
    )
    gates = validate_config(config)
    assert gates
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())


def test_residual_state_conditions_are_single_class():
    assert EXPECTED_CONDITIONS == (
        "intact",
        "clear_refractory_delay",
        "clear_luminance",
        "clear_adaptation",
        "clear_kernel_credit",
    )
    assert TARGET_FIELDS["clear_refractory_delay"] == {
        "refractory", "queue", "queue_count"
    }
    assert TARGET_FIELDS["clear_luminance"] == {"luminance"}
    assert TARGET_FIELDS["clear_adaptation"] == {"adaptation"}
    assert TARGET_FIELDS["clear_kernel_credit"] == {
        "eligibility", "eligibility_last", "modulation", "modulation_last"
    }


def test_residual_state_geometry_is_frozen():
    assert PREFIX_DECISIONS == 40
    assert TERMINAL_DECISIONS == 20
    assert FULL_HISTORY_DECISIONS == 60
