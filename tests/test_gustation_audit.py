from neurofly.gustation_audit import audit_records


def test_gustation_audit_uses_curated_class_not_taste_words() -> None:
    result = audit_records(
        [
            {
                "class": "gustatory",
                "subclass": "sugar",
                "nerve": "MxLbN",
                "type": "GRN_sugar_example",
                "instance": "GRN_sugar_example_L",
                "somaSide": "L",
            },
            {
                "class": "central",
                "type": "Sugar SEL PN",
                "instance": "sugar_downstream_R",
                "somaSide": "R",
            },
        ]
    )

    assert result["passed"] is True
    assert result["gustatory_neurons"] == 1
    assert result["subclass_counts"] == {"sugar": 1}
    assert result["nerve_counts"] == {"MxLbN": 1}
    assert result["type_counts"] == {"GRN_sugar_example": 1}
    assert result["stimulation_enabled"] is False


def test_gustation_audit_does_not_guess_without_curated_class() -> None:
    result = audit_records(
        [
            {"class": "central", "type": "Bitter-SEL"},
            {"class": "sensory", "instance": "Gr5a-like"},
        ]
    )

    assert result["passed"] is False
    assert result["gustatory_neurons"] == 0
    assert result["type_counts"] == {}
    assert result["stimulation_enabled"] is False


def test_gustation_audit_accepts_supported_annotation_column_aliases() -> None:
    result = audit_records(
        [
            {
                "cell_class": "GUSTATORY",
                "sub_class": "bitter",
                "nerve_name": "MxLbN",
                "soma_side": "R",
                "super_class": "sensory",
            }
        ]
    )

    assert result["passed"] is True
    assert result["gustatory_neurons"] == 1
    assert result["subclass_counts"] == {"bitter": 1}
    assert result["nerve_counts"] == {"MxLbN": 1}
    assert result["soma_side_counts"] == {"R": 1}
    assert result["superclass_counts"] == {"sensory": 1}
