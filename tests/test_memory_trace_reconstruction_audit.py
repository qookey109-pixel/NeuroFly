import json
import math
from pathlib import Path

import numpy as np

from neurofly.memory_trace_reconstruction_audit import (
    KC_TRACE_SECONDS,
    NEURAL_MS_PER_DECISION,
    ONE_TAU_DECISIONS,
    THREE_TAU_DECISIONS,
    THREE_TAU_RESIDUAL,
    _trace_metrics,
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


def test_trace_metrics_are_descriptive_and_deterministic():
    target = np.asarray([1.0, 2.0, 0.0, 1.0], dtype=np.float64)
    exact = _trace_metrics(target, target)
    assert exact["cosine_similarity"] == 1.0
    assert exact["l1_overlap_fraction"] == 1.0
    assert exact["normalized_l1_error"] == 0.0
    assert exact["replay_target_l1_ratio"] == 1.0
    assert exact["target_positive_edge_recovery_fraction"] == 1.0

    partial = _trace_metrics(
        target,
        np.asarray([1.0, 0.0, 0.0, 0.5], dtype=np.float64),
    )
    assert partial["l1_overlap_fraction"] == 0.375
    assert partial["normalized_l1_error"] == 0.625
    assert partial["replay_target_l1_ratio"] == 0.375
    assert partial["target_positive_edge_recovery_fraction"] == round(2 / 3, 12)
