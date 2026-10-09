from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tactile_maze_ab_probe.py"


def test_tactile_ab_probe_script_parses() -> None:
    ast.parse(SCRIPT.read_text())


def test_tactile_ab_probe_is_same_checkpoint_and_decoder_safe() -> None:
    text = SCRIPT.read_text()
    assert 'SCHEMA = "neurofly-tactile-maze-ab-probe-v2"' in text
    assert 'kwargs["tactile_current"] = 0.0' in text
    assert 'kwargs["tactile_current"] = TACTILE_CALIBRATED_CURRENT' in text
    assert '"production_merge_authorized": False' in text
    assert '"decoder_change_authorized": False' in text
    assert "source_before != source_after" in text


def test_tactile_ab_probe_requires_onset_adaptation_evidence() -> None:
    text = SCRIPT.read_text()
    assert '"tactile_model": final_telemetry.get("tactile_model")' in text
    assert '"tactile_encoding": tactile_levels.get("encoding")' in text
