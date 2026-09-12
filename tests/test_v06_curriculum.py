from __future__ import annotations

from neurofly.curriculum import (
    ANTI_STALL_POLICY,
    ANTI_STALL_STATIONARY_LIMIT,
    CURRICULUM_VERSION,
    CurriculumMazeEnvironment,
)
from neurofly.goal_training import GoalMazeEnvironment
from neurofly.olfaction import DANGER_ORN_TYPE, FOOD_ORN_TYPE, OLFACTION_MODEL, virtual_olfaction
from neurofly.site_state import _digest_json, build_site_state
from neurofly.upstream import STONKFLY_COMMIT


def _make_next_forward_clear(env: CurriculumMazeEnvironment) -> None:
    for y, row in enumerate(env.grid):
        for x, cell in enumerate(row):
            if cell in {".", "o"}:
                env.grid[y][x] = " "
    env.fly["dir"] = "RIGHT"
    target_x = env.fly["x"] + 1
    target_y = env.fly["y"]
    assert env.grid[target_y][target_x] != "#"
    env.grid[target_y][target_x] = "."


def test_curriculum_starts_on_full_canonical_maze() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    canonical = GoalMazeEnvironment(seed=109)
    state = env.snapshot()

    assert state["curriculum_version"] == CURRICULUM_VERSION
    assert state["curriculum_stage"] == 1
    assert state["curriculum_stage_name"] == "full-maze-food-only"
    assert state["curriculum_enemy_count"] == 0
    assert state["curriculum_clears_to_advance"] == 2
    assert env.enemies == []
    assert env.grid == canonical.grid
    assert env.fly == canonical.fly
    assert env.food_left() == canonical.food_left()
    assert env.effective_world_tick_seconds(0.5) == 1.0
    assert state["olfaction"]["model"] == OLFACTION_MODEL
    assert state["olfaction"]["food"]["intensity"] > 0
    assert state["olfaction"]["danger"]["intensity"] == 0
    assert state["anti_stall_policy"] == ANTI_STALL_POLICY


def test_virtual_odor_field_is_bilateral_and_directional() -> None:
    grid = [[" " for _ in range(7)] for _ in range(7)]
    grid[2][3] = "."
    fly = {"x": 3, "y": 3, "dir": "RIGHT"}
    enemies = [{"x": 3, "y": 4}]

    odor = virtual_olfaction(grid=grid, fly=fly, enemies=enemies)

    # Facing right: north is the fly's left side and south is its right side.
    assert odor["food"]["left"] > odor["food"]["right"]
    assert odor["danger"]["right"] > odor["danger"]["left"]
    assert odor["food"]["orn_type"] == FOOD_ORN_TYPE
    assert odor["danger"]["orn_type"] == DANGER_ORN_TYPE


def test_anti_stall_preserves_raw_action_and_forces_one_forward_attempt() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    start = dict(env.fly)

    for _ in range(ANTI_STALL_STATIONARY_LIMIT):
        env.agent_step("HOLD", move_enemies=False)

    assert env.fly["x"] == start["x"]
    assert env.fly["y"] == start["y"]

    env.agent_step("HOLD", move_enemies=False)
    state = env.snapshot()

    assert state["raw_brain_action"] == "HOLD"
    assert state["applied_action"] == "FORWARD"
    assert state["action_overridden"] is True
    assert state["override_reason"] == "anti_stall_hold_forward"
    assert state["last_action"] == "FORWARD"
    assert env.fly["x"] == start["x"] + 1
    assert env.fly["y"] == start["y"]
    assert state["anti_stall_stationary_steps"] == 0


def test_anti_stall_state_survives_curriculum_checkpoint() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    env.agent_step("HOLD", move_enemies=False)
    env.agent_step("HOLD", move_enemies=False)
    payload = env.persistence_snapshot()

    restored = CurriculumMazeEnvironment(seed=999)
    restored.restore(payload)
    state = restored.snapshot()

    assert state["anti_stall_policy"] == ANTI_STALL_POLICY
    assert state["anti_stall_stationary_steps"] == 2
    assert state["raw_brain_action"] == "HOLD"
    assert state["applied_action"] == "HOLD"
    assert state["action_overridden"] is False


def test_two_verified_clears_promote_stage_one_to_full_maze_slow_predator() -> None:
    env = CurriculumMazeEnvironment(seed=109)

    _make_next_forward_clear(env)
    first = env.agent_step("FORWARD", move_enemies=False)
    assert first.event == "maze_cleared"
    env.reset("maze_cleared")
    assert env.curriculum_stage == 1
    assert env.stage_clear_counts["1"] == 1

    _make_next_forward_clear(env)
    second = env.agent_step("FORWARD", move_enemies=False)
    assert second.event == "maze_cleared"
    env.reset("maze_cleared")

    canonical = GoalMazeEnvironment(seed=109)
    assert env.curriculum_stage == 2
    assert env.stage.name == "full-maze-slow-predator"
    assert env.stage_clear_counts["1"] == 2
    assert len(env.enemies) == 1
    assert env.grid == canonical.grid
    assert env.fly == canonical.fly
    assert len(env.stage_history) == 2


