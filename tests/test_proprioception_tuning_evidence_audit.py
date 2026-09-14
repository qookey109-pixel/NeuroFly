from __future__ import annotations

from neurofly.proprioception_tuning_evidence_audit import STATUS_FAIL, STATUS_REVIEW, audit_evidence


def _payload() -> dict:
    return {
        "schema": "neurofly-snpp39-snpp41-tuning-evidence-v0.1",
        "systematic_types": ["SNpp39", "SNpp41"],
        "supported_claims": [
            {"claim": "hook identity", "sources": ["https://example.invalid/source"]}
        ],
        "annotation_conflicts": [{"systematic_type": "SNpp39"}, {"systematic_type": "SNpp41"}],
        "unresolved_claims": [
            {"claim": "SNpp39 flexion versus extension polarity", "status": "unresolved"},
            {"claim": "SNpp41 flexion versus extension polarity", "status": "unresolved"},
        ],
        "forbidden_inferences": [
            "SNpp39=flexion",
            "SNpp39=extension",
            "SNpp41=flexion",
            "SNpp41=extension",
        ],
        "decision": {
            "hook_directional_movement_identity_supported": True,
            "systematic_type_direction_polarity_resolved": False,
            "current_calibration_authorized": False,
            "stimulation_enabled": False,
            "runtime_transduction_enabled": False,
            "promotion_ready": False,
        },
    }


def test_conservative_unresolved_evidence_is_review_required() -> None:
    report = audit_evidence(_payload())
    assert report["passed"] is True
    assert report["status"] == STATUS_REVIEW
    assert report["systematic_type_direction_polarity_resolved"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False


def test_polarity_assignment_without_new_evidence_fails_closed() -> None:
    payload = _payload()
    payload["decision"]["systematic_type_direction_polarity_resolved"] = True
    report = audit_evidence(payload)
    assert report["passed"] is False
    assert report["status"] == STATUS_FAIL
    assert report["gates"]["polarity_explicitly_unresolved"] is False


def test_dropping_forbidden_polarity_mapping_fails_closed() -> None:
    payload = _payload()
    payload["forbidden_inferences"].remove("SNpp41=extension")
    report = audit_evidence(payload)
    assert report["passed"] is False
    assert report["gates"]["all_four_polarity_assignments_forbidden"] is False


def test_enabling_current_or_stimulation_fails_closed() -> None:
    payload = _payload()
    payload["decision"]["current_calibration_authorized"] = True
    assert audit_evidence(payload)["status"] == STATUS_FAIL

    payload = _payload()
    payload["decision"]["stimulation_enabled"] = True
    assert audit_evidence(payload)["status"] == STATUS_FAIL
