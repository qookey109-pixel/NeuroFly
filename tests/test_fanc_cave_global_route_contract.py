from pathlib import Path

PROBE = Path("scripts/research_probe_fanc_cave_global_route.py").read_text()


def test_official_global_route_is_pinned():
    assert 'GLOBAL_SERVER = "https://global.daf-apis.com"' in PROBE
    assert "/info/api/v2/datastack/full/" in PROBE
    assert 'DATASTACK = "fanc_production_mar2021"' in PROBE
    assert "local_server" in PROBE


def test_authoritative_tables_and_versions_are_pinned():
    assert 'FECO_TABLE = "feco_axons_v0"' in PROBE
    assert "FECO_VERSION = 840" in PROBE
    assert 'CELL_ID_TABLE = "cell_ids_v2"' in PROBE
    assert "CELL_ID_VERSION = 1116" in PROBE
    assert "TARGET_FANC_CELL_ID = 20201" in PROBE


def test_all_five_hook_roots_and_supervoxels_are_pinned():
    for token in (
        "648518346481857725",
        "648518346509569667",
        "648518346494933426",
        "648518346514448583",
        "648518346494264434",
        "72342438215378040",
        "72342438215374178",
        "72342438215365972",
        "72342438215393919",
        "72342438215387174",
    ):
        assert token in PROBE


def test_exact_queries_and_direction_guard_exist():
    assert '"pt_root_id": sorted(HOOK_FLX_ROOTS)' in PROBE
    assert '"id": TARGET_FANC_CELL_ID' in PROBE
    assert '== "hook_flx"' in PROBE
    assert "exact_20201_to_hook_root_found" in PROBE


def test_validation_false_cannot_unlock():
    assert "validation=false" in PROBE
    for key in (
        '"curated_fanc_to_manc_snpp_bridge_found": False',
        '"exact_polarity_verified": False',
        '"current_calibration_authorized": False',
        '"runtime_stimulation_authorized": False',
        '"privileged_state_bypass_authorized": False',
    ):
        assert key in PROBE


def test_public_segment_properties_fallback_is_pinned():
    assert "FANC_SEGMENT_PROPERTIES_URL" in PROBE
    assert "fanc_1116_meshes_elastix_tpsreg_240721" in PROBE
    assert "segment_properties/info" in PROBE
    assert "audit_public_segment_properties" in PROBE
    assert "public_segment_properties_20201_label" in PROBE
