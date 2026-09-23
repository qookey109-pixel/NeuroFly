from pathlib import Path

PROBE = Path("scripts/research_probe_feco_motor_sign_concordance.py").read_text()


def test_sources_are_pinned():
    assert 'LEE_COMMIT = "4328b1d5549749f1014c4d73cccc0c5241d98ae4"' in PROBE
    assert 'LESSER_COMMIT = "93cafa55b8bbdb1493e8d73c941035969349b223"' in PROBE
    assert 'FROZEN_MANC_RECEIPT = Path("data/feco_hook_polarity_crosscheck_v01.json")' in PROBE


def test_directional_module_categories_are_explicit():
    assert 'EXTENSOR_MODULE = "preferred_module_tibia_ex_sensory.json"' in PROBE
    assert '"preferred_module_tibia_ta_flex_A_sensory.json"' in PROBE
    assert "no_crossed_tibia_preference" in PROBE
    assert "dominant_opposed_tibia_preference" in PROBE


def test_five_phelps_roots_are_exactly_pinned():
    for root in (
        "648518346481857725",
        "648518346509569667",
        "648518346494933426",
        "648518346514448583",
        "648518346494264434",
    ):
        assert root in PROBE


def test_no_curated_identity_or_unlock_is_created():
    assert '"curated_cross_connectome_identity_found": False' in PROBE
    assert '"automatic_unlock_performed": False' in PROBE
    for key in (
        '"curated_fanc_to_manc_snpp_bridge_found": False',
        '"exact_polarity_verified": False',
        '"snpp39_snpp41_polarity_resolved": False',
        '"current_calibration_authorized": False',
        '"runtime_stimulation_authorized": False',
        '"privileged_state_bypass_authorized": False',
    ):
        assert key in PROBE
