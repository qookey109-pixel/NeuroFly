from __future__ import annotations

import json
import math
import random
import time
from pathlib import Path
from typing import Any

from .brain_runtime import BrainBackend, BrainDecision


LIGHT_CHASE_MODEL = "neurofly-light-chase-v0.1"
LIGHT_CHASE_VISION_MODEL = "neurofly-light-chase-egocentric-vision-v0.1"
LIGHT_CHASE_FIELD_DEGREES = 300.0

_DIRECTIONS = ("UP", "RIGHT", "DOWN", "LEFT")
_VECTORS = {
    "UP": (0, -1),
    "RIGHT": (1, 0),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
}
_ANGLES = {
    "RIGHT": 0.0,
    "DOWN": math.pi / 2.0,
    "LEFT": math.pi,
    "UP": -math.pi / 2.0,
}


def _normalize_angle(angle: float) -> float:
    while angle <= -math.pi:
        angle += 2.0 * math.pi
    while angle > math.pi:
        angle -= 2.0 * math.pi
    return angle


def _tupleize(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_tupleize(item) for item in value)
    return value


class LightChaseEnvironment:
    """Small 2D light-seeking environment with egocentric visual output.

    Target coordinates are private environment state. The neural agent receives
    only the rendered RGB frame plus a non-spatial sensory contract.
    """

    step_cost = -0.01
    reach_reward = 10.0
    progress_gain = 0.25

    def __init__(
        self,
        *,
        seed: int = 109,
        cols: int = 15,
        rows: int = 11,
    ) -> None:
        if cols < 7 or rows < 7:
            raise ValueError("Light Chase arena must be at least 7x7")
        self.cols = int(cols)
        self.rows = int(rows)
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.agent = {
            "x": self.cols // 2,
            "y": self.rows // 2,
            "dir": "RIGHT",
        }
        self.target = {"x": 1, "y": 1}
        self.episode = 1
        self.ticks = 0
        self.total_ticks = 0
        self.total_lights = 0
        self.last_action = "HOLD"
        self.last_reward = 0.0
        self.last_event: str | None = None
        self._relocate_target()

    def _distance(self) -> float:
        return math.hypot(
            float(self.target["x"] - self.agent["x"]),
            float(self.target["y"] - self.agent["y"]),
        )

    def _relocate_target(self) -> None:
        candidates = [
            (x, y)
            for y in range(self.rows)
            for x in range(self.cols)
            if (x, y) != (self.agent["x"], self.agent["y"])
            and math.hypot(x - self.agent["x"], y - self.agent["y"]) >= 3.0
        ]
        if not candidates:
            raise RuntimeError("Light Chase arena has no valid target cells")
        x, y = self.rng.choice(candidates)
        self.target = {"x": int(x), "y": int(y)}

    def sensory_context(self) -> dict[str, Any]:
        """Return the only non-image context allowed to the brain."""

        return {
            "environment_model": LIGHT_CHASE_MODEL,
            "vision": {
                "model": LIGHT_CHASE_VISION_MODEL,
                "coordinate_frame": "egocentric-wide-field",
                "field_degrees": LIGHT_CHASE_FIELD_DEGREES,
                "target_coordinates_exposed": False,
                "target_bearing_exposed": False,
                "target_distance_exposed": False,
                "recommended_action_exposed": False,
            },
        }

    def _target_bearing_degrees(self) -> float:
        dx = float(self.target["x"] - self.agent["x"])
        dy = float(self.target["y"] - self.agent["y"])
        world = math.atan2(dy, dx)
        heading = _ANGLES[str(self.agent["dir"])]
        return math.degrees(_normalize_angle(world - heading))

    def render_rgb(self, *, width: int = 160, height: int = 90) -> list[list[list[int]]]:
        """Render only an egocentric light cue, never a top-down map."""

        if width < 32 or height < 24:
            raise ValueError("Light Chase visual frame is too small")

        background = [18, 21, 28]
        frame = [[background.copy() for _ in range(width)] for _ in range(height)]
        bearing = self._target_bearing_degrees()
        half_field = LIGHT_CHASE_FIELD_DEGREES / 2.0
        if abs(bearing) > half_field:
            return frame

        distance = max(self._distance(), 0.25)
        center_x = int((bearing + half_field) / LIGHT_CHASE_FIELD_DEGREES * (width - 1))
        center_y = height // 2
        radius = max(2, min(16, int(18.0 / distance)))
        glow_radius = min(22, radius + 4)

        for py in range(max(0, center_y - glow_radius), min(height, center_y + glow_radius + 1)):
            for px in range(max(0, center_x - glow_radius), min(width, center_x + glow_radius + 1)):
                r = math.hypot(px - center_x, py - center_y)
                if r <= radius:
                    frame[py][px] = [245, 244, 192]
                elif r <= glow_radius:
                    falloff = max(0.0, 1.0 - (r - radius) / max(1.0, glow_radius - radius))
                    frame[py][px] = [
                        int(18 + 150 * falloff),
                        int(21 + 145 * falloff),
                        int(28 + 95 * falloff),
                    ]
        return frame

    def step(self, action: str) -> dict[str, Any]:
        if action not in {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}:
            raise ValueError(f"Unknown Light Chase action: {action}")

        before = self._distance()
        event = "hold"

        if action in {"TURN_LEFT", "TURN_RIGHT"}:
            index = _DIRECTIONS.index(str(self.agent["dir"]))
            delta = -1 if action == "TURN_LEFT" else 1
            self.agent["dir"] = _DIRECTIONS[(index + delta) % len(_DIRECTIONS)]
            event = "turn"
        elif action == "FORWARD":
            dx, dy = _VECTORS[str(self.agent["dir"])]
            nx = max(0, min(self.cols - 1, int(self.agent["x"]) + dx))
            ny = max(0, min(self.rows - 1, int(self.agent["y"]) + dy))
            self.agent["x"] = nx
            self.agent["y"] = ny
            event = "move"

        after = self._distance()
        reward = self.step_cost + (before - after) * self.progress_gain

        if self.agent["x"] == self.target["x"] and self.agent["y"] == self.target["y"]:
            reward += self.reach_reward
            self.total_lights += 1
            event = "light_reached"
            self.episode += 1
            self._relocate_target()

        self.ticks += 1
        self.total_ticks += 1
        self.last_action = action
        self.last_reward = float(reward)
        self.last_event = event
        return self.public_snapshot()

    def public_snapshot(self) -> dict[str, Any]:
        """State for visualization/evaluation, not neural context."""

        return {
            "model": LIGHT_CHASE_MODEL,
            "episode": self.episode,
            "ticks": self.ticks,
            "total_ticks": self.total_ticks,
            "total_lights": self.total_lights,
            "agent": dict(self.agent),
            "target": dict(self.target),
            "last_action": self.last_action,
            "last_reward": self.last_reward,
            "last_event": self.last_event,
        }

    def persistence_snapshot(self) -> dict[str, Any]:
        return {
            **self.public_snapshot(),
            "seed": self.seed,
            "_rng_state": self.rng.getstate(),
        }

    def restore(self, payload: dict[str, Any]) -> None:
        if payload.get("model") != LIGHT_CHASE_MODEL:
            raise ValueError("Unsupported Light Chase state model")
        agent = payload.get("agent")
        target = payload.get("target")
        if not isinstance(agent, dict) or not isinstance(target, dict):
            raise ValueError("Invalid Light Chase state")
        direction = str(agent.get("dir"))
        if direction not in _DIRECTIONS:
            raise ValueError("Invalid Light Chase direction")

        self.seed = int(payload.get("seed", self.seed))
        self.agent = {
            "x": int(agent["x"]),
            "y": int(agent["y"]),
            "dir": direction,
        }
        self.target = {
            "x": int(target["x"]),
            "y": int(target["y"]),
        }
        for point in (self.agent, self.target):
            if not (0 <= point["x"] < self.cols and 0 <= point["y"] < self.rows):
                raise ValueError("Light Chase coordinate outside arena")

        self.episode = max(1, int(payload.get("episode", 1)))
        self.ticks = max(0, int(payload.get("ticks", 0)))
        self.total_ticks = max(self.ticks, int(payload.get("total_ticks", self.ticks)))
        self.total_lights = max(0, int(payload.get("total_lights", 0)))
        self.last_action = str(payload.get("last_action", "HOLD"))
        self.last_reward = float(payload.get("last_reward", 0.0))
        self.last_event = payload.get("last_event")
        state = payload.get("_rng_state")
        if state is not None:
            self.rng.setstate(_tupleize(state))


