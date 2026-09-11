from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .brain_runtime import BrainBackend, BrainDecision
from .maze_runtime import MazeEnvironment


class GoalMazeEnvironment(MazeEnvironment):
    """Maze variant whose dominant objective is clearing the level.

    The agent still receives sparse shaping for food so reinforcement can begin
    before the first full clear, but maze completion is intentionally much more
    valuable than any intermediate event. Enemy contact always terminates the
    episode, even while the power timer is active.
    """

    step_cost = -0.01
    food_reward = 1.0
    energy_food_reward = 2.0
    captured_penalty = -10.0
    clear_reward = 100.0

    def __init__(self, *, seed: int = 109) -> None:
        self.total_ticks = 0
        self.clear_history: list[dict[str, Any]] = []
        super().__init__(seed=seed)

    def restore(self, payload: dict[str, Any]) -> None:
        super().restore(payload)
        self.total_ticks = max(self.ticks, int(payload.get("total_ticks", self.ticks)))
        history = payload.get("clear_history") or []
        if not isinstance(history, list):
            raise ValueError("Invalid clear history")
        cleaned: list[dict[str, Any]] = []
        for item in history:
            if not isinstance(item, dict):
                raise ValueError("Invalid clear history entry")
            cleaned.append(
                {
                    "clear_index": max(1, int(item.get("clear_index", len(cleaned) + 1))),
                    "episode": max(1, int(item.get("episode", 1))),
                    "seconds": max(0.0, float(item.get("seconds", 0.0))),
                    "ticks": max(1, int(item.get("ticks", 1))),
                    "total_ticks": max(1, int(item.get("total_ticks", 1))),
                }
            )
        self.clear_history = cleaned
        self.total_clears = max(self.total_clears, len(self.clear_history))

    def _record_clear(self) -> None:
        self.clear_history.append(
            {
                "clear_index": len(self.clear_history) + 1,
                "episode": self.episode,
                "seconds": round(time.monotonic() - self.started_monotonic, 3),
                "ticks": self.ticks,
                "total_ticks": self.total_ticks,
            }
        )

    def step(self, action: str):
        if action not in {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}:
            raise ValueError(f"Unknown maze action: {action}")

        self.ticks += 1
        self.total_ticks += 1
        self.last_action = action
        reward = self.step_cost
        event = None
        terminal = False
        self._move_fly(action)

        cell = self.grid[self.fly["y"]][self.fly["x"]]
        if cell == ".":
            self.grid[self.fly["y"]][self.fly["x"]] = " "
            reward += self.food_reward
            self.episode_food += 1
            self.total_food += 1
            event = "food"
        elif cell == "o":
            self.grid[self.fly["y"]][self.fly["x"]] = " "
            reward += self.energy_food_reward
            self.episode_food += 1
            self.total_food += 1
            self.power_ticks = 34
            event = "energy_food"

        self._move_enemies()
        if self._collision() is not None:
            reward += self.captured_penalty
            self.total_deaths += 1
            event = "captured"
            terminal = True

        if self.power_ticks > 0:
            self.power_ticks -= 1

        if not terminal and self.food_left() == 0:
            reward += self.clear_reward
            self.total_clears += 1
            self._record_clear()
            event = "maze_cleared"
            terminal = True

        self.last_reward = reward
        self.episode_reward += reward
        self.cumulative_reward += reward
        self.last_event = event

        # Import here to keep the base module as the authority for the result type.
        from .maze_runtime import StepResult

        return StepResult(reward=reward, event=event, terminal=terminal)

    def snapshot(self, *, include_grid: bool = True) -> dict[str, Any]:
        data = super().snapshot(include_grid=include_grid)
        first = self.clear_history[0] if self.clear_history else None
        latest = self.clear_history[-1] if self.clear_history else None
        best = min(self.clear_history, key=lambda item: item["seconds"]) if self.clear_history else None
        data.update(
            {
                "goal": "maze_cleared",
                "total_ticks": self.total_ticks,
                "clear_history": [dict(item) for item in self.clear_history],
                "first_clear_seconds": None if first is None else first["seconds"],
                "latest_clear_seconds": None if latest is None else latest["seconds"],
                "best_clear_seconds": None if best is None else best["seconds"],
                "first_clear_ticks": None if first is None else first["ticks"],
                "latest_clear_ticks": None if latest is None else latest["ticks"],
                "best_clear_ticks": None if best is None else best["ticks"],
            }
        )
        return data

    def persistence_snapshot(self) -> dict[str, Any]:
        data = super().persistence_snapshot()
        data.update(
            {
                "goal": "maze_cleared",
                "total_ticks": self.total_ticks,
                "clear_history": [dict(item) for item in self.clear_history],
            }
        )
        return data


class GoalMazeSession:
    def __init__(
        self,
        brain: BrainBackend,
        *,
        checkpoint: str | Path | None = None,
        checkpoint_every: float = 300.0,
        seed: int = 109,
    ) -> None:
        self.brain = brain
        self.environment = GoalMazeEnvironment(seed=seed)
        self.checkpoint = Path(checkpoint) if checkpoint else None
        self.checkpoint_every = float(checkpoint_every)
        self.last_checkpoint = time.monotonic()
        self.last_decision: BrainDecision | None = None

        if self.checkpoint:
            state_path = self.checkpoint.with_suffix(".maze.json")
            if state_path.exists():
                payload = json.loads(state_path.read_text())
                if not isinstance(payload, dict):
                    raise ValueError("Persisted maze state must be a JSON object")
                self.environment.restore(payload)

    def tick(self) -> dict[str, Any]:
        context = self.environment.snapshot(include_grid=False)
        frame = self.environment.render_rgb()
        decision = self.brain.decide(
            frame,
            self.environment.reinforcement(),
            context=context,
        )
        self.last_decision = decision
        result = self.environment.step(decision.action)
        terminal_snapshot = self.environment.snapshot()
        terminal_snapshot["brain"] = {
            "backend": decision.backend,
            "telemetry": decision.telemetry,
        }
        terminal_snapshot["step_event"] = result.event

        if result.terminal:
            self.environment.reset(result.event or "terminal")
        self._checkpoint_if_due()
        return terminal_snapshot

    def _checkpoint_if_due(self) -> None:
        if not self.checkpoint:
            return
        now = time.monotonic()
        if now - self.last_checkpoint < self.checkpoint_every:
            return
        self.save()
        self.last_checkpoint = now

    def save(self) -> None:
        if not self.checkpoint:
            return
        self.checkpoint.parent.mkdir(parents=True, exist_ok=True)
        self.brain.save(self.checkpoint)
        state_path = self.checkpoint.with_suffix(".maze.json")
        temporary = state_path.with_suffix(state_path.suffix + ".partial")
        temporary.write_text(json.dumps(self.environment.persistence_snapshot(), indent=2) + "\n")
        temporary.replace(state_path)

    def snapshot(self) -> dict[str, Any]:
        data = self.environment.snapshot()
        data["brain"] = {
            "backend": getattr(self.brain, "name", type(self.brain).__name__),
            "telemetry": {} if self.last_decision is None else self.last_decision.telemetry,
        }
        return data
