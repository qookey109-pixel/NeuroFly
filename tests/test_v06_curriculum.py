from __future__ import annotations

from neurofly.curriculum import CURRICULUM_VERSION, CurriculumMazeEnvironment
from neurofly.goal_training import GoalMazeEnvironment
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


def test_curriculum_starts_with_safe_food_corridor() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    state = env.snapshot()

    assert state["curriculum_version"] == CURRICULUM_VERSION
    assert state["curriculum_stage"] == 1
    assert state["curriculum_stage_name"] == "food-corridor"
    assert state["curriculum_enemy_count"] == 0
    assert state["curriculum_clears_to_advance"] == 2
    assert env.enemies == []
    assert env.food_left() == 5
    assert env.effective_world_tick_seconds(0.5) == 1.0


def test_two_verified_clears_promote_stage_one_to_turning_food() -> None:
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

    assert env.curriculum_stage == 2
    assert env.stage.name == "turning-food"
    assert env.stage_clear_counts["1"] == 2
    assert env.enemies == []
    assert len(env.stage_history) == 2


def test_later_stages_restore_predators_gradually() -> None:
    env = CurriculumMazeEnvironment(seed=109)

    env.curriculum_stage = 3
    env.reset("test")
    assert env.stage.name == "slow-predator"
    assert len(env.enemies) == 1
    assert env.effective_world_tick_seconds(0.5) == 2.0

    env.curriculum_stage = 4
    env.reset("test")
    assert env.stage.name == "full-live-maze"
    assert len(env.enemies) == 2
    assert env.effective_world_tick_seconds(9.0) == 0.5


def test_curriculum_checkpoint_preserves_eaten_food() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    assert env.grid[7][4] == "."
    env.grid[7][4] = " "
    payload = env.persistence_snapshot()

    restored = CurriculumMazeEnvironment(seed=999)
    restored.restore(payload)

    assert restored.curriculum_stage == 1
    assert restored.grid[7][4] == " "
    assert restored.food_left() == 4


def test_v05_state_migrates_to_stage_one_without_erasing_global_totals() -> None:
    old = GoalMazeEnvironment(seed=109)
    old.total_ticks = 17
    old.total_world_ticks = 99
    old.total_food = 3
    payload = old.persistence_snapshot()

    migrated = CurriculumMazeEnvironment(seed=109)
    migrated.restore(payload)

    assert migrated.curriculum_stage == 1
    assert migrated.enemies == []
    assert migrated.food_left() == 5
    assert migrated.total_ticks == 17
    assert migrated.total_world_ticks == 99
    assert migrated.total_food == 3


def test_v3_curriculum_receipt_is_verified_for_site_state() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    state = env.snapshot()
    state["last_action"] = "HOLD"
    state["world_tick_seconds"] = 1.0
    state["state_kind"] = "neural_decision"
    state["decision_applied"] = True
    state["brain"] = {
        "backend": "malecns",
        "telemetry": {"brain_ms": 500.0, "total_spikes": 123},
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
        "trajectory": [state],
        "final_state": state,
    }
    receipt["receipt_sha256"] = _digest_json(receipt)

    site = build_site_state(receipt)

    assert site["verified"] is True
    assert site["source_receipt_schema"] == "neurofly-self-training-v3"
    assert site["curriculum"] is True
    assert site["curriculum_version"] == CURRICULUM_VERSION
    assert site["final_state"]["curriculum_stage"] == 1
