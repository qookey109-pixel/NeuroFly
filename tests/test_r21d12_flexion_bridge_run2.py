import json
from pathlib import Path


ANALYSIS = Path("data/r21d12_flexion_bridge_run2_analysis.json")


def test_run2_preserves_bidirectional_artifact_provenance() -> None:
    payload = json.loads(ANALYSIS.read_text())
    workflow = payload["workflow"]

    assert workflow["run_id"] == 35446074417
    assert workflow["result"] == "success"
    assert workflow["artifact_digest"] == (
        "sha256:0e8c329cfbac91572878bf59ebfe6e8cf73494f57d2f52170392d3c4b62534e2"
    )


def test_r21d12_is_the_resolved_neuronbridge_accession() -> None:
    payload = json.loads(ANALYSIS.read_text())
    source = payload["source_identity"]
    nb = payload["neuronbridge"]

    assert source["functional_driver"] == "GMR21D12-GAL4"
    assert source["neuronbridge_accession"] == "R21D12"
    assert source["functional_polarity"] == "hook_flexion"
    assert nb["direct_line_lookup_http_status"] == 200
    assert nb["direct_line_lookup_result_count"] == 81


def test_snpp41_911942_is_strongest_in_both_search_directions() -> None:
    payload = json.loads(ANALYSIS.read_text())
    forward = payload["forward_body_to_line_best_hits"]
    reverse = payload["reverse_line_to_body_best_hits"]

    assert forward["SNpp41:911942"]["rank"] == 2
    assert forward["SNpp41:911942"]["rank"] < forward["SNpp39:810041"]["rank"]
    assert forward["SNpp41:911942"]["rank"] < forward["SNpp39:913886"]["rank"]

    assert reverse["SNpp41:911942"]["rank"] == 6
    assert reverse["SNpp41:911942"]["rank"] < reverse["SNpp39:810041"]["rank"]
    assert reverse["SNpp41:911942"]["rank"] < reverse["SNpp39:913886"]["rank"]


def test_bridge_is_not_type_exclusive_and_is_segment_confounded() -> None:
    payload = json.loads(ANALYSIS.read_text())
    interpretation = payload["interpretation"]
    sampling = payload["body_sampling_context"]

    assert interpretation["bridge_is_type_exclusive"] is False
    assert interpretation["bridge_is_curated_identity"] is False
    assert sampling["segment_balanced_for_type_inference"] is False


def test_strong_r21d12_evidence_does_not_unlock_exact_polarity() -> None:
    payload = json.loads(ANALYSIS.read_text())
    interpretation = payload["interpretation"]
    governance = payload["governance"]

    assert interpretation["SNpp41_flexion_candidate_strengthened"] is True
    assert interpretation["computed_morphology_is_sufficient_for_exact_polarity"] is False
    assert governance["direct_type_to_polarity_source_found"] is False
    assert governance["snpp39_snpp41_polarity_resolved"] is False
    assert governance["exact_polarity_verified"] is False
    assert governance["current_calibration_authorized"] is False
    assert governance["runtime_stimulation_authorized"] is False
    assert governance["privileged_state_bypass_authorized"] is False
