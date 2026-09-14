from __future__ import annotations

import pytest

from neurofly.tactile import (
    TACTILE_ENCODING,
    TACTILE_MODEL,
    blocked_forward_contact,
    contact_mechanosensation,
    tactile_channel_levels,
)


def test_contact_payload_is_bounded_and_current_stays_disabled() -> None:
    payload = contact_mechanosensation(front=9.0)
    assert payload == {
        "model": TACTILE_MODEL,
        "available": True,
        "encoding": TACTILE_ENCODING,
        "contact": True,
        "channels": {"front": 1.0},
        "stimulation_enabled": False,
    }
    assert tactile_channel_levels(payload) == {
        "available": True,
        "contact": True,
        "front": 1.0,
    }


def test_only_blocked_nonterminal_forward_is_front_contact() -> None:
    blocked = blocked_forward_contact(
        applied_action="FORWARD",
        before_position=(3, 4),
        after_position=(3, 4),
    )
    assert blocked["contact"] is True
    assert blocked["channels"] == {"front": 1.0}

    moved = blocked_forward_contact(
        applied_action="FORWARD",
        before_position=(3, 4),
        after_position=(4, 4),
    )
    assert moved["contact"] is False

    held = blocked_forward_contact(
        applied_action="HOLD",
        before_position=(3, 4),
        after_position=(3, 4),
    )
    assert held["contact"] is False

    turned = blocked_forward_contact(
        applied_action="TURN_LEFT",
        before_position=(3, 4),
        after_position=(3, 4),
    )
    assert turned["contact"] is False

    terminal = blocked_forward_contact(
        applied_action="FORWARD",
        before_position=(3, 4),
        after_position=(3, 4),
        terminal=True,
    )
    assert terminal["contact"] is False


def test_tactile_validator_rejects_inconsistent_contact_flag() -> None:
    payload = contact_mechanosensation(front=1.0)
    payload["contact"] = False
    with pytest.raises(ValueError, match="contact flag"):
        tactile_channel_levels(payload)


def test_tactile_positions_must_be_exact_xy_pairs() -> None:
    with pytest.raises(ValueError, match="exactly two coordinates"):
        blocked_forward_contact(
            applied_action="FORWARD",
            before_position=(1, 2, 3),
            after_position=(1, 2),
        )

    with pytest.raises(ValueError, match="Unknown applied maze action"):
        blocked_forward_contact(
            applied_action="JUMP",
            before_position=(1, 2),
            after_position=(1, 2),
        )
