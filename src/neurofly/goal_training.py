from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .brain_runtime import BrainBackend, BrainDecision
from .maze_runtime import MazeEnvironment, StepResult


REINFORCEMENT_TRAIN_POLICY = "neurofly-event-reinforcement-train-v1"
REINFORCEMENT_EVENT_STEPS = {
    "food": 1,
    "energy_food": 2,
    "maze_cleared": 4,
    "captured": 2,
}


def _reinforcement_for_reward(reward: float) -> str:
    if reward >= 0.5:
        return "reward"
    if reward <= -0.5:
        return "aversive"
    return "none"


def _reinforcement_train_for_event(reward: float, event: str | None) -> tuple[str, int]:
    """Encode event salience as a short bounded pulse train.

    The retained MaleCNS receives the same reviewed pulse amplitude per neural
    decision. Salience is represented by repeating that pulse across a small,
    fixed number of subsequent decisions instead of multiplying current.
    """
    kind = _reinforcement_for_reward(reward)
    if kind == "none":
        return "none", 0
    steps = REINFORCEMENT_EVENT_STEPS.get(str(event), 1)
    return kind, int(steps)


class GoalMazeEnvironment(MazeEnvironment):
    step_cost = -0.01
    food_reward = 1.0
    energy_food_reward = 2.0
    captured_penalty = -10.0
    clear_reward = 100.0

    def __init__(self, *, seed: int = 109) -> None:
        self.total_ticks = 0
        self.total_world_ticks = 0
        self.clear_history: list[dict[str, Any]] = []
        self._active_seconds_offset = 0.0
        self._active_started_monotonic = time.monotonic()
        super().__init__(seed=seed)

    def reset(self, reason: str = "reset") -> None:
        super().reset(reason)
        self.world_ticks = 0

    def effective_world_tick_seconds(self, default: float) -> float:
        return float(default)

    def restore(self, payload: dict[str, Any]) -> None:
        super().restore(payload)
        self.total_ticks = max(self.ticks, int(payload.get("total_ticks", self.ticks)))
        self.world_ticks = max(0, int(payload.get("world_ticks", 0)))
        self.total_world_ticks = max(
            self.world_ticks,
            int(payload.get("total_world_ticks", self.world_ticks)),
        )
        restored_active = payload.get("total_active_seconds", payload.get("survival_seconds", 0.0))
        self._active_seconds_offset = max(0.0, float(restored_active))
        self._active_started_monotonic = time.monotonic()
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
                    "world_ticks": max(0, int(item.get("world_ticks", 0))),
                    "total_world_ticks": max(0, int(item.get("total_world_ticks", 0))),
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
                "world_ticks": self.world_ticks,
                "total_world_ticks": self.total_world_ticks,
            }
        )

    def _finish_reward(self, reward: float, event: str | None) -> None:
        self.last_reward = reward
        self.episode_reward += reward
        self.cumulative_reward += reward
        self.last_event = event

    def world_step(self) -> StepResult:
        self.world_ticks += 1
        self.total_world_ticks += 1
        self._move_enemies()
        if self._collision() is not None:
            self.total_deaths += 1
            reward = self.captured_penalty
            self._finish_reward(reward, "captured")
            return StepResult(reward=reward, event="captured", terminal=True)
        if self.power_ticks > 0:
            self.power_ticks -= 1
        self.last_reward = 0.0
        self.last_event = None
        return StepResult(reward=0.0, event=None, terminal=False)

    def agent_step(self, action: str, *, move_enemies: bool) -> StepResult:
        if action not in {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}:
            raise ValueError(f"Unknown maze action: {action}")

        self.ticks += 1
        self.total_ticks += 1
        self.last_action = action
        reward = self.step_cost
        event = None
        terminal = False
        self._move_fly(action)

        if self._collision() is not None:
            reward += self.captured_penalty
            self.total_deaths += 1
            event = "captured"
            terminal = True

        if not terminal:
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

        if not terminal and move_enemies:
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

        self._finish_reward(reward, event)
        return StepResult(reward=reward, event=event, terminal=terminal)

    def step(self, action: str) -> StepResult:
        return self.agent_step(action, move_enemies=True)

    def snapshot(self, *, include_grid: bool = True) -> dict[str, Any]:
        data = super().snapshot(include_grid=include_grid)
        first = self.clear_history[0] if self.clear_history else None
        latest = self.clear_history[-1] if self.clear_history else None
        best = min(self.clear_history, key=lambda item: item["seconds"]) if self.clear_history else None
        total_active_seconds = self._active_seconds_offset + (
            time.monotonic() - self._active_started_monotonic
        )
        data.update(
            {
                "goal": "maze_cleared",
                "total_ticks": self.total_ticks,
                "world_ticks": self.world_ticks,
                "total_world_ticks": self.total_world_ticks,
                "total_active_seconds": round(max(0.0, total_active_seconds), 1),
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
        total_active_seconds = self._active_seconds_offset + (
            time.monotonic() - self._active_started_monotonic
        )
        data.update(
            {
                "goal": "maze_cleared",
                "total_ticks": self.total_ticks,
                "world_ticks": self.world_ticks,
                "total_world_ticks": self.total_world_ticks,
                "total_active_seconds": round(max(0.0, total_active_seconds), 1),
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
        world_tick_seconds: float = 0.5,
        environment: GoalMazeEnvironment | None = None,
        decision_synchronous_world: bool = False,
    ) -> None:
        if world_tick_seconds <= 0:
            raise ValueError("world_tick_seconds must be > 0")
        self.brain = brain
        self.environment = environment or GoalMazeEnvironment(seed=seed)
        self.checkpoint = Path(checkpoint) if checkpoint else None
        self.checkpoint_every = float(checkpoint_every)
        self.world_tick_seconds = float(world_tick_seconds)
        self.decision_synchronous_world = bool(decision_synchronous_world)
        self.last_checkpoint = time.monotonic()
        self.last_decision: BrainDecision | None = None
        self.pending_reinforcement = "none"
        self.pending_reinforcement_steps = 0
        self._lock = threading.RLock()

        if self.checkpoint:
            state_path = self.checkpoint.with_suffix(".maze.json")
            if state_path.exists():
                payload = json.loads(state_path.read_text())
                if not isinstance(payload, dict):
                    raise ValueError("Persisted maze state must be a JSON object")
                self.environment.restore(payload)
                pending = str(payload.get("_pending_reinforcement", "none"))
                if pending in {"none", "reward", "aversive"}:
                    self.pending_reinforcement = pending
                restored_steps = int(payload.get("_pending_reinforcement_steps", 0))
                if self.pending_reinforcement != "none":
                    self.pending_reinforcement_steps = max(1, restored_steps)

        # Keep one absolute world-clock deadline across neural decisions. The old
        # per-decision timer restarted from a full interval every time tick() was
        # called, so fast 50 ms decisions could permanently starve enemy motion.
        # A fresh session intentionally starts a fresh deadline; offline time is
        # never replayed as a burst of predator movement after checkpoint restore.
        self._world_next_tick_monotonic = (
            time.monotonic() + self._effective_world_tick_seconds()
        )

    def _queue_reinforcement(self, reward: float, event: str | None) -> None:
        kind, steps = _reinforcement_train_for_event(reward, event)
        if steps <= 0:
            return
        self.pending_reinforcement = kind
        self.pending_reinforcement_steps = steps

    def _take_reinforcement(self) -> str:
        if self.pending_reinforcement_steps <= 0 or self.pending_reinforcement == "none":
            self.pending_reinforcement = "none"
            self.pending_reinforcement_steps = 0
            return "none"
        kind = self.pending_reinforcement
        self.pending_reinforcement_steps -= 1
        if self.pending_reinforcement_steps <= 0:
            self.pending_reinforcement = "none"
        return kind

    def _effective_world_tick_seconds(self) -> float:
        interval = float(self.environment.effective_world_tick_seconds(self.world_tick_seconds))
        if interval <= 0:
            raise ValueError("effective world tick interval must be > 0")
        return interval

    def _reset_world_clock_deadline(self) -> None:
        self._world_next_tick_monotonic = (
            time.monotonic() + self._effective_world_tick_seconds()
        )

    def _snapshot_locked(
        self,
        *,
        decision: BrainDecision | None = None,
        state_kind: str,
        step_event: str | None = None,
        decision_applied: bool | None = None,
    ) -> dict[str, Any]:
        data = self.environment.snapshot()
        active_decision = decision if decision is not None else self.last_decision
        data["brain"] = {
            "backend": getattr(self.brain, "name", type(self.brain).__name__),
            "telemetry": {} if active_decision is None else active_decision.telemetry,
        }
        data["state_kind"] = state_kind
        data["world_tick_seconds"] = self._effective_world_tick_seconds()
        if step_event is not None:
            data["step_event"] = step_event
        if decision is not None:
            data["decision_action"] = decision.action
        if decision_applied is not None:
            data["decision_applied"] = bool(decision_applied)
        return data

    @staticmethod
    def _emit(
        callback: Callable[[dict[str, Any]], None] | None,
        state: dict[str, Any],
    ) -> None:
        if callback is None:
            return
        try:
            callback(state)
        except Exception:
            return

    def _run_world_clock(
        self,
        *,
        observed_episode: int,
        stop_event: threading.Event,
        on_world_tick: Callable[[dict[str, Any]], None] | None,
    ) -> None:
        while True:
            delay = max(0.0, self._world_next_tick_monotonic - time.monotonic())
            if stop_event.wait(delay):
                # Crucially, do not reset the deadline here. The remaining delay
                # carries into the next neural decision.
                return
            emitted: list[dict[str, Any]] = []
            terminal = False
            with self._lock:
                if self.environment.episode != observed_episode:
                    return
                result = self.environment.world_step()
                emitted.append(
                    self._snapshot_locked(
                        state_kind="world_tick",
                        step_event=result.event,
                    )
                )
                terminal = result.terminal
                if terminal:
                    self._queue_reinforcement(result.reward, result.event)
                    self.environment.reset(result.event or "terminal")
                    self._reset_world_clock_deadline()
                    emitted.append(
                        self._snapshot_locked(
                            state_kind="episode_reset",
                            step_event="episode_reset",
                        )
                    )
                else:
                    self._reset_world_clock_deadline()
            for state in emitted:
                self._emit(on_world_tick, state)
            if terminal:
                return

    def tick(
        self,
        *,
        on_world_tick: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            observed_episode = self.environment.episode
            context = self.environment.snapshot(include_grid=False)
            frame = self.environment.render_rgb()
            reinforcement = self._take_reinforcement()
            reinforcement_source = "event_train" if reinforcement != "none" else "none"
            if reinforcement == "none":
                reinforcement = self.environment.reinforcement()
                if reinforcement != "none":
                    reinforcement_source = "environment"
            context = dict(context)
            context["_reinforcement_source"] = reinforcement_source

        stop_event = threading.Event()
        world_thread: threading.Thread | None = None
        if not self.decision_synchronous_world:
            world_thread = threading.Thread(
                target=self._run_world_clock,
                kwargs={
                    "observed_episode": observed_episode,
                    "stop_event": stop_event,
                    "on_world_tick": on_world_tick,
                },
                name="neurofly-world-clock",
                daemon=True,
            )
            world_thread.start()
        try:
            decision = self.brain.decide(frame, reinforcement, context=context)
        finally:
            if world_thread is not None:
                stop_event.set()
                world_thread.join(
                    timeout=max(1.0, self._effective_world_tick_seconds() * 3)
                )

        with self._lock:
            self.last_decision = decision
            if self.environment.episode != observed_episode:
                state = self._snapshot_locked(
                    decision=decision,
                    state_kind="stale_decision",
                    step_event="decision_discarded",
                    decision_applied=False,
                )
                self._checkpoint_if_due()
                return state

            result = self.environment.agent_step(
                decision.action,
                move_enemies=self.decision_synchronous_world,
            )
            self._queue_reinforcement(result.reward, result.event)
            terminal_snapshot = self._snapshot_locked(
                decision=decision,
                state_kind="neural_decision",
                step_event=result.event,
                decision_applied=True,
            )
            if result.terminal:
                self.environment.reset(result.event or "terminal")
                self._reset_world_clock_deadline()
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
        with self._lock:
            self.checkpoint.parent.mkdir(parents=True, exist_ok=True)
            self.brain.save(self.checkpoint)
            state_path = self.checkpoint.with_suffix(".maze.json")
            temporary = state_path.with_suffix(state_path.suffix + ".partial")
            payload = self.environment.persistence_snapshot()
            payload["_pending_reinforcement"] = self.pending_reinforcement
            payload["_pending_reinforcement_steps"] = self.pending_reinforcement_steps
            payload["_reinforcement_train_policy"] = REINFORCEMENT_TRAIN_POLICY
            temporary.write_text(json.dumps(payload, indent=2) + "\n")
            temporary.replace(state_path)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot_locked(state_kind="snapshot")
