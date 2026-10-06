from neurofly.vision import (
    VISION_FIELD_DEGREES,
    VISION_MODEL,
    WALL_RENDERING_POLICY,
    _wall_depth_salience,
    _wall_texture_offset,
)
from neurofly.vision_adapter import interpolate_fly_pose, visual_contract


def test_visual_contract_is_egocentric_and_action_free() -> None:
    fly = {"x": 5, "y": 5, "dir": "RIGHT"}
    enemies = [{"x": 7, "y": 5}, {"x": 2, "y": 5}]

    state = visual_contract(fly=fly, enemies=enemies)

    assert state["model"] == VISION_MODEL
    assert state["available"] is True
    assert state["field_degrees"] == VISION_FIELD_DEGREES
    assert state["coordinate_frame"] == "egocentric-wide-panorama"
    assert state["wall_rendering_policy"] == WALL_RENDERING_POLICY
    assert state["visible_enemies"] == 1
    assert abs(state["nearest_enemy"]["bearing_degrees"]) < 1e-6
    assert "action" not in state
    assert "target" not in state


def test_visual_contract_changes_with_heading() -> None:
    enemy = [{"x": 7, "y": 5}]
    facing_right = visual_contract(
        fly={"x": 5, "y": 5, "dir": "RIGHT"},
        enemies=enemy,
    )
    facing_down = visual_contract(
        fly={"x": 5, "y": 5, "dir": "DOWN"},
        enemies=enemy,
    )

    assert facing_right["nearest_enemy"]["bearing_degrees"] == 0.0
    assert facing_down["nearest_enemy"]["bearing_degrees"] < 0.0


def test_visual_contract_can_be_unavailable_without_pose() -> None:
    state = visual_contract(fly=None, enemies=[])
    assert state["model"] == VISION_MODEL
    assert state["available"] is False


def test_wall_depth_salience_expands_near_vs_open_contrast() -> None:
    near = _wall_depth_salience(0.6)
    medium = _wall_depth_salience(1.5)
    open_space = _wall_depth_salience(3.0)

    assert WALL_RENDERING_POLICY == "world-anchored-wall-texture-v4"
    assert 0.0 <= open_space < medium < near <= 1.0
    assert (near - medium) > ((1.0 - 0.6 / 8.0) - (1.0 - 1.5 / 8.0))


def test_wall_texture_is_periodic_nonunique_and_avoids_one_cell_aliasing() -> None:
    origin = _wall_texture_offset(0.20, 0.20)
    one_cell_forward = _wall_texture_offset(1.20, 0.20)
    exact_period_repeat = _wall_texture_offset(1.70, 0.20)

    assert origin == exact_period_repeat
    assert origin != one_cell_forward
    assert abs(origin) <= 28
    assert abs(one_cell_forward) <= 28


def test_interpolated_fly_pose_preserves_real_translation_and_turn_geometry() -> None:
    previous = {"x": 4, "y": 5, "dir": "RIGHT"}
    current = {"x": 5, "y": 5, "dir": "DOWN"}

    start = interpolate_fly_pose(previous, current, 0.0)
    middle = interpolate_fly_pose(previous, current, 0.5)
    end = interpolate_fly_pose(previous, current, 1.0)

    assert start["x"] == 4.0
    assert end["x"] == 5.0
    assert middle["x"] == 4.5
    assert middle["y"] == 5.0
    assert abs(middle["_heading_radians"] - 0.7853981633974483) < 1e-12
    assert abs(end["_heading_radians"] - 1.5707963267948966) < 1e-12


def test_interpolated_heading_contract_remains_action_free() -> None:
    pose = interpolate_fly_pose(
        {"x": 5, "y": 5, "dir": "RIGHT"},
        {"x": 5, "y": 5, "dir": "DOWN"},
        0.5,
    )
    state = visual_contract(fly=pose, enemies=[{"x": 7, "y": 5}])

    assert state["available"] is True
    assert "action" not in state
    assert "target" not in state
