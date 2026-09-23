from pathlib import Path

PROBE = Path("scripts/research_probe_2026_fanc_manc_match_table.py").read_text()


def test_2026_author_source_is_pinned():
    assert 'ARTICLE_DOI = "10.1016/j.isci.2026.114902"' in PROBE
    assert 'ARTICLE_PII = "S2589004226002774"' in PROBE
    assert 'ARTICLE_PMCID = "PMC12933626"' in PROBE
    assert 'TABLE_LABEL = "Table S2"' in PROBE


def test_exact_neurofly_targets_are_pinned():
    for token in (
        "97015",
        "SNpp41",
        "20201",
        "648518346481857725",
        "648518346509569667",
        "648518346494933426",
        "648518346514448583",
        "648518346494264434",
    ):
        assert token in PROBE


def test_xlsx_parser_is_standard_library_and_exact():
    assert "zipfile.ZipFile" in PROBE
    assert "xml.etree.ElementTree" in PROBE
    assert 'if rc["value"] == token' in PROBE
    assert "direct_same_row_bridge_candidate_found" in PROBE
    assert "fuzzy" in PROBE.lower()


def test_fetch_or_parse_block_is_fail_closed():
    assert "Fetch/parse blocks are informative fail-closed outcomes" in PROBE
    assert "return 0" in PROBE


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
