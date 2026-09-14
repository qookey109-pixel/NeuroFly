from __future__ import annotations

from neurofly.proprioception_peer_morphology_protocol import (
    FEATURE_NAMES,
    STATUS_DISCOVERY,
    STATUS_FAIL,
    STATUS_REVIEW,
    audit_protocol,
    build_protocol,
)
from neurofly.proprioception_peer_swc_asset_audit import PEER_ASSETS


def _stats(index: int) -> dict:
    node_count = 180 + index * 7
    branch_points = 8 + (index % 9)
    terminal_nodes = branch_points + 1
    cable_length = 110.0 + index * 6.5
    return {
        "node_count": node_count,
        "root_count": 1,
        "terminal_nodes": terminal_nodes,
        "branch_points": branch_points,
        "cable_length": cable_length,
        "bbox": {
            "x_min": 0.0,
            "x_max": 20.0 + index * 0.3,
            "y_min": 0.0,
            "y_max": 30.0 + index * 0.4,
            "z_min": 0.0,
            "z_max": 10.0 + index * 0.2,
        },
        "node_type_counts": {"0": node_count - branch_points - terminal_nodes, "5": branch_points, "6": terminal_nodes},
    }


def _records() -> list[dict]:
    return [
        {"body_id": body_id, "vfb_id": vfb_id, "swc_url": url, "stats": _stats(index)}
        for index, (body_id, vfb_id, url) in enumerate(PEER_ASSETS)
    ]


def test_protocol_uses_exact_predeclared_features_and_peer_only_population() -> None:
    protocol = build_protocol(_records())
    assert protocol["feature_names"] == list(FEATURE_NAMES)
    assert len(protocol["peers"]) == 21
    assert "905407" not in [row["body_id"] for row in protocol["peers"]]
    assert protocol["peer_envelope"]["threshold"] == max(
        row["nearest_peer_distance"] for row in protocol["peers"]
    )


def test_protocol_is_translation_free_for_bbox_origin() -> None:
    records = _records()
    first = build_protocol(records)
    shifted = _records()
    for record in shifted:
        bbox = record["stats"]["bbox"]
        bbox["x_min"] += 1000.0
        bbox["x_max"] += 1000.0
        bbox["y_min"] -= 500.0
        bbox["y_max"] -= 500.0
    second = build_protocol(shifted)
    assert first == second


def test_unfrozen_valid_protocol_is_discovery_required() -> None:
    protocol = build_protocol(_records())
    report = audit_protocol(protocol, expected_protocol_receipt_sha256=None)
    assert report["status"] == STATUS_DISCOVERY
    assert report["passed"] is False
    assert report["target_morphology_compared"] is False
    assert report["current_calibration_authorized"] is False


def test_exact_frozen_protocol_is_review_required_not_promotion() -> None:
    protocol = build_protocol(_records())
    discovery = audit_protocol(protocol, expected_protocol_receipt_sha256=None)
    report = audit_protocol(
        protocol,
        expected_protocol_receipt_sha256=discovery["protocol_receipt_sha256"],
    )
    assert report["status"] == STATUS_REVIEW
    assert report["passed"] is True
    assert report["promotion_ready"] is False
    assert report["stimulation_enabled"] is False


def test_population_drift_fails_closed() -> None:
    protocol = build_protocol(_records())
    protocol["peers"] = protocol["peers"][1:]
    report = audit_protocol(protocol, expected_protocol_receipt_sha256=None)
    assert report["status"] == STATUS_FAIL
    assert report["gates"]["exact_peer_count"] is False


def test_threshold_tampering_fails_closed() -> None:
    protocol = build_protocol(_records())
    protocol["peer_envelope"]["threshold"] += 0.01
    report = audit_protocol(protocol, expected_protocol_receipt_sha256=None)
    assert report["status"] == STATUS_FAIL
    assert report["gates"]["threshold_is_peer_only_max_loo_nearest_neighbor"] is False
