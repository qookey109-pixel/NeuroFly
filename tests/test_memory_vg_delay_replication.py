import json
from pathlib import Path

from neurofly.memory_vg_delay_replication import (
    CANDIDATE_POOL,
    EXPECTED_CONDITIONS,
    TARGET_FIELDS,
    validate_config,
)

def test_vg_delay_replication_contract():
    c=json.loads(Path("data/memory_vg_delay_replication_v01.json").read_text())
    gates=validate_config(c)
    assert gates and all(gates.values()), gates
    assert EXPECTED_CONDITIONS == (
        "intact",
        "clear_vg_delay",
        "clear_broad_physical_transient",
    )
    assert TARGET_FIELDS["clear_vg_delay"] == ("v","g","refractory","queue","queue_count")
    assert TARGET_FIELDS["clear_broad_physical_transient"] == (
        "v","g","adaptation","luminance","refractory","queue","queue_count"
    )
    assert len(CANDIDATE_POOL)==20
    assert c["selection"]["selection_is_outcome_blind"] is True
    assert c["replication_analysis"]["replication_pattern"] == (
        "candidate condition is lower than intact on all three primary neural endpoints in each selected history"
    )
    assert all(v is False for v in c["claim_policy"].values())
