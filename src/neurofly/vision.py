from __future__ import annotations

import math
from typing import Any


VISION_MODEL = "neurofly-compound-eye-proxy-v1"
VISION_FIELD_DEGREES = 300.0
VISION_MAX_RANGE_CELLS = 8.0
WALL_RENDERING_POLICY = "world-anchored-wall-texture-v3"
WALL_DEPTH_CONTRAST_POWER = 2.0
WALL_DEPTH_CONTRAST_GAIN = 1.15
WALL_TEXTURE_PERIOD_CELLS = 0.5
WALL_TEXTURE_LUMINANCE_AMPLITUDE = 28


def _wall_depth_salience(
    distance: float,
    *,
    max_range: float = VISION_MAX_RANGE_CELLS,
) -> float:
    """Nonlinearly expand retinal contrast between near walls and open space.

    This transforms egocentric ray distance into visual salience only. It does
    not encode a route, target direction, or action.
    """
    limit = max(1e-9, float(max_range))
    closeness = max(0.0, min(1.0, 1.0 - float(distance) / limit))
    return max(
        0.0,
        min(
            1.0,
            WALL_DEPTH_CONTRAST_GAIN * (closeness ** WALL_DEPTH_CONTRAST_POWER),
        ),
    )

def _wall_texture_offset(hit_x: float, hit_y: float) -> int:
    """Return a repeating world-anchored wall texture luminance offset.

    The texture is periodic rather than position-unique, so it supplies local
    visual features / optic-flow structure without encoding a route or landmark
    identity. It is purely part of the rendered sensory scene.
    """

    period = max(1e-6, float(WALL_TEXTURE_PERIOD_CELLS))
    phase_x = int(math.floor(float(hit_x) / period))
    phase_y = int(math.floor(float(hit_y) / period))
    return (
        WALL_TEXTURE_LUMINANCE_AMPLITUDE
        if (phase_x + phase_y) % 2 == 0
        else -WALL_TEXTURE_LUMINANCE_AMPLITUDE
    )


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


def _ray_hit(
    *,
    grid: list[list[str]],
    fly: dict[str, Any],
    relative_degrees: float,
    max_range: float = VISION_MAX_RANGE_CELLS,
) -> tuple[float, float, float]:
    heading = _DIR_ANGLES[str(fly["dir"])]
    angle = heading + math.radians(relative_degrees)
    origin_x = float(fly["x"]) + 0.5
    origin_y = float(fly["y"]) + 0.5
    step = 0.12
    distance = step
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    while distance <= max_range:
        hit_x = origin_x + math.cos(angle) * distance
        hit_y = origin_y + math.sin(angle) * distance
        x = int(hit_x)
        y = int(hit_y)
        if x < 0 or y < 0 or x >= cols or y >= rows:
            return distance, hit_x, hit_y
        if grid[y][x] == "#":
            return distance, hit_x, hit_y
        distance += step
    hit_x = origin_x + math.cos(angle) * max_range
    hit_y = origin_y + math.sin(angle) * max_range
    return max_range, hit_x, hit_y


def _ray_distance(
    *,
    grid: list[list[str]],
    fly: dict[str, Any],
    relative_degrees: float,
    max_range: float = VISION_MAX_RANGE_CELLS,
) -> float:
    return _ray_hit(
        grid=grid,
        fly=fly,
        relative_degrees=relative_degrees,
        max_range=max_range,
    )[0]


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
        distance, hit_x, hit_y = _ray_hit(
            grid=grid,
            fly=fly,
            relative_degrees=relative,
        )
        wall_distances.append(distance)
        salience = _wall_depth_salience(distance)
        wall_half_height = int(6 + salience * height * 0.44)
        top = max(0, horizon - wall_half_height)
        bottom = min(height - 1, horizon + wall_half_height)
        base_shade = int(124 - salience * 92)
        shade = max(8, min(164, base_shade + _wall_texture_offset(hit_x, hit_y)))
        draw.line((px, top, px, bottom), fill=(shade, min(178, shade + 14), min(172, shade + 8)))

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
