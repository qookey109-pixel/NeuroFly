from neurofly.mechanosensation_audit import audit_records


def test_audit_passes_for_bilateral_c_and_e_with_curated_sides() -> None:
    result = audit_records(
        [
            {"type": "JO-CA1", "instance": "JO-CA1_L", "somaSide": "L", "predictedNt": "ACh"},
            {"type": "JO-CA1", "instance": "JO-CA1_R", "somaSide": "R", "predictedNt": "ACh"},
            {"type": "JO-EV3", "instance": "JO-EV3_L", "somaSide": "L", "predictedNt": "ACh"},
            {"type": "JO-EV3", "instance": "JO-EV3_R", "somaSide": "R", "predictedNt": "ACh"},
            {"type": "ORN_DM1", "instance": "ORN_DM1_L", "somaSide": "L"},
        ]
    )

    assert result["passed"] is True
    assert result["stimulation_enabled"] is False
    assert result["families"]["JO-C"]["left"] == 1
    assert result["families"]["JO-C"]["right"] == 1
    assert result["families"]["JO-E"]["left"] == 1
    assert result["families"]["JO-E"]["right"] == 1
    assert result["families"]["JO-C"]["types"] == {"JO-CA1": 2}
    assert result["families"]["JO-E"]["types"] == {"JO-EV3": 2}


def test_audit_allows_curated_instance_suffix_fallback() -> None:
    result = audit_records(
        [
            {"type": "JO-CM", "instance": "JO-CM_L", "somaSide": ""},
            {"type": "JO-CM", "instance": "JO-CM_R", "somaSide": None},
            {"type": "JO-EV1", "instance": "JO-EV1_L", "somaSide": ""},
            {"type": "JO-EV1", "instance": "JO-EV1_R", "somaSide": ""},
        ]
    )

    assert result["passed"] is True
    assert result["families"]["JO-C"]["side_sources"] == {"instance_suffix": 2}
    assert result["families"]["JO-E"]["side_sources"] == {"instance_suffix": 2}


def test_audit_fails_if_a_family_is_not_bilateral() -> None:
    result = audit_records(
        [
            {"type": "JO-CA2", "instance": "JO-CA2_L", "somaSide": "L"},
            {"type": "JO-CA2", "instance": "JO-CA2_R", "somaSide": "R"},
            {"type": "JO-ED2_b", "instance": "JO-ED2_b_L", "somaSide": "L"},
        ]
    )

    assert result["passed"] is False
    e_gate = next(item for item in result["gates"] if item["family"] == "JO-E")
    assert e_gate["right_nonempty"] is False
    assert e_gate["passed"] is False


def test_audit_fails_on_unresolved_candidate_side() -> None:
    result = audit_records(
        [
            {"type": "JO-CA1", "instance": "JO-CA1_L", "somaSide": "L"},
            {"type": "JO-CA1", "instance": "JO-CA1_R", "somaSide": "R"},
            {"type": "JO-CA2", "instance": "JO-CA2_unknown", "somaSide": ""},
            {"type": "JO-EV3", "instance": "JO-EV3_L", "somaSide": "L"},
            {"type": "JO-EV3", "instance": "JO-EV3_R", "somaSide": "R"},
        ]
    )

    assert result["passed"] is False
    assert result["families"]["JO-C"]["unresolved"] == 1
    c_gate = next(item for item in result["gates"] if item["family"] == "JO-C")
    assert c_gate["all_candidates_lateralized"] is False


def test_non_jo_c_e_types_are_ignored() -> None:
    result = audit_records(
        [
            {"type": "JO-AA", "instance": "JO-AA_L", "somaSide": "L"},
            {"type": "JO-BA", "instance": "JO-BA_R", "somaSide": "R"},
        ]
    )

    assert result["records_scanned"] == 2
    assert result["families"]["JO-C"]["total"] == 0
    assert result["families"]["JO-E"]["total"] == 0
    assert result["passed"] is False
