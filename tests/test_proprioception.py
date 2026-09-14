from __future__ import annotations

import pytest

from neurofly.proprioception import (
    PROPRIOCEPTION_ENCODING,
    PROPRIOCEPTION_MODEL,
    feco_motion_proprioception,
    proprioceptive_channel_levels,
)
from neurofly.sensory_contract import assert_unprivileged_agent_input


def test_neutral_joint_state_has_zero_motion_channels() -> None:
    payload = feco_motion_proprioception()
    assert payload["model"] == PROPRIOCEPTION_MODEL
    assert payload["encoding"] == PROPRIOCEPTION_ENCODING
    assert payload["channels"] == {
        "hook_extension": 0.0,
        "hook_flexion": 0.0,
        "club_motion": 0.0,
        "club_vibration": 0.0,
    }
    assert payload["claw_position_available"] is False
    assert payload["stimulation_enabled"] is False
    assert payload["runtime_transduction_enabled"] is False


def test_positive_joint_delta_is_extension_and_club_motion() -> None:
    payload = feco_motion_proprioception(joint_delta=0.35, vibration=0.2)
    levels = proprioceptive_channel_levels(payload)
    assert levels["hook_extension"] == pytest.approx(0.35)
    assert levels["hook_flexion"] == 0.0
    assert levels["club_motion"] == pytest.approx(0.35)
    assert levels["club_vibration"] == pytest.approx(0.2)


def test_negative_joint_delta_is_flexion_and_club_motion() -> None:
    payload = feco_motion_proprioception(joint_delta=-0.7)
    levels = proprioceptive_channel_levels(payload)
    assert levels["hook_extension"] == 0.0
    assert levels["hook_flexion"] == pytest.approx(0.7)
    assert levels["club_motion"] == pytest.approx(0.7)


def test_motion_and_vibration_are_bounded() -> None:
    payload = feco_motion_proprioception(joint_delta=9.0, vibration=12.0)
    levels = proprioceptive_channel_levels(payload)
    assert levels["hook_extension"] == 1.0
    assert levels["club_motion"] == 1.0
    assert levels["club_vibration"] == 1.0


def test_claw_position_cannot_be_enabled_by_this_contract() -> None:
    payload = feco_motion_proprioception(joint_delta=0.1)
    payload["claw_position_available"] = True
    with pytest.raises(ValueError, match="Claw position"):
        proprioceptive_channel_levels(payload)


def test_hook_directions_must_remain_mutually_exclusive() -> None:
    payload = feco_motion_proprioception(joint_delta=0.2)
    payload["channels"]["hook_flexion"] = 0.1
    with pytest.raises(ValueError, match="mutually exclusive"):
        proprioceptive_channel_levels(payload)


def test_contract_contains_no_world_state_or_motor_command_fields() -> None:
    payload = feco_motion_proprioception(joint_delta=-0.4, vibration=0.1)
    forbidden = {
        "x",
        "y",
        "heading",
        "world_velocity",
        "world_displacement",
        "route",
        "reward",
        "action",
        "desired_action",
        "joint_delta",
        "joint_position",
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


@pytest.mark.parametrize(
    "forbidden_key",
    [
        "heading",
        "world_velocity",
        "world_displacement",
        "reward",
        "desired_action",
        "joint_delta",
        "joint_position",
    ],
)
def test_raw_world_or_joint_state_is_rejected_by_global_sensory_guard(
    forbidden_key: str,
) -> None:
    with pytest.raises(ValueError, match="Privileged field"):
        assert_unprivileged_agent_input(
            {"proprioception": {forbidden_key: 0.25}}
        )
