from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data" / "proprioception_temporal_gating_evidence_v01.json"


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text())


def test_temporal_gating_evidence_remains_human_only_and_non_executable() -> None:
    evidence = _evidence()

    assert evidence["schema"] == "neurofly-proprioception-temporal-gating-evidence-v0.1"
    assert evidence["status"] == "REVIEW_REQUIRED"
    assert evidence["runtime_gating_authorized"] is False
    assert evidence["phase_kernel_authorized"] is False
    assert evidence["current_calibration_authorized"] is False
    assert evidence["stimulation_enabled"] is False
    assert evidence["systematic_type_mapping_exposed"] is False
    assert evidence["neural_payload_eligible"] is False


def test_hook_class_predictive_inhibition_does_not_resolve_snpp_polarity() -> None:
    evidence = _evidence()
    boundary = evidence["identity_boundary"]

    assert boundary["hook_class_modulation_supported"] is True
    assert boundary["SNpp39_directional_tuning_direct"] is None
    assert boundary["SNpp41_directional_tuning_direct"] is None
    assert boundary["SNpp39_candidate_direction"] == "extension"
    assert boundary["SNpp41_candidate_direction"] == "flexion"
    assert boundary["candidate_evidence_level"] == "PHYSIOLOGY_SUPPORTED_INFERENCE"
    assert boundary["direct_type_level_polarity_crosswalk_found"] is False
    assert "must not be used to promote" in boundary["rule"]


def test_phase_and_lead_time_remain_explicitly_unresolved() -> None:
    evidence = _evidence()
    boundary = evidence["temporal_resolution_boundary"]

    assert boundary["evidence_level"] == "DIRECT_AUTHOR_LIMITATION"
    assert boundary["phase_of_step_cycle_resolved"] is False
    assert boundary["inhibitory_lead_time_resolved"] is False
    assert boundary["millisecond_kernel_resolved"] is False
    assert "voltage imaging" in boundary["claim"]


def test_evidence_separates_allowed_analysis_from_forbidden_runtime_promotion() -> None:
    evidence = _evidence()
    allowed = "\n".join(evidence["allowed_human_only_analysis"])
    forbidden = "\n".join(evidence["forbidden_promotions"])

    assert "receptor pulse onset and offset" in allowed
    assert "decision-index units" in allowed
    assert "millisecond inhibitory kernel" in forbidden
    assert "SNpp39 or SNpp41" in forbidden
    assert "motor command or world truth" in forbidden
    assert "temporal correlation as neuron identity evidence" in forbidden


def test_primary_sources_cover_hook_physiology_connectivity_and_malecns_context() -> None:
    evidence = _evidence()
    sources = {
        item["source"]
        for group in ("hook_class_evidence", "malecns_context")
        for item in evidence[group]
    }

    assert "https://www.nature.com/articles/s41586-025-09554-2" in sources
    assert "https://www.nature.com/articles/s41467-025-59302-3" in sources
    assert "https://elifesciences.org/reviewed-preprints/97766" in sources
