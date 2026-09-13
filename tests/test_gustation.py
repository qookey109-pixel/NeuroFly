from neurofly.gustation import (
    GUSTATION_CROSSWALK_SCHEMA,
    GUSTATION_MODEL,
    contact_gustation,
)
from neurofly.sensory_contract import assert_unprivileged_agent_input


def test_no_contact_has_zero_taste_channels() -> None:
    payload = contact_gustation()

    assert payload["model"] == GUSTATION_MODEL
    assert payload["crosswalk_schema"] == GUSTATION_CROSSWALK_SCHEMA
    assert payload["available"] is True
    assert payload["contact"] is False
    assert payload["channels"] == {"bitter": 0.0, "sugar_water": 0.0}
    assert payload["stimulation_enabled"] is False
    assert payload["status"] == "no-gustatory-contact"
    assert_unprivileged_agent_input({"gustation": payload})


def test_maze_food_contact_is_sugar_water_not_pure_sugar() -> None:
    for event in ("food", "energy_food"):
        payload = contact_gustation(event=event)
        assert payload["contact"] is True
        assert payload["channels"]["sugar_water"] == 1.0
        assert payload["channels"]["bitter"] == 0.0
        assert payload["stimulation_enabled"] is False
        assert_unprivileged_agent_input({"gustation": payload})


def test_non_gustatory_game_events_do_not_create_taste() -> None:
    for event in ("captured", "maze_cleared", "wall", "enemy", ""):
        payload = contact_gustation(event=event)
        assert payload["contact"] is False
        assert payload["channels"] == {"bitter": 0.0, "sugar_water": 0.0}


def test_explicit_bitter_contact_is_supported_without_inference() -> None:
    payload = contact_gustation(bitter=0.75)

    assert payload["contact"] is True
    assert payload["channels"] == {"bitter": 0.75, "sugar_water": 0.0}
    assert payload["stimulation_enabled"] is False
    assert_unprivileged_agent_input({"gustation": payload})


def test_contact_levels_are_bounded() -> None:
    payload = contact_gustation(bitter=2.0, sugar_water=-1.0)
    assert payload["channels"] == {"bitter": 1.0, "sugar_water": 0.0}
