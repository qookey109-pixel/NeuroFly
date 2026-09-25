import json
import math
from pathlib import Path

from neurofly.memory_trace_reconstruction_audit import (
    KC_TRACE_SECONDS,
    NEURAL_MS_PER_DECISION,
    ONE_TAU_DECISIONS,
    THREE_TAU_DECISIONS,
    THREE_TAU_RESIDUAL,
    validate_config,
)


def test_trace_reconstruction_contract_is_frozen():
    config = json.loads(
        Path("data/memory_trace_reconstruction_audit_v01.json").read_text()
    )
    gates = validate_config(config)
    assert gates
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())


def test_trace_windows_match_frozen_model_time_constants():
    assert ONE_TAU_DECISIONS == round(
        KC_TRACE_SECONDS * 1000 / NEURAL_MS_PER_DECISION
    )
    assert ONE_TAU_DECISIONS == 20
    assert THREE_TAU_DECISIONS == 60
    assert THREE_TAU_DECISIONS == 3 * ONE_TAU_DECISIONS
    assert THREE_TAU_RESIDUAL == round(math.exp(-3.0), 12)
