from pathlib import Path

PROBE = Path("scripts/research_probe_banc_snpp_fanc_coverage.py").read_text()


def test_banc_source_and_targets_are_pinned():
    assert 'BANC_COMMIT = "e31a2e26b9937dca72e5ca1c1960df6454d76114"' in PROBE
    assert 'TARGET_BANC_ROOT = "720575941508169089"' in PROBE
    assert 'TARGET_MANC_BODY = "97015"' in PROBE
    assert 'TARGET_MALECNS_BODY = "911942"' in PROBE
    assert 'TARGET_TYPES = {"SNpp39", "SNpp41"}' in PROBE


def test_csv_dialect_is_detected_not_tab_assumed():
    assert "csv.Sniffer().sniff" in PROBE
    assert 'delimiters=",\\t;"' in PROBE
    assert 'delimiter = ","' in PROBE


def test_same_row_bridge_rule_is_strict():
    assert "exact_same_row_bridge" in PROBE
    assert 'r.get("cell_type") == "SNpp41"' in PROBE
    assert 'r.get("cell_sub_class") == TARGET_SUBCLASS' in PROBE
    assert 'r.get("manc_match") == TARGET_MANC_BODY' in PROBE
    assert 'r.get("malecns_match") == TARGET_MALECNS_BODY' in PROBE
    assert 'nonmissing(r.get("fanc_match"))' in PROBE


def test_other_segment_matches_are_context_only():
    assert "not transferred across legs/sides by type name" in PROBE
    assert "other_snpp_fanc_context" in PROBE


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


def test_curated_fanc_nblast_join_is_exact_and_validated():
    assert "FANC_NBLAST_URL" in PROBE
    assert "audit_fanc_nblast" in PROBE
    assert 'pair = (qroot, mid)' in PROBE
    assert 'if pair not in wanted' in PROBE
    assert '"nblast_validation": truthy(row.get("validation"))' in PROBE
    assert "replicated_directional_type_crosswalk_candidate_found" in PROBE


def test_directional_candidate_requires_replication_and_opposite_hook_labels():
    assert 'validated_exact_join_count"] >= 2' in PROBE
    assert 'labels39 != labels41' in PROBE
    assert '{"hook_ext", "hook_flx"}' in PROBE


def test_cross_type_fanc_match_ambiguity_is_reported():
    assert "cross_type_fanc_match_ids" in PROBE
    assert "cross_type_fanc_match_id_count" in PROBE
    assert "cross_type_fanc_match_ambiguity_found" in PROBE
