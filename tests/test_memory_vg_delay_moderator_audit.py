import json
from pathlib import Path

from neurofly.memory_vg_delay_moderator_audit import (
    CANDIDATE_POOL,
    EXPECTED_CONDITIONS,
    PHYSICAL_FIELDS,
    PHYSICAL_STATS,
    PRIMARY_ENDPOINTS,
    TARGET_REPLICATES,
    validate_config,
)

def test_vg_delay_moderator_audit_contract():
    c=json.loads(Path("data/memory_vg_delay_moderator_audit_v01.json").read_text())
    gates=validate_config(c)
    assert gates and all(gates.values()), gates
    assert TARGET_REPLICATES == 8
    assert len(CANDIDATE_POOL) == 30
    assert EXPECTED_CONDITIONS == ("intact","clear_vg_delay")
    assert PHYSICAL_FIELDS == ("v","g","adaptation","luminance","refractory","queue_count","nactive")
    assert PHYSICAL_STATS == ("mean","std","p95_abs","max_abs","nonzero_fraction")
    assert PRIMARY_ENDPOINTS == (
        "mean_changed_kc_active_fraction",
        "mean_changed_l1_engaged_fraction",
        "mean_mbon07_state_difference_fraction",
    )
    assert c["analysis_policy"]["exploratory_discovery_only"] is True
    assert c["analysis_policy"]["any_moderator_hypothesis_requires_new_preregistered_cohort"] is True
    assert all(v is False for v in c["claim_policy"].values())
