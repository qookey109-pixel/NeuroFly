from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.proprioception_curated_identity_provenance_audit import audit


EVIDENCE = Path("data/proprioception_curated_identity_provenance_gate_v01.json")


def _payload() -> dict:
    return json.loads(EVIDENCE.read_text())


def test_curated_identity_provenance_gate_passes_only_as_review_required() -> None:
    report = audit(_payload())

    assert report["passed"] is True
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["provenance_state"] == "AUTHENTICATED_CURATED_SOURCE_REQUIRED"
    assert report["direct_crosswalk_found"] is False
    assert report["polarity_resolved"] is False
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["runtime_gating_authorized"] is False
    assert report["neural_payload_eligible"] is False
    assert report["promotion_ready"] is False


def test_public_open_data_is_not_allowed_to_become_identity_authority() -> None:
    payload = _payload()
    payload["neuronbridge_open_data"][
        "computed_or_precomputed_morphology_is_identity_authority"
    ] = True

    report = audit(payload)
    assert report["passed"] is False
    assert report["gates"]["computed_morphology_not_identity_authority"] is False


def test_curated_endpoint_must_remain_jwt_protected_in_this_snapshot() -> None:
    payload = _payload()
    payload["neuronbridge_curated_service"]["jwt_authorizer_required"] = False

    report = audit(payload)
    assert report["passed"] is False
    assert report["gates"]["curated_jwt_required"] is False


def test_claiming_a_curated_result_requires_a_new_frozen_receipt_stage() -> None:
    payload = _payload()
    payload["neuronbridge_curated_service"]["direct_query_result_obtained"] = True

    report = audit(payload)
    assert report["passed"] is False
    assert report["gates"]["curated_direct_result_not_obtained"] is False


def test_archive_access_cannot_be_silently_claimed() -> None:
    payload = _payload()
    payload["neuronbridge_annotation_archive"]["public_readability_verified"] = True
    payload["neuronbridge_annotation_archive"][
        "exact_hook_driver_archive_object_obtained"
    ] = True

    report = audit(payload)
    assert report["passed"] is False
    assert report["gates"]["archive_public_read_not_claimed"] is False
    assert report["gates"]["archive_exact_driver_object_absent"] is False


def test_directional_identity_remains_inferential_only() -> None:
    payload = _payload()
    assert payload["systematic_types"]["SNpp39"]["direct_directional_tuning"] is None
    assert payload["systematic_types"]["SNpp41"]["direct_directional_tuning"] is None
    assert payload["systematic_types"]["SNpp39"]["circuit_consistent_hypothesis"] == "extension"
    assert payload["systematic_types"]["SNpp41"]["circuit_consistent_hypothesis"] == "flexion"

    contaminated = copy.deepcopy(payload)
    contaminated["systematic_types"]["SNpp39"]["direct_directional_tuning"] = "extension"
    report = audit(contaminated)
    assert report["passed"] is False
    assert report["gates"]["systematic_hypotheses_preserved"] is False


def test_runtime_and_promotion_locks_fail_closed() -> None:
    for field in (
        "direct_crosswalk_found",
        "polarity_resolved",
        "current_calibration_authorized",
        "stimulation_enabled",
        "runtime_transduction_enabled",
        "runtime_gating_authorized",
        "neural_payload_eligible",
        "promotion_ready",
    ):
        payload = _payload()
        payload[field] = True
        assert audit(payload)["passed"] is False, field


def test_authorization_bypass_is_explicitly_forbidden() -> None:
    payload = _payload()
    assert payload["provenance_conclusion"]["login_or_authorization_bypass_permitted"] is False

    payload["provenance_conclusion"]["login_or_authorization_bypass_permitted"] = True
    report = audit(payload)
    assert report["passed"] is False
    assert report["gates"]["authorization_bypass_forbidden"] is False
