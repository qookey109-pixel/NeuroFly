import json
from pathlib import Path


ANALYSIS = Path("data/neuronbridge_feco_body_probe_run1_analysis.json")


def test_run1_preserves_artifact_provenance() -> None:
    payload = json.loads(ANALYSIS.read_text())
    workflow = payload["workflow"]

    assert workflow["run_id"] == 35442954845
    assert workflow["result"] == "success"
    assert workflow["artifact_digest"] == (
        "sha256:7ec8366393259cc0a8ef336d33a8eb9c297ab48882d2b15984ee3f64d386696d"
    )


def test_snpp39_body_level_component_morphology_is_consistent_with_extension() -> None:
    payload = json.loads(ANALYSIS.read_text())
    rows = payload["best_directional_component_matches_by_body"]["SNpp39"]

    assert len(rows) == 4
    assert {
        row["preferred_by_best_rank"] for row in rows.values()
    } == {"hook_extension"}


def test_snpp41_body_level_component_morphology_is_supportive_but_not_uniform() -> None:
    payload = json.loads(ANALYSIS.read_text())
    rows = payload["best_directional_component_matches_by_body"]["SNpp41"]

    preferences = [row["preferred_by_best_rank"] for row in rows.values()]
    assert preferences.count("hook_flexion") == 2
    assert preferences.count("hook_extension") == 1

    strong = rows["911942"]["hook_flexion"]
    assert strong["publishedName"] == "R32H08"
    assert strong["rank"] == 9
    assert strong["normalizedScore"] == 31088.082


def test_run1_did_not_recover_complete_functional_split_intersection() -> None:
    payload = json.loads(ANALYSIS.read_text())
    limitation = payload["critical_limitation"]
    libraries = payload["hit_library_distribution"]

    assert libraries["complete_split_gal4_intersection_library_hits"] == 0
    assert limitation["component_match_equivalent_to_split_intersection"] is False
    assert limitation["exact_intersection_lookup_recovered"] is False


def test_run1_strengthens_candidate_without_unlocking_polarity() -> None:
    payload = json.loads(ANALYSIS.read_text())
    interpretation = payload["interpretation"]
    governance = payload["governance"]

    assert interpretation["body_level_morphology_supports_existing_candidate"] is True
    assert interpretation["direct_type_to_polarity_source_found"] is False
    assert interpretation["exact_polarity_verified"] is False
    assert governance["snpp39_snpp41_polarity_resolved"] is False
    assert governance["current_calibration_authorized"] is False
    assert governance["runtime_stimulation_authorized"] is False
    assert governance["privileged_state_bypass_authorized"] is False
