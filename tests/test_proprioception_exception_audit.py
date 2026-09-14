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


def test_first_run_is_intentionally_discovery_required(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_EXCEPTION_IDENTITY", None)
    report = audit.audit_records(_rows())
    assert report["status"] == "DISCOVERY_REQUIRED"
    assert report["passed"] is False
    assert report["type_rows"] == 22
    assert report["accepted_chordotonal_rows"] == 21
    assert report["exception_leg_rows"] == 1
    assert report["exception_identities"] == [
        {
            "body_id": "9999",
            "instance": "SNpp41_exception",
            "type": "SNpp41",
            "class": "mechanosensory_proprioceptive",
            "subclass": "leg",
            "superclass": "vnc_sensory",
            "soma_side": "R",
        }
    ]
    assert report["gates"]["exception_identity_frozen"] is False
    assert report["promotion_ready"] is False
    assert report["stimulation_enabled"] is False
    assert report["current_calibration_authorized"] is False


def test_frozen_identity_reproduces_as_review_required(monkeypatch) -> None:
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
    assert report["gates"]["exception_identity_matches_frozen_receipt"] is True
    assert report["promotion_ready"] is False


def test_changed_body_identity_fails_closed(monkeypatch) -> None:
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
    rows = copy.deepcopy(_rows())
    rows[21]["body_id"] = "9998"
    report = audit.audit_records(rows)
    assert report["passed"] is False
    assert report["status"] == "FAIL"
    assert report["gates"]["exception_identity_matches_frozen_receipt"] is False


def test_extra_or_missing_exception_fails_structural_gate(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_EXCEPTION_IDENTITY", None)

    missing = [row for row in _rows() if row.get("subclass") != "leg"]
    missing_report = audit.audit_records(missing)
    assert missing_report["status"] == "FAIL"
    assert missing_report["gates"]["exact_leg_exception_count"] is False

    extra = _rows() + [
        {
            "body_id": "9997",
            "instance": "SNpp41_exception_2",
            "type": "SNpp41",
            "class": "mechanosensory_proprioceptive",
            "subclass": "leg",
            "superclass": "vnc_sensory",
            "soma_side": "L",
        }
    ]
    extra_report = audit.audit_records(extra)
    assert extra_report["status"] == "FAIL"
    assert extra_report["gates"]["exact_type_row_count"] is False
    assert extra_report["gates"]["exact_leg_exception_count"] is False


def test_non_target_rows_never_affect_snpp41_receipt(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_EXCEPTION_IDENTITY", None)
    rows = _rows() + [
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
