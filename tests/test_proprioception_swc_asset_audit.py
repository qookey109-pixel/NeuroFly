from __future__ import annotations

import pytest

from neurofly.proprioception_swc_asset_audit import (
    STATUS_DISCOVERY,
    STATUS_REVIEW,
    _parse_swc,
    _stats,
    build_report,
)


SYNTHETIC_SWC = b"""# test skeleton\n1 1 0 0 0 1 -1\n2 3 1 0 0 0.5 1\n3 3 2 0 0 0.5 2\n4 3 1 1 0 0.5 1\n"""


def test_parse_and_stats_are_deterministic() -> None:
    nodes = _parse_swc(SYNTHETIC_SWC)
    stats = _stats(nodes)
    assert stats["node_count"] == 4
    assert stats["root_count"] == 1
    assert stats["terminal_nodes"] == 2
    assert stats["branch_points"] == 1
    assert stats["cable_length"] == 3.0
    assert stats["node_type_counts"] == {"1": 1, "3": 3}


def test_discovery_without_frozen_hashes_fails_closed() -> None:
    report = build_report(
        SYNTHETIC_SWC,
        expected_swc_sha256=None,
        expected_stats_sha256=None,
    )
    assert report["status"] == STATUS_DISCOVERY
    assert report["passed"] is False
    assert report["morphology_asset_verified"] is False
    assert report["current_calibration_authorized"] is False


def test_exact_frozen_asset_is_review_required_not_promotion() -> None:
    discovery = build_report(
        SYNTHETIC_SWC,
        expected_swc_sha256=None,
        expected_stats_sha256=None,
    )
    report = build_report(
        SYNTHETIC_SWC,
        expected_swc_sha256=discovery["swc_sha256"],
        expected_stats_sha256=discovery["stats_sha256"],
    )
    assert report["passed"] is True
    assert report["status"] == STATUS_REVIEW
    assert report["morphology_asset_verified"] is True
    assert report["peer_morphology_compared"] is False
    assert report["promotion_ready"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False


def test_one_byte_change_fails_frozen_asset_gate() -> None:
    discovery = build_report(
        SYNTHETIC_SWC,
        expected_swc_sha256=None,
        expected_stats_sha256=None,
    )
    modified = SYNTHETIC_SWC + b"# changed\n"
    report = build_report(
        modified,
        expected_swc_sha256=discovery["swc_sha256"],
        expected_stats_sha256=discovery["stats_sha256"],
    )
    assert report["passed"] is False
    assert report["gates"]["swc_sha_matches"] is False


def test_missing_parent_and_duplicate_node_fail_closed() -> None:
    with pytest.raises(ValueError, match="missing parent"):
        _parse_swc(b"1 1 0 0 0 1 -1\n2 3 1 0 0 1 99\n")
    with pytest.raises(ValueError, match="Duplicate"):
        _parse_swc(b"1 1 0 0 0 1 -1\n1 3 1 0 0 1 -1\n")
