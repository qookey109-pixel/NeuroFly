from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .brain_runtime import BrainBackend, BrainDecision
from .light_chase import LIGHT_CHASE_MODEL, LightChaseEnvironment
from .maze_runtime import MazeEnvironment
from .olfaction import OLFACTION_MODEL, virtual_olfaction
from .vision import VISION_MODEL
from .vision_adapter import retinalize_topdown_rgb


ENVIRONMENT_ADAPTER_SCHEMA = "neurofly-environment-adapter-v0.1"
MAZE_CHASE_MODEL = "neurofly-maze-chase-v0.1"
VALID_ACTIONS = {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}

_FORBIDDEN_NEURAL_CONTEXT_KEYS = {
    "grid",
    "fly",
    "enemies",
    "target",
    "agent",
    "x",
    "y",
    "source",
    "distance_cells",
    "bearing_degrees",
    "demo_action",
    "route",
    "goal_direction",
    "recommended_action",
    "world_state",
}


@dataclass(slots=True)
class NeuralObservation:
    frame: Any
    context: dict[str, Any]


@dataclass(slots=True)
class EnvironmentStep:
    reward: float
    event: str | None
    terminal: bool
    public_state: dict[str, Any]


class EnvironmentAdapter(Protocol):
    model: str
    state_suffix: str

    def observe(self) -> NeuralObservation: ...
    def apply_action(self, action: str) -> EnvironmentStep: ...
    def reset(self, reason: str = "reset") -> None: ...
    def public_snapshot(self) -> dict[str, Any]: ...
    def persistence_snapshot(self) -> dict[str, Any]: ...
    def restore(self, payload: dict[str, Any]) -> None: ...


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.extend(_walk_keys(item))
    return keys


def assert_sensory_only_context(context: dict[str, Any]) -> None:
    if not isinstance(context, dict):
        raise ValueError("neural context must be a dictionary")

    keys = set(_walk_keys(context))
    forbidden = sorted(keys & _FORBIDDEN_NEURAL_CONTEXT_KEYS)
    if forbidden:
        raise ValueError(
            "privileged environment fields are not allowed in neural context: "
            + ", ".join(forbidden)
        )

    encoded = json.dumps(context, sort_keys=True)
    if len(encoded) > 200_000:
        raise ValueError("neural context is unexpectedly large")


