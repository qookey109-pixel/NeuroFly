from __future__ import annotations

import math
from typing import Any

from .vision import (
    VISION_FIELD_DEGREES,
    VISION_MAX_RANGE_CELLS,
    VISION_MODEL,
    WALL_RENDERING_POLICY,
    _wall_depth_salience,
    _wall_texture_offset,
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


def _heading_radians(fly: dict[str, Any]) -> float:
    override = fly.get("_heading_radians")
    if override is not None:
        value = float(override)
        if not math.isfinite(value):
            raise ValueError("visual heading override must be finite")
        return _normalize_angle(value)
    return _DIR_ANGLES[str(fly["dir"])]


def interpolate_fly_pose(
    previous: dict[str, Any],
    current: dict[str, Any],
    fraction: float,
) -> dict[str, Any]:
    """Interpolate an egocentric visual pose without creating an action command."""
    t = max(0.0, min(1.0, float(fraction)))
    start_heading = _heading_radians(previous)
    end_heading = _heading_radians(current)
    heading_delta = _normalize_angle(end_heading - start_heading)
    return {
        "x": float(previous["x"]) + (float(current["x"]) - float(previous["x"])) * t,
        "y": float(previous["y"]) + (float(current["y"]) - float(previous["y"])) * t,
        "dir": str(current["dir"]),
        "_heading_radians": _normalize_angle(start_heading + heading_delta * t),
    }


def _bearing_degrees(fly: dict[str, Any], x: float, y: float) -> float:
    dx = x - (float(fly["x"]) + 0.5)
    dy = y - (float(fly["y"]) + 0.5)
    world = math.atan2(dy, dx)
    heading = _heading_radians(fly)
    return math.degrees(_normalize_angle(world - heading))


def _distance(fly: dict[str, Any], x: float, y: float) -> float:
    return math.hypot(
        x - (float(fly["x"]) + 0.5),
        y - (float(fly["y"]) + 0.5),
    )


def visual_contract(
    *,
    fly: dict[str, Any] | None,
    enemies: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Pure-Python visual contract used for telemetry and tests.

    It deliberately reports sensory geometry rather than a target action. The
    actual RGB retinal proxy is built by ``retinalize_topdown_rgb``.
    """

    if not fly or (
        str(fly.get("dir")) not in _DIR_ANGLES
        and fly.get("_heading_radians") is None
    ):
        return {
            "model": VISION_MODEL,
            "engineered_proxy": True,
            "available": False,
            "field_degrees": VISION_FIELD_DEGREES,
        }

    visible_enemies = 0
    nearest: dict[str, Any] | None = None
    for enemy in enemies or []:
        x = float(enemy["x"]) + 0.5
        y = float(enemy["y"]) + 0.5
        bearing = _bearing_degrees(fly, x, y)
        distance = _distance(fly, x, y)
        if abs(bearing) > VISION_FIELD_DEGREES / 2.0 or distance > VISION_MAX_RANGE_CELLS:
            continue
        visible_enemies += 1
        item = {
            "bearing_degrees": round(bearing, 3),
            "distance_cells": round(distance, 4),
            "looming_proxy": round(min(1.0, 1.5 / max(distance, 0.25)), 6),
        }
        if nearest is None or item["distance_cells"] < nearest["distance_cells"]:
            nearest = item

    return {
        "model": VISION_MODEL,
        "engineered_proxy": True,
        "available": True,
        "field_degrees": VISION_FIELD_DEGREES,
        "max_range_cells": VISION_MAX_RANGE_CELLS,
        "coordinate_frame": "egocentric-wide-panorama",
        "wall_rendering_policy": WALL_RENDERING_POLICY,
        "visible_enemies": visible_enemies,
        "nearest_enemy": nearest,
        "channels": {
            "luminance": "R1-R6-like brightness via pinned Stonkfly mapping",
            "color": "R8 blue-green proxy via pinned Stonkfly mapping",
            "motion": "temporal scene change through retained visual dynamics",
            "looming": "approaching objects occupy more retinal area",
        },
    }


def retinalize_topdown_rgb(
    frame: Any,
    *,
    fly: dict[str, Any] | None,
    enemies: list[dict[str, Any]] | None,
    cols: int = 19,
    rows: int = 14,
    width: int = 320,
    height: int = 180,
) -> tuple[Any, dict[str, Any]]:
    """Convert the omniscient renderer into a fly-centered retinal proxy.

    The environment may still render a top-down frame for debugging, but MaleCNS
    never receives that map directly. This adapter ray-casts a 300-degree local
    panorama from the fly pose. Walls provide luminance/optic-flow structure;
    food remains a small blue/green visual target; predators become dark looming
    silhouettes. No coordinates, route, or target action are encoded in the
    returned neural image.

    This is biologically inspired engineering, not a validated reconstruction of
    Drosophila ommatidial optics.
    """

    try:
        import numpy as np
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError("Fly visual adapter requires Pillow and NumPy") from exc

    source = np.asarray(frame, dtype=np.uint8)
    if source.ndim != 3 or source.shape[2] != 3:
        raise ValueError("Fly visual adapter requires an HxWx3 RGB frame")

    contract = visual_contract(fly=fly, enemies=enemies)
    if not contract["available"]:
        return source, contract

    assert fly is not None
    source_h, source_w = source.shape[:2]
    image = Image.new("RGB", (width, height), (176, 190, 177))
    draw = ImageDraw.Draw(image)
    horizon = height // 2
    draw.rectangle((0, 0, width, horizon), fill=(176, 190, 177))
    draw.rectangle((0, horizon, width, height), fill=(116, 128, 110))
    draw.line((0, horizon, width, horizon), fill=(205, 214, 199), width=1)

    heading = _heading_radians(fly)
    origin_x = float(fly["x"]) + 0.5
    origin_y = float(fly["y"]) + 0.5
    half_field = VISION_FIELD_DEGREES / 2.0

    def sample_grid(gx: float, gy: float) -> tuple[int, int, int]:
        px = max(0, min(source_w - 1, int(gx / cols * source_w)))
        py = max(0, min(source_h - 1, int(gy / rows * source_h)))
        value = source[py, px]
        return int(value[0]), int(value[1]), int(value[2])

    def wall_hit(relative_degrees: float) -> tuple[float, float, float]:
        angle = heading + math.radians(relative_degrees)
        distance = 0.12
        while distance <= VISION_MAX_RANGE_CELLS:
            gx = origin_x + math.cos(angle) * distance
            gy = origin_y + math.sin(angle) * distance
            if gx < 0 or gy < 0 or gx >= cols or gy >= rows:
                return distance, gx, gy
            r, g, b = sample_grid(gx, gy)
            # Canonical maze walls are dark green. A conservative luminance and
            # green-channel test avoids interpreting bright food as a wall.
            luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
            if luminance < 95.0 and g >= r * 0.9:
                return distance, gx, gy
            distance += 0.12
        gx = origin_x + math.cos(angle) * VISION_MAX_RANGE_CELLS
        gy = origin_y + math.sin(angle) * VISION_MAX_RANGE_CELLS
        return VISION_MAX_RANGE_CELLS, gx, gy

    def wall_distance(relative_degrees: float) -> float:
        return wall_hit(relative_degrees)[0]

    # Ray-cast the wide visual field. Near walls cover more retinal height,
    # naturally producing expansion as the fly approaches an obstacle.
    for px in range(width):
        relative = -half_field + (px / max(1, width - 1)) * VISION_FIELD_DEGREES
        distance, hit_x, hit_y = wall_hit(relative)
        salience = _wall_depth_salience(distance)
        wall_half_height = int(6 + salience * height * 0.44)
        top = max(0, horizon - wall_half_height)
        bottom = min(height - 1, horizon + wall_half_height)
        base_shade = int(124 - salience * 92)
        shade = max(8, min(164, base_shade + _wall_texture_offset(hit_x, hit_y)))
        draw.line(
            (px, top, px, bottom),
            fill=(shade, min(178, shade + 14), min(172, shade + 8)),
        )

    # Recover food markers only at canonical cell centers, then project them into
    # the local panorama. This preserves visual availability without exposing the
    # entire map. Food odor remains an independent and stronger appetitive cue.
    food_palette = {
        "food": (224, 171, 47),
        "energy": (70, 150, 230),
    }
    visible_food = 0
    for gy in range(rows):
        for gx in range(cols):
            r, g, b = sample_grid(gx + 0.5, gy + 0.5)
            kind = None
            for label, color in food_palette.items():
                if abs(r - color[0]) <= 18 and abs(g - color[1]) <= 18 and abs(b - color[2]) <= 18:
                    kind = label
                    break
            if kind is None:
                continue
            x = gx + 0.5
            y = gy + 0.5
            bearing = _bearing_degrees(fly, x, y)
            distance = _distance(fly, x, y)
            if abs(bearing) > half_field or distance > VISION_MAX_RANGE_CELLS:
                continue
            visible_food += 1
            out_x = int((bearing + half_field) / VISION_FIELD_DEGREES * (width - 1))
            radius = max(1, min(7 if kind == "energy" else 4, int(6.0 / max(distance, 0.8))))
            out_y = horizon + max(2, int(height * 0.12 / max(distance, 1.0)))
            color = (70, 134, 225) if kind == "energy" else (91, 188, 111)
            draw.ellipse((out_x - radius, out_y - radius, out_x + radius, out_y + radius), fill=color)

    for enemy in enemies or []:
        x = float(enemy["x"]) + 0.5
        y = float(enemy["y"]) + 0.5
        bearing = _bearing_degrees(fly, x, y)
        distance = _distance(fly, x, y)
        if abs(bearing) > half_field or distance > VISION_MAX_RANGE_CELLS:
            continue
        out_x = int((bearing + half_field) / VISION_FIELD_DEGREES * (width - 1))
        radius = max(3, min(28, int(23.0 / max(distance, 0.65))))
        out_y = horizon - max(0, int(radius * 0.2))
        draw.ellipse(
            (out_x - radius, out_y - radius, out_x + radius, out_y + radius),
            fill=(24, 27, 30),
            outline=(220, 224, 218),
            width=max(1, radius // 7),
        )

    contract["visible_food"] = visible_food
    contract["wall_distance_cells"] = {
        "left": round(wall_distance(-60.0), 3),
        "front": round(wall_distance(0.0), 3),
        "right": round(wall_distance(60.0), 3),
    }
    return np.asarray(image, dtype=np.uint8), contract
