from __future__ import annotations

from typing import Any


GUSTATION_MODEL = "neurofly-contact-gustation-v1"
GUSTATION_CROSSWALK_SCHEMA = "neurofly-gustation-functional-crosswalk-v0.1"

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

    This module defines sensory transduction only. It does not authorize or apply
    MaleCNS stimulation current.
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
