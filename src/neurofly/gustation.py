from __future__ import annotations

from typing import Any


GUSTATION_MODEL = "neurofly-contact-gustation-v1"
GUSTATION_CROSSWALK_SCHEMA = "neurofly-gustation-functional-crosswalk-v0.1"
GUSTATION_CALIBRATION_SCHEMA = "neurofly-gustation-current-calibration-v1"
GUSTATION_CALIBRATION_RECEIPT_SHA256 = (
    "595054789f40c1039b8393d32f797db299dad93b4153eecb5547fb9e7fc62610"
)
GUSTATION_CALIBRATED_BITTER_CURRENT = 8.0
GUSTATION_CALIBRATED_SUGAR_WATER_CURRENT = 8.0
BITTER_GRN_TYPES = ("LB1b",)
SUGAR_WATER_GRN_TYPES = ("LB3a", "LB3b", "LB3c", "LB3d")
EXPECTED_BITTER_GRNS = 6
EXPECTED_SUGAR_WATER_GRNS = 77

# Current maze foods are represented only as a conservative sugar/water contact
# channel. This is deliberately not called pure sugar because the evidence-backed
# LB3 crosswalk remains sugar/water ambiguous.
_SUGAR_WATER_EVENTS = frozenset({"food", "energy_food"})


def _bounded_unit(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return max(0.0, min(1.0, number))


def contact_gustation(
    *,
    event: str | None = None,
    bitter: float = 0.0,
    sugar_water: float | None = None,
) -> dict[str, Any]:
    """Transduce only physical gustatory contact into functional channels.

    ``event`` is used only as a contact gate for the existing maze's food events.
    No reward, food coordinates, route, target action, distance or global world
    state is accepted by this API.

    ``bitter`` is an explicit contact stimulus hook for later environments. It is
    not inferred from current maze state. ``sugar_water`` can likewise be supplied
    explicitly by a future physical-contact renderer; when omitted, the current
    maze's ``food``/``energy_food`` contact events map to a unit sugar/water pulse.

    This function only creates the sensory payload. ``stimulation_enabled`` stays
    false here because the transducer itself never injects current; the calibrated
    MaleCNS runtime validates this payload separately and owns neural stimulation.
    """

    event_name = "" if event is None else str(event)
    inferred_sugar_water = 1.0 if event_name in _SUGAR_WATER_EVENTS else 0.0
    sugar_level = (
        inferred_sugar_water if sugar_water is None else _bounded_unit(sugar_water)
    )
    bitter_level = _bounded_unit(bitter)
    contact = sugar_level > 0.0 or bitter_level > 0.0

    return {
        "model": GUSTATION_MODEL,
        "crosswalk_schema": GUSTATION_CROSSWALK_SCHEMA,
        "available": True,
        "encoding": "contact-only-functional-class-proxy",
        "engineered_proxy": True,
        "contact": contact,
        "channels": {
            "bitter": bitter_level,
            "sugar_water": sugar_level,
        },
        "stimulation_enabled": False,
        "status": "contact" if contact else "no-gustatory-contact",
    }
