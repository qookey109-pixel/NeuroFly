import json
from pathlib import Path


AUDIT = Path("data/feco_hook_flybase_ontology_bridge_audit_v01.json")


def test_official_flybase_mapping_stays_at_generic_hook_parent() -> None:
    payload = json.loads(AUDIT.read_text())
    rows = payload["mapping_rows"]

    assert rows["SNpp39"]["FBbt_id"] == "FBbt:00049558"
    assert rows["SNpp41"]["FBbt_id"] == "FBbt:00049558"
    assert rows["SNpp39"]["specificity"] == "parent_term"
    assert rows["SNpp41"]["specificity"] == "parent_term"


def test_directional_child_classes_exist_but_are_not_assigned() -> None:
    payload = json.loads(AUDIT.read_text())
    directional = payload["directional_child_classes_exist"]

    assert directional["hook_extension"]["FBbt_id"] == "FBbt:00052632"
    assert directional["hook_flexion"]["FBbt_id"] == "FBbt:00052633"
    assert payload["interpretation"]["official_manc_to_fbbt_bridge_exists"] is True
    assert payload["interpretation"]["official_bridge_reaches_directional_subclass"] is False


def test_historical_mapping_check_did_not_promote_either_type() -> None:
    payload = json.loads(AUDIT.read_text())
    history = payload["mapping_history"]

    assert history["snpp39_row_changed_to_directional_class"] is False
    assert history["snpp41_row_changed_to_directional_class"] is False


def test_candidate_crosswalk_remains_candidate_only() -> None:
    payload = json.loads(AUDIT.read_text())
    candidate = payload["existing_candidate_crosswalk"]

    assert candidate["SNpp39"] == "hook_extension_candidate"
    assert candidate["SNpp41"] == "hook_flexion_candidate"
    assert candidate["status"] == "unchanged_candidate_only"


def test_runtime_and_calibration_gates_remain_locked() -> None:
    payload = json.loads(AUDIT.read_text())
    governance = payload["governance"]

    assert governance["direct_type_to_polarity_source_found"] is False
    assert governance["snpp39_snpp41_polarity_resolved"] is False
    assert governance["exact_polarity_verified"] is False
    assert governance["current_calibration_authorized"] is False
    assert governance["runtime_stimulation_authorized"] is False
    assert governance["privileged_state_bypass_authorized"] is False
