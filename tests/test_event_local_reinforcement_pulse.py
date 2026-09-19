import json
from pathlib import Path

from neurofly.event_local_reinforcement_pulse import (
    EXPECTED_REPLICATES,
    USED_SEEDS,
    validate_config,
)


CONFIG = Path("data/event_local_reinforcement_pulse_v01.json")
FREEZE = Path("data/full_network_reinforcement_pulse_run1_freeze_v01.json")
SOURCE = Path("src/neurofly/event_local_reinforcement_pulse.py")


def test_event_local_config_is_frozen_and_claims_locked() -> None:
    config = json.loads(CONFIG.read_text())
    assert all(validate_config(config).values())
    assert all(value is False for value in config["claim_policy"].values())


def test_event_local_seeds_are_fresh() -> None:
    seeds = [seed for _, seed in EXPECTED_REPLICATES]
    assert len(seeds) == len(set(seeds))
    assert not (set(seeds) & USED_SEEDS)


def test_event_local_pair_rebuilds_identical_pre_event_state() -> None:
    source = SOURCE.read_text()
    assert "trajectory[:event_index]" in source
    assert "_build_pre_event_checkpoint(" in source
    assert "_branch_event(" in source
    assert 'reinforcement="none"' in source
    assert "pre-event.npz" in source


def test_event_local_pair_uses_real_brain_decide_pulse() -> None:
    source = SOURCE.read_text()
    assert "decision = inner.decide(" in source
    assert "stonkfly.neural.rule" not in source
    assert "_external_current" not in source
    assert "pre-event.npz" in source


def test_full_network_origin_freeze_is_valid() -> None:
    freeze = json.loads(FREEZE.read_text())
    assert freeze["run_id"] == 35429987465
    assert freeze["execution_valid"] is True
    assert freeze["receipt_sha256"] == (
        "b74c77cd32ce848a923f7a548f043c7dd9bc5fe6ad3c611bd44a365d1a05a001"
    )
    assert freeze["aggregate"]["true_minus_endogenous_final_mean_efficacy_delta"] < 0
