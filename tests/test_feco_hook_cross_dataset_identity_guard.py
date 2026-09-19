import json
from pathlib import Path


AUDIT = Path("data/feco_hook_cross_dataset_identity_guard_v01.json")


def test_same_snpp_label_is_not_cross_dataset_identity() -> None:
    payload = json.loads(AUDIT.read_text())
    interpretation = payload["interpretation"]

    assert interpretation["same_systematic_type_name_is_sufficient_cross_dataset_identity"] is False
    assert interpretation["manc_to_malecns_type_name_equivalence_is_safe_for_polarity"] is False


def test_malecns_examples_are_hook_but_manc_counterexamples_are_not_uniform() -> None:
    payload = json.loads(AUDIT.read_text())

    assert {
        row["type"]: row["classification"]
        for row in payload["current_malecns_examples"]
    } == {
        "SNpp39": "femoral chordotonal hook neuron",
        "SNpp41": "femoral chordotonal hook neuron",
    }

    classes = {
        (row["systematic_type"], row["classification"])
        for row in payload["manc_counterexamples"]
    }
    assert ("SNpp39", "femoral chordotonal club neuron") in classes
    assert ("SNpp41", "femoral chordotonal claw neuron") in classes


def test_neuronbridge_body_level_bridge_is_required_before_unlock() -> None:
    payload = json.loads(AUDIT.read_text())
    route = payload["neuronbridge_route"]
    governance = payload["governance"]

    assert route["male_cns_collection_available"] is True
    assert route["manc_collection_available"] is True
    assert route["open_data_api_documented"] is True
    assert route["direct_driver_to_current_malecns_snpp_match_audited"] is False
    assert governance["body_level_mapping_required"] is True
    assert governance["cross_dataset_same_name_inference_authorized"] is False


def test_candidate_crosswalk_is_not_promoted() -> None:
    payload = json.loads(AUDIT.read_text())
    candidate = payload["existing_candidate_crosswalk"]
    governance = payload["governance"]

    assert candidate["SNpp39"] == "hook_extension_candidate"
    assert candidate["SNpp41"] == "hook_flexion_candidate"
    assert candidate["status"] == "unchanged_candidate_only"

    assert governance["direct_type_to_polarity_source_found"] is False
    assert governance["snpp39_snpp41_polarity_resolved"] is False
    assert governance["exact_polarity_verified"] is False
    assert governance["current_calibration_authorized"] is False
    assert governance["runtime_stimulation_authorized"] is False
    assert governance["privileged_state_bypass_authorized"] is False
