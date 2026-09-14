from __future__ import annotations

import copy

import pytest

import neurofly.proprioception_morphology_audit as audit


def _swc() -> bytes:
    return b"""# synthetic tree\n1 1 0 0 0 1 -1\n2 3 10 0 0 1 1\n3 3 20 0 0 1 2\n4 3 10 10 0 1 2\n5 3 10 20 0 1 4\n"""


def _target() -> dict[str, str]:
    return {
        "body_id": audit.TARGET_BODY_ID,
        "type": audit.TARGET_TYPE,
        "class": audit.TARGET_CLASS,
        "subclass": audit.TARGET_SUBCLASS,
        "superclass": "vnc_sensory",
        "instance": "",
        "soma_side": "",
    }


def _peers() -> list[dict[str, str]]:
    return [
        {
            "body_id": str(1000 + index),
            "type": audit.TARGET_TYPE,
            "class": audit.TARGET_CLASS,
            "subclass": audit.PEER_SUBCLASS,
            "superclass": "vnc_sensory",
            "instance": f"peer-{index}",
            "soma_side": "R",
        }
        for index in range(audit.EXPECTED_PEER_COUNT)
    ]


def _summaries() -> dict[str, dict]:
    base = audit.parse_swc(_swc())
    output = {audit.TARGET_BODY_ID: copy.deepcopy(base)}
    for index, peer in enumerate(_peers()):
        item = copy.deepcopy(base)
        item["node_count"] += index
        item["edge_count"] += index
        item["leaf_count"] += index % 3
        item["branchpoint_count"] += index % 2
        item["cable_length_um"] += float(index)
        item["bbox_span_um"]["x"] += float(index)
        item["bbox_span_um"]["y"] += float(index) / 2.0
        item["bbox_span_um"]["z"] += float(index) / 3.0
        item["swc_sha256"] = f"{index + 1:064x}"[-64:]
        output[peer["body_id"]] = item
    return output


def test_parse_swc_geometry_metrics() -> None:
    summary = audit.parse_swc(_swc())
    assert summary["node_count"] == 5
    assert summary["edge_count"] == 4
    assert summary["root_count"] == 1
    assert summary["leaf_count"] == 2
    assert summary["branchpoint_count"] == 1
    assert summary["cable_length_um"] == pytest.approx(0.32)
    assert summary["bbox_span_um"] == {"x": 0.16, "y": 0.16, "z": 0.0}
    assert len(summary["swc_sha256"]) == 64


def test_parse_swc_rejects_missing_parent() -> None:
    bad = b"1 1 0 0 0 1 -1\n2 3 1 0 0 1 99\n"
    with pytest.raises(ValueError, match="missing parent"):
        audit.parse_swc(bad)


def test_discovery_mode_is_structurally_valid_but_not_passed(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_MORPHOLOGY_SHA256", None)
    result = audit.audit_morphology(
        target_record=_target(),
        peer_records=_peers(),
        summaries=_summaries(),
    )
    assert result["status"] == "DISCOVERY_REQUIRED"
    assert result["passed"] is False
    assert result["morphology_evidence_present"] is True
    assert result["promotion_ready"] is False
    assert result["current_calibration_authorized"] is False
    assert result["direction_tuning_resolved"] is False
    assert result["gates"]["morphology_receipt_frozen"] is False


def test_frozen_exact_receipt_is_review_required_only(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_MORPHOLOGY_SHA256", None)
    discovery = audit.audit_morphology(
        target_record=_target(),
        peer_records=_peers(),
        summaries=_summaries(),
    )
    monkeypatch.setattr(
        audit,
        "EXPECTED_MORPHOLOGY_SHA256",
        discovery["morphology_sha256"],
    )
    frozen = audit.audit_morphology(
        target_record=_target(),
        peer_records=_peers(),
        summaries=_summaries(),
    )
    assert frozen["passed"] is True
    assert frozen["status"] == "REVIEW_REQUIRED"
    assert frozen["promotion_ready"] is False
    assert frozen["stimulation_enabled"] is False
    assert frozen["runtime_transduction_enabled"] is False
    assert frozen["current_calibration_authorized"] is False


def test_one_geometry_change_breaks_frozen_receipt(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_MORPHOLOGY_SHA256", None)
    summaries = _summaries()
    discovery = audit.audit_morphology(
        target_record=_target(),
        peer_records=_peers(),
        summaries=summaries,
    )
    monkeypatch.setattr(
        audit,
        "EXPECTED_MORPHOLOGY_SHA256",
        discovery["morphology_sha256"],
    )
    changed = copy.deepcopy(summaries)
    changed[audit.TARGET_BODY_ID]["cable_length_um"] += 0.001
    result = audit.audit_morphology(
        target_record=_target(),
        peer_records=_peers(),
        summaries=changed,
    )
    assert result["passed"] is False
    assert result["status"] == "FAIL"
    assert result["gates"]["morphology_receipt_matches"] is False


def test_wrong_target_taxonomy_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_MORPHOLOGY_SHA256", None)
    target = _target()
    target["subclass"] = audit.PEER_SUBCLASS
    result = audit.audit_morphology(
        target_record=target,
        peer_records=_peers(),
        summaries=_summaries(),
    )
    assert result["status"] == "FAIL"
    assert result["gates"]["target_subclass_is_leg"] is False
