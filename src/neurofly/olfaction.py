from __future__ import annotations

import math
from typing import Any


OLFACTION_MODEL = "neurofly-virtual-olfaction-v1"
FOOD_ORN_TYPE = "ORN_DM1"
DANGER_ORN_TYPE = "ORN_DA2"

_DIR_VECTORS = {
    "UP": (0.0, -1.0),
    "RIGHT": (1.0, 0.0),
    "DOWN": (0.0, 1.0),
    "LEFT": (-1.0, 0.0),
}


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _bilateral_signal(
    *,
    fly: dict[str, Any],
    source_x: int,
    source_y: int,
    decay_cells: float,
    strength: float,
) -> tuple[float, float, float]:
    dx = float(source_x) - float(fly["x"])
    dy = float(source_y) - float(fly["y"])
    distance = math.hypot(dx, dy)
    base = _bounded(float(strength) * math.exp(-distance / float(decay_cells)))
    if distance <= 1e-9:
        return base, base, 0.0

    heading_x, heading_y = _DIR_VECTORS[str(fly["dir"])]
    right_x, right_y = -heading_y, heading_x
    lateral = (dx * right_x + dy * right_y) / distance
    lateral = max(-1.0, min(1.0, lateral))

    # Bilateral difference is intentionally bounded. It provides a directional
    # sensory cue without encoding a target action or a path solution.
    gain = 0.45
    left = _bounded(base * (1.0 - gain * lateral))
    right = _bounded(base * (1.0 + gain * lateral))
    return left, right, distance


def _strongest_source(
    *,
    fly: dict[str, Any],
    sources: list[tuple[int, int, float]],
    decay_cells: float,
) -> dict[str, Any]:
    if not sources:
        return {
            "left": 0.0,
            "right": 0.0,
            "intensity": 0.0,
            "distance_cells": None,
            "source": None,
        }

    best: dict[str, Any] | None = None
    best_intensity = -1.0
    for x, y, strength in sources:
        left, right, distance = _bilateral_signal(
            fly=fly,
            source_x=x,
            source_y=y,
            decay_cells=decay_cells,
            strength=strength,
        )
        intensity = max(left, right)
        if intensity > best_intensity:
            best_intensity = intensity
            best = {
                "left": round(left, 6),
                "right": round(right, 6),
                "intensity": round((left + right) / 2.0, 6),
                "distance_cells": round(distance, 4),
                "source": {"x": int(x), "y": int(y)},
            }
    assert best is not None
    return best


def virtual_olfaction(
    *,
    grid: list[list[str]],
    fly: dict[str, Any],
    enemies: list[dict[str, int]],
) -> dict[str, Any]:
    """Return engineered odor cues for the game world.

    Food is represented by an appetitive ORN_DM1/Or42b proxy and enemies by an
    aversive ORN_DA2/Or56a (geosmin-like) proxy. These are game-to-connectome
    sensory mappings, not claims that pellets or enemies literally emit those
    molecules. Reward and aversive reinforcement remain separate outcome
    signals and are never inferred from odor intensity alone.
    """

    food_sources: list[tuple[int, int, float]] = []
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell == ".":
                food_sources.append((x, y, 1.0))
            elif cell == "o":
                food_sources.append((x, y, 1.25))

    danger_sources = [
        (int(enemy["x"]), int(enemy["y"]), 1.0)
        for enemy in enemies
    ]

    return {
        "model": OLFACTION_MODEL,
        "engineered_proxy": True,
        "food": {
            "orn_type": FOOD_ORN_TYPE,
            "receptor_proxy": "Or42b",
            **_strongest_source(
                fly=fly,
                sources=food_sources,
                decay_cells=4.0,
            ),
        },
        "danger": {
            "orn_type": DANGER_ORN_TYPE,
            "receptor_proxy": "Or56a/geosmin-like",
            **_strongest_source(
                fly=fly,
                sources=danger_sources,
                decay_cells=3.0,
            ),
        },
    }
