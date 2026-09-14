from __future__ import annotations

import copy

import pytest

import neurofly.proprioception_nblast_audit as audit


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
            "body_id": str(1000 + i),
            "type": audit.TARGET_TYPE,
            "class": audit.TARGET_CLASS,
            "subclass": audit.PEER_SUBCLASS,
            "superclass": "vnc_sensory",
            "instance": f"peer-{i}",
            "soma_side": "R",
        }
        for i in range(audit.EXPECTED_PEER_COUNT)
    ]


def _ids() -> list[str]:
    return [audit.TARGET_BODY_ID, *[row["body_id"] for row in _peers()]]


def _sources() -> dict[str, dict]:
    return {
        body_id: {
            "object_name": f"{audit.REGISTERED_PREFIX}{body_id}.swc",
            "generation": "123",
            "size_bytes": 100,
            "gcs_md5_base64": "",
            "gcs_crc32c_base64": "",
            "sha256": f"{index + 1:064x}"[-64:],
        }
        for index, body_id in enumerate(_ids())
    }


def _variants_and_best() -> tuple[dict, dict]:
    ids = _ids()
    variants = {}
    for variant_index, name in enumerate(("oo", "om", "mo", "mm")):
        variants[name] = {}
        for q_index, query in enumerate(ids):
            variants[name][query] = {}
            for t_index, target in enumerate(ids):
                if query == target:
                    score = 1.0
                else:
                    score = 0.25 + (q_index + t_index) / 200.0 + variant_index / 100.0
                variants[name][query][target] = round(score, 9)
    best = audit._best_pair_scores(ids, variants)
    return variants, best


def _package_versions() -> dict[str, str]:
    return {"navis": audit.NAVIS_VERSION, "flybrains": audit.FLYBRAINS_VERSION}


def test_registered_object_selection_requires_exact_single_body_stem() -> None:
    items = [
        {"name": f"{audit.REGISTERED_PREFIX}905407.swc"},
        {"name": f"{audit.REGISTERED_PREFIX}9054070.swc"},
    ]
    selected = audit.select_registered_object("905407", items)
    assert selected["name"].endswith("/905407.swc")


def test_registered_object_selection_fails_on_ambiguity() -> None:
    items = [
        {"name": f"{audit.REGISTERED_PREFIX}905407.swc"},
        {"name": f"{audit.REGISTERED_PREFIX}905407.txt"},
    ]
    with pytest.raises(RuntimeError, match="exactly one registered skeleton"):
        audit.select_registered_object("905407", items)


def test_describe_scores_reports_target_and_peer_distribution() -> None:
    _, best = _variants_and_best()
    peers = [row["body_id"] for row in _peers()]
    result = audit.describe_scores(
        target_body_id=audit.TARGET_BODY_ID,
        peer_body_ids=peers,
        pair_scores=best,
    )
    assert len(result["target_vs_peers"]) == audit.EXPECTED_PEER_COUNT
    assert len(result["peer_leave_one_out_medians"]) == audit.EXPECTED_PEER_COUNT
    assert 0.0 <= result["peer_baseline"]["target_percentile_among_peer_medians"] <= 100.0


def test_discovery_mode_is_structurally_valid_but_not_passed(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_NBLAST_SHA256", None)
    variants, best = _variants_and_best()
    result = audit.audit_nblast(
        target_record=_target(),
        peer_records=_peers(),
        sources=_sources(),
        scoremat_sha256="a" * 64,
        package_versions=_package_versions(),
        score_variants=variants,
        pair_scores=best,
    )
    assert result["status"] == "DISCOVERY_REQUIRED"
    assert result["passed"] is False
    assert result["registered_morphology_evidence_present"] is True
    assert result["current_calibration_authorized"] is False
    assert result["direction_tuning_resolved"] is False
    assert result["gates"]["nblast_receipt_frozen"] is False


def test_exact_frozen_receipt_is_review_required_only(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_NBLAST_SHA256", None)
    variants, best = _variants_and_best()
    discovery = audit.audit_nblast(
        target_record=_target(),
        peer_records=_peers(),
        sources=_sources(),
        scoremat_sha256="b" * 64,
        package_versions=_package_versions(),
        score_variants=variants,
        pair_scores=best,
    )
    monkeypatch.setattr(audit, "EXPECTED_NBLAST_SHA256", discovery["nblast_sha256"])
    frozen = audit.audit_nblast(
        target_record=_target(),
        peer_records=_peers(),
        sources=_sources(),
        scoremat_sha256="b" * 64,
        package_versions=_package_versions(),
        score_variants=variants,
        pair_scores=best,
    )
    assert frozen["passed"] is True
    assert frozen["status"] == "REVIEW_REQUIRED"
    assert frozen["promotion_ready"] is False
    assert frozen["stimulation_enabled"] is False
    assert frozen["runtime_transduction_enabled"] is False
    assert frozen["current_calibration_authorized"] is False


def test_one_score_change_breaks_frozen_receipt(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_NBLAST_SHA256", None)
    variants, best = _variants_and_best()
    discovery = audit.audit_nblast(
        target_record=_target(),
        peer_records=_peers(),
        sources=_sources(),
        scoremat_sha256="c" * 64,
        package_versions=_package_versions(),
        score_variants=variants,
        pair_scores=best,
    )
    monkeypatch.setattr(audit, "EXPECTED_NBLAST_SHA256", discovery["nblast_sha256"])
    changed_variants = copy.deepcopy(variants)
    changed_best = copy.deepcopy(best)
    peer = _peers()[0]["body_id"]
    changed_variants["mm"][audit.TARGET_BODY_ID][peer] += 0.001
    changed_best[audit.TARGET_BODY_ID][peer] += 0.001
    result = audit.audit_nblast(
        target_record=_target(),
        peer_records=_peers(),
        sources=_sources(),
        scoremat_sha256="c" * 64,
        package_versions=_package_versions(),
        score_variants=changed_variants,
        pair_scores=changed_best,
    )
    assert result["passed"] is False
    assert result["status"] == "FAIL"
    assert result["gates"]["nblast_receipt_matches"] is False


def test_wrong_package_version_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_NBLAST_SHA256", None)
    variants, best = _variants_and_best()
    versions = _package_versions()
    versions["navis"] = "999.0"
    result = audit.audit_nblast(
        target_record=_target(),
        peer_records=_peers(),
        sources=_sources(),
        scoremat_sha256="d" * 64,
        package_versions=versions,
        score_variants=variants,
        pair_scores=best,
    )
    assert result["status"] == "FAIL"
    assert result["gates"]["exact_navis_version"] is False
