from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from neurofly.proprioception_crosswalk_audit import audit_records, load_crosswalk


ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "data" / "proprioception_feco_functional_crosswalk_v01.json"


def _crosswalk() -> dict:
    return json.loads(CROSSWALK.read_text())


def _rows() -> list[dict[str, str]]:
    functions = {item["male_cns_type"]: item["functional_class"] for item in _crosswalk()["mappings"]}
    del functions
    return [
        {"class": "mechanosensory_proprioceptive", "subclass": "chordotonal organ", "superclass": "vnc_sensory", "type": neuron_type, "instance": f"{neuron_type}_L"}
        for neuron_type in ("SNpp39", "SNpp40", "SNpp50", "SNpp51", "SNpp58", "SNpp59", "SNpp60")
    ] + [
        {"class": "mechanosensory_proprioceptive", "subclass": "campaniform sensilla", "superclass": "vnc_sensory", "type": "other", "instance": "other"}
    ]


def test_crosswalk_is_exact_read_only_evidence_ledger() -> None:
    payload = load_crosswalk(CROSSWALK)
    assert payload["stimulation_enabled"] is False
    assert payload["runtime_transduction_enabled"] is False
    assert payload["accepted_curator_subclasses"] == ["chordotonal organ"]
    assert [item["male_cns_type"] for item in payload["mappings"]] == [
        "SNpp39", "SNpp40", "SNpp50", "SNpp51", "SNpp58", "SNpp59", "SNpp60"
    ]
    assert {item["functional_class"] for item in payload["mappings"]} == {
        "feco_hook_motion_direction_candidate",
        "feco_claw_tibia_position_candidate",
        "feco_club_bidirectional_motion_vibration_candidate",
    }


def test_clean_exact_population_passes_without_authorizing_runtime() -> None:
    report = audit_records(_rows(), _crosswalk())
    assert report["passed"] is True
    assert report["selected_feco_candidates"] == 7
    assert report["selected_function_counts"] == {
        "feco_claw_tibia_position_candidate": 2,
        "feco_club_bidirectional_motion_vibration_candidate": 4,
        "feco_hook_motion_direction_candidate": 1,
    }
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False


def test_same_name_non_proprioceptive_collision_fails_closed() -> None:
    rows = _rows() + [
        {"class": "unknown_sensory", "subclass": "chordotonal organ", "superclass": "vnc_sensory", "type": "SNpp40", "instance": "collision"}
    ]
    report = audit_records(rows, _crosswalk())
    assert report["passed"] is False
    assert report["non_proprioceptive_mapped_rows"] == {"SNpp40": 1}


def test_mapped_type_in_wrong_subclass_fails_closed() -> None:
    rows = _rows() + [
        {"class": "mechanosensory_proprioceptive", "subclass": "hair plate", "superclass": "vnc_sensory", "type": "SNpp50", "instance": "wrong-subclass"}
    ]
    report = audit_records(rows, _crosswalk())
    assert report["passed"] is False
    assert report["disallowed_subclass_rows"] == {"SNpp50|hair plate": 1}


def test_combined_labels_are_never_split_or_promoted() -> None:
    rows = _rows() + [
        {"class": "mechanosensory_proprioceptive", "subclass": "chordotonal organ", "superclass": "vnc_sensory", "type": "SNpp39,SNpp40", "instance": "ambiguous"}
    ]
    report = audit_records(rows, _crosswalk())
    assert report["passed"] is True
    assert report["selected_feco_candidates"] == 7
    assert report["ambiguous_related_rows_left_unresolved"] == {"SNpp39,SNpp40": 1}


def test_missing_type_fails_closed() -> None:
    rows = [row for row in _rows() if row["type"] != "SNpp60"]
    report = audit_records(rows, _crosswalk())
    assert report["passed"] is False
    assert report["missing_crosswalk_types"] == ["SNpp60"]


def test_crosswalk_cannot_enable_stimulation_or_runtime(tmp_path: Path) -> None:
    payload = copy.deepcopy(_crosswalk())
    payload["runtime_transduction_enabled"] = True
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="runtime transduction"):
        load_crosswalk(path)