def test_predator_pressure_increases_without_changing_maze_geometry() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    canonical = GoalMazeEnvironment(seed=109)

    env.curriculum_stage = 2
    env.reset("test")
    state = env.snapshot()
    assert env.stage.name == "full-maze-slow-predator"
    assert len(env.enemies) == 1
    assert env.effective_world_tick_seconds(0.5) == 2.0
    assert env.grid == canonical.grid
    assert state["olfaction"]["danger"]["intensity"] > 0

    env.curriculum_stage = 3
    env.reset("test")
    assert env.stage.name == "full-maze-predator"
    assert len(env.enemies) == 1
    assert env.effective_world_tick_seconds(0.5) == 1.0
    assert env.grid == canonical.grid

    env.curriculum_stage = 4
    env.reset("test")
    assert env.stage.name == "full-live-maze"
    assert len(env.enemies) == 2
    assert env.effective_world_tick_seconds(9.0) == 0.5
    assert env.grid == canonical.grid


def test_curriculum_checkpoint_preserves_eaten_food() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    baseline_food = env.food_left()
    food_xy = next(
        (x, y)
        for y, row in enumerate(env.grid)
        for x, cell in enumerate(row)
        if cell in {".", "o"}
    )
    x, y = food_xy
    env.grid[y][x] = " "
    payload = env.persistence_snapshot()

    restored = CurriculumMazeEnvironment(seed=999)
    restored.restore(payload)

    assert restored.curriculum_stage == 1
    assert restored.grid[y][x] == " "
    assert restored.food_left() == baseline_food - 1


def test_v05_state_migrates_to_full_maze_stage_one_without_erasing_global_totals() -> None:
    old = GoalMazeEnvironment(seed=109)
    old.total_ticks = 17
    old.total_world_ticks = 99
    old.total_food = 3
    payload = old.persistence_snapshot()

    migrated = CurriculumMazeEnvironment(seed=109)
    migrated.restore(payload)

    assert migrated.curriculum_stage == 1
    assert migrated.stage.name == "full-maze-food-only"
    assert migrated.enemies == []
    assert migrated.grid == old.grid
    assert migrated.food_left() == old.food_left()
    assert migrated.total_ticks == 17
    assert migrated.total_world_ticks == 99
    assert migrated.total_food == 3


def test_v1_enemy_free_checkpoint_migrates_safely_to_v2_full_maze() -> None:
    source = CurriculumMazeEnvironment(seed=109)
    payload = source.persistence_snapshot()
    payload["curriculum_version"] = "neurofly-curriculum-v1"
    payload["enemies"] = []

    restored = CurriculumMazeEnvironment(seed=109)
    restored.restore(payload)
    canonical = GoalMazeEnvironment(seed=109)

    assert restored.curriculum_stage == 1
    assert restored.stage.name == "full-maze-food-only"
    assert restored.enemies == []
    assert restored.grid == canonical.grid


def test_v3_curriculum_receipt_is_verified_for_site_state() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    state = env.snapshot()
    state["last_action"] = "HOLD"
    state["world_tick_seconds"] = 1.0
    state["state_kind"] = "neural_decision"
    state["decision_applied"] = True
    state["brain"] = {
        "backend": "malecns",
        "telemetry": {
            "brain_ms": 500.0,
            "total_spikes": 123,
            "olfaction_model": OLFACTION_MODEL,
            "food_odor_spikes": 11,
            "danger_odor_spikes": 0,
        },
    }
    receipt = {
        "schema": "neurofly-self-training-v3",
        "passed": True,
        "backend": "malecns",
        "neural_activity_verified": True,
        "goal": "maze_cleared",
        "stonkfly_commit": STONKFLY_COMMIT,
        "steps": 1,
        "world_tick_seconds": 1.0,
        "world_states_seen": 1,
        "curriculum": True,
        "curriculum_version": CURRICULUM_VERSION,
        "olfaction_model": OLFACTION_MODEL,
        "olfaction": {
            "model": OLFACTION_MODEL,
            "engineered_proxy": True,
            "food": {
                "orn_type": FOOD_ORN_TYPE,
                "left_neurons": 1,
                "right_neurons": 1,
            },
            "danger": {
                "orn_type": DANGER_ORN_TYPE,
                "left_neurons": 1,
                "right_neurons": 1,
            },
        },
        "trajectory": [state],
        "final_state": state,
    }
    receipt["receipt_sha256"] = _digest_json(receipt)

    site = build_site_state(receipt)

    assert site["verified"] is True
    assert site["source_receipt_schema"] == "neurofly-self-training-v3"
    assert site["curriculum"] is True
    assert site["curriculum_version"] == CURRICULUM_VERSION
    assert site["olfaction_model"] == OLFACTION_MODEL
    assert site["final_state"]["curriculum_stage"] == 1
