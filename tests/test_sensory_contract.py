import pytest

from neurofly.sensory_contract import (
    SENSORY_CONTRACT,
    SENSORY_POLICY,
    assert_unprivileged_agent_input,
    build_sensory_contract,
)


def _world() -> tuple[list[list[str]], dict[str, object], list[dict[str, int]]]:
    grid = [
        list("#####"),
        list("#...#"),
        list("#...#"),
        list("#..o#"),
        list("#####"),
    ]
    fly = {"x": 1, "y": 2, "dir": "RIGHT"}
    enemies = [{"x": 3, "y": 2}]
    return grid, fly, enemies


def test_contract_separates_agent_input_from_world_diagnostics() -> None:
    grid, fly, enemies = _world()
    contract = build_sensory_contract(
        grid=grid,
        fly=fly,
        enemies=enemies,
        airflow={"x": -1.0, "y": 0.0},
    )

    assert contract["schema"] == SENSORY_CONTRACT
    assert contract["policy"] == SENSORY_POLICY

    agent = contract["agent_input"]
    diagnostics = contract["diagnostics"]

    assert agent["vision"]["coordinate_frame"] == "egocentric-retina"
    assert agent["vision"]["world_geometry_exposed"] is False
    assert 0.0 <= agent["olfaction"]["food"]["left"] <= 1.0
    assert 0.0 <= agent["olfaction"]["food"]["right"] <= 1.0
    assert 0.0 <= agent["olfaction"]["danger"]["left"] <= 1.0
    assert 0.0 <= agent["olfaction"]["danger"]["right"] <= 1.0

    mech = agent["antennal_mechanosensation"]
    assert mech["available"] is True
    assert mech["left"] == {"jo_c": 0.0, "jo_e": 1.0}
    assert mech["right"] == {"jo_c": 0.0, "jo_e": 1.0}

    tactile = agent["contact_mechanosensation"]
    assert tactile["available"] is True
    assert tactile["contact"] is False
    assert tactile["channels"] == {"front": 0.0}
    assert tactile["stimulation_enabled"] is False

    taste = agent["gustation"]
    assert taste["available"] is True
    assert taste["contact"] is False
    assert taste["channels"] == {"bitter": 0.0, "sugar_water": 0.0}
    assert taste["stimulation_enabled"] is False

    # Human diagnostics may keep exact geometry, but neural input must not.
    assert diagnostics["olfaction"]["food"]["source"] is not None
    assert "nearest_enemy" in diagnostics["vision"]
    assert diagnostics["antennal_mechanosensation"]["diagnostics"]["airflow_world"]
    assert diagnostics["gustation"]["contact"] is False
    assert diagnostics["contact_mechanosensation"]["contact"] is False
    assert "source" not in agent["olfaction"]["food"]
    assert "distance_cells" not in agent["olfaction"]["food"]
    assert "diagnostics" not in mech
    assert "airflow_world" not in mech

    assert_unprivileged_agent_input(agent)


def test_mechanosensation_is_unavailable_without_world_airflow() -> None:
    grid, fly, enemies = _world()
    agent = build_sensory_contract(grid=grid, fly=fly, enemies=enemies)["agent_input"]

    mech = agent["antennal_mechanosensation"]
    assert mech["available"] is False
    assert mech["status"] == "no-airflow-field"


def test_gustation_requires_contact_event_not_visible_food() -> None:
    grid, fly, enemies = _world()

    without_contact = build_sensory_contract(
        grid=grid,
        fly=fly,
        enemies=enemies,
    )["agent_input"]["gustation"]
    assert without_contact["contact"] is False
    assert without_contact["channels"] == {"bitter": 0.0, "sugar_water": 0.0}

    after_contact = build_sensory_contract(
        grid=grid,
        fly=fly,
        enemies=enemies,
        gustatory_event="food",
    )["agent_input"]["gustation"]
    assert after_contact["contact"] is True
    assert after_contact["channels"] == {"bitter": 0.0, "sugar_water": 1.0}
    assert after_contact["stimulation_enabled"] is False


def test_tactile_requires_explicit_physical_contact_signal() -> None:
    grid, fly, enemies = _world()

    without_contact = build_sensory_contract(
        grid=grid,
        fly=fly,
        enemies=enemies,
    )["agent_input"]["contact_mechanosensation"]
    assert without_contact["contact"] is False
    assert without_contact["channels"] == {"front": 0.0}

    after_contact = build_sensory_contract(
        grid=grid,
        fly=fly,
        enemies=enemies,
        tactile_contact=True,
    )["agent_input"]["contact_mechanosensation"]
    assert after_contact["contact"] is True
    assert after_contact["channels"] == {"front": 1.0}
    assert after_contact["stimulation_enabled"] is False
    assert "object_id" not in after_contact
    assert "collision_normal" not in after_contact
    assert "wall_coordinates" not in after_contact


def test_future_modalities_are_reserved_not_invented() -> None:
    grid, fly, enemies = _world()
    agent = build_sensory_contract(grid=grid, fly=fly, enemies=enemies)["agent_input"]

    for name in (
        "proprioception",
        "thermo_hygrosensation",
        "polarized_light",
    ):
        assert agent[name]["available"] is False
        assert agent[name]["status"] == "pending-biological-mapping"


def test_privileged_world_truth_is_rejected_recursively() -> None:
    with pytest.raises(ValueError, match="Privileged field"):
        assert_unprivileged_agent_input(
            {
                "olfaction": {
                    "food": {
                        "left": 0.4,
                        "right": 0.7,
                        "source": {"x": 9, "y": 4},
                    }
                }
            }
        )

    with pytest.raises(ValueError, match="Privileged field"):
        assert_unprivileged_agent_input(
            {
                "antennal_mechanosensation": {
                    "left": {"jo_c": 0.2, "jo_e": 0.0},
                    "airflow_world": {"x": 1.0, "y": 0.0},
                }
            }
        )

    for forbidden in ("object_id", "collision_normal", "wall_coordinates"):
        with pytest.raises(ValueError, match="Privileged field"):
            assert_unprivileged_agent_input(
                {"contact_mechanosensation": {forbidden: "human-debug-only"}}
            )
