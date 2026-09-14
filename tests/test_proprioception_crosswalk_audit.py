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
            "subclass": "leg",
            "superclass": "vnc_sensory",
            "type": "SNpp41",
            "instance": "SNpp41_mixed_annotation",
        },
        {
            "class": "mechanosensory_proprioceptive",
            "subclass": "campaniform sensilla",
            "superclass": "vnc_sensory",
            "type": "other",
            "instance": "other",
        },
    ]


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "crosswalk.json"
    path.write_text(json.dumps(payload))
    return path


def test_v03_crosswalk_records_hook_pair_as_review_not_promotion() -> None:
    payload = load_crosswalk(CROSSWALK)
    assert payload["schema"] == "neurofly-proprioception-feco-functional-crosswalk-v0.3"
    assert payload["promotion_status"] == "review_required"
    assert payload["promotion_ready"] is False
    assert payload["stimulation_enabled"] is False
    assert payload["runtime_transduction_enabled"] is False
    assert payload["directional_hook_identity_resolved"] is False
    assert payload["current_calibration_authorized"] is False
    assert payload["expected_annotation_exceptions"] == [
        {
            "male_cns_type": "SNpp41",
            "class": "mechanosensory_proprioceptive",
            "subclass": "leg",
            "count": 1,
            "disposition": "review_required_not_selected_not_stimulated",
        }
    ]
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
    statuses = {item["male_cns_type"]: item["mapping_status"] for item in payload["mappings"]}
    assert statuses["SNpp41"] == "review_required_mixed_subclass"
    assert statuses["SNpp39"] == "clean_candidate"


def test_exact_mixed_subclass_receipt_yields_review_required_audit() -> None:
    report = audit_records(_rows(), _crosswalk())
    assert report["passed"] is True
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["promotion_status"] == "review_required"
    assert report["promotion_ready"] is False
    assert report["selected_feco_candidates"] == 5
    assert report["clean_selected_candidates"] == 4
    assert report["review_required_selected_candidates"] == 1
    assert report["selected_function_counts"] == {
        "feco_club_bidirectional_motion_vibration_candidate": 3,
        "feco_hook_motion_direction_candidate": 2,
    }
    assert report["observed_annotation_exceptions"] == {"SNpp41|leg": 1}
    assert report["expected_annotation_exceptions"] == {"SNpp41|leg": 1}
    assert report["hook_types"] == ["SNpp39", "SNpp41"]
    assert report["hook_direction_identity"] == {
        "SNpp39": "unresolved",
        "SNpp41": "unresolved",
    }
    assert report["directional_hook_identity_resolved"] is False
    assert report["current_calibration_authorized"] is False
    assert report["gates"]["annotation_exceptions_match_pinned_receipt"] is True
    assert report["gates"]["complete_hook_pair_present_for_review"] is True
    assert report["gates"]["hook_direction_identity_remains_unresolved"] is True
    assert report["gates"]["promotion_remains_review_required"] is True
    assert report["gates"]["current_calibration_remains_blocked"] is True


def test_missing_pinned_exception_fails_closed() -> None:
    rows = [row for row in _rows() if row["subclass"] != "leg"]
    report = audit_records(rows, _crosswalk())
    assert report["passed"] is False
    assert report["observed_annotation_exceptions"] == {}
    assert report["gates"]["annotation_exceptions_match_pinned_receipt"] is False


def test_unexpected_extra_subclass_collision_fails_closed() -> None:
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
    assert report["observed_annotation_exceptions"] == {
        "SNpp41|leg": 1,
        "SNpp58|hair plate": 1,
    }


def test_same_name_non_proprioceptive_collision_still_fails_closed() -> None:
    rows = _rows() + [
        {
            "class": "unknown_sensory",
            "subclass": "chordotonal organ",
            "superclass": "vnc_sensory",
            "type": "SNpp41",
            "instance": "class-collision",
        }
    ]
    report = audit_records(rows, _crosswalk())
    assert report["passed"] is False
    assert report["non_proprioceptive_mapped_rows"] == {"SNpp41": 1}


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
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["ambiguous_related_rows_left_unresolved"] == {"SNpp39,SNpp41": 1}


def test_v03_cannot_claim_promotion_ready(tmp_path: Path) -> None:
    payload = copy.deepcopy(_crosswalk())
    payload["promotion_ready"] = True
    with pytest.raises(ValueError, match="must not be promotion ready"):
        load_crosswalk(_write(tmp_path, payload))


def test_v03_cannot_erase_or_change_pinned_exception(tmp_path: Path) -> None:
    payload = copy.deepcopy(_crosswalk())
    payload["expected_annotation_exceptions"][0]["count"] = 0
    with pytest.raises(ValueError, match="exception receipt drifted"):
        load_crosswalk(_write(tmp_path, payload))


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


def test_v03_cannot_promote_snpp41_mapping_status(tmp_path: Path) -> None:
    payload = copy.deepcopy(_crosswalk())
    for mapping in payload["mappings"]:
        if mapping["male_cns_type"] == "SNpp41":
            mapping["mapping_status"] = "clean_candidate"
    with pytest.raises(ValueError, match="mapping status drifted for SNpp41"):
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