class LightChaseSession:
    def __init__(
        self,
        brain: BrainBackend,
        *,
        checkpoint: str | Path | None = None,
        checkpoint_every: float = 300.0,
        seed: int = 109,
        environment: LightChaseEnvironment | None = None,
    ) -> None:
        self.brain = brain
        self.checkpoint = Path(checkpoint) if checkpoint else None
        self.checkpoint_every = float(checkpoint_every)
        self.environment = environment or LightChaseEnvironment(seed=seed)
        self.pending_reinforcement = "none"
        self.last_checkpoint = time.monotonic()
        self.last_decision: BrainDecision | None = None

        if self.checkpoint:
            state_path = self.checkpoint.with_suffix(".light.json")
            if state_path.exists():
                payload = json.loads(state_path.read_text())
                self.environment.restore(payload)
                reinforcement = payload.get("_pending_reinforcement", "none")
                if reinforcement not in {"none", "reward", "aversive"}:
                    raise ValueError("Invalid Light Chase pending reinforcement")
                self.pending_reinforcement = reinforcement

    @staticmethod
    def _reinforcement(reward: float) -> str:
        if reward >= 0.5:
            return "reward"
        if reward <= -0.5:
            return "aversive"
        return "none"

    def tick(self) -> dict[str, Any]:
        frame = self.environment.render_rgb()
        context = self.environment.sensory_context()
        decision = self.brain.decide(
            frame,
            self.pending_reinforcement,
            context=context,
        )
        self.pending_reinforcement = "none"
        self.last_decision = decision
        state = self.environment.step(decision.action)
        self.pending_reinforcement = self._reinforcement(float(state["last_reward"]))
        state["brain"] = {
            "backend": decision.backend,
            "telemetry": decision.telemetry,
        }
        state["sensory_contract"] = context
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
        state_path = self.checkpoint.with_suffix(".light.json")
        temporary = state_path.with_suffix(state_path.suffix + ".partial")
        payload = self.environment.persistence_snapshot()
        payload["_pending_reinforcement"] = self.pending_reinforcement
        temporary.write_text(json.dumps(payload, indent=2) + "\n")
        temporary.replace(state_path)
