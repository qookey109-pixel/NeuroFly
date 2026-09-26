from __future__ import annotations

import ast
import json
import random
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .brain_runtime import BrainBackend, BrainDecision


DIRS = ("UP", "RIGHT", "DOWN", "LEFT")
VECTORS = {
    "UP": (0, -1),
    "RIGHT": (1, 0),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
}
ENEMY_NAVIGATION_POLICY = "maze-shortest-path-v2"
ENEMY_PURSUIT_PROBABILITY = 0.90


@dataclass(slots=True)
class StepResult:
    reward: float
    event: str | None
    terminal: bool


class MazeEnvironment:
    cols = 19
    rows = 14

    def __init__(self, *, seed: int = 109) -> None:
        self.rng = random.Random(seed)
        self.episode = 0
        self.total_food = 0
        self.total_deaths = 0
        self.total_clears = 0
        self.cumulative_reward = 0.0
        self.reset("initial")

    def _make_grid(self) -> list[list[str]]:
        grid = [["." for _ in range(self.cols)] for _ in range(self.rows)]
        for x in range(self.cols):
            grid[0][x] = "#"
            grid[self.rows - 1][x] = "#"
        for y in range(self.rows):
            grid[y][0] = "#"
            grid[y][self.cols - 1] = "#"

        def wall(x: int, y: int) -> None:
            if 0 < x < self.cols - 1 and 0 < y < self.rows - 1:
                grid[y][x] = "#"

        for y in range(2, 11):
            if y not in {5, 8}:
                wall(4, y)
        for y in range(3, 12):
            if y not in {6, 9}:
                wall(9, y)
        for y in range(2, 11):
            if y not in {4, 7}:
                wall(14, y)
        for x in range(2, 8):
            if x != 5:
                wall(x, 3)
        for x in range(11, 17):
            if x != 13:
                wall(x, 4)
        for x in range(2, 8):
            if x != 6:
                wall(x, 8)
        for x in range(11, 17):
            if x != 12:
                wall(x, 9)
        for x in range(6, 13):
            if x not in {8, 10}:
                wall(x, 11)
        return grid

    def reset(self, reason: str = "reset") -> None:
        self.episode += 1
        self.grid = self._make_grid()
        self.fly = {"x": 1, "y": 1, "dir": "RIGHT"}
        self.enemies = [
            {"x": self.cols - 2, "y": self.rows - 2},
            {"x": self.cols - 3, "y": 1},
        ]
        self.grid[1][1] = " "
        for enemy in self.enemies:
            self.grid[enemy["y"]][enemy["x"]] = " "
        for x, y in ((1, self.rows - 2), (self.cols - 2, 1), (8, 6), (15, 11)):
            if self.grid[y][x] != "#":
                self.grid[y][x] = "o"
        self.episode_reward = 0.0
        self.episode_food = 0
        self.ticks = 0
        self.power_ticks = 0
        self.last_action = "HOLD"
        self.last_reward = 0.0
        self.last_event = reason
        self.started_monotonic = time.monotonic()

    def restore(self, payload: dict[str, Any]) -> None:
        grid_rows = payload.get("grid")
        if (
            not isinstance(grid_rows, list)
            or len(grid_rows) != self.rows
            or any(not isinstance(row, str) or len(row) != self.cols for row in grid_rows)
        ):
            raise ValueError("Invalid persisted maze grid")
        if any(cell not in "#.o " for row in grid_rows for cell in row):
            raise ValueError("Invalid persisted maze cell")

        fly = payload.get("fly")
        enemies = payload.get("enemies")
        if not isinstance(fly, dict) or fly.get("dir") not in DIRS:
            raise ValueError("Invalid persisted fly state")
        if not isinstance(enemies, list) or not enemies:
            raise ValueError("Invalid persisted enemy state")

        self.grid = [list(row) for row in grid_rows]
        self.fly = {"x": int(fly["x"]), "y": int(fly["y"]), "dir": str(fly["dir"])}
        self.enemies = [{"x": int(e["x"]), "y": int(e["y"])} for e in enemies]
        if not self.is_open(self.fly["x"], self.fly["y"]):
            raise ValueError("Persisted fly is outside the maze")
        if any(not self.is_open(e["x"], e["y"]) for e in self.enemies):
            raise ValueError("Persisted enemy is outside the maze")

        self.episode = max(1, int(payload.get("episode", 1)))
        self.ticks = max(0, int(payload.get("ticks", 0)))
        self.power_ticks = max(0, int(payload.get("power_ticks", 0)))
        self.last_action = str(payload.get("last_action", "HOLD"))
        if self.last_action not in {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}:
            raise ValueError("Invalid persisted action")
        self.last_reward = float(payload.get("last_reward", 0.0))
        self.episode_reward = float(payload.get("episode_reward", 0.0))
        self.cumulative_reward = float(payload.get("cumulative_reward", 0.0))
        self.episode_food = max(0, int(payload.get("episode_food", 0)))
        self.total_food = max(self.episode_food, int(payload.get("total_food", self.episode_food)))
        self.total_deaths = max(0, int(payload.get("total_deaths", 0)))
        self.total_clears = max(0, int(payload.get("total_clears", 0)))
        self.last_event = payload.get("last_event")
        survival = max(0.0, float(payload.get("survival_seconds", 0.0)))
        self.started_monotonic = time.monotonic() - survival

        rng_state = payload.get("_rng_state")
        if isinstance(rng_state, str):
            self.rng.setstate(ast.literal_eval(rng_state))

    def is_open(self, x: int, y: int) -> bool:
        return 0 <= x < self.cols and 0 <= y < self.rows and self.grid[y][x] != "#"

    def neighbors(self, x: int, y: int) -> list[tuple[str, int, int]]:
        out: list[tuple[str, int, int]] = []
        for direction in DIRS:
            dx, dy = VECTORS[direction]
            nx, ny = x + dx, y + dy
            if self.is_open(nx, ny):
                out.append((direction, nx, ny))
        return out

    def food_left(self) -> int:
        return sum(cell in {".", "o"} for row in self.grid for cell in row)

    def threat_distance(self, x: int | None = None, y: int | None = None) -> int:
        x = self.fly["x"] if x is None else x
        y = self.fly["y"] if y is None else y
        return min(abs(e["x"] - x) + abs(e["y"] - y) for e in self.enemies)

    def _next_food_direction(self) -> str | None:
        start = (self.fly["x"], self.fly["y"])
        queue: deque[tuple[int, int, str | None]] = deque([(start[0], start[1], None)])
        seen = {start}
        while queue:
            x, y, first = queue.popleft()
            if (x, y) != start and self.grid[y][x] in {".", "o"}:
                return first
            for direction, nx, ny in self.neighbors(x, y):
                key = (nx, ny)
                if key not in seen:
                    seen.add(key)
                    queue.append((nx, ny, direction if first is None else first))
        return None

    def _relative_action(self, target_direction: str | None) -> str:
        if target_direction is None:
            return "HOLD"
        current = DIRS.index(self.fly["dir"])
        target = DIRS.index(target_direction)
        delta = (target - current) % 4
        if delta == 0:
            return "FORWARD"
        if delta == 1:
            return "TURN_RIGHT"
        if delta == 3:
            return "TURN_LEFT"
        return "TURN_RIGHT"

    def demo_action(self) -> str:
        if self.power_ticks <= 0 and self.threat_distance() <= 2:
            options = self.neighbors(self.fly["x"], self.fly["y"])
            if options:
                direction, _, _ = max(
                    options,
                    key=lambda p: min(
                        abs(e["x"] - p[1]) + abs(e["y"] - p[2]) for e in self.enemies
                    ),
                )
                return self._relative_action(direction)
        return self._relative_action(self._next_food_direction())

    def _move_fly(self, action: str) -> None:
        idx = DIRS.index(self.fly["dir"])
        if action == "TURN_LEFT":
            self.fly["dir"] = DIRS[(idx - 1) % 4]
            return
        if action == "TURN_RIGHT":
            self.fly["dir"] = DIRS[(idx + 1) % 4]
            return
        if action != "FORWARD":
            return
        dx, dy = VECTORS[self.fly["dir"]]
        nx, ny = self.fly["x"] + dx, self.fly["y"] + dy
        if self.is_open(nx, ny):
            self.fly["x"], self.fly["y"] = nx, ny

    def _maze_distance_map(self, target_x: int, target_y: int) -> dict[tuple[int, int], int]:
        """Return true shortest-path distances through the maze to a target cell."""
        target = (int(target_x), int(target_y))
        if not self.is_open(*target):
            return {}
        distances = {target: 0}
        queue: deque[tuple[int, int]] = deque([target])
        while queue:
            x, y = queue.popleft()
            next_distance = distances[(x, y)] + 1
            for _, nx, ny in self.neighbors(x, y):
                key = (nx, ny)
                if key not in distances:
                    distances[key] = next_distance
                    queue.append(key)
        return distances

    def _move_enemies(self) -> None:
        if not self.enemies:
            return

        distances = self._maze_distance_map(self.fly["x"], self.fly["y"])
        fly_cell = (self.fly["x"], self.fly["y"])
        occupied = {(enemy["x"], enemy["y"]) for enemy in self.enemies}
        unreachable = self.cols * self.rows * 4

        for enemy in self.enemies:
            current = (enemy["x"], enemy["y"])
            occupied.discard(current)
            options = self.neighbors(enemy["x"], enemy["y"])
            coordinated = [
                item
                for item in options
                if (item[1], item[2]) == fly_cell or (item[1], item[2]) not in occupied
            ]
            if coordinated:
                options = coordinated
            if not options:
                occupied.add(current)
                continue

            def route_distance(item: tuple[str, int, int]) -> int:
                return distances.get((item[1], item[2]), unreachable)

            flee = self.power_ticks > 0
            target_distance = (
                max(route_distance(item) for item in options)
                if flee
                else min(route_distance(item) for item in options)
            )
            best = [item for item in options if route_distance(item) == target_distance]

            if self.rng.random() < ENEMY_PURSUIT_PROBABILITY:
                pick = self.rng.choice(best)
            else:
                pick = self.rng.choice(options)
            enemy["x"], enemy["y"] = pick[1], pick[2]
            occupied.add((enemy["x"], enemy["y"]))

    def _collision(self) -> dict[str, int] | None:
        return next(
            (
                enemy
                for enemy in self.enemies
                if enemy["x"] == self.fly["x"] and enemy["y"] == self.fly["y"]
            ),
            None,
        )

    def step(self, action: str) -> StepResult:
        if action not in {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}:
            raise ValueError(f"Unknown maze action: {action}")
        self.ticks += 1
        self.last_action = action
        reward = 0.01
        event = None
        terminal = False
        self._move_fly(action)

        cell = self.grid[self.fly["y"]][self.fly["x"]]
        if cell == ".":
            self.grid[self.fly["y"]][self.fly["x"]] = " "
            reward += 1.0
            self.episode_food += 1
            self.total_food += 1
            event = "food"
        elif cell == "o":
            self.grid[self.fly["y"]][self.fly["x"]] = " "
            reward += 4.0
            self.episode_food += 1
            self.total_food += 1
            self.power_ticks = 34
            event = "energy_food"

        self._move_enemies()
        hit = self._collision()
        if hit:
            if self.power_ticks > 0:
                reward += 3.0
                hit["x"], hit["y"] = self.cols - 2, self.rows - 2
                event = "enemy_repelled"
            else:
                reward -= 5.0
                self.total_deaths += 1
                event = "captured"
                terminal = True

        if self.power_ticks > 0:
            self.power_ticks -= 1

        if not terminal and self.food_left() == 0:
            reward += 15.0
            self.total_clears += 1
            event = "maze_cleared"
            terminal = True

        self.last_reward = reward
        self.episode_reward += reward
        self.cumulative_reward += reward
        self.last_event = event
        return StepResult(reward=reward, event=event, terminal=terminal)

    def reinforcement(self) -> str:
        if self.last_reward >= 0.5:
            return "reward"
        if self.last_reward <= -0.5:
            return "aversive"
        return "none"

    def snapshot(self, *, include_grid: bool = True) -> dict[str, Any]:
        snapshot: dict[str, Any] = {
            "episode": self.episode,
            "ticks": self.ticks,
            "fly": dict(self.fly),
            "enemies": [dict(e) for e in self.enemies],
            "power_ticks": self.power_ticks,
            "last_action": self.last_action,
            "last_reward": round(self.last_reward, 4),
            "episode_reward": round(self.episode_reward, 4),
            "cumulative_reward": round(self.cumulative_reward, 4),
            "episode_food": self.episode_food,
            "total_food": self.total_food,
            "food_left": self.food_left(),
            "total_deaths": self.total_deaths,
            "total_clears": self.total_clears,
            "last_event": self.last_event,
            "survival_seconds": round(time.monotonic() - self.started_monotonic, 1),
            "reinforcement": self.reinforcement(),
            "demo_action": self.demo_action(),
            "enemy_navigation_policy": ENEMY_NAVIGATION_POLICY,
            "enemy_pursuit_probability": ENEMY_PURSUIT_PROBABILITY,
        }
        if include_grid:
            snapshot["grid"] = ["".join(row) for row in self.grid]
        return snapshot

    def persistence_snapshot(self) -> dict[str, Any]:
        data = self.snapshot(include_grid=True)
        data["_rng_state"] = repr(self.rng.getstate())
        return data

    def render_rgb(self, *, width: int = 320, height: int = 180) -> Any:
        """Render the same environment into RGB pixels for the fly visual adapter."""
        try:
            import numpy as np
            from PIL import Image, ImageDraw
        except Exception as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError("RGB rendering requires Pillow and NumPy") from exc

        image = Image.new("RGB", (width, height), (244, 247, 239))
        draw = ImageDraw.Draw(image)
        cw = width / self.cols
        ch = height / self.rows
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                x0, y0 = int(x * cw), int(y * ch)
                x1, y1 = int((x + 1) * cw), int((y + 1) * ch)
                if cell == "#":
                    draw.rectangle((x0, y0, x1, y1), fill=(34, 62, 54))
                elif cell in {".", "o"}:
                    r = max(1, int(min(cw, ch) * (0.23 if cell == "o" else 0.11)))
                    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
                    color = (70, 150, 230) if cell == "o" else (224, 171, 47)
                    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)

        for enemy in self.enemies:
            x0, y0 = int(enemy["x"] * cw), int(enemy["y"] * ch)
            x1, y1 = int((enemy["x"] + 1) * cw), int((enemy["y"] + 1) * ch)
            draw.ellipse((x0 + 2, y0 + 2, x1 - 2, y1 - 2), fill=(210, 70, 96))

        fx0, fy0 = int(self.fly["x"] * cw), int(self.fly["y"] * ch)
        fx1, fy1 = int((self.fly["x"] + 1) * cw), int((self.fly["y"] + 1) * ch)
        draw.ellipse((fx0 + 2, fy0 + 2, fx1 - 2, fy1 - 2), fill=(119, 178, 69))
        return np.asarray(image, dtype=np.uint8)


class MazeSession:
    def __init__(
        self,
        brain: BrainBackend,
        *,
        checkpoint: str | Path | None = None,
        checkpoint_every: float = 300.0,
        seed: int = 109,
    ) -> None:
        self.brain = brain
        self.environment = MazeEnvironment(seed=seed)
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
        try:
            frame = self.environment.render_rgb()
        except RuntimeError:
            frame = None
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
