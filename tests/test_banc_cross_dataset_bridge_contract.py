from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path("scripts/research_probe_banc_cross_dataset_bridge.py")


def load_probe():
    spec = spec_from_file_location("research_probe_banc_cross_dataset_bridge", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_targets_are_frozen() -> None:
    probe = load_probe()
    assert probe.TARGET_BANC_ROOT == "720575941508169089"
    assert probe.TARGET_MANC_BODY == "97015"
    assert probe.TARGET_MALECNS_BODY == "911942"
    assert probe.TARGET_TYPE == "SNpp41"
    assert probe.TARGET_SUBCLASS == "middle_leg_hook_chordotonal_organ_neuron"


def test_legacy_fanc_ids_are_not_relabelled() -> None:
    probe = load_probe()
    assert probe.LEGACY_FANC_CATMAID_IDS == [
        "25849", "25842", "25856", "24831", "25909"
    ]


def test_pipeline_semantics_requires_explicit_cell_id_definition() -> None:
    probe = load_probe()
    yes = probe.pipeline_semantics(
        "Columns: query_root_id (BANC root_id), match_id (FANC cell_id), score"
    )
    no = probe.pipeline_semantics("match_id (FANC root_id)")
    assert yes["fanc_match_id_semantics_confirmed"] is True
    assert no["fanc_match_id_semantics_confirmed"] is False


def test_supplement_bridge_requires_exact_proofread_row() -> None:
    probe = load_probe()
    row = {
        "root_id": probe.TARGET_BANC_ROOT,
        "cell_type": probe.TARGET_TYPE,
        "cell_sub_class": probe.TARGET_SUBCLASS,
        "manc_match": probe.TARGET_MANC_BODY,
        "malecns_match": probe.TARGET_MALECNS_BODY,
        "proofread": "TRUE",
        "fanc_match": "NA",
    }
    result = probe.supplement_bridge([row])
    assert result["independent_manc_malecns_bridge_confirmed"] is True
    assert result["exact_bridge_fanc_match"] == "NA"


def test_probe_never_auto_unlocks() -> None:
    probe = load_probe()
    assert probe.RECEIPT_SCHEMA == "neurofly-banc-cross-dataset-bridge-audit-v0.1"
    assert probe.DECISION_POLICY == "evidence_only_no_auto_unlock"
