from neurofly.vision import (
    VISION_FIELD_DEGREES,
    VISION_MODEL,
    WALL_RENDERING_POLICY,
    _wall_depth_salience,
)
from neurofly.vision_adapter import visual_contract


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

    assert WALL_RENDERING_POLICY == "nonlinear-depth-contrast-v2"
    assert 0.0 <= open_space < medium < near <= 1.0
    assert (near - medium) > ((1.0 - 0.6 / 8.0) - (1.0 - 1.5 / 8.0))
