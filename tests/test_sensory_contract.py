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
    contract = build_sensory_contract(grid=grid, fly=fly, enemies=enemies)

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

    # Human diagnostics may keep exact geometry, but neural input must not.
    assert diagnostics["olfaction"]["food"]["source"] is not None
    assert "nearest_enemy" in diagnostics["vision"]
    assert "source" not in agent["olfaction"]["food"]
    assert "distance_cells" not in agent["olfaction"]["food"]

    assert_unprivileged_agent_input(agent)


def test_future_modalities_are_reserved_not_invented() -> None:
    grid, fly, enemies = _world()
    agent = build_sensory_contract(grid=grid, fly=fly, enemies=enemies)["agent_input"]

    for name in (
        "antennal_mechanosensation",
        "proprioception",
        "contact_mechanosensation",
        "gustation",
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
