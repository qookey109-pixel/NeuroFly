from pathlib import Path

PROBE = Path("scripts/research_probe_fanc_lee_supervoxel_direction_bridge.py").read_text()


def test_sources_are_pinned():
    assert 'PHELPS_COMMIT = "5097916fb0d8a0ca627fe4583575ecd6d4cf1ed9"' in PROBE
    assert 'LEE_COMMIT = "4328b1d5549749f1014c4d73cccc0c5241d98ae4"' in PROBE
    assert 'LEE_TABLE_PATH = "synapse_tables/feco_annotation_table.csv"' in PROBE


def test_exact_svid_is_only_positive_bridge():
    assert 'DECISION_POLICY = "exact_svid_overlap_only_fail_closed"' in PROBE
    assert 'r["pt_supervoxel_id"] in svid_set' in PROBE
    assert '"direction_resolved_by_exact_svid": len(directions) == 1' in PROBE
    assert "Spatial proximity, same-number IDs" in PROBE


def test_all_five_legacy_cells_are_frozen():
    for skid in ("25849", "25842", "25856", "24831", "25909"):
        assert skid in PROBE


def test_no_auto_unlocks():
    for key in (
        '"curated_r21d12_to_specific_fanc_em_identity_found": False',
        '"curated_fanc_to_manc_snpp_bridge_found": False',
        '"exact_polarity_verified": False',
        '"current_calibration_authorized": False',
        '"runtime_stimulation_authorized": False',
        '"privileged_state_bypass_authorized": False',
    ):
        assert key in PROBE


def test_no_morphology_or_nblast_recomputation():
    assert "No morphology/NBLAST recomputation is performed" in PROBE
    assert "type_exclusive_directional_candidate_set_found" in PROBE
