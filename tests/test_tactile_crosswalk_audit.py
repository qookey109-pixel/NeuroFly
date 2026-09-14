from neurofly.tactile_crosswalk_audit import audit_records


def _crosswalk() -> dict:
    return {
        "schema": "neurofly-tactile-leg-functional-crosswalk-v0.1",
        "source_population_class": "mechanosensory_tactile",
        "target_function": "leg_external_touch_candidate",
        "policy": "exact-type-plus-curated-subclass-plus-external-leg-nerve-evidence",
        "accepted_curator_subclasses": ["leg", "mechanosensory bristle"],
        "stimulation_enabled": False,
        "runtime_transduction_enabled": False,
        "mappings": [
            {
                "male_cns_type": "SNta20",
                "functional_class": "leg_external_touch_candidate",
                "stimulation_authorized": False,
                "evidence": [{"kind": "VFB", "url": "https://example.test/20", "claim": "leg nerve"}],
            },
            {
                "male_cns_type": "SNta27",
                "functional_class": "leg_external_touch_candidate",
                "stimulation_authorized": False,
                "evidence": [{"kind": "VFB", "url": "https://example.test/27", "claim": "leg nerve"}],
            },
        ],
    }


def test_exact_leg_and_bristle_rows_are_selected() -> None:
    result = audit_records(
        [
            {"class": "mechanosensory_tactile", "subclass": "leg", "type": "SNta27"},
            {
                "class": "mechanosensory_tactile",
                "subclass": "mechanosensory bristle",
                "type": "SNta20",
            },
            {"class": "mechanosensory_tactile", "subclass": "notum", "type": "SNta03"},
        ],
        _crosswalk(),
    )

    assert result["passed"] is True
    assert result["selected_leg_touch_candidates"] == 2
    assert result["selected_type_counts"] == {"SNta20": 1, "SNta27": 1}
    assert result["evidence_tier_counts"] == {
        "curator_leg_plus_external_nerve": 1,
        "external_leg_nerve_plus_bristle_class": 1,
    }
    assert result["stimulation_enabled"] is False
    assert result["runtime_transduction_enabled"] is False


def test_combined_type_labels_remain_unresolved() -> None:
    result = audit_records(
        [
            {"class": "mechanosensory_tactile", "subclass": "leg", "type": "SNta27"},
            {
                "class": "mechanosensory_tactile",
                "subclass": "mechanosensory bristle",
                "type": "SNta20",
            },
            {
                "class": "mechanosensory_tactile",
                "subclass": "leg",
                "type": "SNta20,SNta29",
            },
            {
                "class": "mechanosensory_tactile",
                "subclass": "leg",
                "type": "SNta27,SNta28",
            },
        ],
        _crosswalk(),
    )

    assert result["passed"] is True
    assert result["selected_leg_touch_candidates"] == 2
    assert result["ambiguous_related_rows_left_unresolved"] == {
        "SNta20,SNta29": 1,
        "SNta27,SNta28": 1,
    }


def test_mapped_type_in_notum_or_wing_fails_closed() -> None:
    result = audit_records(
        [
            {"class": "mechanosensory_tactile", "subclass": "leg", "type": "SNta27"},
            {
                "class": "mechanosensory_tactile",
                "subclass": "mechanosensory bristle",
                "type": "SNta20",
            },
            {"class": "mechanosensory_tactile", "subclass": "notum", "type": "SNta20"},
        ],
        _crosswalk(),
    )

    assert result["passed"] is False
    assert result["disallowed_subclass_rows"] == {"SNta20|notum": 1}
    assert result["gates"]["no_mapped_type_leaks_into_disallowed_subclasses"] is False


def test_same_type_outside_tactile_class_fails_closed() -> None:
    result = audit_records(
        [
            {"class": "mechanosensory_tactile", "subclass": "leg", "type": "SNta27"},
            {
                "class": "mechanosensory_tactile",
                "subclass": "mechanosensory bristle",
                "type": "SNta20",
            },
            {"class": "central", "subclass": "leg", "type": "SNta20"},
        ],
        _crosswalk(),
    )

    assert result["passed"] is False
    assert result["non_tactile_mapped_rows"] == {"SNta20": 1}
    assert result["gates"]["all_selected_rows_are_curated_tactile"] is False


def test_missing_exact_crosswalk_type_fails_closed() -> None:
    result = audit_records(
        [
            {
                "class": "mechanosensory_tactile",
                "subclass": "mechanosensory bristle",
                "type": "SNta20",
            }
        ],
        _crosswalk(),
    )

    assert result["passed"] is False
    assert result["missing_crosswalk_types"] == ["SNta27"]
