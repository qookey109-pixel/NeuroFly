from __future__ import annotations

import time
from pathlib import Path

from neurofly.brain_runtime import BrainDecision
from neurofly.goal_training import GoalMazeEnvironment, GoalMazeSession


class FastMaleCNSFixture:
    name = "malecns"

    def __init__(self, *, delay: float = 0.012) -> None:
        self.delay = delay

    def decide(self, frame, reinforcement="none", *, context=None) -> BrainDecision:
        time.sleep(self.delay)
        return BrainDecision(
            action="HOLD",
            backend="malecns",
            telemetry={
                "brain_ms": 50.0,
                "compute_seconds": self.delay,
                "total_spikes": 42,
            },
        )

    def save(self, path: str | Path) -> None:
        return None


def test_world_clock_carries_remaining_delay_across_fast_decisions() -> None:
    env = GoalMazeEnvironment(seed=109)
    # Keep the test focused on timing rather than collision/RNG movement.
    env._move_enemies = lambda: None  # type: ignore[method-assign]
    brain = FastMaleCNSFixture(delay=0.012)
    session = GoalMazeSession(
        brain,
        environment=env,
        world_tick_seconds=0.025,
    )
    session.environment.render_rgb = lambda: None  # type: ignore[method-assign]

    before = session.environment.total_world_ticks
    for _ in range(4):
        session.tick()

    # Each neural decision is faster than one world interval. The old clock
    # restarted the full 25 ms timer every decision and would remain at zero.
    # The persistent deadline must allow at least one predator/world tick.
    assert session.environment.total_world_ticks > before
