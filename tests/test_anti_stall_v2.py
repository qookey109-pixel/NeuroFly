from __future__ import annotations

from neurofly.curriculum import (
    ANTI_STALL_LOOP_WINDOW,
    ANTI_STALL_POLICY,
    CurriculumMazeEnvironment,
)


def test_anti_stall_v2_breaks_two_cell_local_loop_transparently() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    first = (int(env.fly["x"]), int(env.fly["y"]))
    second = (first[0] + 1, first[1])
    assert env.grid[second[1]][second[0]] != "#"

    env._recent_positions = [first, second] * (ANTI_STALL_LOOP_WINDOW // 2)
    env.fly["x"], env.fly["y"] = first

    env.agent_step("HOLD", move_enemies=False)
    state = env.snapshot()

    assert state["anti_stall_policy"] == ANTI_STALL_POLICY
    assert state["raw_brain_action"] == "HOLD"
    assert state["applied_action"] in {"TURN_LEFT", "TURN_RIGHT"}
    assert state["action_overridden"] is True
    assert state["override_reason"] in {
        "anti_stall_local_loop_turn_left",
        "anti_stall_local_loop_turn_right",
    }
    assert state["anti_stall_force_forward_next"] is True
    assert len(state["anti_stall_recent_positions"]) == 1

    env.agent_step("HOLD", move_enemies=False)
    followup = env.snapshot()

    assert followup["raw_brain_action"] == "HOLD"
    assert followup["applied_action"] == "FORWARD"
    assert followup["action_overridden"] is True
    assert followup["override_reason"] == "anti_stall_followup_forward"
    assert followup["anti_stall_force_forward_next"] is False


def test_anti_stall_v2_motion_history_survives_checkpoint() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    start = (int(env.fly["x"]), int(env.fly["y"]))
    env._recent_positions = [start, (start[0] + 1, start[1]), start]
    env._loop_turn_right = False

    payload = env.persistence_snapshot()
    restored = CurriculumMazeEnvironment(seed=999)
    restored.restore(payload)
    state = restored.snapshot()

    assert state["anti_stall_policy"] == ANTI_STALL_POLICY
    assert state["anti_stall_recent_positions"] == [
        [start[0], start[1]],
        [start[0] + 1, start[1]],
        [start[0], start[1]],
    ]
    assert state["anti_stall_loop_turn_right"] is False


def test_anti_stall_v1_checkpoint_resumes_without_fake_loop_history() -> None:
    env = CurriculumMazeEnvironment(seed=109)
    payload = env.persistence_snapshot()
    payload["anti_stall_policy"] = "neurofly-curriculum-anti-stall-v1"
    payload["anti_stall_recent_positions"] = [[1, 1], [2, 1]] * 4

    restored = CurriculumMazeEnvironment(seed=109)
    restored.restore(payload)
    state = restored.snapshot()

    assert state["anti_stall_policy"] == ANTI_STALL_POLICY
    assert state["anti_stall_recent_positions"] == [
        [int(restored.fly["x"]), int(restored.fly["y"])]
    ]
    assert state["anti_stall_recent_unique_positions"] == 1
