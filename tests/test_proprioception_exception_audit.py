from __future__ import annotations

import copy

import neurofly.proprioception_exception_audit as audit


def _rows() -> list[dict[str, str]]:
    rows = [
        {
            "body_id": str(1000 + index),
            "instance": f"SNpp41_{index}",
            "type": "SNpp41",
            "class": "mechanosensory_proprioceptive",
            "subclass": "chordotonal organ",
            "superclass": "vnc_sensory",
            "soma_side": "L" if index % 2 else "R",
        }
        for index in range(21)
    ]
    rows.append(
        {
            "body_id": "9999",
            "instance": "SNpp41_exception",
            "type": "SNpp41",
            "class": "mechanosensory_proprioceptive",
            "subclass": "leg",
            "superclass": "vnc_sensory",
            "soma_side": "R",
        }
    )
    rows.append(
        {
            "body_id": "2000",
            "instance": "SNpp39_other",
            "type": "SNpp39",
            "class": "mechanosensory_proprioceptive",
            "subclass": "chordotonal organ",
            "superclass": "vnc_sensory",
            "soma_side": "L",
        }
    )
    return rows


def _pinned_shape_rows() -> list[dict[str, str]]:
    rows = _rows()
    rows[21] = {
        "body_id": "905407",
        "instance": "",
        "type": "SNpp41",
        "class": "mechanosensory_proprioceptive",
        "subclass": "leg",
        "superclass": "vnc_sensory",
        "soma_side": "",
    }
    return rows


def test_discovery_mode_can_surface_identity_without_frozen_instance(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_EXCEPTION_IDENTITY", None)
    report = audit.audit_records(_pinned_shape_rows())
    assert report["status"] == "DISCOVERY_REQUIRED"
    assert report["passed"] is False
    assert report["type_rows"] == 22
    assert report["accepted_chordotonal_rows"] == 21
    assert report["exception_leg_rows"] == 1
    assert report["exception_identities"] == [
        {
            "body_id": "905407",
            "instance": "",
            "type": "SNpp41",
            "class": "mechanosensory_proprioceptive",
            "subclass": "leg",
            "superclass": "vnc_sensory",
            "soma_side": "",
        }
    ]
    assert report["gates"]["exception_body_id_present"] is True
    assert report["gates"]["exception_required_taxonomy_present"] is True
    assert report["gates"]["exception_identity_frozen"] is False


def test_real_frozen_blank_identity_reproduces_as_review_required() -> None:
    report = audit.audit_records(_pinned_shape_rows())
    assert report["passed"] is True
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["expected_exception_identity"] == {
        "body_id": "905407",
        "instance": "",
        "type": "SNpp41",
        "class": "mechanosensory_proprioceptive",
        "subclass": "leg",
        "superclass": "vnc_sensory",
        "soma_side": "",
    }
    assert report["blank_instance_frozen"] is True
    assert report["blank_soma_side_frozen"] is True
    assert report["gates"]["exception_identity_matches_frozen_receipt"] is True
    assert report["gates"]["instance_annotation_matches_frozen_receipt"] is True
    assert report["gates"]["soma_side_annotation_matches_frozen_receipt"] is True
    assert report["promotion_ready"] is False
    assert report["stimulation_enabled"] is False
    assert report["current_calibration_authorized"] is False


def test_frozen_nonblank_synthetic_identity_still_supported(monkeypatch) -> None:
    expected = {
        "body_id": "9999",
        "instance": "SNpp41_exception",
        "type": "SNpp41",
        "class": "mechanosensory_proprioceptive",
        "subclass": "leg",
        "superclass": "vnc_sensory",
        "soma_side": "R",
    }
    monkeypatch.setattr(audit, "EXPECTED_EXCEPTION_IDENTITY", expected)
    report = audit.audit_records(_rows())
    assert report["passed"] is True
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["expected_exception_identity"] == expected


def test_changed_body_identity_fails_closed() -> None:
    rows = copy.deepcopy(_pinned_shape_rows())
    rows[21]["body_id"] = "905408"
    report = audit.audit_records(rows)
    assert report["passed"] is False
    assert report["status"] == "FAIL"
    assert report["gates"]["exception_identity_matches_frozen_receipt"] is False


def test_filling_blank_instance_without_evidence_fails_closed() -> None:
    rows = copy.deepcopy(_pinned_shape_rows())
    rows[21]["instance"] = "SNpp41_R"
    report = audit.audit_records(rows)
    assert report["passed"] is False
    assert report["gates"]["instance_annotation_matches_frozen_receipt"] is False


def test_inventing_soma_side_without_evidence_fails_closed() -> None:
    rows = copy.deepcopy(_pinned_shape_rows())
    rows[21]["soma_side"] = "R"
    report = audit.audit_records(rows)
    assert report["passed"] is False
    assert report["gates"]["soma_side_annotation_matches_frozen_receipt"] is False


def test_blank_body_id_is_not_accepted_as_complete_identity() -> None:
    rows = copy.deepcopy(_pinned_shape_rows())
    rows[21]["body_id"] = ""
    report = audit.audit_records(rows)
    assert report["passed"] is False
    assert report["gates"]["exception_body_id_present"] is False


def test_extra_or_missing_exception_fails_structural_gate(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_EXCEPTION_IDENTITY", None)

    missing = [row for row in _pinned_shape_rows() if row.get("subclass") != "leg"]
    missing_report = audit.audit_records(missing)
    assert missing_report["status"] == "FAIL"
    assert missing_report["gates"]["exact_leg_exception_count"] is False

    extra = _pinned_shape_rows() + [
        {
            "body_id": "9997",
            "instance": "",
            "type": "SNpp41",
            "class": "mechanosensory_proprioceptive",
            "subclass": "leg",
            "superclass": "vnc_sensory",
            "soma_side": "",
        }
    ]
    extra_report = audit.audit_records(extra)
    assert extra_report["status"] == "FAIL"
    assert extra_report["gates"]["exact_type_row_count"] is False
    assert extra_report["gates"]["exact_leg_exception_count"] is False


def test_non_target_rows_never_affect_snpp41_receipt(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_EXCEPTION_IDENTITY", None)
    rows = _pinned_shape_rows() + [
        {
            "body_id": "8888",
            "instance": "SNpp58_leg",
            "type": "SNpp58",
            "class": "mechanosensory_proprioceptive",
            "subclass": "leg",
            "superclass": "vnc_sensory",
            "soma_side": "L",
        }
    ]
    report = audit.audit_records(rows)
    assert report["type_rows"] == 22
    assert report["exception_leg_rows"] == 1
    assert report["status"] == "DISCOVERY_REQUIRED"
