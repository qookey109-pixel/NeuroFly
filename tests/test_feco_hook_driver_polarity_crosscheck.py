import json
from pathlib import Path


DRIVER_CROSSCHECK = Path("data/feco_hook_driver_polarity_crosscheck_v01.json")
CIRCUIT_CROSSCHECK = Path("data/feco_hook_polarity_crosscheck_v01.json")


def test_functional_driver_polarity_is_verified_without_type_promotion() -> None:
    payload = json.loads(DRIVER_CROSSCHECK.read_text())
    governance = payload["governance"]

    assert governance["functional_driver_polarity_verified"] is True
    assert governance["direct_type_to_polarity_source_found"] is False
    assert governance["snpp39_snpp41_polarity_resolved"] is False
    assert governance["exact_polarity_verified"] is False
    assert governance["current_calibration_authorized"] is False
    assert governance["runtime_stimulation_authorized"] is False
    assert governance["privileged_state_bypass_authorized"] is False


def test_driver_crosscheck_preserves_pr113_candidate_only_mapping() -> None:
    driver = json.loads(DRIVER_CROSSCHECK.read_text())
    circuit = json.loads(CIRCUIT_CROSSCHECK.read_text())

    expected = {
        "SNpp39": "hook_extension_candidate",
        "SNpp41": "hook_flexion_candidate",
    }

    assert driver["existing_candidate_crosswalk"]["status"] == "unchanged_candidate_only"
    assert {
        key: driver["existing_candidate_crosswalk"][key]
        for key in ("SNpp39", "SNpp41")
    } == expected
    assert circuit["circuit_consistency_inference"]["candidate_crosswalk"] == expected


def test_no_unaudited_cross_dataset_bridge_is_promoted() -> None:
    payload = json.loads(DRIVER_CROSSCHECK.read_text())
    bridge = payload["cross_dataset_bridge"]

    assert bridge["explicit_driver_to_SNpp39_match_found"] is False
    assert bridge["explicit_driver_to_SNpp41_match_found"] is False
    assert bridge["explicit_chen_em_axon_to_SNpp39_match_found"] is False
    assert bridge["explicit_chen_em_axon_to_SNpp41_match_found"] is False
    assert bridge["neuronbridge_query_result_used_as_mapping"] is False
    assert bridge["visual_similarity_used_as_mapping"] is False


def test_current_catalog_has_no_directional_systematic_type_label() -> None:
    payload = json.loads(DRIVER_CROSSCHECK.read_text())
    catalog = payload["current_malecns_catalog"]

    assert catalog["SNpp39"]["aka"] == "FeCO hook"
    assert catalog["SNpp41"]["aka"] == "FeCO hook"
    assert catalog["SNpp39"]["directional_label_present"] is False
    assert catalog["SNpp41"]["directional_label_present"] is False
