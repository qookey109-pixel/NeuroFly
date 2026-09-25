import json
from pathlib import Path
from neurofly.memory_scheduler_distributed_control import EXPECTED_CONDITIONS, EXPECTED_REPLICATES, validate_config

def test_scheduler_distributed_contract():
    c=json.loads(Path("data/memory_scheduler_distributed_control_v01.json").read_text())
    gates=validate_config(c)
    assert gates and all(gates.values()), gates
    assert EXPECTED_CONDITIONS == (
        "intact","coherent_scheduler_rebuild","clear_vg_adaptation","clear_broad_physical_transient"
    )
    assert EXPECTED_REPLICATES == (("SD1",3501),("SD2",3511),("SD3",3527),("SD4",3533))
    assert all(v is False for v in c["claim_policy"].values())
