from neurofly.brain_runtime import DemoBrain, brain_status
from neurofly.maze_runtime import MazeEnvironment, MazeSession


def test_maze_environment_exposes_reusable_contract() -> None:
    env = MazeEnvironment(seed=7)
    before = env.snapshot()
    assert before["episode"] == 1
    assert before["food_left"] > 0
    assert before["demo_action"] in {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}

    result = env.step("FORWARD")
    after = env.snapshot()
    assert isinstance(result.reward, float)
    assert after["ticks"] == 1
    assert after["last_action"] == "FORWARD"
    assert after["reinforcement"] in {"none", "reward", "aversive"}


def test_demo_brain_can_drive_headless_session_without_visual_dependencies() -> None:
    session = MazeSession(DemoBrain(), checkpoint=None, seed=11)
    state = session.tick()
    assert state["brain"]["backend"] == "demo"
    assert state["last_action"] in {"TURN_LEFT", "TURN_RIGHT", "FORWARD", "HOLD"}
    assert "grid" in state


def test_brain_status_is_safe_without_optional_dataset() -> None:
    status = brain_status()
    assert status["backend"] == "malecns"
    assert isinstance(status["installed"], bool)
    assert isinstance(status["prepared"], bool)
