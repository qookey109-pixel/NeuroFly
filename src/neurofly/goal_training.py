from __future__ import annotations

import copy
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .brain_runtime import BrainBackend, BrainDecision
from .gustation import contact_gustation
from .maze_runtime import MazeEnvironment, StepResult
from .neural_context import (
    assert_firewalled_bundle,
    olfaction_neural_payload,
    prepare_firewalled_visual_input,
)
from .proprioception import feco_motion_proprioception, proprioceptive_channel_levels
from .sensory_contract import assert_unprivileged_agent_input
from .tactile import blocked_forward_contact, contact_mechanosensation
from .virtual_body import VirtualFeCOJointBody


def _reinforcement_for_reward(reward: float) -> str:
    if reward >= 0.5:
        return "reward"
    if reward <= -0.5:
        return "aversive"
    return "none"


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
    ) -> None:
        if world_tick_seconds <= 0:
            raise ValueError("world_tick_seconds must be > 0")
        self.brain = brain
        self.environment = environment or GoalMazeEnvironment(seed=seed)
        self.checkpoint = Path(checkpoint) if checkpoint else None
        self.checkpoint_every = float(checkpoint_every)
        self.world_tick_seconds = float(world_tick_seconds)
        self.last_checkpoint = time.monotonic()
        self.last_decision: BrainDecision | None = None
        self.pending_reinforcement = "none"
        self.pending_gustatory_event: str | None = None
        self.pending_tactile_contact = False
        self.virtual_body = VirtualFeCOJointBody()
        self.pending_proprioception = feco_motion_proprioception()
        self.last_visual_diagnostics: dict[str, Any] | None = None
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
                pending_taste = payload.get("_pending_gustatory_event")
                if pending_taste in {"food", "energy_food"}:
                    self.pending_gustatory_event = str(pending_taste)
                pending_touch = payload.get("_pending_tactile_contact", False)
                if not isinstance(pending_touch, bool):
                    raise ValueError("Persisted tactile contact latch must be boolean")
                self.pending_tactile_contact = pending_touch

                body_state = payload.get("_virtual_body_state")
                if body_state is not None:
                    if not isinstance(body_state, dict):
                        raise ValueError("Persisted virtual body state must be an object")
                    self.virtual_body.restore(body_state)

                pending_proprioception = payload.get("_pending_proprioception")
                if pending_proprioception is not None:
                    if not isinstance(pending_proprioception, dict):
                        raise ValueError("Persisted proprioception must be an object")
                    proprioceptive_channel_levels(pending_proprioception)
                    assert_unprivileged_agent_input(
                        {"proprioception": pending_proprioception}
                    )
                    self.pending_proprioception = copy.deepcopy(pending_proprioception)

        self._world_next_tick_monotonic = (
            time.monotonic() + self._effective_world_tick_seconds()
        )

    def _effective_world_tick_seconds(self) -> float:
        interval = float(self.environment.effective_world_tick_seconds(self.world_tick_seconds))
        if interval <= 0:
            raise ValueError("effective world tick interval must be > 0")
        return interval

    def _reset_world_clock_deadline(self) -> None:
        self._world_next_tick_monotonic = (
            time.monotonic() + self._effective_world_tick_seconds()
        )

    def _reset_virtual_body(self) -> None:
        self.virtual_body.reset()
        self.pending_proprioception = feco_motion_proprioception()

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
                    self.pending_reinforcement = _reinforcement_for_reward(result.reward)
                    self._reset_virtual_body()
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

    def _prepare_brain_handoff(
        self,
        *,
        world_context: dict[str, Any],
        frame: Any,
        gustation: dict[str, Any],
        tactile: dict[str, Any],
        proprioception: dict[str, Any],
    ) -> tuple[Any, dict[str, Any]]:
        if getattr(self.brain, "name", "") == "demo":
            # DemoBrain is an explicitly privileged lightweight baseline used by
            # smoke tests/UI scaffolding. It is not the MaleCNS neural agent.
            self.last_visual_diagnostics = None
            return frame, world_context

        sensory_context: dict[str, Any] = {
            "gustation": copy.deepcopy(gustation),
            "contact_mechanosensation": copy.deepcopy(tactile),
            "proprioception": copy.deepcopy(proprioception),
        }

        raw_olfaction = world_context.get("olfaction")
        if isinstance(raw_olfaction, dict):
            sensory_context["olfaction"] = olfaction_neural_payload(raw_olfaction)

        mechanosensation = world_context.get("antennal_mechanosensation")
        if isinstance(mechanosensation, dict):
            sensory_context["antennal_mechanosensation"] = copy.deepcopy(
                mechanosensation
            )

        bundle = prepare_firewalled_visual_input(
            frame,
            fly=self.environment.fly,
            enemies=self.environment.enemies,
            sensory_context=sensory_context,
        )
        assert_firewalled_bundle(bundle)
        self.last_visual_diagnostics = copy.deepcopy(bundle["diagnostics"]["vision"])
        return bundle["frame"], bundle["context"]

    def _restore_visual_telemetry(self, decision: BrainDecision) -> BrainDecision:
        if not self.last_visual_diagnostics or decision.backend != "malecns":
            return decision
        telemetry = dict(decision.telemetry)
        internal = telemetry.get("vision")
        vision = copy.deepcopy(self.last_visual_diagnostics)
        if isinstance(internal, dict):
            for key in ("change", "left_change", "right_change"):
                if key in internal:
                    vision[key] = internal[key]
        telemetry["vision"] = vision
        telemetry["visual_change"] = vision.get("change", 0.0)
        telemetry["visual_left_change"] = vision.get("left_change", 0.0)
        telemetry["visual_right_change"] = vision.get("right_change", 0.0)
        return BrainDecision(
            action=decision.action,
            backend=decision.backend,
            telemetry=telemetry,
        )

    def tick(
        self,
        *,
        on_world_tick: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            observed_episode = self.environment.episode
            world_context = self.environment.snapshot(include_grid=False)

            gustatory_event = self.pending_gustatory_event
            self.pending_gustatory_event = None
            gustation = contact_gustation(event=gustatory_event)
            assert_unprivileged_agent_input({"gustation": gustation})
            world_context["gustation"] = gustation

            tactile = contact_mechanosensation(
                front=1.0 if self.pending_tactile_contact else 0.0
            )
            self.pending_tactile_contact = False
            assert_unprivileged_agent_input({"contact_mechanosensation": tactile})
            world_context["contact_mechanosensation"] = tactile

            proprioception = copy.deepcopy(self.pending_proprioception)
            proprioceptive_channel_levels(proprioception)
            assert_unprivileged_agent_input({"proprioception": proprioception})
            world_context["proprioception"] = proprioception
            self.pending_proprioception = feco_motion_proprioception()

            raw_frame = self.environment.render_rgb()
            frame, context = self._prepare_brain_handoff(
                world_context=world_context,
                frame=raw_frame,
                gustation=gustation,
                tactile=tactile,
                proprioception=proprioception,
            )

            reinforcement = self.pending_reinforcement
            if reinforcement == "none":
                reinforcement = self.environment.reinforcement()
            self.pending_reinforcement = "none"

        stop_event = threading.Event()
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
            decision = self._restore_visual_telemetry(decision)
        finally:
            stop_event.set()
            world_thread.join(timeout=max(1.0, self._effective_world_tick_seconds() * 3))

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

            food_before = int(self.environment.total_food)
            before_position = (
                int(self.environment.fly["x"]),
                int(self.environment.fly["y"]),
            )
            result = self.environment.agent_step(decision.action, move_enemies=False)
            after_position = (
                int(self.environment.fly["x"]),
                int(self.environment.fly["y"]),
            )

            if int(self.environment.total_food) > food_before:
                self.pending_gustatory_event = "food"

            applied_action = str(
                getattr(self.environment, "last_applied_action", decision.action)
            )
            tactile_result = blocked_forward_contact(
                applied_action=applied_action,
                before_position=before_position,
                after_position=after_position,
                terminal=result.terminal,
            )
            if tactile_result["contact"]:
                self.pending_tactile_contact = True

            if result.terminal:
                self._reset_virtual_body()
            else:
                self.pending_proprioception = self.virtual_body.advance(applied_action)
                proprioceptive_channel_levels(self.pending_proprioception)
                assert_unprivileged_agent_input(
                    {"proprioception": self.pending_proprioception}
                )

            self.pending_reinforcement = _reinforcement_for_reward(result.reward)
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
            payload["_pending_gustatory_event"] = self.pending_gustatory_event
            payload["_pending_tactile_contact"] = self.pending_tactile_contact
            payload["_virtual_body_state"] = self.virtual_body.persistence_snapshot()
            payload["_pending_proprioception"] = copy.deepcopy(self.pending_proprioception)
            temporary.write_text(json.dumps(payload, indent=2) + "\n")
            temporary.replace(state_path)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot_locked(state_kind="snapshot")
