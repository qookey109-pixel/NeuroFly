import json
from pathlib import Path

from neurofly.memory_interaction_diversity_recovery import (
    CANDIDATE_POOL,
    TARGET_REPLICATES,
    VOLATILE_CONTEXT_KEYS,
    _stable,
    validate_config,
)

def test_diversity_recovery_contract():
    config=json.loads(Path("data/memory_interaction_diversity_recovery_v01.json").read_text())
    gates=validate_config(config)
    assert gates and all(gates.values()), gates
    assert TARGET_REPLICATES == 4
    assert tuple(config["candidate_pool"]) == CANDIDATE_POOL
    assert tuple(x["id"] for x in config["runtime"]["conditions"]) == (
        "intact",
        "coherent_scheduler_rebuild",
        "clear_vg_adaptation",
        "clear_input_delay",
        "clear_broad_physical_transient",
    )
    assert all(v is False for v in config["claim_policy"].values())

def test_stable_context_removes_only_frozen_volatile_time_keys_recursively():
    payload={
        "survival_seconds":1.2,
        "fly":{"x":3,"seconds":99,"dir":"RIGHT"},
        "enemies":[{"x":4,"y":5,"total_active_seconds":2.0}],
        "reward":1.0,
    }
    stable=_stable(payload)
    assert stable == {
        "enemies":[{"x":4,"y":5}],
        "fly":{"dir":"RIGHT","x":3},
        "reward":1.0,
    }
    assert VOLATILE_CONTEXT_KEYS == {
        "survival_seconds","total_active_seconds","first_clear_seconds",
        "latest_clear_seconds","best_clear_seconds","seconds",
    }
