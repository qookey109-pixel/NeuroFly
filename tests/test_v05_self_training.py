from __future__ import annotations

import time
from pathlib import Path

from neurofly.brain_runtime import BrainDecision
from neurofly.goal_training import GoalMazeEnvironment, GoalMazeSession
from neurofly.site_state import _digest_json, build_site_state
from neurofly.upstream import STONKFLY_COMMIT


def _leave_only_one_food(env: GoalMazeEnvironment) -> None:
    for y, row in enumerate(env.grid):
        for x, cell in enumerate(row):
            if cell != "#":
                env.grid[y][x] = " "
    env.fly = {"x": 1, "y": 1, "dir": "RIGHT"}
    env.grid[1][2] = "."
    env.enemies = [{"x": env.cols - 2, "y": env.rows - 2}]


class SlowMaleCNSFixture:
    name = "malecns"

    def __init__(self, *, delay: float = 0.05) -> None:
        self.delay = delay
        self.reinforcements: list[str] = []

    def decide(self, frame, reinforcement="none", *, context=None) -> BrainDecision:
        self.reinforcements.append(reinforcement)
        time.sleep(self.delay)
        return BrainDecision(
            action="HOLD",
            backend="malecns",
            telemetry={
                "brain_ms": 500.0,
                "compute_seconds": self.delay,
                "total_spikes": 42,
            },
        )

    def save(self, path: str | Path) -> None:
        return None


def test_maze_clear_is_dominant_goal_and_records_first_clear() -> None:
    env = GoalMazeEnvironment(seed=7)
    _leave_only_one_food(env)

    result = env.step("FORWARD")

    assert result.terminal is True
    assert result.event == "maze_cleared"
    assert result.reward > 100.0
    assert env.total_clears == 1
    assert len(env.clear_history) == 1
    state = env.snapshot()
    assert state["goal"] == "maze_cleared"
    assert state["first_clear_seconds"] is not None
    assert state["first_clear_ticks"] == 1
    assert state["latest_clear_ticks"] == 1
    assert state["best_clear_ticks"] == 1
    assert "total_world_ticks" in state


def test_enemy_contact_always_restarts_even_during_power_state() -> None:
    env = GoalMazeEnvironment(seed=3)
    env.power_ticks = 20
    env.enemies = [{"x": env.fly["x"], "y": env.fly["y"]}]
    env._move_enemies = lambda: None  # type: ignore[method-assign]

    result = env.step("HOLD")

    assert result.terminal is True
    assert result.event == "captured"
    assert result.reward < -9.0
    assert env.total_deaths == 1


def test_world_clock_can_capture_during_brain_compute_and_discard_stale_action() -> None:
    brain = SlowMaleCNSFixture(delay=0.05)
    session = GoalMazeSession(brain, world_tick_seconds=0.01)
    session.environment.render_rgb = lambda: None  # type: ignore[method-assign]

    calls = 0

    def capture_once() -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            session.environment.enemies[0] = {
                "x": session.environment.fly["x"],
                "y": session.environment.fly["y"],
            }

    session.environment._move_enemies = capture_once  # type: ignore[method-assign]
    world_states: list[dict] = []

    stale = session.tick(on_world_tick=world_states.append)

    assert stale["state_kind"] == "stale_decision"
    assert stale["decision_applied"] is False
    assert stale["step_event"] == "decision_discarded"
    assert session.environment.episode == 2
    assert session.environment.total_deaths == 1
    assert session.pending_reinforcement == "aversive"
    assert any(
        state.get("state_kind") == "world_tick" and state.get("step_event") == "captured"
        for state in world_states
    )
    assert any(state.get("state_kind") == "episode_reset" for state in world_states)

    session.tick()
    assert brain.reinforcements[:2] == ["none", "aversive"]


def test_clear_history_and_world_clock_survive_checkpoint_payload() -> None:
    env = GoalMazeEnvironment(seed=11)
    _leave_only_one_food(env)
    env.world_step()
    env.step("FORWARD")
    payload = env.persistence_snapshot()

    restored = GoalMazeEnvironment(seed=99)
    restored.restore(payload)

    assert restored.total_clears == 1
    assert restored.clear_history == env.clear_history
    assert restored.snapshot()["first_clear_ticks"] == 1
    assert restored.total_world_ticks == env.total_world_ticks


def test_verified_self_training_v2_receipt_can_drive_site() -> None:
    neural_state = {
        "grid": ["###", "# #", "###"],
        "fly": {"x": 1, "y": 1, "dir": "RIGHT"},
        "enemies": [{"x": 1, "y": 1}],
        "last_action": "HOLD",
        "goal": "maze_cleared",
        "state_kind": "neural_decision",
        "decision_applied": True,
        "world_ticks": 3,
        "total_world_ticks": 9,
        "total_clears": 0,
        "clear_history": [],
        "brain": {
            "backend": "malecns",
            "telemetry": {"brain_ms": 500.0, "total_spikes": 42},
        },
    }
    receipt = {
        "schema": "neurofly-self-training-v2",
        "passed": True,
        "backend": "malecns",
        "neural_activity_verified": True,
        "goal": "maze_cleared",
        "stonkfly_commit": STONKFLY_COMMIT,
        "steps": 1,
        "world_tick_seconds": 0.5,
        "world_states_seen": 3,
        "trajectory": [neural_state],
        "final_state": neural_state,
        "reward_policy": {"maze_cleared": 100.0},
    }
    receipt["receipt_sha256"] = _digest_json(receipt)

    site = build_site_state(receipt)

    assert site["verified"] is True
    assert site["backend"] == "malecns"
    assert site["goal"] == "maze_cleared"
    assert site["source_receipt_schema"] == "neurofly-self-training-v2"
    assert site["world_tick_seconds"] == 0.5
