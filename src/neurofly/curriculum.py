from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .goal_training import GoalMazeEnvironment
from .olfaction import virtual_olfaction


CURRICULUM_VERSION = "neurofly-curriculum-v4"
ACTION_AUTONOMY_POLICY = "neurofly-sensory-only-action-autonomy-v1"
ANTI_STALL_POLICY = "neurofly-stall-observation-only-v2"
ANTI_STALL_STATIONARY_LIMIT = 2
STALL_STIMULUS_POLICY = "neurofly-nondirectional-stall-aversive-v1"
STALL_STIMULUS_AFTER = 4
STALL_STIMULUS_INTERVAL = 4


@dataclass(frozen=True)
class CurriculumStage:
    number: int
    name: str
    clears_to_advance: int | None
    world_tick_seconds: float
    enemy_count: int


STAGES: tuple[CurriculumStage, ...] = (
    CurriculumStage(1, "full-maze-foraging", 2, 2.0, 0),
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

    MaleCNS owns every locomotor action. The environment may observe stalls and
    provide sensory/reinforcement inputs, but it must never replace a decoded
    HOLD/FORWARD/TURN action with a hand-authored movement. Raw and applied
    actions therefore remain identical by construction.
    """

    def __init__(self, *, seed: int = 109) -> None:
        self.curriculum_stage = 1
        self.stage_clear_counts = {str(stage.number): 0 for stage in STAGES}
        self.stage_history: list[dict[str, Any]] = []
        self._advance_on_reset = False
        self._stationary_agent_steps = 0
        self._force_forward_next = False
        self.last_raw_action = "HOLD"
        self.last_applied_action = "HOLD"
        self.last_action_overridden = False
        self.last_override_reason: str | None = None
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

    def _reset_anti_stall(self) -> None:
        self._stationary_agent_steps = 0
        self._force_forward_next = False
        self.last_raw_action = "HOLD"
        self.last_applied_action = "HOLD"
        self.last_action_overridden = False
        self.last_override_reason = None

    def reinforcement(self) -> str:
        """Add only a non-directional stimulus when translationally stalled."""
        base = super().reinforcement()
        if base != "none":
            return base
        if (
            self._stationary_agent_steps >= STALL_STIMULUS_AFTER
            and self._stationary_agent_steps % STALL_STIMULUS_INTERVAL == 0
        ):
            return "aversive"
        return "none"

    def _canonical_enemy_spawns(self) -> list[dict[str, int]]:
        return [
            {"x": self.cols - 2, "y": self.rows - 2},
            {"x": self.cols - 3, "y": 1},
        ]

    def _ensure_stage_enemies(self) -> None:
        """Keep restored checkpoints aligned with the stage predator contract."""
        target = self.stage.enemy_count
        current = [dict(enemy) for enemy in self.enemies[:target]]
        occupied = {(int(enemy["x"]), int(enemy["y"])) for enemy in current}
        fly_xy = (int(self.fly["x"]), int(self.fly["y"]))
        for spawn in self._canonical_enemy_spawns():
            if len(current) >= target:
                break
            xy = (spawn["x"], spawn["y"])
            if xy == fly_xy or xy in occupied:
                continue
            current.append(dict(spawn))
            occupied.add(xy)
        self.enemies = current

    def _apply_stage_layout(self) -> None:
        """Rebuild the exact canonical maze and vary only predator pressure."""
        self.grid = self._make_grid()
        self.fly = {"x": 1, "y": 1, "dir": "RIGHT"}

        canonical_enemy_spawns = self._canonical_enemy_spawns()
        self.enemies = [dict(item) for item in canonical_enemy_spawns[: self.stage.enemy_count]]

        # Preserve the canonical V0.5 visual/food geometry even when a curriculum
        # stage temporarily uses fewer than the full two predators.
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
        self._reset_anti_stall()
        if hasattr(self, "curriculum_stage"):
            self._apply_stage_layout()

    def agent_step(self, action: str, *, move_enemies: bool):
        """Apply the decoded MaleCNS action verbatim and observe stalls only."""
        raw_action = action
        before = (int(self.fly["x"]), int(self.fly["y"]))
        result = super().agent_step(raw_action, move_enemies=move_enemies)
        after = (int(self.fly["x"]), int(self.fly["y"]))

        self.last_raw_action = raw_action
        self.last_applied_action = raw_action
        self.last_action_overridden = False
        self.last_override_reason = None
        self._force_forward_next = False

        if result.terminal or after != before or raw_action in {"TURN_LEFT", "TURN_RIGHT"}:
            self._stationary_agent_steps = 0
        else:
            self._stationary_agent_steps += 1

        return result

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
        source_curriculum = payload.get("curriculum_version")
        same_curriculum = source_curriculum == CURRICULUM_VERSION
        sensory_only_compatible = source_curriculum in {
            CURRICULUM_VERSION,
            "neurofly-curriculum-v3",
        }
        empty_enemies = payload.get("enemies") == []
        if empty_enemies:
            # The generic V0.5 persistence validator requires at least one enemy.
            # Feed it a temporary valid enemy so historical enemy-free checkpoints
            # can migrate safely before the current stage predator floor is applied.
            compatible = dict(payload)
            compatible["enemies"] = [self._compat_enemy_for_empty_checkpoint(payload)]
            super().restore(compatible)
            self.enemies = []
        else:
            super().restore(payload)

        if sensory_only_compatible:
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
            self._stationary_agent_steps = max(
                0, int(payload.get("anti_stall_stationary_steps", 0))
            )
            self._force_forward_next = False
            self.last_raw_action = str(payload.get("raw_brain_action", self.last_action))
            self.last_applied_action = self.last_raw_action
            self.last_action_overridden = False
            self.last_override_reason = None
            self._ensure_stage_enemies()
            # The superclass already restored exact grid/fly/RNG state. Only the
            # predator floor is repaired when an older checkpoint had no enemy.
            return

        # Migration from older pre-v3 curricula: retain the trained brain and
        # global behavior counters, but begin curriculum v4 on the full canonical
        # maze instead of carrying forward a simplified training layout.
        self.curriculum_stage = 1
        self.stage_clear_counts = {str(stage.number): 0 for stage in STAGES}
        self.stage_history = []
        self._advance_on_reset = False
        self._reset_anti_stall()
        GoalMazeEnvironment.reset(self, "curriculum_v4_migration")
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
                "action_autonomy_policy": ACTION_AUTONOMY_POLICY,
                "direct_action_override_enabled": False,
                "stall_stimulus_policy": STALL_STIMULUS_POLICY,
                "stall_stimulus_after": STALL_STIMULUS_AFTER,
                "stall_stimulus_interval": STALL_STIMULUS_INTERVAL,
                "anti_stall_policy": ANTI_STALL_POLICY,
                "anti_stall_stationary_steps": self._stationary_agent_steps,
                "anti_stall_force_forward_next": self._force_forward_next,
                "raw_brain_action": self.last_raw_action,
                "applied_action": self.last_applied_action,
                "action_overridden": self.last_action_overridden,
                "override_reason": self.last_override_reason,
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
                "action_autonomy_policy": ACTION_AUTONOMY_POLICY,
                "direct_action_override_enabled": False,
                "stall_stimulus_policy": STALL_STIMULUS_POLICY,
                "stall_stimulus_after": STALL_STIMULUS_AFTER,
                "stall_stimulus_interval": STALL_STIMULUS_INTERVAL,
                "anti_stall_policy": ANTI_STALL_POLICY,
                "anti_stall_stationary_steps": self._stationary_agent_steps,
                "anti_stall_force_forward_next": self._force_forward_next,
                "raw_brain_action": self.last_raw_action,
                "applied_action": self.last_applied_action,
                "action_overridden": self.last_action_overridden,
                "override_reason": self.last_override_reason,
            }
        )
        return data
