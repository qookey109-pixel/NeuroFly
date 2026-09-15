from __future__ import annotations

import json
from pathlib import Path

import pytest

from neurofly.neural_context import sanitize_neural_context
from neurofly.proprioception_polarity_semantics import (
    EVIDENCE_LEVEL,
    build_systematic_type_semantic_contract,
    require_direct_runtime_mapping,
)


EVIDENCE_PATH = Path("data/proprioception_hook_direction_evidence_v01.json")


def _evidence() -> dict:
    return json.loads(EVIDENCE_PATH.read_text())


def test_semantic_contract_keeps_systematic_type_polarity_unresolved() -> None:
    contract = build_systematic_type_semantic_contract(_evidence())

    assert contract["systematic_type_polarity_resolved"] is False
    assert contract["semantic_polarity"] == "unresolved"
    assert contract["neural_payload_eligible"] is False
    assert contract["current_calibration_authorized"] is False
    assert contract["stimulation_enabled"] is False
    assert contract["runtime_transduction_enabled"] is False

    channel_a = contract["opaque_systematic_channels"]["hook_direction_channel_A"]
    channel_b = contract["opaque_systematic_channels"]["hook_direction_channel_B"]
    assert channel_a == {
        "systematic_type": "SNpp39",
        "anatomical_identity": "FeCO hook",
        "candidate_function": "hook_extension_sensitive",
        "evidence_level": EVIDENCE_LEVEL,
        "authoritative_polarity": False,
        "runtime_routable": False,
    }
    assert channel_b == {
        "systematic_type": "SNpp41",
        "anatomical_identity": "FeCO hook",
        "candidate_function": "hook_flexion_sensitive",
        "evidence_level": EVIDENCE_LEVEL,
        "authoritative_polarity": False,
        "runtime_routable": False,
    }


def test_engineering_direction_channels_have_no_systematic_type_binding() -> None:
    contract = build_systematic_type_semantic_contract(_evidence())

    assert contract["engineering_receptor_channels"]["hook_extension"]["systematic_type_binding"] is None
    assert contract["engineering_receptor_channels"]["hook_flexion"]["systematic_type_binding"] is None

    with pytest.raises(RuntimeError, match="Direct SNpp39/SNpp41 polarity evidence"):
        require_direct_runtime_mapping(contract)


def test_direct_tuning_cannot_be_smuggled_into_unresolved_evidence() -> None:
    evidence = _evidence()
    evidence["systematic_types"]["SNpp39"]["direct_directional_tuning"] = "extension"

    with pytest.raises(ValueError, match="Direct directional tuning"):
        build_systematic_type_semantic_contract(evidence)


def test_inferred_candidate_cannot_open_runtime_or_calibration_locks() -> None:
    evidence = _evidence()
    evidence["runtime_transduction_enabled"] = True

    with pytest.raises(ValueError, match="lock opened"):
        build_systematic_type_semantic_contract(evidence)


def test_control_plane_semantics_cannot_cross_neural_context_firewall() -> None:
    contract = build_systematic_type_semantic_contract(_evidence())

    with pytest.raises(ValueError, match="Non-sensory fields"):
        sanitize_neural_context({"proprioception_semantics": contract})

    with pytest.raises(ValueError, match="Unexpected proprioception model"):
        sanitize_neural_context({"proprioception": contract})
