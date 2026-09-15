from __future__ import annotations

import json
from pathlib import Path

from neurofly.proprioception_polarity_semantics import (
    build_systematic_type_semantic_contract,
)


EVIDENCE_PATH = Path("data/proprioception_hook_direction_evidence_v01.json")
SITE_PATH = Path("site/proprioception-semantics.json")
OBSERVER_PATH = Path("site/all-clear-history.js")


def test_site_semantic_snapshot_matches_frozen_control_plane_contract() -> None:
    evidence = json.loads(EVIDENCE_PATH.read_text())
    expected = build_systematic_type_semantic_contract(evidence)
    observed = json.loads(SITE_PATH.read_text())
    assert observed == expected


def test_site_semantics_remain_human_only_and_fail_closed() -> None:
    observed = json.loads(SITE_PATH.read_text())

    assert observed["plane"] == "control-plane-only-not-neural-input"
    assert observed["systematic_type_polarity_resolved"] is False
    assert observed["neural_payload_eligible"] is False
    assert observed["current_calibration_authorized"] is False
    assert observed["stimulation_enabled"] is False
    assert observed["runtime_transduction_enabled"] is False
    assert observed["promotion_ready"] is False

    engineering = observed["engineering_receptor_channels"]
    assert engineering["hook_extension"]["systematic_type_binding"] is None
    assert engineering["hook_flexion"]["systematic_type_binding"] is None

    channel_a = observed["opaque_systematic_channels"]["hook_direction_channel_A"]
    channel_b = observed["opaque_systematic_channels"]["hook_direction_channel_B"]
    assert channel_a["systematic_type"] == "SNpp39"
    assert channel_b["systematic_type"] == "SNpp41"
    assert channel_a["authoritative_polarity"] is False
    assert channel_b["authoritative_polarity"] is False
    assert channel_a["runtime_routable"] is False
    assert channel_b["runtime_routable"] is False


def test_site_observer_labels_inference_without_creating_runtime_alias() -> None:
    source = OBSERVER_PATH.read_text()

    assert "proprioception-semantics.json" in source
    assert "PHYSIOLOGY_SUPPORTED_INFERENCE" not in source
    assert "（推論）" in source
    assert "control plane only" in source
    assert "systematic_type_binding" in source
    assert "runtime_routable" in source
    assert "沒有 executable hook_extension/flexion → SNpp39/41 alias" in source
