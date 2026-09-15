from __future__ import annotations

import json
from pathlib import Path

from neurofly.proprioception_hook_direction_evidence_audit import audit


EVIDENCE = Path("data/proprioception_hook_direction_evidence_v01.json")


def _payload():
    return json.loads(EVIDENCE.read_text())


def test_current_evidence_passes_but_remains_review_required():
    report = audit(_payload())
    assert report["passed"] is True
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["direct_crosswalk_found"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["promotion_ready"] is False


def test_direct_tuning_claim_without_direct_crosswalk_fails_closed():
    payload = _payload()
    payload["systematic_types"]["SNpp41"]["direct_directional_tuning"] = "flexion"
    report = audit(payload)
    assert report["passed"] is False
    assert report["status"] == "FAIL"


def test_authorizing_current_fails_closed():
    payload = _payload()
    payload["current_calibration_authorized"] = True
    assert audit(payload)["passed"] is False


def test_hypothesis_polarity_is_pinned():
    payload = _payload()
    payload["systematic_types"]["SNpp39"]["circuit_consistent_hypothesis"] = "flexion"
    assert audit(payload)["passed"] is False


def test_missing_evidence_link_fails_closed():
    payload = _payload()
    payload["systematic_types"]["SNpp41"]["evidence"] = []
    assert audit(payload)["passed"] is False
