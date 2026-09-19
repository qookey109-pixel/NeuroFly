import json
from pathlib import Path

from neurofly.full_network_reinforcement_pulse_replay import (
    EXPECTED_REPLICATES,
    USED_SEEDS,
    validate_config,
)


CONFIG = Path("data/full_network_reinforcement_pulse_replay_v01.json")
FREEZE = Path("data/external_reinforcement_increment_run2_freeze_v01.json")
SOURCE = Path("src/neurofly/full_network_reinforcement_pulse_replay.py")


def test_full_network_pulse_replay_config_is_frozen() -> None:
    config = json.loads(CONFIG.read_text())
    assert all(validate_config(config).values())
    assert all(value is False for value in config["claim_policy"].values())


def test_full_network_pulse_replay_seeds_are_fresh() -> None:
    seeds = [seed for _, seed in EXPECTED_REPLICATES]
    assert len(seeds) == len(set(seeds))
    assert not (set(seeds) & USED_SEEDS)


def test_full_network_replay_uses_real_brain_pulse_not_rule_input_proxy() -> None:
    source = SOURCE.read_text()
    assert 'decision = self.inner.decide(frame_copy, "none", context=context_copy)' in source
    assert 'condition == "true_external"' in source
    assert "decision = inner.decide(" in source
    assert "stonkfly.neural.rule" not in source
    assert "_external_current" not in source


def test_run2_freeze_pins_valid_origin_and_limit() -> None:
    freeze = json.loads(FREEZE.read_text())
    assert freeze["run_id"] == 35426688269
    assert freeze["execution_valid"] is True
    assert freeze["receipt_sha256"] == (
        "d0f685da13ebcfc805fb954bfd4567d9d41b86932649d31635f5d6c436f63a2f"
    )
    assert freeze["aggregate"]["true_minus_endogenous_final_mean_efficacy_delta"] < 0
    assert "not a full-network LIF pulse replay" in freeze["interpretation_limit"]
