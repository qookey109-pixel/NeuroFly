from __future__ import annotations

import copy

import pytest

from neurofly.proprioception import proprioceptive_channel_levels
from neurofly.sensory_contract import assert_unprivileged_agent_input
from neurofly.virtual_body import (
    VIRTUAL_BODY_MODEL,
    VIRTUAL_BODY_POLICY,
    VIRTUAL_BODY_STATE_SCHEMA,
    VirtualFeCOJointBody,
)


def _channels(payload: dict) -> dict[str, float]:
    levels = proprioceptive_channel_levels(payload)
    return {
        "hook_extension": levels["hook_extension"],
        "hook_flexion": levels["hook_flexion"],
        "club_motion": levels["club_motion"],
        "club_vibration": levels["club_vibration"],
    }


def test_neutral_hold_has_no_receptor_motion() -> None:
    body = VirtualFeCOJointBody()
    payload = body.advance("HOLD")
    assert _channels(payload) == {
        "hook_extension": 0.0,
        "hook_flexion": 0.0,
        "club_motion": 0.0,
        "club_vibration": 0.0,
    }
    assert payload["claw_position_available"] is False
    assert payload["stimulation_enabled"] is False
    assert payload["runtime_transduction_enabled"] is False


def test_forward_execution_creates_stateful_joint_motion_without_world_state() -> None:
    body = VirtualFeCOJointBody()
    first = _channels(body.advance("FORWARD"))
    second = _channels(body.advance("FORWARD"))

    assert first["hook_extension"] > 0.0
    assert first["hook_flexion"] == 0.0
    assert first["club_motion"] == pytest.approx(first["hook_extension"])

    assert second["hook_extension"] == 0.0
    assert second["hook_flexion"] > 0.0
    assert second["club_motion"] == pytest.approx(second["hook_flexion"])


def test_left_and_right_turns_have_same_representative_joint_envelope() -> None:
    left = VirtualFeCOJointBody()
    right = VirtualFeCOJointBody()
    left_channels = _channels(left.advance("TURN_LEFT"))
    right_channels = _channels(right.advance("TURN_RIGHT"))
    assert left_channels == right_channels
    assert left_channels["club_motion"] > 0.0


def test_hold_after_motion_can_report_passive_return_motion() -> None:
    body = VirtualFeCOJointBody()
    body.advance("FORWARD")
    channels = _channels(body.advance("HOLD"))
    assert channels["hook_extension"] == 0.0
    assert channels["hook_flexion"] > 0.0
    assert channels["club_motion"] > 0.0


def test_vibration_is_external_internal_mechanics_not_synthesized_by_action() -> None:
    body = VirtualFeCOJointBody()
    no_vibration = _channels(body.advance("FORWARD"))
    assert no_vibration["club_vibration"] == 0.0

    body.reset()
    with_vibration = _channels(body.advance("FORWARD", mechanical_vibration=0.37))
    assert with_vibration["club_vibration"] == pytest.approx(0.37)


def test_neural_payload_contains_no_private_body_or_motor_execution_fields() -> None:
    body = VirtualFeCOJointBody()
    payload = body.advance("TURN_LEFT", mechanical_vibration=0.2)
    forbidden = {
        "action",
        "motor_execution",
        "heading",
        "world_velocity",
        "world_displacement",
        "joint_phase",
        "joint_position",
        "joint_delta",
        "mechanical_vibration",
        "reward",
        "desired_action",
        "x",
        "y",
    }

    def walk(value):
        if isinstance(value, dict):
            for key, nested in value.items():
                assert key not in forbidden
                walk(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                walk(nested)

    walk(payload)
    assert_unprivileged_agent_input({"proprioception": payload})


def test_private_body_snapshot_is_diagnostics_only_and_guard_rejects_it() -> None:
    body = VirtualFeCOJointBody()
    body.advance("FORWARD")
    snapshot = body.persistence_snapshot()
    assert snapshot["schema"] == VIRTUAL_BODY_STATE_SCHEMA
    assert snapshot["model"] == VIRTUAL_BODY_MODEL
    assert snapshot["policy"] == VIRTUAL_BODY_POLICY
    assert snapshot["representative_joint_only"] is True
    assert snapshot["six_leg_model"] is False
    with pytest.raises(ValueError, match="Privileged field"):
        assert_unprivileged_agent_input({"proprioception": snapshot})


def test_checkpoint_roundtrip_preserves_private_joint_state() -> None:
    body = VirtualFeCOJointBody()
    body.advance("FORWARD")
    body.advance("TURN_RIGHT")
    snapshot = body.persistence_snapshot()

    restored = VirtualFeCOJointBody()
    restored.restore(copy.deepcopy(snapshot))
    assert restored.persistence_snapshot() == snapshot
    assert _channels(restored.advance("FORWARD")) == _channels(body.advance("FORWARD"))


def test_invalid_execution_and_invalid_state_fail_closed() -> None:
    body = VirtualFeCOJointBody()
    with pytest.raises(ValueError, match="Unknown virtual body motor execution"):
        body.advance("TELEPORT")

    invalid = body.persistence_snapshot()
    invalid["six_leg_model"] = True
    with pytest.raises(ValueError, match="must not claim a six-leg model"):
        body.restore(invalid)
