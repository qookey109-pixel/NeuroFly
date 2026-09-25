import json
from pathlib import Path

from neurofly.memory_cross_subsystem_localization import (
    CANDIDATE_POOL,
    EXPECTED_CONDITIONS,
    TARGET_FIELDS,
    validate_config,
)

def test_cross_subsystem_localization_contract():
    c=json.loads(Path("data/memory_cross_subsystem_localization_v01.json").read_text())
    gates=validate_config(c)
    assert gates and all(gates.values()), gates
    assert EXPECTED_CONDITIONS == (
        "intact",
        "clear_vg_luminance",
        "clear_vg_delay",
        "clear_adaptation_luminance",
        "clear_adaptation_delay",
        "clear_broad_physical_transient",
    )
    assert TARGET_FIELDS["clear_vg_luminance"] == ("v","g","luminance")
    assert TARGET_FIELDS["clear_vg_delay"] == ("v","g","refractory","queue","queue_count")
    assert TARGET_FIELDS["clear_adaptation_luminance"] == ("adaptation","luminance")
    assert TARGET_FIELDS["clear_adaptation_delay"] == ("adaptation","refractory","queue","queue_count")
    assert len(CANDIDATE_POOL)==20
    assert c["selection"]["selection_is_outcome_blind"] is True
    assert c["scheduler_control_policy"]["retired_from_this_round"] is True
    assert all(v is False for v in c["claim_policy"].values())
