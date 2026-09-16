from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data" / "proprioception_temporal_wiring_evidence_v01.json"


def _load() -> dict[str, object]:
    payload = json.loads(EVIDENCE.read_text())
    assert isinstance(payload, dict)
    return payload


def test_temporal_wiring_evidence_keeps_all_runtime_locks_closed() -> None:
    payload = _load()

    assert payload["schema"] == "neurofly-proprioception-temporal-wiring-evidence-v0.1"
    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["direct_snpp39_snpp41_direction_crosswalk_found"] is False
    assert payload["systematic_type_mapping_exposed"] is False
    assert payload["current_calibration_authorized"] is False
    assert payload["stimulation_enabled"] is False
    assert payload["runtime_transduction_enabled"] is False
    assert payload["neural_payload_eligible"] is False


def test_temporal_wiring_evidence_keeps_history_human_only() -> None:
    payload = _load()
    observability = payload["observability"]
    assert isinstance(observability, dict)

    assert observability == {
        "receptor_history_capacity": 36,
        "source": "verified-neural-handoff-receptor-domain",
        "persistent": False,
        "records_world_state": False,
        "records_motor_command": False,
        "records_reward": False,
        "records_systematic_type": False,
    }


def test_snpp_polarity_remains_inference_not_direct_tuning() -> None:
    payload = _load()
    boundary = payload["polarity_boundary"]
    assert isinstance(boundary, dict)

    snpp39 = boundary["SNpp39"]
    snpp41 = boundary["SNpp41"]
    assert isinstance(snpp39, dict)
    assert isinstance(snpp41, dict)

    assert snpp39["direct_directional_tuning"] is None
    assert snpp41["direct_directional_tuning"] is None
    assert snpp39["candidate_direction"] == "extension"
    assert snpp41["candidate_direction"] == "flexion"
    assert snpp39["candidate_evidence_level"] == "PHYSIOLOGY_SUPPORTED_INFERENCE"
    assert snpp41["candidate_evidence_level"] == "PHYSIOLOGY_SUPPORTED_INFERENCE"


def test_connectivity_evidence_cannot_silently_become_execution_authority() -> None:
    payload = _load()
    encoded = json.dumps(payload, sort_keys=True)

    assert "DIRECT_CONNECTIVITY" in encoded
    assert "DIRECT_DATABASE_ANNOTATION" in encoded
    assert "PHYSIOLOGY_SUPPORTED_INFERENCE" in encoded
    assert "promotion_rule" in encoded

    for forbidden in (
        '"current_calibration_authorized": true',
        '"stimulation_enabled": true',
        '"runtime_transduction_enabled": true',
        '"neural_payload_eligible": true',
        '"systematic_type_mapping_exposed": true',
    ):
        assert forbidden not in encoded
