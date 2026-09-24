from pathlib import Path

PROBE = Path("scripts/research_probe_public_fanc_meta_export.py").read_text()


def test_pipeline_mapping_semantics_are_pinned():
    assert 'PIPELINE_COMMIT = "5c333c12f0b9e03873f88cf4e23cad34c0bb49c1"' in PROBE
    assert 'PIPELINE_META_PATH = "fanc/fanc-meta.R"' in PROBE
    assert 'TARGET_CELL_ID = "20201"' in PROBE


def test_all_five_hook_flx_roots_are_pinned():
    for root in (
        "648518346481857725",
        "648518346509569667",
        "648518346494933426",
        "648518346514448583",
        "648518346494264434",
    ):
        assert root in PROBE


def test_public_metadata_candidate_paths_are_explicit():
    for path in (
        "meta/fanc_meta.csv",
        "meta/fanc_meta.feather",
        "compiled_data/fanc_1116/fanc_meta.csv",
        "compiled_data/fanc_1116/fanc_1116_meta.feather",
    ):
        assert path in PROBE
    assert '"meta/fanc"' in PROBE


def test_exact_same_row_mapping_is_required():
    assert "exact_20201_to_hook_root_rows" in PROBE
    assert "exact_20201_to_hook_root_found" in PROBE
    assert "cell_id == TARGET_CELL_ID and root_id in HOOK_FLX_ROOTS" in PROBE


def test_hard_locks_remain_false():
    for key in (
        '"curated_fanc_to_manc_snpp_bridge_found": False',
        '"exact_polarity_verified": False',
        '"current_calibration_authorized": False',
        '"runtime_stimulation_authorized": False',
        '"privileged_state_bypass_authorized": False',
    ):
        assert key in PROBE
