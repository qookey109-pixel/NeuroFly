import json
from pathlib import Path

from neurofly.memory_temporal_index_audit import (
    KC_TRACE_SECONDS,
    NEURAL_MS_PER_DECISION,
    TRACE_WINDOW_DECISIONS,
    validate_config,
)


def test_temporal_index_contract_is_frozen():
    config = json.loads(
        Path("data/memory_temporal_index_audit_v01.json").read_text()
    )
    gates = validate_config(config)
    assert gates
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())


def test_trace_window_matches_one_frozen_model_time_constant():
    assert TRACE_WINDOW_DECISIONS == round(
        KC_TRACE_SECONDS * 1000 / NEURAL_MS_PER_DECISION
    )
    assert TRACE_WINDOW_DECISIONS == 20
