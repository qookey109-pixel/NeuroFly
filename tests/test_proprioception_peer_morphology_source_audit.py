from __future__ import annotations

from neurofly.proprioception_peer_morphology_source_audit import (
    PEER_BODY_IDS,
    STATUS_DISCOVERY,
    STATUS_FAIL,
    STATUS_REVIEW,
    _candidate_vfb_ids,
    _contains_body_id,
    _swc_urls,
    audit_inventory,
)


def _complete_records() -> list[dict]:
    return [
        {
            "body_id": body_id,
            "matched_vfb_ids": [f"VFB_peer_{body_id}"],
            "swc_urls": [f"https://example.invalid/{body_id}.swc"],
        }
        for body_id in PEER_BODY_IDS
    ]


def test_frozen_peer_population_matches_connectivity_receipt() -> None:
    assert len(PEER_BODY_IDS) == 21
    assert len(set(PEER_BODY_IDS)) == 21
    assert "905407" not in PEER_BODY_IDS
    assert PEER_BODY_IDS[0] == "807970"
    assert PEER_BODY_IDS[-1] == "936031"


def test_recursive_helpers_find_identity_and_swc_only() -> None:
    payload = {
        "result": {
            "id": "VFB_alpha",
            "crossref": "MaleCNS:807970",
            "files": [
                "https://example.invalid/a.swc",
                "https://example.invalid/a.obj",
            ],
        }
    }
    assert _candidate_vfb_ids(payload) == ["VFB_alpha"]
    assert _contains_body_id(payload, "807970") is True
    assert _contains_body_id(payload, "80797") is False
    assert _swc_urls(payload) == ["https://example.invalid/a.swc"]


def test_complete_unfrozen_inventory_is_discovery_required() -> None:
    report = audit_inventory(_complete_records(), expected_inventory_sha256=None)
    assert report["status"] == STATUS_DISCOVERY
    assert report["passed"] is False
    assert report["unresolved_body_ids"] == []
    assert report["peers_without_swc"] == []
    assert report["peer_morphology_assets_frozen"] is False
    assert report["current_calibration_authorized"] is False


def test_exact_frozen_inventory_is_review_required_not_promotion() -> None:
    discovery = audit_inventory(_complete_records(), expected_inventory_sha256=None)
    report = audit_inventory(
        _complete_records(),
        expected_inventory_sha256=discovery["inventory_sha256"],
    )
    assert report["passed"] is True
    assert report["status"] == STATUS_REVIEW
    assert report["peer_morphology_assets_frozen"] is False
    assert report["peer_morphology_compared"] is False
    assert report["promotion_ready"] is False
    assert report["stimulation_enabled"] is False


def test_ambiguous_identity_or_missing_swc_fails_structurally() -> None:
    records = _complete_records()
    records[0]["matched_vfb_ids"] = ["VFB_a", "VFB_b"]
    report = audit_inventory(records, expected_inventory_sha256=None)
    assert report["status"] == STATUS_FAIL
    assert report["passed"] is False
    assert report["unresolved_body_ids"] == [PEER_BODY_IDS[0]]

    records = _complete_records()
    records[-1]["swc_urls"] = []
    report = audit_inventory(records, expected_inventory_sha256=None)
    assert report["status"] == STATUS_FAIL
    assert report["peers_without_swc"] == [PEER_BODY_IDS[-1]]


def test_population_drift_fails_closed() -> None:
    records = _complete_records()[1:]
    report = audit_inventory(records, expected_inventory_sha256=None)
    assert report["status"] == STATUS_FAIL
    assert report["gates"]["exact_peer_count"] is False
    assert report["gates"]["peer_body_ids_match_frozen_connectivity_receipt"] is False
