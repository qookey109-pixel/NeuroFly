from __future__ import annotations

from neurofly.proprioception_morphology_source_audit import (
    EXPECTED_SOURCE_SHA256,
    EXPECTED_VFB_ID,
    STATUS_DISCOVERY,
    STATUS_REVIEW,
    _candidate_vfb_ids,
    _contains_target_accession,
    _morphology_hints,
    build_report,
)


def test_frozen_vfb_identity_and_source_receipt_are_pinned() -> None:
    assert EXPECTED_VFB_ID == "VFB_jrmc173b"
    assert (
        EXPECTED_SOURCE_SHA256
        == "f1ff278a2c40691987f2de473302fcc259df3ad854f0b8c942eb05c7127067da"
    )


def test_candidate_vfb_ids_are_discovered_recursively() -> None:
    payload = {"results": [{"id": "VFB_alpha"}, {"nested": "term VFB_beta"}]}
    assert _candidate_vfb_ids(payload) == ["VFB_alpha", "VFB_beta"]


def test_target_accession_detection_is_exact() -> None:
    assert _contains_target_accession({"accession": "905407"}) is True
    assert _contains_target_accession({"name": "MaleCNS:905407"}) is True
    assert _contains_target_accession({"accession": "1905407"}) is False


def test_morphology_hints_find_swc_obj_and_skeleton_strings() -> None:
    hints = _morphology_hints(
        {
            "files": [
                "https://example.invalid/a.swc",
                "https://example.invalid/b.obj",
                "skeleton download",
            ]
        }
    )
    values = {item["value"] for item in hints}
    assert "https://example.invalid/a.swc" in values
    assert "https://example.invalid/b.obj" in values
    assert "skeleton download" in values


def test_discovery_without_frozen_identity_fails_closed() -> None:
    search = {"result": {"id": "VFB_target"}}
    info = {
        "VFB_target": {
            "accession": "905407",
            "downloads": ["https://example.invalid/905407.swc"],
        }
    }
    report = build_report(
        search_body=search,
        search_type={},
        term_info_by_id=info,
        expected_vfb_id=None,
        expected_source_sha256=None,
    )
    assert report["matched_vfb_ids"] == ["VFB_target"]
    assert report["status"] == STATUS_DISCOVERY
    assert report["passed"] is False
    assert report["morphology_evidence_present"] is False
    assert report["current_calibration_authorized"] is False


def test_exact_frozen_source_becomes_review_required_not_promotion() -> None:
    search = {"result": {"id": "VFB_target"}}
    info = {
        "VFB_target": {
            "accession": "905407",
            "downloads": ["https://example.invalid/905407.swc"],
        }
    }
    discovery = build_report(
        search_body=search,
        search_type={},
        term_info_by_id=info,
        expected_vfb_id=None,
        expected_source_sha256=None,
    )
    report = build_report(
        search_body=search,
        search_type={},
        term_info_by_id=info,
        expected_vfb_id="VFB_target",
        expected_source_sha256=discovery["source_sha256"],
    )
    assert report["passed"] is True
    assert report["status"] == STATUS_REVIEW
    assert report["morphology_evidence_present"] is True
    assert report["promotion_ready"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False


def test_wrong_or_ambiguous_vfb_identity_fails_closed() -> None:
    search = {"results": [{"id": "VFB_a"}, {"id": "VFB_b"}]}
    info = {
        "VFB_a": {"accession": "905407"},
        "VFB_b": {"bodyId": "905407"},
    }
    report = build_report(
        search_body=search,
        search_type={},
        term_info_by_id=info,
        expected_vfb_id="VFB_a",
        expected_source_sha256="not-the-right-sha",
    )
    assert report["passed"] is False
    assert report["gates"]["exact_one_vfb_match"] is False
