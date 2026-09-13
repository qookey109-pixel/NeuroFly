import json

import pytest

from neurofly.gustation_crosswalk_audit import audit_records, load_crosswalk


def _crosswalk() -> dict[str, object]:
    return {
        "schema": "neurofly-gustation-functional-crosswalk-v0.1",
        "stimulation_enabled": False,
        "policy": "explicit-curated-cross-dataset-evidence-only",
        "mappings": [
            {
                "male_cns_type": "LB1b",
                "functional_class": "bitter",
                "stimulation_authorized": False,
                "evidence": [{"kind": "vfb", "url": "https://example.test/lb1b"}],
            },
            {
                "male_cns_type": "LB3a",
                "functional_class": "sugar_water",
                "stimulation_authorized": False,
                "evidence": [{"kind": "vfb", "url": "https://example.test/lb3a"}],
            },
        ],
    }


def test_crosswalk_audit_maps_only_exact_curated_types() -> None:
    report = audit_records(
        [
            {"class": "gustatory", "type": "LB1b"},
            {"class": "gustatory", "type": "LB1b"},
            {"class": "gustatory", "type": "LB3a"},
            {"class": "gustatory", "type": "LB1a"},
            {"class": "central", "type": "LB3a-like"},
        ],
        _crosswalk(),
    )

    assert report["passed"] is True
    assert report["gustatory_neurons_total"] == 4
    assert report["mapped_neurons"] == 3
    assert report["unresolved_gustatory_neurons"] == 1
    assert report["mapped_type_counts"] == {"LB1b": 2, "LB3a": 1}
    assert report["functional_class_counts"] == {"bitter": 2, "sugar_water": 1}
    assert report["stimulation_enabled"] is False


def test_crosswalk_audit_fails_if_a_mapping_is_missing_from_dataset() -> None:
    report = audit_records(
        [{"class": "gustatory", "type": "LB1b"}],
        _crosswalk(),
    )

    assert report["passed"] is False
    assert report["missing_crosswalk_types"] == ["LB3a"]


def test_crosswalk_audit_fails_if_mapped_type_occurs_outside_gustatory_class() -> None:
    report = audit_records(
        [
            {"class": "gustatory", "type": "LB1b"},
            {"class": "central", "type": "LB1b"},
            {"class": "gustatory", "type": "LB3a"},
        ],
        _crosswalk(),
    )

    assert report["passed"] is False
    assert report["non_gustatory_mapped_rows"] == {"LB1b": 1}


def test_load_crosswalk_rejects_stimulation_authorization(tmp_path) -> None:
    payload = _crosswalk()
    payload["mappings"][0]["stimulation_authorized"] = True
    path = tmp_path / "crosswalk.json"
    path.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="must not authorize stimulation"):
        load_crosswalk(path)


def test_load_crosswalk_rejects_duplicate_types(tmp_path) -> None:
    payload = _crosswalk()
    payload["mappings"].append(dict(payload["mappings"][0]))
    path = tmp_path / "crosswalk.json"
    path.write_text(json.dumps(payload))

    with pytest.raises(ValueError, match="Duplicate MaleCNS type"):
        load_crosswalk(path)
