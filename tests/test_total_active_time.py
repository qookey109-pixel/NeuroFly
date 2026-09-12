from __future__ import annotations

from neurofly import goal_training
from neurofly.goal_training import GoalMazeEnvironment


def test_total_active_time_keeps_running_across_reset_and_checkpoint(monkeypatch) -> None:
    clock = {"now": 100.0}
    monkeypatch.setattr(goal_training.time, "monotonic", lambda: clock["now"])

    env = GoalMazeEnvironment(seed=109)
    clock["now"] = 112.5
    assert env.snapshot()["total_active_seconds"] == 12.5

    env.reset("captured")
    clock["now"] = 120.0
    assert env.snapshot()["total_active_seconds"] == 20.0

    payload = env.persistence_snapshot()
    clock["now"] = 500.0
    restored = GoalMazeEnvironment(seed=999)
    restored.restore(payload)

    assert restored.snapshot()["total_active_seconds"] == 20.0
    clock["now"] = 505.25
    assert restored.snapshot()["total_active_seconds"] == 25.2
