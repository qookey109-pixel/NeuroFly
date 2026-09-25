import json
from pathlib import Path

from neurofly.memory_history_expression_bridge import (
    KC_TRACE_SECONDS,
    NEURAL_MS_PER_DECISION,
    ONE_TAU_DECISIONS,
    THREE_TAU_DECISIONS,
    validate_config,
)


def test_history_expression_contract_is_frozen():
    config = json.loads(
        Path("data/memory_history_expression_bridge_v01.json").read_text()
    )
    gates = validate_config(config)
    assert gates
    assert all(gates.values()), gates
    assert all(value is False for value in config["claim_policy"].values())


def test_history_windows_match_frozen_model_clock():
    assert ONE_TAU_DECISIONS == round(
        KC_TRACE_SECONDS * 1000 / NEURAL_MS_PER_DECISION
    )
    assert ONE_TAU_DECISIONS == 20
    assert THREE_TAU_DECISIONS == 60
    assert THREE_TAU_DECISIONS == 3 * ONE_TAU_DECISIONS


def test_primary_comparison_window_is_common_terminal_window():
    config = json.loads(
        Path("data/memory_history_expression_bridge_v01.json").read_text()
    )
    runtime = config["runtime"]
    assert runtime["primary_comparison_window"] == (
        "common terminal lags -20 through 0 inclusive"
    )
    assert runtime["three_tau_context_only_window"] == (
        "lags -60 through -21 are context warmup only and are excluded "
        "from primary expression counts"
    )
