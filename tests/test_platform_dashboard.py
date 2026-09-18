from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neurofly.brain_runtime import BrainDecision
from neurofly.cli import build_parser
from neurofly.environment_adapter import (
    EnvironmentSession,
    LightChaseAdapter,
    MazeChaseAdapter,
)
from neurofly.light_chase import LightChaseEnvironment
from neurofly.maze_runtime import MazeEnvironment
from neurofly.platform_server import PLATFORM_STATE_SCHEMA, PlatformService


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "site" / "platform.html"
JS = ROOT / "site" / "platform.js"
CSS = ROOT / "site" / "platform.css"


class CaptureBrain:
    name = "capture"

    def __init__(self, action: str = "HOLD") -> None:
        self.action = action
        self.calls: list[dict[str, Any]] = []

    def decide(self, frame, reinforcement="none", *, context=None) -> BrainDecision:
        self.calls.append(
            {
                "frame": frame,
                "reinforcement": reinforcement,
                "context": json.loads(json.dumps(context or {})),
            }
        )
        return BrainDecision(
            action=self.action,
            backend=self.name,
            telemetry={
                "brain_ms": 1.0,
                "compute_seconds": 0.001,
                "total_spikes": 1,
                "gate_spikes": 1,
            },
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text("capture\n")


class NoVisualMaze(MazeEnvironment):
    def render_rgb(self, *, width: int = 320, height: int = 180):
        raise RuntimeError("visual extras intentionally absent in unit test")


def _keys(value: Any) -> set[str]:
    out: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            out.add(str(key))
            out |= _keys(item)
    elif isinstance(value, list):
        for item in value:
            out |= _keys(item)
    return out


def test_platform_service_wraps_light_chase_public_state() -> None:
    brain = CaptureBrain()
    session = EnvironmentSession(
        brain,
        LightChaseAdapter(environment=LightChaseEnvironment(seed=109)),
    )
    service = PlatformService(session, tick_seconds=0.6, running=False)

    service.tick_once()
    payload = service.state()

    assert payload["schema"] == PLATFORM_STATE_SCHEMA
    assert payload["public_evaluation_state"] is True
    assert payload["neural_input_authority"] is False
    assert payload["environment_model"] == "neurofly-light-chase-v0.1"
    assert payload["arena"] == {"cols": 15, "rows": 11}
    assert "target" in payload["state"]
    assert "agent" in payload["state"]

    sensory_keys = _keys(payload["state"]["sensory_contract"])
    assert "target" not in sensory_keys
    assert "agent" not in sensory_keys
    assert "x" not in sensory_keys
    assert "y" not in sensory_keys


def test_platform_service_wraps_maze_public_state_without_neural_world_truth() -> None:
    brain = CaptureBrain()
    session = EnvironmentSession(
        brain,
        MazeChaseAdapter(environment=NoVisualMaze(seed=109)),
    )
    service = PlatformService(session, tick_seconds=0.6, running=False)

    service.tick_once()
    payload = service.state()

    assert payload["environment_model"] == "neurofly-maze-chase-v0.1"
    assert payload["arena"] == {"cols": 19, "rows": 14}
    assert "grid" in payload["state"]
    assert "fly" in payload["state"]
    assert "enemies" in payload["state"]

    sensory_keys = _keys(payload["state"]["sensory_contract"])
    for forbidden in {
        "grid",
        "fly",
        "enemies",
        "x",
        "y",
        "source",
        "distance_cells",
        "demo_action",
    }:
        assert forbidden not in sensory_keys


def test_platform_control_changes_runtime_only() -> None:
    session = EnvironmentSession(
        CaptureBrain(),
        LightChaseAdapter(environment=LightChaseEnvironment(seed=7)),
    )
    service = PlatformService(session, tick_seconds=0.6, running=True)

    before = session.adapter.persistence_snapshot()
    result = service.control({"running": False, "tick_seconds": 0.2})
    after = session.adapter.persistence_snapshot()

    assert result["runtime"]["running"] is False
    assert result["runtime"]["tick_seconds"] == 0.2
    assert before == after


def test_platform_cli_supports_both_registered_environments() -> None:
    parser = build_parser()

    maze = parser.parse_args(
        ["platform-server", "--environment", "maze", "--brain", "demo"]
    )
    light = parser.parse_args(
        ["platform-server", "--environment", "light", "--brain", "demo"]
    )

    assert maze.command == "platform-server"
    assert maze.environment == "maze"
    assert light.environment == "light"
    assert not hasattr(light, "target_x")
    assert not hasattr(light, "target_y")


def test_platform_site_is_parallel_to_legacy_maze_hud() -> None:
    html = HTML.read_text()
    js = JS.read_text()
    css = CSS.read_text()

    assert 'id="worldCanvas"' in html
    assert "platform.js?v=1" in html
    assert "platform.css?v=1" in html
    assert "/api/platform/state" in js
    assert "neurofly-maze-chase-v0.1" in js
    assert "neurofly-light-chase-v0.1" in js
    assert "drawMaze" in js
    assert "drawLight" in js
    assert "neural_input_authority" not in html
    assert ".dashboard-grid" in css

    # Existing production Maze HUD remains present and is not replaced.
    assert (ROOT / "site" / "index.html").is_file()
    assert (ROOT / "site" / "app.js").is_file()
