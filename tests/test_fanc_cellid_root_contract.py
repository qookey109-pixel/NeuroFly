from pathlib import Path

PROBE = Path("scripts/research_probe_fanc_cellid_root.py").read_text()


def test_exact_fanc_snapshot_and_cell_id_are_pinned():
    assert 'BANC_FANC_VERSION = 1116' in PROBE
    assert 'TARGET_FANC_CELL_ID = 20201' in PROBE
    assert 'TABLE = "cell_ids_v2"' in PROBE
    assert 'DATASTACK = "fanc_production_mar2021"' in PROBE


def test_all_five_hook_flx_roots_are_pinned():
    for root in (
        "648518346481857725",
        "648518346509569667",
        "648518346494933426",
        "648518346514448583",
        "648518346494264434",
    ):
        assert root in PROBE


def test_both_forward_and_reverse_exact_queries_exist():
    assert '"id": TARGET_FANC_CELL_ID' in PROBE
    assert '"user_id": TARGET_FANC_CELL_ID' in PROBE
    assert '"pt_root_id": sorted(HOOK_FLX_ROOTS)' in PROBE
    assert "target_cell_to_hook_root_exact_found" in PROBE
    assert "reverse_hook_root_to_target_cell_exact_found" in PROBE


def test_auth_block_is_not_negative_scientific_evidence():
    assert "HTTP-200 login interstitials are valid fail-closed auth outcomes" in PROBE
    assert "AUTH_INTERSTITIAL" in PROBE
    assert "accounts.google.com" in PROBE
    assert "auth_interstitial_response_count" in PROBE
    assert "validation=false" in PROBE


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


def test_public_static_fanc_metadata_discovery_is_included():
    assert 'GCS_BUCKET = "lee-lab_brain-and-nerve-cord-fly-connectome"' in PROBE
    assert '"compiled_data/fanc"' in PROBE
    assert "list_public_gcs" in PROBE
    assert "public_gcs_static_candidate_objects" in PROBE


def test_public_gcs_hierarchy_listing_is_pinned():
    assert 'GCS_HIERARCHY_PREFIX = "compiled_data/fanc_1116/"' in PROBE
    assert 'delimiter="/"' in PROBE
    assert "common_prefixes" in PROBE
    assert "public_gcs_hierarchy" in PROBE
