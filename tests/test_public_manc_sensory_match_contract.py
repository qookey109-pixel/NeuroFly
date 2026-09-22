from pathlib import Path

PROBE = Path("scripts/research_probe_public_manc_sensory_matches.py").read_text()


def test_author_public_source_is_pinned():
    assert 'PIPELINE_COMMIT = "5c333c12f0b9e03873f88cf4e23cad34c0bb49c1"' in PROBE
    assert "2024-09-02_manc_sensory_matches.csv" in PROBE
    assert "lee-lab_brain-and-nerve-cord-fly-connectome" in PROBE


def test_exact_targets_are_frozen():
    assert 'TARGET_MANC_BODY = "97015"' in PROBE
    assert 'TARGET_TYPE = "SNpp41"' in PROBE
    assert 'TARGET_FANC_CELL_ID = "20201"' in PROBE
    for root in (
        "648518346481857725",
        "648518346509569667",
        "648518346494933426",
        "648518346514448583",
        "648518346494264434",
    ):
        assert root in PROBE


def test_same_row_exact_match_is_required():
    assert "same_row_manc_to_cell_id" in PROBE
    assert "same_row_manc_to_current_root" in PROBE
    assert "same_row_type_to_current_root" in PROBE
    assert "Only exact token co-occurrence" in PROBE


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
