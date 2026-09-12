from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .goal_training import GoalMazeEnvironment
from .olfaction import virtual_olfaction


CURRICULUM_VERSION = "neurofly-curriculum-v2"


@dataclass(frozen=True)
class CurriculumStage:
    number: int
    name: str
    clears_to_advance: int | None
    world_tick_seconds: float
    enemy_count: int


STAGES: tuple[CurriculumStage, ...] = (
    CurriculumStage(1, "full-maze-food-only", 2, 1.0, 0),
    CurriculumStage(2, "full-maze-slow-predator", 2, 2.0, 1),
    CurriculumStage(3, "full-maze-predator", 3, 1.0, 1),
    CurriculumStage(4, "full-live-maze", None, 0.5, 2),
)


class CurriculumMazeEnvironment(GoalMazeEnvironment):
    """Versioned training curriculum that preserves the same MaleCNS controller.

    Every stage uses the canonical V0.5 19x14 maze, start position, food layout,
    turns and visual geometry. Difficulty changes only through predator count and
    authoritative world-clock speed. Stage progression depends only on verified
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

    def threat_distance(self, x: int | None = None, y: int | None = None) -> int:
        if not self.enemies:
            return 1_000_000
        return super().threat_distance(x=x, y=y)

    def _apply_stage_layout(self) -> None:
        """Rebuild the exact canonical maze and vary only predator pressure."""
        self.grid = self._make_grid()
        self.fly = {"x": 1, "y": 1, "dir": "RIGHT"}

        canonical_enemy_spawns = [
            {"x": self.cols - 2, "y": self.rows - 2},
            {"x": self.cols - 3, "y": 1},
        ]
        self.enemies = [dict(item) for item in canonical_enemy_spawns[: self.stage.enemy_count]]

        # Preserve the canonical V0.5 visual/food geometry even when a curriculum
        # stage temporarily disables one or both predators.
        self.grid[1][1] = " "
        for enemy in canonical_enemy_spawns:
            self.grid[enemy["y"]][enemy["x"]] = " "
        for x, y in ((1, self.rows - 2), (self.cols - 2, 1), (8, 6), (15, 11)):
            if self.grid[y][x] != "#":
                self.grid[y][x] = "o"

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

    @staticmethod
    def _compat_enemy_for_empty_checkpoint(payload: dict[str, Any]) -> dict[str, int]:
        grid = payload.get("grid") or []
        fly = payload.get("fly") or {}
        fly_xy = (int(fly.get("x", -1)), int(fly.get("y", -1)))
        for y, row in enumerate(grid):
            if not isinstance(row, str):
                continue
            for x, cell in enumerate(row):
                if cell != "#" and (x, y) != fly_xy:
                    return {"x": x, "y": y}
        raise ValueError("Enemy-free curriculum checkpoint has no spare open cell")

    def restore(self, payload: dict[str, Any]) -> None:
        same_curriculum = payload.get("curriculum_version") == CURRICULUM_VERSION
        empty_enemies = payload.get("enemies") == []
        if empty_enemies:
            # The generic V0.5 persistence validator requires at least one enemy.
            # Feed it a temporary valid enemy so both v1 and v2 enemy-free
            # checkpoints can migrate safely.
            compatible = dict(payload)
            compatible["enemies"] = [self._compat_enemy_for_empty_checkpoint(payload)]
            super().restore(compatible)
            self.enemies = []
        else:
            super().restore(payload)

        if same_curriculum:
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
            # The superclass already restored exact grid/fly/RNG state.
            return

        # Migration from V0.5 or curriculum v1: retain the trained brain and
        # global behavior counters, but begin curriculum v2 on the full canonical
        # maze instead of carrying forward a simplified training layout.
        self.curriculum_stage = 1
        self.stage_clear_counts = {str(stage.number): 0 for stage in STAGES}
        self.stage_history = []
        self._advance_on_reset = False
        GoalMazeEnvironment.reset(self, "curriculum_v2_migration")
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
                "olfaction": virtual_olfaction(
                    grid=self.grid,
                    fly=self.fly,
                    enemies=self.enemies,
                ),
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
