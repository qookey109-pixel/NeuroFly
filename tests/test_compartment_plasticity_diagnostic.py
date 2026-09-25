import json
from pathlib import Path

from neurofly.compartment_plasticity_diagnostic import (
    _summarize_difference,
    validate_config,
)


def test_compartment_plasticity_contract_is_frozen():
    config = json.loads(
        Path("data/compartment_plasticity_diagnostic_v01.json").read_text()
    )
    gates = validate_config(config)
    assert gates
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())


def test_compartment_summary_uses_preselected_mask_only():
    summary = _summarize_difference(
        [-0.20, 0.10, 0.01, -0.01],
        [True, True, False, False],
    )
    assert summary["target_edge_count"] == 2
    assert summary["off_target_edge_count"] == 2
    assert summary["target_changed_edge_count"] == 2
    assert summary["off_target_changed_edge_count"] == 2
    assert summary["target_negative_edge_count"] == 1
    assert summary["target_positive_edge_count"] == 1
    assert summary["target_l1"] == 0.3
    assert summary["off_target_l1"] == 0.02
    assert summary["target_l1_fraction"] == 0.9375
    assert summary["target_dominant"] is True
    assert summary["target_negative_edge_fraction"] == 0.5
    assert summary["target_positive_edge_fraction"] == 0.5
    assert summary["off_target_max_abs_delta"] == 0.01
