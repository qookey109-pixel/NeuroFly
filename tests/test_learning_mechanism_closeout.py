import json
from pathlib import Path


EVENT_FREEZE = Path("data/event_local_reinforcement_pulse_run1_freeze_v01.json")
CLOSEOUT = Path("data/learning_mechanism_closeout_v01.json")


def test_event_local_run1_freeze_is_exact_and_locked() -> None:
    freeze = json.loads(EVENT_FREEZE.read_text())
    assert freeze["run_id"] == 35434647150
    assert freeze["execution_valid"] is True
    assert freeze["artifact_id"] == 10581628974
    assert freeze["artifact_digest"] == (
        "sha256:61326964f7e25093a56a21a54f7260899d59c789de7b4310400600487cb38ca2"
    )
    assert freeze["receipt_sha256"] == (
        "6d7c7fc8c38106e8ceafb8e0346f87a7a6ae71cbfea59b2b3d9e372203e42712"
    )
    aggregate = freeze["aggregate"]
    assert aggregate["event_count"] == 22
    assert aggregate["reward_event_count"] == 14
    assert aggregate["aversive_event_count"] == 8
    assert aggregate["reward_event_negative_efficacy_events"] == 14
    assert aggregate["aversive_event_negative_efficacy_events"] == 8
    assert aggregate["reward_event_positive_efficacy_events"] == 0
    assert aggregate["aversive_event_positive_efficacy_events"] == 0
    assert aggregate["event_action_divergence_fraction"] == 0.0
    assert all(value is False for value in freeze["claim_locks"].values())


def test_learning_mechanism_closeout_does_not_promote_claims() -> None:
    closeout = json.loads(CLOSEOUT.read_text())
    assert closeout["status"] == "LEARNING_MECHANISM_DIAGNOSTIC_CLOSED"
    assert closeout["frozen_findings"]["event_local_all_events"] == 22
    assert closeout["frozen_findings"]["event_local_negative_events"] == 22
    assert closeout["frozen_findings"]["event_local_action_divergence_fraction"] == 0.0
    assert all(value is False for value in closeout["claim_locks"].values())
    branch = closeout["mechanism_branch"]
    assert branch["further_automatic_experiments_authorized"] is False
    assert branch["tuning_eta_decoder_pulse_or_reward_thresholds_authorized"] is False
