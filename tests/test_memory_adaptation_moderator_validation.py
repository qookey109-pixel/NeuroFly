import json
from pathlib import Path

from neurofly.memory_adaptation_moderator_validation import (
    CANDIDATE_POOL,
    ENGAGED_MIN,
    EXPECTED_CONDITIONS,
    LEAD_FEATURE,
    QUIESCENT_MAX,
    TARGET_PER_STRATUM,
    _classify,
    validate_config,
)

def test_adaptation_moderator_validation_contract():
    c=json.loads(Path("data/memory_adaptation_moderator_validation_v01.json").read_text())
    gates=validate_config(c)
    assert gates and all(gates.values()), gates
    assert TARGET_PER_STRATUM == 4
    assert len(CANDIDATE_POOL) == 48
    assert LEAD_FEATURE == "adaptation.paired_mean.std"
    assert QUIESCENT_MAX == 0.10
    assert ENGAGED_MIN == 0.50
    assert _classify(0.05) == "quiescent"
    assert _classify(0.30) == "intermediate"
    assert _classify(1.00) == "engaged"
    assert EXPECTED_CONDITIONS == ("intact","clear_vg_delay")
    assert c["validation"]["passing_both_targets_supports_replication_not_confirmation"] is True
    assert all(v is False for v in c["claim_policy"].values())
