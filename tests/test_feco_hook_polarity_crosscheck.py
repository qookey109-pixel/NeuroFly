import json
from pathlib import Path


CROSSCHECK = Path("data/feco_hook_polarity_crosscheck_v01.json")


def test_feco_hook_candidate_crosswalk_is_explicit_but_not_promoted() -> None:
    payload = json.loads(CROSSCHECK.read_text())
    inference = payload["circuit_consistency_inference"]
    governance = payload["governance"]

    assert inference["candidate_crosswalk"] == {
        "SNpp39": "hook_extension_candidate",
        "SNpp41": "hook_flexion_candidate",
    }
    assert inference["confidence_class"] == (
        "strong_circuit_consistency_inference_not_direct_annotation"
    )

    assert governance["directional_candidate_crosswalk_supported"] is True
    assert governance["exact_polarity_verified"] is False
    assert governance["snpp39_snpp41_polarity_resolved"] is False
    assert governance["current_calibration_authorized"] is False
    assert governance["runtime_stimulation_authorized"] is False


def test_feco_hook_direct_type_to_polarity_evidence_remains_absent() -> None:
    payload = json.loads(CROSSCHECK.read_text())
    direct = payload["direct_evidence"]

    assert direct["snpp39_is_feco_hook"] is True
    assert direct["snpp41_is_feco_hook"] is True
    assert direct["direct_type_to_polarity_source_found"] is False

    for key in (
        "direct_snpp39_extension_label_found",
        "direct_snpp39_flexion_label_found",
        "direct_snpp41_extension_label_found",
        "direct_snpp41_flexion_label_found",
    ):
        assert direct[key] is False


def test_feco_hook_crosscheck_does_not_use_hemilineage_as_decisive_mapping() -> None:
    payload = json.loads(CROSSCHECK.read_text())
    inference = payload["circuit_consistency_inference"]

    assert inference["decisive_hemilineage_crosswalk_used"] is False
