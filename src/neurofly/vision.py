from __future__ import annotations

import math
from typing import Any


VISION_MODEL = "neurofly-compound-eye-proxy-v1"
VISION_FIELD_DEGREES = 300.0
VISION_MAX_RANGE_CELLS = 8.0

_DIR_ANGLES = {
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


def _relative_bearing_degrees(fly: dict[str, Any], x: float, y: float) -> float:
    dx = float(x) - (float(fly["x"]) + 0.5)
    dy = float(y) - (float(fly["y"]) + 0.5)
    world = math.atan2(dy, dx)
    heading = _DIR_ANGLES[str(fly["dir"])]
    return math.degrees(_normalize_angle(world - heading))


def _distance_cells(fly: dict[str, Any], x: float, y: float) -> float:
    return math.hypot(
        float(x) - (float(fly["x"]) + 0.5),
        float(y) - (float(fly["y"]) + 0.5),
    )


def _visible(bearing_degrees: float) -> bool:
    return abs(float(bearing_degrees)) <= VISION_FIELD_DEGREES / 2.0


def _ray_distance(
    *,
    grid: list[list[str]],
    fly: dict[str, Any],
    relative_degrees: float,
    max_range: float = VISION_MAX_RANGE_CELLS,
) -> float:
    heading = _DIR_ANGLES[str(fly["dir"])]
    angle = heading + math.radians(relative_degrees)
    origin_x = float(fly["x"]) + 0.5
    origin_y = float(fly["y"]) + 0.5
    step = 0.12
    distance = step
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    while distance <= max_range:
        x = int(origin_x + math.cos(angle) * distance)
        y = int(origin_y + math.sin(angle) * distance)
        if x < 0 or y < 0 or x >= cols or y >= rows:
            return distance
        if grid[y][x] == "#":
            return distance
        distance += step
    return max_range


def _nearest_visible_enemy(
    *,
    fly: dict[str, Any],
    enemies: list[dict[str, int]],
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    for enemy in enemies:
        cx = float(enemy["x"]) + 0.5
        cy = float(enemy["y"]) + 0.5
        bearing = _relative_bearing_degrees(fly, cx, cy)
        if not _visible(bearing):
            continue
        distance = _distance_cells(fly, cx, cy)
        candidate = {
            "bearing_degrees": round(bearing, 3),
            "distance_cells": round(distance, 4),
            # A bounded proxy for retinal expansion / looming salience. It is
            # deliberately descriptive telemetry, not a hand-authored action.
            "looming_proxy": round(min(1.0, 1.5 / max(distance, 0.25)), 6),
        }
        if best is None or candidate["distance_cells"] < best["distance_cells"]:
            best = candidate
    return best


def fly_vision_state(
    *,
    grid: list[list[str]],
    fly: dict[str, Any],
    enemies: list[dict[str, int]],
) -> dict[str, Any]:
    """Describe the engineered fly-like visual state for telemetry.

    The game no longer gives the brain an omniscient top-down map as visual
    input. Instead it renders a wide egocentric panorama. Walls create contrast
    and optic-flow changes, nearby objects occupy more retinal area, and scene
    motion emerges naturally as the fly or predators move.

    This is an engineered sensory adapter inspired by Drosophila wide-field
    compound-eye vision. It is not a claim of exact ommatidial optics or fully
    validated retinal physiology.
    """

    visible_food = 0
    visible_energy_food = 0
    nearest_food_distance: float | None = None
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell not in {".", "o"}:
                continue
            cx = float(x) + 0.5
            cy = float(y) + 0.5
            bearing = _relative_bearing_degrees(fly, cx, cy)
            if not _visible(bearing):
                continue
            distance = _distance_cells(fly, cx, cy)
            if cell == ".":
                visible_food += 1
            else:
                visible_energy_food += 1
            if nearest_food_distance is None or distance < nearest_food_distance:
                nearest_food_distance = distance

    nearest_enemy = _nearest_visible_enemy(fly=fly, enemies=enemies)
    visible_enemies = 0
    for enemy in enemies:
        bearing = _relative_bearing_degrees(
            fly,
            float(enemy["x"]) + 0.5,
            float(enemy["y"]) + 0.5,
        )
        if _visible(bearing):
            visible_enemies += 1

    return {
        "model": VISION_MODEL,
        "engineered_proxy": True,
        "field_degrees": VISION_FIELD_DEGREES,
        "max_range_cells": VISION_MAX_RANGE_CELLS,
        "coordinate_frame": "egocentric-wide-panorama",
        "channels": {
            "luminance": "R1-R6-like brightness through pinned Stonkfly mapping",
            "color": "R8 blue-green proxy through pinned Stonkfly mapping",
            "motion": "temporal frame change through retained visual dynamics",
            "looming": "retinal-size growth from approaching objects",
        },
        "wall_distance_cells": {
            "left": round(_ray_distance(grid=grid, fly=fly, relative_degrees=-60.0), 3),
            "front": round(_ray_distance(grid=grid, fly=fly, relative_degrees=0.0), 3),
            "right": round(_ray_distance(grid=grid, fly=fly, relative_degrees=60.0), 3),
        },
        "visible_food": visible_food,
        "visible_energy_food": visible_energy_food,
        "nearest_food_distance_cells": (
            None if nearest_food_distance is None else round(nearest_food_distance, 4)
        ),
        "visible_enemies": visible_enemies,
        "nearest_enemy": nearest_enemy,
    }


def render_compound_eye_rgb(
    *,
    grid: list[list[str]],
    fly: dict[str, Any],
    enemies: list[dict[str, int]],
    width: int = 320,
    height: int = 180,
) -> Any:
    """Render a wide egocentric retinal proxy for Stonkfly visual input.

    The frame intentionally omits the top-down maze map. A 300-degree panorama
    is ray-cast from the fly's current pose. Wall contrast and object angular
    size carry local spatial information; approaching predators therefore grow
    in retinal area without exposing coordinates or a solved path.
    """

    try:
        import numpy as np
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover - optional visual runtime
        raise RuntimeError("Fly visual rendering requires Pillow and NumPy") from exc

    if width < 32 or height < 32:
        raise ValueError("visual frame is too small")

    image = Image.new("RGB", (width, height), (151, 166, 151))
    draw = ImageDraw.Draw(image)
    horizon = height // 2

    # A quiet sky/ground split provides stable luminance landmarks while moving.
    draw.rectangle((0, 0, width, horizon), fill=(176, 190, 177))
    draw.rectangle((0, horizon, width, height), fill=(116, 128, 110))
    draw.line((0, horizon, width, horizon), fill=(205, 214, 199), width=1)

    half_field = VISION_FIELD_DEGREES / 2.0
    wall_distances: list[float] = []
    for px in range(width):
        relative = -half_field + (px / max(1, width - 1)) * VISION_FIELD_DEGREES
        distance = _ray_distance(grid=grid, fly=fly, relative_degrees=relative)
        wall_distances.append(distance)
        closeness = max(0.0, min(1.0, 1.0 - distance / VISION_MAX_RANGE_CELLS))
        wall_half_height = int(6 + closeness * height * 0.42)
        top = max(0, horizon - wall_half_height)
        bottom = min(height - 1, horizon + wall_half_height)
        shade = int(112 - closeness * 72)
        draw.line((px, top, px, bottom), fill=(shade, shade + 14, shade + 8))

    # Draw food as small blue/green-biased high-contrast targets. Odor remains the
    # dominant appetitive cue; the visual adapter does not encode a target action.
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell not in {".", "o"}:
                continue
            cx = float(x) + 0.5
            cy = float(y) + 0.5
            bearing = _relative_bearing_degrees(fly, cx, cy)
            if not _visible(bearing):
                continue
            distance = _distance_cells(fly, cx, cy)
            px = int((bearing + half_field) / VISION_FIELD_DEGREES * (width - 1))
            radius = max(1, min(8 if cell == "o" else 5, int(7.0 / max(distance, 0.8))))
            py = horizon + max(2, int(height * 0.12 / max(distance, 1.0)))
            color = (70, 134, 225) if cell == "o" else (91, 188, 111)
            draw.ellipse((px - radius, py - radius, px + radius, py + radius), fill=color)

    # Predators are visualized as dark looming silhouettes, not as a semantic
    # red 'enemy' label. Their angular size increases automatically with approach.
    for enemy in enemies:
        cx = float(enemy["x"]) + 0.5
        cy = float(enemy["y"]) + 0.5
        bearing = _relative_bearing_degrees(fly, cx, cy)
        if not _visible(bearing):
            continue
        distance = _distance_cells(fly, cx, cy)
        px = int((bearing + half_field) / VISION_FIELD_DEGREES * (width - 1))
        radius = max(3, min(28, int(23.0 / max(distance, 0.65))))
        py = horizon - max(0, int(radius * 0.2))
        draw.ellipse(
            (px - radius, py - radius, px + radius, py + radius),
            fill=(24, 27, 30),
            outline=(220, 224, 218),
            width=max(1, radius // 7),
        )

    return np.asarray(image, dtype=np.uint8)
