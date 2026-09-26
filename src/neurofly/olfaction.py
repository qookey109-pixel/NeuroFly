from __future__ import annotations

import math
from typing import Any


OLFACTION_MODEL = "neurofly-virtual-olfaction-v2"
FOOD_ORN_TYPE = "ORN_DM1"
DANGER_ORN_TYPE = "ORN_DA2"
FOOD_BILATERAL_CONTRAST_GAIN = 0.75
DANGER_BILATERAL_CONTRAST_GAIN = 0.45
FOOD_FIELD_POWER = 4.0
FOOD_DECAY_CELLS = 5.0

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
    lateral_gain: float = 0.45,
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
    gain = max(0.0, min(0.95, float(lateral_gain)))
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
            "source_count": 0,
            "aggregation": "strongest-source-field",
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
            lateral_gain=DANGER_BILATERAL_CONTRAST_GAIN,
        )
        intensity = max(left, right)
        if intensity > best_intensity:
            best_intensity = intensity
            best = {
                "left": round(left, 6),
                "right": round(right, 6),
                "intensity": round((left + right) / 2.0, 6),
                "source_count": len(sources),
                "aggregation": "strongest-source-field",
            }
    assert best is not None
    return best


def _aggregate_sources(
    *,
    fly: dict[str, Any],
    sources: list[tuple[int, int, float]],
    decay_cells: float,
    lateral_gain: float,
    power: float,
) -> dict[str, Any]:
    """Build a smooth bilateral concentration field from all available sources."""
    if not sources:
        return {
            "left": 0.0,
            "right": 0.0,
            "intensity": 0.0,
            "source_count": 0,
            "aggregation": f"lp{power:g}-all-sources",
        }

    p = max(1.0, float(power))
    left_power = 0.0
    right_power = 0.0
    for x, y, strength in sources:
        left, right, _ = _bilateral_signal(
            fly=fly,
            source_x=x,
            source_y=y,
            decay_cells=decay_cells,
            strength=strength,
            lateral_gain=lateral_gain,
        )
        left_power += left**p
        right_power += right**p

    left = _bounded(left_power ** (1.0 / p))
    right = _bounded(right_power ** (1.0 / p))
    return {
        "left": round(left, 6),
        "right": round(right, 6),
        "intensity": round((left + right) / 2.0, 6),
        "source_count": len(sources),
        "aggregation": f"lp{p:g}-all-sources",
    }


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
            "contrast_gain": FOOD_BILATERAL_CONTRAST_GAIN,
            **_aggregate_sources(
                fly=fly,
                sources=food_sources,
                decay_cells=FOOD_DECAY_CELLS,
                lateral_gain=FOOD_BILATERAL_CONTRAST_GAIN,
                power=FOOD_FIELD_POWER,
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
