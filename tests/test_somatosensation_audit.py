from neurofly.somatosensation_audit import audit_records


def test_somatosensation_audit_requires_exact_curated_classes() -> None:
    result = audit_records(
        [
            {
                "class": "mechanosensory_tactile",
                "subclass": "mechanosensory bristle",
                "type": "SNta07",
                "instance": "SNta07_L",
                "somaSide": "L",
                "superclass": "vnc_sensory",
            },
            {
                "class": "mechanosensory_proprioceptive",
                "subclass": "chordotonal organ",
                "type": "SNpp40",
                "instance": "SNpp40_R",
                "somaSide": "R",
                "superclass": "vnc_sensory",
            },
            {
                "class": "central",
                "subclass": "chordotonal-like downstream",
                "type": "fake club interneuron",
            },
        ]
    )

    assert result["passed"] is True
    assert result["modality_counts"] == {"tactile": 1, "proprioception": 1}
    assert result["target_neurons_total"] == 2
    assert result["subclass_counts"]["tactile"] == {"mechanosensory bristle": 1}
    assert result["subclass_counts"]["proprioception"] == {"chordotonal organ": 1}
    assert result["type_counts"]["tactile"] == {"SNta07": 1}
    assert result["type_counts"]["proprioception"] == {"SNpp40": 1}
    assert result["stimulation_enabled"] is False
    assert result["runtime_transduction_enabled"] is False


def test_somatosensation_audit_does_not_promote_descriptive_words() -> None:
    result = audit_records(
        [
            {"class": "central", "type": "club proprioceptive relay"},
            {"class": "sensory", "subclass": "mechanosensory bristle"},
            {"class": "gustatory", "instance": "tactile-looking-name"},
        ]
    )

    assert result["passed"] is False
    assert result["modality_counts"] == {"tactile": 0, "proprioception": 0}
    assert result["target_neurons_total"] == 0
    assert result["type_counts"]["tactile"] == {}
    assert result["type_counts"]["proprioception"] == {}


def test_broad_mechanosensory_class_is_context_only() -> None:
    result = audit_records(
        [
            {
                "class": "mechanosensory",
                "type": "JO-C",
                "instance": "JO-C_R",
                "somaSide": "R",
            },
            {
                "class": "mechanosensory_tactile",
                "type": "SNta04",
            },
            {
                "class": "mechanosensory_proprioceptive",
                "type": "SNpp51",
            },
        ]
    )

    assert result["passed"] is True
    assert result["context_only_class_counts"] == {"mechanosensory": 1}
    assert result["target_neurons_total"] == 2
    assert result["existing_jo_ce_routing_modified"] is False


def test_somatosensation_audit_accepts_supported_column_aliases() -> None:
    result = audit_records(
        [
            {
                "cell_class": "MECHANOSENSORY_TACTILE",
                "sub_class": "mechanosensory bristle",
                "nerve_name": "ADMN",
                "soma_side": "L",
                "super_class": "vnc_sensory",
            },
            {
                "cellClass": "mechanosensory_proprioceptive",
                "subclass": "campaniform sensillum",
                "nerveName": "LegN",
                "somaSide": "R",
                "superclass": "sensory_ascending",
            },
        ]
    )

    assert result["passed"] is True
    assert result["modality_counts"] == {"tactile": 1, "proprioception": 1}
    assert result["nerve_counts"]["tactile"] == {"ADMN": 1}
    assert result["nerve_counts"]["proprioception"] == {"LegN": 1}
    assert result["soma_side_counts"]["tactile"] == {"L": 1}
    assert result["soma_side_counts"]["proprioception"] == {"R": 1}
