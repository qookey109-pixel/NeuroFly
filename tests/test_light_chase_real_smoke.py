from __future__ import annotations

import copy
import json
from pathlib import Path

from neurofly.light_chase import LIGHT_CHASE_MODEL
from neurofly.light_chase_real_smoke import (
    RECEIPT_SCHEMA,
    evaluate_light_smoke_evidence,
    validate_contract,
)


CONTRACT = Path("data/light_chase_real_malecns_smoke_v01.json")
WORKFLOW = Path(".github/workflows/light-chase-real-malecns-smoke.yml")


def _contract() -> dict:
    return json.loads(CONTRACT.read_text())


def _state() -> dict:
    return {
        "environment_model": LIGHT_CHASE_MODEL,
        "episode": 1,
        "last_action": "HOLD",
        "last_reward": -0.01,
        "last_event": "hold",
        "total_lights": 0,
        "brain": {
            "backend": "malecns",
            "telemetry": {
                "brain_ms": 50.0,
                "total_spikes": 3,
            },
        },
        "sensory_contract": {
            "adapter_schema": "neurofly-environment-adapter-v0.1",
            "environment_model": LIGHT_CHASE_MODEL,
            "vision": {
                "model": "neurofly-light-chase-egocentric-vision-v0.1",
                "coordinate_frame": "egocentric-wide-field",
                "target_coordinates_exposed": False,
                "target_bearing_exposed": False,
                "target_distance_exposed": False,
                "recommended_action_exposed": False,
            },
        },
    }


def _report(states=None, *, source_after=None, learning=False):
    return evaluate_light_smoke_evidence(
        _contract(),
        source_sha_before="a" * 64,
        source_sha_after=source_after or "a" * 64,
        source_isolated=True,
        proof_brain_exists=True,
        proof_environment_exists=True,
        learning_enabled=learning,
        states=states or [_state(), _state(), _state()],
    )


def test_contract_is_exact_and_non_promotional() -> None:
    contract = _contract()
    gates = validate_contract(contract)

    assert all(gates.values())
    assert contract["environment_model"] == LIGHT_CHASE_MODEL
    assert contract["learning_enabled"] is False
    assert all(contract["required_invariants"].values())
    assert all(value is False for value in contract["claim_limits"].values())


def test_structurally_valid_real_light_execution_evidence_passes() -> None:
    report = _report()

    assert report["schema"] == RECEIPT_SCHEMA
    assert report["status"] == "PASS"
    assert report["passed"] is True
    assert report["steps"] == 3
    assert report["neural_activity_verified"] is True
    assert all(report["contract_gates"].values())
    assert all(report["invariants"].values())


def test_gate_fails_if_privileged_target_geometry_reaches_neural_context() -> None:
    state = _state()
    state["sensory_contract"]["target"] = {"x": 8, "y": 3}

    report = _report(states=[state])

    assert report["passed"] is False
    assert report["invariants"]["all_steps_sensory_context_unprivileged"] is False


def test_gate_fails_if_neural_activity_is_not_verified() -> None:
    state = _state()
    state["brain"]["telemetry"]["total_spikes"] = 0

    report = _report(states=[state])

    assert report["passed"] is False
    assert report["invariants"]["all_steps_neural_activity_verified"] is False


def test_gate_fails_if_source_checkpoint_changes() -> None:
    report = _report(source_after="b" * 64)

    assert report["passed"] is False
    assert report["invariants"]["source_checkpoint_unchanged"] is False


def test_gate_fails_if_learning_is_enabled() -> None:
    report = _report(learning=True)

    assert report["passed"] is False
    assert report["invariants"]["learning_disabled"] is False


def test_gate_fails_if_contract_opens_behavioral_claim() -> None:
    contract = copy.deepcopy(_contract())
    contract["claim_limits"]["light_seeking_behavior_validated"] = True

    gates = validate_contract(contract)

    assert gates["claim_limits_exact"] is False


def test_manual_workflow_is_isolated_and_does_not_mutate_production() -> None:
    workflow = WORKFLOW.read_text()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "push:" not in workflow
    assert "actions/cache/restore@v4" in workflow
    assert "actions/cache/save@v4" not in workflow
    assert "git push" not in workflow
    assert "SOURCE_STATE: runs/free-malecns" in workflow
    assert "runs/light-chase-real-smoke" in workflow
    assert "light_seeking_behavior_validated" in workflow
    assert "light_chase_learning_validated" in workflow
