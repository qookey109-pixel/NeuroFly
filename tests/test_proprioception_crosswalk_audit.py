from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from neurofly.proprioception_crosswalk_audit import audit_records, load_crosswalk


ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "data" / "proprioception_feco_functional_crosswalk_v03.json"


def _crosswalk() -> dict:
    return json.loads(CROSSWALK.read_text())


def _rows() -> list[dict[str, str]]:
    return [
        {
            "class": "mechanosensory_proprioceptive",
            "subclass": "chordotonal organ",
            "superclass": "vnc_sensory",
            "type": neuron_type,
            "instance": f"{neuron_type}_L",
        }
        for neuron_type in ("SNpp39", "SNpp41", "SNpp58", "SNpp59", "SNpp60")
    ] + [
        {
            "class": "mechanosensory_proprioceptive",
            "subclass": "campaniform sensilla",
            "superclass": "vnc_sensory",
            "type": "other",
            "instance": "other",
        }
    ]


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "crosswalk.json"
    path.write_text(json.dumps(payload))
    return path


def test_v03_crosswalk_contains_complete_hook_pair_but_no_direction_identity() -> None:
    payload = load_crosswalk(CROSSWALK)
    assert payload["schema"] == "neurofly-proprioception-feco-functional-crosswalk-v0.3"
    assert payload["stimulation_enabled"] is False
    assert payload["runtime_transduction_enabled"] is False
    assert payload["directional_hook_identity_resolved"] is False
    assert payload["current_calibration_authorized"] is False
    assert [item["male_cns_type"] for item in payload["mappings"]] == [
        "SNpp39",
        "SNpp41",
        "SNpp58",
        "SNpp59",
        "SNpp60",
    ]
    hooks = {
        item["male_cns_type"]: item["hook_direction_identity"]
        for item in payload["mappings"]
        if item["functional_class"] == "feco_hook_motion_direction_candidate"
    }
    assert hooks == {"SNpp39": "unresolved", "SNpp41": "unresolved"}


def test_clean_v03_population_passes_only_as_evidence_gate() -> None:
    report = audit_records(_rows(), _crosswalk())
    assert report["passed"] is True
    assert report["selected_feco_candidates"] == 5
    assert report["selected_function_counts"] == {
        "feco_club_bidirectional_motion_vibration_candidate": 3,
        "feco_hook_motion_direction_candidate": 2,
    }
    assert report["hook_types"] == ["SNpp39", "SNpp41"]
    assert report["hook_direction_identity"] == {
        "SNpp39": "unresolved",
        "SNpp41": "unresolved",
    }
    assert report["directional_hook_identity_resolved"] is False
    assert report["current_calibration_authorized"] is False
    assert report["gates"]["complete_hook_pair_present"] is True
    assert report["gates"]["hook_direction_identity_remains_unresolved"] is True
    assert report["gates"]["current_calibration_remains_blocked"] is True
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False


def test_missing_second_hook_type_fails_closed() -> None:
    rows = [row for row in _rows() if row["type"] != "SNpp41"]
    report = audit_records(rows, _crosswalk())
    assert report["passed"] is False
    assert report["missing_crosswalk_types"] == ["SNpp41"]


def test_same_name_non_proprioceptive_collision_fails_closed() -> None:
    rows = _rows() + [
        {
            "class": "unknown_sensory",
            "subclass": "chordotonal organ",
            "superclass": "vnc_sensory",
            "type": "SNpp39",
            "instance": "collision",
        }
    ]
    report = audit_records(rows, _crosswalk())
    assert report["passed"] is False
    assert report["non_proprioceptive_mapped_rows"] == {"SNpp39": 1}


def test_mapped_type_in_wrong_subclass_fails_closed() -> None:
    rows = _rows() + [
        {
            "class": "mechanosensory_proprioceptive",
            "subclass": "hair plate",
            "superclass": "vnc_sensory",
            "type": "SNpp58",
            "instance": "wrong-subclass",
        }
    ]
    report = audit_records(rows, _crosswalk())
    assert report["passed"] is False
    assert report["disallowed_subclass_rows"] == {"SNpp58|hair plate": 1}


def test_combined_labels_are_never_split_or_promoted() -> None:
    rows = _rows() + [
        {
            "class": "mechanosensory_proprioceptive",
            "subclass": "chordotonal organ",
            "superclass": "vnc_sensory",
            "type": "SNpp39,SNpp41",
            "instance": "ambiguous",
        }
    ]
    report = audit_records(rows, _crosswalk())
    assert report["passed"] is True
    assert report["ambiguous_related_rows_left_unresolved"] == {
        "SNpp39,SNpp41": 1
    }


def test_v03_cannot_claim_hook_direction_is_resolved(tmp_path: Path) -> None:
    payload = copy.deepcopy(_crosswalk())
    payload["directional_hook_identity_resolved"] = True
    with pytest.raises(ValueError, match="directional hook identity unresolved"):
        load_crosswalk(_write(tmp_path, payload))


@pytest.mark.parametrize("direction", ["extension", "flexion"])
def test_v03_cannot_assign_extension_or_flexion_to_type(
    tmp_path: Path, direction: str
) -> None:
    payload = copy.deepcopy(_crosswalk())
    payload["mappings"][0]["hook_direction_identity"] = direction
    with pytest.raises(ValueError, match="extension/flexion identity unresolved"):
        load_crosswalk(_write(tmp_path, payload))


def test_v03_cannot_authorize_current_calibration(tmp_path: Path) -> None:
    payload = copy.deepcopy(_crosswalk())
    payload["current_calibration_authorized"] = True
    with pytest.raises(ValueError, match="must not authorize current calibration"):
        load_crosswalk(_write(tmp_path, payload))


def test_crosswalk_cannot_enable_stimulation_or_runtime(tmp_path: Path) -> None:
    payload = copy.deepcopy(_crosswalk())
    payload["runtime_transduction_enabled"] = True
    with pytest.raises(ValueError, match="runtime transduction"):
        load_crosswalk(_write(tmp_path, payload))
