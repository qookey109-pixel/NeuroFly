from __future__ import annotations

import copy

import neurofly.proprioception_connectivity_audit as audit


def _fixture():
    target = {
        "body_id": "905407",
        "instance": "",
        "type": "SNpp41",
        "class": "mechanosensory_proprioceptive",
        "subclass": "leg",
        "superclass": "vnc_sensory",
        "soma_side": "",
    }
    peers = [
        {
            "body_id": str(1000 + index),
            "instance": f"SNpp41_{index}",
            "type": "SNpp41",
            "class": "mechanosensory_proprioceptive",
            "subclass": "chordotonal organ",
            "superclass": "vnc_sensory",
            "soma_side": "L" if index % 2 else "R",
        }
        for index in range(21)
    ]
    profiles = {
        target["body_id"]: {
            "incoming": {"type:A": 10, "type:B": 5},
            "outgoing": {"type:X": 30, "type:Y": 10},
        }
    }
    for index, peer in enumerate(peers):
        profiles[peer["body_id"]] = {
            "incoming": {"type:A": 10 + index % 3, "type:B": 5},
            "outgoing": {"type:X": 30, "type:Y": 10 + index % 2},
        }
    return target, peers, profiles


def test_discovery_run_publishes_receipt_but_keeps_all_promotion_locked(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_CONNECTIVITY_SHA256", None)
    target, peers, profiles = _fixture()
    report = audit.audit_profiles(
        target_record=target,
        peer_records=peers,
        profiles=profiles,
    )
    assert report["status"] == "DISCOVERY_REQUIRED"
    assert report["passed"] is False
    assert report["peer_count"] == 21
    assert len(report["connectivity_sha256"]) == 64
    assert report["morphology_evidence_present"] is False
    assert report["promotion_ready"] is False
    assert report["stimulation_enabled"] is False
    assert report["runtime_transduction_enabled"] is False
    assert report["current_calibration_authorized"] is False


def test_exact_frozen_receipt_reproduces_only_as_review_required(monkeypatch) -> None:
    target, peers, profiles = _fixture()
    monkeypatch.setattr(audit, "EXPECTED_CONNECTIVITY_SHA256", None)
    discovered = audit.audit_profiles(
        target_record=target,
        peer_records=peers,
        profiles=profiles,
    )
    monkeypatch.setattr(
        audit, "EXPECTED_CONNECTIVITY_SHA256", discovered["connectivity_sha256"]
    )
    report = audit.audit_profiles(
        target_record=target,
        peer_records=peers,
        profiles=profiles,
    )
    assert report["passed"] is True
    assert report["status"] == "REVIEW_REQUIRED"
    assert report["gates"]["connectivity_receipt_matches"] is True
    assert report["promotion_ready"] is False


def test_any_connectivity_change_breaks_frozen_digest(monkeypatch) -> None:
    target, peers, profiles = _fixture()
    monkeypatch.setattr(audit, "EXPECTED_CONNECTIVITY_SHA256", None)
    discovered = audit.audit_profiles(
        target_record=target,
        peer_records=peers,
        profiles=profiles,
    )
    monkeypatch.setattr(
        audit, "EXPECTED_CONNECTIVITY_SHA256", discovered["connectivity_sha256"]
    )
    changed = copy.deepcopy(profiles)
    changed["905407"]["outgoing"]["type:X"] += 1
    report = audit.audit_profiles(
        target_record=target,
        peer_records=peers,
        profiles=changed,
    )
    assert report["passed"] is False
    assert report["status"] == "FAIL"
    assert report["gates"]["connectivity_receipt_matches"] is False


def test_wrong_target_taxonomy_fails_before_interpretation(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_CONNECTIVITY_SHA256", None)
    target, peers, profiles = _fixture()
    target = dict(target)
    target["subclass"] = "chordotonal organ"
    report = audit.audit_profiles(
        target_record=target,
        peer_records=peers,
        profiles=profiles,
    )
    assert report["status"] == "FAIL"
    assert report["gates"]["target_subclass_is_leg"] is False


def test_missing_peer_fails_exact_population_gate(monkeypatch) -> None:
    monkeypatch.setattr(audit, "EXPECTED_CONNECTIVITY_SHA256", None)
    target, peers, profiles = _fixture()
    missing = peers[:-1]
    reduced = {key: value for key, value in profiles.items() if key != peers[-1]["body_id"]}
    report = audit.audit_profiles(
        target_record=target,
        peer_records=missing,
        profiles=reduced,
    )
    assert report["status"] == "FAIL"
    assert report["gates"]["exact_peer_count"] is False


def test_identical_profiles_have_unit_cosine() -> None:
    target, peers, profiles = _fixture()
    first_peer = peers[0]["body_id"]
    profiles[first_peer] = copy.deepcopy(profiles["905407"])
    comparison = audit.compare_profiles(
        profiles,
        target_body_id="905407",
        peer_body_ids=[row["body_id"] for row in peers],
    )
    row = next(item for item in comparison["target_vs_peers"] if item["body_id"] == first_peer)
    assert row["incoming_cosine"] == 1.0
    assert row["outgoing_cosine"] == 1.0
    assert row["combined_cosine"] == 1.0
