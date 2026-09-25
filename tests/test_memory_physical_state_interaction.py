import json
from pathlib import Path
from neurofly.memory_physical_state_interaction import EXPECTED_CONDITIONS, EXPECTED_REPLICATES, validate_config

def test_scheduler_distributed_contract():
    c=json.loads(Path("data/memory_physical_state_interaction_v01.json").read_text())
    gates=validate_config(c)
    assert gates and all(gates.values()), gates
    assert EXPECTED_CONDITIONS == (
        "intact","coherent_scheduler_rebuild","clear_vg_adaptation","clear_broad_physical_transient"
    )
    assert EXPECTED_REPLICATES == (("PI1",3607),("PI2",3613),("PI3",3617),("PI4",3623))
    assert all(v is False for v in c["claim_policy"].values())


def test_physical_state_interaction_contract_extra():
    config=json.loads(Path("data/memory_physical_state_interaction_v01.json").read_text())
    assert tuple(x["id"] for x in config["runtime"]["conditions"]) == (
        "intact","coherent_scheduler_rebuild","clear_vg_adaptation",
        "clear_input_delay","clear_broad_physical_transient",
    )
    ia=config["interaction_analysis"]
    assert ia["descriptive_interaction_contrast"] == "combined - subsystem_a - subsystem_b + intact"
