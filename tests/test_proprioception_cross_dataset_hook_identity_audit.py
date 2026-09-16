from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.proprioception_cross_dataset_hook_identity_audit import audit


EVIDENCE_PATH = Path("data/proprioception_cross_dataset_hook_identity_v01.json")


def _evidence() -> dict:
    return json.loads(EVIDENCE_PATH.read_text())


def test_cross_dataset_hook_identity_snapshot_passes_without_resolving_polarity() -> None:
    report = audit(_evidence())

    assert report["passed"] is True
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["systematic_hook_identity_supported"] is True
    assert report["direct_crosswalk_found"] is False
    assert report["polarity_resolved"] is False
    assert report["direct_directional_tuning"] == {"SNpp39": None, "SNpp41": None}
    assert report["circuit_consistent_hypotheses"] == {
        "SNpp39": "extension",
        "SNpp41": "flexion",
    }
    assert report["current_calibration_authorized"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["runtime_gating_authorized"] is False
    assert report["neural_payload_eligible"] is False
    assert report["promotion_ready"] is False


def test_banc_snapshot_covers_both_systematic_types_across_all_three_legs() -> None:
    evidence = _evidence()
    records = evidence["records"]

    for systematic_type in ("SNpp39", "SNpp41"):
        legs = {
            record["leg"]
            for record in records
            if record["dataset"] == "BANC_626"
            and record["systematic_type"] == systematic_type
        }
        assert legs == {"front", "middle", "hind"}


def test_both_types_are_present_in_banc_and_malecns_as_hook_classification() -> None:
    evidence = _evidence()
    records = evidence["records"]

    for systematic_type in ("SNpp39", "SNpp41"):
        datasets = {
            record["dataset"]
            for record in records
            if record["systematic_type"] == systematic_type
        }
        assert datasets == {"BANC_626", "MaleCNS_v1.0"}

    assert all(
        record["classification"] == "femoral chordotonal hook neuron"
        for record in records
    )


def test_direct_directional_tuning_cannot_be_inserted_into_identity_evidence() -> None:
    evidence = copy.deepcopy(_evidence())
    evidence["systematic_types"]["SNpp41"]["direct_directional_tuning"] = "flexion"

    report = audit(evidence)

    assert report["passed"] is False
    assert report["status"] == "FAIL"
    assert report["gates"]["direct_directional_tuning_unresolved"] is False


def test_identity_evidence_fails_if_a_record_stops_being_hook_classified() -> None:
    evidence = copy.deepcopy(_evidence())
    evidence["records"][0]["classification"] = "femoral chordotonal claw neuron"

    report = audit(evidence)

    assert report["passed"] is False
    assert report["gates"]["record_contract_exact"] is False


def test_identity_evidence_fails_if_banc_serial_leg_coverage_is_reduced() -> None:
    evidence = copy.deepcopy(_evidence())
    evidence["records"] = [
        record
        for record in evidence["records"]
        if not (
            record["dataset"] == "BANC_626"
            and record["systematic_type"] == "SNpp39"
            and record["leg"] == "middle"
        )
    ]

    report = audit(evidence)

    assert report["passed"] is False
    assert report["gates"]["banc_front_middle_hind_coverage_per_type"] is False


def test_all_runtime_and_promotion_locks_must_remain_closed() -> None:
    for lock in (
        "current_calibration_authorized",
        "stimulation_enabled",
        "runtime_transduction_enabled",
        "runtime_gating_authorized",
        "neural_payload_eligible",
        "promotion_ready",
    ):
        evidence = copy.deepcopy(_evidence())
        evidence[lock] = True
        report = audit(evidence)
        assert report["passed"] is False
