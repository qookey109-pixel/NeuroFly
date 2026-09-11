from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .goal_training import GoalMazeEnvironment


CURRICULUM_VERSION = "neurofly-curriculum-v1"


@dataclass(frozen=True)
class CurriculumStage:
    number: int
    name: str
    clears_to_advance: int | None
    world_tick_seconds: float
    enemy_count: int


STAGES: tuple[CurriculumStage, ...] = (
    CurriculumStage(1, "food-corridor", 2, 1.0, 0),
    CurriculumStage(2, "turning-food", 2, 1.0, 0),
    CurriculumStage(3, "slow-predator", 3, 2.0, 1),
    CurriculumStage(4, "full-live-maze", None, 0.5, 2),
)


class CurriculumMazeEnvironment(GoalMazeEnvironment):
    """Versioned training curriculum that preserves the same MaleCNS controller.

    Stages deliberately teach simpler behavioral primitives before restoring the
    full V0.5 live-maze difficulty. Stage progression depends only on verified
    maze clears, never wall-clock runtime or hand-authored action labels.
    """

    def __init__(self, *, seed: int = 109) -> None:
        self.curriculum_stage = 1
        self.stage_clear_counts = {str(stage.number): 0 for stage in STAGES}
        self.stage_history: list[dict[str, Any]] = []
        self._advance_on_reset = False
        super().__init__(seed=seed)
        self._apply_stage_layout()

    @property
    def stage(self) -> CurriculumStage:
        return STAGES[self.curriculum_stage - 1]

    def effective_world_tick_seconds(self, default: float) -> float:
        return self.stage.world_tick_seconds

    def _blank_grid(self) -> list[list[str]]:
        return [["#" for _ in range(self.cols)] for _ in range(self.rows)]

    def _apply_stage_layout(self) -> None:
        stage = self.curriculum_stage
        if stage == 1:
            grid = self._blank_grid()
            y = 7
            for x in range(2, 17):
                grid[y][x] = " "
            for x in (4, 7, 10, 13, 16):
                grid[y][x] = "."
            self.grid = grid
            self.fly = {"x": 2, "y": y, "dir": "RIGHT"}
            self.enemies = []
            return

        if stage == 2:
            grid = self._blank_grid()
            y = 8
            for x in range(2, 11):
                grid[y][x] = " "
            for yy in range(3, 9):
                grid[yy][10] = " "
            for x, yy in ((4, y), (7, y), (10, y), (10, 6), (10, 4), (10, 3)):
                grid[yy][x] = "."
            self.grid = grid
            self.fly = {"x": 2, "y": y, "dir": "RIGHT"}
            self.enemies = []
            return

        # Stages 3 and 4 intentionally reuse the canonical V0.5 maze geometry.
        # The difference is predator count/speed, so vision remains comparable.
        if stage == 3:
            self.enemies = [{"x": self.cols - 2, "y": self.rows - 2}]
        else:
            self.enemies = [
                {"x": self.cols - 2, "y": self.rows - 2},
                {"x": self.cols - 3, "y": 1},
            ]

    def reset(self, reason: str = "reset") -> None:
        if getattr(self, "_advance_on_reset", False):
            self.curriculum_stage = min(len(STAGES), self.curriculum_stage + 1)
            self._advance_on_reset = False
        super().reset(reason)
        if hasattr(self, "curriculum_stage"):
            self._apply_stage_layout()

    def _record_clear(self) -> None:
        super()._record_clear()
        key = str(self.curriculum_stage)
        self.stage_clear_counts[key] = int(self.stage_clear_counts.get(key, 0)) + 1
        stage = self.stage
        entry = {
            "stage": stage.number,
            "stage_name": stage.name,
            "stage_clear": self.stage_clear_counts[key],
            "total_clear": self.total_clears,
            "total_ticks": self.total_ticks,
            "total_world_ticks": self.total_world_ticks,
        }
        self.stage_history.append(entry)
        target = stage.clears_to_advance
        if target is not None and self.stage_clear_counts[key] >= target:
            self._advance_on_reset = True

    def restore(self, payload: dict[str, Any]) -> None:
        super().restore(payload)
        if payload.get("curriculum_version") == CURRICULUM_VERSION:
            stage = int(payload.get("curriculum_stage", 1))
            self.curriculum_stage = min(len(STAGES), max(1, stage))
            counts = payload.get("stage_clear_counts") or {}
            if isinstance(counts, dict):
                self.stage_clear_counts = {
                    str(item.number): max(0, int(counts.get(str(item.number), 0)))
                    for item in STAGES
                }
            history = payload.get("stage_history") or []
            if isinstance(history, list):
                self.stage_history = [dict(item) for item in history if isinstance(item, dict)]
            self._advance_on_reset = bool(payload.get("advance_on_reset", False))
        else:
            # V0.5 migration: retain the trained brain and global counters, but
            # start the new curriculum at Stage 1 instead of inheriting a hard maze.
            self.curriculum_stage = 1
            self.stage_clear_counts = {str(stage.number): 0 for stage in STAGES}
            self.stage_history = []
            self._advance_on_reset = False
        self._apply_stage_layout()

    def snapshot(self, *, include_grid: bool = True) -> dict[str, Any]:
        data = super().snapshot(include_grid=include_grid)
        stage = self.stage
        data.update(
            {
                "curriculum_version": CURRICULUM_VERSION,
                "curriculum_stage": stage.number,
                "curriculum_stage_name": stage.name,
                "curriculum_stage_clears": self.stage_clear_counts[str(stage.number)],
                "curriculum_clears_to_advance": stage.clears_to_advance,
                "curriculum_enemy_count": stage.enemy_count,
                "curriculum_world_tick_seconds": stage.world_tick_seconds,
                "curriculum_stage_history": [dict(item) for item in self.stage_history],
                "curriculum_complete": stage.number == len(STAGES),
            }
        )
        return data

    def persistence_snapshot(self) -> dict[str, Any]:
        data = super().persistence_snapshot()
        data.update(
            {
                "curriculum_version": CURRICULUM_VERSION,
                "curriculum_stage": self.curriculum_stage,
                "stage_clear_counts": dict(self.stage_clear_counts),
                "stage_history": [dict(item) for item in self.stage_history],
                "advance_on_reset": self._advance_on_reset,
            }
        )
        return data
