from __future__ import annotations

from neurofly.curriculum import (
    AMBIENT_AIRFLOW_POLICY,
    AMBIENT_AIRFLOW_WORLD,
    CurriculumMazeEnvironment,
)
from neurofly.mechanosensation import MECHANOSENSATION_MODEL
from neurofly.sensory_contract import assert_unprivileged_agent_input


def test_curriculum_exposes_strict_default_ambient_mechanosensation() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    state = env.snapshot(include_grid=False)
    mech = state["antennal_mechanosensation"]

    assert state["ambient_airflow_policy"] == AMBIENT_AIRFLOW_POLICY
    assert mech["model"] == MECHANOSENSATION_MODEL
    assert mech["available"] is True
    assert mech["left"] == {"jo_c": 0.42, "jo_e": 0.0}
    assert mech["right"] == {"jo_c": 0.0, "jo_e": 0.42}

    assert "diagnostics" not in mech
    assert "airflow_world" not in mech
    assert "body_relative" not in mech
    assert "signed_deflection" not in mech
    assert "ambient_airflow_world" not in state
    assert_unprivileged_agent_input({"antennal_mechanosensation": mech})


def test_same_world_wind_changes_fly_relative_channels_with_heading() -> None:
    env = CurriculumMazeEnvironment(seed=109)

    env.fly["dir"] = "RIGHT"
    right_facing = env.snapshot(include_grid=False)["antennal_mechanosensation"]

    env.fly["dir"] = "UP"
    up_facing = env.snapshot(include_grid=False)["antennal_mechanosensation"]

    assert right_facing["left"] == {"jo_c": 0.42, "jo_e": 0.0}
    assert right_facing["right"] == {"jo_c": 0.0, "jo_e": 0.42}
    assert up_facing["left"] == {"jo_c": 0.0, "jo_e": 0.6}
    assert up_facing["right"] == {"jo_c": 0.0, "jo_e": 0.6}


def test_ambient_airflow_is_independent_of_food_enemy_and_reward_truth() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    env.fly["dir"] = "RIGHT"
    before = env.snapshot(include_grid=False)["antennal_mechanosensation"]

    for row in env.grid:
        for x, cell in enumerate(row):
            if cell in {".", "o"}:
                row[x] = " "
    env.enemies = [{"x": 2, "y": 2}, {"x": 3, "y": 3}]
    env.last_reward = 999.0
    env.episode_reward = -999.0

    after = env.snapshot(include_grid=False)["antennal_mechanosensation"]

    assert after == before


def test_checkpoint_records_airflow_provenance_without_routing_world_vector_to_brain_context() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    runtime_state = env.snapshot(include_grid=False)
    persisted = env.persistence_snapshot()

    assert "ambient_airflow_world" not in runtime_state
    assert persisted["ambient_airflow_policy"] == AMBIENT_AIRFLOW_POLICY
    assert persisted["ambient_airflow_world"] == {
        "x": AMBIENT_AIRFLOW_WORLD[0],
        "y": AMBIENT_AIRFLOW_WORLD[1],
    }
