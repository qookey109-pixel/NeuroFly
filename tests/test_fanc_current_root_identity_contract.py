from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

SCRIPT = Path("scripts/research_probe_fanc_current_root_identity.py")

def load_probe():
    spec = spec_from_file_location("research_probe_fanc_current_root_identity", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_legacy_ids_and_namespace_are_frozen() -> None:
    probe = load_probe()
    assert probe.LEGACY_FANC_SKIDS == [25849, 25842, 25856, 24831, 25909]
    assert probe.ID_NAMESPACE == "FANC_Phelps_CATMAID_project2_skeleton"

def test_official_fanc_mapping_services_are_pinned() -> None:
    probe = load_probe()
    assert "fanc_v4_to_v3" in probe.FANC_V4_TO_V3_BASE
    assert "fanc_v4" in probe.FANC_SVID_LOOKUP
    assert probe.FANC_DATASTACK == "fanc_production_mar2021"

def test_swc_paths_are_author_hook_cells() -> None:
    probe = load_probe()
    for skid in probe.LEGACY_FANC_SKIDS:
        path = probe.SWC_PATHS[skid]
        assert f"(neuron {skid}).swc" in path
        assert "hook chordotonal sensory neuron" in path

def test_namespace_collision_is_not_identity() -> None:
    probe = load_probe()
    assert probe.TARGET_MANC_BODY == 97015
    assert probe.TARGET_MALECNS_BODY == 911942
    assert 25849 != probe.TARGET_MANC_BODY

def test_probe_never_auto_unlocks() -> None:
    probe = load_probe()
    assert probe.RECEIPT_SCHEMA == "neurofly-fanc-current-root-audit-v0.5"
    assert probe.DECISION_POLICY == "evidence_only_no_auto_unlock"


def test_direct_chunkedgraph_endpoint_is_pinned() -> None:
    probe = load_probe()
    assert probe.FANC_CHUNKEDGRAPH_BASE == "https://cave.fanc-fly.com/segmentation/api/v1"
    assert probe.FANC_CHUNKEDGRAPH_TABLE == "mar2021_prod"


def test_vfb_xref_fallback_is_public_and_read_only() -> None:
    probe = load_probe()
    assert probe.VFB_BASE == "https://v3-cached.virtualflybrain.org"


def test_vfb_xref_is_dataset_filtered() -> None:
    probe = load_probe()
    assert probe.VFB_FANC_XREF_DBS == (
        "catmaid_fanc",
        "catmaid_fanc_JRC2018VF",
    )
