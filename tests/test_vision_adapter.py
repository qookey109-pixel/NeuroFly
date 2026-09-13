from neurofly.vision import VISION_FIELD_DEGREES, VISION_MODEL
from neurofly.vision_adapter import visual_contract


def test_visual_contract_is_egocentric_and_action_free() -> None:
    fly = {"x": 5, "y": 5, "dir": "RIGHT"}
    enemies = [{"x": 7, "y": 5}, {"x": 2, "y": 5}]

    state = visual_contract(fly=fly, enemies=enemies)

    assert state["model"] == VISION_MODEL
    assert state["available"] is True
    assert state["field_degrees"] == VISION_FIELD_DEGREES
    assert state["coordinate_frame"] == "egocentric-wide-panorama"
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
