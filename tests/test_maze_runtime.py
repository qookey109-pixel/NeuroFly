from pathlib import Path

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


def test_maze_state_restores_from_checkpoint(tmp_path: Path) -> None:
    checkpoint = tmp_path / "brain.npz"
    first = MazeSession(DemoBrain(), checkpoint=checkpoint, seed=17)
    first.tick()
    first.tick()
    expected = first.environment.snapshot()
    first.save()

    restored = MazeSession(DemoBrain(), checkpoint=checkpoint, seed=999)
    actual = restored.environment.snapshot()
    assert actual["episode"] == expected["episode"]
    assert actual["ticks"] == expected["ticks"]
    assert actual["fly"] == expected["fly"]
    assert actual["enemies"] == expected["enemies"]
    assert actual["grid"] == expected["grid"]
    assert actual["food_left"] == expected["food_left"]


def test_brain_status_is_safe_without_optional_dataset() -> None:
    status = brain_status()
    assert status["backend"] == "malecns"
    assert isinstance(status["installed"], bool)
    assert isinstance(status["prepared"], bool)
