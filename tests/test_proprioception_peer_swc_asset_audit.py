from __future__ import annotations

from copy import deepcopy

from neurofly.proprioception_peer_swc_asset_audit import (
    PEER_ASSETS,
    STATUS_DISCOVERY,
    STATUS_FAIL,
    STATUS_REVIEW,
    audit_records,
    build_asset_record,
)


SIMPLE_SWC = b"""# simple rooted tree\n1 1 0 0 0 1 -1\n2 5 1 0 0 1 1\n3 6 1 1 0 1 2\n4 6 2 1 0 1 2\n"""


def _complete_records() -> list[dict]:
    return [
        build_asset_record(body_id, vfb_id, swc_url, SIMPLE_SWC)
        for body_id, vfb_id, swc_url in PEER_ASSETS
    ]


def test_frozen_peer_asset_population_is_exact_and_excludes_target() -> None:
    body_ids = [body_id for body_id, _vfb_id, _url in PEER_ASSETS]
    assert len(body_ids) == 21
    assert len(set(body_ids)) == 21
    assert "905407" not in body_ids


def test_build_asset_record_uses_shared_swc_statistics() -> None:
    body_id, vfb_id, swc_url = PEER_ASSETS[0]
    record = build_asset_record(body_id, vfb_id, swc_url, SIMPLE_SWC)
    assert record["stats"]["node_count"] == 4
    assert record["stats"]["root_count"] == 1
    assert record["stats"]["branch_points"] == 1
    assert record["stats"]["terminal_nodes"] == 2
    assert len(record["swc_sha256"]) == 64
    assert len(record["stats_sha256"]) == 64


def test_complete_unfrozen_cohort_is_discovery_required() -> None:
    report = audit_records(_complete_records(), expected_cohort_receipt_sha256=None)
    assert report["status"] == STATUS_DISCOVERY
    assert report["passed"] is False
    assert report["peer_count"] == 21
    assert report["peer_swc_assets_frozen"] is False
    assert report["current_calibration_authorized"] is False


def test_exact_frozen_cohort_is_review_required_not_promotion() -> None:
    records = _complete_records()
    discovery = audit_records(records, expected_cohort_receipt_sha256=None)
    report = audit_records(
        records,
        expected_cohort_receipt_sha256=discovery["cohort_receipt_sha256"],
    )
    assert report["status"] == STATUS_REVIEW
    assert report["passed"] is True
    assert report["peer_swc_assets_frozen"] is True
    assert report["peer_morphology_compared"] is False
    assert report["promotion_ready"] is False
    assert report["stimulation_enabled"] is False


def test_source_identity_drift_fails_closed() -> None:
    records = _complete_records()
    records[0]["vfb_id"] = "VFB_wrong"
    report = audit_records(records, expected_cohort_receipt_sha256=None)
    assert report["status"] == STATUS_FAIL
    assert report["gates"]["vfb_identity_and_swc_urls_match_frozen_inventory"] is False


def test_stats_receipt_tamper_fails_closed() -> None:
    records = deepcopy(_complete_records())
    records[0]["stats"]["node_count"] += 1
    report = audit_records(records, expected_cohort_receipt_sha256=None)
    assert report["status"] == STATUS_FAIL
    assert report["gates"]["all_stats_receipts_self_consistent"] is False


def test_population_drift_fails_closed() -> None:
    report = audit_records(_complete_records()[1:], expected_cohort_receipt_sha256=None)
    assert report["status"] == STATUS_FAIL
    assert report["gates"]["exact_peer_count"] is False
    assert report["gates"]["peer_body_ids_match_frozen_source_inventory"] is False
