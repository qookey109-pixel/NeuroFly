from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "live_maze_steering_dn_screen.py"


def test_live_maze_steering_dn_screen_script_parses() -> None:
    ast.parse(SCRIPT.read_text())


def test_live_maze_steering_dn_screen_is_observer_only() -> None:
    text = SCRIPT.read_text()
    assert 'SCHEMA = "neurofly-live-maze-steering-dn-screen-v1"' in text
    assert 'CANDIDATES = ("DNa03", "DNb06", "DNg13", "DNa11")' in text
    assert '"steering_observer_used_for_action": False' in text
    assert '"action_decoder_type": "DNa02"' in text
    assert '"decoder_change_authorized": False' in text
    assert "training_module.MaleCNSBrain = ProbeObserverBrain" in text
