from __future__ import annotations

from typing import Any, Sequence


TACTILE_MODEL = "neurofly-contact-mechanosensation-v1"
TACTILE_ENCODING = "blocked-forward-external-touch-proxy"


def _bounded_unit(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        number = 0.0
    return max(0.0, min(1.0, number))


def contact_mechanosensation(*, front: float = 0.0) -> dict[str, Any]:
    """Return a strict contact-only tactile payload with no world geometry.

    This is an engineering external-touch proxy. It represents only whether a
    physical front contact occurred in the supported environment. It does not
    encode wall identity, object identity, coordinates, collision normals,
    target semantics, reward, or desired action. Neural current remains disabled
    until a separate prepared-MaleCNS calibration gate passes.
    """

    front_level = _bounded_unit(front)
    return {
        "model": TACTILE_MODEL,
        "available": True,
        "encoding": TACTILE_ENCODING,
        "contact": front_level > 0.0,
        "channels": {"front": front_level},
        "stimulation_enabled": False,
    }


def blocked_forward_contact(
    *,
    applied_action: str,
    before_position: Sequence[int],
    after_position: Sequence[int],
    terminal: bool = False,
) -> dict[str, Any]:
    """Transduce one blocked forward attempt into a front-contact payload.

    In the current maze body proxy, a non-terminal applied FORWARD that leaves
    the fly at the exact same position is the narrow supported physical-contact
    fact. TURN/HOLD immobility is not contact. A successful FORWARD is not
    contact. Terminal predator/body interactions are deliberately outside this
    v1 contract and must not be inferred from event labels or rewards.
    """

    before = tuple(int(value) for value in before_position)
    after = tuple(int(value) for value in after_position)
    if len(before) != 2 or len(after) != 2:
        raise ValueError("Tactile contact positions must contain exactly two coordinates")
    if applied_action not in {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}:
        raise ValueError(f"Unknown applied maze action: {applied_action}")

    blocked = applied_action == "FORWARD" and before == after and not bool(terminal)
    return contact_mechanosensation(front=1.0 if blocked else 0.0)


def tactile_channel_levels(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the strict tactile contract without authorizing stimulation."""

    if payload.get("model") != TACTILE_MODEL:
        raise ValueError("Unexpected tactile model")
    if payload.get("available") is not True:
        raise ValueError("Tactile payload must be available in this contract")
    if payload.get("encoding") != TACTILE_ENCODING:
        raise ValueError("Unexpected tactile encoding")
    if payload.get("stimulation_enabled") is not False:
        raise ValueError("Tactile stimulation must remain disabled before calibration")

    channels = payload.get("channels")
    if not isinstance(channels, dict) or set(channels) != {"front"}:
        raise ValueError("Tactile payload must contain exactly the front channel")
    try:
        front = float(channels["front"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Tactile front channel must be numeric") from exc
    if not 0.0 <= front <= 1.0:
        raise ValueError("Tactile front channel must stay within [0,1]")

    contact = payload.get("contact")
    if not isinstance(contact, bool):
        raise ValueError("Tactile contact flag must be boolean")
    if contact != (front > 0.0):
        raise ValueError("Tactile contact flag must agree with the front channel")

    return {
        "available": True,
        "contact": contact,
        "front": front,
    }
