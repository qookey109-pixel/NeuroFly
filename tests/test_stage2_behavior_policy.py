from __future__ import annotations

from neurofly.curriculum import (
    STALL_STIMULUS_AFTER,
    CurriculumMazeEnvironment,
)
from neurofly.olfaction import (
    OLFACTION_FIELD_NORMALIZATION,
    OLFACTION_MODEL,
    virtual_olfaction,
)


def test_dense_food_field_preserves_directional_contrast_without_action_hint() -> None:
    # Dense food surrounds the fly, but removing two far-left columns leaves a
    # modest rightward bias. Under independent clipping both bilateral LP4
    # channels exceed 1 and collapse to exactly 1.0, erasing that bias.
    grid = [["." for _ in range(9)] for _ in range(9)]
    for y in range(9):
        grid[y][0] = " "
        grid[y][1] = " "
    grid[4][4] = " "

    odor = virtual_olfaction(
        grid=grid,
        fly={"x": 4, "y": 4, "dir": "UP"},
        enemies=[],
    )
    food = odor["food"]

    assert odor["model"] == "neurofly-virtual-olfaction-v4"
    assert OLFACTION_MODEL == "neurofly-virtual-olfaction-v4"
    assert food["normalization"] == OLFACTION_FIELD_NORMALIZATION
    assert OLFACTION_FIELD_NORMALIZATION == "shared-peak-preserve-contrast-v1"
    assert food["source_count"] == 62
    assert 0.0 <= food["left"] < food["right"] <= 1.0
    assert food["right"] - food["left"] > 0.08
    assert max(food["left"], food["right"], food["front"], food["back"]) == 1.0
    assert "source" not in food


def test_single_enemy_danger_field_stays_bounded_and_directional() -> None:
    grid = [[" " for _ in range(9)] for _ in range(9)]
    odor = virtual_olfaction(
        grid=grid,
        fly={"x": 4, "y": 4, "dir": "UP"},
        enemies=[{"x": 7, "y": 4}],
    )
    danger = odor["danger"]

    assert danger["source_count"] == 1
    assert danger["normalization"] == OLFACTION_FIELD_NORMALIZATION
    assert 0.0 <= danger["left"] < danger["right"] <= 1.0
    assert danger["right"] - danger["left"] > 0.10


def test_in_place_turning_counts_as_stall_without_overriding_action() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    start_xy = (env.fly["x"], env.fly["y"])

    for step in range(1, STALL_STIMULUS_AFTER + 1):
        action = "TURN_LEFT" if step % 2 else "TURN_RIGHT"
        env.agent_step(action, move_enemies=False)
        state = env.snapshot()
        assert (env.fly["x"], env.fly["y"]) == start_xy
        assert state["anti_stall_stationary_steps"] == step
        assert state["raw_brain_action"] == action
        assert state["applied_action"] == action
        assert state["action_overridden"] is False
        assert state["direct_action_override_enabled"] is False

    assert env.reinforcement() == "aversive"


def test_successful_translation_resets_stall_counter() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    env.agent_step("TURN_LEFT", move_enemies=False)
    env.agent_step("TURN_RIGHT", move_enemies=False)
    assert env.snapshot()["anti_stall_stationary_steps"] == 2

    before = (env.fly["x"], env.fly["y"])
    env.agent_step("FORWARD", move_enemies=False)
    after = (env.fly["x"], env.fly["y"])

    assert after != before
    assert env.snapshot()["anti_stall_stationary_steps"] == 0
