from pathlib import Path

PROBE = Path("scripts/research_probe_public_fanc_raw_nblast.py").read_text()


def test_raw_pipeline_semantics_are_pinned():
    assert 'PIPELINE_COMMIT = "5c333c12f0b9e03873f88cf4e23cad34c0bb49c1"' in PROBE
    assert 'PIPELINE_RAW_PATH = "banc/nblast/banc-fanc-nblast.R"' in PROBE
    assert 'NBLAST_VERSION = "elastix_tpsreg_240721"' in PROBE


def test_exact_query_and_candidate_are_pinned():
    assert 'TARGET_BANC_ROOT = "720575941508169089"' in PROBE
    assert 'TARGET_BANC_SUPERVOXEL = "77060647762534032"' in PROBE
    assert 'TARGET_FANC_CELL_ID = "20201"' in PROBE
    assert "supervoxel_id_" in PROBE
    assert "root_id_" in PROBE


def test_public_review_and_raw_paths_are_checked():
    assert 'REVIEWED_OBJECT = "nblast/banc_fanc_reviewed_matches.csv"' in PROBE
    assert "nblast/fanc/results" in PROBE
    assert "matching/fanc/results" in PROBE
    assert '"nblast/"' in PROBE


def test_only_same_raw_row_resolves_root():
    assert 'row.get("cell_id", "") == TARGET_FANC_CELL_ID' in PROBE
    assert 'row.get("fanc_match", "")' in PROBE
    assert "resolved_fanc_roots_for_20201" in PROBE


def test_governance_stays_locked():
    assert "validation=false" in PROBE
    for key in (
        '"curated_fanc_to_manc_snpp_bridge_found": False',
        '"exact_polarity_verified": False',
        '"current_calibration_authorized": False',
        '"runtime_stimulation_authorized": False',
    ):
        assert key in PROBE
