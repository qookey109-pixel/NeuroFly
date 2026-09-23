from pathlib import Path

PROBE = Path("scripts/research_probe_fancr_cellid_versions.py").read_text()


def test_official_sources_are_pinned():
    assert 'FANCR_COMMIT = "7b3d429729627d83dad9387f54294272640e87f9"' in PROBE
    assert 'DALLMANN_COMMIT = "e1233f4a987c532c9f1ab42273af21a0a6a50393"' in PROBE
    assert 'LEE_COMMIT = "4328b1d5549749f1014c4d73cccc0c5241d98ae4"' in PROBE


def test_versions_and_tables_are_frozen():
    assert "VERSIONS = (840, 1116)" in PROBE
    assert 'CELL_TABLE_CANDIDATES = ("cell_ids_v2", "cell_ids")' in PROBE
    assert 'FECO_TABLE = "feco_axons_v0"' in PROBE
    assert "TARGET_FANC_CELL_ID = 20201" in PROBE


def test_five_hook_flx_roots_and_supervoxels_are_frozen():
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


def test_forward_and_reverse_namespace_checks_exist():
    assert '{"id": TARGET_FANC_CELL_ID}' in PROBE
    assert '"pt_root_id": sorted(HOOK_FLX_ROOTS)' in PROBE
    assert "exact_20201_to_hook_flx_root_found" in PROBE
    assert "exact_cellid_20201_to_hook_flx_root_found" in PROBE


def test_auth_interstitial_is_fail_closed():
    assert "AUTH_INTERSTITIAL" in PROBE
    assert "accounts.google.com" in PROBE
    assert "Authentication/login interstitials are infrastructure boundaries" in PROBE


def test_hard_locks_remain_false():
    for key in (
        '"curated_r21d12_to_specific_fanc_em_identity_found": False',
        '"curated_fanc_to_manc_snpp_bridge_found": False',
        '"exact_polarity_verified": False',
        '"current_calibration_authorized": False',
        '"runtime_stimulation_authorized": False',
        '"privileged_state_bypass_authorized": False',
    ):
        assert key in PROBE