def _sensory_olfaction(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("model") != OLFACTION_MODEL:
        raise ValueError("unsupported olfaction model")

    result: dict[str, Any] = {
        "model": raw["model"],
        "engineered_proxy": bool(raw.get("engineered_proxy", True)),
    }
    for channel_name in ("food", "danger"):
        channel = raw.get(channel_name)
        if not isinstance(channel, dict):
            raise ValueError(f"missing olfactory channel: {channel_name}")
        result[channel_name] = {
            key: channel[key]
            for key in ("orn_type", "receptor_proxy", "left", "right", "intensity")
            if key in channel
        }
    return result


class MazeChaseAdapter:
    model = MAZE_CHASE_MODEL
    state_suffix = ".environment-maze.json"

    def __init__(self, environment: MazeEnvironment | None = None, *, seed: int = 109) -> None:
        self.environment = environment or MazeEnvironment(seed=seed)

    def observe(self) -> NeuralObservation:
        try:
            topdown = self.environment.render_rgb()
            frame, _ = retinalize_topdown_rgb(
                topdown,
                fly=self.environment.fly,
                enemies=self.environment.enemies,
                cols=self.environment.cols,
                rows=self.environment.rows,
            )
        except RuntimeError:
            frame = None

        raw_olfaction = virtual_olfaction(
            grid=self.environment.grid,
            fly=self.environment.fly,
            enemies=self.environment.enemies,
        )
        context = {
            "adapter_schema": ENVIRONMENT_ADAPTER_SCHEMA,
            "environment_model": self.model,
            "vision": {
                "model": VISION_MODEL,
                "coordinate_frame": "egocentric-wide-panorama",
                "frame_is_egocentric": True,
                "privileged_geometry_exposed": False,
            },
            "olfaction": _sensory_olfaction(raw_olfaction),
        }
        assert_sensory_only_context(context)
        return NeuralObservation(frame=frame, context=context)

    def apply_action(self, action: str) -> EnvironmentStep:
        if action not in VALID_ACTIONS:
            raise ValueError(f"unsupported environment action: {action}")
        result = self.environment.step(action)
        state = self.environment.snapshot()
        return EnvironmentStep(
            reward=float(result.reward),
            event=result.event,
            terminal=bool(result.terminal),
            public_state=state,
        )

    def reset(self, reason: str = "reset") -> None:
        self.environment.reset(reason)

    def public_snapshot(self) -> dict[str, Any]:
        return self.environment.snapshot()

    def persistence_snapshot(self) -> dict[str, Any]:
        return self.environment.persistence_snapshot()

    def restore(self, payload: dict[str, Any]) -> None:
        self.environment.restore(payload)


class LightChaseAdapter:
    model = LIGHT_CHASE_MODEL
    state_suffix = ".environment-light.json"

    def __init__(
        self,
        environment: LightChaseEnvironment | None = None,
        *,
        seed: int = 109,
    ) -> None:
        self.environment = environment or LightChaseEnvironment(seed=seed)

    def observe(self) -> NeuralObservation:
        context = {
            "adapter_schema": ENVIRONMENT_ADAPTER_SCHEMA,
            **self.environment.sensory_context(),
        }
        assert_sensory_only_context(context)
        return NeuralObservation(
            frame=self.environment.render_rgb(),
            context=context,
        )

    def apply_action(self, action: str) -> EnvironmentStep:
        if action not in VALID_ACTIONS:
            raise ValueError(f"unsupported environment action: {action}")
        state = self.environment.step(action)
        return EnvironmentStep(
            reward=float(state["last_reward"]),
            event=state.get("last_event"),
            terminal=False,
            public_state=state,
        )

    def reset(self, reason: str = "reset") -> None:
        # Light Chase relocates its target internally when reached and has no
        # terminal episode state requiring an external reset.
        return None

    def public_snapshot(self) -> dict[str, Any]:
        return self.environment.public_snapshot()

    def persistence_snapshot(self) -> dict[str, Any]:
        return self.environment.persistence_snapshot()

    def restore(self, payload: dict[str, Any]) -> None:
        self.environment.restore(payload)


def make_environment_adapter(
    name: str,
    *,
    seed: int = 109,
) -> EnvironmentAdapter:
    normalized = str(name).strip().lower().replace("_", "-")
    if normalized in {"maze", "maze-chase"}:
        return MazeChaseAdapter(seed=seed)
    if normalized in {"light", "light-chase"}:
        return LightChaseAdapter(seed=seed)
    raise ValueError(f"unknown NeuroFly environment: {name}")


class EnvironmentSession:
    """Shared brain/environment orchestration for v1 game adapters."""

    def __init__(
        self,
        brain: BrainBackend,
        adapter: EnvironmentAdapter,
        *,
        checkpoint: str | Path | None = None,
        checkpoint_every: float = 300.0,
    ) -> None:
        self.brain = brain
        self.adapter = adapter
        self.checkpoint = Path(checkpoint) if checkpoint else None
        self.checkpoint_every = float(checkpoint_every)
        if self.checkpoint_every <= 0.0:
            raise ValueError("checkpoint_every must be > 0")
        self.pending_reinforcement = "none"
        self.last_checkpoint = time.monotonic()
        self.last_decision: BrainDecision | None = None

        if self.checkpoint:
            state_path = self._state_path()
            if state_path.exists():
                payload = json.loads(state_path.read_text())
                if payload.get("schema") != ENVIRONMENT_ADAPTER_SCHEMA:
                    raise ValueError("unsupported environment session state schema")
                if payload.get("environment_model") != self.adapter.model:
                    raise ValueError("environment checkpoint model mismatch")
                environment_state = payload.get("environment_state")
                if not isinstance(environment_state, dict):
                    raise ValueError("environment checkpoint lacks state")
                self.adapter.restore(environment_state)
                pending = payload.get("_pending_reinforcement", "none")
                if pending not in {"none", "reward", "aversive"}:
                    raise ValueError("invalid pending reinforcement")
                self.pending_reinforcement = str(pending)

    @staticmethod
    def _reinforcement(reward: float) -> str:
        if reward >= 0.5:
            return "reward"
        if reward <= -0.5:
            return "aversive"
        return "none"

    def _state_path(self) -> Path:
        assert self.checkpoint is not None
        return self.checkpoint.with_suffix(self.adapter.state_suffix)

    def tick(self) -> dict[str, Any]:
        observation = self.adapter.observe()
        assert_sensory_only_context(observation.context)

        decision = self.brain.decide(
            observation.frame,
            self.pending_reinforcement,
            context=observation.context,
        )
        if decision.action not in VALID_ACTIONS:
            raise ValueError(f"brain returned unsupported action: {decision.action}")

        self.pending_reinforcement = "none"
        self.last_decision = decision
        step = self.adapter.apply_action(decision.action)
        self.pending_reinforcement = self._reinforcement(step.reward)

        state = dict(step.public_state)
        state["brain"] = {
            "backend": decision.backend,
            "telemetry": decision.telemetry,
        }
        state["sensory_contract"] = observation.context
        state["environment_model"] = self.adapter.model
        state["step_event"] = step.event

        if step.terminal:
            self.adapter.reset(step.event or "terminal")

        self._checkpoint_if_due()
        return state

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
        state_path = self._state_path()
        temporary = state_path.with_suffix(state_path.suffix + ".partial")
        payload = {
            "schema": ENVIRONMENT_ADAPTER_SCHEMA,
            "environment_model": self.adapter.model,
            "environment_state": self.adapter.persistence_snapshot(),
            "_pending_reinforcement": self.pending_reinforcement,
        }
        temporary.write_text(json.dumps(payload, indent=2) + "\n")
        temporary.replace(state_path)

    def snapshot(self) -> dict[str, Any]:
        state = dict(self.adapter.public_snapshot())
        state["environment_model"] = self.adapter.model
        state["brain"] = {
            "backend": getattr(self.brain, "name", type(self.brain).__name__),
            "telemetry": (
                {}
                if self.last_decision is None
                else dict(self.last_decision.telemetry)
            ),
        }
        return state
